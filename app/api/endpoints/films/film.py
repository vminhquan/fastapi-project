from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.core.security import RoleChecker 
from app.schemas.film import (
    FilmCreate,
    FilmListResponse,
    FilmResponse,
    FilmUpdate,
)
from app.services import film_service

router = APIRouter()
admin_only = RoleChecker(["admin"])

@router.post("/", response_model=FilmResponse, dependencies=[Depends(admin_only)])
def create_film(film_in: FilmCreate, db: Session = Depends(get_db)):
    """[ADMIN] Tạo phim chiếu mới"""
    return film_service.create_new_film(db, film_in)

@router.put("/{film_id}", response_model=FilmResponse, dependencies=[Depends(admin_only)])
def update_film(film_id: UUID, film_in: FilmUpdate, db: Session = Depends(get_db)):
    """[ADMIN] Cập nhật phim chiếu"""
    return film_service.update_film_logic(db, film_id, film_in)

@router.delete("/{film_id}", dependencies=[Depends(admin_only)])
def delete_film(film_id: UUID, db: Session = Depends(get_db)):
    """[ADMIN] Xóa phim chiếu"""
    film_service.delete_film_logic(db, film_id)
    return {"message": "Đã xóa phim chiếu thành công!"}

@router.get("/", response_model=FilmListResponse)
def read_all_films(
    page: int = Query(1, ge=1),
    skip: int | None = Query(None, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: str | None = Query(None, max_length=255),
    db: Session = Depends(get_db),
):
    """[PUBLIC] Lấy danh sách phim (Không cần đăng nhập cũng xem được)"""
    offset = skip if skip is not None else (page - 1) * limit
    return film_service.get_list_films(
        db,
        page=page,
        skip=offset,
        limit=limit,
        search=search,
    )

@router.get("/{film_id}", response_model=FilmResponse)
def read_film_detail(film_id: UUID, db: Session = Depends(get_db)):
    """[PUBLIC] Xem chi tiết 1 phim"""
    return film_service.get_film_detail(db, film_id)
