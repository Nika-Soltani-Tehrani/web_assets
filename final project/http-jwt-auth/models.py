from sqlalchemy.sql import func
from sqlalchemy import DateTime, ForeignKey, String, Integer, Boolean, Column
from sqlalchemy.orm import relationship


class Users:
    id = Column('id', Integer, primary_key=True)
    username = Column(String(255))
    password = Column(String(255))
    is_admin = Column(Boolean)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    urls = relationship("URLs", back_populates="user")


class URLs:
    id = Column('id', Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey(Users.id))
    address = Column(String(255))
    threshold = Column(Integer)
    checking_seconds = Column(Integer)
    last_checking_date = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("Users", back_populates="urls")
    requests = relationship("Requests", back_populates="url")


class Requests:
    id = Column('id', Integer, primary_key=True)
    url_id = Column(Integer, ForeignKey(URLs.id))
    result = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    url = relationship("URLs", back_populates="requests")
