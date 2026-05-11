from pydantic import BaseModel, ConfigDict

class FilmCreate():
    title: str
    duration: int
    description: str
