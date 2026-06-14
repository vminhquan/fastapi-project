import secrets
import time
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.booking import BookingStatus, SeatStatus
from app.models.order import Order, OrderStatus
from app.models.payment import PaymentStatus
from app.repositories.booking import booking_repo
from app.repositories.order import order_repo
from app.repositories.payment import payment_repo
from app.services import payos_service
from app.services.payos_service import PayOSError
from app.core.time_utils import utc_now_naive


def _generate_order_code(db: Session) -> int:
    for _ in range(10):
        code = int(f"{int(time.time())}{secrets.randbelow(10000):04d}")
        if not order_repo.get_order_by_order_code(db, code):
            return code
    raise HTTPException(status_code=500, detail="Không thể tạo mã đơn hàng.")


def _payment_description(order_code: int) -> str:
    # Giữ tối đa 9 ký tự để tương thích nội dung chuyển khoản payOS.
    return f"QTIK{order_code % 100000:05d}"


def create_order_for_booking(
    db: Session,
    *,
    booking_id: UUID,
    user_id: UUID,
    amount: int,
) -> Order:
    """Tạo Order nội bộ; service gọi hàm này phải tự commit/rollback."""
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Tổng tiền đơn hàng không hợp lệ.")

    existing_order = order_repo.get_order_by_booking_id(db, booking_id)
    if existing_order:
        return existing_order

    order_code = _generate_order_code(db)
    return order_repo.create_order(
        db,
        {
            "booking_id": booking_id,
            "user_id": user_id,
            "order_code": order_code,
            "amount": amount,
            "description": _payment_description(order_code),
            "status": OrderStatus.PENDING,
        },
    )


def get_my_orders(
    db: Session,
    current_user_id: UUID,
    page: int = 1,
    skip: int = 0,
    limit: int = 5,
    search: str | None = None,
):
    normalized_search = " ".join((search or "").split()) or None
    orders, total = order_repo.get_orders_by_user_id(
        db,
        user_id=current_user_id,
        skip=max(skip, 0),
        limit=min(max(limit, 1), 100),
        search=normalized_search,
    )
    return {
        "items": orders,
        "total": total,
        "page": page,
        "limit": limit,
    }


def get_order_detail(
    db: Session,
    order_id: UUID,
    current_user_id: UUID,
):
    order = order_repo.get_order_by_id_and_user_id(
        db,
        order_id=order_id,
        user_id=current_user_id,
    )
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng.")
    return order


def get_all_orders(
    db: Session,
    skip: int = 0,
    limit: int = 100,
):
    return order_repo.get_all_orders(
        db,
        skip=max(skip, 0),
        limit=min(max(limit, 1), 100),
    )


def cancel_order(
    db: Session,
    *,
    order_id: UUID,
    current_user_id: UUID,
    reason: str,
) -> Order:
    """
    Hủy Order PENDING, hủy link payOS nếu có và trả ghế về AVAILABLE.
    Toàn bộ thay đổi local chỉ commit sau khi payOS xác nhận hủy link.
    """
    order = order_repo.get_order_for_update(db, order_id)
    if not order or order.user_id != current_user_id:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng.")

    if order.status == OrderStatus.CANCELLED:
        return order
    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail="Chỉ có thể hủy đơn hàng đang chờ thanh toán.",
        )

    booking = booking_repo.get_booking_for_update(db, order.booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Không tìm thấy booking.")

    payments = payment_repo.get_payments_by_order_id(db, order.id)
    active_payment = next(
        (
            payment
            for payment in payments
            if payment.status == PaymentStatus.PENDING
            and payment.payment_link_id
        ),
        None,
    )

    try:
        if active_payment:
            response = payos_service.cancel_payment_link(
                active_payment.payment_link_id,
                reason,
            )
            if response.get("data", {}).get("status") != "CANCELLED":
                raise HTTPException(
                    status_code=409,
                    detail="Link thanh toán không thể hủy ở trạng thái hiện tại.",
                )
            active_payment.raw_response = response

        order.status = OrderStatus.CANCELLED
        order.cancelled_at = datetime.now(timezone.utc)

        if booking.status == BookingStatus.HELD:
            booking.status = BookingStatus.CANCELLED
            booking.cancelled_at = utc_now_naive()

        for item in booking.booking_items:
            if item.seat.status == SeatStatus.HELD:
                item.seat.status = SeatStatus.AVAILABLE

        for payment in payments:
            if payment.status == PaymentStatus.PENDING:
                payment.status = PaymentStatus.CANCELLED

        db.commit()
        db.refresh(order)
        return order
    except PayOSError as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise
