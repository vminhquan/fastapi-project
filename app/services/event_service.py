from sqlalchemy.orm import Session
from app.repositories.event import event_repo
from app.models.booking import Film, Room, Seat
from app.schemas.event import EventCreate
from fastapi import HTTPException
from datetime import timedelta

def create_new_event(db: Session, event_in: EventCreate):
    # Kiểm tra phim có tồn tại không
    film = db.query(Film).filter(Film.id == event_in.film_id).first()
    if not Film:
        raise HTTPException(
            status_code=404,
            detail="Bộ phim không tồn tại!"
        )
    
    # Kiểm tra phòng có tồn tại không
    room = db.query(Room).filter(Room.id == event_in.room_id).first()
    if not Room:
        raise HTTPException(
            status_code=404,
            detail="Phòng chiếu không tồn tại!"
        )
    
    # Tự động tính Giờ kết thúc = Bắt đầu + Thời lượng phim + 15p dọn rạp
    calculated_end_time = event_in.start_time + timedelta(minutes=film.duration) + timedelta(minutes=15)
    
    # Kiểm tra trùng giờ
    time_conflict = event_repo.check_time_conflict(db, room.id, event_in.start_time, calculated_end_time)
    if time_conflict:
        raise HTTPException(
            status_code=400, 
            detail=f"Phòng này đã có lịch chiếu từ {time_conflict.start_time.strftime('%H:%M')} đến {time_conflict.end_time.strftime('%H:%M')}."
        )
    
    # Đóng gói và lưu db   
    event_data = {
        "film_id": event_in.film_id,
        "room_id": event_in.room_id,
        "start_time": event_in.start_time,
        "end_time": calculated_end_time, # Dùng giờ hệ thống tự tính
        "price": event_in.price
    }
    new_event = event_repo.create_event(db, event_data)
    
    # 6. TỰ ĐỘNG SINH GHẾ NGỒI DỰA VÀO SỨC CHỨA CỦA PHÒNG
    seats_to_create = []
    rows = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    seats_per_row = 10 # Cố định mỗi hàng 10 ghế
    
    for i in range(room.capacity):
        # Thuật toán tính mã ghế (Ví dụ sức chứa 50 -> A1 đến A10, B1 đến B10... E10)
        row_letter = rows[i // seats_per_row]
        seat_num = (i % seats_per_row) + 1
        seat_code = f"{row_letter}{seat_num}"
        
        # Gom các Object Seat lại (Mặc định status đã là AVAILABLE trong model)
        seats_to_create.append(Seat(event_id=new_event.id, seat_code=seat_code))
        
    # Lưu một phát toàn bộ ghế xuống Database
    event_repo.bulk_create_seats(db, seats_to_create)
    
    return new_event