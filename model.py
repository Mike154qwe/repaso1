from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field
from pydantic import field_validator


class BookBase(SQLModel):
    name: str = Field(min_length=2, max_length=100)
    author: str = Field(min_length=2, max_length=100)
    pages: int = Field(gt=0, le=5000)
    available: bool = True
    language: str = Field(min_length=2, max_length=50)
    img: Optional[str] = None

    @field_validator("name", "author", "language")
    @classmethod
    def no_texto_vacio(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El campo no puede estar vacio")
        return value


class Book(BookBase, table=True):
    __tablename__ = "books"

    id: Optional[int] = Field(default=None, primary_key=True)
    created: datetime = Field(default_factory=datetime.utcnow)


class BookCreate(BookBase):
    pass


class BookUpdate(SQLModel):
    name: Optional[str] = None
    author: Optional[str] = None
    pages: Optional[int] = Field(default=None, gt=0, le=5000)
    available: Optional[bool] = None
    language: Optional[str] = None
    img: Optional[str] = None
