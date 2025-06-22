from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from app.core.config import get_settings
from enum import Enum as PyEnum

settings = get_settings()

class MessageStatus(PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    ERROR = "error"

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    integration_id = Column(Integer, ForeignKey("integrations.id"))
    protocol = Column(String, nullable=False)
    original_message = Column(JSON, nullable=False)
    processed_message = Column(JSON)
    error = Column(String)
    status = Column(Enum(MessageStatus), default=MessageStatus.PENDING)
    timestamp = Column(DateTime, nullable=False)

    integration = relationship("Integration", back_populates="messages")

    async def save(self):
        """
        Save message to database
        """
        from app.db.session import SessionLocal
        
        async with SessionLocal() as db:
            db.add(self)
            await db.commit()
            await db.refresh(self)
            return self

    @classmethod
    async def get(cls, message_id: int):
        """
        Get message by ID
        """
        from app.db.session import SessionLocal
        
        async with SessionLocal() as db:
            return await db.get(cls, message_id)

    @classmethod
    async def get_by_integration(
        cls,
        integration_id: int,
        status: Optional[MessageStatus] = None,
        limit: int = 100
    ):
        """
        Get messages for a specific integration
        """
        from app.db.session import SessionLocal
        
        async with SessionLocal() as db:
            query = db.query(cls).filter(cls.integration_id == integration_id)
            if status:
                query = query.filter(cls.status == status)
            return await query.order_by(cls.timestamp.desc()).limit(limit).all()
