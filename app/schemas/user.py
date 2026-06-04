from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import date

# Khuôn mẫu cơ bản
class UserBase(BaseModel):
    # Dùng EmailStr thay cho str thông thường để tự động check định dạng email (@gmail.com)
    email: EmailStr 
    full_name: str | None = None
    phone_number: str | None = None
    date_of_birth: date | None = None
    is_active: bool = True
    
# Request
class UserCreate(UserBase):
    password: str
    role: str = "user"

class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    phone_number: str | None = None
    date_of_birth: date | None = None
    password: str | None = None
    
# Response
class UserResponse(UserBase):
    id: int
    
    # TUYỆT ĐỐI KHÔNG CÓ TRƯỜNG PASSWORD Ở ĐÂY
    # Việc này giúp lỡ bạn có return cả object, mật khẩu cũng không bị lộ ra ngoài
    
    # Cấu hình Pydantic V2 giúp tự động đọc dữ liệu từ SQLAlchemy Model
    model_config = ConfigDict(from_attributes=True)
    role: str = "user"
    
class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    
class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp: str 
    
class ForgotPwdRequest(BaseModel):
    email: EmailStr
    
class ResetPwdRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str
    
class ResendOTPRequest(BaseModel):
    email: EmailStr
