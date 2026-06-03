from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

# Import Database và các hàm Dependency của bạn
from app.core.database import get_db
from app.schemas import booking as booking_schema
from app.services import booking_service

# Giả định bạn có file dependency chuyên xử lý Auth (giải mã token)
from app.core.security import any_user, admin_only
from app.models.user import User # Model User

router = APIRouter()

@router.post("/", response_model=booking_schema.BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    booking_in: booking_schema.BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(any_user)
):
    """
    Tạo đơn hàng đặt vé mới (Giữ ghế 5 phút)
    """
    return booking_service.create_booking_logic(
        db=db, 
        booking_in=booking_in, 
        current_user_id=current_user.id
    )

@router.get("/my-tickets", response_model=List[booking_schema.BookingResponse])
@router.get("/tickets", response_model=List[booking_schema.BookingResponse])
def get_my_bookings(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(any_user) # Bắt buộc đăng nhập
):
    """
    Lấy danh sách lịch sử đặt vé của User đang đăng nhập
    """
    return booking_service.get_my_bookings(
        db=db, 
        current_user_id=current_user.id,
        skip=skip,
        limit=limit
    )

@router.get("/admin/all-tickets", response_model=List[booking_schema.BookingResponse])
def get_all_bookings_for_admin(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only) 
):
    """
    [DÀNH CHO ADMIN] Lấy danh sách toàn bộ hóa đơn của hệ thống để thống kê doanh thu
    """
    return booking_service.get_all_bookings_logic(db, skip=skip, limit=limit)

@router.get("/{booking_id}", response_model=booking_schema.BookingResponse)
def get_booking_detail(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(any_user) # Bắt buộc đăng nhập
):
    """
    Lấy chi tiết 1 đơn hàng (Dùng để hiển thị QR Code ở Frontend)
    - Có chốt chặn: Chỉ User sở hữu vé mới được xem
    """
    return booking_service.get_booking_detail(
        db=db, 
        booking_id=booking_id, 
        current_user_id=current_user.id
    )

@router.put("/{booking_id}/pay", response_model=booking_schema.BookingResponse)
def confirm_payment(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(any_user) 
):
    """
    Xác nhận thanh toán đơn hàng (Chuyển ghế từ HELD -> SOLD)
    - Trong thực tế, API này có thể được gọi bởi Webhook của VNPay/MoMo
    """
    return booking_service.confirm_payment_logic(
        db=db, 
        booking_id=booking_id, 
        current_user_id=current_user.id
    )

@router.delete("/{booking_id}")
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(any_user) 
):
    """
    Khách hàng chủ động hủy vé khi đang chờ thanh toán (PENDING)
    """
    return booking_service.cancel_booking_logic(
        db=db, 
        booking_id=booking_id, 
        current_user_id=current_user.id
    )
