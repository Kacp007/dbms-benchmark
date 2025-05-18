import argparse
import os
import json
import psycopg2
import pandas as pd
import ast
from psycopg2 import sql
import gc  # Garbage collector - do zarządzania pamięcią
import time
from database_definition import DDL, INDEX_DDL

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'postgres', 
    'user': 'postgres',
    'password': 'admin'
}
TARGET_DB = 'benchmarkdb' 
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def get_abs_path(filename):
    return os.path.join(SCRIPT_DIR, filename)

CSV_PATHS = {
    'players': get_abs_path('players.csv'),
    'games': get_abs_path('games.csv'), 
    'prices': get_abs_path('cleaned\prices_cleaned.csv'),
    'achievements': get_abs_path('cleaned/achievements_cleaned.csv'),
    'history': get_abs_path('cleaned\history_cleaned.csv'),
    'library': get_abs_path('cleaned\player_games_cleaned.csv')
}
RESULTS_FILE = get_abs_path('benchmark_results.txt')
ENCODINGS = ['utf-8', 'latin1']


# ----------------------------------------
# Helpers
# ----------------------------------------

def get_conn(dbname=None):
    """Returns a new database connection using a DSN string to avoid encoding issues."""
    # Build DSN string explicitly (ASCII-safe)
    config = DB_CONFIG.copy()
    if dbname:
        config['dbname'] = dbname
        
    dsn = (
        f"host={config['host']} "
        f"port={config['port']} "
        f"dbname={config['dbname']} "
        f"user={config['user']} "
        f"password={config['password']}"
    )
    print(f"Connecting to database with DSN: {dsn}")
    return psycopg2.connect(dsn)

def create_database():
    """Create the benchmarkdb database if it doesn't exist."""
    # Connect to default postgres database
    conn = get_conn()
    conn.autocommit = True  # Required for CREATE DATABASE
    try:
        with conn.cursor() as cur:
            # Check if database exists
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TARGET_DB,))
            exists = cur.fetchone()
            
            if not exists:
                print(f"Creating database {TARGET_DB}...")
                # Escape database name to prevent SQL injection
                create_db_sql = sql.SQL("CREATE DATABASE {}").format(
                    sql.Identifier(TARGET_DB)
                )
                cur.execute(create_db_sql)
                print(f"Database {TARGET_DB} created successfully.")
            else:
                print(f"Database {TARGET_DB} already exists.")

            # Utwórz indeksy po stworzeniu tabel
            print("\n=== TWORZENIE INDEKSÓW ===")
            create_indexes()
    finally:
        conn.close()

# ----------------------------------------
# Create schema
# ----------------------------------------

def create_tables():
    conn = get_conn(TARGET_DB)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(DDL)
        print("Schema created.")
    finally:
        conn.close()

def create_indexes():
    conn = get_conn(TARGET_DB)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(INDEX_DDL)
        print("Indexes created.")
    finally:
        conn.close()

def optimize_postgres_for_bulk_load():
    """Optymalizuje parametry PostgreSQL dla ładowania dużych zbiorów danych."""
    conn = get_conn(TARGET_DB)
    try:
        with conn:
            with conn.cursor() as cur:
                # Zwiększ pamięć roboczą
                cur.execute("SET work_mem = '256MB'")
                
                # Wyłącz autovacuum podczas ładowania
                cur.execute("ALTER TABLE players SET (autovacuum_enabled = false)")
                cur.execute("ALTER TABLE games SET (autovacuum_enabled = false)")
                cur.execute("ALTER TABLE prices SET (autovacuum_enabled = false)")
                cur.execute("ALTER TABLE achievements SET (autovacuum_enabled = false)")
                cur.execute("ALTER TABLE history SET (autovacuum_enabled = false)")
                
                # Inne optymalizacje
                cur.execute("SET maintenance_work_mem = '1GB'")  # Przyspiesza tworzenie indeksów
                cur.execute("SET max_wal_size = '4GB'")          # Zwiększa rozmiar WAL, mniej flushów
                cur.execute("ALTER TABLE prices DISABLE TRIGGER ALL")
        print("PostgreSQL zoptymalizowany dla masowego ładowania.")
    except Exception as e:
        print(f"Błąd podczas optymalizacji PostgreSQL: {str(e)}")
    finally:
        conn.close()

def restore_postgres_settings():
    """Przywraca normalne ustawienia po załadowaniu danych."""
    conn = get_conn(TARGET_DB)
    try:
        with conn:
            with conn.cursor() as cur:
                # Włącz autovacuum ponownie
                try:
                    cur.execute("ALTER TABLE players SET (autovacuum_enabled = true)")
                    cur.execute("ALTER TABLE games SET (autovacuum_enabled = true)")
                    cur.execute("ALTER TABLE prices SET (autovacuum_enabled = true)")
                    cur.execute("ALTER TABLE achievements SET (autovacuum_enabled = true)")
                    cur.execute("ALTER TABLE history SET (autovacuum_enabled = true)")
                    cur.execute("ALTER TABLE prices ENABLE TRIGGER ALL")

                except Exception as e:
                    print(f"Ostrzeżenie przy przywracaniu autovacuum: {str(e)}")
                
                # Wywołaj VACUUM ANALYZE dla lepszych planów zapytań
                try:
                    cur.execute("VACUUM ANALYZE")
                except Exception as e:
                    print(f"Ostrzeżenie przy wykonywaniu VACUUM: {str(e)}")
        print("Przywrócono normalne ustawienia PostgreSQL i wykonano VACUUM ANALYZE.")
    except Exception as e:
        print(f"Błąd podczas przywracania ustawień PostgreSQL: {str(e)}")
    finally:
        conn.close()


# ----------------------------------------
# Bulk load base tables with encoding fallback and chunking
# ----------------------------------------

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

# ----------------------------------------
# Normalize list fields (generic with ast fallback)
# ----------------------------------------
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


# ----------------------------------------
# Full data load
# ----------------------------------------
def load_all(data_cap):
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


# ----------------------------------------
# Benchmark helper (writes to file)
# ----------------------------------------
def benchmark_query(conn, sql_text, params=None):
    with conn.cursor() as cur:
        cur.execute('EXPLAIN ANALYZE ' + sql_text, params or ())
        rows = cur.fetchall()
    plan = '\n'.join(r[0] for r in rows)
    exec_time = None
    for line in rows[-1]:
        if 'Execution Time' in line:
            exec_time = float(line.split()[2])
    with open(RESULTS_FILE, 'a', encoding='utf-8') as f:
        f.write(f"--- QUERY ---\n{sql_text}\nExecution Time: {exec_time} ms\n{plan}\n\n")
    return exec_time, plan


def run_benchmarks():
    conn = get_conn(TARGET_DB)
    tests = []

    # ——— READ (SELECT) ———
    # simple full‐table scans
    tests += [
        ("Select all players (small table)", "SELECT * FROM players;"),
        ("Select first 10k players", "SELECT * FROM players LIMIT 10000;"),
        ("Select 100k rows from history", "SELECT * FROM history LIMIT 100000;"),
    ]
    # selective predicates
    tests += [
        ("Players from US", "SELECT * FROM players WHERE country = 'US';"),
        ("Recent prices (last year)", "SELECT * FROM prices WHERE date_acquired >= CURRENT_DATE - INTERVAL '1 year';"),
    ]
    # joins
    tests += [
        ("Player → their games (1 join)",
         """
         SELECT p.playerid, p.nickname, g.title
         FROM players p
                  JOIN player_games pg ON p.playerid = pg.player_id
                  JOIN games g ON pg.game_id = g.gameid;
         """),
        ("Full achievement chain (3 joins)",
         """
         SELECT p.nickname, g.title, a.title AS achievement
         FROM players p
                  JOIN history h ON p.playerid = h.playerid
                  JOIN achievements a ON h.achievementid = a.achievementid
                  JOIN games g ON a.gameid = g.gameid
         WHERE h.date_acquired >= CURRENT_DATE - INTERVAL '30 days';
         """),
    ]

    # ——— CREATE (INSERT) ———
    # single row
    tests += [
        ("Insert single dummy player",
         "INSERT INTO players(playerid, nickname, country) VALUES (9999999, 'bench_user', 'PL');")
    ]
    # bulk insert via generate_series
    tests += [
        ("Bulk insert 10k players",
         """
         INSERT INTO players(playerid, nickname, country)
         SELECT 2000000 + gs, 'user_' || gs, 'XX'
         FROM generate_series(1, 10000) AS gs;
         """)
    ]

    # ——— UPDATE ———
    # single row
    tests += [
        ("Update one player country",
         "UPDATE players SET country = 'DE' WHERE playerid = 9999999;")
    ]
    # many rows
    tests += [
        ("Update 10k players to country 'ZZ'",
         """
         UPDATE players
         SET country = 'ZZ'
         WHERE playerid BETWEEN 2000001 AND 2010000;
         """)
    ]

    # ——— DELETE ———
    # single row
    tests += [
        ("Delete one dummy player",
         "DELETE FROM players WHERE playerid = 9999999;")
    ]
    # bulk delete
    tests += [
        ("Delete bulk 10k players",
         "DELETE FROM players WHERE playerid BETWEEN 2000001 AND 2010000;")
    ]

    # run all
    print("\n=== STARTING BENCHMARKS ===")
    for name, sql_text in tests:
        print(f"\n--- {name} ---")
        t, plan = benchmark_query(conn, sql_text)
        print(f"Execution time: {t} ms")

    conn.close()


# ----------------------------------------
# Main
# ----------------------------------------
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Load CSVs and prepare benchmarking DB')
    parser.add_argument('--load', action='store_true', help='Create schema and load data')
    parser.add_argument('--data-cap', type=int, help='The maximum number of history rows to load', default=100000000)
    parser.add_argument('--check-connection', action='store_true', help='Check only database connection')
    parser.add_argument('--benchmark', action='store_true', help='Run benchmarks')
    args = parser.parse_args()

    # Jeśli podano katalog z plikami CSV, zaktualizuj ścieżki

    if args.check_connection:
        try:
            print("Sprawdzanie połączenia z bazą danych...")
            # Najpierw połącz z domyślną bazą postgres
            conn = get_conn()
            conn.close()
            print("Połączenie z bazą postgres udane.")

            # Sprawdź, czy istnieje baza benchmarkdb
            conn = get_conn()
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TARGET_DB,))
                exists = cur.fetchone()
            conn.close()

            if exists:
                try:
                    # Sprawdź połączenie z benchmarkdb
                    conn = get_conn(TARGET_DB)
                    conn.close()
                    print(f"Połączenie z bazą {TARGET_DB} udane.")
                except Exception as e:
                    print(f"Nie można połączyć się z bazą {TARGET_DB}: {str(e)}")
            else:
                print(f"Baza danych {TARGET_DB} nie istnieje.")
        except Exception as e:
            print(f"Błąd połączenia: {str(e)}")

    elif args.load:
        print("\n=== INICJALIZACJA BAZY DANYCH ===")
        print("Tworzenie bazy danych...")
        create_database()
        print("Tworzenie tabel...")
        create_tables()
        print("\n=== ŁADOWANIE DANYCH ===")
        if load_all(int(args.data_cap)):
            print("\n=== SUKCES ===")
            print("Dane załadowane pomyślnie.")
        else:
            print("\n=== BŁĄD ===")
            print("Wystąpił błąd podczas ładowania danych.")

    elif args.benchmark:
        print("\n=== URUCHAMIANIE BENCHMARKÓW ===")
        run_benchmarks()
        print(f"Wyniki benchmarku zostaną zapisane do {RESULTS_FILE}")
    else:
        print("Uruchom z opcją --load, aby utworzyć tabele i zaimportować dane CSV.")
        print("Lub z opcją --check-connection, aby sprawdzić połączenie z bazą danych.")
