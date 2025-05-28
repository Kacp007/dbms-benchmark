#!/usr/bin/env python3
"""
MongoDB benchmark main entry point.
Provides command-line interface for loading data and running benchmarks.
"""
import argparse
from typing import Optional, List

# Import modules from the db package
from db.mongo_connection import create_database, check_connection, get_mongo_database
from db.mongo_schema import create_indexes, validate_collection_data
from db.mongo_data_loader import load_all
from db.mongo_benchmark import run_all_benchmarks, run_crud_benchmarks, run_aggregation_benchmarks, RESULTS_FILE, CSV_RESULTS_FILE


def main() -> None:
    """
    Main entry point for the MongoDB benchmark application.
    Parses command line arguments and executes the appropriate action.
    """
    parser = argparse.ArgumentParser(description='MongoDB benchmark tool - Load data and run performance tests')
    parser.add_argument('--init', action='store_true', help='Initialize database (create database and indexes)')
    parser.add_argument('--load', nargs='?', const=100000000, type=int, metavar='DATA_CAP', 
                        help='Load data into the database with optional row limit (default: 100000000)')
    parser.add_argument('--check-connection', action='store_true', help='Check only database connection')
    
    # Benchmark options
    benchmark_group = parser.add_argument_group('Benchmark Options')
    benchmark_group.add_argument('--benchmark', action='store_true', help='Run all benchmarks')
    benchmark_group.add_argument('--benchmark-crud', action='store_true', help='Run CRUD benchmarks')
    benchmark_group.add_argument('--benchmark-aggregation', action='store_true', help='Run aggregation benchmarks')
    benchmark_group.add_argument('--scopes', type=str, metavar='SCOPE_LIST',
                              help='Comma-separated list of sample sizes to benchmark (e.g., "10,100,1000,10000")')
    benchmark_group.add_argument('--sample-size', type=int, default=5, metavar='N',
                              help='Number of times to run each query (default: 5)')
    
    args = parser.parse_args()

    # Parse scope list if provided
    scopes = None
    if args.scopes:
        try:
            scopes = [int(s.strip()) for s in args.scopes.split(',')]
            print(f"Using custom scopes: {scopes}")
        except ValueError:
            print(f"Error parsing scopes '{args.scopes}'. Using default scopes.")
    
    # Default scopes for CRUD benchmarks if not specified
    default_crud_scopes = [10, 100, 1000, 10000, 100000]

    if args.check_connection:
        check_connection()
        return

    if args.init:
        print("Initializing MongoDB database...")
        create_database()
        db = get_mongo_database()
        create_indexes(db)
        print("Database initialization completed.")
        return

    if args.load is not None:
        print(f"Loading data (cap: {args.load})...")
        db = get_mongo_database()
        results = load_all(db, data_cap=args.load)
        print("Data loading completed.")
        
        # Validate data after loading
        print("\nValidating loaded data:")
        validate_collection_data(db)
        return

    # Benchmark operations
    if args.benchmark or args.benchmark_crud or args.benchmark_aggregation:
        db = get_mongo_database()
        
        # Validate that data exists
        print("Checking database state...")
        counts = validate_collection_data(db)
        
        if not any(counts.values()):
            print("Warning: No data found in database. Consider running --load first.")
            return
        
        if args.benchmark:
            print("Running all MongoDB benchmarks...")
            run_all_benchmarks(db, scopes or default_crud_scopes, args.sample_size)
            
        elif args.benchmark_crud:
            print("Running CRUD benchmarks...")
            results = run_crud_benchmarks(db, scopes or default_crud_scopes, args.sample_size)
            from db.mongo_benchmark import save_benchmark_results
            save_benchmark_results(results, RESULTS_FILE.replace('.txt', '_crud.txt'))
            
        elif args.benchmark_aggregation:
            print("Running aggregation benchmarks...")
            results = run_aggregation_benchmarks(db, args.sample_size)
            from db.mongo_benchmark import save_benchmark_results
            save_benchmark_results(results, RESULTS_FILE.replace('.txt', '_aggregation.txt'))
        
        print(f"Benchmark results saved to {RESULTS_FILE} and {CSV_RESULTS_FILE}")
        return

    # If no specific action is provided, show help
    parser.print_help()


if __name__ == '__main__':
    main()
