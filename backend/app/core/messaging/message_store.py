"""Message storage and retrieval with PostgreSQL and Redis caching."""
from typing import Dict, Any, Optional, List
import json
import logging
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import Column, String, Text, DateTime, JSON, create_engine, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy setup
Base = declarative_base()

class MessageModel(Base):
    """SQLAlchemy model for storing messages."""
    __tablename__ = "messages"
    
    id = Column(String(36), primary_key=True, index=True)
    message_id = Column(String(100), index=True)
    message_type = Column(String(50), index=True)
    status = Column(String(50), index=True)
    source_system = Column(String(100), index=True)
    destination_systems = Column(JSON)
    headers = Column(JSON)
    body = Column(Text)
    metadata_ = Column("metadata", JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MessageStore:
    """Handles message storage and retrieval with Redis caching."""
    
    def __init__(self, db_url: str = None, redis_url: str = None):
        # Database setup
        self.db_url = db_url or settings.SQLALCHEMY_DATABASE_URI
        self.engine = create_engine(self.db_url)
        self.SessionLocal = scoped_session(
            sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        )
        
        # Redis setup
        self.redis_url = redis_url or settings.REDIS_URL
        self.redis = redis.Redis.from_url(self.redis_url)
        self.cache_ttl = 3600  # 1 hour cache TTL
        
        # Create tables if they don't exist
        Base.metadata.create_all(bind=self.engine)
    
    def _get_session(self):
        """Get a new database session."""
        return self.SessionLocal()
    
    def _get_cache_key(self, message_id: str) -> str:
        """Generate a cache key for a message."""
        return f"message:{message_id}"
    
    async def store_message(self, message: Dict[str, Any]) -> str:
        """Store a message in the database and cache."""
        message_id = message.get('message_id') or str(uuid4())
        cache_key = self._get_cache_key(message_id)
        
        # Prepare message data
        message_data = {
            'id': str(uuid4()),
            'message_id': message_id,
            'message_type': message.get('message_type'),
            'status': message.get('status', 'received'),
            'source_system': message.get('source_system'),
            'destination_systems': message.get('destination_systems', []),
            'headers': message.get('headers', {}),
            'body': message.get('body'),
            'metadata_': message.get('metadata', {})
        }
        
        # Store in database
        db = self._get_session()
        try:
            db_message = MessageModel(**message_data)
            db.add(db_message)
            db.commit()
            db.refresh(db_message)
            
            # Update cache
            self.redis.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(message_data, default=str)
            )
            
            return str(db_message.id)
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to store message: {str(e)}")
            raise
        finally:
            db.close()
    
    async def get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a message by ID, checking cache first."""
        cache_key = self._get_cache_key(message_id)
        
        # Try cache first
        cached = self.redis.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # Fall back to database
        db = self._get_session()
        try:
            message = db.query(MessageModel)\
                .filter(MessageModel.message_id == message_id)\
                .first()
                
            if not message:
                return None
                
            # Convert to dict
            result = {
                'id': message.id,
                'message_id': message.message_id,
                'message_type': message.message_type,
                'status': message.status,
                'source_system': message.source_system,
                'destination_systems': message.destination_systems or [],
                'headers': message.headers or {},
                'body': message.body,
                'metadata': message.metadata_ or {},
                'created_at': message.created_at.isoformat() if message.created_at else None,
                'updated_at': message.updated_at.isoformat() if message.updated_at else None
            }
            
            # Update cache
            self.redis.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(result, default=str)
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to retrieve message {message_id}: {str(e)}")
            raise
        finally:
            db.close()
    
    async def update_message_status(
        self, 
        message_id: str, 
        status: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update a message's status and metadata."""
        cache_key = self._get_cache_key(message_id)
        
        db = self._get_session()
        try:
            # Get current metadata
            message = db.query(MessageModel).filter(
                MessageModel.message_id == message_id
            ).first()
            
            if not message:
                return False
                
            # Update status
            message.status = status
            
            # Update metadata by merging with existing
            current_metadata = message.metadata_ or {}
            new_metadata = {**current_metadata, **(metadata or {})}
            message.metadata_ = new_metadata
            
            # Commit changes
            db.commit()
            
            # Invalidate cache
            self.redis.delete(cache_key)
            
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update message {message_id}: {str(e)}")
            raise
        finally:
            db.close()
    
    async def search_messages(
        self,
        message_type: Optional[str] = None,
        status: Optional[str] = None,
        source_system: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Search for messages with optional filters."""
        db = self._get_session()
        try:
            query = db.query(MessageModel)
            
            if message_type:
                query = query.filter(MessageModel.message_type == message_type)
            if status:
                query = query.filter(MessageModel.status == status)
            if source_system:
                query = query.filter(MessageModel.source_system == source_system)
            
            messages = query.order_by(MessageModel.created_at.desc())\
                           .offset(offset).limit(limit).all()
            
            return [{
                'id': msg.id,
                'message_id': msg.message_id,
                'message_type': msg.message_type,
                'status': msg.status,
                'source_system': msg.source_system,
                'created_at': msg.created_at.isoformat() if msg.created_at else None,
                'updated_at': msg.updated_at.isoformat() if msg.updated_at else None
            } for msg in messages]
            
        except Exception as e:
            logger.error(f"Failed to search messages: {str(e)}")
            raise
        finally:
            db.close()

# Singleton instance for easy import
message_store = MessageStore()
