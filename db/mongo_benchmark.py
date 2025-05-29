"""
MongoDB benchmark module for database performance testing.

This module contains functions for executing benchmark queries and
recording their execution times and query plans.
"""
from typing import Tuple, List, Any, Optional, Callable, Dict
import os
import csv
import time
from datetime import datetime
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from db.mongo_connection import get_abs_path, get_mongo_database
from db.mongo_schema import create_indexes, validate_collection_data
from db.mongo_data_loader import load_all
from db.mongo_query_generators import (
    MongoQuery,
    QueryType,
    generate_find_query,
    generate_find_with_filter_query,
    generate_insert_one_query,
    generate_insert_many_query,
    generate_update_one_query,
    generate_update_many_query,
    generate_delete_one_query,
    generate_delete_many_query,
    generate_aggregation_query,
    generate_text_search_query,
    generate_complex_analytical_query
)

# Path for storing benchmark results
RESULTS_DIR = get_abs_path('results')
RESULTS_FILE = os.path.join(RESULTS_DIR, 'mongo_benchmark_results.txt')
CSV_RESULTS_FILE = os.path.join(RESULTS_DIR, f'mongo_benchmark_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')

def ensure_results_directory() -> None:
    """Ensure the results directory exists."""
    os.makedirs(RESULTS_DIR, exist_ok=True)

def execute_mongo_query(db: Database, query: MongoQuery, sample_size: int = 5) -> Dict[str, Any]:
    """
    Execute a MongoDB query and measure its performance.
    
    Args:
        db: MongoDB database object
        query: MongoQuery object containing the query details
        sample_size: Number of times to run the query for averaging
        
    Returns:
        Dictionary containing execution statistics
    """
    collection = db[query.collection]
    execution_times = []
    results_count = 0
    error_message = None
    
    for i in range(sample_size):
        try:
            start_time = time.perf_counter()
            
            if query.operation == QueryType.FIND:
                if query.options and "limit" in query.options:
                    cursor = collection.find(query.query or {}).limit(query.options["limit"])
                else:
                    cursor = collection.find(query.query or {})
                  # Force execution by converting to list
                result = list(cursor)
                results_count = len(result)
                
            elif query.operation == QueryType.INSERT_ONE:
                # Use upsert to avoid duplicate key errors
                filter_query = query.query.copy()
                if 'playerid' in filter_query:
                    filter_doc = {'playerid': filter_query['playerid']}
                elif 'gameid' in filter_query:
                    filter_doc = {'gameid': filter_query['gameid']}
                else:
                    filter_doc = filter_query
                
                result = collection.replace_one(filter_doc, query.query, upsert=True)
                results_count = 1 if result.upserted_id or result.modified_count else 0
                
            elif query.operation == QueryType.INSERT_MANY:
                # For insert_many, we'll need to handle duplicates differently
                try:
                    result = collection.insert_many(query.query, ordered=False)
                    results_count = len(result.inserted_ids)
                except Exception as e:
                    # If there are duplicate key errors, try to insert one by one with upsert
                    results_count = 0
                    for doc in query.query:
                        try:
                            if 'playerid' in doc:
                                filter_doc = {'playerid': doc['playerid']}
                            elif 'gameid' in doc:
                                filter_doc = {'gameid': doc['gameid']}
                            else:
                                filter_doc = doc
                            
                            upsert_result = collection.replace_one(filter_doc, doc, upsert=True)
                            if upsert_result.upserted_id or upsert_result.modified_count:
                                results_count += 1
                        except Exception:
                            pass  # Skip individual failures
                
            elif query.operation == QueryType.UPDATE_ONE:
                result = collection.update_one(query.query, query.update_doc)
                results_count = result.modified_count
                
            elif query.operation == QueryType.UPDATE_MANY:
                result = collection.update_many(query.query, query.update_doc)
                results_count = result.modified_count
                
            elif query.operation == QueryType.DELETE_ONE:
                result = collection.delete_one(query.query)
                results_count = result.deleted_count
                
            elif query.operation == QueryType.DELETE_MANY:
                result = collection.delete_many(query.query)
                results_count = result.deleted_count
                
            elif query.operation == QueryType.AGGREGATE:
                cursor = collection.aggregate(query.pipeline)
                result = list(cursor)
                results_count = len(result)
            
            end_time = time.perf_counter()
            execution_time = (end_time - start_time) * 1000  # Convert to milliseconds
            execution_times.append(execution_time)
            
        except PyMongoError as e:
            error_message = str(e)
            print(f"Error executing query '{query.name}': {error_message}")
            break
        except Exception as e:
            error_message = str(e)
            print(f"Unexpected error executing query '{query.name}': {error_message}")
            break
    
    if execution_times:
        avg_time = sum(execution_times) / len(execution_times)
        min_time = min(execution_times)
        max_time = max(execution_times)
    else:
        avg_time = min_time = max_time = None
    
    return {
        "query_name": query.name,
        "collection": query.collection,
        "operation": query.operation.name,
        "average_time_ms": avg_time,
        "min_time_ms": min_time,
        "max_time_ms": max_time,
        "all_times_ms": execution_times,
        "results_count": results_count,
        "sample_size": len(execution_times),
        "error": error_message
    }

def save_benchmark_results(results: List[Dict[str, Any]], output_file: str = None) -> None:
    """
    Save benchmark results to both text and CSV files.
    
    Args:
        results: List of benchmark result dictionaries
        output_file: Optional custom output file path
    """
    ensure_results_directory()
    
    # Save to text file
    text_file = output_file or RESULTS_FILE
    with open(text_file, 'w') as f:
        f.write(f"MongoDB Benchmark Results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        for result in results:
            f.write(f"Query: {result['query_name']}\n")
            f.write(f"Collection: {result['collection']}\n")
            f.write(f"Operation: {result['operation']}\n")
            
            if result['error']:
                f.write(f"Error: {result['error']}\n")
            else:
                f.write(f"Average Time: {result['average_time_ms']:.2f} ms\n")
                f.write(f"Min Time: {result['min_time_ms']:.2f} ms\n")
                f.write(f"Max Time: {result['max_time_ms']:.2f} ms\n")
                f.write(f"Results Count: {result['results_count']}\n")
                f.write(f"Sample Size: {result['sample_size']}\n")
            
            f.write("-" * 40 + "\n")
    
    # Save to CSV file
    csv_file = output_file.replace('.txt', '.csv') if output_file else CSV_RESULTS_FILE
    with open(csv_file, 'w', newline='') as f:
        fieldnames = [
            'query_name', 'collection', 'operation', 'average_time_ms',
            'min_time_ms', 'max_time_ms', 'results_count', 'sample_size', 'error'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in results:
            # Create a copy without the 'all_times_ms' field for CSV
            csv_result = {k: v for k, v in result.items() if k != 'all_times_ms'}
            writer.writerow(csv_result)
    
    print(f"Results saved to {text_file} and {csv_file}")

def run_crud_benchmarks(db: Database, scopes: List[int] = None, sample_size: int = 5) -> List[Dict[str, Any]]:
    """
    Run CRUD (Create, Read, Update, Delete) benchmarks following PostgreSQL pattern.
    For each scope: runs CREATE → UPDATE → DELETE in sequence for each sample.
    
    Args:
        db: MongoDB database object
        scopes: List of data sizes to test
        sample_size: Number of times to run each query
        
    Returns:
        List of benchmark results
    """
    if scopes is None:
        scopes = [10, 100, 1000, 10000]
    
    print(f"Running MongoDB CRUD benchmarks with scopes: {scopes}")
    
    results = []
    
    # First run Read operations separately (they don't modify data)
    print("Running READ benchmarks...")
    for scope in scopes:
        # Ensure we have data to read
        cleanup_benchmark_data(db)
        insert_query = generate_insert_many_query(scope, "players")
        execute_single_mongo_query(db, insert_query)
        
        # Simple find
        query = generate_find_query(scope, "players")
        result = execute_mongo_query(db, query, sample_size)
        results.append(result)
        
        # Find with filter
        query = generate_find_with_filter_query(scope, "players")
        result = execute_mongo_query(db, query, sample_size)
        results.append(result)
    
    # Now run CUD operations in sequence for each scope
    print("Running CUD (Create-Update-Delete) benchmarks...")
    for scope in scopes:
        print(f"\n=== BENCHMARKING CUD SCOPE: {scope} ===")
        
        # Track execution times for each operation type
        create_times = []
        update_times = []
        delete_times = []
        
        # Run the complete CUD sequence for each sample
        for sample in range(sample_size):
            print(f"Sample {sample + 1}/{sample_size} for scope {scope}")
            
            # Clean benchmark data before each sample to ensure fresh data
            cleanup_benchmark_data(db)
            
            # CREATE operation
            if scope == 1:
                create_query = generate_insert_one_query("players")
            else:
                create_query = generate_insert_many_query(scope, "players")
            
            create_result = execute_single_mongo_query(db, create_query)
            create_times.append(create_result["execution_time"])
            print(f"  CREATE: {create_result['execution_time']:.2f}ms, inserted {create_result['results_count']} records")
            
            # UPDATE operation (update some of the just-inserted records)
            if scope == 1:
                update_query = generate_update_one_query("players")
            else:
                update_query = generate_update_many_query(min(scope, 100), "players")  # Limit updates to reasonable number
            
            update_result = execute_single_mongo_query(db, update_query)
            update_times.append(update_result["execution_time"])
            print(f"  UPDATE: {update_result['execution_time']:.2f}ms, updated {update_result['results_count']} records")
            
            # DELETE operation (delete some of the records)
            if scope == 1:
                delete_query = generate_delete_one_query("players")
            else:
                delete_query = generate_delete_many_query(min(scope, 100), "players")  # Limit deletes to reasonable number
            
            delete_result = execute_single_mongo_query(db, delete_query)
            delete_times.append(delete_result["execution_time"])
            print(f"  DELETE: {delete_result['execution_time']:.2f}ms, deleted {delete_result['results_count']} records")
        
        # Create averaged results for each operation type
        create_avg_result = create_average_result(
            f"INSERT_{scope}", "players", "INSERT", create_times, scope
        )
        update_avg_result = create_average_result(
            f"UPDATE_{min(scope, 100)}", "players", "UPDATE", update_times, min(scope, 100)
        )
        delete_avg_result = create_average_result(
            f"DELETE_{min(scope, 100)}", "players", "DELETE", delete_times, min(scope, 100)
        )
        
        results.extend([create_avg_result, update_avg_result, delete_avg_result])
        
        print(f"Scope {scope} completed:")
        print(f"  CREATE avg: {create_avg_result['average_time_ms']:.2f}ms")
        print(f"  UPDATE avg: {update_avg_result['average_time_ms']:.2f}ms") 
        print(f"  DELETE avg: {delete_avg_result['average_time_ms']:.2f}ms")
    
    return results

def run_aggregation_benchmarks(db: Database, sample_size: int = 5) -> List[Dict[str, Any]]:
    """
    Run aggregation (join-like) benchmarks.
    
    Args:
        db: MongoDB database object
        sample_size: Number of times to run each query
        
    Returns:
        List of benchmark results
    """
    print("Running MongoDB aggregation benchmarks...")
    results = []
    
    # Different complexity aggregations
    for join_count in [1, 2, 3]:
        query = generate_aggregation_query(join_count)
        result = execute_mongo_query(db, query, sample_size)
        results.append(result)
    
    # Text search
    query = generate_text_search_query("action", "games")
    result = execute_mongo_query(db, query, sample_size)
    results.append(result)
    
    # Analytical query
    query = generate_complex_analytical_query()
    result = execute_mongo_query(db, query, sample_size)
    results.append(result)
    
    return results

def run_all_benchmarks(db: Database, crud_scopes: List[int] = None, sample_size: int = 5) -> List[Dict[str, Any]]:
    """
    Run all benchmark tests.
    
    Args:
        db: MongoDB database object
        crud_scopes: List of data sizes for CRUD tests
        sample_size: Number of times to run each query
        
    Returns:
        List of all benchmark results
    """
    print("Running all MongoDB benchmarks...")
    
    all_results = []
    
    # Run CRUD benchmarks
    crud_results = run_crud_benchmarks(db, crud_scopes, sample_size)
    all_results.extend(crud_results)
    
    # Run aggregation benchmarks
    agg_results = run_aggregation_benchmarks(db, sample_size)
    all_results.extend(agg_results)
    
    # Save all results
    save_benchmark_results(all_results)
    
    # Print summary
    print(f"\nBenchmark Summary:")
    print(f"Total queries executed: {len(all_results)}")
    
    successful_results = [r for r in all_results if not r['error']]
    if successful_results:
        avg_times = [r['average_time_ms'] for r in successful_results]
        print(f"Average execution time: {sum(avg_times) / len(avg_times):.2f} ms")
        print(f"Fastest query: {min(avg_times):.2f} ms")
        print(f"Slowest query: {max(avg_times):.2f} ms")
    
    failed_results = [r for r in all_results if r['error']]
    if failed_results:
        print(f"Failed queries: {len(failed_results)}")
    
    return all_results

def cleanup_benchmark_data(db: Database) -> None:
    """
    Remove benchmark test data from MongoDB collections.
    
    This function removes any documents that might have been inserted during benchmarks
    to ensure clean benchmark runs and avoid duplicate key errors.
    
    Args:
        db: MongoDB database object
    """
    try:
        # Remove benchmark test documents from collections
        # Use a more comprehensive approach to remove recent benchmark data
        
        # Get current timestamp to identify recent benchmark data
        current_time = int(time.time() * 1000000)
        # Remove data from the last 2 hours (7200 seconds = 7200000000 microseconds)
        two_hours_ago = current_time - 7200000000
        
        # Players: Remove benchmark users (playerid >= two_hours_ago or contains benchmark patterns)
        players_result = db.players.delete_many({
            "$or": [
                {"playerid": {"$gte": two_hours_ago}},
                {"nickname": {"$regex": "^bench.*"}},
                {"nickname": {"$regex": "^benchmark.*"}}
            ]
        })
        print(f"Removed {players_result.deleted_count} benchmark player documents")
        
        # Games: Remove benchmark games  
        games_result = db.games.delete_many({
            "$or": [
                {"gameid": {"$gte": two_hours_ago}},
                {"title": {"$regex": "^Benchmark.*"}}
            ]
        })
        print(f"Removed {games_result.deleted_count} benchmark game documents")
        
        # Achievements: Remove any benchmark achievements
        achievements_result = db.achievements.delete_many({
            "gameid": {"$gte": two_hours_ago}
        })
        print(f"Removed {achievements_result.deleted_count} benchmark achievement documents")
        
        # Prices: Remove any benchmark prices
        prices_result = db.prices.delete_many({
            "gameid": {"$gte": two_hours_ago}
        })
        print(f"Removed {prices_result.deleted_count} benchmark price documents")
        
        # History: Remove any benchmark history
        history_result = db.history.delete_many({
            "playerid": {"$gte": two_hours_ago}
        })
        print(f"Removed {history_result.deleted_count} benchmark history documents")
        
        # Player_games: Remove any benchmark relationships
        player_games_result = db.player_games.delete_many({
            "playerid": {"$gte": two_hours_ago}
        })
        print(f"Removed {player_games_result.deleted_count} benchmark player_games documents")
        
        print("MongoDB benchmark data cleanup completed.")
        
    except Exception as e:
        print(f"Error during MongoDB cleanup: {e}")

def execute_single_mongo_query(db: Database, query: MongoQuery) -> Dict[str, Any]:
    """
    Execute a single MongoDB query and measure its performance.
    
    Args:
        db: MongoDB database object
        query: MongoQuery object containing the query details
        
    Returns:
        Dictionary containing execution statistics for a single run
    """
    collection = db[query.collection]
    results_count = 0
    error_message = None
    
    try:
        start_time = time.perf_counter()
        
        if query.operation == QueryType.FIND:
            if query.options and "limit" in query.options:
                cursor = collection.find(query.query or {}).limit(query.options["limit"])
            else:
                cursor = collection.find(query.query or {})
            # Force execution by converting to list
            result = list(cursor)
            results_count = len(result)
            
        elif query.operation == QueryType.INSERT_ONE:
            # Use upsert to avoid duplicate key errors
            filter_query = query.query.copy()
            if 'playerid' in filter_query:
                filter_doc = {'playerid': filter_query['playerid']}
            elif 'gameid' in filter_query:
                filter_doc = {'gameid': filter_query['gameid']}
            else:
                filter_doc = filter_query
            
            result = collection.replace_one(filter_doc, query.query, upsert=True)
            results_count = 1 if result.upserted_id or result.modified_count else 0
            
        elif query.operation == QueryType.INSERT_MANY:
            # For insert_many, we'll need to handle duplicates differently
            try:
                result = collection.insert_many(query.query, ordered=False)
                results_count = len(result.inserted_ids)
            except Exception as e:
                # If there are duplicate key errors, try to insert one by one with upsert
                results_count = 0
                for doc in query.query:
                    try:
                        if 'playerid' in doc:
                            filter_doc = {'playerid': doc['playerid']}
                        elif 'gameid' in doc:
                            filter_doc = {'gameid': doc['gameid']}
                        else:
                            filter_doc = doc
                        
                        upsert_result = collection.replace_one(filter_doc, doc, upsert=True)
                        if upsert_result.upserted_id or upsert_result.modified_count:
                            results_count += 1
                    except Exception:
                        pass  # Skip individual failures
            
        elif query.operation == QueryType.UPDATE_ONE:
            result = collection.update_one(query.query, query.update_doc)
            results_count = result.modified_count
            
        elif query.operation == QueryType.UPDATE_MANY:
            result = collection.update_many(query.query, query.update_doc)
            results_count = result.modified_count
            
        elif query.operation == QueryType.DELETE_ONE:
            result = collection.delete_one(query.query)
            results_count = result.deleted_count
            
        elif query.operation == QueryType.DELETE_MANY:
            result = collection.delete_many(query.query)
            results_count = result.deleted_count
            
        elif query.operation == QueryType.AGGREGATE:
            cursor = collection.aggregate(query.pipeline)
            result = list(cursor)
            results_count = len(result)
        
        end_time = time.perf_counter()
        execution_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
    except PyMongoError as e:
        error_message = str(e)
        print(f"Error executing query '{query.name}': {error_message}")
        execution_time = None
        results_count = 0
    except Exception as e:
        error_message = str(e)
        print(f"Unexpected error executing query '{query.name}': {error_message}")
        execution_time = None
        results_count = 0
    
    return {
        "execution_time": execution_time,
        "results_count": results_count,
        "error": error_message
    }

def create_average_result(query_name: str, collection: str, operation: str, times: List[float], results_count: int) -> Dict[str, Any]:
    """
    Create a result dictionary with averaged execution times.
    
    Args:
        query_name: Name of the query
        collection: Collection name
        operation: Operation type
        times: List of execution times
        results_count: Number of results affected/returned
        
    Returns:
        Dictionary containing averaged execution statistics
    """
    valid_times = [t for t in times if t is not None]
    
    if valid_times:
        avg_time = sum(valid_times) / len(valid_times)
        min_time = min(valid_times)
        max_time = max(valid_times)
        error_message = None
    else:
        avg_time = min_time = max_time = None
        error_message = "All executions failed"
    
    return {
        "query_name": query_name,
        "collection": collection,
        "operation": operation,
        "average_time_ms": avg_time,
        "min_time_ms": min_time,
        "max_time_ms": max_time,
        "all_times_ms": valid_times,
        "results_count": results_count,
        "sample_size": len(times),
        "error": error_message
    }
