from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Column, String, Integer, TEXT, ForeignKey
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class UserTable(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)


class NewsTable(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, autoincrement=True)
    author_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    title = Column(String(255), nullable=False)
    text = Column(TEXT, nullable=True)


class User(BaseModel):
    id: int
    username: str
    password: str
    display_name: str


class UserCreateForm(BaseModel):
    username: str
    password: str
    display_name: str


class UserUpdateForm(BaseModel):
    display_name: Optional[str] = None
    username: Optional[str] = None


class News(BaseModel):
    id: int
    author_id: Optional[int] = None
    title: str
    text: Optional[str] = None


class NewsCreateForm(BaseModel):
    title: str
    text: Optional[str] = None
    author_id: Optional[int] = None


class NewsUpdateForm(BaseModel):
    title: str
    text: Optional[str] = None
