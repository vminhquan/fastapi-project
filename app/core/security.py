import bcrypt
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError, ExpiredSignatureError
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.repositories import token_repo
from app.repositories.user import user_repo
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security_scheme = HTTPBearer()
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

def get_password_hash(password: str) -> str:
    # Chuyển string thành byte, băm nó, rồi chuyển ngược lại thành chuỗi để lưu DB
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_password.decode('utf-8')
    
def verify_password(plain_password: str, hashed_password: str) -> bool:
    # so sánh password khi nhập vào với pwd hashed trong db
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )
    
def create_access_token(data: dict, expires_delta: timedelta = None):
    """Tạo JWT token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt

# refresh token
def create_refresh_token(data: dict):
    """Tạo Refresh Token có hạn 7 ngày"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    
    # đóng dấu "refresh"
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt

def verify_and_refresh_token(refresh_token: str, db: Session) -> str:
    """Xử lý logic giải mã thẻ Refresh và cấp thẻ Access mới"""
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Token không hợp lệ!")
            
        user_email = payload.get("sub")
        user = user_repo.get_user_by_email(db, email=user_email)
        
        if not user:
            raise HTTPException(status_code=401, detail="Người dùng không tồn tại!")
            
        new_access_token = create_access_token(
            data={"sub": user.email, "role": user.role}
        )
        return new_access_token
        
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh Token đã hết hạn. Vui lòng đăng nhập lại!")
    except JWTError:
        raise HTTPException(status_code=401, detail="Refresh Token không hợp lệ!")
    
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security_scheme), db: Session = Depends(get_db)):
    """Verify token và check blacklist"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, 
                                detail="Vui lòng sử dụng Access Token!"
                                )
        user_email: str = payload.get("sub")
        
        if user_email is None:
            raise HTTPException(status_code=401, detail="Token không chứa thông tin user")
        
        # 1. Check blacklist
        if token_repo.is_token_blacklisted(db, token):
            raise HTTPException(
                status_code=401,
                detail="Tài khoản đã đăng xuất. Vui lòng đăng nhập lại!"
            )
            
        # 2. Truy vấn User từ Database 
        user = user_repo.get_user_by_email(db, email=user_email)
        if user is None:
            raise HTTPException(status_code=401, detail="Không tìm thấy người dùng này")
        
        return user
        
    except ExpiredSignatureError:
        # Bắt riêng lỗi hết hạn
        raise HTTPException(status_code=401, detail="Token đã hết hạn. Vui lòng đăng nhập lại!")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token không hợp lệ")
    
class RoleChecker:
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles
    def __call__(self, current_user = Depends(get_current_user)):
        # current_user lúc này là Object User mà hàm cũ trả về
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=403, 
                detail="Bạn không có quyền thực hiện hành động này!"
            )
        return current_user

# Tạo sẵn các "chốt chặn" phổ biến
admin_only = RoleChecker(["admin"])
any_user = RoleChecker(["admin", "user"])