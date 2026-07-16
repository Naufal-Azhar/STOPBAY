"""
Manual verification for grace-period-free exit logic on process_exit.
Run: python verify_exit_grace.py
Uses the real Postgres DB (per database.py) — cleans up rows it creates.
"""
import sys
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from main import app
from database import SessionLocal
from models import ActiveParking, ParkingLog, User

client = TestClient(app)
TEST_UID_NOSESSION = f"TESTNOSESS{datetime.now().strftime('%H%M%S')}"
TEST_UID_FREE = f"TESTFREE{datetime.now().strftime('%H%M%S')}"
TEST_UID_CHARGED = f"TESTCHRG{datetime.now().strftime('%H%M%S')}"


def cleanup(uid):
    db = SessionLocal()
    db.query(ParkingLog).filter(ParkingLog.card_uid == uid).delete()
    db.query(ActiveParking).filter(ActiveParking.card_uid == uid).delete()
    db.query(User).filter(User.card_uid == uid).delete()
    db.commit()
    db.close()


def make_active_session(uid, entry_minutes_ago):
    """Insert an ACTIVE session directly, backdating entry_time to simulate elapsed time."""
    db = SessionLocal()
    entry_time = datetime.now(timezone.utc) - timedelta(minutes=entry_minutes_ago)
    session = ActiveParking(
        parking_space_id="SPACE-01", card_uid=uid, status="ACTIVE",
        entry_time=entry_time, space_label="SLOT_1",
    )
    db.add(session)
    db.commit()
    db.close()


def main():
    for uid in (TEST_UID_NOSESSION, TEST_UID_FREE, TEST_UID_CHARGED):
        cleanup(uid)
    failures = []

    # 1) Exit with a card that never tapped a slot -> free, no log row
    r1 = client.post("/api/parking/exit", json={"card_uid": TEST_UID_NOSESSION})
    if r1.status_code != 200 or r1.json().get("total_fare") != 0:
        failures.append(f"Expected 200/total_fare=0 for no-session exit, got {r1.status_code}: {r1.text}")
    else:
        db = SessionLocal()
        log_count = db.query(ParkingLog).filter(ParkingLog.card_uid == TEST_UID_NOSESSION).count()
        db.close()
        if log_count != 0:
            failures.append(f"Expected 0 ParkingLog rows for no-session exit, found {log_count}")
        else:
            print("[OK] No-session exit -> total_fare=0, no ParkingLog row")

    # 2) Exit within grace period (2 minutes elapsed) -> free, but log row created
    make_active_session(TEST_UID_FREE, entry_minutes_ago=2)
    r2 = client.post("/api/parking/exit", json={"card_uid": TEST_UID_FREE})
    if r2.status_code != 200 or r2.json().get("total_fare") != 0:
        failures.append(f"Expected 200/total_fare=0 for grace-period exit, got {r2.status_code}: {r2.text}")
    else:
        db = SessionLocal()
        log = db.query(ParkingLog).filter(ParkingLog.card_uid == TEST_UID_FREE).first()
        db.close()
        if not log or log.payment_method != "FREE_EXIT":
            failures.append(f"Expected ParkingLog with payment_method=FREE_EXIT, got {log}")
        else:
            print("[OK] Grace-period exit -> total_fare=0, ParkingLog.payment_method=FREE_EXIT")

    # 3) Exit after grace period (10 minutes elapsed) -> charged normally (regression check)
    make_active_session(TEST_UID_CHARGED, entry_minutes_ago=10)
    r3 = client.post("/api/parking/exit", json={"card_uid": TEST_UID_CHARGED})
    if r3.status_code != 200 or r3.json().get("total_fare", 0) <= 0:
        failures.append(f"Expected 200/total_fare>0 for post-grace exit, got {r3.status_code}: {r3.text}")
    else:
        print(f"[OK] Post-grace exit -> total_fare={r3.json()['total_fare']} (charged normally)")

    for uid in (TEST_UID_NOSESSION, TEST_UID_FREE, TEST_UID_CHARGED):
        cleanup(uid)

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
