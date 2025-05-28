from typing import Optional
import mysql.connector

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
    
    Checks if each index exists before creating it to avoid MySQL syntax errors.
    """
    conn = get_conn(TARGET_DB)
    try:
        with conn.cursor() as cur:
            # Parse individual CREATE INDEX statements from INDEX_DDL
            index_statements = [stmt.strip() for stmt in INDEX_DDL.strip().split(';') if stmt.strip()]
            
            for statement in index_statements:
                if statement.startswith('CREATE INDEX'):
                    # Extract index name and table name from statement
                    # Format: CREATE INDEX index_name ON table_name(columns)
                    parts = statement.split()
                    index_name = parts[2]  # index name
                    table_name = parts[4].split('(')[0]  # table name before (
                    
                    # Check if index already exists
                    cur.execute("""
                        SELECT COUNT(*) 
                        FROM information_schema.statistics 
                        WHERE table_schema = %s 
                        AND table_name = %s 
                        AND index_name = %s
                    """, (TARGET_DB, table_name, index_name))
                    
                    exists = cur.fetchone()[0] > 0
                    
                    if not exists:
                        try:
                            cur.execute(statement)
                            print(f"Created index: {index_name}")
                        except mysql.connector.Error as e:
                            print(f"Error creating index {index_name}: {e}")
                    else:
                        print(f"Index {index_name} already exists, skipping.")
            
        conn.commit()
        print("Index creation completed.")
    finally:
        conn.close()


def optimize_mysql_for_bulk_load() -> None:
    """
    Optimize MySQL parameters for loading large datasets.
    
    Disables unique checks, foreign key checks, and autocommit
    to speed up bulk data loading.
    """
    conn = get_conn(TARGET_DB)
    try:
        with conn.cursor() as cur:
            # Disable foreign key checks
            cur.execute("SET foreign_key_checks = 0")
            
            # Disable unique checks
            cur.execute("SET unique_checks = 0")
            
            # Disable autocommit for better performance
            conn.autocommit = False
            
            # Increase bulk insert buffer size
            cur.execute("SET bulk_insert_buffer_size = 256*1024*1024")
            
            # Disable binlog for session
            cur.execute("SET sql_log_bin = 0")
            
        conn.commit()
        print("MySQL optimized for bulk loading.")
    except Exception as e:
        print(f"Error while optimizing MySQL: {str(e)}")
    finally:
        conn.close()


def restore_mysql_settings() -> None:
    """
    Restore normal settings after data loading.
    
    Re-enables foreign key checks, unique checks, and autocommit.
    Runs ANALYZE TABLE to update statistics for better query planning.
    """
    conn = get_conn(TARGET_DB)
    try:
        with conn.cursor() as cur:
            # Re-enable foreign key checks
            try:
                cur.execute("SET foreign_key_checks = 1")
                cur.execute("SET unique_checks = 1")
                cur.execute("SET sql_log_bin = 1")
                conn.autocommit = True
            except Exception as e:
                print(f"Warning when restoring checks: {str(e)}")
            
            # Update table statistics for better query plans
            try:
                tables = ['players', 'games', 'prices', 'achievements', 'history',
                         'developers', 'publishers', 'genres', 'supported_languages',
                         'player_games', 'game_developers', 'game_publishers', 
                         'game_genres', 'game_supported_languages']
                for table in tables:
                    cur.execute(f"ANALYZE TABLE {table}")
            except Exception as e:
                print(f"Warning when executing ANALYZE: {str(e)}")
                
        conn.commit()
        print("Restored normal MySQL settings and ran ANALYZE TABLE.")
    except Exception as e:
        print(f"Error while restoring MySQL settings: {str(e)}")
    finally:
        conn.close()