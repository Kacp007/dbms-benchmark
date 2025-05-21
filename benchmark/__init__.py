"""
Benchmark module for testing database performance.
Contains utilities for running SQL benchmarks and recording results.
"""

from benchmark.run import baseline_benchmark, save_benchmark_result, read_sql_file

__all__ = [
    'baseline_benchmark',
    'save_benchmark_result',
    'read_sql_file'
]