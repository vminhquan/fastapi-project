from sqlalchemy.orm import Session
from app.models.booking import Room
from app.schemas.room import RoomCreate

def get_all_rooms(db: Session, skip: int = 0, limit: int = 100):
    """Lấy tất cả danh sách phòng"""
    return db.query(Room).order_by(Room.id).offset(skip).limit(limit).all()

def get_room_by_id(db: Session, room_id: int):
    """Lấy phòng theo id phòng"""
    return db.query(Room).filter(Room.id == room_id).first()

def get_room_by_name(db: Session, room_name: str):
    """Lấy phòng theo tên phòng"""
    return db.query(Room).filter(Room.name == room_name).first()

def create_room(db: Session, room_in: RoomCreate):
    """Tạo mới phòng"""
    new_room = Room(name = room_in.name, capacity = room_in.capacity)
    db.add(new_room)
    db.commit()
    db.refresh(new_room)
    
    return new_room

def update_room(db: Session, room_id: int, room_data: dict):
    """Cập nhật thông tin của phòng theo id"""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        return None
    
    # Cập nhật các field
    for key, value in room_data.items():
        if hasattr(room, key) and value is not None:
            setattr(room, key, value)
    
    db.commit()
    db.refresh(room)
    
    return room

def delete_room(db: Session, room_id: int):
    """Xoá phòng"""
    room = db.query(Room).filter(Room.id == room_id).first()
    
    if not room:
        return False
    
    db.delete(room)
    db.commit()
    
    return True
    