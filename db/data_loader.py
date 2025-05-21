import os
import json
import ast
import pandas as pd
import gc  # Garbage collector - do zarządzania pamięcią
import time
from psycopg2 import sql
from db.connection import get_conn, TARGET_DB, get_abs_path
from db.schema import optimize_postgres_for_bulk_load, restore_postgres_settings

# CSV paths configuration
CSV_PATHS = {
    'players': get_abs_path('players.csv'),
    'games': get_abs_path('games.csv'), 
    'prices': get_abs_path('cleaned\prices_cleaned.csv'),
    'achievements': get_abs_path('cleaned/achievements_cleaned.csv'),
    'history': get_abs_path('cleaned\history_cleaned.csv'),
    'library': get_abs_path('cleaned\player_games_cleaned.csv')
}

# Encoding fallbacks
ENCODINGS = ['utf-8', 'latin1']

def load_base_csv(table, csv_path, columns, data_cap=10000000000000000):
    """Uses COPY FROM STDIN with column selection and chunking for large files."""
    total_rows = 0
    chunk_size = 10000000  # Rozmiar pojedynczej partii
    start_time = time.time()
    
    for enc in ENCODINGS:
        try:
            print(f"Próba wczytania {csv_path} z kodowaniem {enc}...")
            
            # Najpierw sprawdź nagłówki pliku CSV
            try:
                # Wczytaj tylko pierwszy wiersz, aby sprawdzić kolumny
                df_headers = pd.read_csv(csv_path, encoding=enc, nrows=1)
                print(f"Wczytano nagłówki {csv_path}. Dostępne kolumny: {df_headers.columns.tolist()}")
                
                # Sprawdź, czy wszystkie wymagane kolumny są dostępne
                for col in columns:
                    if col not in df_headers.columns:
                        print(f"OSTRZEŻENIE: Kolumna {col} nie jest dostępna w pliku {csv_path}")
                        return False
            except Exception as e:
                print(f"Błąd podczas sprawdzania nagłówków: {str(e)}")
                continue
            
            # Przetwarzanie partiami
            chunk_count = 0
            for chunk in pd.read_csv(csv_path, encoding=enc, chunksize=chunk_size, nrows=data_cap):
                chunk_count += 1
                rows_in_chunk = len(chunk)
                total_rows += rows_in_chunk
                
                print(f"Przetwarzanie partii {chunk_count} z {table} ({rows_in_chunk} wierszy)...")
                
                # Wybierz tylko potrzebne kolumny
                chunk_filtered = chunk[columns]
                
                # Zapisz do tymczasowego pliku CSV
                temp_csv = f"temp_{table}_{chunk_count}.csv"
                chunk_filtered.to_csv(temp_csv, index=False)
                
                # Użyj COPY dla przefiltrowanego pliku
                conn = get_conn(TARGET_DB)
                try:
                    cur = conn.cursor()
                    with open(temp_csv, 'r', encoding='utf-8') as f:
                        cols = ','.join(columns)
                        copy = sql.SQL("COPY {table} ({cols}) FROM STDIN WITH CSV HEADER").format(
                            table=sql.Identifier(table),
                            cols=sql.SQL(cols)
                        )
                        cur.copy_expert(copy, f)
                    conn.commit()
                except Exception as e:
                    print(f"Błąd podczas kopiowania danych: {str(e)}")
                    conn.rollback()
                    raise
                finally:
                    cur.close()
                    conn.close()
                
                # Usuń tymczasowy plik
                if os.path.exists(temp_csv):
                    os.remove(temp_csv)
                
                # Wymuś czyszczenie pamięci
                del chunk, chunk_filtered
                gc.collect()
                
                # Raportuj postęp
                elapsed = time.time() - start_time
                rows_per_second = total_rows / elapsed if elapsed > 0 else 0
                print(f"  Postęp: załadowano {total_rows} wierszy, {rows_per_second:.1f} wierszy/s")
            
            print(f"Zakończono ładowanie {table} z {csv_path}. Łącznie wierszy: {total_rows}")
            return True
            
        except UnicodeDecodeError:
            print(f"Nie udało się zdekodować {csv_path} z kodowaniem {enc}, próbuję następne...")
        except Exception as e:
            print(f"Błąd ładowania {table}: {str(e)}")
            if 'temp_csv' in locals() and os.path.exists(temp_csv):
                try:
                    os.remove(temp_csv)
                except:
                    pass
            raise
    
    print(f"BŁĄD: Nie można odczytać {csv_path} z żadnym z kodowań {ENCODINGS}")
    return False

def parse_and_insert_list_field(csv_path, id_col, list_col, lookup_table, junction_table,
                            lookup_fk=None, id_name=None):
    """Parsuje kolumny zawierające listy i wstawia je do tabel łączących."""
    try:
        conn = get_conn(TARGET_DB)
        conn.autocommit = False
        cur = conn.cursor()
        
        total_rows = 0
        chunk_size = 100000
        start_time = time.time()
        chunk_count = 0
        
        # Znajdź poprawne kodowanie pliku
        encoding_to_use = None
        for enc in ENCODINGS:
            try:
                # Próbuj odczytać pierwszy wiersz aby zweryfikować kodowanie
                pd.read_csv(csv_path, encoding=enc, nrows=1)
                encoding_to_use = enc
                print(f"Znaleziono poprawne kodowanie dla {csv_path}: {enc}")
                break
            except UnicodeDecodeError:
                continue
        
        if not encoding_to_use:
            print(f"BŁĄD: Nie znaleziono poprawnego kodowania dla {csv_path}")
            return False
        
        # Przetwarzaj plik partiami
        for chunk_idx, df in enumerate(pd.read_csv(csv_path, usecols=[id_col, list_col],
                                               encoding=encoding_to_use, chunksize=chunk_size)):
            chunk_count += 1
            rows_in_chunk = len(df)
            total_rows += rows_in_chunk
            
            print(f"Przetwarzanie partii {chunk_count} dla {junction_table} ({rows_in_chunk} wierszy)...")
            
            counter = 0
            for _, row in df.iterrows():
                entity_id = row[id_col]
                lst = row[list_col]
                
                if pd.isna(lst) or not lst:
                    continue
                    
                # Próba różnych metod parsowania list
                items = None
                try:
                    # Metoda 1: JSON parsing
                    if isinstance(lst, str) and (lst.startswith('[') or lst.startswith('{')):
                        items = json.loads(lst)
                except json.JSONDecodeError:
                    pass
                
                if items is None:
                    try:
                        # Metoda 2: AST literal evaluation
                        if isinstance(lst, str):
                            items = ast.literal_eval(lst)
                    except (SyntaxError, ValueError):
                        pass
                
                if items is None and isinstance(lst, str):
                    # Metoda 3: Ręczne parsowanie
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
                
                # Jeśli wszystkie metody zawiodły, spróbuj parsowanie jako pojedynczy element
                if items is None:
                    if isinstance(lst, (list, tuple)):
                        items = lst
                    else:
                        items = [lst]
                
                # Upewnij się, że mamy listę
                if not isinstance(items, (list, tuple)):
                    items = [items]
                
                for val in items:
                    if val is None or (isinstance(val, str) and val.strip() == ''):
                        continue
                        
                    if lookup_table:
                        # Utwórz lub znajdź wartość w tabeli poszukiwań
                        try:
                            cur.execute(
                                sql.SQL("INSERT INTO {lookup} (name) VALUES (%s) ON CONFLICT (name) DO NOTHING").format(
                                    lookup=sql.Identifier(lookup_table)
                                ), (str(val),)
                            )

                            cur.execute(
                                sql.SQL("SELECT id FROM {lookup} WHERE name=%s").format(
                                    lookup=sql.Identifier(lookup_table)
                                ), (str(val),)
                            )
                            result = cur.fetchone()
                            if result:
                                lk_id = result[0]

                                # Dodaj do tabeli łączącej
                                cur.execute(
                                    sql.SQL(
                                        "INSERT INTO {junction} ({fk1}, {fk2}) VALUES (%s, %s) ON CONFLICT DO NOTHING").format(
                                        junction=sql.Identifier(junction_table),
                                        fk1=sql.Identifier(id_name),
                                        fk2=sql.Identifier(lookup_fk)
                                    ), (entity_id, lk_id)
                                )
                            else:
                                print(f"UWAGA: Nie znaleziono ID dla wartości '{val}' w tabeli {lookup_table}")
                        except Exception as e:
                            print(f"Błąd podczas wstawiania do tabeli {lookup_table}/{junction_table}: {str(e)}")
                    else:
                        # Wstaw bezpośrednio do tabeli łączącej
                        try:
                            cur.execute(
                                sql.SQL(
                                    "INSERT INTO {junction} ({fk1}, {fk2}) VALUES (%s, %s) ON CONFLICT DO NOTHING").format(
                                    junction=sql.Identifier(junction_table),
                                    fk1=sql.Identifier(id_name),
                                    fk2=sql.Identifier(lookup_fk)
                                ), (entity_id, val)
                            )
                        except Exception as e:
                            print(f"Błąd podczas wstawiania do tabeli {junction_table}: {str(e)}")

                counter += 1
                if counter % 1000 == 0:
                    conn.commit()

            # Zatwierdź zmiany na końcu każdej partii
            conn.commit()

            # Wymuś czyszczenie pamięci
            del df
            gc.collect()

            # Raportuj postęp
            elapsed = time.time() - start_time
            rows_per_second = total_rows / elapsed if elapsed > 0 else 0
            print(f"  Postęp: przetworzono {total_rows} wierszy, {rows_per_second:.1f} wierszy/s")

        print(f"Zakończono przetwarzanie {junction_table}. Łącznie wierszy: {total_rows}")
        return True
    except Exception as e:
        print(f"Błąd w funkcji parse_and_insert_list_field: {str(e)}")
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

def load_all(data_cap):
    """Load all data into the database."""
    # Sprawdź, czy pliki istnieją przed rozpoczęciem ładowania
    missing_files = []
    for file_type, filename in CSV_PATHS.items():
        if not os.path.exists(filename):
            missing_files.append(f"{file_type}: {filename}")

    if missing_files:
        print("BŁĄD: Następujące pliki nie istnieją:")
        for missing in missing_files:
            print(f"  - {missing}")
        print("\nBieżący katalog roboczy:", os.getcwd())
        print("Zawartość bieżącego katalogu:")
        for item in os.listdir():
            print(f"  - {item}")
        return False

    try:
        # Optymalizuj PostgreSQL przed ładowaniem
        optimize_postgres_for_bulk_load()

        # Załaduj tabele bazowe
        print("\n=== ŁADOWANIE TABEL BAZOWYCH ===")
        load_base_csv('players', CSV_PATHS['players'], ['playerid', 'nickname', 'country'])
        load_base_csv('games', CSV_PATHS['games'], ['gameid', 'title', 'platform', 'release_date'])
        load_base_csv('prices', CSV_PATHS['prices'], ['gameid', 'usd', 'eur', 'gbp', 'jpy', 'rub', 'date_acquired'])
        load_base_csv('achievements', CSV_PATHS['achievements'],
                  ['achievementid', 'gameid', 'title', 'description', 'rarity'])
        load_base_csv('history', CSV_PATHS['history'], ['playerid', 'achievementid', 'date_acquired'], data_cap)
        load_base_csv('player_games', get_abs_path('/cleaned/player_games_cleaned.csv'), ['playerid', 'gameid'])

        # Załaduj dane relacyjne
        print("\n=== ŁADOWANIE DANYCH RELACYJNYCH ===")
        cols = [
            ('developers', 'developers', 'game_developers', 'developer_id', 'game_id'),
            ('publishers', 'publishers', 'game_publishers', 'publisher_id', 'game_id'),
            ('genres', 'genres', 'game_genres', 'genre_id', 'game_id'),
            ('supported_languages', 'supported_languages', 'game_supported_languages', 'language_id', 'game_id')
        ]

        for col, lookup, junction, fk, idn in cols:
            print(f"\nPrzetwarzanie relacji {col} -> {junction}...")
            parse_and_insert_list_field(CSV_PATHS['games'], 'gameid', col, lookup, junction, fk, idn)

        print("\nPrzetwarzanie biblioteki gier graczy...")
        parse_and_insert_list_field(CSV_PATHS['library'], 'playerid', 'library', None, 'player_games', 'game_id',
                                'player_id')

        # Przywróć normalne ustawienia PostgreSQL
        restore_postgres_settings()

        return True
    except Exception as e:
        print(f"Błąd podczas ładowania danych: {str(e)}")
        import traceback
        traceback.print_exc()
        return False