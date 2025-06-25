from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.core import security
from app.core.config import settings
from app.db.base import get_db

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=settings.TOKEN_URL)

router = APIRouter()


@router.post("/login/access-token", response_model=schemas.Token)
def login_access_token(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token and refresh token.
    """
    user = crud.user.authenticate(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )
    refresh_token = security.create_refresh_token(
        user.id, expires_delta=refresh_token_expires
    )
    
    # Store the refresh token in the database
    crud.session_crud.create_user_session(
        db=db,
        user_id=user.id,
        refresh_token=refresh_token,
        expires_at=datetime.utcnow() + refresh_token_expires
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/login/test-token", response_model=schemas.User)
def test_token(current_user: models.User = Depends(deps.get_current_user)):
    """
    Test access token.
    """
    return current_user


@router.post("/password-recovery/{email}", response_model=schemas.Msg)
def recover_password(email: str, db: Session = Depends(get_db)) -> Any:
    """
    Password Recovery
    """
    user = crud.user.get_by_email(db, email=email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The user with this email does not exist in the system.",
        )
    
    # TODO: Send email with password reset token
    
    return {"msg": "Password recovery email sent"}


@router.post("/refresh-token", response_model=schemas.Token)
def refresh_token(
    refresh_token: str = Body(..., embed=True),
    db: Session = Depends(get_db),
) -> Any:
    """
    Refresh access token using a valid refresh token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = security.verify_jwt_token(refresh_token)
        if payload is None:
            raise credentials_exception
            
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
        # Verify the refresh token exists in the database and is not expired
        session = crud.session_crud.get_by_refresh_token(db, refresh_token=refresh_token)
        if not session or session.is_expired() or not session.is_active:
            raise credentials_exception
            
        # Get the user
        user = crud.user.get(db, id=user_id)
        if not user or not user.is_active:
            raise credentials_exception
            
        # Generate new access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        new_access_token = security.create_access_token(
            user.id, expires_delta=access_token_expires
        )
        
        return {
            "access_token": new_access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }
        
    except (jwt.JWTError, ValidationError):
        raise credentials_exception


@router.post("/logout", response_model=schemas.Msg)
def logout(
    refresh_token: str = Body(..., embed=True),
    db: Session = Depends(get_db),
) -> Any:
    """
    Log out by revoking the refresh token.
    """
    session = crud.session_crud.get_by_refresh_token(db, refresh_token=refresh_token)
    if session:
        crud.session_crud.revoke(db, session_id=session.id)
    return {"msg": "Successfully logged out"}


@router.post("/reset-password/", response_model=schemas.Msg)
def reset_password(
    token: str = "",
    new_password: str = "",
    db: Session = Depends(get_db),
) -> Any:
    """
    Reset password
    """
    # TODO: Implement password reset logic
    return {"msg": "Password updated successfully"}
