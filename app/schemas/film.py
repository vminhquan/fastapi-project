from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from uuid import UUID

class FilmCreate(BaseModel):
    title: str
    genre: str | None = None
    duration: int
    description: str
    release_date: date
    poster_url: str

class FilmUpdate(FilmCreate):
    pass

class FilmResponse(FilmCreate):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FilmListResponse(BaseModel):
    items: list[FilmResponse]
    total: int
    page: int
    limit: int
