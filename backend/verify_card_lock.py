"""
Manual verification for card-discipline guard on register_card.
Run: python verify_card_lock.py
Uses the real Postgres DB (per database.py) — cleans up rows it creates.
"""
import sys
from datetime import datetime
from fastapi.testclient import TestClient

from main import app
from database import SessionLocal
from models import ActiveParking, User

client = TestClient(app)
TEST_UID = f"TESTCARD{datetime.now().strftime('%H%M%S')}"


def cleanup():
    db = SessionLocal()
    db.query(ActiveParking).filter(ActiveParking.card_uid == TEST_UID).delete()
    db.query(User).filter(User.card_uid == TEST_UID).delete()
    db.commit()
    db.close()


def main():
    cleanup()
    failures = []

    # 1) First tap at SPACE-01 must succeed (creates ACTIVE session)
    r1 = client.put("/api/parking/register-card", json={
        "card_uid": TEST_UID, "parking_space_id": "SPACE-01",
    })
    if r1.status_code != 200:
        failures.append(f"Expected 200 on first tap, got {r1.status_code}: {r1.text}")
    else:
        print(f"[OK] First tap at SPACE-01 -> 200: {r1.json()['message']}")

    # 2) Second tap at SPACE-02 with same card must be rejected (409)
    r2 = client.put("/api/parking/register-card", json={
        "card_uid": TEST_UID, "parking_space_id": "SPACE-02",
    })
    if r2.status_code != 409:
        failures.append(f"Expected 409 on cross-slot re-tap, got {r2.status_code}: {r2.text}")
    else:
        print(f"[OK] Second tap at SPACE-02 -> 409 as expected")

    # 3) Re-tap at SAME slot (SPACE-01) with same card must also be rejected (409)
    r3 = client.put("/api/parking/register-card", json={
        "card_uid": TEST_UID, "parking_space_id": "SPACE-01",
    })
    if r3.status_code != 409:
        failures.append(f"Expected 409 on same-slot re-tap, got {r3.status_code}: {r3.text}")
    else:
        print(f"[OK] Re-tap at SPACE-01 (same slot) -> 409 as expected")

    cleanup()

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
