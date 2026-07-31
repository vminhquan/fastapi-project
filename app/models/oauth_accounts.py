from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Column, Index, String, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid

class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"
    __table_args__ = (
        CheckConstraint(
            "provider IN ('google', 'facebook')",
            name="ck_oauth_accounts_provider",
        ),
        UniqueConstraint(
            "provider",
            "provider_subject",
            name="uq_oauth_provider_subject",
        ),
        UniqueConstraint(
            "user_id",
            "provider",
            name="uq_oauth_user_provider",
        ),
        Index("ix_oauth_accounts_user_id", "user_id"),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    provider =  Column(String(20), nullable=False)
    provider_subject = Column(String(255), nullable=True)
    
    provider_email = Column(String(255), nullable=True)
    provider_email_verified = Column(Boolean, nullable=False, default=False)
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    
    user = relationship("User", back_populates="oauth_accounts")