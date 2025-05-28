import csv
import os
from typing import Optional, Tuple, Any, List

import psycopg2

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


def benchmark_query(
    conn: psycopg2.extensions.connection,
    sql_text: str,
    params: Optional[Tuple[Any, ...]] = None
) -> Tuple[Optional[float], str]:
    """Execute a query and record its execution time using EXPLAIN ANALYZE."""
    try:
        with conn.cursor() as cur:
            # Always use EXPLAIN ANALYZE for all queries
            cur.execute('EXPLAIN ANALYZE ' + sql_text, params or ())
            rows = cur.fetchall()
            plan = '\n'.join(r[0] for r in rows)
            exec_time = None
            # Find the line with 'Execution Time' and extract the value
            for r in rows:
                line = r[0]
                if 'Execution Time' in line:
                    try:
                        exec_time = float(line.split('Execution Time:')[1].split('ms')[0].strip())
                    except Exception:
                        pass
    except Exception as e:
        print(f"Error executing query: {e}")
        raise

    print(f"--- QUERY ---\n{sql_text}\nExecution Time: {exec_time} ms\n{plan}\n\n")

    return exec_time, plan


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


def truncate_all_tables(conn: psycopg2.extensions.connection, table: Optional[List[str]] = None) -> None:
    """Truncate all tables in the database."""
    tables = [
        'history', 'player_games', 'game_developers', 'game_publishers',
        'game_genres', 'game_supported_languages', 'prices', 'achievements',
        'developers', 'publishers', 'genres', 'supported_languages',
        'games', 'players'
    ] if table is None else table

    with conn.cursor() as cur:
        # Disable triggers temporarily
        cur.execute("SET session_replication_role = 'replica';")

        # Truncate each table
        for table in tables:
            cur.execute(f"TRUNCATE TABLE {table} CASCADE;")

        # Re-enable triggers
        cur.execute("SET session_replication_role = 'origin';")

    conn.commit()
