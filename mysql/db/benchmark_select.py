from db import generate_select_query, generate_complex_select_query, BenchmarkQuery
from db.connection import get_conn, TARGET_DB, get_abs_path
from db.benchmark_utils import ensure_database_initialized, create_csv_file, RESULTS_DIR, benchmark_query, \
    add_benchmark_result, truncate_all_tables
from typing import Tuple, List, Any, Optional
import os
import psycopg2
from db.data_loader import load_all
from datetime import datetime

RESULTS_FILE = os.path.join(RESULTS_DIR, 'benchmark_select_results.txt')


def load_data_for_select_benchmark(conn: psycopg2.extensions.connection, scope: int) -> None:
    """Load data for SELECT benchmark."""
    import csv
    history_csv = get_abs_path('data/cleaned/history_cleaned.csv')
    rows = []
    with open(history_csv, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        first_row = next(reader)
        # Check if first row is header (contains column names)
        if all(x.lower() in ['playerid', 'achievementid', 'date_acquired'] for x in first_row):
            # skip header, read up to scope rows
            for i, row in enumerate(reader):
                if i >= scope:
                    break
                rows.append(row)
        else:
            # first row is data
            rows.append(first_row)
            for i, row in enumerate(reader):
                if i >= scope - 1:
                    break
                rows.append(row)
    # Insert into history table
    with conn.cursor() as cur:
        cur.execute('TRUNCATE TABLE history;')
        for row in rows:
            cur.execute(
                'INSERT INTO history (playerid, achievementid, date_acquired) VALUES (%s, %s, %s);',
                row
            )
        conn.commit()


def run_select_benchmarks(scopes: List[int] = None) -> bool:
    """Run SELECT benchmarks for each specified scope."""
    CSV_RESULTS_FILE = os.path.join(RESULTS_DIR, f'benchmark_select_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')

    if not ensure_database_initialized():
        return False

    conn = get_conn(TARGET_DB)

    try:
        create_csv_file(CSV_RESULTS_FILE)
        with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
            f.write("=== SELECT BENCHMARK RESULTS ===\n\n")

        # Sort scopes in ascending order
        scopes.sort()

        # For each scope, prepare data and run benchmarks
        for scope in scopes:
            # Prepare data with controlled history size
            simple_time_sum = 0
            bit_complex_time_sum = 0
            complex_time_sum = 0

            load_data_for_select_benchmark(conn, scope)
            print(f"\n=== BENCHMARKING SCOPE: {scope} ===")
            for _ in range(3):

                simple_query = BenchmarkQuery(
                    f"Simple select {scope}",
                    f"SELECT * FROM history;")

                simple_time, _ = benchmark_query(conn, simple_query.sql_text)
                simple_time_sum += simple_time

                bit_complex_query = BenchmarkQuery(
                    f"Bit complex select {scope}",
                    """SELECT COUNT(*) FROM history h
                     INNER JOIN achievements a ON h.achievementid = a.achievementid;""")
                bit_complex_time, _ = benchmark_query(conn, bit_complex_query.sql_text)
                bit_complex_time_sum += bit_complex_time

                complex_query = BenchmarkQuery(
                    f"Complex select {scope}",
                    """SELECT COUNT(*)
                       FROM history h
                                INNER JOIN achievements a ON h.achievementid = a.achievementid
                                INNER JOIN games g ON a.gameid = g.gameid
                                INNER JOIN game_developers gd ON g.gameid = gd.game_id
                                INNER JOIN prices p ON g.gameid = p.gameid
                                INNER JOIN game_genres gg ON g.gameid = gg.game_id
                    ;""")
                complex_time, _ = benchmark_query(conn, complex_query.sql_text)
                complex_time_sum += complex_time

            add_benchmark_result(
                operation_type="SELECT_SIMPLE",
                sample_size=scope,
                execution_time=simple_time_sum / 3,
                table="history",
                csv_result_file=CSV_RESULTS_FILE
            )
            add_benchmark_result(
                operation_type="SELECT_BIT_COMPLEX",
                sample_size=scope,
                execution_time=bit_complex_time_sum / 3,
                table="history",
                csv_result_file=CSV_RESULTS_FILE
            )
            add_benchmark_result(
                operation_type="SELECT_COMPLEX",
                sample_size=scope,
                execution_time=complex_time_sum / 3,
                table="history",
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

