from sqlalchemy import Column, String, Enum, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    status = Column(Enum("ACTIVE", "BLOCKED", name="user_status"), default="ACTIVE")
    last_login = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, server_default=func.now())

    roles = relationship("UserRole", backref="user", cascade="all, delete-orphan", lazy="selectin")
