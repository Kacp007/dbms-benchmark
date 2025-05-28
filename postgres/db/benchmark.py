"""
Benchmark module for database performance testing.

This module contains functions for executing benchmark queries and
recording their execution times and query plans.
"""
from typing import List
import os
from datetime import datetime

from db.benchmark_utils import ensure_database_initialized, create_csv_file, RESULTS_DIR, benchmark_query, \
    add_benchmark_result, truncate_all_tables
from db.connection import get_conn, TARGET_DB
from db.query_generators import (
    QueryType,
    generate_insert_query,
    generate_update_query,
    generate_delete_query
)

# Path for storing benchmark results
RESULTS_FILE = os.path.join(RESULTS_DIR, 'benchmark_results.txt')
CSV_RESULTS_FILE = os.path.join(RESULTS_DIR, f'benchmark_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')


def run_cud_benchmarks(scopes: List[int] = None) -> bool:
    """Run Create, Update, Delete benchmarks for each scope sequentially."""
    if scopes is None:
        scopes = [10, 100, 1000, 10000, 100000]
    
    if not ensure_database_initialized():
        return False
    
    conn = get_conn(TARGET_DB)
    
    try:
        create_csv_file(RESULTS_FILE)
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
                csv_result_file=CSV_RESULTS_FILE
            )

            add_benchmark_result(
                operation_type=QueryType.UPDATE.name,
                sample_size=scope,
                execution_time=update_time_sum / 3,
                table="players",
                csv_result_file=CSV_RESULTS_FILE
            )

            add_benchmark_result(
                operation_type=QueryType.DELETE.name,
                sample_size=scope,
                execution_time=delete_time_sum / 3,
                table="players",
                csv_result_file=CSV_RESULTS_FILE
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
    raise "use run_cud_benchmarks and run_select_benchmarks instead"
    # """Run both CUD and SELECT benchmarks with default scopes."""
    #cud_success = run_cud_benchmarks([10, 100, 1000, 10000])
    #select_success = run_select_benchmarks([10, 100, 1000, 10000, 100000])
    
    #return cud_success and select_success

