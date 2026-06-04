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

    GEMINI_API_KEY: str

    # Resend Email API
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = "QTIK Cinemas <onboarding@resend.dev>"

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
