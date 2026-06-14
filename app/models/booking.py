from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.time_utils import utc_now_naive
import enum
from sqlalchemy.dialects.postgresql import UUID
import uuid

class SeatStatus(enum.Enum):
    AVAILABLE = "available"
    HELD = "held"
    SOLD = "sold"

class BookingStatus(enum.Enum):
    HELD = "held"   # Đang giữ ghế
    CONFIRMED = "confirmed" # Đã thanh toán và xác nhận ghế
    EXPIRED = "expired"   # Hết thời gian giữ
    CANCELLED = "cancelled" # Người dùng/hệ thống hủy

class TicketStatus(enum.Enum):
    ISSUED = "issued"
    USED = "used"
    EXPIRED = "expired"
class Room(Base):
    __tablename__ = "rooms"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), unique=True, index=True)
    capacity = Column(Integer)

    # Quan hệ: Một phòng có nhiều suất chiếu
    events = relationship("Event", back_populates="room")

class Film(Base):
    __tablename__ = "films"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String(255), index=True, nullable=False) # Tên phim
    genre = Column(String(255), nullable=True)              # Thể loại phim
    duration = Column(Integer, nullable=False)              # Thời lượng phim (Tính bằng phút)
    description = Column(Text, nullable=True)               # Mô tả phim
    release_date = Column(Date, nullable=True)              # Ngày công chiếu
    poster_url = Column(String(500), nullable=True)         # Link ảnh poster 
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    
    # Mối quan hệ 1-N: 1 Phim có nhiều Suất chiếu (Event)
    events = relationship("Event", back_populates="film")

class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_room_start_time", "room_id", "start_time"),
        Index("ix_events_film_start_time", "film_id", "start_time"),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Khóa ngoại liên kết tới Phim và Phòng
    film_id = Column(UUID(as_uuid=True), ForeignKey("films.id", ondelete="CASCADE"), nullable=False, index=True)
    room_id = Column(UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False) 
    price = Column(Integer, nullable=False)
    
    # Quan hệ ngược lại
    film = relationship("Film", back_populates="events")
    room = relationship("Room", back_populates="events")
    seats = relationship("Seat", back_populates="event", cascade="all, delete")
    bookings = relationship("Booking", back_populates="event")
    
class Seat(Base):
    __tablename__ = "seats"
    __table_args__ = (
        UniqueConstraint("event_id", "seat_code"),
        Index("ix_seats_event_status", "event_id", "status"),
    )
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    seat_code = Column(String, nullable=False)
    status = Column(Enum(SeatStatus), default=SeatStatus.AVAILABLE, nullable=False)

    event = relationship("Event", back_populates="seats")
    
class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        Index("ix_bookings_status_created_at", "status", "created_at"),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(
    Enum(BookingStatus),
    nullable=False,
    default=BookingStatus.HELD,
    )

    hold_expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime,
    default=utc_now_naive,
    onupdate=utc_now_naive,
    nullable=False,)

    confirmed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)

    # Quan hệ
    booking_items = relationship("BookingItem", back_populates="booking", cascade="all, delete")
    order = relationship(
    "Order",
    back_populates="booking",
    uselist=False,
    )
    event = relationship("Event", back_populates="bookings")

class BookingItem(Base):
    __tablename__ = "booking_items"
    __table_args__ = (
        UniqueConstraint(
            "booking_id",
            "seat_id"
        ),
    )
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id = Column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id"),
        nullable=False,
    )
    seat_id = Column(
        UUID(as_uuid=True),
        ForeignKey("seats.id"),
        nullable=False,
    )
    unit_price = Column(Integer, nullable=False)
    created_at = Column(
        DateTime,
        default=utc_now_naive,
        nullable=False,
    )
    booking = relationship("Booking", back_populates="booking_items")
    seat = relationship("Seat")
    ticket = relationship(
        "Ticket",
        back_populates="booking_item",
        uselist=False,
    )

    @property
    def seat_code(self):
        return self.seat.seat_code if self.seat else ""

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("booking_items.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    qr_token = Column(String(255), nullable=False, unique=True)
    issued_at = Column(DateTime, nullable=False, default=utc_now_naive)
    used_at = Column(DateTime, nullable=True)
    status = Column(Enum(TicketStatus), nullable=False, default=TicketStatus.ISSUED)

    booking_item = relationship(
        "BookingItem",
        back_populates="ticket"
    )
