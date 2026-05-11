from pydantic import BaseModel, ConfigDict
import os
class FilmCreate(BaseModel):
    title: str
    duration: int
    description: str

