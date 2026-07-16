"""
Manual verification for capture_and_detect's new space_id param + snapshot_url output.
Run: python verify_capture_snapshot.py
Stubs _grab_frame so no real ESP32-CAM is required.
"""
import glob
import os
import sys
from unittest.mock import patch

import numpy as np

import services.capture_detect as cd

SPACE_ID = "SPACE-98"  # dummy, won't collide with real slots


def cleanup():
    for f in glob.glob(os.path.join(cd.CAPTURES_DIR, f"{SPACE_ID}_*.jpg")):
        os.remove(f)


def fake_grab_frame_with_plate(cam_ip, timeout=5.0):
    return np.zeros((240, 320, 3), dtype=np.uint8)


def fake_detect_plate_with_plate(frame):
    return [{"bbox": [10, 10, 100, 50], "yolo_confidence": 0.9, "ocr_text": "B1234ABC", "ocr_confidence": 0.8}]


def fake_detect_plate_none(frame):
    return []


def main():
    cleanup()
    failures = []

    # Case 1: plate detected across shots -> success, snapshot_url set
    with patch.object(cd, "_grab_frame", side_effect=fake_grab_frame_with_plate), \
         patch.object(cd, "_detect_plate", side_effect=fake_detect_plate_with_plate):
        result = cd.capture_and_detect("fake-ip", SPACE_ID, shots=2, delay=0)

    if not result["success"] or result["plate_number"] != "B1234ABC":
        failures.append(f"Expected success with plate B1234ABC, got {result}")
    elif not result.get("snapshot_url"):
        failures.append(f"Expected snapshot_url to be set, got {result.get('snapshot_url')}")
    else:
        print(f"[OK] Plate detected -> snapshot_url={result['snapshot_url']}")

    cleanup()

    # Case 2: no plate detected in any shot -> failure, but snapshot_url still set (plain frame saved)
    with patch.object(cd, "_grab_frame", side_effect=fake_grab_frame_with_plate), \
         patch.object(cd, "_detect_plate", side_effect=fake_detect_plate_none):
        result2 = cd.capture_and_detect("fake-ip", SPACE_ID, shots=2, delay=0)

    if result2["success"]:
        failures.append(f"Expected success=False when no plate detected, got {result2}")
    elif not result2.get("snapshot_url"):
        failures.append(f"Expected snapshot_url still set (plain frame) even without plate, got {result2.get('snapshot_url')}")
    else:
        print(f"[OK] No plate detected -> success=False, snapshot_url still set: {result2['snapshot_url']}")

    cleanup()

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
