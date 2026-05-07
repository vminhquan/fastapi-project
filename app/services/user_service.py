from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.repositories.user import user_repo
from app.schemas import user as user_schema
from app.core.security import get_password_hash,verify_password, create_access_token


def register_new_user(db: Session, user_in: user_schema.UserCreate):
    # kiểm tra emai đã tồn tại chưa
    existing_user = user_repo.get_user_by_email(db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email này đã được sử dụng. Vui lòng chọn email khác!"
        )
    # Bảo mật
    hashed_pwd = get_password_hash(user_in.password)
    
    # Chuẩn bị dữ liệu để lưu
    user_data = {
        "email":user_in.email,
        "full_name": user_in.full_name,
        "hashed_password": hashed_pwd
    }
    
    # Gọi Repository để Insert vào Database
    created_user = user_repo.create_user(db, user_data)
    
    return created_user

def get_users(db: Session, skip: int = 0, limit: int = 100):
    # có thể thêm logic kiểm tra ở đây nếu cần (VD: limit không được vượt quá 1000)
    return user_repo.get_all_users(db, skip=skip, limit=limit)

def get_user_by_id(db: Session, user_id: int):
    return user_repo.get_user_by_id(db, user_id)

def update_user(db: Session, user_id: int, user_in: user_schema.UserUpdate):
    # Kiểm tra user tồn tại
    user = user_repo.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User không tồn tại!")
    
    # Chuẩn bị dữ liệu cập nhật
    user_data = {}
    
    if user_in.email:
        # Check email không trùng với user khác
        existing = user_repo.get_user_by_email(db, user_in.email)
        if existing and existing.id != user_id:
            raise HTTPException(status_code=400, detail="Email này đã được sử dụng. Vui lòng chọn email khác!")
        user_data["email"] = user_in.email
    
    if user_in.full_name:
        user_data["full_name"] = user_in.full_name
    
    if user_in.password:
        # Hash password mới
        hashed_pwd = get_password_hash(user_in.password)
        user_data["hashed_password"] = hashed_pwd
    
    # Nếu không có gì cập nhật
    if not user_data:
        return user
    
    # Update
    updated_user = user_repo.update_user(db, user_id, user_data)
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
    from app.core.security import verify_password, create_access_token
    
    # Tìm user theo email
    user = user_repo.get_user_by_email(db, email)
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Email hoặc mật khẩu không đúng!"
        )
    
    # Verify password
    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Email hoặc mật khẩu không đúng!"
        )
    
    # Tạo JWT token
    access_token = create_access_token(data={"sub": user.email})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name
        }
    }

def logout_user(db: Session, token: str):
    """Logout user - thêm token vào blacklist"""
    from jose import jwt
    from app.core.security import SECRET_KEY, ALGORITHM
    from app.repositories import token_repo
    from datetime import datetime
    
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