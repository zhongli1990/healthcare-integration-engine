#!/usr/bin/env python3
"""
Script to create a superuser account.
Run with: docker compose exec backend python /app/scripts/create_superuser.py <email> <password>
"""
import sys
import bcrypt
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash
from app.crud.crud_user import user as user_crud
from app.db.base import Base, SessionLocal, engine
from app.models.user import User
from app.schemas.user import UserCreate

# Workaround for bcrypt import issues
try:
    import bcrypt
except ImportError:
    import sys
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "bcrypt==4.3.0"])
    import bcrypt

def init_db() -> None:
    """Initialize the database."""
    Base.metadata.create_all(bind=engine)

def create_superuser(
    db: Session, 
    email: str, 
    password: str, 
    full_name: str = "Admin User"
) -> User:
    """Create a superuser account."""
    # Check if user already exists
    existing_user = user_crud.get_by_email(db, email=email)
    if existing_user:
        print(f"User with email {email} already exists.")
        return existing_user
    
    # Create superuser
    hashed_password = get_password_hash(password)
    db_user = User(
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        is_superuser=True,
        is_active=True
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    print(f"Superuser created successfully with ID: {db_user.id}")
    return db_user

def main() -> None:
    """Main function to create a superuser."""
    if len(sys.argv) != 3:
        print("Usage: python create_superuser.py <email> <password>")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    
    print("Initializing database...")
    init_db()
    
    print(f"Creating superuser with email: {email}")
    db = SessionLocal()
    try:
        user = create_superuser(db, email=email, password=password)
        if not user:
            print("Failed to create superuser.")
            sys.exit(1)
    except Exception as e:
        print(f"Error creating superuser: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
