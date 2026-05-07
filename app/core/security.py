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
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security_scheme), db: Session = Depends(get_db)):
    """Verify token và check blacklist"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
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
        
        return user_email
        
    except ExpiredSignatureError:
        # Bắt riêng lỗi hết hạn
        raise HTTPException(status_code=401, detail="Token đã hết hạn. Vui lòng đăng nhập lại!")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token không hợp lệ")