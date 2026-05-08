from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Float
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum

class SeatStatus(enum.Enum):
    AVAILABLE = "available"
    HELD = "held"
    SOLD = "sold"

class BookingStatus(enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class Room(Base):
    __tablename__ = "rooms"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    capacity = Column(Integer)

    # Quan hệ: Một phòng có nhiều suất chiếu
    events = relationship("Event", back_populates="room")

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    movie_title = Column(String, index=True)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    price = Column(Float)
    room_id = Column(Integer, ForeignKey("rooms.id"))

    room = relationship("Room", back_populates="events")
    # Quan hệ: Một suất chiếu có nhiều ghế (inventory)
    seats = relationship("Seat", back_populates="event")

class Seat(Base):
    __tablename__ = "seats"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"))
    seat_code = Column(String) # Ví dụ: "A1"
    status = Column(Enum(SeatStatus), default=SeatStatus.AVAILABLE)

    event = relationship("Event", back_populates="seats")

class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    seat_id = Column(Integer, ForeignKey("seats.id"))
    status = Column(Enum(BookingStatus), default=BookingStatus.PENDING)
    created_at = Column(DateTime)
    expire_at = Column(DateTime)