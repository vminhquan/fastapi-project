from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from uuid import UUID

class SeatStatus(str, Enum):
    AVAILABLE = "available"
    HELD = "held"
    SOLD = "sold"
    
# Ghi chú: Không có SeatCreate vì Seat được hệ thống tự động sinh ra khi tạo Event
class SeatResponse(BaseModel):
    id: UUID
    event_id: UUID
    seat_code: str = Field(..., description="Mã ghế, VD: A1, B12")
    status: SeatStatus
    
    model_config = ConfigDict(from_attributes=True)