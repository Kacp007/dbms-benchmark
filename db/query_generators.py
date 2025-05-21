"""
Query generator module for benchmark operations.

This module contains functions that generate SQL queries for benchmarking
various database operations with configurable scopes and parameters.
"""
from typing import List
from dataclasses import dataclass
from enum import Enum, auto


class QueryType(Enum):
    """Enum representing different types of SQL operations."""
    SELECT = auto()
    INSERT = auto()
    UPDATE = auto()
    DELETE = auto()


@dataclass
class BenchmarkQuery:
    """
    A class representing a benchmark query.
    
    Attributes:
        name: A descriptive name for the query
        sql_text: The SQL query to execute
    """
    name: str
    sql_text: str


def generate_select_query(scope: int = 10000, table: str = "players") -> BenchmarkQuery:
    """
    Generate a parameterized SELECT query.
    
    Args:
        scope: Number of rows to select
        table: Table to select from
        
    Returns:
        BenchmarkQuery object with the generated query
    """
    return BenchmarkQuery(
        f"Select {scope} rows from {table}",
        f"SELECT * FROM {table} LIMIT {scope};"
    )


def generate_insert_query(scope: int = 1, table: str = "players") -> BenchmarkQuery:
    """
    Generate a parameterized INSERT query.
    
    Args:
        scope: Number of rows to insert (1 for single row, >1 for bulk insert)
        table: Table to insert into
        
    Returns:
        BenchmarkQuery object with the generated query
    """
    if scope == 1:
        return BenchmarkQuery(
            f"Insert single row into {table}",
            f"INSERT INTO {table}(playerid, nickname, country) VALUES (9999999, 'bench_user', 'PL');"
        )
    else:
        return BenchmarkQuery(
            f"Bulk insert {scope} rows into {table}",
            f"""
            INSERT INTO {table}(nickname, country)
            SELECT 'user_' || gs, 'XX'
            FROM generate_series(1, {scope}) AS gs;
            """
        )


def generate_update_query(scope: int = 1, table: str = "players") -> BenchmarkQuery:
    """
    Generate a parameterized UPDATE query.
    
    Args:
        scope: Number of rows to update (1 for single row, >1 for bulk update)
        table: Table to update
        
    Returns:
        BenchmarkQuery object with the generated query
    """
    if scope == 1:
        return BenchmarkQuery(
            f"Update single row in {table}",
            f"UPDATE {table} SET country = 'DE' WHERE playerid = 9999999;"
        )
    else:
        return BenchmarkQuery(
            f"Update {scope} rows in {table}",
            f"""
            UPDATE {table}
            SET country = 'ZZ'
            WHERE playerid BETWEEN 2000001 AND {2000000 + scope};
            """
        )


def generate_delete_query(scope: int = 1, table: str = "players") -> BenchmarkQuery:
    """
    Generate a parameterized DELETE query.
    
    Args:
        scope: Number of rows to delete (1 for single row, >1 for bulk delete)
        table: Table to delete from
        
    Returns:
        BenchmarkQuery object with the generated query
    """
    if scope == 1:
        return BenchmarkQuery(
            f"Delete single row from {table}",
            f"DELETE FROM {table} WHERE playerid = 9999999;"
        )
    else:
        return BenchmarkQuery(
            f"Delete {scope} rows from {table}",
            f"""
            DELETE FROM {table} 
            WHERE playerid BETWEEN 2000001 AND {2000000 + scope};
            """
        )


def generate_complex_select_query(join_count: int = 1) -> BenchmarkQuery:
    """
    Generate SELECT queries with different join complexities.
    
    Args:
        join_count: Number of joins to include (1-3)
        
    Returns:
        BenchmarkQuery object with the generated query
    """
    if join_count == 1:
        return BenchmarkQuery(
            "Simple join query (1 join)",
            """
            SELECT p.playerid, p.nickname, g.title
            FROM players p
                JOIN player_games pg ON p.playerid = pg.player_id
                JOIN games g ON pg.game_id = g.gameid
            LIMIT 1000;
            """
        )
    elif join_count == 2:
        return BenchmarkQuery(
            "Medium join query (2 joins)",
            """
            SELECT p.playerid, p.nickname, g.title, a.title AS achievement
            FROM players p
                JOIN history h ON p.playerid = h.playerid
                JOIN achievements a ON h.achievementid = a.achievementid
                JOIN games g ON a.gameid = g.gameid
            LIMIT 1000;
            """
        )
    else:
        return BenchmarkQuery(
            "Complex join query (3+ joins with filtering)",
            """
            SELECT p.nickname, g.title, a.title AS achievement, pr.usd
            FROM players p
                JOIN history h ON p.playerid = h.playerid
                JOIN achievements a ON h.achievementid = a.achievementid
                JOIN games g ON a.gameid = g.gameid
                JOIN prices pr ON g.gameid = pr.gameid
            WHERE h.date_acquired >= CURRENT_DATE - INTERVAL '30 days'
            LIMIT 1000;
            """
        )