"""
MongoDB connection module for database performance testing.

This module provides MongoDB connection utilities and database setup functions.
"""
import os
from typing import Dict, Optional, Any, Union
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection

# MongoDB configuration
MONGO_CONFIG: Dict[str, Union[str, int]] = {
    'host': 'localhost',
    'port': 27017,
    'username': 'admin',
    'password': 'admin',
    'authSource': 'admin'
}

TARGET_DB: str = 'benchmarkdb'
SCRIPT_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_abs_path(filename: str) -> str:
    """Returns absolute path for a given filename."""
    return os.path.join(SCRIPT_DIR, filename)

def get_mongo_client() -> MongoClient:
    """
    Returns a new MongoDB client connection.
    
    Returns:
        A new pymongo MongoClient object.
    """
    # Connect without authentication (MongoDB container running without auth)
    connection_string = f"mongodb://{MONGO_CONFIG['host']}:{MONGO_CONFIG['port']}/"
    print(f"Connecting to MongoDB: {connection_string}")
    return MongoClient(connection_string)

def get_mongo_database(dbname: Optional[str] = None) -> Database:
    """
    Returns a MongoDB database object.
    
    Args:
        dbname: Optional database name. If None, uses TARGET_DB.
        
    Returns:
        A pymongo Database object.
    """
    client = get_mongo_client()
    db_name = dbname or TARGET_DB
    return client[db_name]

def create_database() -> None:
    """Create the benchmarkdb database and initialize collections."""
    try:
        db = get_mongo_database()
        # MongoDB creates database/collections automatically when first document is inserted
        # But we can initialize by creating collections with validators
        print(f"Initializing MongoDB database: {TARGET_DB}")
        
        # Create collections (equivalent to tables)
        collections = [
            'players', 'games', 'prices', 'achievements', 'history',
            'developers', 'publishers', 'genres', 'supported_languages',
            'player_games', 'game_developers', 'game_publishers', 
            'game_genres', 'game_supported_languages'
        ]
        
        for collection_name in collections:
            if collection_name not in db.list_collection_names():
                db.create_collection(collection_name)
                print(f"Created collection: {collection_name}")
            else:
                print(f"Collection already exists: {collection_name}")
        
        print("MongoDB database initialization completed successfully.")
        
    except Exception as e:
        print(f"Error creating MongoDB database: {e}")
        raise

def check_connection() -> None:
    """Test the MongoDB connection."""
    try:
        client = get_mongo_client()
        # Test connection by pinging the server
        client.admin.command('ping')
        print("MongoDB connection successful!")
        
        # List databases to verify access
        databases = client.list_database_names()
        print(f"Available databases: {databases}")
        
        client.close()
        
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        raise

def drop_database() -> None:
    """Drop the benchmark database."""
    try:
        client = get_mongo_client()
        client.drop_database(TARGET_DB)
        print(f"Dropped database: {TARGET_DB}")
        client.close()
    except Exception as e:
        print(f"Error dropping database: {e}")
        raise
