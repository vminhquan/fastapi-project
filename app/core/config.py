from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Database config
    DB_SERVER: str
    DB_PORT: str
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    
    # JWT config 
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Báo cho Pydantic biết phải tự động tìm và đọc file .env
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# Khởi tạo đối tượng settings để các file khác gọi dùng
settings = Settings()