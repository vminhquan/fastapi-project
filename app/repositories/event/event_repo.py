from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.booking import Event,Film
from app.schemas.event import EventCreate
from datetime import timedelta

def create_event_logic(db: Session, event_in: EventCreate):
    # lấy thông tin film
    film = db.query(Film).filter(Film.id == event_in.film_id).first()
    if not film:
        raise HTTPException(status_code=404, detail="Phim không tồn tại!")
    # tính thời gian kêt thúc:
    # Công thức: start_time + thời lượng film + 15 phút dọn phòng
    calculated_end_time = event_in.start_time + timedelta(minutes=film.duration) + timedelta(minutes=film.duration)
    
    new_event_data = {
        "film_id": event_in.film_id,
        "room_id": event_in.room_id,
        "start_time": event_in.start_time,
        "end_time": calculated_end_time,
        "price": event_in.price
    }
    
    db.commit(new_event_data)
    db.refresh()
    
    return new_event_data