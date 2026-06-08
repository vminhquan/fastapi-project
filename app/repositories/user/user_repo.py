from uuid import UUID

from sqlalchemy.orm import Session
from app.models.user import User
from app.repositories.order import order_repo

def get_all_users(db: Session, skip: int = 0, limit: int = 100):
    users = db.query(User).order_by(User.id).offset(skip).limit(limit).all()
    return users

def create_user(db: Session, user_data: dict):
    # Ép cứng role là "user". 
    # Bất kể ở trên người dùng gửi cái gì xuống, đến đây đều bị đè lại thành "user" thường.
    user_data["role"] = "user"
    user_data["is_active"] = False
    # Lúc này bung **user_data ra là an toàn tuyệt đối 100%
    new_user = User(**user_data)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def get_user_by_id(db: Session, user_id: UUID):
    # Tìm user theo id
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    # Tìm user theo email
    return db.query(User).filter(User.email == email).first()

def get_my_orders(db: Session, current_user_id: UUID):
    return order_repo.get_orders_by_user_id(
        db=db,
        user_id=current_user_id,
    )

def save_user(db: Session, user: User):
    db.commit()
    db.refresh(user)
    return user

def update_user(db: Session, user_id: UUID, user_data: dict):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    
    # cập nhật các field
    for key, value in user_data.items():
        if hasattr(user, key):
            setattr(user, key, value)
            
    db.commit()
    db.refresh(user)
    
    return user

def delete_user(db: Session, user_id: UUID):
    # Tìm user trước
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        return False  # User không tồn tại
    
    # Xóa user
    db.delete(user)
    db.commit()
    
    return True
    
