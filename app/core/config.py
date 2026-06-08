from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Database config
    # DB_SERVER: str
    # DB_PORT: str
    # DB_NAME: str
    # DB_USER: str
    # DB_PASSWORD: str
    
    # JWT config 
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    GEMINI_API_KEY: str = ""
    CHATGPT_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    DATABASE_URL: str
    DIRECT_DATABASE_URL: str = ""

    # payOS
    PAYOS_CLIENT_ID: str = ""
    PAYOS_API_KEY: str = ""
    PAYOS_CHECKSUM_KEY: str = ""
    PAYOS_BASE_URL: str = ""
    PAYOS_RETURN_URL: str = ""
    PAYOS_CANCEL_URL: str = ""
    PAYOS_REQUEST_TIMEOUT: int = 15
    BOOKING_HOLD_MINUTES: int = 5
    BOOKING_CLEANUP_INTERVAL_SECONDS: int = 15
    APP_TIMEZONE: str = "Asia/Ho_Chi_Minh"

    # Resend Email API
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = ""

    # Email được tự động nâng quyền admin, phân tách bằng dấu phẩy nếu có nhiều email
    ADMIN_EMAILS: str = ""
    
    # Báo cho Pydantic biết phải tự động tìm và đọc file .env
    model_config = SettingsConfigDict(
        env_file=".env",              # Chỉ cần ghi tên file, Pydantic sẽ tự động tìm ở thư mục gốc
        env_file_encoding="utf-8",
        extra="ignore"                # Rất quan trọng: Bỏ qua nếu có biến môi trường thừa trên Server
    )

# Khởi tạo đối tượng settings để các file khác gọi dùng
settings = Settings()
