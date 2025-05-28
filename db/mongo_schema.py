"""
MongoDB schema definition module.
Defines collections structure and indexes for the gaming database.
"""
from typing import List, Dict, Any
from pymongo import ASCENDING, DESCENDING, TEXT
from pymongo.database import Database
from pymongo.collection import Collection

def create_indexes(db: Database) -> None:
    """
    Create all indexes for MongoDB collections.
    
    Args:
        db: MongoDB database object
    """
    print("Creating MongoDB indexes...")
    
    try:
        # Players collection indexes
        db.players.create_index("playerid", unique=True)
        db.players.create_index("country")
        db.players.create_index("nickname")
        
        # Games collection indexes
        db.games.create_index("gameid", unique=True)
        db.games.create_index("title")
        db.games.create_index("platform")
        db.games.create_index("release_date")
        db.games.create_index([("title", TEXT)])  # Text search index
        
        # Prices collection indexes
        db.prices.create_index("gameid")
        db.prices.create_index("date_acquired")
        db.prices.create_index([("gameid", ASCENDING), ("date_acquired", DESCENDING)])
        
        # Achievements collection indexes
        db.achievements.create_index("achievementid", unique=True)
        db.achievements.create_index("gameid")
        db.achievements.create_index("rarity")
        db.achievements.create_index([("title", TEXT), ("description", TEXT)])
        
        # History collection indexes
        db.history.create_index([("playerid", ASCENDING), ("achievementid", ASCENDING)], unique=True)
        db.history.create_index("playerid")
        db.history.create_index("achievementid")
        db.history.create_index("date_acquired")
        db.history.create_index([("playerid", ASCENDING), ("date_acquired", DESCENDING)])
        
        # Relationship collection indexes
        db.player_games.create_index([("playerid", ASCENDING), ("gameid", ASCENDING)], unique=True)
        db.player_games.create_index("playerid")
        db.player_games.create_index("gameid")
          # Relationship collection indexes - using actual names instead of IDs for simplicity
        db.game_developers.create_index([("gameid", ASCENDING), ("developer", ASCENDING)], unique=True)
        db.game_developers.create_index("gameid")
        db.game_developers.create_index("developer")
        
        db.game_publishers.create_index([("gameid", ASCENDING), ("publisher", ASCENDING)], unique=True)
        db.game_publishers.create_index("gameid")
        db.game_publishers.create_index("publisher")
        
        db.game_genres.create_index([("gameid", ASCENDING), ("genre", ASCENDING)], unique=True)
        db.game_genres.create_index("gameid")
        db.game_genres.create_index("genre")
        
        db.game_supported_languages.create_index([("gameid", ASCENDING), ("language", ASCENDING)], unique=True)
        db.game_supported_languages.create_index("gameid")
        db.game_supported_languages.create_index("language")
        
        # Reference data indexes
        db.developers.create_index("name", unique=True)
        db.publishers.create_index("name", unique=True)
        db.genres.create_index("name", unique=True)
        db.supported_languages.create_index("name", unique=True)
        
        print("MongoDB indexes created successfully.")
        
    except Exception as e:
        print(f"Error creating indexes: {e}")
        raise

def get_collection_schema() -> Dict[str, Dict[str, Any]]:
    """
    Returns the schema definition for each collection.
    This is informational and helps understand the data structure.
    """
    return {
        "players": {
            "playerid": "int (unique)",
            "nickname": "string",
            "country": "string"
        },
        "games": {
            "gameid": "int (unique)",
            "title": "string",
            "platform": "string",
            "developers": "array of strings",
            "publishers": "array of strings", 
            "genres": "array of strings",
            "supported_languages": "array of strings",
            "release_date": "date"
        },
        "prices": {
            "gameid": "int (foreign key)",
            "usd": "decimal",
            "eur": "decimal", 
            "gbp": "decimal",
            "jpy": "decimal",
            "rub": "decimal",
            "date_acquired": "date"
        },
        "achievements": {
            "achievementid": "string (unique)",
            "gameid": "int (foreign key)",
            "title": "string",
            "description": "string",
            "rarity": "string"
        },
        "history": {
            "playerid": "int (foreign key)",
            "achievementid": "string (foreign key)",
            "date_acquired": "datetime"
        },
        "developers": {
            "_id": "ObjectId",
            "name": "string (unique)"
        },
        "publishers": {
            "_id": "ObjectId", 
            "name": "string (unique)"
        },
        "genres": {
            "_id": "ObjectId",
            "name": "string (unique)"
        },
        "supported_languages": {
            "_id": "ObjectId",
            "name": "string (unique)"
        },
        "player_games": {
            "playerid": "int",
            "gameid": "int"
        },
        "game_developers": {
            "game_id": "int",
            "developer_id": "ObjectId"
        },
        "game_publishers": {
            "game_id": "int", 
            "publisher_id": "ObjectId"
        },
        "game_genres": {
            "game_id": "int",
            "genre_id": "ObjectId"
        },
        "game_supported_languages": {
            "game_id": "int",
            "language_id": "ObjectId"
        }
    }

def validate_collection_data(db: Database) -> Dict[str, int]:
    """
    Validate and return document counts for all collections.
    
    Args:
        db: MongoDB database object
        
    Returns:
        Dictionary with collection names and document counts
    """
    collections = [
        'players', 'games', 'prices', 'achievements', 'history',
        'developers', 'publishers', 'genres', 'supported_languages',
        'player_games', 'game_developers', 'game_publishers',
        'game_genres', 'game_supported_languages'
    ]
    
    counts = {}
    for collection_name in collections:
        count = db[collection_name].count_documents({})
        counts[collection_name] = count
        print(f"{collection_name}: {count:,} documents")
    
    return counts
