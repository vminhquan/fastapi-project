from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CreatePaymentLinkRequest(BaseModel):
    order_id: UUID


class PaymentLinkResponse(BaseModel):
    payment_id: UUID
    order_id: UUID
    order_code: int
    amount: int
    status: PaymentStatus
    checkout_url: str
    payment_link_id: str
    qr_code: str | None = None


class PaymentResponse(BaseModel):
    id: UUID
    order_id: UUID
    provider: str
    provider_order_code: int
    payment_link_id: str | None = None
    checkout_url: str | None = None
    amount: int
    status: PaymentStatus
    transaction_reference: str | None = None
    created_at: datetime
    updated_at: datetime
    paid_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PaymentReconcileResponse(BaseModel):
    payment: PaymentResponse
    provider_status: str
    changed: bool


class PayOSWebhookData(BaseModel):
    order_code: int = Field(alias="orderCode")
    amount: int
    description: str
    account_number: str = Field(alias="accountNumber")
    reference: str
    transaction_datetime: str = Field(alias="transactionDateTime")
    currency: str
    payment_link_id: str = Field(alias="paymentLinkId")
    code: str
    desc: str

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class PayOSWebhookRequest(BaseModel):
    code: str
    desc: str
    success: bool
    data: PayOSWebhookData
    signature: str


class CancelPaymentRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=255)
