from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Float, Text, Date
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
    name = Column(String(255), unique=True, index=True)
    capacity = Column(Integer)

    # Quan hệ: Một phòng có nhiều suất chiếu
    events = relationship("Event", back_populates="room")

class Film(Base):
    __tablename__ = "films"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True, nullable=False) # Tên phim
    duration = Column(Integer, nullable=False)              # Thời lượng phim (Tính bằng phút)
    description = Column(Text, nullable=True)               # Mô tả phim
    release_date = Column(Date, nullable=True)              # Ngày công chiếu
    poster_url = Column(String(500), nullable=True)         # Link ảnh poster 
    
    # Mối quan hệ 1-N: 1 Phim có nhiều Suất chiếu (Event)
    events = relationship("Event", back_populates="film")
class Event(Base):
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Khóa ngoại liên kết tới Phim và Phòng
    film_id = Column(Integer, ForeignKey("films.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False) 
    price = Column(Float, nullable=False)
    
    # Quan hệ ngược lại
    film = relationship("Film", back_populates="events")
    room = relationship("Room", back_populates="events")
    seats = relationship("Seat", back_populates="event", cascade="all, delete")
    bookings = relationship("Booking", back_populates="event")
    
class Seat(Base):
    __tablename__ = "seats"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    seat_code = Column(String, nullable=False)
    status = Column(Enum(SeatStatus), default=SeatStatus.AVAILABLE)

    event = relationship("Event", back_populates="seats")
    
class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    total_price = Column(Float, nullable=False) 
    
    status = Column(Enum(BookingStatus), default=BookingStatus.PENDING)
    created_at = Column(DateTime, default=datetime.now)
    expire_at = Column(DateTime) # Hạn chót để thanh toán (VD: 5 phút giữ ghế)

    # Quan hệ
    tickets = relationship("Ticket", back_populates="booking", cascade="all, delete")
    user = relationship("User", back_populates="bookings")
    event = relationship("Event", back_populates="bookings")

class Ticket(Base):
    __tablename__ = "tickets"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    seat_id = Column(Integer, ForeignKey("seats.id"), nullable=False)
    
    # Giá của riêng cái ghế này tại thời điểm mua
    price = Column(Float, nullable=False) 

    # Quan hệ
    booking = relationship("Booking", back_populates="tickets")
    seat = relationship("Seat")
 