import os
import sys
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

@pytest.mark.asyncio
async def test_database_connection():
    """Test database connection and basic operations using the test schema."""
    try:
        # Create engine using test database URL (which includes the test schema)
        engine = create_engine(settings.TEST_DATABASE_URL)
        
        # Create a session
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # Test connection
        result = db.execute(text("SELECT 1"))
        assert result.scalar() == 1, "Database connection failed"
        
        # Verify we're using the test schema
        schema_result = db.execute(text("SELECT current_schema()")).scalar()
        assert schema_result == settings.TEST_SCHEMA, f"Not using test schema: {schema_result}"
        
        # Create a test table if it doesn't exist
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS test_table (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        
        
        
        """))
        db.commit()
        
        # Insert test data
        db.execute(
            text("INSERT INTO test_table (name) VALUES (:name)"),
            [{"name": "Test Entry 1"}, {"name": "Test Entry 2"}]
        )
        db.commit()
        
        # Query the test data
        result = db.execute(text("SELECT * FROM test_table ORDER BY id DESC LIMIT 5"))
        entries = result.fetchall()
        
        # Verify we got our test data back
        assert len(entries) >= 2, "Test data not found"
        assert any(row.name == "Test Entry 1" for row in entries), "Test entry 1 not found"
        assert any(row.name == "Test Entry 2" for row in entries), "Test entry 2 not found"
        
    except Exception as e:
        pytest.fail(f"Database test failed: {e}")
    finally:
        # Clean up
        if 'db' in locals():
            db.close()
        if 'engine' in locals():
            engine.dispose()

# This allows running the test directly with: python -m pytest tests/test_database.py -v
if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
