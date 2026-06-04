from sqlalchemy.orm import Session
from fastapi import HTTPException, BackgroundTasks
from app.repositories.user import user_repo
from app.schemas import user as user_schema
from app.core.security import get_password_hash,verify_password, create_access_token, create_refresh_token
from datetime import datetime, timedelta, timezone
from app.core.utils import generate_otp_code
from app.core.config import settings
from app.schemas.user import ResetPwdRequest
from jose import jwt
from app.core.security import SECRET_KEY, ALGORITHM
from app.repositories import token_repo
import resend

def register_new_user(db: Session, user_in: user_schema.UserCreate, background_tasks: BackgroundTasks):
    # kiểm tra emai đã tồn tại chưa
    existing_user = user_repo.get_user_by_email(db, email=user_in.email)
    if existing_user:
        # TRƯỜNG HỢP A: Email đã là thành viên chính thức
        if existing_user.is_active:
            raise HTTPException(
                status_code=400,
                detail="Email này đã được sử dụng. Vui lòng chọn email khác!"
            )
        
        # TRƯỜNG HỢP B: Email đã đăng ký nhưng CHƯA xác thực OTP
        # Áp dụng Cooldown 60s tại đây để chặn spam đăng ký lại
        if existing_user.otp_expire_at:
            current_time = datetime.now(timezone.utc)
            expire_time = existing_user.otp_expire_at.replace(tzinfo=timezone.utc) if existing_user.otp_expire_at.tzinfo is None else existing_user.otp_expire_at
            
            time_left = expire_time - current_time
            if time_left > timedelta(minutes=4):
                wait_seconds = int(time_left.total_seconds() - 240)
                raise HTTPException(
                    status_code=429,
                    detail=f"Tài khoản này đang chờ xác thực. Vui lòng đợi {wait_seconds} giây để nhận mã mới!"
                )
                
        # Nếu đã qua thời gian cooldown, ta cập nhật OTP mới cho user cũ này luôn
        otp = generate_otp_code()
        existing_user.otp_code = otp
        existing_user.otp_expire_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        # Cập nhật cả mật khẩu nếu họ lỡ gõ mật khẩu khác ở lần đăng ký này
        existing_user.hashed_password = get_password_hash(user_in.password)
        
        user_repo.save_user(db, existing_user)
        background_tasks.add_task(send_otp_email, existing_user.email, otp)
        return existing_user
    # Bảo mật
    hashed_pwd = get_password_hash(user_in.password)
    
    # 3. Sinh mã OTP và tính toán thời gian hết hạn (5 phút)
    otp = generate_otp_code()
    expire_time = datetime.now(timezone.utc) + timedelta(minutes=5)
    # Chuẩn bị dữ liệu để lưu
    
    user_data = {
        "email": user_in.email,
        "full_name": user_in.full_name,
        "hashed_password": hashed_pwd,
        "otp_code": otp,                  
        "otp_expire_at": expire_time
    }
    
    # Gọi Repository để Insert vào Database
    created_user = user_repo.create_user(db, user_data)
    # 6. Giao việc gửi email cho BackgroundTasks xử lý ngầm để API trả kết quả ngay lập tức
    background_tasks.add_task(send_otp_email, created_user.email, otp)
    
    return created_user

def get_users(db: Session, skip: int = 0, limit: int = 100):
    # có thể thêm logic kiểm tra ở đây nếu cần (VD: limit không được vượt quá 1000)
    return user_repo.get_all_users(db, skip=skip, limit=limit)

def get_user_by_id(db: Session, user_id: int):
    user = user_repo.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User không tồn tại!"
        )
    return user

def update_user(db: Session, user_id: int, user_in: user_schema.UserUpdate, background_tasks: BackgroundTasks):
    # Kiểm tra user tồn tại
    user = user_repo.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User không tồn tại!")
    
    # Chuẩn bị dữ liệu cập nhật
    user_data = {}
    email_changed = False 
    otp_to_send = None 
    
    if user_in.email and user_in.email != user.email:
        existing = user_repo.get_user_by_email(db, user_in.email)
        if existing:
            raise HTTPException(status_code=400, detail="Email này đã được sử dụng. Vui lòng chọn email khác!")
        
        user_data["email"] = user_in.email
        user_data["is_active"] = False 
        email_changed = True
        
        # Sinh OTP và đưa vào user_data để LƯU XUỐNG DATABASE
        otp_to_send = generate_otp_code()
        user_data["otp_code"] = otp_to_send
        user_data["otp_expire_at"] = datetime.now(timezone.utc) + timedelta(minutes=5)
        
    if user_in.full_name:
        user_data["full_name"] = user_in.full_name
    
    if user_in.password:
        hashed_pwd = get_password_hash(user_in.password)
        user_data["hashed_password"] = hashed_pwd
    
    if not user_data:
        return user
    
    # Update xuống DB
    updated_user = user_repo.update_user(db, user_id, user_data)
    if email_changed and otp_to_send:
        background_tasks.add_task(send_otp_email, updated_user.email, otp_to_send)
    
    return updated_user

def delete_user(db: Session, user_id: int):
    # Kiểm tra user tồn tại
    user = user_repo.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User không tồn tại!")
    
    # Xóa user
    is_deleted = user_repo.delete_user(db, user_id)
    return {"deleted": is_deleted}

def login_user(db: Session, email: str, password: str):
    """Đăng nhập user"""
    
    # Tìm user theo email
    user = user_repo.get_user_by_email(db, email)

    if not user or not verify_password(password, user.hashed_password): 
        raise HTTPException(
            status_code=401,
            detail="Email hoặc mật khẩu không đúng!"
        )
    # chặn user chưa xác thực
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Tài khoản chưa được kích hoạt. Vui lòng xác thực mã OTP!"
        )
    # access token
    access_token = create_access_token(
        data={
        "sub": user.email,
        "role": user.role
        }
    )
    
    # refresh token
    refresh_token = create_refresh_token(
        data={
        "sub": user.email 
        }
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role
        }
    }

def logout_user(db: Session, token: str):
    """Logout user - thêm token vào blacklist"""
    try:
        # Decode token để lấy thông tin
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_email = payload.get("sub")
        expires_at = datetime.fromtimestamp(payload.get("exp"))
        
        # Thêm token vào blacklist
        token_repo.add_to_blacklist(db, token, user_email, expires_at)
        
        return {
            "message": "Logout thành công",
            "detail": "Token đã bị vô hiệu hóa"
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Logout thất bại: {str(e)}"
        )

def _send_email(receiver_email: str, subject: str, html: str):
    """Gửi email qua Resend HTTP API để tránh bị Render chặn SMTP."""
    if not settings.RESEND_API_KEY:
        raise ValueError("Thiếu biến môi trường RESEND_API_KEY")

    resend.api_key = settings.RESEND_API_KEY
    params = {
        "from": settings.RESEND_FROM_EMAIL,
        "to": receiver_email,
        "subject": subject,
        "html": html,
    }
    return resend.Emails.send(params)

# Hàm gửi email chứa mã OTP
def send_otp_email(receiver_email: str, otp: str):
    """Gửi OTP xác thực tài khoản qua Resend Email API."""
    html = f"""
    <p>Xin chào,</p>
    <p>Bạn vừa yêu cầu kích hoạt tài khoản tại hệ thống của chúng tôi.</p>
    <p>Mã OTP kích hoạt tài khoản của bạn là: <strong>{otp}</strong></p>
    <p>Lưu ý: Mã này chỉ có hiệu lực trong vòng 5 phút. Vui lòng không chia sẻ mã này cho bất kỳ ai.</p>
    <p>Trân trọng,<br>Đội ngũ Hỗ trợ Hệ Thống Bán Vé QTik.</p>
    """
    try:
        _send_email(receiver_email, "Mã OTP Xác Thực Tài Khoản", html)
        print(f"[SUCCESS] Đã gửi OTP thực tế thành công tới {receiver_email}")
    except Exception as e:
        print(f"[ERROR] Lỗi không thể gửi email: {e}")

# xác nhận OTP
def verify_otp_logic(db: Session, email: str, otp: str):
    # 1. Tìm user
    user = user_repo.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng!")
        
    if user.is_active:
        raise HTTPException(status_code=400, detail="Tài khoản đã được kích hoạt trước đó!")
        
    # 2. Check mã OTP
    if user.otp_code != otp:
        raise HTTPException(status_code=400, detail="Mã OTP không chính xác!")
        
    # 3. Check hạn sử dụng
    current_time = datetime.now(timezone.utc)
    expire_time = user.otp_expire_at.replace(tzinfo=timezone.utc) if user.otp_expire_at.tzinfo is None else user.otp_expire_at
    
    if current_time > expire_time:
        raise HTTPException(status_code=400, detail="Mã OTP đã hết hạn!")
        
    # 4. Logic mở khóa
    user.is_active = True
    user.otp_code = None
    user.otp_expire_at = None
    
    db.commit()
    db.refresh(user)

    return user

# gửi otp cấp lại pwd
def send_forgot_pwd_email(receiver_email: str, otp: str):
    """Gửi OTP cấp lại mật khẩu qua Resend Email API."""
    html = f"""
    <p>Xin chào,</p>
    <p>Hệ thống vừa nhận được yêu cầu khôi phục mật khẩu cho tài khoản của bạn.</p>
    <p>Mã OTP của bạn là: <strong>{otp}</strong></p>
    <p>Lưu ý: Mã này chỉ có hiệu lực trong vòng 5 phút. Nếu bạn không yêu cầu đổi mật khẩu, vui lòng bỏ qua email này!</p>
    """
    try:
        _send_email(receiver_email, "Yêu Cầu Khôi Phục Mật Khẩu", html)
        print(f"[SUCCESS] Đã gửi OTP khôi phục mật khẩu thành công tới {receiver_email}")
    except Exception as e:
        print(f"[ERROR] Lỗi gửi mail: {e}")
        
def forgot_password_logic(db: Session, email: str, background_tasks: BackgroundTasks):
    # 1. Tìm tài khoản
    user = user_repo.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản với email này!")
    
    if not user.is_active:
        raise HTTPException(
            status_code=403, 
            detail="Tài khoản của bạn chưa được xác thực. Vui lòng đăng ký lại hoặc xác thực OTP trước!"
        )
    if user.otp_expire_at:
        current_time = datetime.now(timezone.utc)
        # Đảm bảo đồng bộ múi giờ để không bị lỗi trừ thời gian
        expire_time = user.otp_expire_at.replace(tzinfo=timezone.utc) if user.otp_expire_at.tzinfo is None else user.otp_expire_at
        
        # Nếu thời gian sống còn lại lớn hơn 4 phút (240 giây)
        time_left = expire_time - current_time
        if time_left > timedelta(minutes=4):
            # Tính ra số giây khách phải đợi thêm (vd: còn 4 phút 50s -> bắt đợi 50s)
            wait_seconds = int(time_left.total_seconds() - 240)
            raise HTTPException(
                status_code=429, # HTTP 429 là chuẩn quốc tế cho việc "Spam"
                detail=f"Bạn gửi yêu cầu quá nhanh! Vui lòng đợi {wait_seconds} giây nữa rồi thử lại."
            )
    # 2. Sinh mã OTP mới (Tái sử dụng hàm cũ ở security)
    otp = generate_otp_code()
    user.otp_code = otp
    user.otp_expire_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    
    # 3. Lưu vào DB 
    db.commit()
    db.refresh(user)
    
    # 4. Nhờ BackgroundTasks gửi mail
    background_tasks.add_task(send_forgot_pwd_email, user.email, otp)
    return True

def reset_password_logic(db: Session, request: ResetPwdRequest):
    # 1. Tìm tài khoản
    user = user_repo.get_user_by_email(db, request.email)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng!")
        
    # 2. Kiểm tra OTP
    if user.otp_code != request.otp:
        raise HTTPException(status_code=400, detail="Mã OTP không chính xác!")
        
    # 3. Kiểm tra hạn sử dụng OTP
    current_time = datetime.now(timezone.utc)
    expire_time = user.otp_expire_at.replace(tzinfo=timezone.utc) if user.otp_expire_at.tzinfo is None else user.otp_expire_at
    if current_time > expire_time:
        raise HTTPException(status_code=400, detail="Mã OTP đã hết hạn!")
        
    # 4. THÀNH CÔNG: Băm mật khẩu mới đè lên mật khẩu cũ
    user.hashed_password = get_password_hash(request.new_password)
    
    # Dọn dẹp OTP
    user.otp_code = None
    user.otp_expire_at = None
    
    # Lưu xuống DB
    db.commit()
    db.refresh(user)
    
    return True

def resend_otp_logic(db: Session, email: str, background_tasks: BackgroundTasks):
    # 1. Tìm user
    user = user_repo.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản với email này!")
        
    # 2. Chốt chặn: Đã kích hoạt rồi thì không gửi nữa
    if user.is_active:
        raise HTTPException(
            status_code=400, 
            detail="Tài khoản này đã được kích hoạt thành công rồi. Vui lòng đăng nhập!"
        )
    if user.otp_expire_at:
        current_time = datetime.now(timezone.utc)
        # Đảm bảo đồng bộ múi giờ để không bị lỗi trừ thời gian
        expire_time = user.otp_expire_at.replace(tzinfo=timezone.utc) if user.otp_expire_at.tzinfo is None else user.otp_expire_at
        
        # Nếu thời gian sống còn lại lớn hơn 4 phút (240 giây)
        time_left = expire_time - current_time
        if time_left > timedelta(minutes=4):
            # Tính ra số giây khách phải đợi thêm (vd: còn 4 phút 50s -> bắt đợi 50s)
            wait_seconds = int(time_left.total_seconds() - 240)
            raise HTTPException(
                status_code=429, # HTTP 429 là chuẩn quốc tế cho việc "Spam"
                detail=f"Bạn gửi yêu cầu quá nhanh! Vui lòng đợi {wait_seconds} giây nữa rồi thử lại."
            )
    # 3. Sinh mã OTP mới (Tái sử dụng hàm cũ)
    new_otp = generate_otp_code()
    user.otp_code = new_otp
    user.otp_expire_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    
    # 4. Lưu cập nhật xuống DB
    db.commit()
    db.refresh(user)
    
    # 5. Gửi email ngầm (Tái sử dụng lại đúng cái hàm gửi mail lúc đăng ký)
    background_tasks.add_task(send_otp_email, user.email, new_otp)
    
    return True
