import psycopg2
from psycopg2 import sql
import os

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'postgres', 
    'user': 'postgres',
    'password': 'admin'
}
TARGET_DB = 'benchmarkdb' 
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_abs_path(filename):
    """Returns absolute path for a given filename."""
    return os.path.join(SCRIPT_DIR, filename)

def get_conn(dbname=None):
    """Returns a new database connection using a DSN string to avoid encoding issues."""
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

def create_database():
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

            # Utwórz indeksy po stworzeniu tabel
            print("\n=== TWORZENIE INDEKSÓW ===")
            from db.schema import create_indexes
            create_indexes()
    finally:
        conn.close()

def check_connection():
    """Check database connection status."""
    try:
        print("Sprawdzanie połączenia z bazą danych...")
        # Najpierw połącz z domyślną bazą postgres
        conn = get_conn()
        conn.close()
        print("Połączenie z bazą postgres udane.")

        # Sprawdź, czy istnieje baza benchmarkdb
        conn = get_conn()
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TARGET_DB,))
            exists = cur.fetchone()
        conn.close()

        if exists:
            try:
                # Sprawdź połączenie z benchmarkdb
                conn = get_conn(TARGET_DB)
                conn.close()
                print(f"Połączenie z bazą {TARGET_DB} udane.")
            except Exception as e:
                print(f"Nie można połączyć się z bazą {TARGET_DB}: {str(e)}")
        else:
            print(f"Baza danych {TARGET_DB} nie istnieje.")
        return True
    except Exception as e:
        print(f"Błąd połączenia: {str(e)}")
        return False