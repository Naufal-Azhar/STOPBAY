"""
STOPBAY v3.0 — MJPEG Stream Proxy
Proxy live MJPEG streams from ESP32-S/CAM via FastAPI StreamingResponse.
"""

import asyncio
import os
import httpx
from fastapi import HTTPException

SLOT1_IP = os.getenv("ESP32_CAM_SLOT1_IP", "192.168.1.101")
SLOT2_IP = os.getenv("ESP32_CAM_SLOT2_IP", "192.168.1.102")

SLOT_IPS = {
    1: SLOT1_IP,
    2: SLOT2_IP,
}


def get_cam_url(slot: int) -> str:
    ip = SLOT_IPS.get(slot)
    if not ip:
        raise HTTPException(400, f"Invalid slot: {slot}")
    return f"http://{ip}/cam.mjpeg"


async def proxy_stream(slot: int):
    url = get_cam_url(slot)

    for attempt in range(3):
        if attempt > 0:
            await asyncio.sleep(1.5)  # ponytail: ESP32-CAM single-connection race retry
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                async with client.stream("GET", url) as resp:
                    if resp.status_code != 200:
                        raise HTTPException(502, f"Camera unavailable: HTTP {resp.status_code}")

                    async for chunk in resp.aiter_bytes():
                        yield chunk
                    return  # stream ended gracefully
            except httpx.ConnectError:
                continue  # retry
            except httpx.ReadTimeout:
                continue  # retry

    raise HTTPException(502, f"Camera at {url} is offline")
