from pydantic import BaseModel, ConfigDict
from datetime import date

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
    id: int

    model_config = ConfigDict(from_attributes=True)
