"""
Benchmark module for database performance testing.

This module contains functions for executing benchmark queries and
recording their execution times and query plans.
"""
from typing import Tuple, List, Dict, Any, Optional, Callable
import psycopg2

from db.connection import get_conn, TARGET_DB, get_abs_path
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
RESULTS_FILE = get_abs_path('benchmark_results.txt')


def benchmark_query(conn: psycopg2.extensions.connection, sql_text: str, params: Optional[Tuple[Any, ...]] = None) -> Tuple[Optional[float], str]:
    """
    Execute a query with EXPLAIN ANALYZE and record the results.

    Args:
        conn: Database connection object
        sql_text: SQL query to benchmark
        params: Any parameters for the SQL query

    Returns:
        Tuple of (execution time in ms, execution plan)
    """
    with conn.cursor() as cur:
        cur.execute('EXPLAIN ANALYZE ' + sql_text, params or ())
        rows = cur.fetchall()

    plan = '\n'.join(r[0] for r in rows)
    exec_time = None

    for line in rows[-1]:
        if 'Execution Time' in line:
            exec_time = float(line.split()[2])

    with open(RESULTS_FILE, 'a', encoding='utf-8') as f:
        f.write(f"--- QUERY ---\n{sql_text}\nExecution Time: {exec_time} ms\n{plan}\n\n")

    return exec_time, plan


def run_benchmark_set(
    conn: psycopg2.extensions.connection,
    query_type: QueryType,
    scopes: List[int],
    generator_func: Callable,
    **kwargs
) -> None:
    """
    Run a set of benchmarks for a specific query type and various scopes.
    
    Args:
        conn: Database connection
        query_type: Type of query to run
        scopes: List of scopes (sizes) to benchmark
        generator_func: Function to generate the queries
        kwargs: Additional arguments to pass to the generator function
    """
    print(f"\n=== BENCHMARKING {query_type.name} QUERIES ===")
    for scope in scopes:
        query = generator_func(scope=scope, **kwargs)
        print(f"\n--- {query.name} ---")
        execution_time, plan = benchmark_query(conn, query.sql_text)
        print(f"Execution time: {execution_time} ms")


def run_benchmarks() -> bool:
    """
    Run a comprehensive set of benchmark tests on the database.
    Tests include SELECT, INSERT, UPDATE, and DELETE operations of various complexity.
    Results are printed to the console and saved to the results file.
    
    Returns:
        True if benchmarks completed successfully, False otherwise.
    """
    conn = get_conn(TARGET_DB)
    
    try:
        # Open in append mode to add header
        with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
            f.write("=== BENCHMARK RESULTS ===\n\n")
            
        print("\n=== STARTING BENCHMARKS ===")
        
        # SELECT queries with different scopes
        run_benchmark_set(
            conn,
            QueryType.SELECT,
            [10, 100, 1000, 10000, 100000],
            generate_select_query
        )
        
        # Test with different tables
        for table in ["players", "games", "history"]:
            run_benchmark_set(
                conn,
                QueryType.SELECT,
                [1000],
                generate_select_query,
                table=table
            )
        
        # Complex SELECT queries with different join complexities
        print("\n=== BENCHMARKING COMPLEX SELECT QUERIES ===")
        for join_count in [1, 2, 3]:
            query = generate_complex_select_query(join_count)
            print(f"\n--- {query.name} ---")
            execution_time, plan = benchmark_query(conn, query.sql_text)
            print(f"Execution time: {execution_time} ms")
        
        # INSERT queries with different scopes
        run_benchmark_set(
            conn,
            QueryType.INSERT,
            [1, 10, 100, 1000, 10000],
            generate_insert_query
        )
        
        # UPDATE queries with different scopes
        run_benchmark_set(
            conn,
            QueryType.UPDATE,
            [1, 10, 100, 1000, 10000],
            generate_update_query
        )
        
        # DELETE queries with different scopes
        run_benchmark_set(
            conn,
            QueryType.DELETE,
            [1, 10, 100, 1000, 10000],
            generate_delete_query
        )
        
        print(f"\nBenchmark results written to {RESULTS_FILE}")
        return True
        
    except Exception as e:
        print(f"Error during benchmarking: {str(e)}")
        return False
    finally:
        conn.close()