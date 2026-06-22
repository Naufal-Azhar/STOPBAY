"""
STOPBAY v2.0 - SQLAlchemy Database Models
Tables: active_parking, parking_logs, users, hardware_status
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, DateTime, Enum as SQLEnum, Boolean, Text
)
from database import Base


class ActiveParking(Base):
    """Temporary parking sessions — data hidup selama mobil parkir."""

    __tablename__ = "active_parking"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    parking_space_id = Column(String(20), nullable=False, index=True)
    plate_number = Column(String(20), nullable=False)
    card_uid = Column(String(64), nullable=True, default=None)
    entry_time = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    status = Column(
        SQLEnum("WAITING", "ACTIVE", name="parking_status"),
        default="WAITING",
        nullable=False,
    )
    space_label = Column(String(20), nullable=True, default="SLOT_1")
    snapshot_url = Column(Text, nullable=True)            # base64 atau URL foto mobil
    user_name = Column(String(100), nullable=True)        # auto dari users table
    nik = Column(String(40), nullable=True)               # auto dari users table
    last_update = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    expiry_time = Column(DateTime, nullable=True)         # forced billing deadline (entry + 5 min)

    def to_dict(self):
        return {
            "id": self.id,
            "parking_space_id": self.parking_space_id,
            "plate_number": self.plate_number,
            "card_uid": self.card_uid,
            "entry_time": self.entry_time.isoformat() if self.entry_time else None,
            "status": self.status,
            "space_label": self.space_label,
            "snapshot_url": self.snapshot_url,
            "user_name": self.user_name,
            "nik": self.nik,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "expiry_time": self.expiry_time.isoformat() if self.expiry_time else None,
        }


class ParkingLog(Base):
    """Permanent history — moved from active_parking after exit/payment."""

    __tablename__ = "parking_logs"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    plate_number = Column(String(20), nullable=False)
    card_uid = Column(String(64), nullable=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    total_fare = Column(Integer, default=0)
    parking_space_id = Column(String(20), nullable=True)
    space_label = Column(String(20), nullable=True)
    user_name = Column(String(100), nullable=True)
    nik = Column(String(40), nullable=True)
    snapshot_url = Column(Text, nullable=True)
    payment_method = Column(String(30), default="DUMMY_BALANCE")
    balance_before = Column(Integer, nullable=True)
    balance_after = Column(Integer, nullable=True)
    forced_billing = Column(Boolean, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "plate_number": self.plate_number,
            "card_uid": self.card_uid,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_fare": self.total_fare,
            "parking_space_id": self.parking_space_id,
            "space_label": self.space_label,
            "user_name": self.user_name,
            "nik": self.nik,
            "snapshot_url": self.snapshot_url,
            "payment_method": self.payment_method,
            "balance_before": self.balance_before,
            "balance_after": self.balance_after,
            "forced_billing": self.forced_billing,
            "duration_hours": round(
                (self.end_time - self.start_time).total_seconds() / 3600.0, 2
            ) if self.start_time and self.end_time else 0,
        }


class User(Base):
    """User accounts — created automatically on first RFID tap."""

    __tablename__ = "users"

    card_uid = Column(String(64), primary_key=True, index=True)
    full_name = Column(String(100), nullable=True)
    nik = Column(String(40), nullable=True)
    email = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    balance = Column(Integer, default=100000)  # saldo default Rp 100.000
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "card_uid": self.card_uid,
            "full_name": self.full_name,
            "nik": self.nik,
            "email": self.email,
            "phone": self.phone,
            "balance": self.balance,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
        }


class HardwareStatus(Base):
    """Hardware health monitoring — heartbeat from ESP32 devices."""

    __tablename__ = "hardware_status"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    device_id = Column(String(50), unique=True, nullable=False)
    device_type = Column(String(30), nullable=False)        # MAIN_CONTROLLER, CAM, RFID, LCD, SERVO
    location = Column(String(50), nullable=True)
    is_online = Column(Boolean, default=True)
    last_heartbeat = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    extra_info = Column(Text, nullable=True)                # JSON extra info

    def to_dict(self):
        return {
            "id": self.id,
            "device_id": self.device_id,
            "device_type": self.device_type,
            "location": self.location,
            "is_online": self.is_online,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "extra_info": self.extra_info,
        }
