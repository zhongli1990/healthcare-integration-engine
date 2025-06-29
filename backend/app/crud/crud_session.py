from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.session import Session
from app.schemas.session import SessionCreate, SessionUpdate


class CRUDSession(CRUDBase[Session, SessionCreate, SessionUpdate]):
    def get_by_refresh_token(self, db: Session, *, refresh_token: str) -> Optional[Session]:
        """Get a session by refresh token."""
        return db.query(Session).filter(Session.token == refresh_token).first()
    
    def create_user_session(
        self, db: Session, *, user_id: str, refresh_token: str, expires_at: datetime
    ) -> Session:
        """Create a new user session."""
        from app.models.session import Session as SessionModel
        
        db_obj = SessionModel(
            user_id=user_id,
            token=refresh_token,
            expires_at=expires_at,
            is_active=True,
        )
        
        db.add(db_obj)
        try:
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except Exception as e:
            db.rollback()
            raise e
    
    def revoke(self, db: Session, *, session_id: str) -> Optional[Session]:
        """Revoke a session by ID."""
        session = self.get(db, id=session_id)
        if not session:
            return None
        session.is_active = False
        db.add(session)
        db.commit()
        db.refresh(session)
        return session
    
    def update_refresh_token(
        self, 
        db: Session, 
        *, 
        session_id: str, 
        new_refresh_token: str, 
        expires_at: datetime
    ) -> Optional[Session]:
        """Update a session's refresh token."""
        session = self.get(db, id=session_id)
        if not session:
            return None
        
        session.refresh_token = new_refresh_token
        session.expires_at = expires_at
        session.is_revoked = False
        
        db.add(session)
        db.commit()
        db.refresh(session)
        return session
    
    def revoke_all_user_sessions(self, db: Session, *, user_id: str) -> int:
        """Revoke all active sessions for a user."""
        result = db.query(Session).filter(
            Session.user_id == user_id,
            Session.is_revoked == False  # noqa
        ).update({"is_revoked": True})
        db.commit()
        return result


# Create a single instance of CRUDSession
session = CRUDSession(Session)
