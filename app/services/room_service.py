from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.schemas.room import RoomCreate
from app.repositories.room import room_repo

def create_new_room(db: Session, room_in: RoomCreate):
    """Logic Tạo Phòng Mới"""
    # 1. Kiểm tra xem tên phòng đã tồn tại chưa
    existing_room = room_repo.get_room_by_name(db, name=room_in.name)
    if existing_room:
        raise HTTPException(
            status_code=400, 
            detail=f"Phòng chiếu mang tên '{room_in.name}' đã tồn tại trong hệ thống!"
        )
    
    # 2. Hợp lệ thì gọi repo tạo mới
    return room_repo.create_room(db, room_in)

def get_list_rooms(db: Session, skip: int = 0, limit: int = 100):
    """Logic Lấy Danh Sách Phòng"""
    return room_repo.get_all_rooms(db, skip=skip, limit=limit)

def get_room_detail(db: Session, room_id: int):
    """Logic Lấy Chi Tiết 1 Phòng"""
    room = room_repo.get_room_by_id(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Không tìm thấy phòng chiếu này!")
    return room

def update_room_logic(db: Session, room_id: int):
    """Logic cập nhật Phòng"""
    room = room_repo.update_room(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Không tìm thấy phòng chiếu này!")
    
    return room

def delete_room_logic(db: Session, room_id: int):
    """Logic Xóa Phòng - Kèm chốt chặn an toàn"""
    room = room_repo.get_room_by_id(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Không tìm thấy phòng chiếu này!")
    
    # CHỐT CHẶN BẢO MẬT: Không cho xóa phòng nếu đang có suất chiếu (Event) nằm trong đó
    # SQLAlchemy relationship cho phép gọi room.events để lấy các suất chiếu liên kết
    if room.events:
        raise HTTPException(
            status_code=400, 
            detail="Không thể xóa! Phòng này đang có lịch chiếu phim. Vui lòng xóa suất chiếu trước."
        )
        
    return room_repo.delete_room(db, room)