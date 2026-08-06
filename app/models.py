import uuid
from sqlalchemy import Column, String, DateTime, JSON, Uuid
from sqlalchemy.sql import func
from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    status = Column(
        String, nullable=False, default="pending"
    )  # pending, processing, completed, failed
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
