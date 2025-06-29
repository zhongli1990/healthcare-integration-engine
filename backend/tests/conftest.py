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
    print("\n=== Setting up test database ===")
    # Create test schema
    with engine.connect() as conn:
        print(f"Dropping and recreating schema: {settings.TEST_SCHEMA}")
        # Drop and recreate the schema to ensure a clean state
        conn.execute(text(f'DROP SCHEMA IF EXISTS {settings.TEST_SCHEMA} CASCADE'))
        conn.execute(text(f'CREATE SCHEMA {settings.TEST_SCHEMA}'))
        conn.commit()
    
    # Set search path for the connection
    def set_search_path(conn, _):
        conn.execute(text(f'SET search_path TO {settings.TEST_SCHEMA}'))
    
    event.listen(engine, 'connect', set_search_path)
    
    # Import all models to ensure they are registered with SQLAlchemy
    from app.models.user import User
    from app.models.session import Session
    
    # Create all tables in the test schema
    with engine.connect() as conn:
        print(f"Creating tables in schema: {settings.TEST_SCHEMA}")
        # Ensure we're using the test schema
        conn.execute(text(f'SET search_path TO {settings.TEST_SCHEMA}'))
        # Create all tables
        Base.metadata.create_all(bind=conn)
        conn.commit()
        
        # Verify schema is set correctly
        result = conn.execute(text('SELECT current_schema()')).scalar()
        print(f"Current schema after setup: {result}")
        assert result == settings.TEST_SCHEMA.lower(), f"Schema not set correctly. Expected {settings.TEST_SCHEMA}, got {result}"
        
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
    
    email = "tester123@example.com"
    password = "tester123"
    
    # Check if user already exists and clean up if needed
    existing_user = crud_user.get_by_email(db, email=email)
    if existing_user:
        db.delete(existing_user)
        db.commit()
    
    # Create user using CRUD to ensure proper password hashing
    user_in = UserCreate(
        email=email,
        password=password,
        full_name="Test User"
    )
    
    user = crud_user.create(db, obj_in=user_in)
    
    # Verify the user was created and password is hashed
    db_user = crud_user.get_by_email(db, email=email)
    assert db_user is not None, f"Test user {email} was not created in the database"
    assert db_user.email == email.lower(), f"Email not normalized correctly. Expected {email.lower()}, got {db_user.email}"
    assert db_user.hashed_password != password, "Password was not hashed"
    print(f"Test user created successfully: {db_user.email}")
    
    # Add the plain password to the returned user object for testing
    db_user.plain_password = password
    
    # Clean up after test
    yield db_user
    
    # Remove the test user
    try:
        db.delete(db_user)
        db.commit()
        print(f"Cleaned up test user: {email}")
    except Exception as e:
        print(f"Error cleaning up test user: {e}")
        db.rollback()
