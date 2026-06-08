from uuid import UUID
import re

from sqlalchemy.orm import Session
from app.models.booking import Booking, Event, Seat
from datetime import datetime

def create_event(db: Session, event_data: dict):
    """Lưu suất chiếu mới vào bảng events"""
    new_event = Event(**event_data)
    db.add(new_event)
    db.commit()            
    db.refresh(new_event)
    
    return new_event

def get_all_events(db: Session, skip: int = 0, limit: int = 100):
    """Lấy tất cả danh sách suất chiếu"""
    return db.query(Event).order_by(Event.id).offset(skip).limit(limit).all()

def get_event_by_id(db: Session, event_id: UUID):
    """Lấy suất chiếu theo id"""
    return db.query(Event).filter(Event.id == event_id).first()

def has_bookings(db: Session, event_id: UUID):
    """Kiểm tra suất chiếu đã phát sinh booking chưa"""
    return db.query(Booking.id).filter(Booking.event_id == event_id).first() is not None

def update_event(db: Session, event_id: UUID, event_data: dict):
    """Cập nhật thông tin của suất chiếu theo id"""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return None
    
    # Cập nhật các field
    for key, value in event_data.items():
        if hasattr(event, key) and value is not None:
            setattr(event, key, value)
    
    db.commit()
    db.refresh(event)
    
    return event

def get_seats_by_event_id(db: Session, event_id: UUID):
    """Lấy sơ đồ ghế theo id suất chiếu"""
    seats = db.query(Seat).filter(Seat.event_id == event_id).all()

    def seat_sort_key(seat: Seat):
        match = re.fullmatch(r"([A-Za-z]+)(\d+)", seat.seat_code or "")
        if not match:
            return (seat.seat_code or "", 0)
        return (match.group(1).upper(), int(match.group(2)))

    return sorted(seats, key=seat_sort_key)

def delete_event(db: Session, event_id: UUID):
    """Xoá suất chiếu"""
    event = db.query(Event).filter(Event.id == event_id).first()
    
    if not event:
        return False
    
    db.delete(event)
    db.commit()
    
    return True 

def check_time_conflict(db: Session,
                        room_id:UUID,
                        start_time: datetime,
                        end_time: datetime,
                        exclude_event_id: UUID = None
                        ):
    """Kiểm tra có trùng giờ chiếu trong 1 phòng không"""
    query = db.query(Event).filter(
        Event.room_id == room_id,
        Event.start_time < end_time, # Phim cũ bắt đầu TRƯỚC KHI phim mới kết thúc
        Event.end_time > start_time  # Phim cũ kết thúc SAU KHI phim mới bắt đầu
    )
    # Nếu đang Update, loại trừ chính suất chiếu này ra khỏi vòng quét
    if exclude_event_id is not None:
        query = query.filter(Event.id != exclude_event_id)
        
    return query.first()
    

def bulk_create_seats(db: Session, seats: list):
    """Lưu 1 loạt danh sách ghế vào bảng seats cùng lúc (Bulk Insert)"""
    db.add_all(seats) # Gom 100 cái ghế lại
    db.commit()
