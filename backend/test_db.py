import os
import sys
import time
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def test_database_connection():
    """Test database connection and create a test table with a record."""
    print("Testing database connection...")
    
    # Get database connection details from environment
    db_params = {
        'dbname': os.getenv('POSTGRES_DB', 'healthcare_integration'),
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', 'postgres'),
        'host': os.getenv('POSTGRES_HOST', 'db'),
        'port': os.getenv('POSTGRES_PORT', '5432')
    }
    
    # Try to connect to the database
    max_retries = 5
    retry_delay = 2  # seconds
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"Attempt {attempt}/{max_retries} to connect to database...")
            conn = psycopg2.connect(**db_params)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            print("✅ Successfully connected to the database!")
            break
        except psycopg2.OperationalError as e:
            print(f"❌ Connection attempt {attempt} failed: {e}")
            if attempt == max_retries:
                print("❌ All connection attempts failed. Exiting.")
                return False
            print(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
    
    # Create a test table
    try:
        with conn.cursor() as cur:
            # Create a test table if it doesn't exist
            cur.execute("""
                CREATE TABLE IF NOT EXISTS test_connection (
                    id SERIAL PRIMARY KEY,
                    test_message TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("✅ Created test_connection table")
            
            # Insert a test record
            test_message = f"Test connection at {time.ctime()}"
            cur.execute(
                "INSERT INTO test_connection (test_message) VALUES (%s) RETURNING id",
                (test_message,)
            )
            record_id = cur.fetchone()[0]
            print(f"✅ Inserted test record with ID: {record_id}")
            
            # Verify the record was inserted
            cur.execute("SELECT * FROM test_connection WHERE id = %s", (record_id,))
            record = cur.fetchone()
            print(f"✅ Retrieved test record: {record}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error during database operations: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()
            print("✅ Database connection closed")

if __name__ == "__main__":
    success = test_database_connection()
    sys.exit(0 if success else 1)
