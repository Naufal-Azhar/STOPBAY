"""
STOPBAY v3.0 — OTA Firmware Hosting
Serve firmware binary files for ESP32 OTA updates.
"""

import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/ota", tags=["ota"])

FIRMWARE_DIR = os.path.join(os.path.dirname(__file__), "..", "firmware")
FIRMWARE_FILE = "firmware.bin"
CURRENT_VERSION = "1.0.0"


@router.get("/version")
def get_version():
    path = os.path.join(FIRMWARE_DIR, FIRMWARE_FILE)
    available = os.path.exists(path)
    size = os.path.getsize(path) if available else 0
    return {
        "latest_version": CURRENT_VERSION,
        "filename": FIRMWARE_FILE,
        "size": size,
        "available": available,
    }


@router.get("/firmware")
def download_firmware():
    path = os.path.join(FIRMWARE_DIR, FIRMWARE_FILE)
    if not os.path.exists(path):
        raise HTTPException(404, "Firmware not available")
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=FIRMWARE_FILE,
    )
