from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import UUID


class EventCreate(BaseModel):
    film_id: UUID = Field(..., description="ID của bộ phim")
    room_id: UUID = Field(..., description="ID của phòng chiếu")
    start_time: datetime = Field(..., description="Giờ bắt đầu chiếu")
    price: float = Field(..., gt=0, description="Giá vé (phải lớn hơn 0)")

class EventUpdate(EventCreate):
    pass
class EventResponse(BaseModel):
    id: UUID
    film_id: UUID
    room_id: UUID
    start_time: datetime
    end_time: datetime
    price: float
    
    model_config = ConfigDict(from_attributes=True) # dòng này để SQLAlchemy map được với Pydantic


class EventScheduleFilm(BaseModel):
    id: UUID
    title: str
    genre: str | None = None
    duration: int
    poster_url: str | None = None


class EventScheduleRoom(BaseModel):
    id: UUID
    name: str
    capacity: int


class EventScheduleResponse(EventResponse):
    available_seats: int
    total_seats: int
    film: EventScheduleFilm
    room: EventScheduleRoom
