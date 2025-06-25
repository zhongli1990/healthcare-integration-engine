import os
import sys
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text, DDL
from sqlalchemy.orm import sessionmaker, Session

# Add the backend directory to the Python path
sys.path.append(str(Path(__file__).parent))

from app.core.config import settings
from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.user import User

# Use the test database URL with test schema
SQLALCHEMY_DATABASE_URL = f"{settings.DATABASE_URL}?options=-c%20search_path%3D{settings.TEST_SCHEMA}"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Set the SQLALCHEMY_DATABASE_URI in settings for the test environment
settings.SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URL

# Create and drop test schema for tests
@pytest.fixture(scope="session", autouse=True)
def setup_database():
    # Create test schema
    with engine.connect() as conn:
        # Drop and recreate the schema to ensure a clean state
        conn.execute(text(f'DROP SCHEMA IF EXISTS {settings.TEST_SCHEMA} CASCADE'))
        conn.execute(text(f'CREATE SCHEMA {settings.TEST_SCHEMA}'))
        conn.commit()
    
    # Set search path for the connection
    event.listen(engine, 'connect', 
        lambda conn, _: conn.execute(
            text(f'SET search_path TO {settings.TEST_SCHEMA}'))
    )
    
    # Import all models to ensure they are registered with SQLAlchemy
    from app.models.user import User
    from app.models.session import Session
    
    # Create all tables in the test schema
    with engine.connect() as conn:
        # Set the search path for this connection
        conn.execute(text(f'SET search_path TO {settings.TEST_SCHEMA}'))
        conn.commit()
        
        # Create all tables
        Base.metadata.create_all(bind=conn)
        conn.commit()
    
    yield  # This is where the testing happens
    
    # Clean up after tests are done
    with engine.connect() as conn:
        # Drop all tables
        Base.metadata.drop_all(bind=conn)
        conn.commit()
        
        # Drop the schema
        conn.execute(text(f'DROP SCHEMA IF EXISTS {settings.TEST_SCHEMA} CASCADE'))
        conn.commit()

# Create a fresh database session for each test
@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    # Start a savepoint for nested transactions
    nested = connection.begin_nested()
    
    # If the application code calls session.commit, it will end the nested
    # transaction. We need to start a new one when that happens.
    @event.listens_for(session, 'after_transaction_end')
    def restart_savepoint(session, transaction):
        nonlocal nested
        if not nested.is_active and not connection.in_nested_transaction():
            nested = connection.begin_nested()
    
    yield session
    
    # Cleanup
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db):
    """Create a test client that uses the override_get_db fixture."""
    # Override the get_db dependency
    def override_get_db():
        try:
            yield db
        finally:
            pass  # Don't close the session here, it's managed by the db fixture
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    
    # Clean up
    app.dependency_overrides.clear()

@pytest.fixture
def test_user(db):
    """Create a test123 user with known credentials."""
    from app.schemas.user import UserCreate
    from app.crud import user as crud_user
    
    email = "test123@example.com"
    password = "test123password"
    
    # Check if user already exists and clean up if needed
    existing_user = crud_user.get_by_email(db, email=email)
    if existing_user:
        db.delete(existing_user)
        db.commit()
    
    # Create user using CRUD to ensure proper password hashing
    user_in = UserCreate(
        email=email,
        password=password,
        full_name="Test User 123"
    )
    
    user = crud_user.create(db, obj_in=user_in)
    
    # Verify the user was created and password is hashed
    db_user = crud_user.get_by_email(db, email=email)
    assert db_user is not None, "Test123 user was not created in the database"
    assert db_user.email == email.lower()  # Email should be normalized to lowercase
    assert db_user.hashed_password != password  # Password should be hashed
    
    # Add the plain password to the returned user object for testing
    db_user.plain_password = password
    
    # Clean up after test
    yield db_user
    
    # Remove the test user
    db.delete(db_user)
    db.commit()
