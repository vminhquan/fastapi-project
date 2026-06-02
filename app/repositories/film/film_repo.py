from sqlalchemy.orm import Session
from app.models.booking import Film
from app.schemas.film import FilmCreate

def get_all_films(db: Session, skip: int = 0, limit: int = 100):
    """Lấy tất cả danh sách phim"""
    return db.query(Film).order_by(Film.id).offset(skip).limit(limit).all()

def get_film_by_id(db: Session, film_id: int):
    "Lấy film theo id film"
    return db.query(Film).filter(Film.id == film_id).first()

def get_film_by_title(db: Session, film_name: str):
    "Lấy film theo tên film"
    return db.query(Film).filter(Film.title == film_name).first()

def update_film(db: Session, film_id: int, film_data: dict):
    """Cập nhật thông tin của phim theo id"""
    film = db.query(Film).filter(Film.id == film_id).first()
    if not film:
        return None
    
    # Cập nhật các field
    for key, value in film_data.items():
        if hasattr(film, key) and value is not None:
            setattr(film, key, value)
    
    db.commit()
    db.refresh(film)
    
    return film

def delete_film(db: Session, film_id: int):
    film = db.query(Film).filter(Film.id == film_id).first()
    if not film:
        return False
    db.delete(film)
    db.commit()

    return True

def create_film(db: Session, film_data: dict):
    "Tạo mới phim"
    new_film = Film(**film_data)
    db.add(new_film)
    db.commit()
    db.refresh(new_film)
    
    return new_film
