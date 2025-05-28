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
    'password': 'admin'
}
TARGET_DB: str = 'benchmarkdb' 
SCRIPT_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_abs_path(filename: str) -> str:
    """Returns absolute path for a given filename."""
    return os.path.join(SCRIPT_DIR, filename)

def get_conn(dbname: Optional[str] = None) -> psycopg2.extensions.connection:
    """
    Returns a new database connection using a DSN string to avoid encoding issues.
    
    Args:
        dbname: Optional database name to connect to. If None, uses default from DB_CONFIG.
        
    Returns:
        A new psycopg2 connection object.
    """
    # Build DSN string explicitly (ASCII-safe)
    config = DB_CONFIG.copy()
    if dbname:
        config['dbname'] = dbname
        
    dsn = (
        f"host={config['host']} "
        f"port={config['port']} "
        f"dbname={config['dbname']} "
        f"user={config['user']} "
        f"password={config['password']}"
    )
    print(f"Connecting to database with DSN: {dsn}")
    return psycopg2.connect(dsn)

def create_database() -> None:
    """Create the benchmarkdb database if it doesn't exist."""
    # Connect to default postgres database
    conn = get_conn()
    conn.autocommit = True  # Required for CREATE DATABASE
    try:
        with conn.cursor() as cur:
            # Check if database exists
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TARGET_DB,))
            exists = cur.fetchone()
            
            if not exists:
                print(f"Creating database {TARGET_DB}...")
                # Escape database name to prevent SQL injection
                create_db_sql = sql.SQL("CREATE DATABASE {}").format(
                    sql.Identifier(TARGET_DB)
                )
                cur.execute(create_db_sql)
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
        # First connect to the default postgres database
        conn = get_conn()
        conn.close()
        print("Connection to postgres database successful.")

        # Check if benchmarkdb exists
        conn = get_conn()
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TARGET_DB,))
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