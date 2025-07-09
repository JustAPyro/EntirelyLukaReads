import os
from datetime import date, datetime
from typing import List

import boto3
from botocore.client import Config
from flask_login import UserMixin
from sqlalchemy import (DECIMAL, JSON, Boolean, Column, Date, DateTime, Enum,
                        ForeignKey, String, Table, event)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

# Set these appropriately
r2_client = boto3.client(
    's3',
    endpoint_url=os.getenv('ELR_AWS_URL'),
    aws_access_key_id=os.getenv('ELR_AWS_ACCESS'),
    aws_secret_access_key=os.getenv('ELR_AWS_SECRET'),
    region_name='auto',
    config=Config(signature_version='s3v4')  # This forces SigV4
)

def upload_to_r2(file, segment):
    filename = secure_filename(file.filename)
    r2_key = f'{os.getenv('ELR_STATE')}/books/{segment.book_id}/segments/{segment.id}/{filename}'

    r2_client.upload_fileobj(
        file,
        Bucket='elr',
        Key=r2_key,
        ExtraArgs={'ContentType': file.mimetype},
    )

    # Store the key or full URL
    segment.audio_url = r2_key


class Base(DeclarativeBase):
    pass

book_access = Table(
    'book_access',
    Base.metadata,
    Column('book_id', ForeignKey('books.id')),
    Column('user_id', ForeignKey('users.id'))
)

chapter_access = Table(
    'chapter_access',
    Base.metadata,
    Column('segment_id', ForeignKey('segments.id')),
    Column('user_id', ForeignKey('users.id'))
)


class User(Base, UserMixin):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)

    email: Mapped[str] = mapped_column(String(36))
    password: Mapped[str] = mapped_column(String(150))

    created_on: Mapped[datetime] = mapped_column(server_default=func.now())
    last_login: Mapped[datetime] = mapped_column(server_default=func.now())
    last_activity: Mapped[datetime] = mapped_column(server_default=func.now())

    available: Mapped[List['Books']] = relationship(secondary=book_access, back_populates='users')
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





class Books(Base):
    __tablename__ = 'books'
    id: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str] = mapped_column(String(1024))
    chapters: Mapped[List['Segment']] = relationship(back_populates='book')
    title: Mapped[str] = mapped_column(String(128))
    author: Mapped[str] = mapped_column(String(128))
    producer_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    users: Mapped[List['User']] = relationship(secondary=book_access, back_populates='available')

class Segment(Base):
    __tablename__ = 'segments'
    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey('books.id'))
    book: Mapped['Books'] = relationship(back_populates='chapters')
    title: Mapped[str] = mapped_column(String(200))
    position: Mapped[int] = mapped_column()
    audio_url: Mapped[str] = mapped_column(String(255), nullable=True)
    length: Mapped[str] = mapped_column(String(50), nullable=True)
    commentary: Mapped[bool] = mapped_column()
    users: Mapped[List['User']] = relationship(secondary=chapter_access)
    
    def generate_url(self):
        return r2_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': 'elr', 'Key': self.audio_url},
            ExpiresIn=3600  # URL valid for 1 hour
    )
