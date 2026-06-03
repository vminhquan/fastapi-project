from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from enum import Enum
from app.schemas.seat import SeatResponse

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import List
from enum import Enum
# from app.schemas.seat import SeatResponse (Không cần cái này ở đây nữa, ta sẽ dùng TicketResponse)

class BookingStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

# ========================================================
# 1. ĐẦU VÀO: Mua NHIỀU ghế trong 1 lần
# ========================================================
class BookingCreate(BaseModel):
    event_id: int = Field(..., gt=0, description="ID của suất chiếu")
    
    # Bắt buộc là List (mảng) để mua nhiều ghế, min_length=1 để chặn mảng rỗng
    seat_ids: List[int] = Field(..., min_length=1, description="Danh sách ID các ghế muốn đặt")
    
    # user_id tự lấy từ Token (Chuẩn!)


# ========================================================
# 2. ĐẦU RA: Trả về 1 Hóa đơn chứa nhiều vé bên trong
# ========================================================

# Thêm 1 schema nhỏ gọn này để hiển thị chi tiết từng vé
class TicketResponse(BaseModel):
    id: int
    seat_id: int
    price: float
    model_config = ConfigDict(from_attributes=True)

class BookingResponse(BaseModel):
    id: int
    user_id: int
    event_id: int
    total_price: float
    status: BookingStatus
    created_at: datetime
    expire_at: datetime
    
    # 👈 Mấu chốt: Lồng danh sách vé vào bên trong Hóa đơn
    tickets: List[TicketResponse] 
    
    model_config = ConfigDict(from_attributes=True)