from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.schemas import user as user_schema
from app.schemas.user import OTPVerifyRequest, ForgotPwdRequest, ResetPwdRequest, ResendOTPRequest
from app.services import user_service
from typing import List
from app.core.database import get_db
from app.core.security import security_scheme, admin_only, verify_and_refresh_token, any_user
from fastapi.security import HTTPAuthorizationCredentials
from app.models.user import User
from pydantic import BaseModel
from uuid import UUID

router = APIRouter()

@router.post("/register")
def register_endpoint(user_in: user_schema.UserCreate, background_tasks: BackgroundTasks,db: Session = Depends(get_db)):
    # Lớp API chỉ cần đứng vẫy tay gọi Service ra làm việc
    user_service.register_new_user(db, user_in, background_tasks)
    
    return {"message": "Đăng ký thành công! Vui lòng kiểm tra email để lấy mã OTP."}

@router.post("/verify-otp")
def verify_otp(
    request: OTPVerifyRequest, 
    db: Session = Depends(get_db)
):
    """API Xác thực mã OTP"""
    # Giao hết cho Service lo
    user_service.verify_otp_logic(db, request.email, request.otp)
    
    return {"message": "Kích hoạt tài khoản thành công! Bây giờ bạn có thể đăng nhập."}

# tự động tạo ra 2 ô nhập liệu là skip và limit.
# Nếu bạn muốn lấy trang 1 (10 người đầu tiên): Nhập skip=0, limit=10.
# Nếu bạn muốn lấy trang 2 (10 người tiếp theo): Nhập skip=10, limit=10.
@router.get("/", response_model=List[user_schema.UserResponse],dependencies=[Depends(admin_only)])
def read_all_users(
    skip: int = Query(0, description="Số lượng bản ghi muốn bỏ qua"),
    limit: int = Query(100, description="Số lượng bản ghi tối đa muốn lấy"),
    db: Session = Depends(get_db)
):
    users = user_service.get_users(db, skip=skip, limit=limit)
    return users

@router.get("/me", response_model=user_schema.UserResponse)
def read_my_profile(
    current_user: User = Depends(any_user)
):
    """API để User xem thông tin cá nhân của chính mình"""
    return current_user

@router.put("/me", response_model=user_schema.UserResponse)
def update_my_profile(
    user_in: user_schema.UserUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(any_user) # Bất kỳ ai đăng nhập cũng dùng được
):
    """API để User tự cập nhật thông tin cá nhân của chính mình"""
    return user_service.update_user(db, current_user.id, user_in, background_tasks)

@router.get("/{user_id}", response_model=user_schema.UserResponse, dependencies=[Depends(admin_only)])
def read_user_by_id(user_id: UUID, db: Session = Depends(get_db)):
    # Lấy user theo ID
    user = user_service.get_user_by_id(db, user_id)
    return user

@router.put("/{user_id}",  dependencies=[Depends(admin_only)])
def update_user_endpoint(user_id: UUID, user_in: user_schema.UserUpdate, background_tasks: BackgroundTasks,db: Session = Depends(get_db)):
    # Cập nhật user
    updated_user = user_service.update_user(db, user_id, user_in, background_tasks)
    return updated_user


@router.delete("/{user_id}", dependencies=[Depends(admin_only)])
def delete_user_endpoint(user_id: UUID, db: Session = Depends(get_db)):
    result = user_service.delete_user(db, user_id)
    return {"message": "User đã được xóa thành công", **result}

@router.post("/login", response_model=dict)
def login_endpoint(credentials: user_schema.UserLogin, db: Session = Depends(get_db)):
    result = user_service.login_user(db, credentials.email, credentials.password)
    return result

# API refresh token để ng dùng duy trì đăng nhập trong 7 ngày
class TokenRefreshRequest(BaseModel):
    refresh_token: str

@router.post("/refresh")
def refresh_access_token(request: TokenRefreshRequest, db: Session = Depends(get_db)):
    """API Đổi Refresh Token lấy Access Token mới"""
    
    # Chỉ việc gọi hộp đồ nghề từ security.py ra dùng
    new_access_token = verify_and_refresh_token(request.refresh_token, db)
    
    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }

@router.post("/logout")
def logout_endpoint(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme), 
    db: Session = Depends(get_db)
):
    """
    Đăng xuất user - Vô hiệu hóa token
    """
    token = credentials.credentials
    result = user_service.logout_user(db, token)
    return result

@router.post("/forgot-password")
def forgot_password(
    request: ForgotPwdRequest, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    """API Gửi yêu cầu quên mật khẩu (Nhận OTP)"""
    user_service.forgot_password_logic(db, request.email, background_tasks)
    return {"message": "Mã OTP khôi phục mật khẩu đã được gửi đến email của bạn."}

@router.post("/reset-password")
def reset_password(
    request: ResetPwdRequest, 
    db: Session = Depends(get_db)
):
    """API Đổi mật khẩu mới bằng OTP"""
    user_service.reset_password_logic(db, request)
    return {"message": "Đổi mật khẩu thành công! Bạn có thể đăng nhập bằng mật khẩu mới."}

@router.post("/resend-otp")
def resend_otp(
    request: ResendOTPRequest, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    """API Gửi lại mã OTP kích hoạt tài khoản"""
    user_service.resend_otp_logic(db, request.email, background_tasks)
    return {"message": "Mã OTP mới đã được gửi đến email của bạn. Vui lòng kiểm tra!"}
