from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.order import OrderResponse


class BookingStatus(str, Enum):
    HELD = "held"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class TicketStatus(str, Enum):
    ISSUED = "issued"
    USED = "used"
    EXPIRED = "expired"

class BookingCreate(BaseModel):
    event_id: UUID
    seat_ids: list[UUID] = Field(..., min_length=1)

    @field_validator("seat_ids")
    @classmethod
    def validate_unique_seats(cls, seat_ids: list[UUID]):
        if len(seat_ids) != len(set(seat_ids)):
            raise ValueError("Danh sách ghế không được trùng nhau")
        return seat_ids


class TicketResponse(BaseModel):
    id: UUID
    qr_token: str
    issued_at: datetime
    used_at: datetime | None = None
    status: TicketStatus

    model_config = ConfigDict(from_attributes=True)


class BookingFilmResponse(BaseModel):
    id: UUID
    title: str

    model_config = ConfigDict(from_attributes=True)


class BookingRoomResponse(BaseModel):
    id: UUID
    name: str

    model_config = ConfigDict(from_attributes=True)


class BookingEventResponse(BaseModel):
    id: UUID
    start_time: datetime
    end_time: datetime
    film: BookingFilmResponse
    room: BookingRoomResponse

    model_config = ConfigDict(from_attributes=True)


class UserTicketResponse(TicketResponse):
    booking_id: UUID
    booking_item_id: UUID
    event_id: UUID
    seat_id: UUID
    seat_code: str
    unit_price: int


class BookingItemResponse(BaseModel):
    id: UUID
    seat_id: UUID
    seat_code: str
    unit_price: int
    created_at: datetime
    ticket: TicketResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class BookingResponse(BaseModel):
    id: UUID
    event_id: UUID
    status: BookingStatus
    hold_expires_at: datetime
    created_at: datetime
    updated_at: datetime
    confirmed_at: datetime | None = None
    cancelled_at: datetime | None = None
    booking_items: list[BookingItemResponse]
    event: BookingEventResponse

    model_config = ConfigDict(from_attributes=True)


class BookingCheckoutResponse(BaseModel):
    booking: BookingResponse
    order: OrderResponse
