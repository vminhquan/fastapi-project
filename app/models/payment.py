import uuid
import enum
from sqlalchemy import JSON, BigInteger, Column, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

class PaymentStatus(enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Payment(Base):
    __tablename__ = "payments"
    
    # ĐÃ XÓA __table_args__ 

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Cột này có thể giữ hoặc xóa. Nếu giữ, cứ để mặc định là payos
    provider = Column(String(50), default="payos", nullable=False)
    provider_order_code = Column(BigInteger, unique=True, nullable=False)
    
    # Thông tin đường link thanh toán PayOS trả về
    payment_link_id = Column(String(255), unique=True, nullable=True)
    checkout_url = Column(String(1000), nullable=True)

    amount = Column(BigInteger, nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    transaction_reference = Column(String(255), nullable=True)
    raw_response = Column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)

    order = relationship("Order", back_populates="payments")
