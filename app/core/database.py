import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# 1. Xác định thư mục gốc của project (fastapi-project)
# File này đang nằm ở app/core/database.py nên ta cần lùi 2 cấp (dirname 3 lần)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 2. Tạo chuỗi kết nối SQLite (File sẽ được tạo tên là fastapi-project-db.db)
SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'fastapi-project-db.db')}"

# 3. Khởi tạo Engine (Siêu nhẹ, không cần pool_size hay max_overflow)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False} # Cờ BẮT BUỘC khi dùng SQLite với FastAPI
)

# 4. Khởi tạo Session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 5. Nền móng Models
Base = declarative_base()

# 6. Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()