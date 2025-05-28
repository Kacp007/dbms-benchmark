#!/usr/bin/env python3
"""
Main entry point for the benchmark application.
Provides command-line interface for loading data and running benchmarks.
"""
import argparse
from typing import Optional, List

# Import modules from the db package
from db.connection import create_database, check_connection
from db.schema import create_tables, create_indexes
from db.data_loader import load_all
from db.benchmark import run_benchmarks, run_cud_benchmarks, CSV_RESULTS_FILE
from db.benchmark_select import run_select_benchmarks


def main() -> None:
    """
    Main entry point for the benchmark application.
    Parses command line arguments and executes the appropriate action.
    """
    parser = argparse.ArgumentParser(description='Load CSVs and prepare benchmarking DB')
    parser.add_argument('--init', action='store_true', help='Initialize database (create database, tables, and indexes)')
    parser.add_argument('--load', nargs='?', const=100000000, type=int, metavar='DATA_CAP', 
                        help='Load data into the database with optional row limit (default: 100000000)')
    parser.add_argument('--check-connection', action='store_true', help='Check only database connection')
    
    # Benchmark options
    benchmark_group = parser.add_argument_group('Benchmark Options')
    benchmark_group.add_argument('--benchmark', action='store_true', help='Run all benchmarks')
    benchmark_group.add_argument('--benchmark-cud', action='store_true', help='Run Create, Update, Delete benchmarks')
    benchmark_group.add_argument('--benchmark-select', action='store_true', help='Run SELECT benchmarks')
    benchmark_group.add_argument('--scopes', type=str, metavar='SCOPE_LIST',
                              help='Comma-separated list of sample sizes to benchmark (e.g., "10,100,1000,10000")')
    
    args = parser.parse_args()

    # Parse scope list if provided
    scopes = None
    if args.scopes:
        try:
            scopes = [int(s.strip()) for s in args.scopes.split(',')]
            print(f"Using custom scopes: {scopes}")
        except ValueError:
            print(f"Error parsing scopes '{args.scopes}'. Using default scopes.")
    
    # Default scopes for CUD benchmarks if not specified
    default_cud_scopes = [10, 100, 1000, 10000, 100000, 1000000, 10000000]
    default_cud_scopes = [10000000]
    #default_cud_scopes = [10, 100, 1000, 10000]

    if args.check_connection:
        check_connection()
    elif args.init:
        print("\n=== INITIALIZING DATABASE ===")
        print("Creating database...")
        create_database()
        print("Creating tables...")
        create_tables()
        # Create indexes after creating tables
        print("\n=== CREATING INDEXES ===")
        create_indexes()
        print("\nDatabase initialization completed successfully.")
    elif args.load is not None:
        data_cap = args.load
        print(f"\n=== LOADING DATA (cap: {data_cap} rows) ===")
        if load_all(data_cap):
            print("\n=== SUCCESS ===")
            print("Data loaded successfully.")
        else:
            print("\n=== ERROR ===")
            print("An error occurred while loading data.")
    elif args.benchmark_cud:
        print("\n=== RUNNING CREATE/UPDATE/DELETE BENCHMARKS ===")
        cud_scopes = scopes if scopes else default_cud_scopes
        run_cud_benchmarks(cud_scopes)
        print(f"Benchmark results saved to {CSV_RESULTS_FILE}")
    elif args.benchmark_select:
        print("\n=== RUNNING SELECT BENCHMARKS ===")
        select_scopes = scopes if scopes else default_cud_scopes
        run_select_benchmarks(select_scopes)
        print(f"Benchmark results saved to {CSV_RESULTS_FILE}")
    elif args.benchmark:
        print("\n=== RUNNING ALL BENCHMARKS ===")
        # Use provided scopes or defaults
        if scopes:
            run_cud_benchmarks(scopes)
            run_select_benchmarks(scopes)
        else:
            run_benchmarks()  # Uses default scopes
        print(f"Benchmark results saved to {CSV_RESULTS_FILE}")
    else:
        print("Run with --init option to initialize the database (create tables and indexes).")
        print("Run with --load [DATA_CAP] to load data into the database with optional row cap.")
        print("   Example: python postgres_test.py --load 1000")
        print("   Default: python postgres_test.py --load (uses 100,000,000 as cap)")
        print("Run with --check-connection option to check database connection.")
        print("Run with --benchmark option to run all performance tests.")
        print("Run with --benchmark-cud option to run Create/Update/Delete benchmarks.")
        print("Run with --benchmark-select option to run SELECT benchmarks.")
        print("Add --scopes \"10,100,1000,10000,100000\" to specify custom sample sizes.")


if __name__ == '__main__':
    main()