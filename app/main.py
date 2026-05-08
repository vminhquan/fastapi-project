from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# Import cấu hình Database và các Models
from app.core.database import engine, Base
from app.models import user, token, booking  

# Import các Router (các nhóm API)
from app.api.endpoints.users import user as user_api
from app.api.endpoints.rooms import room as room_api

logger = logging.getLogger(__name__)

# Lệnh này sẽ tự động nhìn vào app/models và tạo bảng trong SQL Server nếu nó chưa tồn tại.
try:
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables created successfully")
except Exception as e:
    logger.error(f"❌ Database connection error: {e}")

# Khởi tạo app
app = FastAPI(
    title="API Quản lý Bán hàng",
    description="Hệ thống Backend FastAPI kết nối SQL Server",
    version="1.0.0"
)

# Cho phép các trang web (HTML/JS, React, Vue) ở tên miền khác được phép gọi API này.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Trong thực tế, bạn nên thay "*" bằng URL của web Frontend (VD: ["http://localhost:3000"])
    allow_credentials=True,
    allow_methods=["*"],  # Cho phép tất cả các lệnh GET, POST, PUT, DELETE
    allow_headers=["*"],  # Cho phép tất cả các Headers
)

# Gắn các nhóm API vào ứng dụng chính.
app.include_router(user_api.router, prefix="/users", tags=["Quản lý Người dùng"])
app.include_router(room_api.router, prefix="/rooms", tags=["Quản Lý Phòng Chiếu"])

@app.get("/", tags=["Hệ thống"])
def read_root():
    return {
        "status": "Hoạt động bình thường",
        "message": "Chào mừng đến với hệ thống API của tôi!"
    }

