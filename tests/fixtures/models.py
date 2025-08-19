from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Column, String, Integer, TEXT
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class News(BaseModel):
    id: int
    title: str
    text: Optional[str]


class OrmNews(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    text = Column(TEXT, nullable=True)


class NewsCreateForm(BaseModel):
    title: str
    text: Optional[str]


class NewsUpdateForm(BaseModel):
    title: str
    text: Optional[str]


class User(BaseModel):
    id: int
    username: str
    password: str
    display_name: str


class OrmUser(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), nullable=False)
    password = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)


class UserCreateForm(BaseModel):
    username: str
    password: str
    display_name: str


class UserUpdateForm(BaseModel):
    display_name: str
