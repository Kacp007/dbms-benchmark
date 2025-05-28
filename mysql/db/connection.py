import os
import mysql.connector
from mysql.connector import Error
from typing import Dict, Optional, Any, Union

# Database configuration
DB_CONFIG: Dict[str, Union[str, int]] = {
    'host': 'localhost',
    'port': 3306,
    'database': 'mysql', 
    'user': 'root',
    'password': 'example'
}
TARGET_DB: str = 'benchmarkdb' 
SCRIPT_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_abs_path(filename: str) -> str:
    """Returns absolute path for a given filename."""
    return os.path.join(SCRIPT_DIR, filename)

def get_conn(dbname: Optional[str] = None) -> mysql.connector.MySQLConnection:
    """
    Returns a new MySQL database connection.
    
    Args:
        dbname: Optional database name to connect to. If None, uses default from DB_CONFIG.
        
    Returns:
        A new MySQL connection object.
    """
    config = DB_CONFIG.copy()
    if dbname:
        config['database'] = dbname
        
    print(f"Connecting to MySQL database: {config.get('database', 'mysql')} on {config['host']}:{config['port']}")
    return mysql.connector.connect(**config)

def create_database() -> None:
    """Create the benchmarkdb database if it doesn't exist."""
    # Connect to default mysql database
    conn = get_conn()
    conn.autocommit = True  # Required for CREATE DATABASE
    try:
        with conn.cursor() as cur:
            # Check if database exists
            cur.execute("SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = %s", (TARGET_DB,))
            exists = cur.fetchone()
            
            if not exists:
                print(f"Creating database {TARGET_DB}...")
                cur.execute(f"CREATE DATABASE {TARGET_DB}")
                print(f"Database {TARGET_DB} created successfully.")
            else:
                print(f"Database {TARGET_DB} already exists.")
    finally:
        conn.close()

def check_connection() -> bool:
    """
    Check database connection status.
    
    Returns:
        True if connection is successful, False otherwise.
    """
    try:
        print("Checking database connection...")
        # First connect to the default mysql database
        conn = get_conn()
        conn.close()
        print("Connection to mysql database successful.")

        # Check if benchmarkdb exists
        conn = get_conn()
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = %s", (TARGET_DB,))
            exists = cur.fetchone()
        conn.close()

        if exists:
            try:
                # Check connection to benchmarkdb
                conn = get_conn(TARGET_DB)
                conn.close()
                print(f"Connection to {TARGET_DB} database successful.")
            except Exception as e:
                print(f"Cannot connect to {TARGET_DB} database: {str(e)}")
        else:
            print(f"Database {TARGET_DB} does not exist.")
        return True
    except Exception as e:
        print(f"Connection error: {str(e)}")
        return False