"""
STOPBAY v3.0 — Web Push Notification Service
VAPID key management + browser subscription storage + push trigger.
"""

import json
import os
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pywebpush import webpush, WebPushException

logger = logging.getLogger("push")

router = APIRouter(prefix="/api/push", tags=["push"])

# ponytail: in-memory subscription store (persist if >10k users)
_subscriptions: dict[str, dict] = {}

# VAPID keys — generate once with: py_vapid --gen
VAPID_PRIVKEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_CLAIMS = {"sub": "mailto:admin@stopbay.local"}


class SubscribeRequest(BaseModel):
    endpoint: str
    keys: dict


class PushPayload(BaseModel):
    card_uid: str | None = None
    title: str = "STOPBAY"
    body: str = "Parking update"


@router.post("/subscribe")
def subscribe(req: SubscribeRequest):
    """Store browser push subscription."""
    _subscriptions[req.endpoint] = {
        "endpoint": req.endpoint,
        "keys": req.keys,
    }
    return {"success": True, "message": "Subscribed"}


@router.post("/send")
def send_push(payload: PushPayload):
    """Send push notification to subscribed browsers."""
    if not VAPID_PRIVKEY:
        raise HTTPException(501, "VAPID keys not configured")

    data = json.dumps({"title": payload.title, "body": payload.body})
    delivered = 0
    errors = []

    for endpoint, sub in list(_subscriptions.items()):
        try:
            webpush(
                subscription_info=sub,
                data=data,
                vapid_private_key=VAPID_PRIVKEY,
                vapid_claims=VAPID_CLAIMS,
            )
            delivered += 1
        except WebPushException as e:
            logger.warning(f"Push failed: {e}")
            if e.response and e.response.status_code in (404, 410):
                del _subscriptions[endpoint]
            else:
                errors.append(str(e))

    return {
        "success": True,
        "delivered": delivered,
        "total": len(_subscriptions),
        "errors": errors,
    }
