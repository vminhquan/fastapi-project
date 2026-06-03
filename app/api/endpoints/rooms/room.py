from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.security import RoleChecker 
from app.schemas.room import RoomCreate, RoomResponse,RoomUpdate
from app.services import room_service

router = APIRouter()
admin_only = RoleChecker(["admin"])

@router.post("/", response_model=RoomResponse, dependencies=[Depends(admin_only)])
def create_room(room_in: RoomCreate, db: Session = Depends(get_db)):
    """[ADMIN] Tạo phòng chiếu mới"""
    return room_service.create_new_room(db, room_in)

@router.put("/{room_id}", dependencies=[Depends(admin_only)])
def update_room(room_id: int, room_in: RoomUpdate,db: Session = Depends(get_db)):
    """[ADMIN] Cập nhật phòng chiếu"""
    return room_service.update_room_logic(db, room_id, room_in)

@router.delete("/{room_id}", dependencies=[Depends(admin_only)])
def delete_room(room_id: int, db: Session = Depends(get_db)):
    """[ADMIN] Xóa phòng chiếu"""
    room_service.delete_room_logic(db, room_id)
    return {"message": "Đã xóa phòng chiếu thành công!"}

@router.get("/", response_model=List[RoomResponse])
def read_all_rooms(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """[PUBLIC] Lấy danh sách phòng (Không cần đăng nhập cũng xem được)"""
    return room_service.get_list_rooms(db, skip=skip, limit=limit)

@router.get("/{room_id}", response_model=RoomResponse)
def read_room_detail(room_id: int, db: Session = Depends(get_db)):
    """[PUBLIC] Xem chi tiết 1 phòng"""
    return room_service.get_room_detail(db, room_id)