"""
STOPBAY v3.0 — On-demand Plate Capture + Detection
Grab single frame(s) from ESP32-CAM MJPEG stream on trigger (RFID tap),
run YOLOv8 + EasyOCR, return plate number + detection details.

Replaces continuous-stream detection.py: camera only wakes up when triggered,
instead of streaming/inferring 24/7.
"""

import os
import time
from collections import Counter

import cv2
import numpy as np
import requests
import torch
from ultralytics import YOLO
import easyocr

MODEL_PATH = os.path.join(os.path.dirname(__file__), "license-plate-detect.pt")

_model = None
_reader = None


def _get_model():
    """Load YOLOv8 plate detector once, cache in module global."""
    global _model
    if _model is not None:
        return _model

    if os.path.exists(MODEL_PATH):
        print(f"[capture] Loading model: {MODEL_PATH}")
        _model = YOLO(MODEL_PATH)
        return _model

    print(f"[capture] Model not found: {MODEL_PATH}")
    try:
        from huggingface_hub import hf_hub_download
        path = hf_hub_download(
            repo_id="keremberke/license-plate-object-detection",
            filename="best.pt",
            local_dir=os.path.dirname(__file__),
        )
        _model = YOLO(path)
        return _model
    except Exception:
        pass

    print("[capture] Falling back to yolov8n.pt (generic object detection, not plate-specific)")
    _model = YOLO("yolov8n.pt")
    return _model


def _get_reader():
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(["en"], gpu=torch.cuda.is_available())
    return _reader


def _grab_frame(cam_ip: str, timeout: float = 5.0):
    """Connect to MJPEG stream, grab the first complete JPEG frame, disconnect."""
    url = f"http://{cam_ip}/cam.mjpeg"
    resp = requests.get(url, stream=True, timeout=timeout)
    try:
        if resp.status_code != 200:
            return None
        content_type = resp.headers.get("Content-Type", "")
        if "boundary=" not in content_type:
            return None
        boundary = content_type.split("boundary=")[1].strip().strip("\"'")
        boundary_bytes = f"--{boundary}".encode()

        buffer = b""
        for chunk in resp.iter_content(chunk_size=4096):
            buffer += chunk
            start = buffer.find(boundary_bytes)
            if start == -1:
                continue
            next_start = buffer.find(boundary_bytes, start + len(boundary_bytes))
            if next_start == -1:
                continue
            part = buffer[start:next_start]
            jpg_start = part.find(b"\xff\xd8")
            jpg_end = part.rfind(b"\xff\xd9")
            if jpg_start == -1 or jpg_end == -1:
                continue
            jpg_data = part[jpg_start:jpg_end + 2]
            if len(jpg_data) < 100:
                continue
            return cv2.imdecode(np.frombuffer(jpg_data, dtype=np.uint8), cv2.IMREAD_COLOR)
    finally:
        resp.close()
    return None


def _detect_plate(frame):
    """Run YOLO + OCR on one frame. Returns list of {bbox, yolo_confidence, ocr_text, ocr_confidence}."""
    model = _get_model()
    reader = _get_reader()

    detections = []
    results = model(frame, verbose=False)
    for r in results:
        if r.boxes is None:
            continue
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            conf = float(box.conf[0]) if box.conf is not None else 0.0
            plate_img = frame[y1:y2, x1:x2]
            if plate_img.size == 0:
                continue

            ocr_results = reader.readtext(plate_img)
            texts = [t[1] for t in ocr_results if t[2] > 0.4]
            ocr_conf = max([t[2] for t in ocr_results], default=0.0)
            plate_text = "".join(c for c in " ".join(texts).strip().upper() if c.isalnum())

            detections.append({
                "bbox": [x1, y1, x2, y2],
                "yolo_confidence": round(conf, 3),
                "ocr_text": plate_text,
                "ocr_confidence": round(ocr_conf, 3),
            })
    return detections


def _draw_annotations(frame, detections: list, winning_plate: str | None):
    """Draw YOLO boxes on a copy of frame — green for the winning plate, gray for others."""
    annotated = frame.copy()
    for d in detections:
        x1, y1, x2, y2 = d["bbox"]
        is_winner = winning_plate is not None and d["ocr_text"] == winning_plate
        color = (0, 200, 0) if is_winner else (150, 150, 150)  # BGR
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        label = d["ocr_text"] or "?"
        cv2.putText(annotated, label, (x1, max(y1 - 8, 12)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    return annotated


def capture_and_detect(cam_ip: str, shots: int = 3, delay: float = 0.3) -> dict:
    """
    Take `shots` snapshots in quick succession, run YOLO+OCR on each,
    vote for the most consistent plate reading (replaces continuous-stream voting).

    Returns:
        {
            "success": bool,
            "plate_number": str | None,
            "votes": int,
            "total_shots": int,
            "shots": [{"shot": 1, "detections": [...]}, ...],
        }
    """
    shots_taken = []
    plate_votes = Counter()

    for i in range(shots):
        frame = _grab_frame(cam_ip)
        if frame is None:
            shots_taken.append({"shot": i + 1, "detections": [], "error": "capture failed"})
            continue

        dets = _detect_plate(frame)
        for d in dets:
            if len(d["ocr_text"]) >= 4:
                plate_votes[d["ocr_text"]] += 1
        shots_taken.append({"shot": i + 1, "detections": dets})

        if i < shots - 1:
            time.sleep(delay)

    if not plate_votes:
        return {
            "success": False,
            "plate_number": None,
            "votes": 0,
            "total_shots": len(shots_taken),
            "shots": shots_taken,
        }

    best_plate, votes = plate_votes.most_common(1)[0]
    return {
        "success": True,
        "plate_number": best_plate,
        "votes": votes,
        "total_shots": len(shots_taken),
        "shots": shots_taken,
    }
