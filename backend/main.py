"""
STOPBAY v3.0 - FastAPI Backend
Ticketless Smart Parking System with MQTT + Camera Stream Proxy

Endpoints:
  POST   /api/parking/space-occupied
  PUT    /api/parking/register-card
  POST   /api/parking/forced-billing
  GET    /api/parking/status/{card_uid}
  POST   /api/parking/exit
  GET    /api/parking/active
  GET    /api/parking/logs
  GET    /api/parking/stats
  GET    /api/parking/by-plate/{plate}     (NEW v3)
  POST   /api/hardware/heartbeat
  GET    /api/hardware/status
  GET    /api/users
  GET    /api/users/{card_uid}
  POST   /api/users/{card_uid}/topup
  GET    /api/stream/{slot}               (NEW v3)
"""

import asyncio, json, os, random, uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

import aiomqtt

from database import SessionLocal, get_db, init_db
from models import ActiveParking, ParkingLog, User, HardwareStatus
from schemas import (
    SpaceOccupiedRequest, RegisterCardRequest, ForcedBillingRequest,
    ExitRequest, HeartbeatRequest, TopupRequest,
    SpaceOccupiedResponse, RegisterCardResponse, ForcedBillingResponse,
    ParkingStatusResponse, ParkingStatusData, ExitResponse, HeartbeatResponse,
)
from services.stream_proxy import proxy_stream

# ponytail: optional modules — skip if deps not installed (Render free tier)
try:
    from api.ota import router as ota_router
except ImportError:
    ota_router = None

try:
    from services.push_notification import router as push_router
except ImportError:
    push_router = None

# ============================================================
# CONFIG
# ============================================================
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

FARE_PER_HOUR = 1000  # v3: Rp 1.000/jam
GRACE_MINUTES = 5
FORCED_BILLING_FARE = FARE_PER_HOUR


# ============================================================
# MQTT Listener (background task)
# ============================================================
async def mqtt_listener(client: aiomqtt.Client):
    """Subscribe plates/#, forward plate detections to space-occupied."""
    await client.subscribe("plates/#")
    async for message in client.messages:
        try:
            data = json.loads(message.payload.decode())
            plate = data.get("plate", "").strip()
            slot = data.get("slot", 1)
            if not plate:
                continue
            # ponytail: slot -> parking_space_id mapping
            space_id = f"SPACE-0{slot}"
            _handle_plate_detection(plate, space_id)
        except Exception:
            pass


def _handle_plate_detection(plate_number: str, parking_space_id: str):
    """Write plate detection directly to DB (no HTTP call needed)."""
    db = SessionLocal()
    try:
        existing = db.query(ActiveParking).filter(
            ActiveParking.parking_space_id == parking_space_id,
            ActiveParking.status.in_(["WAITING", "ACTIVE"]),
        ).first()
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(minutes=GRACE_MINUTES)

        if existing:
            existing.plate_number = plate_number
            existing.status = "WAITING"
            existing.card_uid = None
            existing.entry_time = now
            existing.space_label = f"SLOT_{parking_space_id[-1]}"
            existing.expiry_time = expiry
            existing.user_name = None
            existing.nik = None
        else:
            session = ActiveParking(
                parking_space_id=parking_space_id,
                plate_number=plate_number,
                status="WAITING",
                entry_time=now,
                space_label=f"SLOT_{parking_space_id[-1]}",
                expiry_time=expiry,
            )
            db.add(session)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


# ============================================================
# APP + Lifespan (MQTT startup/shutdown)
# ============================================================
@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    # Start MQTT client
    try:
        async with aiomqtt.Client(MQTT_BROKER, MQTT_PORT) as mqtt_client:
            task = asyncio.create_task(mqtt_listener(mqtt_client))
            yield
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    except aiomqtt.MqttError as e:
        print(f"[MQTT] Broker unavailable: {e}. Backend running without MQTT.")
        yield


app = FastAPI(title="STOPBAY v3.0", version="3.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

if ota_router:
    app.include_router(ota_router)
if push_router:
    app.include_router(push_router)

@app.get("/")
def root():
    return {"service": "STOPBAY v2.0", "status": "running"}


# ============================================================
# Dummy name generator for auto-registered users
# ============================================================
DUMMY_NAMES = ["Andi Pratama", "Budi Santoso", "Citra Dewi", "Dewi Lestari",
               "Eko Prasetyo", "Fitri Handayani", "Gilang Ramadhan",
               "Hendra Gunawan", "Indah Permata", "Joko Widodo"]
DUMMY_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "mail.com"]

def _generate_user_info(card_uid: str):
    """Auto-generate dummy user info from card UID."""
    seed = sum(ord(c) for c in card_uid)
    name = DUMMY_NAMES[seed % len(DUMMY_NAMES)]
    nik = f"32{seed:010d}"[:16]
    email = f"{name.lower().replace(' ', '.')}.{card_uid[:4].lower()}@{DUMMY_DOMAINS[seed % len(DUMMY_DOMAINS)]}"
    return name, nik, email


def _get_or_create_user(db: Session, card_uid: str) -> User:
    """Get existing user or auto-register on first tap."""
    user = db.query(User).filter(User.card_uid == card_uid).first()
    if not user:
        name, nik, email = _generate_user_info(card_uid)
        balance = random.randint(50000, 200000)  # random saldo
        user = User(card_uid=card_uid, full_name=name, nik=nik, email=email, balance=balance)
        db.add(user)
        db.commit()
        db.refresh(user)
    user.last_seen = datetime.now(timezone.utc)
    db.commit()
    return user


# ============================================================
# POST /api/parking/space-occupied
# ============================================================
@app.post("/api/parking/space-occupied", response_model=SpaceOccupiedResponse)
def space_occupied(req: SpaceOccupiedRequest, db: Session = Depends(get_db)):
    existing = db.query(ActiveParking).filter(
        ActiveParking.parking_space_id == req.parking_space_id,
        ActiveParking.status.in_(["WAITING", "ACTIVE"]),
    ).first()
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(minutes=GRACE_MINUTES)

    if existing:
        existing.plate_number = req.plate_number
        existing.status = "WAITING"
        existing.card_uid = None
        existing.entry_time = now
        existing.snapshot_url = req.snapshot_url
        existing.space_label = req.space_label or existing.space_label
        existing.expiry_time = expiry
        existing.user_name = None
        existing.nik = None
        db.commit()
        return SpaceOccupiedResponse(
            success=True, message="Space re-occupied, waiting for card",
            id=existing.id, expiry_time=expiry.isoformat(), grace_period_minutes=GRACE_MINUTES,
        )

    session = ActiveParking(
        parking_space_id=req.parking_space_id, plate_number=req.plate_number,
        status="WAITING", entry_time=now, snapshot_url=req.snapshot_url,
        space_label=req.space_label or "SLOT_1", expiry_time=expiry,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return SpaceOccupiedResponse(
        success=True, message="Space occupied, waiting for card",
        id=session.id, expiry_time=expiry.isoformat(), grace_period_minutes=GRACE_MINUTES,
    )


# ============================================================
# PUT /api/parking/register-card
# ============================================================
@app.put("/api/parking/register-card", response_model=RegisterCardResponse)
def register_card(req: RegisterCardRequest, db: Session = Depends(get_db)):
    session = db.query(ActiveParking).filter(
        ActiveParking.parking_space_id == req.parking_space_id,
        ActiveParking.plate_number == req.plate_number,
        ActiveParking.status == "WAITING",
    ).order_by(ActiveParking.entry_time.desc()).first()

    if not session:
        raise HTTPException(404, "No waiting session found")

    # Check grace period
    elapsed = (datetime.now(timezone.utc) - session.entry_time.replace(tzinfo=timezone.utc)).total_seconds()
    if elapsed > GRACE_MINUTES * 60:
        db.delete(session); db.commit()
        raise HTTPException(408, "Grace period expired — session cancelled")

    # Auto-register user
    user = _get_or_create_user(db, req.card_uid)

    session.card_uid = req.card_uid
    session.status = "ACTIVE"
    session.entry_time = datetime.now(timezone.utc)
    session.user_name = user.full_name
    session.nik = user.nik
    session.expiry_time = None  # clear forced billing deadline
    session.last_update = datetime.now(timezone.utc)
    db.commit()
    db.refresh(session)

    return RegisterCardResponse(
        success=True, message=f"Registration success — Welcome {user.full_name}!",
        fare_per_hour=FARE_PER_HOUR, entry_time=session.entry_time.isoformat(),
        user_name=user.full_name, balance=user.balance,
    )


# ============================================================
# POST /api/parking/forced-billing
# ============================================================
@app.post("/api/parking/forced-billing", response_model=ForcedBillingResponse)
def forced_billing(req: ForcedBillingRequest, db: Session = Depends(get_db)):
    session = db.query(ActiveParking).filter(
        ActiveParking.parking_space_id == req.parking_space_id,
        ActiveParking.plate_number == req.plate_number,
        ActiveParking.status == "WAITING",
    ).first()

    if not session:
        raise HTTPException(404, "No waiting session found for this plate")

    now = datetime.now(timezone.utc)
    log = ParkingLog(
        plate_number=session.plate_number, card_uid=None,
        start_time=session.entry_time, end_time=now,
        total_fare=FORCED_BILLING_FARE, parking_space_id=session.parking_space_id,
        space_label=session.space_label, user_name=None, nik=None,
        snapshot_url=session.snapshot_url, payment_method="FORCED_BILLING",
        forced_billing=True,
    )
    db.add(log)
    db.delete(session)
    db.commit()
    return ForcedBillingResponse(
        success=True, message=f"Forced billing applied — Rp {FORCED_BILLING_FARE:,}",
        total_fare=FORCED_BILLING_FARE, plate_number=req.plate_number,
    )


# ============================================================
# GET /api/parking/status/{card_uid}
# ============================================================
@app.get("/api/parking/status/{card_uid}", response_model=ParkingStatusResponse)
def get_status(card_uid: str, db: Session = Depends(get_db)):
    session = db.query(ActiveParking).filter(
        ActiveParking.card_uid == card_uid,
        ActiveParking.status == "ACTIVE",
    ).first()
    if not session:
        return ParkingStatusResponse(success=False, message="No active session", data=None)

    now = datetime.now(timezone.utc)
    entry = session.entry_time.replace(tzinfo=timezone.utc) if session.entry_time.tzinfo is None else session.entry_time
    dur_sec = max(int((now - entry).total_seconds()), 1)
    fare = max(int((dur_sec / 3600.0) * FARE_PER_HOUR), FARE_PER_HOUR)

    return ParkingStatusResponse(success=True, message="Active", data=ParkingStatusData(
        plate_number=session.plate_number, parking_space_id=session.parking_space_id,
        space_label=session.space_label, card_uid=session.card_uid,
        user_name=session.user_name, entry_time=session.entry_time.isoformat(),
        duration_minutes=round(dur_sec / 60.0, 1), duration_seconds=dur_sec,
        current_fare=fare, status=session.status, fare_per_hour=FARE_PER_HOUR,
    ))


# ============================================================
# POST /api/parking/exit
# ============================================================
@app.post("/api/parking/exit", response_model=ExitResponse)
def process_exit(req: ExitRequest, db: Session = Depends(get_db)):
    session = db.query(ActiveParking).filter(
        ActiveParking.card_uid == req.card_uid, ActiveParking.status == "ACTIVE",
    ).first()
    if not session:
        raise HTTPException(404, "No active session found")

    user = db.query(User).filter(User.card_uid == req.card_uid).first()
    now = datetime.now(timezone.utc)
    entry = session.entry_time.replace(tzinfo=timezone.utc) if session.entry_time.tzinfo is None else session.entry_time
    dur_h = round((now - entry).total_seconds() / 3600.0, 2)
    fare = max(int(dur_h * FARE_PER_HOUR), FARE_PER_HOUR)

    bal_before = user.balance if user else 0
    bal_after = max(bal_before - fare, 0) if user else 0
    if bal_before < fare:
        # Saldo kurang — tetap proses tapi log
        bal_after = 0

    if user:
        user.balance = bal_after
        user.last_seen = now

    log = ParkingLog(
        plate_number=session.plate_number, card_uid=session.card_uid,
        start_time=session.entry_time, end_time=now, total_fare=fare,
        parking_space_id=session.parking_space_id, space_label=session.space_label,
        user_name=session.user_name, nik=session.nik,
        snapshot_url=session.snapshot_url, payment_method="DUMMY_BALANCE",
        balance_before=bal_before, balance_after=bal_after, forced_billing=False,
    )
    db.add(log)
    db.delete(session)
    db.commit()
    db.refresh(log)

    return ExitResponse(
        success=True, message="Payment success",
        plate_number=log.plate_number, start_time=log.start_time.isoformat(),
        end_time=log.end_time.isoformat(), duration_hours=dur_h, total_fare=fare,
        balance_before=bal_before, balance_after=bal_after,
    )


# ============================================================
# GET /api/parking/active
# ============================================================
@app.get("/api/parking/active")
def get_active(db: Session = Depends(get_db)):
    sessions = db.query(ActiveParking).all()
    now = datetime.now(timezone.utc)
    result = []
    for s in sessions:
        entry = s.entry_time.replace(tzinfo=timezone.utc) if s.entry_time and s.entry_time.tzinfo is None else s.entry_time
        dmin = round((now - entry).total_seconds() / 60.0, 1) if entry else 0
        fare = max(int((dmin / 60.0) * FARE_PER_HOUR), 0) if s.status == "ACTIVE" else 0
        result.append({**s.to_dict(), "duration_minutes": dmin, "current_fare": fare})
    return {"success": True, "count": len(result), "data": result}


# ============================================================
# GET /api/parking/logs
# ============================================================
@app.get("/api/parking/logs")
def get_logs(page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=200),
             date: str = Query(None), db: Session = Depends(get_db)):
    q = db.query(ParkingLog)
    if date: q = q.filter(ParkingLog.start_time >= datetime.fromisoformat(date))
    total = q.count()
    logs = q.order_by(ParkingLog.end_time.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return {
        "success": True, "page": page, "per_page": per_page, "total": total,
        "total_pages": max(1, (total + per_page - 1) // per_page),
        "total_revenue": sum(l.total_fare for l in logs),
        "data": [l.to_dict() for l in logs],
    }


# ============================================================
# GET /api/parking/stats
# ============================================================
@app.get("/api/parking/stats")
def get_stats(db: Session = Depends(get_db)):
    active = db.query(ActiveParking).count()
    waiting = db.query(ActiveParking).filter(ActiveParking.status == "WAITING").count()
    parked = db.query(ActiveParking).filter(ActiveParking.status == "ACTIVE").count()
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_rev = db.query(func.coalesce(func.sum(ParkingLog.total_fare), 0)).filter(ParkingLog.end_time >= today).scalar()
    today_sess = db.query(ParkingLog).filter(ParkingLog.end_time >= today).count()
    total_logs = db.query(ParkingLog).count()
    return {
        "success": True,
        "stats": {
            "active_sessions": active, "waiting_registration": waiting,
            "active_parked": parked, "total_history": total_logs,
            "today_sessions": today_sess, "today_revenue": int(today_rev),
            "fare_per_hour": FARE_PER_HOUR, "grace_minutes": GRACE_MINUTES,
            "forced_billing_fare": FORCED_BILLING_FARE,
        },
    }


# ============================================================
# POST /api/hardware/heartbeat
# ============================================================
@app.post("/api/hardware/heartbeat")
def heartbeat(req: HeartbeatRequest, db: Session = Depends(get_db)):
    extra = json.dumps({
        "slots_active": req.slots_active, "rfid_slot1_ok": req.rfid_slot1_ok,
        "cam1_ok": req.cam1_ok, "lcd1_ok": req.lcd1_ok, "servo_ok": req.servo_ok,
    }) if any([req.slots_active, req.rfid_slot1_ok, req.cam1_ok, req.lcd1_ok, req.servo_ok]) else None

    hw = db.query(HardwareStatus).filter(HardwareStatus.device_id == req.device_id).first()
    if hw:
        hw.is_online = True
        hw.last_heartbeat = datetime.now(timezone.utc)
        hw.extra_info = extra
        hw.device_type = req.device_type
        hw.location = req.location
    else:
        hw = HardwareStatus(
            device_id=req.device_id, device_type=req.device_type,
            location=req.location, is_online=True, extra_info=extra,
        )
        db.add(hw)
    db.commit()
    return {"success": True}


# ============================================================
# GET /api/hardware/status
# ============================================================
@app.get("/api/hardware/status")
def get_hardware_status(db: Session = Depends(get_db)):
    devices = db.query(HardwareStatus).all()
    online = sum(1 for d in devices if d.is_online)
    # Mark devices offline if no heartbeat in 2 minutes
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=2)
    for d in devices:
        if d.last_heartbeat.replace(tzinfo=timezone.utc) < cutoff:
            d.is_online = False
    db.commit()
    return {"success": True, "devices_online": online, "total": len(devices),
            "data": [d.to_dict() for d in devices]}


# ============================================================
# GET /api/users
# ============================================================
@app.get("/api/users")
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return {"success": True, "count": len(users), "data": [u.to_dict() for u in users]}


# ============================================================
# GET /api/users/{card_uid}
# ============================================================
@app.get("/api/users/{card_uid}")
def get_user(card_uid: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.card_uid == card_uid).first()
    if not user:
        raise HTTPException(404, "User not found")
    return {"success": True, "data": user.to_dict()}


# ============================================================
# POST /api/users/{card_uid}/topup
# ============================================================
@app.post("/api/users/{card_uid}/topup")
def topup_user(card_uid: str, req: TopupRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.card_uid == card_uid).first()
    if not user:
        user = _get_or_create_user(db, card_uid)
    user.balance += req.amount
    user.last_seen = datetime.now(timezone.utc)
    db.commit()
    return {"success": True, "message": f"Top-up Rp {req.amount:,}",
            "card_uid": card_uid, "new_balance": user.balance}


# ============================================================
# GET /api/parking/by-plate/{plate}   (NEW v3 — PWA lookup)
# ============================================================
@app.get("/api/parking/by-plate/{plate}")
def get_by_plate(plate: str, db: Session = Depends(get_db)):
    session = db.query(ActiveParking).filter(
        ActiveParking.plate_number.ilike(f"%{plate}%"),
        ActiveParking.status.in_(["WAITING", "ACTIVE"]),
    ).order_by(ActiveParking.entry_time.desc()).first()

    if not session:
        return {"success": False, "message": "No session found for this plate", "data": None}

    now = datetime.now(timezone.utc)
    entry = session.entry_time.replace(tzinfo=timezone.utc) if session.entry_time and session.entry_time.tzinfo is None else session.entry_time
    dmin = round((now - entry).total_seconds() / 60.0, 1) if entry else 0
    fare = max(int((dmin / 60.0) * FARE_PER_HOUR), 0) if session.status == "ACTIVE" else 0

    return {
        "success": True,
        "data": {
            **session.to_dict(),
            "duration_minutes": dmin,
            "current_fare": fare,
        },
    }


# ============================================================
# GET /api/stream/{slot}   (NEW v3 — MJPEG proxy)
# ============================================================
@app.get("/api/stream/{slot}")
async def stream_slot(slot: int):
    return StreamingResponse(
        proxy_stream(slot),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


# ============================================================
# RUN
# ============================================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
