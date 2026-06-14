from sqlalchemy.orm import Session
from sqlalchemy import text
from uuid import UUID
from fastapi import HTTPException
from app.models.booking import Event
from app.schemas.film import FilmCreate, FilmUpdate
from app.repositories.film import film_repo
from datetime import date, datetime

MAX_HOT_FILMS = 8
HOT_FILMS_LOCK_ID = 741852


def _ensure_hot_slot(db: Session):
    db.execute(
        text("SELECT pg_advisory_xact_lock(:lock_id)"),
        {"lock_id": HOT_FILMS_LOCK_ID},
    )
    if film_repo.count_hot_films(db) >= MAX_HOT_FILMS:
        raise HTTPException(
            status_code=409,
            detail=(
                "Đã đủ 8 phim hot. Hãy bỏ chọn một phim hot trước "
                "khi thêm phim khác."
            ),
        )


def create_new_film(db: Session, film_in: FilmCreate):
    """Logic tạo phim mới"""
    existing_film = film_repo.get_film_by_title(db, film_in.title)

    if existing_film:
        raise HTTPException(
            status_code=400,
            detail=f"Phim mang tên '{film_in.title}' đã tồn tại!"
        )

    if film_in.release_date < date.today():
        raise HTTPException(
            status_code=400,
            detail="Không hợp lệ! Ngày công chiếu không được nằm trong quá khứ."
        )

    if film_in.is_hot:
        _ensure_hot_slot(db)

    return film_repo.create_film(db, film_in.model_dump())

def get_list_films(
    db: Session,
    *,
    page: int = 1,
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    is_hot: bool | None = None,
):
    """Logic lấy danh sách phim"""
    normalized_search = " ".join((search or "").split()) or None
    films, total = film_repo.get_all_films(
        db,
        skip=skip,
        limit=limit,
        search=normalized_search,
        is_hot=is_hot,
    )
    return {
        "items": films,
        "total": total,
        "page": page,
        "limit": limit,
    }

def get_film_detail(db: Session, film_id: UUID):
    """Logic lấy film theo id"""
    film = film_repo.get_film_by_id(db, film_id)

    if not film:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy phim này!"
        )
    return film


def get_hot_films(db: Session):
    return film_repo.get_hot_films(db, limit=MAX_HOT_FILMS)

def update_film_logic(db: Session, film_id: UUID, film_in: FilmUpdate):
    """Logic cập nhật phim"""
    film = film_repo.get_film_by_id(db, film_id)

    if not film:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy phim này!"
        ) 
    
    film_data = {}

    # xử lí đổi tên film
    if film_in.title and film_in.title != film.title:
        existing_film = film_repo.get_film_by_title(db, film_in.title)
        if existing_film:
            raise HTTPException(
                status_code=400,
                detail=f"Tên phim '{film_in.title}' đã tồn tại!"
            )
        film_data["title"] = film_in.title

    # xử lí đổi mô tả
    if film_in.description and film_in.description != film.description:
        film_data["description"] = film_in.description

    if film_in.genre is not None and film_in.genre != film.genre:
        film_data["genre"] = film_in.genre

    if film_in.duration and film_in.duration != film.duration:
        film_data["duration"] = film_in.duration

    if film_in.poster_url and film_in.poster_url != film.poster_url:
        film_data["poster_url"] = film_in.poster_url

    if film_in.is_hot and not film.is_hot:
        _ensure_hot_slot(db)
    if film_in.is_hot != film.is_hot:
        film_data["is_hot"] = film_in.is_hot

    # xử lí đổi ngày công chiếu
    if film_in.release_date and film_in.release_date != film.release_date:
        if film_in.release_date < date.today():
            raise HTTPException(
                status_code=400, 
                detail="Không hợp lệ! Ngày công chiếu không được nằm trong quá khứ."
            )
        film_data["release_date"] = film_in.release_date

    if not film_data:
        return film
    
    # lưu vào db
    updated_film = film_repo.update_film(db, film_id, film_data)

    return updated_film

def delete_film_logic(db: Session, film_id: UUID):
    """Logic xoá phim - Kèm chốt chặn an toàn"""
    film = film_repo.get_film_by_id(db, film_id)
    if not film:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy phim này!"
        )
    
    # --- CHỐT CHẶN NGHIỆP VỤ ---
    now = datetime.now()
    
    # Chặn nếu phim ĐANG CHIẾU hoặc SẮP CHIẾU
    # tìm xem có suất chiếu nào của phim này mà giờ kết thúc vẫn ở trong tương lai không
    active_event = db.query(Event).filter(
        Event.film_id == film_id,
        Event.end_time >= now
    ).first()
    
    if active_event:
        raise HTTPException(
            status_code=400,
            detail="Không thể xoá! Bộ phim này đang có suất chiếu hoặc sắp được chiếu."
        )

    # Chặn xoá NGAY CẢ KHI phim đã chiếu xong từ lâu
    # Lý do: Nếu bạn xoá phim, các vé cũ khách đã mua trong quá khứ sẽ bị mất data (hoặc báo lỗi Database).s
    has_history = db.query(Event).filter(Event.film_id == film_id).first()
    if has_history:
        raise HTTPException(
            status_code=400,
            detail="Không thể xoá phim đã từng được lên lịch chiếu để bảo vệ dữ liệu lịch sử vé!"
        )
   

    return film_repo.delete_film(db, film_id)
