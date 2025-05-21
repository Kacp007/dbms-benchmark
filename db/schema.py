from database_definition import DDL, INDEX_DDL
from db.connection import get_conn, TARGET_DB

def create_tables():
    """Create all tables in the database using DDL from database_definition."""
    conn = get_conn(TARGET_DB)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(DDL)
        print("Schema created.")
    finally:
        conn.close()

def create_indexes():
    """Create all indexes in the database using INDEX_DDL from database_definition."""
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