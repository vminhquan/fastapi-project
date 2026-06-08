from sqlalchemy import Column, Integer, String, DateTime
from app.core.database import Base
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
import uuid
class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    token = Column(String(500), unique=True, index=True)
    user_email = Column(String(255), index=True)
    blacklisted_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)  # Khi nào token chết
