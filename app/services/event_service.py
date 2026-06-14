from sqlalchemy.orm import Session
from app.repositories.event import event_repo
from app.models.booking import Film, Room, Seat
from app.repositories.film import film_repo
from app.repositories.room import room_repo
from app.schemas.event import EventCreate,EventUpdate
from app.services import booking_service
from app.core.time_utils import app_now_naive
from fastapi import HTTPException
from datetime import datetime, timedelta
from uuid import UUID

def create_new_event(db: Session, event_in: EventCreate):
    """Logic tạo suất chiếu"""
    # Kiểm tra phim có tồn tại không
    film = db.query(Film).filter(Film.id == event_in.film_id).first()
    if not film:
        raise HTTPException(
            status_code=404,
            detail="Bộ phim không tồn tại!"
        )
    
    # Kiểm tra phòng có tồn tại không
    room = db.query(Room).filter(Room.id == event_in.room_id).first()
    if not room:
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

def get_list_events(db: Session, skip: int = 0, limit: int = 100):
    """Logic lấy danh sách suất chiếu"""
    return event_repo.get_all_events(db, skip=skip, limit=limit)


def get_schedule(
    db: Session,
    *,
    film_id: UUID | None = None,
    room_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
):
    """Lấy lịch chiếu công khai bằng một truy vấn tổng hợp."""
    booking_service.cleanup_expired_bookings_logic(db, limit=500)
    return event_repo.get_event_schedule(
        db,
        film_id=film_id,
        room_id=room_id,
        starts_after=app_now_naive(),
        skip=skip,
        limit=min(max(limit, 1), 500),
    )


def get_event_detail(db: Session, event_id: UUID):
    """Logic lấy suất chiếu theo event"""
    event = event_repo.get_event_by_id(db, event_id)

    if not event:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy suất chiếu này!"
        )
    return event

def get_event_seats_logic(db: Session, event_id: UUID):
    """Logic lấy sơ đồ ghế của suất chiếu"""
    booking_service.cleanup_expired_bookings_logic(db, limit=500)

    # 1. Kiểm tra xem suất chiếu này có thật không
    event = event_repo.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy suất chiếu này!"
        )
    
    # 2. Gọi Repo lấy sơ đồ ghế đã được sắp xếp chuẩn
    return event_repo.get_seats_by_event_id(db, event_id)

def update_event_logic(db: Session, event_id: UUID, event_in: EventUpdate):
    """Logic cập nhật suất chiếu"""
    event = event_repo.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy suất chiếu này!"
        )
    
    event_data = {}

    # 1. Nhóm dữ liệu ảnh hưởng đến Thời gian (Phim, Phòng, Giờ bắt đầu)
    # Vì Schema Update bắt buộc gửi các trường này, ta so sánh xem nó có khác dữ liệu cũ không
    if (event_in.film_id != event.film_id) or (event_in.room_id != event.room_id) or (event_in.start_time != event.start_time):
        
        film = film_repo.get_film_by_id(db, event_in.film_id)
        if not film:
            raise HTTPException(status_code=404, detail="Không tìm thấy bộ phim này!")
        
        room = room_repo.get_room_by_id(db, event_in.room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Phòng chiếu không tồn tại!")

        # Tính lại giờ kết thúc mới (Cộng thời lượng phim + 15 phút dọn rạp)
        new_end_time = event_in.start_time + timedelta(minutes=film.duration + 15)

        conflict = event_repo.check_time_conflict(
            db=db, 
            room_id=event_in.room_id, 
            start_time=event_in.start_time, 
            end_time=new_end_time,
            exclude_event_id=event.id
        )
        if conflict:
            raise HTTPException(
                status_code=400, 
                detail="Lỗi: Thời gian này đã bị trùng với một suất chiếu khác trong phòng!"
            )

        # Lưu lại các thông tin thời gian mới để chuẩn bị update
        event_data["film_id"] = event_in.film_id
        event_data["room_id"] = event_in.room_id
        event_data["start_time"] = event_in.start_time
        event_data["end_time"] = new_end_time

    # 2. Xử lý đổi Giá vé (Độc lập với thời gian)
    if event_in.price != event.price:
        event_data["price"] = event_in.price

    # 3. Gọi tầng Repo để thực thi Update nếu có sự thay đổi
    if event_data:
        updated_event = event_repo.update_event(db, event_id, event_data)
        return updated_event
        
    # Nếu Admin bấm "Lưu" nhưng không sửa chữ nào, trả về event cũ luôn (đỡ tốn công gọi DB)
    return event

def delete_event_logic(db: Session, event_id: UUID):
    """Logic xoá suất chiếu"""
    event = event_repo.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy suất chiếu này!"
        )
    
    # Lấy thời gian hiện tại của hệ thống
    now = datetime.now()
    
    # Nếu giờ bắt đầu của suất chiếu nhỏ hơn hoặc bằng giờ hiện tại
    # -> Tức là phim đang chiếu, hoặc đã chiếu xong từ đời nào rồi
    if event.start_time <= now:
        raise HTTPException(
            status_code=400,
            detail="Không thể xoá! Suất chiếu này đang diễn ra hoặc đã kết thúc."
        )

    if event_repo.has_bookings(db, event_id):
        raise HTTPException(
            status_code=400,
            detail="Không thể xoá! Suất chiếu này đã có booking/vé phát sinh, cần giữ lại để bảo vệ lịch sử giao dịch."
        )
    
    return event_repo.delete_event(db, event_id)
