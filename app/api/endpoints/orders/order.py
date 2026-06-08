from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import admin_only, any_user
from app.models.user import User
from app.schemas.order import OrderResponse
from app.schemas.payment import CancelPaymentRequest
from app.services import booking_service, order_service


router = APIRouter()


# ========================================================
# 1. USER: XEM DANH SÁCH ĐƠN HÀNG CỦA CHÍNH MÌNH
# ========================================================
@router.get("/me", response_model=List[OrderResponse])
def get_my_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(any_user),
):
    booking_service.cleanup_expired_bookings_logic(db, limit=500)
    booking_service.cleanup_expired_tickets_logic(db, limit=500)
    return order_service.get_my_orders(
        db,
        current_user_id=current_user.id,
        skip=skip,
        limit=limit,
    )


# ========================================================
# 2. ADMIN: XEM TOÀN BỘ ĐƠN HÀNG
# ========================================================
@router.get("/admin/all", response_model=List[OrderResponse])
def get_all_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    booking_service.cleanup_expired_bookings_logic(db, limit=500)
    booking_service.cleanup_expired_tickets_logic(db, limit=500)
    return order_service.get_all_orders(db, skip=skip, limit=limit)


# ========================================================
# 3. DETAIL/CANCEL: KIỂM TRA ORDER THUỘC CURRENT USER
# ========================================================
@router.get("/{order_id}", response_model=OrderResponse)
def get_order_detail(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(any_user),
):
    booking_service.cleanup_expired_bookings_logic(db, limit=500)
    booking_service.cleanup_expired_tickets_logic(db, limit=500)
    return order_service.get_order_detail(
        db,
        order_id=order_id,
        current_user_id=current_user.id,
    )


@router.post("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(
    order_id: UUID,
    request: CancelPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(any_user),
):
    return order_service.cancel_order(
        db,
        order_id=order_id,
        current_user_id=current_user.id,
        reason=request.reason,
    )
