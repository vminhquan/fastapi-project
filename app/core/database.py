import urllib.parse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from app.core.config import settings

# SỬ DỤNG settings thay vì gõ cứng mật khẩu
encoded_password = urllib.parse.quote_plus(settings.DB_PASSWORD)

SQLALCHEMY_DATABASE_URL = f"mssql+pymssql://{settings.DB_USER}:{encoded_password}@{settings.DB_SERVER}:{settings.DB_PORT}/{settings.DB_NAME}"

# Khởi tạo Engine (giảm quá tải db, biên dịch câu lệnh SQL)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True, 
    pool_size=5,        
    max_overflow=10     
)

# Khởi tạo Session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Nền móng Models
Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


