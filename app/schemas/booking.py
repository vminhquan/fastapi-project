from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from enum import Enum
from app.schemas.seat import SeatResponse

class BookingStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    
class BookingCreate(BaseModel):
    seat_id: int = Field(..., gt=0, description="ID của ghế muốn đặt")
    # Lưu ý: Không cần user_id ở đây vì user_id sẽ được trích xuất tự động từ Access Token của khách

class BookingResponse(BaseModel):
    id: int
    user_id: int
    
    # Lồng schema Seat vào để khách biết mình vừa đặt ghế nào, thuộc phim gì
    seat: SeatResponse 
    status: BookingStatus
    created_at: datetime
    expire_at: datetime
    
    model_config = ConfigDict(from_attributes=True)