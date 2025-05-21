#!/usr/bin/env python3
"""
Main entry point for the benchmark application.
Provides command-line interface for loading data and running benchmarks.
"""
import argparse
from typing import Optional

# Import modules from the db package
from db.connection import create_database, check_connection
from db.schema import create_tables, create_indexes
from db.data_loader import load_all
from db.benchmark import run_benchmarks, RESULTS_FILE


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
    parser.add_argument('--benchmark', action='store_true', help='Run benchmarks')
    args = parser.parse_args()

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
    elif args.benchmark:
        print("\n=== RUNNING BENCHMARKS ===")
        run_benchmarks()
        print(f"Benchmark results saved to {RESULTS_FILE}")
    else:
        print("Run with --init option to initialize the database (create tables and indexes).")
        print("Run with --load [DATA_CAP] to load data into the database with optional row cap.")
        print("   Example: python postgres_test.py --load 1000")
        print("   Default: python postgres_test.py --load (uses 100,000,000 as cap)")
        print("Run with --check-connection option to check database connection.")
        print("Run with --benchmark option to run performance tests.")


if __name__ == '__main__':
    main()