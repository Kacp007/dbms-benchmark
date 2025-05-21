import argparse
import os

# Import modules from the db package
from db.connection import create_database, check_connection
from db.schema import create_tables
from db.data_loader import load_all
from db.benchmark import run_benchmarks, RESULTS_FILE

def main():
    """
    Main entry point for the benchmark application.
    Parses command line arguments and executes the appropriate action.
    """
    parser = argparse.ArgumentParser(description='Load CSVs and prepare benchmarking DB')
    parser.add_argument('--load', action='store_true', help='Create schema and load data')
    parser.add_argument('--data-cap', type=int, help='The maximum number of history rows to load', default=100000000)
    parser.add_argument('--check-connection', action='store_true', help='Check only database connection')
    parser.add_argument('--benchmark', action='store_true', help='Run benchmarks')
    args = parser.parse_args()

    if args.check_connection:
        check_connection()
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
        print(f"Wyniki benchmarku zapisane do {RESULTS_FILE}")
    else:
        print("Uruchom z opcją --load, aby utworzyć tabele i zaimportować dane CSV.")
        print("Lub z opcją --check-connection, aby sprawdzić połączenie z bazą danych.")
        print("Lub z opcją --benchmark, aby uruchomić testy wydajnościowe.")

if __name__ == '__main__':
    main()