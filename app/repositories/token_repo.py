from sqlalchemy.orm import Session
from app.models.token import TokenBlacklist

def add_to_blacklist(db: Session, token: str, user_email: str, expires_at):
    """Thêm token vào blacklist"""
    blacklist_entry = TokenBlacklist(
        token=token,
        user_email=user_email,
        expires_at=expires_at
    )
    db.add(blacklist_entry)
    db.commit()
    db.refresh(blacklist_entry)
    return blacklist_entry

def is_token_blacklisted(db: Session, token: str) -> bool:
    """Kiểm tra token có bị blacklist không (Đã tối ưu RAM)"""
    # Chỉ select cột ID để truy vấn siêu nhanh
    blacklist_entry = db.query(TokenBlacklist.id).filter(
        TokenBlacklist.token == token
    ).first()
    return blacklist_entry is not None
