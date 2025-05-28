"""
MongoDB query generator module for benchmark operations.

This module contains functions that generate MongoDB queries for benchmarking
various database operations with configurable scopes and parameters.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum, auto
from datetime import datetime, timedelta
from bson import ObjectId
import time

class QueryType(Enum):
    """Enum representing different types of MongoDB operations."""
    FIND = auto()
    INSERT_ONE = auto()
    INSERT_MANY = auto()
    UPDATE_ONE = auto()
    UPDATE_MANY = auto()
    DELETE_ONE = auto()
    DELETE_MANY = auto()
    AGGREGATE = auto()

@dataclass
class MongoQuery:
    """
    A class representing a MongoDB benchmark query.
    
    Attributes:
        name: A descriptive name for the query
        collection: MongoDB collection name
        operation: Type of operation (find, insert, update, etc.)
        query: Query filter/document
        update_doc: Update document (for update operations)
        pipeline: Aggregation pipeline (for aggregate operations)
        options: Additional options (limit, sort, etc.)
    """
    name: str
    collection: str
    operation: QueryType
    query: Optional[Dict[str, Any]] = None
    update_doc: Optional[Dict[str, Any]] = None
    pipeline: Optional[List[Dict[str, Any]]] = None
    options: Optional[Dict[str, Any]] = None

def generate_find_query(scope: int = 10000, collection: str = "players") -> MongoQuery:
    """
    Generate a MongoDB find query.
    
    Args:
        scope: Number of documents to find
        collection: Collection to query
        
    Returns:
        MongoQuery object with the generated query
    """
    return MongoQuery(
        name=f"Find {scope} documents from {collection}",
        collection=collection,
        operation=QueryType.FIND,
        query={},
        options={"limit": scope}
    )

def generate_find_with_filter_query(scope: int = 1000, collection: str = "players") -> MongoQuery:
    """
    Generate a MongoDB find query with filtering.
    
    Args:
        scope: Number of documents to find
        collection: Collection to query
        
    Returns:
        MongoQuery object with the generated query
    """
    if collection == "players":
        query_filter = {"country": {"$in": ["United States", "United Kingdom", "Germany"]}}
    elif collection == "games":
        query_filter = {"platform": {"$in": ["PC", "PS4", "PS5"]}}
    elif collection == "achievements":
        query_filter = {"rarity": {"$in": ["Common", "Rare"]}}
    else:
        query_filter = {}
    
    return MongoQuery(
        name=f"Find {scope} filtered documents from {collection}",
        collection=collection,
        operation=QueryType.FIND,
        query=query_filter,
        options={"limit": scope}
    )

def generate_insert_one_query(collection: str = "players") -> MongoQuery:
    """
    Generate a MongoDB insert one query.
    
    Args:
        collection: Collection to insert into
        
    Returns:
        MongoQuery object with the generated query
    """
    # Use timestamp-based unique ID with additional randomness to avoid conflicts
    import random
    timestamp_id = int(time.time() * 1000000) + random.randint(1, 999999)  # Microsecond timestamp + random
    
    if collection == "players":
        document = {
            "playerid": timestamp_id,
            "nickname": f"benchmark_user_{timestamp_id}",
            "country": "PL"
        }
    elif collection == "games":
        document = {
            "gameid": timestamp_id,
            "title": f"Benchmark Game {timestamp_id}",
            "platform": "PC",
            "developers": ["Benchmark Studio"],
            "publishers": ["Benchmark Publisher"],
            "genres": ["Action"],
            "supported_languages": ["English"],
            "release_date": datetime.now()
        }
    else:
        document = {"test_field": f"test_value_{timestamp_id}", "created_at": datetime.now()}
    
    return MongoQuery(
        name=f"Insert single document into {collection}",
        collection=collection,
        operation=QueryType.INSERT_ONE,
        query=document
    )

def generate_insert_many_query(scope: int = 1000, collection: str = "players") -> MongoQuery:
    """
    Generate a MongoDB insert many query.
    
    Args:
        scope: Number of documents to insert
        collection: Collection to insert into
        
    Returns:
        MongoQuery object with the generated query
    """
    documents = []
    
    # Use timestamp-based unique ID with additional randomness to avoid conflicts
    import random
    base_timestamp = int(time.time() * 1000000) + random.randint(1, 999999)  # Microsecond timestamp + random
    
    if collection == "players":
        for i in range(scope):
            documents.append({
                "playerid": base_timestamp + i,
                "nickname": f"bench_user_{base_timestamp + i}",
                "country": "XX"
            })
    elif collection == "games":
        for i in range(scope):
            documents.append({
                "gameid": base_timestamp + i,
                "title": f"Benchmark Game {base_timestamp + i}",
                "platform": "PC",
                "developers": ["Benchmark Studio"],
                "publishers": ["Benchmark Publisher"],
                "genres": ["Action"],
                "supported_languages": ["English"],
                "release_date": datetime.now()
            })
    else:
        for i in range(scope):
            documents.append({
                "test_field": f"test_value_{base_timestamp + i}",
                "created_at": datetime.now()
            })
    
    return MongoQuery(
        name=f"Insert {scope} documents into {collection}",
        collection=collection,
        operation=QueryType.INSERT_MANY,
        query=documents
    )

def generate_update_one_query(collection: str = "players") -> MongoQuery:
    """
    Generate a MongoDB update one query.
    
    Args:
        collection: Collection to update
        
    Returns:
        MongoQuery object with the generated query
    """
    # Target recent benchmark data (within last hour)
    current_time = int(time.time() * 1000000)
    hour_ago = current_time - 3600000000
    
    if collection == "players":
        filter_query = {
            "$or": [
                {"playerid": {"$gte": hour_ago}},
                {"nickname": {"$regex": "^bench.*"}}
            ]
        }
        update_doc = {"$set": {"nickname": "updated_user", "country": "YY"}}
    elif collection == "games":
        filter_query = {
            "$or": [
                {"gameid": {"$gte": hour_ago}},
                {"title": {"$regex": "^Benchmark.*"}}
            ]
        }
        update_doc = {"$set": {"title": "Updated Game", "platform": "PS5"}}
    else:
        filter_query = {"test_field": {"$regex": "^test_value.*"}}
        update_doc = {"$set": {"test_field": "updated_value", "updated_at": datetime.now()}}
    
    return MongoQuery(
        name=f"Update single document in {collection}",
        collection=collection,
        operation=QueryType.UPDATE_ONE,
        query=filter_query,
        update_doc=update_doc
    )

def generate_update_many_query(scope: int = 1000, collection: str = "players") -> MongoQuery:
    """
    Generate a MongoDB update many query.
    
    Args:
        scope: Approximate number of documents to update
        collection: Collection to update
        
    Returns:
        MongoQuery object with the generated query
    """
    # Target recent benchmark data (within last hour) and pattern-based data
    current_time = int(time.time() * 1000000)
    hour_ago = current_time - 3600000000
    
    if collection == "players":
        filter_query = {
            "$or": [
                {"playerid": {"$gte": hour_ago}},
                {"nickname": {"$regex": "^bench.*"}}
            ]
        }
        update_doc = {"$set": {"nickname": "bulk_updated", "country": "ZZ"}}
    elif collection == "games":
        filter_query = {
            "$or": [
                {"gameid": {"$gte": hour_ago}},
                {"title": {"$regex": "^Benchmark.*"}}
            ]
        }
        update_doc = {"$set": {"title": "Bulk Updated Game", "platform": "XBOX"}}
    else:
        filter_query = {"test_field": {"$regex": "^test_value_"}}
        update_doc = {"$set": {"test_field": "bulk_updated", "updated_at": datetime.now()}}
    
    return MongoQuery(
        name=f"Update multiple documents in {collection}",
        collection=collection,
        operation=QueryType.UPDATE_MANY,
        query=filter_query,
        update_doc=update_doc
    )

def generate_delete_one_query(collection: str = "players") -> MongoQuery:
    """
    Generate a MongoDB delete one query.
    
    Args:
        collection: Collection to delete from
        
    Returns:
        MongoQuery object with the generated query
    """
    # Target recent benchmark data (within last hour)
    current_time = int(time.time() * 1000000)
    hour_ago = current_time - 3600000000
    
    if collection == "players":
        filter_query = {
            "$or": [
                {"playerid": {"$gte": hour_ago}},
                {"nickname": {"$regex": "^bench.*"}}
            ]
        }
    elif collection == "games":
        filter_query = {
            "$or": [
                {"gameid": {"$gte": hour_ago}},
                {"title": {"$regex": "^Benchmark.*"}}
            ]
        }
    else:
        filter_query = {"test_field": "updated_value"}
    
    return MongoQuery(
        name=f"Delete single document from {collection}",
        collection=collection,
        operation=QueryType.DELETE_ONE,
        query=filter_query
    )

def generate_delete_many_query(scope: int = 1000, collection: str = "players") -> MongoQuery:
    """
    Generate a MongoDB delete many query.
    
    Args:
        scope: Approximate number of documents to delete
        collection: Collection to delete from
        
    Returns:
        MongoQuery object with the generated query
    """
    # Target recent benchmark data (within last hour) and pattern-based data
    current_time = int(time.time() * 1000000)
    hour_ago = current_time - 3600000000
    
    if collection == "players":
        filter_query = {
            "$or": [
                {"playerid": {"$gte": hour_ago}},
                {"nickname": {"$regex": "^bench.*"}},
                {"nickname": "bulk_updated"}
            ]
        }
    elif collection == "games":
        filter_query = {
            "$or": [
                {"gameid": {"$gte": hour_ago}},
                {"title": {"$regex": "^Benchmark.*"}},
                {"title": "Bulk Updated Game"}
            ]
        }
    else:
        filter_query = {"test_field": "bulk_updated"}
    
    return MongoQuery(
        name=f"Delete multiple documents from {collection}",
        collection=collection,
        operation=QueryType.DELETE_MANY,
        query=filter_query
    )

def generate_aggregation_query(join_count: int = 1) -> MongoQuery:
    """
    Generate MongoDB aggregation queries with different join complexities.
    
    Args:
        join_count: Number of joins to include (1-3)
        
    Returns:
        MongoQuery object with the generated aggregation
    """
    if join_count == 1:
        # Simple lookup (equivalent to SQL JOIN)
        pipeline = [
            {"$lookup": {
                "from": "games",
                "localField": "gameid",
                "foreignField": "gameid",
                "as": "game_info"
            }},
            {"$unwind": "$game_info"},
            {"$project": {
                "playerid": 1,
                "gameid": 1,
                "game_title": "$game_info.title",
                "platform": "$game_info.platform"
            }},
            {"$limit": 1000}
        ]
        
        return MongoQuery(
            name="Simple aggregation (1 lookup)",
            collection="player_games",
            operation=QueryType.AGGREGATE,
            pipeline=pipeline
        )
    
    elif join_count == 2:
        # Medium complexity with multiple lookups
        pipeline = [
            {"$lookup": {
                "from": "achievements",
                "localField": "achievementid",
                "foreignField": "achievementid",
                "as": "achievement_info"
            }},
            {"$unwind": "$achievement_info"},
            {"$lookup": {
                "from": "games",
                "localField": "achievement_info.gameid",
                "foreignField": "gameid",
                "as": "game_info"
            }},
            {"$unwind": "$game_info"},
            {"$project": {
                "playerid": 1,
                "achievement_title": "$achievement_info.title",
                "game_title": "$game_info.title",
                "platform": "$game_info.platform",
                "date_acquired": 1
            }},
            {"$limit": 1000}
        ]
        
        return MongoQuery(
            name="Medium aggregation (2 lookups)",
            collection="history",
            operation=QueryType.AGGREGATE,
            pipeline=pipeline
        )
    
    else:
        # Complex aggregation with filtering and multiple lookups
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        pipeline = [
            {"$match": {"date_acquired": {"$gte": thirty_days_ago}}},
            {"$lookup": {
                "from": "achievements",
                "localField": "achievementid",
                "foreignField": "achievementid",
                "as": "achievement_info"
            }},
            {"$unwind": "$achievement_info"},
            {"$lookup": {
                "from": "games",
                "localField": "achievement_info.gameid",
                "foreignField": "gameid",
                "as": "game_info"
            }},
            {"$unwind": "$game_info"},
            {"$lookup": {
                "from": "prices",
                "localField": "game_info.gameid",
                "foreignField": "gameid",
                "as": "price_info"
            }},
            {"$unwind": "$price_info"},
            {"$lookup": {
                "from": "players",
                "localField": "playerid",
                "foreignField": "playerid",
                "as": "player_info"
            }},
            {"$unwind": "$player_info"},
            {"$project": {
                "player_nickname": "$player_info.nickname",
                "game_title": "$game_info.title",
                "achievement_title": "$achievement_info.title",
                "price_usd": "$price_info.usd",
                "date_acquired": 1,
                "rarity": "$achievement_info.rarity"
            }},
            {"$limit": 1000}
        ]
        
        return MongoQuery(
            name="Complex aggregation (4+ lookups with filtering)",
            collection="history",
            operation=QueryType.AGGREGATE,
            pipeline=pipeline
        )

def generate_text_search_query(search_term: str = "action", collection: str = "games") -> MongoQuery:
    """
    Generate a MongoDB text search query.
    
    Args:
        search_term: Term to search for
        collection: Collection to search in
        
    Returns:
        MongoQuery object with the generated query
    """
    return MongoQuery(
        name=f"Text search for '{search_term}' in {collection}",
        collection=collection,
        operation=QueryType.FIND,
        query={"$text": {"$search": search_term}},
        options={"limit": 1000}
    )

def generate_geospatial_query() -> MongoQuery:
    """
    Generate a MongoDB geospatial query (if location data is available).
    Note: This is a placeholder for potential geospatial queries.
    """
    return MongoQuery(
        name="Geospatial query placeholder",
        collection="players",
        operation=QueryType.FIND,
        query={"country": {"$in": ["United States", "Canada", "Mexico"]}},
        options={"limit": 1000}
    )

def generate_complex_analytical_query() -> MongoQuery:
    """
    Generate complex analytical aggregation query.
    """
    pipeline = [
        {"$group": {
            "_id": "$country",
            "player_count": {"$sum": 1},
            "unique_players": {"$addToSet": "$playerid"}
        }},
        {"$project": {
            "country": "$_id",
            "player_count": 1,
            "unique_count": {"$size": "$unique_players"}
        }},
        {"$sort": {"player_count": -1}},
        {"$limit": 20}
    ]
    
    return MongoQuery(
        name="Complex analytical query (grouping and counting)",
        collection="players",
        operation=QueryType.AGGREGATE,
        pipeline=pipeline
    )
