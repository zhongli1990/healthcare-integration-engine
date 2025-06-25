from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SessionBase(BaseModel):
    """Base session schema."""
    user_id: str
    refresh_token: str
    expires_at: datetime
    is_revoked: bool = False


class SessionCreate(SessionBase):
    """Schema for creating a new session."""
    pass


class SessionUpdate(BaseModel):
    """Schema for updating a session."""
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    is_revoked: Optional[bool] = None


class SessionInDBBase(SessionBase):
    """Base session schema for database representation."""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Session(SessionInDBBase):
    """Session schema for API responses."""
    pass
