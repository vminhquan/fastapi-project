from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import admin_only, any_user
from app.models.user import User
from app.schemas import booking as booking_schema
from app.services import booking_service


router = APIRouter()


# ========================================================
# 1. CREATE: GIỮ GHẾ VÀ TẠO ORDER
# ========================================================
@router.post(
    "/",
    response_model=booking_schema.BookingCheckoutResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_booking(
    booking_in: booking_schema.BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(any_user),
):
    """
    Giữ nhiều ghế trong một Booking và tạo Order tương ứng.
    Ticket chưa được tạo ở bước này.
    """
    return booking_service.create_booking_logic(
        db=db,
        booking_in=booking_in,
        current_user_id=current_user.id,
    )


# ========================================================
# 2. READ: USER VÀ ADMIN XEM BOOKING
# ========================================================
@router.get(
    "/me",
    response_model=List[booking_schema.BookingResponse],
)
def get_my_bookings(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(any_user),
):
    return booking_service.get_my_bookings(
        db=db,
        current_user_id=current_user.id,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/my-tickets",
    response_model=List[booking_schema.UserTicketResponse],
)
def get_my_tickets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(any_user),
):
    return booking_service.get_my_tickets(
        db=db,
        current_user_id=current_user.id,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/admin/all",
    response_model=List[booking_schema.BookingResponse],
)
def get_all_bookings_for_admin(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    return booking_service.get_all_bookings_logic(
        db,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/admin/{booking_id}",
    response_model=booking_schema.BookingResponse,
)
def get_booking_detail_for_admin(
    booking_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    return booking_service.get_booking_detail_for_admin(
        db=db,
        booking_id=booking_id,
    )


# ========================================================
# 3. SYSTEM/TICKET: CLEANUP VÀ QUÉT VÉ
# ========================================================
@router.post("/admin/cleanup-expired")
def cleanup_expired_bookings(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    count = booking_service.cleanup_expired_bookings_logic(db, limit=limit)
    return {"expired_bookings": count}


@router.post(
    "/tickets/{qr_token}/use",
    response_model=booking_schema.TicketResponse,
)
def use_ticket(
    qr_token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    return booking_service.use_ticket_logic(db, qr_token)


# ========================================================
# 4. DETAIL/CANCEL: LUÔN KIỂM TRA QUYỀN SỞ HỮU
# ========================================================
@router.get(
    "/{booking_id}",
    response_model=booking_schema.BookingResponse,
)
def get_booking_detail(
    booking_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(any_user),
):
    return booking_service.get_booking_detail(
        db=db,
        booking_id=booking_id,
        current_user_id=current_user.id,
    )


@router.delete("/{booking_id}")
def cancel_booking(
    booking_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(any_user),
):
    return booking_service.cancel_booking_logic(
        db=db,
        booking_id=booking_id,
        current_user_id=current_user.id,
    )
