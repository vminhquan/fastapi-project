from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.event import EventResponse,EventCreate
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
    new_event = event_service.create_new_event(db, event_in)
    return new_event