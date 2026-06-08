from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import any_user
from app.models.user import User
from app.schemas.payment import (
    CreatePaymentLinkRequest,
    PaymentLinkResponse,
    PaymentReconcileResponse,
    PaymentResponse,
    PayOSWebhookRequest,
)
from app.services import payment_service


router = APIRouter()


# ========================================================
# 1. CREATE LINK: AMOUNT LẤY TỪ ORDER, KHÔNG LẤY TỪ CLIENT
# ========================================================
@router.post(
    "/links",
    response_model=PaymentLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_payment_link(
    request: CreatePaymentLinkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(any_user),
):
    return payment_service.create_payment_link_logic(
        db,
        order_id=request.order_id,
        current_user_id=current_user.id,
    )


# ========================================================
# 2. WEBHOOK: PUBLIC ENDPOINT NHƯNG BẮT BUỘC VERIFY SIGNATURE
# ========================================================
@router.post("/payos/webhook")
def payos_webhook(
    webhook: PayOSWebhookRequest,
    db: Session = Depends(get_db),
):
    return payment_service.process_payos_webhook(db, webhook)


# ========================================================
# 3. READ: USER CHỈ XEM PAYMENT THUỘC ORDER CỦA MÌNH
# ========================================================
@router.get(
    "/orders/{order_id}",
    response_model=List[PaymentResponse],
)
def get_order_payments(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(any_user),
):
    return payment_service.get_order_payments(
        db,
        order_id=order_id,
        current_user_id=current_user.id,
    )


# ========================================================
# 4. RECONCILE: ĐỒNG BỘ TRẠNG THÁI LOCAL VỚI PAYOS
# ========================================================
@router.post(
    "/reconcile/provider-order-code/{provider_order_code}",
    response_model=PaymentReconcileResponse,
)
def reconcile_by_provider_order_code(
    provider_order_code: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(any_user),
):
    return payment_service.reconcile_payment_by_provider_order_code(
        db,
        provider_order_code=provider_order_code,
        current_user_id=current_user.id,
    )


@router.post(
    "/reconcile/payment-link/{payment_link_id}",
    response_model=PaymentReconcileResponse,
)
def reconcile_by_payment_link_id(
    payment_link_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(any_user),
):
    return payment_service.reconcile_payment_by_payment_link_id(
        db,
        payment_link_id=payment_link_id,
        current_user_id=current_user.id,
    )


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment_detail(
    payment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(any_user),
):
    return payment_service.get_payment_detail(
        db,
        payment_id=payment_id,
        current_user_id=current_user.id,
    )
