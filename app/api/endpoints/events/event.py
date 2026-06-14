from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.event import (
    EventCreate,
    EventResponse,
    EventScheduleResponse,
    EventUpdate,
)
from app.services import event_service
from app.core.security import RoleChecker

router = APIRouter()
admin_only = RoleChecker(["admin"])

@router.post("/", response_model=EventResponse, dependencies=[Depends(admin_only)])
def create_event_endpoint(
    event_in: EventCreate, 
    db: Session = Depends(get_db)
):
    """
    API Tạo suất chiếu mới (Admin). 
    - Sẽ tự động tính toán giờ kết thúc dựa vào thời lượng phim.
    - Sẽ tự động sinh danh sách ghế dựa vào sức chứa của phòng.
    """
    return event_service.create_new_event(db, event_in)
     
@router.get("/", response_model=List[EventResponse])
def read_all_events(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """Lấy danh sách tất cả suất chiếu"""
    events = event_service.get_list_events(db, skip=skip, limit=limit)
    return events


@router.get("/schedule", response_model=List[EventScheduleResponse])
def read_event_schedule(
    film_id: UUID | None = None,
    room_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Lấy lịch chiếu kèm phim, phòng và số ghế trống."""
    return event_service.get_schedule(
        db,
        film_id=film_id,
        room_id=room_id,
        skip=skip,
        limit=limit,
    )


@router.get("/{event_id}", response_model=EventResponse)
@router.get("/event/{event_id}", response_model=EventResponse)
def read_event_detail(
    event_id: UUID,
    db: Session = Depends(get_db)
):
    """Lấy thông tin chi tiết của 1 suất chiếu"""
    return event_service.get_event_detail(db, event_id)

@router.get("/{event_id}/seats")
def read_event_seats(
    event_id: UUID,
    db: Session = Depends(get_db)
):
    """Lấy sơ đồ toàn bộ ghế ngồi của suất chiếu này để Frontend vẽ rạp"""
    return event_service.get_event_seats_logic(db, event_id)

@router.put("/{event_id}", response_model=EventResponse, dependencies=[Depends(admin_only)])
def update_event(
    event_id: UUID,
    event_in: EventUpdate, 
    db: Session = Depends(get_db)
):
    """Cập nhật suất chiếu (Có tự động check trùng lịch và tính lại giờ)"""
    return event_service.update_event_logic(db, event_id, event_in)

@router.delete("/{event_id}", dependencies=[Depends(admin_only)])
def delete_event(
    event_id: UUID,
    db: Session = Depends(get_db)
):
    """Xoá suất chiếu (Chặn xoá nếu phim đang/đã chiếu)"""
    success = event_service.delete_event_logic(db, event_id)
    if success:
        return {"message": "Xoá suất chiếu thành công!"}
    raise HTTPException(status_code=400, detail="Xoá suất chiếu thất bại!")
