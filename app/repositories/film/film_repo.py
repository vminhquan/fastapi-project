from uuid import UUID

from sqlalchemy.orm import Session
from app.models.booking import Film
from app.schemas.film import FilmCreate


def _escape_like(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def get_all_films(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    is_hot: bool | None = None,
):
    """Lấy danh sách phim, chỉ tìm kiếm theo tên phim."""
    query = db.query(Film)
    if search:
        query = query.filter(
            Film.title.ilike(f"%{_escape_like(search)}%", escape="\\")
        )
    if is_hot is not None:
        query = query.filter(Film.is_hot.is_(is_hot))

    total = query.count()
    films = (
        query.order_by(
            Film.created_at.desc(),
            Film.release_date.desc(),
            Film.id.desc(),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )
    return films, total


def get_hot_films(db: Session, limit: int = 8):
    return (
        db.query(Film)
        .filter(Film.is_hot.is_(True))
        .order_by(
            Film.created_at.desc(),
            Film.release_date.desc(),
            Film.id.desc(),
        )
        .limit(limit)
        .all()
    )


def count_hot_films(db: Session) -> int:
    return db.query(Film).filter(Film.is_hot.is_(True)).count()


def get_film_by_id(db: Session, film_id: UUID):
    "Lấy film theo id film"
    return db.query(Film).filter(Film.id == film_id).first()

def get_film_by_title(db: Session, film_name: str):
    "Lấy film theo tên film"
    return db.query(Film).filter(Film.title == film_name).first()

def update_film(db: Session, film_id: UUID, film_data: dict):
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

def delete_film(db: Session, film_id: UUID):
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
