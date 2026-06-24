"""
STOPBAY v2.0 - Database Seeder
Generate dummy data for demo/testing without hardware.

Usage:
  python seed_data.py                 # default: 50 users, 20 active, 100 logs
  python seed_data.py --clean          # clear all data first
  python seed_data.py --users 100      # custom user count
  python seed_data.py --logs 200       # custom log count
  python seed_data.py --keep-active 0  # no active sessions
"""

import sys, os, random, argparse
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine, init_db
from models import Base, ActiveParking, ParkingLog, User, HardwareStatus

# ============================================================
# DUMMY DATA POOLS
# ============================================================
NAMES = [
    "Andi Pratama", "Budi Santoso", "Citra Dewi", "Dewi Lestari",
    "Eko Prasetyo", "Fitri Handayani", "Gilang Ramadhan",
    "Hendra Gunawan", "Indah Permata", "Joko Widodo",
    "Kartika Sari", "Lutfi Hakim", "Maya Anggraini", "Nina Amelia",
    "Oscar Putra", "Putri Ayu", "Rizky Febrian", "Sari Mulyani",
    "Tono Wijaya", "Umar Bakri", "Vina Melati", "Wawan Hermawan",
    "Yanti Susanti", "Zainal Arifin", "Ahmad Fauzi", "Bagus Prakoso",
    "Cahyo Nugroho", "Dina Amalia", "Erwin Kurniawan", "Farah Dibba",
]
DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "mail.com"]
PLATES = ["B", "D", "L", "F", "N", "AE", "AB", "H", "T", "W"]
PLATE_SUFFIX = ["ABC", "XYZ", "EFG", "HIJ", "KLM", "NOP", "QRS", "TUV", "WXY", "ZAB"]
STATUSES = ["WAITING", "ACTIVE"]
SPACES = ["SLOT_1", "SLOT_2"]

# ============================================================
# HELPERS
# ============================================================
def gen_plate():
    p = random.choice(PLATES)
    n = random.randint(1, 9999)
    s = random.choice(PLATE_SUFFIX)
    return f"{p} {n} {s}"

def gen_uid(seed=None):
    if seed is not None:
        random.seed(seed)
    return "".join(random.choices("0123456789ABCDEF", k=8))

def gen_nik():
    return f"32{random.randint(100000000000, 999999999999)}"[:16]

def gen_email(name):
    clean = name.lower().replace(" ", ".")
    return f"{clean}{random.randint(1,99)}@{random.choice(DOMAINS)}"

def random_date(days_back=30):
    now = datetime.now(timezone.utc)
    delta = timedelta(days=random.randint(0, days_back), hours=random.randint(0, 23), minutes=random.randint(0, 59))
    return now - delta

# ============================================================
# SEED FUNCTIONS
# ============================================================
def seed_users(db, count=50):
    print(f"\n[SEED] Generating {count} users...", end=" ")
    users = []
    existing = db.query(User).count()
    db.query(User).delete()
    for i in range(count):
        uid = gen_uid(seed=i)
        name = random.choice(NAMES)
        u = User(
            card_uid=uid,
            full_name=f"{name} {i+1}" if i < len(NAMES) else name,
            nik=gen_nik(),
            email=gen_email(name),
            phone=f"08{random.randint(1000000000, 9999999999)}",
            balance=random.choice([50000, 75000, 100000, 125000, 150000, 175000, 200000]),
            created_at=random_date(90),
            last_seen=random_date(7),
        )
        db.add(u)
        users.append(u)
    db.commit()
    print(f"\u2713 {count} created (was: {existing})")
    return users

def seed_active_parking(db, count=20):
    print(f"[SEED] Generating {count} active parking sessions...", end=" ")
    existing = db.query(ActiveParking).count()
    db.query(ActiveParking).delete()
    sessions = []
    users = db.query(User).all()
    now = datetime.now(timezone.utc)
    for i in range(count):
        status = random.choice(STATUSES)
        has_card = (status == "ACTIVE") and random.random() > 0.2
        user = random.choice(users) if users and has_card else None
        entry = now - timedelta(minutes=random.randint(5, 180))
        expiry = entry + timedelta(minutes=5) if status == "WAITING" else None
        s = ActiveParking(
            parking_space_id=f"SPACE-{random.randint(1, 2):02d}",
            plate_number=gen_plate(),
            card_uid=user.card_uid if user else None,
            entry_time=entry,
            status=status,
            space_label=random.choice(SPACES),
            snapshot_url=None,
            user_name=user.full_name if user else None,
            nik=user.nik if user else None,
            last_update=now,
            expiry_time=expiry,
        )
        db.add(s)
        sessions.append(s)
    db.commit()
    waiting = sum(1 for s in sessions if s.status == "WAITING")
    active = sum(1 for s in sessions if s.status == "ACTIVE")
    print(f"\u2713 {count} created ({waiting} WAITING + {active} ACTIVE) (was: {existing})")
    return sessions

def seed_parking_logs(db, count=100):
    print(f"[SEED] Generating {count} parking logs...", end=" ")
    existing = db.query(ParkingLog).count()
    db.query(ParkingLog).delete()
    logs = []
    users = db.query(User).all()
    for i in range(count):
        user = random.choice(users) if users and random.random() > 0.1 else None
        start = random_date(30)
        end = start + timedelta(hours=random.randint(1, 48))
        dur_h = round((end - start).total_seconds() / 3600.0, 2)
        fare = max(int(dur_h * 2000), 2000)
        forced = random.random() < 0.15
        bal = user.balance if user else 0
        bal_after = max(bal - fare, 0)
        l = ParkingLog(
            plate_number=gen_plate(),
            card_uid=user.card_uid if user else None,
            start_time=start,
            end_time=end,
            total_fare=fare,
            parking_space_id=f"SPACE-{random.randint(1, 2):02d}",
            space_label=random.choice(SPACES),
            user_name=user.full_name if user else None,
            nik=user.nik if user else None,
            snapshot_url=None,
            payment_method="FORCED_BILLING" if forced else "DUMMY_BALANCE",
            balance_before=bal if not forced else None,
            balance_after=bal_after if not forced else None,
            forced_billing=forced,
        )
        db.add(l)
        logs.append(l)
    db.commit()
    forced_count = sum(1 for l in logs if l.forced_billing)
    revenue = sum(l.total_fare for l in logs)
    print(f"\u2713 {count} created ({forced_count} forced, total revenue: Rp {revenue:,}) (was: {existing})")
    return logs

def seed_hardware_status(db):
    print(f"[SEED] Generating hardware devices...", end=" ")
    existing = db.query(HardwareStatus).count()
    db.query(HardwareStatus).delete()
    devices = [
        HardwareStatus(device_id="MAIN_ESP32_01", device_type="MAIN_CONTROLLER", location="PARKING_CENTER", is_online=True, last_heartbeat=datetime.now(timezone.utc)),
        HardwareStatus(device_id="CAM_SLOT1", device_type="ESP32_CAM", location="SLOT_1", is_online=True, last_heartbeat=datetime.now(timezone.utc)),
        HardwareStatus(device_id="RFID_SLOT1", device_type="RFID_RC522", location="SLOT_1", is_online=True, last_heartbeat=datetime.now(timezone.utc)),
        HardwareStatus(device_id="LCD_MAIN", device_type="LCD_I2C", location="PARKING_CENTER", is_online=True, last_heartbeat=datetime.now(timezone.utc)),
        HardwareStatus(device_id="SERVO_EXIT", device_type="SERVO_GATE", location="EXIT_GATE", is_online=True, last_heartbeat=datetime.now(timezone.utc)),
    ]
    for d in devices:
        db.add(d)
    db.commit()
    print(f"\u2713 {len(devices)} devices (was: {existing})")

def seed_all(users=50, active=20, logs=100, clean=False):
    print("=" * 50)
    print("  STOPBAY Database Seeder v2.0")
    print("=" * 50)
    init_db()
    db = SessionLocal()
    try:
        if clean:
            print("\n[CLEAN] Dropping all data...")
            db.query(ParkingLog).delete()
            db.query(ActiveParking).delete()
            db.query(User).delete()
            db.query(HardwareStatus).delete()
            db.commit()
            print("[CLEAN] All tables cleared.")
        seed_users(db, users)
        seed_active_parking(db, active)
        seed_parking_logs(db, logs)
        seed_hardware_status(db)
        print("\n" + "=" * 50)
        print("  \u2713 Database ready for demo!")
        print("=" * 50)
    finally:
        db.close()

# ============================================================
# CLI
# ============================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="STOPBAY Database Seeder")
    parser.add_argument("--clean", action="store_true", help="Clear all data before seeding")
    parser.add_argument("--users", type=int, default=50, help="Number of users (default: 50)")
    parser.add_argument("--active", type=int, default=20, help="Number of active parking (default: 20)")
    parser.add_argument("--logs", type=int, default=100, help="Number of parking logs (default: 100)")
    args = parser.parse_args()
    seed_all(users=args.users, active=args.active, logs=args.logs, clean=args.clean)
