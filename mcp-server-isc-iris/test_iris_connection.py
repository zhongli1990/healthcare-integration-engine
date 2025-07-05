import os
from irisnative._IRISNative import createConnection, createIris

def test_connection():
    config = {
        "hostname": "database",
        "port": 1972,
        "namespace": "USER",
        "username": "_SYSTEM",
        "password": "password"
    }
    
    print(f"Attempting to connect to IRIS at {config['hostname']}:{config['port']}...")
    try:
        # Use createConnection and createIris from _IRISNative
        db = createConnection(sharedmemory=False, **config)
        iris = createIris(db)
        print("Successfully connected to IRIS!")
        
        # Test a simple IRIS command
        version = iris.classMethodValue("%SYSTEM.Version", "GetVersion")
        print(f"IRIS Version: {version}")
        
        db.close()
        return True
    except Exception as ex:
        print(f"Error connecting to IRIS: {ex}")
        return False

if __name__ == "__main__":
    test_connection()
