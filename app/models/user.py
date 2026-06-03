from sqlalchemy import Column, Integer, String, DateTime,Boolean
from app.core.database import Base
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    # email thường dùng làm tài khoản đăng nhập nên cần unique=True (duy nhất)
    email = Column(String(255), unique=True, index=True, nullable=False)
    date_of_birth = Column(DateTime, index=True)
    # Chỉ lưu mật khẩu đã mã hóa
    hashed_password = Column(String(255), nullable=False)
    
    full_name = Column(String(255), nullable=True)
    
    # Cờ đánh dấu tài khoản có đang hoạt động hay bị khóa
    is_active = Column(Boolean, default=False)
    otp_code = Column(String, nullable=True)     # Lưu mã 6 số
    otp_expire_at = Column(DateTime, nullable=True) # lưu giờ hêt hạn
    role = Column(String, default="user")

    bookings = relationship("Booking", back_populates="user")