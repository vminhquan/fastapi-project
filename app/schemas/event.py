from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from app.schemas.room import RoomResponse

class EventBase(BaseModel):
    movie_title: str = Field(..., min_length=1, max_length=100)
    start_time: datetime
    end_time: datetime
    price: float = Field(..., ge=0, description="Giá vé không được âm")

class EventCreate(EventBase):
    room_id: int = Field(..., gt=0, description="ID của phòng chiếu")

class EventResponse(EventBase):
    id: int
    # Lồng (Nest) schema Room vào trong Event để API trả về đầy đủ thông tin phòng
    room: RoomResponse 
    
    model_config = ConfigDict(from_attributes=True)