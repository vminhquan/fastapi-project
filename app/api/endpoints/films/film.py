from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.security import RoleChecker 
from app.schemas.film import FilmCreate, FilmResponse,FilmUpdate
from app.services import film_service

router = APIRouter()
admin_only = RoleChecker(["admin"])

@router.post("/", response_model=FilmResponse, dependencies=[Depends(admin_only)])
def create_film(film_in: FilmCreate, db: Session = Depends(get_db)):
    """[ADMIN] Tạo phim chiếu mới"""
    return film_service.create_new_film(db, film_in)

@router.put("/{film_id}", dependencies=[Depends(admin_only)])
def update_film(film_id: int, film_in: FilmUpdate,db: Session = Depends(get_db)):
    """[ADMIN] Cập nhật phim chiếu"""
    film_service.update_film_logic(db, film_id, film_in)
    return {"message": "Đã cập nhật phim chiếu thành công!"}

@router.delete("/{film_id}", dependencies=[Depends(admin_only)])
def delete_film(film_id: int, db: Session = Depends(get_db)):
    """[ADMIN] Xóa phim chiếu"""
    film_service.delete_film_logic(db, film_id)
    return {"message": "Đã xóa phim chiếu thành công!"}

@router.get("/", response_model=List[FilmResponse])
def read_all_films(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """[PUBLIC] Lấy danh sách phim (Không cần đăng nhập cũng xem được)"""
    return film_service.get_list_films(db, skip=skip, limit=limit)

@router.get("/{film_id}", response_model=FilmResponse)
def read_film_detail(film_id: int, db: Session = Depends(get_db)):
    """[PUBLIC] Xem chi tiết 1 phim"""
    return film_service.get_film_detail(db, film_id)