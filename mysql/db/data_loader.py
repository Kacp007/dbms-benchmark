import os
import json
import ast
import time
import gc  # Garbage collector for memory management
from typing import Dict, List, Any, Optional, Union, Tuple
import pandas as pd
import mysql.connector
from mysql.connector import Error

from db.connection import get_conn, TARGET_DB, get_abs_path

# CSV paths configuration with consistent path separators
CSV_PATHS: Dict[str, str] = {
    'players': get_abs_path('data/cleaned/players.csv'),
    'games': get_abs_path('data/cleaned/games.csv'),
    'prices': get_abs_path('data/cleaned/prices_cleaned.csv'),
    'achievements': get_abs_path('data/cleaned/achievements_cleaned.csv'),
    'history': get_abs_path('data/cleaned/history_cleaned.csv'),
    'library': get_abs_path('data/cleaned/player_games_cleaned.csv')
}

# Encoding fallbacks to try when reading files
ENCODINGS: List[str] = ['utf-8', 'latin1']


def load_base_csv(table: str, csv_path: str, columns: List[str], data_cap: int = 10000000000000000) -> bool:
    """
    Use COPY FROM STDIN with column selection and chunking for large files.
    
    Args:
        table: Target database table name
        csv_path: Path to the CSV file to load
        columns: List of column names to include
        data_cap: Maximum number of rows to load
    
    Returns:
        True if data was loaded successfully, False otherwise
    """
    total_rows = 0
    chunk_size = 10000000  # Size of a single batch
    start_time = time.time()
    
    for enc in ENCODINGS:
        try:
            print(f"Attempting to load {csv_path} with encoding {enc}...")
            
            # First check CSV headers
            try:
                # Read only the first row to check columns
                df_headers = pd.read_csv(csv_path, encoding=enc, nrows=1)
                print(f"Loaded headers from {csv_path}. Available columns: {df_headers.columns.tolist()}")
                
                # Check if all required columns are available
                for col in columns:
                    if col not in df_headers.columns:
                        print(f"WARNING: Column {col} is not available in file {csv_path}")
                        return False
            except Exception as e:
                print(f"Error while checking headers: {str(e)}")
                continue
            
            # Process in batches
            chunk_count = 0
            for chunk in pd.read_csv(csv_path, encoding=enc, chunksize=chunk_size, nrows=data_cap):
                chunk_count += 1
                rows_in_chunk = len(chunk)
                total_rows += rows_in_chunk
                
                print(f"Processing batch {chunk_count} from {table} ({rows_in_chunk} rows)...")
                
                # Select only needed columns
                chunk_filtered = chunk[columns]
                
                # Insert data using MySQL bulk insert with sub-batching
                conn = get_conn(TARGET_DB)
                try:
                    cur = conn.cursor()
                    
                    # Prepare bulk insert statement
                    placeholders = ', '.join(['%s'] * len(columns))
                    insert_sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
                    
                    # Convert DataFrame to list of tuples for bulk insert
                    data_tuples = []
                    for _, row in chunk_filtered.iterrows():
                        # Handle NaN values by converting to None
                        row_data = []
                        for value in row:
                            if pd.isna(value):
                                row_data.append(None)
                            else:
                                row_data.append(value)
                        data_tuples.append(tuple(row_data))
                    
                    # Process in smaller sub-batches to avoid max_allowed_packet limit
                    sub_batch_size = 5000  # Smaller batch size for executemany
                    total_inserted = 0
                    
                    for i in range(0, len(data_tuples), sub_batch_size):
                        sub_batch = data_tuples[i:i + sub_batch_size]
                        try:
                            cur.executemany(insert_sql, sub_batch)
                            total_inserted += len(sub_batch)
                            if total_inserted % 50000 == 0:  # Progress reporting
                                print(f"    Inserted {total_inserted}/{len(data_tuples)} rows...")
                        except mysql.connector.IntegrityError as e:
                            print(f"Duplicate key error in sub-batch {i//sub_batch_size + 1}: {str(e)}. Continuing...")
                            conn.rollback()
                            continue
                        except Exception as e:
                            print(f"Error inserting sub-batch {i//sub_batch_size + 1}: {str(e)}")
                            conn.rollback()
                            raise
                    
                    conn.commit()
                    print(f"    Successfully inserted {total_inserted} rows")
                        
                except Exception as e:
                    print(f"Error during bulk insert: {str(e)}")
                    conn.rollback()
                    raise
                finally:
                    cur.close()
                    conn.close()
                
                # No temporary file to remove in MySQL approach
                
                # Force memory cleanup
                del chunk, chunk_filtered
                gc.collect()
                
                # Report progress
                elapsed = time.time() - start_time
                rows_per_second = total_rows / elapsed if elapsed > 0 else 0
                print(f"  Progress: loaded {total_rows} rows, {rows_per_second:.1f} rows/s")
            
            print(f"Finished loading {table} from {csv_path}. Total rows: {total_rows}")
            return True
            
        except UnicodeDecodeError:
            print(f"Failed to decode {csv_path} with encoding {enc}, trying next...")
        except Exception as e:
            print(f"Error loading {table}: {str(e)}")
            raise
    
    print(f"ERROR: Cannot read {csv_path} with any of the encodings {ENCODINGS}")
    return False


def parse_and_insert_list_field(
    csv_path: str, 
    id_col: str, 
    list_col: str, 
    lookup_table: Optional[str], 
    junction_table: str,
    lookup_fk: Optional[str] = None, 
    id_name: Optional[str] = None
) -> bool:
    """
    Parse columns containing lists and insert them into junction tables.
    
    Args:
        csv_path: Path to the CSV file
        id_col: Column name containing the entity ID
        list_col: Column name containing the list data
        lookup_table: Optional lookup table name for normalized data
        junction_table: Junction table name for many-to-many relationships
        lookup_fk: Foreign key column name in the lookup table
        id_name: ID column name
    
    Returns:
        True if data was loaded successfully, False otherwise
    """
    try:
        conn = get_conn(TARGET_DB)
        conn.autocommit = False
        cur = conn.cursor()
        
        total_rows = 0
        chunk_size = 100000
        start_time = time.time()
        chunk_count = 0
        
        # Find the correct encoding for the file
        encoding_to_use = None
        for enc in ENCODINGS:
            try:
                # Try to read the first row to verify encoding
                pd.read_csv(csv_path, encoding=enc, nrows=1)
                encoding_to_use = enc
                print(f"Found correct encoding for {csv_path}: {enc}")
                break
            except UnicodeDecodeError:
                continue
        
        if not encoding_to_use:
            print(f"ERROR: No valid encoding found for {csv_path}")
            return False
        
        # Process file in batches
        for chunk_idx, df in enumerate(pd.read_csv(csv_path, usecols=[id_col, list_col],
                                               encoding=encoding_to_use, chunksize=chunk_size)):
            chunk_count += 1
            rows_in_chunk = len(df)
            total_rows += rows_in_chunk
            
            print(f"Processing batch {chunk_count} for {junction_table} ({rows_in_chunk} rows)...")
            
            counter = 0
            for _, row in df.iterrows():
                entity_id = row[id_col]
                lst = row[list_col]
                
                if pd.isna(lst) or not lst:
                    continue
                    
                # Try different list parsing methods
                items = None
                try:
                    # Method 1: JSON parsing
                    if isinstance(lst, str) and (lst.startswith('[') or lst.startswith('{')):
                        items = json.loads(lst)
                except json.JSONDecodeError:
                    pass
                
                if items is None:
                    try:
                        # Method 2: AST literal evaluation
                        if isinstance(lst, str):
                            items = ast.literal_eval(lst)
                    except (SyntaxError, ValueError):
                        pass
                
                if items is None and isinstance(lst, str):
                    # Method 3: Manual parsing
                    lst = lst.strip()
                    if lst.startswith('[') and lst.endswith(']'):
                        # Format: ['item1', 'item2', ...]
                        items_str = lst[1:-1].split(',')
                        items = []
                        for item in items_str:
                            item = item.strip()
                            if item.startswith("'") and item.endswith("'"):
                                items.append(item[1:-1])
                            elif item.startswith('"') and item.endswith('"'):
                                items.append(item[1:-1])
                            else:
                                items.append(item)
                
                # If all methods failed, try parsing as a single element
                if items is None:
                    if isinstance(lst, (list, tuple)):
                        items = lst
                    else:
                        items = [lst]
                
                # Make sure we have a list
                if not isinstance(items, (list, tuple)):
                    items = [items]
                
                for val in items:
                    if val is None or (isinstance(val, str) and val.strip() == ''):
                        continue
                        
                    if lookup_table:
                        # Create or find value in lookup table
                        try:
                            cur.execute(
                                f"INSERT INTO {lookup_table} (name) VALUES (%s) ON DUPLICATE KEY UPDATE name=name", 
                                (str(val),)
                            )

                            cur.execute(
                                f"SELECT id FROM {lookup_table} WHERE name=%s", 
                                (str(val),)
                            )
                            result = cur.fetchone()
                            if result:
                                lk_id = result[0]

                                # Add to junction table
                                cur.execute(
                                    f"INSERT INTO {junction_table} ({id_name}, {lookup_fk}) VALUES (%s, %s) ON DUPLICATE KEY UPDATE {id_name}={id_name}", 
                                    (entity_id, lk_id)
                                )
                            else:
                                print(f"WARNING: ID not found for value '{val}' in table {lookup_table}")
                        except Exception as e:
                            print(f"Error inserting into {lookup_table}/{junction_table} tables: {str(e)}")
                    else:
                        # Insert directly into junction table
                        try:
                            cur.execute(
                                f"INSERT INTO {junction_table} ({id_name}, {lookup_fk}) VALUES (%s, %s) ON DUPLICATE KEY UPDATE {id_name}={id_name}", 
                                (entity_id, val)
                            )
                        except Exception as e:
                            print(f"Error inserting into {junction_table} table: {str(e)}")

                counter += 1
                if counter % 1000 == 0:
                    conn.commit()

            # Commit changes at the end of each batch
            conn.commit()

            # Force memory cleanup
            del df
            gc.collect()

            # Report progress
            elapsed = time.time() - start_time
            rows_per_second = total_rows / elapsed if elapsed > 0 else 0
            print(f"  Progress: processed {total_rows} rows, {rows_per_second:.1f} rows/s")

        print(f"Finished processing {junction_table}. Total rows: {total_rows}")
        return True
    except Exception as e:
        print(f"Error in parse_and_insert_list_field function: {str(e)}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals() and conn:
            conn.rollback()
        return False
    finally:
        if 'cur' in locals() and cur:
            cur.close()
        if 'conn' in locals() and conn:
            conn.close()


def load_all(
    data_cap: int = 1000000000000,
    history_cap: Optional[int] = 0,
    load_other_tables: bool = True
) -> bool:
    """
    Load all data into the database.
    
    Args:
        data_cap: Maximum number of rows to load for large tables
        history_cap: Specific cap for history records (overrides data_cap for history)
        load_other_tables: Whether to load tables other than history
        
    Returns:
        True if all data was loaded successfully, False otherwise
    """
    # Check if files exist before starting to load
    missing_files = []
    for file_type, filename in CSV_PATHS.items():
        if not os.path.exists(filename):
            missing_files.append(f"{file_type}: {filename}")

    if missing_files:
        print("ERROR: The following files do not exist:")
        for missing in missing_files:
            print(f"  - {missing}")
        print("\nCurrent working directory:", os.getcwd())
        print("Contents of current directory:")
        for item in os.listdir():
            print(f"  - {item}")
        return False

    try:
        # Optimize MySQL before loading
        from db.schema import optimize_mysql_for_bulk_load
        optimize_mysql_for_bulk_load()

        if load_other_tables:
            # Load base tables (excluding history if history_cap is provided)
            print("\n=== LOADING BASE TABLES ===")
            load_base_csv('players', CSV_PATHS['players'], ['playerid', 'nickname', 'country'])
            load_base_csv('games', CSV_PATHS['games'], ['gameid', 'title', 'platform', 'release_date'])
            load_base_csv('prices', CSV_PATHS['prices'], ['gameid', 'usd', 'eur', 'gbp', 'jpy', 'rub', 'date_acquired'])
            load_base_csv('achievements', CSV_PATHS['achievements'],
                      ['achievementid', 'gameid', 'title', 'description', 'rarity'])
            load_base_csv('player_games', CSV_PATHS['library'], ['playerid', 'gameid'])

            # Load relational data
            print("\n=== LOADING RELATIONAL DATA ===")
            cols = [
                ('developers', 'developers', 'game_developers', 'developer_id', 'game_id'),
                ('publishers', 'publishers', 'game_publishers', 'publisher_id', 'game_id'),
                ('genres', 'genres', 'game_genres', 'genre_id', 'game_id'),
                # ('supported_languages', 'supported_languages', 'game_supported_languages', 'language_id', 'game_id')
            ]

            for col, lookup, junction, fk, idn in cols:
                print(f"\nProcessing relation {col} -> {junction}...")
                parse_and_insert_list_field(CSV_PATHS['games'], 'gameid', col, lookup, junction, fk, idn)

            print("\nProcessing player game libraries...")
            parse_and_insert_list_field(CSV_PATHS['library'], 'playerid', 'library', None, 'player_games', 'game_id',
                                    'player_id')

        # Load history with specific cap if provided
        if history_cap is not None:
            print(f"\n=== LOADING HISTORY (cap: {history_cap} rows) ===")
            load_base_csv('history', CSV_PATHS['history'], 
                         ['playerid', 'achievementid', 'date_acquired'], 
                         history_cap)
        elif load_other_tables:
            # Load history with general data_cap if we're loading all tables
            print(f"\n=== LOADING HISTORY (cap: {data_cap} rows) ===")
            load_base_csv('history', CSV_PATHS['history'], 
                         ['playerid', 'achievementid', 'date_acquired'], 
                         data_cap)

        # Restore normal MySQL settings
        from db.schema import restore_mysql_settings
        restore_mysql_settings()

        return True
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        import traceback
        traceback.print_exc()
        return False