from fastapi import APIRouter, Depends, Query, HTTPException, Header
from sqlalchemy.orm import Session
from app.schemas import user as user_schema
from app.services import user_service
from typing import List, Optional
from app.core.database import get_db
from app.core.security import security_scheme
from fastapi.security import HTTPAuthorizationCredentials

router = APIRouter()


@router.post("/", response_model=user_schema.UserResponse)
def register_endpoint(user_in: user_schema.UserCreate, db: Session = Depends(get_db)):
    # Lớp API chỉ cần đứng vẫy tay gọi Service ra làm việc
    return user_service.register_new_user(db, user_in)

# tự động tạo ra 2 ô nhập liệu là skip và limit.
# Nếu bạn muốn lấy trang 1 (10 người đầu tiên): Nhập skip=0, limit=10.
# Nếu bạn muốn lấy trang 2 (10 người tiếp theo): Nhập skip=10, limit=10.
@router.get("/", response_model=List[user_schema.UserResponse])
def read_all_users(
    skip: int = Query(0, description="Số lượng bản ghi muốn bỏ qua"),
    limit: int = Query(100, description="Số lượng bản ghi tối đa muốn lấy"),
    db: Session = Depends(get_db)
):
    users = user_service.get_users(db, skip=skip, limit=limit)
    return users

@router.get("/{user_id}", response_model=user_schema.UserResponse)
def read_user_by_id(user_id: int, db: Session = Depends(get_db)):
    # Lấy user theo ID
    user = user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User không tồn tại!"
        )
    return user

@router.put("/{user_id}", response_model=user_schema.UserResponse)
def update_user_endpoint(user_id: int, user_in: user_schema.UserUpdate, db: Session = Depends(get_db)):
    # Cập nhật user
    updated_user = user_service.update_user(db, user_id, user_in)
    return updated_user

@router.delete("/{user_id}")
def delete_user_endpoint(user_id: int, db: Session = Depends(get_db)):
    result = user_service.delete_user(db, user_id)
    return {"message": "User đã được xóa thành công", **result}

@router.post("/login", response_model=dict)
def login_endpoint(credentials: user_schema.UserLogin, db: Session = Depends(get_db)):
    result = user_service.login_user(db, credentials.email, credentials.password)
    return result

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
