from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4, UUID


@dataclass
class Message:
    """A message in the integration engine.
    
    This class represents a message that flows through the integration engine.
    It contains the message content, type, and metadata.
    """
    message_type: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    message_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the message to a dictionary.
        
        Returns:
            Dict containing the message data.
        """
        return {
            "message_id": self.message_id,
            "message_type": self.message_type,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create a Message from a dictionary.
        
        Args:
            data: Dictionary containing message data.
            
        Returns:
            A new Message instance.
        """
        return cls(
            message_type=data.get('message_type', ''),
            content=data.get('content', ''),
            metadata=data.get('metadata', {}),
            message_id=data.get('message_id', str(uuid4())),
            timestamp=datetime.fromisoformat(data.get('timestamp', datetime.utcnow().isoformat()))
        )


class MessageStatus(str, Enum):
    RECEIVED = "received"
    VALIDATED = "validated"
    TRANSFORMED = "transformed"
    ROUTED = "routed"
    SENT = "sent"
    FAILED = "failed"


@dataclass
class MessageHeader:
    message_id: UUID = field(default_factory=uuid4)
    correlation_id: Optional[UUID] = None
    message_type: str = ""
    source: str = ""
    destination: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    status: MessageStatus = MessageStatus.RECEIVED
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": str(self.message_id),
            "correlation_id": str(self.correlation_id) if self.correlation_id else None,
            "message_type": self.message_type,
            "source": self.source,
            "destination": self.destination,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "retry_count": self.retry_count,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MessageHeader':
        return cls(
            message_id=UUID(data.get('message_id', str(uuid4()))),
            correlation_id=UUID(data['correlation_id']) if data.get('correlation_id') else None,
            message_type=data.get('message_type', ''),
            source=data.get('source', ''),
            destination=data.get('destination', []),
            timestamp=datetime.fromisoformat(data.get('timestamp', datetime.utcnow().isoformat())),
            status=MessageStatus(data.get('status', MessageStatus.RECEIVED.value)),
            retry_count=data.get('retry_count', 0),
            metadata=data.get('metadata', {})
        )


@dataclass
class MessageBody:
    content_type: str
    content: Optional[Any] = None
    raw_content: Optional[Union[bytes, str]] = None
    schema_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content_type": self.content_type,
            "content": self.content,
            "raw_content": self.raw_content.decode('utf-8') if isinstance(self.raw_content, bytes) else self.raw_content,
            "schema_id": self.schema_id,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MessageBody':
        raw_content = data.get('raw_content')
        if raw_content and isinstance(raw_content, str):
            raw_content = raw_content.encode('utf-8')
        return cls(
            content_type=data.get('content_type', ''),
            content=data.get('content'),
            raw_content=raw_content,
            schema_id=data.get('schema_id'),
            metadata=data.get('metadata', {})
        )


@dataclass
class MessageEnvelope:
    header: MessageHeader
    body: MessageBody

    def to_dict(self) -> Dict[str, Any]:
        return {
            "header": self.header.to_dict(),
            "body": self.body.to_dict()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MessageEnvelope':
        return cls(
            header=MessageHeader.from_dict(data['header']),
            body=MessageBody.from_dict(data['body'])
        )

    def clone(self) -> 'MessageEnvelope':
        """Create a deep copy of the message."""
        return MessageEnvelope.from_dict(self.to_dict())
