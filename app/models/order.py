from sqlalchemy import BigInteger,DateTime, Column, Integer, ForeignKey, String, Enum
from sqlalchemy.sql import func
import enum
from app.core.database import Base
from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

class OrderStatus(enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    order_code = Column (BigInteger, unique=True, index=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True, unique=True)
    amount = Column(BigInteger, nullable=False)
    currency = Column(String(3), nullable=False, default="VND", server_default="VND")
    description = Column(String(255), nullable=False)

    status = Column(
        Enum(OrderStatus),
        default=OrderStatus.PENDING,
        nullable=False,
    )
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    paid_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    expired_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User", back_populates="orders")
    booking = relationship("Booking", back_populates="order")
    payments = relationship("Payment", back_populates="order")

    @property
    def customer(self):
        return self.user

    @property
    def booking_status(self):
        return self.booking.status.value if self.booking else None

    @property
    def movie_title(self):
        if not self.booking or not self.booking.event or not self.booking.event.film:
            return None
        return self.booking.event.film.title

    @property
    def ticket_count(self):
        if not self.booking:
            return 0
        return sum(
            1
            for item in self.booking.booking_items
            if item.ticket is not None
        )

    @property
    def seat_codes(self):
        if not self.booking:
            return []
        return [
            item.seat.seat_code
            for item in self.booking.booking_items
            if item.seat is not None
        ]

    def _latest_payment(self):
        if not self.payments:
            return None
        return max(
            self.payments,
            key=lambda payment: (
                payment.created_at.timestamp()
                if payment.created_at
                else 0
            ),
        )

    @property
    def provider_order_code(self):
        payment = self._latest_payment()
        return payment.provider_order_code if payment else None

    @property
    def payment_status(self):
        payment = self._latest_payment()
        return payment.status.value if payment else None
