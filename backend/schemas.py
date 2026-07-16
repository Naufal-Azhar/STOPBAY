"""
STOPBAY v2.0 - Pydantic Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional


# ============================================================
# Request Schemas
# ============================================================

class SpaceOccupiedRequest(BaseModel):
    plate_number: str = Field(..., min_length=1, max_length=20)
    parking_space_id: str = Field(default="SPACE-01", max_length=20)
    snapshot_url: Optional[str] = Field(default=None)
    space_label: Optional[str] = Field(default="SLOT_1")


class RegisterCardRequest(BaseModel):
    card_uid: str = Field(..., min_length=1, max_length=64)
    parking_space_id: str = Field(default="SPACE-01", max_length=20)
    plate_number: Optional[str] = Field(default=None, max_length=20)
    space_label: Optional[str] = Field(default=None)


class ForcedBillingRequest(BaseModel):
    plate_number: str = Field(..., min_length=1, max_length=20)
    parking_space_id: str = Field(default="SPACE-01", max_length=20)


class ExitRequest(BaseModel):
    card_uid: str = Field(..., min_length=1, max_length=64)


class HeartbeatRequest(BaseModel):
    device_id: str = Field(..., max_length=50)
    device_type: str = Field(default="MAIN_CONTROLLER", max_length=30)
    location: Optional[str] = Field(default=None, max_length=50)
    slots_active: Optional[int] = None
    rfid_slot1_ok: Optional[bool] = None
    cam1_ok: Optional[bool] = None
    lcd1_ok: Optional[bool] = None
    servo_ok: Optional[bool] = None


class TopupRequest(BaseModel):
    amount: int = Field(..., gt=0, le=10000000)  # max Rp 10.000.000


# ============================================================
# Response Schemas
# ============================================================

class BaseResponse(BaseModel):
    success: bool
    message: str


class SpaceOccupiedResponse(BaseResponse):
    id: Optional[int] = None
    expiry_time: Optional[str] = None
    grace_period_minutes: int = 5


class RegisterCardResponse(BaseResponse):
    fare_per_hour: int = 2000
    entry_time: Optional[str] = None
    user_name: Optional[str] = None
    balance: Optional[int] = None


class ForcedBillingResponse(BaseResponse):
    total_fare: int = 2000
    plate_number: Optional[str] = None


class ParkingStatusData(BaseModel):
    plate_number: str
    parking_space_id: str
    space_label: Optional[str] = None
    card_uid: Optional[str] = None
    user_name: Optional[str] = None
    entry_time: Optional[str] = None
    duration_minutes: float = 0
    duration_seconds: int = 0
    current_fare: int = 0
    status: str = "WAITING"
    fare_per_hour: int = 2000


class ParkingStatusResponse(BaseResponse):
    data: Optional[ParkingStatusData] = None


class ExitResponse(BaseResponse):
    plate_number: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_hours: Optional[float] = None
    total_fare: Optional[int] = None
    balance_before: Optional[int] = None
    balance_after: Optional[int] = None


class HeartbeatResponse(BaseModel):
    success: bool = True
    devices_online: int = 0
