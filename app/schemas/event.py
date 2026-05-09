from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from app.schemas.room import RoomResponse

class EventCreate(BaseModel):
    film_id: int = Field(..., description="ID của bộ phim")
    room_id: int = Field(..., description="ID của phòng chiếu")
    start_time: datetime = Field(..., description="Giờ bắt đầu chiếu")
    price: float = Field(..., gt=0, description="Giá vé (phải lớn hơn 0)")
class EventResponse(BaseModel):
    id: int
    film_id: int
    room_id: int
    start_time: datetime
    end_time: datetime
    price: float
    
    model_config = ConfigDict(from_attributes=True)