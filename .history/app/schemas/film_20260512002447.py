from pydantic import BaseModel, ConfigDict
from datetime import datetime
class FilmCreate(BaseModel):
    title: str
    duration: int
    description: str
    release_date: datetime
    