"""
Manual verification for _save_capture in capture_detect.py.
Run: python verify_save_capture.py
"""
import glob
import os
import sys
import numpy as np

from services.capture_detect import _save_capture, CAPTURES_DIR


def main():
    failures = []
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    space_id = "SPACE-99"  # dummy slot id, won't collide with real slots 1/2

    # Clean slate
    for f in glob.glob(os.path.join(CAPTURES_DIR, f"{space_id}_*.jpg")):
        os.remove(f)

    url1 = _save_capture(frame, space_id)
    path1 = os.path.join(CAPTURES_DIR, os.path.basename(url1))
    if not url1.startswith("/captures/"):
        failures.append(f"Expected url to start with /captures/, got {url1}")
    elif not os.path.exists(path1):
        failures.append(f"Expected file to exist at {path1}")
    else:
        print(f"[OK] First save created {url1}")

    # Second save for same space_id must overwrite (only one file should remain)
    url2 = _save_capture(frame, space_id)
    remaining = glob.glob(os.path.join(CAPTURES_DIR, f"{space_id}_*.jpg"))
    if len(remaining) != 1:
        failures.append(f"Expected exactly 1 file after second save (overwrite), found {len(remaining)}: {remaining}")
    else:
        print(f"[OK] Second save overwrote old file — 1 file remains: {url2}")

    # Cleanup
    for f in glob.glob(os.path.join(CAPTURES_DIR, f"{space_id}_*.jpg")):
        os.remove(f)

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
