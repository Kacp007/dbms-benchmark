"""
MongoDB data loader module.

This module contains functions for loading CSV data into MongoDB collections.
"""
import os
import csv
import ast
from typing import List, Dict, Any, Optional
from datetime import datetime
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo import InsertOne

from db.mongo_connection import get_abs_path

def parse_csv_value(value: str, field_type: str = 'string') -> Any:
    """
    Parse a CSV value based on its expected type.
    
    Args:
        value: String value from CSV
        field_type: Expected type ('string', 'int', 'float', 'date', 'list')
        
    Returns:
        Parsed value in appropriate Python type
    """
    if not value or value.strip() == '':
        return None
        
    value = value.strip()
    
    if field_type == 'int':
        return int(value)
    elif field_type == 'float':
        return float(value)
    elif field_type == 'date':
        if value:
            return datetime.strptime(value, '%Y-%m-%d')
        return None
    elif field_type == 'datetime':
        if value:
            # Handle different datetime formats that might be in the CSV
            try:
                return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    return datetime.strptime(value, '%Y-%m-%d')
                except ValueError:
                    return datetime.fromisoformat(value)
        return None
    elif field_type == 'list':
        if value and value != '[]':
            try:
                # Parse array-like strings from CSV
                return ast.literal_eval(value)
            except (ValueError, SyntaxError):
                # If parsing fails, treat as comma-separated string
                return [item.strip() for item in value.split(',')]
        return []
    else:
        return value

def load_players(db: Database, data_folder="data/cleaned", data_cap: Optional[int] = None) -> int:
    """Load players data from CSV into MongoDB."""
    print("Loading players data...")
    
    file_path = get_abs_path(f'{data_folder}/players.csv')
    collection = db.players
    
    # Clear existing data
    collection.delete_many({})
    
    documents = []
    count = 0
    
    with open(file_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if data_cap and count >= data_cap:
                break
                
            document = {
                'playerid': parse_csv_value(row['playerid'], 'int'),
                'nickname': parse_csv_value(row['nickname']),
                'country': parse_csv_value(row['country'])
            }
            documents.append(document)
            count += 1
            
            # Batch insert every 10000 documents
            if len(documents) >= 10000:
                collection.insert_many(documents)
                documents = []
                print(f"Inserted {count:,} players...")
    
    # Insert remaining documents
    if documents:
        collection.insert_many(documents)
    
    print(f"Loaded {count:,} players.")
    return count

def load_games(db: Database, data_folder="data/cleaned", data_cap: Optional[int] = None) -> int:
    """Load games data from CSV into MongoDB."""
    print("Loading games data...")
    
    file_path = get_abs_path(f'{data_folder}/games.csv')
    collection = db.games
    
    # Clear existing data
    collection.delete_many({})
    
    documents = []
    count = 0
    
    with open(file_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if data_cap and count >= data_cap:
                break
                
            document = {
                'gameid': parse_csv_value(row['gameid'], 'int'),
                'title': parse_csv_value(row['title']),
                'platform': parse_csv_value(row['platform']),
                'developers': parse_csv_value(row['developers'], 'list'),
                'publishers': parse_csv_value(row['publishers'], 'list'),
                'genres': parse_csv_value(row['genres'], 'list'),
                'supported_languages': parse_csv_value(row['supported_languages'], 'list'),
                'release_date': parse_csv_value(row['release_date'], 'date')
            }
            documents.append(document)
            count += 1
            
            # Batch insert every 10000 documents
            if len(documents) >= 10000:
                collection.insert_many(documents)
                documents = []
                print(f"Inserted {count:,} games...")
    
    # Insert remaining documents
    if documents:
        collection.insert_many(documents)
    
    print(f"Loaded {count:,} games.")
    return count

def load_achievements(db: Database, data_folder="data/cleaned", data_cap: Optional[int] = None) -> int:
    """Load achievements data from CSV into MongoDB."""
    print("Loading achievements data...")
    
    file_path = get_abs_path(f'{data_folder}/achievements_cleaned.csv')
    collection = db.achievements
    
    # Clear existing data
    collection.delete_many({})
    
    documents = []
    count = 0
    
    with open(file_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if data_cap and count >= data_cap:
                break
                
            document = {
                'achievementid': parse_csv_value(row['achievementid']),
                'gameid': parse_csv_value(row['gameid'], 'int'),
                'title': parse_csv_value(row['title']),
                'description': parse_csv_value(row['description']),
                'rarity': parse_csv_value(row['rarity'])
            }
            documents.append(document)
            count += 1
            
            # Batch insert every 10000 documents
            if len(documents) >= 10000:
                collection.insert_many(documents)
                documents = []
                print(f"Inserted {count:,} achievements...")
    
    # Insert remaining documents
    if documents:
        collection.insert_many(documents)
    
    print(f"Loaded {count:,} achievements.")
    return count

def load_history(db: Database, data_folder="data/cleaned", data_cap: Optional[int] = None) -> int:
    """Load history data from CSV into MongoDB."""
    print("Loading history data...")
    
    file_path = get_abs_path(f'{data_folder}/history_cleaned.csv')
    collection = db.history
    
    # Clear existing data
    collection.delete_many({})
    
    documents = []
    count = 0
    
    with open(file_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if data_cap and count >= data_cap:
                break
                
            document = {
                'playerid': parse_csv_value(row['playerid'], 'int'),
                'achievementid': parse_csv_value(row['achievementid']),
                'date_acquired': parse_csv_value(row['date_acquired'], 'datetime')
            }
            documents.append(document)
            count += 1
            
            # Batch insert every 10000 documents
            if len(documents) >= 10000:
                collection.insert_many(documents)
                documents = []
                print(f"Inserted {count:,} history records...")
    
    # Insert remaining documents
    if documents:
        collection.insert_many(documents)
    
    print(f"Loaded {count:,} history records.")
    return count

def load_prices(db: Database, data_folder="data/cleaned", data_cap: Optional[int] = None) -> int:
    """Load prices data from CSV into MongoDB."""
    print("Loading prices data...")
    
    file_path = get_abs_path(f'{data_folder}/prices_cleaned.csv')
    collection = db.prices
    
    # Clear existing data
    collection.delete_many({})
    
    documents = []
    count = 0
    
    with open(file_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if data_cap and count >= data_cap:
                break
                
            document = {
                'gameid': parse_csv_value(row['gameid'], 'int'),
                'usd': parse_csv_value(row['usd'], 'float'),
                'eur': parse_csv_value(row['eur'], 'float'),
                'gbp': parse_csv_value(row['gbp'], 'float'),
                'jpy': parse_csv_value(row['jpy'], 'float'),
                'rub': parse_csv_value(row['rub'], 'float'),
                'date_acquired': parse_csv_value(row['date_acquired'], 'date')
            }
            documents.append(document)
            count += 1
            
            # Batch insert every 10000 documents
            if len(documents) >= 10000:
                collection.insert_many(documents)
                documents = []
                print(f"Inserted {count:,} prices...")
    
    # Insert remaining documents
    if documents:
        collection.insert_many(documents)
    
    print(f"Loaded {count:,} prices.")
    return count

def load_purchased_games(db: Database, data_folder="data/cleaned", data_cap: Optional[int] = None) -> int:
    """Load purchased games (player_games) data from CSV into MongoDB."""
    print("Loading purchased games data...")
    
    file_path = get_abs_path(f'{data_folder}/player_games_cleaned.csv')
    collection = db.player_games
    
    # Clear existing data
    collection.delete_many({})
    
    documents = []
    count = 0
    
    with open(file_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if data_cap and count >= data_cap:
                break
                
            # The cleaned file already has playerid,gameid columns - no JSON parsing needed
            document = {
                'playerid': parse_csv_value(row['playerid'], 'int'),
                'gameid': parse_csv_value(row['gameid'], 'int')
            }
            documents.append(document)
            count += 1
            
            # Batch insert every 10000 documents
            if len(documents) >= 10000:
                collection.insert_many(documents)
                documents = []
                print(f"Inserted {count:,} player-game relationships...")
    
    # Insert remaining documents
    if documents:
        collection.insert_many(documents)
    
    print(f"Loaded {count:,} player-game relationships.")
    return count
    return count

def load_normalized_game_data(db: Database, data_folder="data/cleaned", data_cap: Optional[int] = None) -> Dict[str, int]:
    """
    Load normalized game data - extract developers, publishers, genres, etc. from games.csv
    and create separate collections with relationships.
    """
    print("Loading normalized game data (developers, publishers, genres, etc.)...")
    
    file_path = get_abs_path(f'{data_folder}/games.csv')
    
    # Collections for normalized data
    developers_collection = db.developers
    publishers_collection = db.publishers
    genres_collection = db.genres
    languages_collection = db.supported_languages
    
    # Relationship collections
    game_developers_collection = db.game_developers
    game_publishers_collection = db.game_publishers
    game_genres_collection = db.game_genres
    game_languages_collection = db.game_supported_languages
    
    # Clear existing data
    developers_collection.delete_many({})
    publishers_collection.delete_many({})
    genres_collection.delete_many({})
    languages_collection.delete_many({})
    game_developers_collection.delete_many({})
    game_publishers_collection.delete_many({})
    game_genres_collection.delete_many({})
    game_languages_collection.delete_many({})
    
    # Sets to track unique values and avoid duplicates
    developers_set = set()
    publishers_set = set()
    genres_set = set()
    languages_set = set()
    
    # Lists for relationship documents
    game_dev_relationships = []
    game_pub_relationships = []
    game_genre_relationships = []
    game_lang_relationships = []
    
    count = 0
    
    with open(file_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if data_cap and count >= data_cap:
                break
                
            gameid = parse_csv_value(row['gameid'], 'int')
            if not gameid:
                continue
                
            # Process developers
            developers = parse_csv_value(row['developers'], 'list')
            if developers:
                for dev in developers:
                    if dev and dev.strip():
                        dev_name = dev.strip()
                        developers_set.add(dev_name)
                        game_dev_relationships.append({
                            'gameid': gameid,
                            'developer': dev_name
                        })
            
            # Process publishers
            publishers = parse_csv_value(row['publishers'], 'list')
            if publishers:
                for pub in publishers:
                    if pub and pub.strip():
                        pub_name = pub.strip()
                        publishers_set.add(pub_name)
                        game_pub_relationships.append({
                            'gameid': gameid,
                            'publisher': pub_name
                        })
            
            # Process genres
            genres = parse_csv_value(row['genres'], 'list')
            if genres:
                for genre in genres:
                    if genre and genre.strip():
                        genre_name = genre.strip()
                        genres_set.add(genre_name)
                        game_genre_relationships.append({
                            'gameid': gameid,
                            'genre': genre_name
                        })
            
            # Process supported languages
            languages = parse_csv_value(row['supported_languages'], 'list')
            if languages:
                for lang in languages:
                    if lang and lang.strip():
                        lang_name = lang.strip()
                        languages_set.add(lang_name)
                        game_lang_relationships.append({
                            'gameid': gameid,
                            'language': lang_name
                        })
            
            count += 1
            if count % 1000 == 0:
                print(f"Processed {count:,} games for normalization...")
    
    # Insert unique values into lookup collections
    results = {}
    
    if developers_set:
        dev_docs = [{'name': dev} for dev in developers_set]
        developers_collection.insert_many(dev_docs)
        results['developers'] = len(dev_docs)
        print(f"Loaded {len(dev_docs)} unique developers")
    
    if publishers_set:
        pub_docs = [{'name': pub} for pub in publishers_set]
        publishers_collection.insert_many(pub_docs)
        results['publishers'] = len(pub_docs)
        print(f"Loaded {len(pub_docs)} unique publishers")
    
    if genres_set:
        genre_docs = [{'name': genre} for genre in genres_set]
        genres_collection.insert_many(genre_docs)
        results['genres'] = len(genre_docs)
        print(f"Loaded {len(genre_docs)} unique genres")
    
    if languages_set:
        lang_docs = [{'name': lang} for lang in languages_set]
        languages_collection.insert_many(lang_docs)
        results['supported_languages'] = len(lang_docs)
        print(f"Loaded {len(lang_docs)} unique supported languages")
    
    # Insert relationships
    if game_dev_relationships:
        game_developers_collection.insert_many(game_dev_relationships)
        results['game_developers'] = len(game_dev_relationships)
        print(f"Loaded {len(game_dev_relationships)} game-developer relationships")
    
    if game_pub_relationships:
        game_publishers_collection.insert_many(game_pub_relationships)
        results['game_publishers'] = len(game_pub_relationships)
        print(f"Loaded {len(game_pub_relationships)} game-publisher relationships")
    
    if game_genre_relationships:
        game_genres_collection.insert_many(game_genre_relationships)
        results['game_genres'] = len(game_genre_relationships)
        print(f"Loaded {len(game_genre_relationships)} game-genre relationships")
    
    if game_lang_relationships:
        game_languages_collection.insert_many(game_lang_relationships)
        results['game_supported_languages'] = len(game_lang_relationships)
        print(f"Loaded {len(game_lang_relationships)} game-language relationships")
    
    print(f"Normalized game data loading completed from {count:,} games.")
    return results

def load_all(db: Database, data_folder="data/cleaned", data_cap: Optional[int] = None) -> Dict[str, int]:
    """
    Load all CSV data into MongoDB collections.
    
    Args:
        db: MongoDB database object
        data_folder: Folder containing CSV files (default: "data/cleaned")
        data_cap: Optional limit on number of records to load per table
        
    Returns:
        Dictionary with collection names and record counts
    """
    print(f"Loading all data into MongoDB from {data_folder} (cap: {data_cap or 'unlimited'})...")
    
    results = {}
    
    try:
        results['players'] = load_players(db, data_folder, data_cap)
        results['games'] = load_games(db, data_folder, data_cap)
        results['achievements'] = load_achievements(db, data_folder, data_cap)
        results['history'] = load_history(db, data_folder, data_cap)
        results['prices'] = load_prices(db, data_folder, data_cap)
        results['player_games'] = load_purchased_games(db, data_folder, data_cap)
        
        # Load normalized game data (developers, publishers, genres, etc.)
        normalized_results = load_normalized_game_data(db, data_folder, data_cap)
        results.update(normalized_results)
        
        print("\nData loading summary:")
        for collection, count in results.items():
            print(f"  {collection}: {count:,} documents")
        
        return results
        
    except Exception as e:
        print(f"Error loading data: {e}")
        raise
