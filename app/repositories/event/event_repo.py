from sqlalchemy.orm import Session
from app.models.booking import Event
from datetime import datetime

def create_event(db: Session, event_data: dict):
    """Lưu suất chiếu mới vào bảng events"""
    new_event = Event(**event_data)
    db.add(new_event)
    db.commit(new_event)
    db.refresh()
    
    return new_event

def check_time_conflict(db: Session, room_id:int, start_time: datetime, end_time: datetime):
    """Kiểm tra có trùng giờ chiếu trong 1 phòng không"""
    overlapping_event = db.query(Event).filter(
        Event.room_id == room_id,
        Event.start_time > start_time, # Phim cũ bắt đầu TRƯỚC KHI phim mới kết thúc
        Event.end_time < end_time      # Phim cũ kết thúc SAU KHI phim mới bắt đầu
    ).first()
    
    return overlapping_event

def bulk_create_seats(db: Session, seats: list):
    """Lưu 1 loạt danh sách ghế vào bảng seats cùng lúc (Bulk Insert)"""
    db.add_all(seats) # Gom 100 cái ghế lại
    db.commit()
