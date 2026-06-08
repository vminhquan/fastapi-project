import asyncio
import logging
from contextlib import suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

# Import cấu hình Database và các Models
from app.core.database import engine, Base, SessionLocal
from app.core.config import settings
from app.models.booking import Booking, BookingItem, Event, Film, Room, Seat, Ticket
from app.models.order import Order
from app.models.payment import Payment
from app.models.token import TokenBlacklist
from app.models.user import User

# Import các Router (các nhóm API)
from app.api.endpoints.users import user as user_api
from app.api.endpoints.rooms import room as room_api
from app.api.endpoints.events import event as event_api
from app.api.endpoints.films import film as film_api
from app.api.endpoints.bookings import booking as booking_api
from app.api.endpoints.chatbots import chatbot as chatbot_api
from app.api.endpoints.orders import order as order_api
from app.api.endpoints.payments import payment as payment_api
from app.services import booking_service

logger = logging.getLogger(__name__)
booking_cleanup_task: asyncio.Task | None = None

# Lệnh này sẽ tự động nhìn vào app/models và tạo bảng trong SQL Server nếu nó chưa tồn tại.
try:
    Base.metadata.create_all(bind=engine)
    if engine.dialect.name == "postgresql":
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TYPE ticketstatus "
                    "ADD VALUE IF NOT EXISTS 'EXPIRED'"
                )
            )
    logger.info("✅ Database tables created successfully")
except Exception as e:
    logger.error(f"❌ Database connection error: {e}")

# Khởi tạo app
app = FastAPI(
    title="API Hệ Thống Bán Vé QTIK",
    description="Backend FastAPI",
    version="1.0.0"
)

# Cho phép các trang web (HTML/JS, React, Vue) ở tên miền khác được phép gọi API này.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "https://qtik-frontend.onrender.com","https://qtik.io.vn",
    "https://www.qtik.io.vn",],  # Trong thực tế, bạn nên thay "*" bằng URL của web Frontend (VD: ["http://localhost:3000"])
    allow_credentials=True,
    allow_methods=["*"],  # Cho phép tất cả các lệnh GET, POST, PUT, DELETE
    allow_headers=["*"],  # Cho phép tất cả các Headers
)

# Gắn các nhóm API vào ứng dụng chính.
app.include_router(user_api.router, prefix="/api/users", tags=["Quản lý Người dùng"])
app.include_router(room_api.router, prefix="/api/rooms", tags=["Quản Lý Phòng chiếu"])
app.include_router(event_api.router, prefix="/api/events", tags=["Quản Lý Suất chiếu"])
app.include_router(film_api.router, prefix="/api/films", tags=["Quản Lý Phim"])
app.include_router(booking_api.router, prefix="/api/bookings", tags=["Quản Lý Đặt vé"])
app.include_router(order_api.router, prefix="/api/orders", tags=["Quản Lý Đơn hàng"])
app.include_router(payment_api.router, prefix="/api/payments", tags=["Quản Lý Thanh toán"])
app.include_router(chatbot_api.router, prefix="/api/chat", tags=["Trợ Lý Ảo AI"])

@app.on_event("startup")
def seed_admin_users():
    admin_emails = [
        email.strip().lower()
        for email in settings.ADMIN_EMAILS.split(",")
        if email.strip()
    ]
    if not admin_emails:
        return

    db = SessionLocal()
    try:
        users = db.query(User).filter(User.email.in_(admin_emails)).all()
        for user in users:
            if user.role != "admin":
                user.role = "admin"
        db.commit()
        logger.info("Seeded %s admin user(s)", len(users))
    finally:
        db.close()


def cleanup_expired_bookings_once():
    db = SessionLocal()
    try:
        cleaned_count = booking_service.cleanup_expired_bookings_logic(
            db,
            limit=500,
        )
        expired_ticket_count = booking_service.cleanup_expired_tickets_logic(
            db,
            limit=500,
        )
        if cleaned_count:
            logger.info("Released seats for %s expired booking(s)", cleaned_count)
        if expired_ticket_count:
            logger.info("Expired %s ticket(s)", expired_ticket_count)
    except Exception:
        logger.exception("Failed to clean up expired bookings")
    finally:
        db.close()


async def cleanup_expired_bookings_loop():
    interval = max(settings.BOOKING_CLEANUP_INTERVAL_SECONDS, 1)
    while True:
        await asyncio.to_thread(cleanup_expired_bookings_once)
        await asyncio.sleep(interval)


@app.on_event("startup")
async def start_booking_cleanup():
    global booking_cleanup_task
    if booking_cleanup_task is None or booking_cleanup_task.done():
        booking_cleanup_task = asyncio.create_task(
            cleanup_expired_bookings_loop()
        )


@app.on_event("shutdown")
async def stop_booking_cleanup():
    global booking_cleanup_task
    if booking_cleanup_task is None:
        return

    booking_cleanup_task.cancel()
    with suppress(asyncio.CancelledError):
        await booking_cleanup_task
    booking_cleanup_task = None


@app.get("/", tags=["Hệ thống"])
def read_root():
    return {
        "status": "Hoạt động bình thường",
        "message": "Chào mừng đến với hệ thống API của tôi!"
    }
