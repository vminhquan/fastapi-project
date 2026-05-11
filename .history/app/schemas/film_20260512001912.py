from pydantic import BaseModel, ConfigDict

class FilmCreate(BaseModel):
    title: str
    duration: int
    description: str

