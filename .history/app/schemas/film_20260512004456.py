from pydantic import BaseModel, ConfigDict
from datetime import datetime

class FilmCreate(BaseModel):
    title: str
    duration: int
    description: str
    release_date: datetime
    poster_url: str

class FilmUpdate(FilmCreate):
    pass

class FilmResponse(FilmCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)
