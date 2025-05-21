"""
Benchmark module for database performance testing.

This module contains functions for executing benchmark queries and
recording their execution times and query plans.
"""
from typing import Tuple, List, Any, Optional, Callable
import os
import csv
import psycopg2
from datetime import datetime

from db.connection import get_conn, TARGET_DB, get_abs_path, create_database
from db.schema import create_tables, create_indexes
from db.data_loader import load_all
from db.query_generators import (
    BenchmarkQuery,
    QueryType,
    generate_select_query,
    generate_insert_query,
    generate_update_query,
    generate_delete_query,
    generate_complex_select_query
)

# Path for storing benchmark results
RESULTS_DIR = get_abs_path('results')
RESULTS_FILE = os.path.join(RESULTS_DIR, 'benchmark_results.txt')
CSV_RESULTS_FILE = os.path.join(RESULTS_DIR, f'benchmark_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')


def ensure_results_dir() -> None:
    """Ensure the results directory exists."""
    os.makedirs(RESULTS_DIR, exist_ok=True)


def create_csv_file() -> None:
    """Create a new CSV file with headers for benchmark results."""
    ensure_results_dir()
    with open(CSV_RESULTS_FILE, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Operation Type', 'Sample Size', 'Table', 'Time (ms)'])


def add_benchmark_result(
    operation_type: str,
    sample_size: int,
    execution_time: Optional[float],
    table: str = 'players',
    join_count: Optional[int] = None,
    description: str = ''
) -> None:
    """Add a benchmark result to the CSV file."""
    ensure_results_dir()
    with open(CSV_RESULTS_FILE, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            operation_type,
            sample_size,
            table,
            execution_time
        ])


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

    # Write results to file
    with open(RESULTS_FILE, 'a', encoding='utf-8') as f:
        f.write(f"--- QUERY ---\n{sql_text}\nExecution Time: {exec_time} ms\n{plan}\n\n")

    return exec_time, plan


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


def truncate_all_tables(conn: psycopg2.extensions.connection) -> None:
    """Truncate all tables in the database."""
    tables = [
        'history', 'player_games', 'game_developers', 'game_publishers',
        'game_genres', 'game_supported_languages', 'prices', 'achievements',
        'developers', 'publishers', 'genres', 'supported_languages',
        'games', 'players'
    ]
    
    with conn.cursor() as cur:
        # Disable triggers temporarily
        cur.execute("SET session_replication_role = 'replica';")
        
        # Truncate each table
        for table in tables:
            cur.execute(f"TRUNCATE TABLE {table} CASCADE;")
        
        # Re-enable triggers
        cur.execute("SET session_replication_role = 'origin';")
    
    conn.commit()


def load_data_for_select_benchmark(conn: psycopg2.extensions.connection, scope: int) -> None:
    """Load data for SELECT benchmark."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM history")
        current_count = cur.fetchone()[0]
    
    if current_count > scope:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE history")
        conn.commit()
        current_count = 0
    
    records_to_add = scope - current_count
    
    if records_to_add > 0:
        if current_count == 0:
            # Load base data
            conn.close()
            load_all(history_cap=0, load_other_tables=True)
            conn = get_conn(TARGET_DB)
        
        # Load history records
        conn.close()
        load_all(history_cap=records_to_add, load_other_tables=False)
        conn = get_conn(TARGET_DB)


def run_cud_benchmarks(scopes: List[int] = None) -> bool:
    """Run Create, Update, Delete benchmarks for each scope sequentially."""
    if scopes is None:
        scopes = [10, 100, 1000, 10000, 100000]
    
    if not ensure_database_initialized():
        return False
    
    conn = get_conn(TARGET_DB)
    
    try:
        create_csv_file()
        with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
            f.write("=== CUD BENCHMARK RESULTS ===\n\n")
        
        # For each scope, perform CREATE, UPDATE, DELETE in sequence
        for scope in scopes:
            create_time_sum = 0
            update_time_sum = 0
            delete_time_sum = 0
            for _ in range(3):
                print(f"\n=== BENCHMARKING SCOPE: {scope} ===")

                # Truncate tables before benchmarking
                truncate_all_tables(conn)

                # INSERT operation
                insert_query = generate_insert_query(scope=scope)
                insert_time, _ = benchmark_query(conn, insert_query.sql_text)
                conn.commit()
                create_time_sum += insert_time

                # UPDATE operation
                update_query = generate_update_query(scope=scope)
                update_time, _ = benchmark_query(conn, update_query.sql_text)
                conn.commit()
                update_time_sum += update_time

                # DELETE operation
                delete_query = generate_delete_query(scope=scope)
                delete_time, _ = benchmark_query(conn, delete_query.sql_text)
                conn.commit()
                delete_time_sum += delete_time

            add_benchmark_result(
                operation_type=QueryType.INSERT.name,
                sample_size=scope,
                execution_time=create_time_sum / 3,
                table="players",
            )

            add_benchmark_result(
                operation_type=QueryType.UPDATE.name,
                sample_size=scope,
                execution_time=update_time_sum / 3,
                table="players",
            )

            add_benchmark_result(
                operation_type=QueryType.DELETE.name,
                sample_size=scope,
                execution_time=delete_time_sum / 3,
                table="players",
            )
        return True
        
    except Exception as e:
        print(f"Error during benchmarking: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


def run_select_benchmarks(scopes: List[int] = None) -> bool:
    """Run SELECT benchmarks for each specified scope."""
    if scopes is None:
        scopes = [10, 100, 1000, 10000, 100000]
    
    if not ensure_database_initialized():
        return False
    
    conn = get_conn(TARGET_DB)
    
    try:
        create_csv_file()
        with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
            f.write("=== SELECT BENCHMARK RESULTS ===\n\n")
        
        # Sort scopes in ascending order
        scopes.sort()
        
        # For each scope, prepare data and run benchmarks
        for scope in scopes:
            # Prepare data with controlled history size
            load_data_for_select_benchmark(conn, scope)
            
            # Basic SELECT benchmark
            query = generate_select_query(scope=scope, table="history")
            execution_time, _ = benchmark_query(conn, query.sql_text)
            
            add_benchmark_result(
                operation_type="SELECT",
                sample_size=scope,
                execution_time=execution_time,
                table="history",
                description=f"Select from history (size: {scope})"
            )
            
            # Table-specific queries
            for table in ["players", "games"]:
                query = generate_select_query(scope=min(scope, 10000), table=table)
                execution_time, _ = benchmark_query(conn, query.sql_text)
                
                add_benchmark_result(
                    operation_type="SELECT",
                    sample_size=min(scope, 10000),
                    execution_time=execution_time,
                    table=table,
                    description=f"Select from {table} with history size {scope}"
                )
            
            # Complex join queries
            for join_count in [1, 2, 3]:
                query = generate_complex_select_query(join_count)
                execution_time, _ = benchmark_query(conn, query.sql_text)
                
                add_benchmark_result(
                    operation_type='COMPLEX_SELECT',
                    sample_size=scope,
                    execution_time=execution_time,
                    join_count=join_count,
                    description=f"{query.name} with history size {scope}"
                )
        
        return True
        
    except Exception as e:
        print(f"Error during benchmarking: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


def run_benchmarks() -> bool:
    """Run both CUD and SELECT benchmarks with default scopes."""
    cud_success = run_cud_benchmarks([10, 100, 1000, 10000])
    select_success = run_select_benchmarks([10, 100, 1000, 10000, 100000])
    
    return cud_success and select_success

