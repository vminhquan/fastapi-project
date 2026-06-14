import secrets
import time
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.time_utils import effective_expiry_utc, utc_now_naive
from app.models.booking import BookingStatus, SeatStatus
from app.models.order import OrderStatus
from app.models.payment import PaymentStatus
from app.repositories.booking import booking_repo
from app.repositories.order import order_repo
from app.repositories.payment import payment_repo
from app.schemas.payment import PayOSWebhookRequest
from app.services import payos_service
from app.services.payos_service import PayOSError


ACTIVE_PAYOS_STATUSES = {"PENDING", "PROCESSING"}
FINAL_PAYOS_STATUSES = {"PAID", "CANCELLED"}


def _generate_provider_order_code(db: Session) -> int:
    for _ in range(10):
        code = int(f"{int(time.time())}{secrets.randbelow(10000):04d}")
        if not payment_repo.get_payment_by_provider_order_code(db, code):
            return code
    raise HTTPException(status_code=500, detail="Không thể tạo mã thanh toán.")


def _payment_description(provider_order_code: int) -> str:
    return f"QTIK{provider_order_code % 100000:05d}"


def _payment_link_response(payment, qr_code: str | None = None) -> dict:
    return {
        "payment_id": payment.id,
        "order_id": payment.order_id,
        "order_code": payment.provider_order_code,
        "amount": payment.amount,
        "status": payment.status.value,
        "checkout_url": payment.checkout_url,
        "payment_link_id": payment.payment_link_id,
        "qr_code": qr_code,
    }


def _transaction_reference(data: dict) -> str | None:
    transactions = data.get("transactions")
    if isinstance(transactions, list):
        candidates = reversed(transactions)
    elif isinstance(transactions, dict):
        if "reference" in transactions:
            candidates = [transactions]
        else:
            candidates = reversed(list(transactions.values()))
    else:
        return None

    for transaction in candidates:
        if not isinstance(transaction, dict):
            continue
        reference = transaction.get("reference") or transaction.get("referenceId")
        if reference:
            return str(reference)
    return None


def _complete_paid_payment(
    db: Session,
    *,
    payment,
    order,
    booking,
    raw_response: dict,
    transaction_reference: str | None = None,
) -> tuple[bool, str]:
    changed = (
        payment.status != PaymentStatus.PAID
        or order.status != OrderStatus.PAID
        or booking.status != BookingStatus.CONFIRMED
    )

    if transaction_reference:
        duplicate_reference = payment_repo.get_payment_by_transaction_reference(
            db,
            transaction_reference,
        )
        if duplicate_reference and duplicate_reference.id != payment.id:
            raise HTTPException(
                status_code=409,
                detail="Mã giao dịch đã được sử dụng.",
            )
        payment.transaction_reference = transaction_reference

    now_utc = datetime.now(timezone.utc)
    payment.status = PaymentStatus.PAID
    payment.raw_response = raw_response
    payment.paid_at = payment.paid_at or now_utc

    order.status = OrderStatus.PAID
    order.paid_at = order.paid_at or now_utc

    if booking.status == BookingStatus.CONFIRMED:
        return changed, "Booking đã được xác nhận trước đó."

    if booking.status != BookingStatus.HELD:
        return (
            changed,
            "Đã ghi nhận thanh toán; booking cần được xử lý thủ công.",
        )

    tickets_data = []
    for item in booking.booking_items:
        item.seat.status = SeatStatus.SOLD
        if item.ticket is None:
            tickets_data.append(
                {
                    "booking_item_id": item.id,
                    "qr_token": secrets.token_urlsafe(32),
                }
            )

    if tickets_data:
        booking_repo.create_tickets(db, tickets_data)

    booking.status = BookingStatus.CONFIRMED
    booking.confirmed_at = utc_now_naive()
    return changed, "Thanh toán và phát hành vé thành công."


def _apply_payos_state(
    db: Session,
    *,
    payment,
    order,
    booking,
    response: dict,
) -> dict:
    data = response.get("data")
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=502,
            detail="payOS trả về dữ liệu đối soát không hợp lệ.",
        )

    provider_status = str(data.get("status", "")).upper()
    if provider_status not in ACTIVE_PAYOS_STATUSES | FINAL_PAYOS_STATUSES:
        raise HTTPException(
            status_code=502,
            detail=f"Trạng thái payOS không được hỗ trợ: {provider_status or 'EMPTY'}.",
        )

    try:
        provider_order_code = (
            int(data["orderCode"])
            if data.get("orderCode") is not None
            else None
        )
        provider_amount = (
            int(data["amount"])
            if data.get("amount") is not None
            else None
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Mã đơn hàng hoặc số tiền từ payOS không hợp lệ.",
        ) from exc

    if (
        provider_order_code is not None
        and provider_order_code != payment.provider_order_code
    ):
        raise HTTPException(
            status_code=409,
            detail="Mã đơn hàng đối soát không khớp.",
        )

    if (
        provider_amount is not None
        and (
            provider_amount != payment.amount
            or provider_amount != order.amount
        )
    ):
        raise HTTPException(
            status_code=409,
            detail="Số tiền đối soát không khớp.",
        )

    previous_status = payment.status
    previous_order_status = order.status
    previous_booking_status = booking.status
    provider_payment_link_id = data.get("paymentLinkId") or data.get("id")
    if provider_payment_link_id:
        provider_payment_link_id = str(provider_payment_link_id)
        if (
            payment.payment_link_id
            and payment.payment_link_id != provider_payment_link_id
        ):
            raise HTTPException(
                status_code=409,
                detail="Payment link đối soát không khớp.",
            )
        payment.payment_link_id = provider_payment_link_id

    if data.get("checkoutUrl"):
        payment.checkout_url = data["checkoutUrl"]
    payment.raw_response = response

    message = "Trạng thái payment đã được đối soát."
    changed = False
    if provider_status == "PAID":
        changed, message = _complete_paid_payment(
            db,
            payment=payment,
            order=order,
            booking=booking,
            raw_response=response,
            transaction_reference=_transaction_reference(data),
        )
    elif provider_status == "CANCELLED":
        if payment.status != PaymentStatus.PAID:
            payment.status = PaymentStatus.CANCELLED
            if order.status == OrderStatus.PENDING:
                order.status = OrderStatus.CANCELLED
                order.cancelled_at = datetime.now(timezone.utc)

            if booking.status == BookingStatus.HELD:
                booking.status = BookingStatus.CANCELLED
                booking.cancelled_at = utc_now_naive()
                for item in booking.booking_items:
                    if item.seat.status == SeatStatus.HELD:
                        item.seat.status = SeatStatus.AVAILABLE

        changed = (
            previous_status != payment.status
            or previous_order_status != order.status
            or previous_booking_status != booking.status
        )
        message = "Đã hủy thanh toán, hủy vé và giải phóng ghế."
    elif payment.status == PaymentStatus.PENDING:
        changed = False

    return {
        "provider_status": provider_status,
        "changed": changed,
        "message": message,
    }


def _fetch_and_apply_payos_state(
    db: Session,
    *,
    payment,
    order,
    booking,
) -> dict:
    lookup_id = payment.payment_link_id or payment.provider_order_code
    response = payos_service.get_payment_link(lookup_id)
    return _apply_payos_state(
        db,
        payment=payment,
        order=order,
        booking=booking,
        response=response,
    )


def create_payment_link_logic(
    db: Session,
    *,
    order_id: UUID,
    current_user_id: UUID,
):
    """
    Tạo một lần thanh toán payOS cho Order.
    Amount luôn lấy từ Order, frontend không được quyền quyết định số tiền.
    """
    order = order_repo.get_order_for_update(db, order_id)
    if not order or order.user_id != current_user_id:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng.")
    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail="Đơn hàng không còn ở trạng thái chờ thanh toán.",
        )

    booking = booking_repo.get_booking_for_update(db, order.booking_id)
    if not booking or booking.status != BookingStatus.HELD:
        raise HTTPException(status_code=400, detail="Booking không còn hiệu lực.")
    booking_expires_at = effective_expiry_utc(
        created_at=booking.created_at,
        hold_expires_at=booking.hold_expires_at,
        order_created_at=order.created_at,
    )
    if booking_expires_at <= utc_now_naive():
        raise HTTPException(status_code=400, detail="Booking đã hết thời gian giữ ghế.")

    latest_payment = payment_repo.get_latest_payment_by_order_id(db, order.id)
    if latest_payment and latest_payment.status == PaymentStatus.PENDING:
        latest_payment = payment_repo.get_payment_by_id_for_update(
            db,
            latest_payment.id,
        )
        try:
            reconciliation = _fetch_and_apply_payos_state(
                db,
                payment=latest_payment,
                order=order,
                booking=booking,
            )
        except PayOSError as exc:
            db.rollback()
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except HTTPException:
            db.rollback()
            raise

        if reconciliation["provider_status"] in ACTIVE_PAYOS_STATUSES:
            db.commit()
            db.refresh(latest_payment)
            if latest_payment.checkout_url and latest_payment.payment_link_id:
                return _payment_link_response(latest_payment)
            raise HTTPException(
                status_code=409,
                detail="Yêu cầu tạo link thanh toán đang được xử lý.",
            )

        if reconciliation["provider_status"] == "PAID":
            db.commit()
            raise HTTPException(
                status_code=409,
                detail="Đơn hàng đã được thanh toán.",
            )

    provider_order_code = _generate_provider_order_code(db)
    payment = payment_repo.create_payment(
        db,
        {
            "order_id": order.id,
            "provider": "payos",
            "provider_order_code": provider_order_code,
            "amount": order.amount,
            "status": PaymentStatus.PENDING,
        },
    )

    # Lưu lần thử trước khi gọi hệ thống bên ngoài để có thể đối soát khi timeout.
    db.commit()
    db.refresh(payment)

    items = [
        {
            "name": f"Ghế {item.seat.seat_code}",
            "quantity": 1,
            "price": item.unit_price,
        }
        for item in booking.booking_items
    ]
    items_total = sum(item["price"] * item["quantity"] for item in items)
    if items_total != order.amount:
        payment.status = PaymentStatus.FAILED
        payment.raw_response = {"error": "Order amount does not match booking items."}
        db.commit()
        raise HTTPException(
            status_code=409,
            detail="Tổng tiền đơn hàng không khớp với các ghế đã đặt.",
        )

    try:
        response = payos_service.create_payment_link(
            order_code=provider_order_code,
            amount=order.amount,
            description=_payment_description(provider_order_code),
            expired_at=int(
                booking_expires_at.replace(tzinfo=timezone.utc).timestamp()
            ),
            items=items,
        )
        data = response["data"]
        payment.payment_link_id = data["paymentLinkId"]
        payment.checkout_url = data["checkoutUrl"]
        payment.raw_response = response
        db.commit()
        db.refresh(payment)
        return _payment_link_response(payment, data.get("qrCode"))
    except PayOSError as exc:
        payment.status = PaymentStatus.FAILED
        payment.raw_response = {"error": str(exc)}
        db.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise


def get_payment_detail(
    db: Session,
    *,
    payment_id: UUID,
    current_user_id: UUID,
):
    payment = payment_repo.get_payment_by_id(db, payment_id)
    if not payment or payment.order.user_id != current_user_id:
        raise HTTPException(status_code=404, detail="Không tìm thấy thanh toán.")
    return payment


def get_order_payments(
    db: Session,
    *,
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
    return payment_repo.get_payments_by_order_id(db, order_id)


def _reconcile_owned_payment(
    db: Session,
    *,
    payment,
    current_user_id: UUID,
):
    if not payment:
        raise HTTPException(status_code=404, detail="Không tìm thấy thanh toán.")

    order = order_repo.get_order_for_update(db, payment.order_id)
    if not order or order.user_id != current_user_id:
        db.rollback()
        raise HTTPException(status_code=404, detail="Không tìm thấy thanh toán.")

    booking = booking_repo.get_booking_for_update(db, order.booking_id)
    if not booking:
        db.rollback()
        raise HTTPException(status_code=404, detail="Không tìm thấy booking.")

    try:
        result = _fetch_and_apply_payos_state(
            db,
            payment=payment,
            order=order,
            booking=booking,
        )
        db.commit()
        db.refresh(payment)
        return {
            "payment": payment,
            "provider_status": result["provider_status"],
            "changed": result["changed"],
        }
    except PayOSError as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise


def reconcile_payment_by_provider_order_code(
    db: Session,
    *,
    provider_order_code: int,
    current_user_id: UUID,
):
    payment = payment_repo.get_payment_by_provider_order_code_for_update(
        db,
        provider_order_code,
    )
    return _reconcile_owned_payment(
        db,
        payment=payment,
        current_user_id=current_user_id,
    )


def reconcile_payment_by_payment_link_id(
    db: Session,
    *,
    payment_link_id: str,
    current_user_id: UUID,
):
    payment = payment_repo.get_payment_by_payment_link_id_for_update(
        db,
        payment_link_id,
    )
    return _reconcile_owned_payment(
        db,
        payment=payment,
        current_user_id=current_user_id,
    )


def process_payos_webhook(
    db: Session,
    webhook: PayOSWebhookRequest,
):
    """
    Xác minh chữ ký và xử lý webhook theo kiểu idempotent.
    Một webhook gửi lại nhiều lần chỉ phát hành mỗi BookingItem đúng một Ticket.
    """
    webhook_data = webhook.data.model_dump(
        mode="json",
        by_alias=True,
        exclude_none=False,
    )
    if not payos_service.verify_signature(webhook_data, webhook.signature):
        raise HTTPException(status_code=400, detail="Chữ ký webhook không hợp lệ.")

    payment = payment_repo.get_payment_by_provider_order_code_for_update(
        db,
        webhook.data.order_code,
    )
    if not payment:
        # payOS gửi dữ liệu mẫu khi xác nhận webhook URL.
        return {"success": True, "message": "Webhook hợp lệ, không có giao dịch local."}

    order = order_repo.get_order_for_update(db, payment.order_id)
    if not order:
        db.rollback()
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng.")

    booking = booking_repo.get_booking_for_update(db, order.booking_id)
    if not booking:
        db.rollback()
        raise HTTPException(status_code=404, detail="Dữ liệu thanh toán không đầy đủ.")

    if webhook.data.amount != payment.amount or webhook.data.amount != order.amount:
        db.rollback()
        raise HTTPException(status_code=409, detail="Số tiền webhook không khớp.")

    if not webhook.success or webhook.code != "00" or webhook.data.code != "00":
        payment.raw_response = webhook.model_dump(mode="json", by_alias=True)
        db.commit()
        return {"success": True, "message": "Webhook không phải giao dịch thành công."}

    _, message = _complete_paid_payment(
        db,
        payment=payment,
        order=order,
        booking=booking,
        raw_response=webhook.model_dump(mode="json", by_alias=True),
        transaction_reference=webhook.data.reference,
    )
    db.commit()
    return {"success": True, "message": message}
