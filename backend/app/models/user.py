from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from app.db.session import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(30), unique=True, index=True)
    hashed_password = Column(String(30))
    name = Column(String(20), index=True)
    created_at = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)
    # progress = Column(Integer, default=0) если понадобится, когда будем считать очки или что-то другое
