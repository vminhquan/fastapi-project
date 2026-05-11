from pydantic import BaseModel, ConfigDict

class FilmCreate(Base):
    title: str
    duration: int
    description: str

