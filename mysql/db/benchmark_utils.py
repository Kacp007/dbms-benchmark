import csv
import os
from typing import Optional, Tuple, Any, List

import mysql.connector

from db import get_conn, TARGET_DB, create_database, create_tables, create_indexes, get_abs_path
#from db.benchmark import CSV_RESULTS_FILE


def ensure_database_initialized() -> bool:
    """Ensure the database is initialized before running benchmarks."""
    try:
        conn = get_conn(TARGET_DB)
        conn.close()
        print(f"Database {TARGET_DB} exists and is accessible.")
        return True
    except Exception:
        print(f"Database {TARGET_DB} not accessible. Initializing...")
        create_database()
        create_tables()
        create_indexes()
        return True


def create_csv_file(filename: str) -> None:
    """Create a new CSV file with headers for benchmark results."""
    ensure_results_dir()
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Operation Type', 'Sample Size', 'Table', 'Time (ms)'])


RESULTS_DIR = get_abs_path('results')


import time
from typing import Optional, Tuple, Any
import mysql.connector

def benchmark_query(
        conn: mysql.connector.connection.MySQLConnection,
        sql_text: str,
        params: Optional[Tuple[Any, ...]] = None
) -> Tuple[Optional[float], str]:
    """Execute a query and record its execution time in milliseconds (MySQL version)."""
    try:
        with conn.cursor() as cur:
            start = time.perf_counter()
            cur.execute(sql_text, params or ())
            if cur.with_rows:
                cur.fetchall()
            end = time.perf_counter()
            exec_time = (end - start) * 1000  # convert to ms
    except Exception as e:
        print(f"Error executing query: {e}")
        raise

    #print(f"--- QUERY ---\n{sql_text}\nExecution Time: {exec_time:.3f} ms\n")
    return exec_time, ""


def add_benchmark_result(
    operation_type: str,
    sample_size: int,
    execution_time: Optional[float],
    table: str = 'players',
    csv_result_file = "chuj.csv"
) -> None:
    """Add a benchmark result to the CSV file."""
    ensure_results_dir()
    with open(csv_result_file, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            operation_type,
            sample_size,
            table,
            execution_time
        ])


def ensure_results_dir() -> None:
    """Ensure the results directory exists."""
    os.makedirs(RESULTS_DIR, exist_ok=True)


def truncate_all_tables(conn: mysql.connector.MySQLConnection, table: Optional[List[str]] = None) -> None:
    """Truncate all tables in the database."""
    tables = [
        'history', 'player_games', 'game_developers', 'game_publishers',
        'game_genres', 'game_supported_languages', 'prices', 'achievements',
        'developers', 'publishers', 'genres', 'supported_languages',
        'games', 'players'
    ] if table is None else table

    with conn.cursor() as cur:
        # Disable foreign key checks temporarily
        cur.execute("SET FOREIGN_KEY_CHECKS = 0;")

        # Truncate each table
        for table_name in tables:
            cur.execute(f"TRUNCATE TABLE {table_name};")

        # Re-enable foreign key checks
        cur.execute("SET FOREIGN_KEY_CHECKS = 1;")

    conn.commit()
