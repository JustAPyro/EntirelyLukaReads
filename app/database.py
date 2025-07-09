from datetime import date, datetime
from typing import List

from flask_login import UserMixin
from sqlalchemy import (DECIMAL, JSON, Boolean, Column, Date, DateTime, Enum,
                        ForeignKey, String, Table, event)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from werkzeug.security import check_password_hash, generate_password_hash


class Base(DeclarativeBase):
    pass

class User(Base, UserMixin):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)

    email: Mapped[str] = mapped_column(String(36))
    password: Mapped[str] = mapped_column(String(150))

    created_on: Mapped[datetime] = mapped_column(server_default=func.now())
    last_login: Mapped[datetime] = mapped_column(server_default=func.now())
    last_activity: Mapped[datetime] = mapped_column(server_default=func.now())

    produced: Mapped[List['Books']] = relationship()

    def check_pass(self, password: str):
        return check_password_hash(self.password, password)

    @staticmethod
    def hash_pass(password: str):
        return generate_password_hash(password, method='pbkdf2')


class Progress(Base):
    __tablename__ = 'progress'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    book_id: Mapped[int] = mapped_column(ForeignKey('books.id'))
    chapter: Mapped['Segment'] = relationship()
    chapter_id: Mapped[int] = mapped_column(ForeignKey('segments.id'))
    timestamp: Mapped[int] = mapped_column()


book_access = Table(
    'book_access',
    Base.metadata,
    Column('book_id', ForeignKey('books.id')),
    Column('user_id', ForeignKey('users.id'))
)



class Books(Base):
    __tablename__ = 'books'
    id: Mapped[int] = mapped_column(primary_key=True)


    chapters: Mapped[List['Segment']] = relationship()
    title: Mapped[str] = mapped_column(String(128))
    author: Mapped[str] = mapped_column(String(128))
    producer_id: Mapped[int] = mapped_column(ForeignKey('users.id'))

class Segment(Base):
    __tablename__ = 'segments'
    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey('books.id'))
    title: Mapped[str] = mapped_column(String(200))
    position: Mapped[int] = mapped_column()
    audio_url: Mapped[str] = mapped_column(String(255), nullable=True)
    length: Mapped[str] = mapped_column(String(50), nullable=True)
    commentary: Mapped[bool] = mapped_column()
