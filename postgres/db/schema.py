from typing import Optional
import psycopg2

from database_definition import DDL, INDEX_DDL
from db.connection import get_conn, TARGET_DB


def create_tables() -> None:
    """
    Create all tables in the database using DDL from database_definition.
    
    Creates the database schema based on the DDL constant from database_definition module.
    """
    conn = get_conn(TARGET_DB)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(DDL)
        print("Schema created.")
    finally:
        conn.close()


def create_indexes() -> None:
    """
    Create all indexes in the database using INDEX_DDL from database_definition.
    
    Creates indexes based on the INDEX_DDL constant from database_definition module.
    """
    conn = get_conn(TARGET_DB)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(INDEX_DDL)
        print("Indexes created.")
    finally:
        conn.close()


def optimize_postgres_for_bulk_load() -> None:
    """
    Optimize PostgreSQL parameters for loading large datasets.
    
    Increases work memory, maintenance memory, disables autovacuum,
    and makes other optimizations to speed up bulk data loading.
    """
    conn = get_conn(TARGET_DB)
    try:
        with conn:
            with conn.cursor() as cur:
                # Increase work memory
                cur.execute("SET work_mem = '256MB'")
                
                # Disable autovacuum during loading
                cur.execute("ALTER TABLE players SET (autovacuum_enabled = false)")
                cur.execute("ALTER TABLE games SET (autovacuum_enabled = false)")
                cur.execute("ALTER TABLE prices SET (autovacuum_enabled = false)")
                cur.execute("ALTER TABLE achievements SET (autovacuum_enabled = false)")
                cur.execute("ALTER TABLE history SET (autovacuum_enabled = false)")
                
                # Other optimizations
                cur.execute("SET maintenance_work_mem = '1GB'")  # Speed up index creation
                cur.execute("SET max_wal_size = '4GB'")          # Increase WAL size, fewer flushes
                cur.execute("ALTER TABLE prices DISABLE TRIGGER ALL")
        print("PostgreSQL optimized for bulk loading.")
    except Exception as e:
        print(f"Error while optimizing PostgreSQL: {str(e)}")
    finally:
        conn.close()


def restore_postgres_settings() -> None:
    """
    Restore normal settings after data loading.
    
    Re-enables autovacuum, enables triggers, and runs VACUUM ANALYZE
    to improve query planning after bulk data loading.
    """
    conn = get_conn(TARGET_DB)
    try:
        with conn:
            with conn.cursor() as cur:
                # Re-enable autovacuum
                try:
                    cur.execute("ALTER TABLE players SET (autovacuum_enabled = true)")
                    cur.execute("ALTER TABLE games SET (autovacuum_enabled = true)")
                    cur.execute("ALTER TABLE prices SET (autovacuum_enabled = true)")
                    cur.execute("ALTER TABLE achievements SET (autovacuum_enabled = true)")
                    cur.execute("ALTER TABLE history SET (autovacuum_enabled = true)")
                    cur.execute("ALTER TABLE prices ENABLE TRIGGER ALL")
                except Exception as e:
                    print(f"Warning when restoring autovacuum: {str(e)}")
                
                # Run VACUUM ANALYZE for better query plans
                try:
                    cur.execute("VACUUM ANALYZE")
                except Exception as e:
                    print(f"Warning when executing VACUUM: {str(e)}")
        print("Restored normal PostgreSQL settings and ran VACUUM ANALYZE.")
    except Exception as e:
        print(f"Error while restoring PostgreSQL settings: {str(e)}")
    finally:
        conn.close()