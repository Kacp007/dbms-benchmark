from db.connection import get_conn, TARGET_DB, get_abs_path

# Path for storing benchmark results
RESULTS_FILE = get_abs_path('benchmark_results.txt')

def benchmark_query(conn, sql_text, params=None):
    """
    Execute a query with EXPLAIN ANALYZE and record the results.
    
    Args:
        conn: Database connection object
        sql_text: SQL query to benchmark
        params: Any parameters for the SQL query
        
    Returns:
        Tuple of (execution time in ms, execution plan)
    """
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
    """
    Run a comprehensive set of benchmark tests on the database.
    Tests include SELECT, INSERT, UPDATE, and DELETE operations of various complexity.
    Results are printed to the console and saved to the results file.
    """
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
    
    print(f"Benchmark results written to {RESULTS_FILE}")
    return True