from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.time_utils import (
    app_datetime_to_local_naive,
    app_datetime_to_utc_naive,
    app_now_naive,
    effective_expiry_utc,
    utc_now_naive,
)
from app.models.booking import (
    BookingStatus,
    Event,
    SeatStatus,
    TicketStatus,
)
from app.models.order import OrderStatus
from app.models.payment import PaymentStatus
from app.repositories.booking import booking_repo
from app.repositories.order import order_repo
from app.schemas.booking import BookingCreate
from app.services import order_service


# ========================================================
# 1. CREATE: GIỮ GHẾ, TẠO BOOKING ITEMS VÀ ORDER
# ========================================================
def create_booking_logic(
    db: Session,
    booking_in: BookingCreate,
    current_user_id: UUID,
):
    """
    Luồng tạo booking:
    1. Kiểm tra suất chiếu.
    2. Khóa các ghế được chọn để chống đặt trùng.
    3. Tạo Booking HELD và một BookingItem cho mỗi ghế.
    4. Tạo Order PENDING từ tổng unit_price.
    5. Commit tất cả trong cùng một transaction.
    """
    cleanup_expired_bookings_logic(db, limit=500)

    event = db.query(Event).filter(Event.id == booking_in.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Không tìm thấy suất chiếu.")

    now_local = app_now_naive()
    now_utc = utc_now_naive()
    event_start_time = app_datetime_to_local_naive(event.start_time)
    if event_start_time <= now_local:
        raise HTTPException(
            status_code=400,
            detail="Suất chiếu đã bắt đầu, không thể đặt vé.",
        )

    seats = booking_repo.lock_seats_for_event(
        db,
        event_id=booking_in.event_id,
        seat_ids=booking_in.seat_ids,
    )
    if len(seats) != len(booking_in.seat_ids):
        raise HTTPException(
            status_code=400,
            detail="Một số ghế không tồn tại hoặc không thuộc suất chiếu.",
        )

    unavailable_seats = [
        seat.seat_code
        for seat in seats
        if seat.status != SeatStatus.AVAILABLE
    ]
    if unavailable_seats:
        raise HTTPException(
            status_code=409,
            detail=f"Ghế đã được giữ hoặc bán: {', '.join(unavailable_seats)}.",
        )

    hold_expires_at = min(
        now_utc + timedelta(minutes=settings.BOOKING_HOLD_MINUTES),
        app_datetime_to_utc_naive(event.start_time),
    )

    try:
        booking = booking_repo.create_booking(
            db,
            {
                "event_id": event.id,
                "status": BookingStatus.HELD,
                "hold_expires_at": hold_expires_at,
                "created_at": now_utc,
                "updated_at": now_utc,
            },
        )

        booking_items_data = []
        for seat in seats:
            seat.status = SeatStatus.HELD
            booking_items_data.append(
                {
                    "booking_id": booking.id,
                    "seat_id": seat.id,
                    "unit_price": event.price,
                    "created_at": now_utc,
                }
            )

        booking_repo.create_booking_items(db, booking_items_data)
        amount = sum(item["unit_price"] for item in booking_items_data)
        order = order_service.create_order_for_booking(
            db,
            booking_id=booking.id,
            user_id=current_user_id,
            amount=amount,
        )

        db.commit()
        db.refresh(booking)
        db.refresh(order)
        return {"booking": booking, "order": order}
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Booking hoặc đơn hàng bị trùng dữ liệu.",
        ) from exc
    except Exception:
        db.rollback()
        raise


# ========================================================
# 2. READ: BOOKING CỦA USER VÀ DANH SÁCH ADMIN
# ========================================================
def get_my_bookings(
    db: Session,
    current_user_id: UUID,
    skip: int = 0,
    limit: int = 100,
):
    cleanup_expired_tickets_logic(db, limit=500)
    return booking_repo.get_bookings_by_user_id(
        db,
        user_id=current_user_id,
        skip=max(skip, 0),
        limit=min(max(limit, 1), 100),
    )


def get_my_tickets(
    db: Session,
    current_user_id: UUID,
    skip: int = 0,
    limit: int = 100,
):
    cleanup_expired_tickets_logic(db, limit=500)
    tickets = booking_repo.get_tickets_by_user_id(
        db,
        user_id=current_user_id,
        skip=max(skip, 0),
        limit=min(max(limit, 1), 100),
    )
    return [
        {
            "id": ticket.id,
            "qr_token": ticket.qr_token,
            "issued_at": ticket.issued_at,
            "used_at": ticket.used_at,
            "status": ticket.status,
            "booking_id": ticket.booking_item.booking_id,
            "booking_item_id": ticket.booking_item_id,
            "event_id": ticket.booking_item.booking.event_id,
            "seat_id": ticket.booking_item.seat_id,
            "seat_code": ticket.booking_item.seat.seat_code,
            "unit_price": ticket.booking_item.unit_price,
        }
        for ticket in tickets
    ]


def get_all_bookings_logic(
    db: Session,
    skip: int = 0,
    limit: int = 100,
):
    cleanup_expired_tickets_logic(db, limit=500)
    return booking_repo.get_all_bookings(
        db,
        skip=max(skip, 0),
        limit=min(max(limit, 1), 100),
    )


def get_booking_detail(
    db: Session,
    booking_id: UUID,
    current_user_id: UUID,
):
    cleanup_expired_tickets_logic(db, limit=500)
    booking = booking_repo.get_booking_by_id_and_user_id(
        db,
        booking_id=booking_id,
        user_id=current_user_id,
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Không tìm thấy booking.")
    return booking


def get_booking_detail_for_admin(
    db: Session,
    booking_id: UUID,
):
    cleanup_expired_tickets_logic(db, limit=500)
    booking = booking_repo.get_booking_by_id(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Không tìm thấy booking.")
    return booking


# ========================================================
# 3. CANCEL: USER HỦY BOOKING THÔNG QUA ORDER
# ========================================================
def cancel_booking_logic(
    db: Session,
    booking_id: UUID,
    current_user_id: UUID,
):
    order = order_repo.get_order_by_booking_id(db, booking_id)
    if not order or order.user_id != current_user_id:
        raise HTTPException(status_code=404, detail="Không tìm thấy booking.")

    cancelled_order = order_service.cancel_order(
        db,
        order_id=order.id,
        current_user_id=current_user_id,
        reason="User cancelled booking",
    )
    return {
        "message": "Đã hủy booking và trả ghế thành công.",
        "order_id": str(cancelled_order.id),
    }


# ========================================================
# 4. SYSTEM: GIẢI PHÓNG BOOKING HẾT HẠN
# ========================================================
def cleanup_expired_bookings_logic(
    db: Session,
    limit: int = 100,
) -> int:
    """
    Booking quá hạn được chuyển EXPIRED và ghế HELD được trả về AVAILABLE.
    Link payOS đã được tạo với expiredAt cùng thời điểm nên không cần gọi hủy
    từng link trong batch cleanup.
    """
    now_utc = utc_now_naive()
    bookings = booking_repo.get_held_bookings_for_expiry_check(
        db,
        limit=min(max(limit, 1), 500),
    )

    try:
        expired_count = 0
        for booking in bookings:
            order = booking.order
            expires_at_utc = effective_expiry_utc(
                created_at=booking.created_at,
                hold_expires_at=booking.hold_expires_at,
                order_created_at=order.created_at if order else None,
            )
            if expires_at_utc > now_utc:
                continue

            booking.status = BookingStatus.EXPIRED
            expired_count += 1

            for item in booking.booking_items:
                if item.seat.status == SeatStatus.HELD:
                    item.seat.status = SeatStatus.AVAILABLE

            if order and order.status == OrderStatus.PENDING:
                order.status = OrderStatus.EXPIRED
                order.expired_at = datetime.now(timezone.utc)

                for payment in order.payments:
                    if payment.status == PaymentStatus.PENDING:
                        payment.status = PaymentStatus.CANCELLED

        db.commit()
        return expired_count
    except Exception:
        db.rollback()
        raise


def cleanup_expired_tickets_logic(
    db: Session,
    limit: int = 500,
) -> int:
    tickets = booking_repo.get_expired_issued_tickets_for_update(
        db,
        now=app_now_naive(),
        limit=min(max(limit, 1), 500),
    )

    try:
        for ticket in tickets:
            ticket.status = TicketStatus.EXPIRED
        db.commit()
        return len(tickets)
    except Exception:
        db.rollback()
        raise


# ========================================================
# 5. TICKET: QUÉT QR VÀ ĐÁNH DẤU VÉ ĐÃ SỬ DỤNG
# ========================================================
def use_ticket_logic(db: Session, qr_token: str):
    ticket = booking_repo.get_ticket_by_qr_token_for_update(db, qr_token)
    if not ticket:
        raise HTTPException(status_code=404, detail="Không tìm thấy vé.")
    if ticket.status == TicketStatus.USED:
        raise HTTPException(status_code=409, detail="Vé đã được sử dụng.")
    if ticket.status == TicketStatus.EXPIRED:
        raise HTTPException(status_code=409, detail="Vé đã hết hiệu lực.")

    event = ticket.booking_item.booking.event
    now = app_now_naive()
    event_start_time = app_datetime_to_local_naive(event.start_time)
    film_end_time = (
        app_datetime_to_local_naive(event.end_time)
        - timedelta(minutes=15)
    )
    if film_end_time <= now:
        ticket.status = TicketStatus.EXPIRED
        db.commit()
        raise HTTPException(status_code=409, detail="Vé đã hết hiệu lực.")
    if event_start_time > now:
        raise HTTPException(status_code=409, detail="Suất chiếu chưa bắt đầu.")

    ticket.status = TicketStatus.USED
    ticket.used_at = utc_now_naive()
    db.commit()
    db.refresh(ticket)
    return ticket
