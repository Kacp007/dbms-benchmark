import re
import os
from typing import Dict, List, Optional, Any
import psycopg2


def baseline_benchmark(
    query: str, 
    conn: psycopg2.extensions.connection, 
    result_file: str, 
    sample_size: int = 5
) -> Dict[str, Any]:
    """
    Benchmark a SQL query using EXPLAIN ANALYZE.
    
    Args:
        query: The SQL query to benchmark
        conn: The database connection object
        result_file: The name of the result file to save the benchmark results
        sample_size: Number of times to run the benchmark
        
    Returns:
        Dict containing average execution time and list of all execution times (ms)
    """
    times: List[float] = []
    for _ in range(sample_size):
        with conn.cursor() as cur:
            cur.execute(f"EXPLAIN ANALYZE {query}")
            result = cur.fetchall()
            for row in result:
                match = re.search(r'Execution Time: ([0-9.]+) ms', row[0])
                if match:
                    times.append(float(match.group(1)))
                    break
                    
    avg_time = sum(times) / len(times) if times else None
    save_benchmark_result(avg_time, result_file)
    return {"average_time_ms": avg_time, "all_times_ms": times}


def save_benchmark_result(avg_time: Optional[float], result_file: str) -> None:
    """
    Save the benchmark result to a file in the /results directory.
    
    If the directory or file does not exist, create them. 
    If the file exists, append the result.
    
    Args:
        avg_time: The average execution time to save
        result_file: The name of the result file
    """
    results_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'results')
    os.makedirs(results_dir, exist_ok=True)
    file_path = os.path.join(results_dir, result_file)
    mode = 'a' if os.path.exists(file_path) else 'w'
    
    with open(file_path, mode) as f:
        if mode == 'w':
            f.write('result\n')
        f.write(f"{avg_time},\n")


def read_sql_file(file_path: str) -> str:
    """
    Reads a SQL file and returns its contents as a single string.
    
    Args:
        file_path: Path to the SQL file
        
    Returns:
        The SQL query as a string
    """
    with open(file_path, 'r') as f:
        return f.read().strip()