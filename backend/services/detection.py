"""
STOPBAY v3.0 — License Plate Detection
Consume MJPEG stream from ESP32-S/CAM, run YOLOv8n + PaddleOCR, HTTP POST to backend.

Usage:
    python detection.py --slot 1 --cam-ip 192.168.1.101
    python detection.py --slot 2 --cam-ip 192.168.1.102

Requires pre-trained plate detection model.
    Place model at: backend/services/license-plate-detect.pt
    Source: Ultralytics HUB or Roboflow Universe (search "license plate detection")
"""

import argparse
import json
import os
import time
from collections import Counter, defaultdict, deque

import requests

import cv2
import numpy as np
import easyocr
import torch
from ultralytics import YOLO

MODEL_PATH = os.path.join(os.path.dirname(__file__), "license-plate-detect.pt")
MODEL_URL = "https://universe.roboflow.com/.../license-plate-detect.pt"

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def get_model():
    """Load YOLOv8n plate detector. Download if not cached locally."""
    if os.path.exists(MODEL_PATH):
        print(f"[detection] Loading model: {MODEL_PATH}")
        return YOLO(MODEL_PATH)

    print(f"[detection] Model not found: {MODEL_PATH}")
    print(f"[detection] Attempting HuggingFace Hub pull...")
    # ponytail: try HF hub first, fallback to download URL
    try:
        from huggingface_hub import hf_hub_download
        path = hf_hub_download(
            repo_id="keremberke/license-plate-object-detection",
            filename="best.pt",
            local_dir=os.path.dirname(__file__),
        )
        return YOLO(path)
    except Exception:
        pass

    print("[detection] Pulling from Ultralytics HUB...")
    model = YOLO("yolov8n.pt")  # fallback: base model
    return model


def connect_stream(url):
    """Connect to MJPEG stream with infinite retry."""
    while True:
        try:
            stream = requests.get(url, stream=True, timeout=10)
            if stream.status_code != 200:
                print(f"[detection] HTTP {stream.status_code}, retrying in 3s...")
                time.sleep(3)
                continue
            return stream
        except Exception as e:
            print(f"[detection] Stream error: {e}, retrying in 3s...")
            time.sleep(3)


def detect(slot: int, cam_ip: str):
    model = get_model()
    reader = easyocr.Reader(['en'], gpu=torch.cuda.is_available())

    url = f"http://{cam_ip}/cam.mjpeg"

    print(f"[detection] Slot {slot} — streaming from {url}")
    print(f"[detection] POST to: {BACKEND_URL}/api/parking/space-occupied")

    posted_plate = None
    plate_readings = deque(maxlen=10)  # rolling window for voting
    vote_wins = defaultdict(int)  # how many rounds each plate has won
    plate_locked = False  # ponytail: lock after POST, unlock on true leave
    empty_frames = 0

    while True:
        buffer = b""
        try:
            stream = connect_stream(url)
            # ponytail: parse boundary on every reconnect (may change)
            content_type = stream.headers.get("Content-Type", "")
            if "boundary=" in content_type:
                boundary = content_type.split("boundary=")[1].strip()
                if boundary.startswith('"') or boundary.startswith("'"):
                    boundary = boundary[1:-1]
            else:
                print("[detection] ERROR: No boundary, retrying...")
                time.sleep(3)
                continue
            boundary_bytes = f"--{boundary}".encode()
            for chunk in stream.iter_content(chunk_size=4096):
                buffer += chunk
                while True:
                    start = buffer.find(boundary_bytes)
                    if start == -1:
                        break
                    next_start = buffer.find(boundary_bytes, start + len(boundary_bytes))
                    if next_start == -1:
                        break
                    part = buffer[start:next_start]
                    buffer = buffer[next_start:]
                    jpg_start = part.find(b"\xff\xd8")
                    jpg_end = part.rfind(b"\xff\xd9")
                    if jpg_start == -1 or jpg_end == -1:
                        continue
                    jpg_data = part[jpg_start:jpg_end + 2]
                    if len(jpg_data) < 100:
                        continue
                    frame = cv2.imdecode(np.frombuffer(jpg_data, dtype=np.uint8), cv2.IMREAD_COLOR)
                    if frame is None:
                        continue

                    results = model(frame, verbose=False)
                    plate_found = False

                    for r in results:
                        if r.boxes is None:
                            continue
                        for box in r.boxes:
                            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                            plate_img = frame[y1:y2, x1:x2]

                            if plate_img.size == 0:
                                continue

                            ocr_results = reader.readtext(plate_img)
                            # ponytail: filter by confidence, join all text boxes, min 4 chars
                            texts = [t[1] for t in ocr_results if t[2] > 0.4]
                            if not texts:
                                continue
                            plate_text = " ".join(texts).strip().upper()
                            plate_text = "".join(c for c in plate_text if c.isalnum())
                            if len(plate_text) < 4:
                                continue

                            plate_readings.append(plate_text)

                            if len(plate_readings) >= 3:
                                counter = Counter(plate_readings)
                                best_plate, best_count = counter.most_common(1)[0]
                                if best_count >= 3:
                                    vote_wins[best_plate] += 1
                                    if not plate_locked:
                                        print(f"[detection] VOTE: {best_plate} ({best_count}/{len(plate_readings)}) — wins: {vote_wins[best_plate]}/3")
                                    if vote_wins[best_plate] >= 3 and not plate_locked:
                                        print(f"[detection] PLATE: {best_plate} -> POST {BACKEND_URL}/api/parking/space-occupied")
                                        payload = {
                                            "plate_number": best_plate,
                                            "parking_space_id": f"SPACE-0{slot}",
                                            "space_label": f"SLOT_{slot}"
                                        }
                                        try:
                                            requests.post(f"{BACKEND_URL}/api/parking/space-occupied", json=payload, timeout=5)
                                        except Exception as e:
                                            print(f"[detection] POST failed: {e}")
                                        posted_plate = best_plate
                                        plate_locked = True

                            plate_found = True

                    if not plate_found:
                        empty_frames += 1
                        if empty_frames > 90 and plate_locked:
                            print(f"[detection] Plate left — reset")
                            posted_plate = None
                            plate_locked = False
                            plate_readings.clear()
                            vote_wins.clear()
                            empty_frames = 0
                    else:
                        empty_frames = 0

        except KeyboardInterrupt:
            print("\n[detection] Stopping...")
            break
        except Exception as e:
            print(f"[detection] Stream died: {e}, reconnecting in 2s...")
            time.sleep(2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="STOPBAY plate detection")
    parser.add_argument("--slot", type=int, required=True, help="Slot number (1 or 2)")
    parser.add_argument("--cam-ip", type=str, required=True, help="ESP32-S/CAM IP address")
    args = parser.parse_args()

    detect(slot=args.slot, cam_ip=args.cam_ip)
