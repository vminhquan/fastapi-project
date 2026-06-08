from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID


class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class OrderCreateInternal(BaseModel):
    booking_id: UUID
    user_id: UUID
    order_code: int
    amount: int
    description: str


class OrderCustomerResponse(BaseModel):
    id: UUID
    email: str
    full_name: str | None = None
    phone_number: str | None = None

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    id: UUID
    order_code: int
    user_id: UUID
    booking_id: UUID
    amount: int
    currency: str
    description: str
    status: OrderStatus

    created_at: datetime
    updated_at: datetime
    paid_at: datetime | None = None
    cancelled_at: datetime | None = None
    expired_at: datetime | None = None
    customer: OrderCustomerResponse | None = None
    booking_status: str | None = None
    movie_title: str | None = None
    ticket_count: int = 0
    seat_codes: list[str] = Field(default_factory=list)
    provider_order_code: int | None = None
    payment_status: str | None = None

    model_config = ConfigDict(from_attributes=True)
