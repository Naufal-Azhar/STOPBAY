"""
Manual verification for _draw_annotations in capture_detect.py.
Run: python verify_draw_annotations.py
"""
import sys
import numpy as np

from services.capture_detect import _draw_annotations


def main():
    failures = []
    frame = np.zeros((240, 320, 3), dtype=np.uint8)  # blank BGR frame

    detections = [
        {"bbox": [10, 10, 100, 50], "yolo_confidence": 0.9, "ocr_text": "B1234ABC", "ocr_confidence": 0.8},
        {"bbox": [150, 100, 250, 140], "yolo_confidence": 0.5, "ocr_text": "GARBAGE1", "ocr_confidence": 0.3},
    ]

    annotated = _draw_annotations(frame, detections, winning_plate="B1234ABC")

    if annotated is frame:
        failures.append("_draw_annotations must return a new array, not mutate/alias the input")
    if annotated.shape != frame.shape:
        failures.append(f"Expected same shape {frame.shape}, got {annotated.shape}")
    if np.array_equal(annotated, frame):
        failures.append("Expected annotated frame to differ from blank input (no boxes drawn)")
    else:
        print("[OK] Annotated frame differs from blank input (boxes were drawn)")

    # No-plate case: empty detections + winning_plate=None should not raise
    try:
        blank_annotated = _draw_annotations(frame, [], None)
        if blank_annotated.shape != frame.shape:
            failures.append("Expected same shape for empty-detections case")
        else:
            print("[OK] Empty detections + winning_plate=None handled without error")
    except Exception as e:
        failures.append(f"Empty-detections case raised: {e}")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
