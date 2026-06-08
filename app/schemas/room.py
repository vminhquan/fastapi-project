from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID

class RoomBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=50, description="Tên phòng chiếu")
    capacity: int = Field(..., gt=0, le=100, description="Sức chứa tối đa của phòng")

class RoomCreate(RoomBase):
    pass

class RoomUpdate(RoomBase):
    pass
class RoomResponse(RoomBase):
    id: UUID
    
    # Pydantic V2: Chuyển đổi Object của SQLAlchemy thành JSON
    model_config = ConfigDict(from_attributes=True)
    
