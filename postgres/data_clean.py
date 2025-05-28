import os
import pandas as pd
import argparse
import ast

# ----------------------------------------
# Configuration: input CSV directory and output
# ----------------------------------------
CSV_FILES = {
    'players': 'players.csv',
    'games': 'games.csv',
    'prices': 'prices.csv',
    'achievements': 'achievements.csv',
    'history': 'history.csv',
    'library': 'purchased_games.csv'
}

CLEANED_SUFFIX = '_cleaned.csv'
MISSING_REPORT = 'missing_ids_report.txt'


def clean_prices(games_df, prices_df):
    orig = len(prices_df)
    cleaned = prices_df[prices_df['gameid'].isin(games_df['gameid'])]
    return cleaned, orig - len(cleaned)


def clean_achievements(games_df, ach_df):
    orig = len(ach_df)
    cleaned = ach_df[ach_df['gameid'].isin(games_df['gameid'])]
    return cleaned, orig - len(cleaned)


def clean_history(players_df, ach_clean_df, hist_df):
    orig = len(hist_df)
    mask = (
        hist_df['playerid'].isin(players_df['playerid']) &
        hist_df['achievementid'].isin(ach_clean_df['achievementid'])
    )
    cleaned = hist_df[mask]
    return cleaned, orig - len(cleaned)


def clean_library(players_df, games_df, lib_df):
    lib_df = lib_df.copy()
    lib_df['game_list'] = lib_df['library'].apply(
        lambda x: ast.literal_eval(x) if isinstance(x, str) else []
    )
    exploded = lib_df[['playerid', 'game_list']].explode('game_list')
    exploded.rename(columns={'game_list': 'gameid'}, inplace=True)
    # Count exploded rows
    exploded_count = len(exploded)
    # Filter valid combinations
    mask = (
        exploded['playerid'].isin(players_df['playerid']) &
        exploded['gameid'].isin(games_df['gameid'])
    )
    cleaned = exploded[mask]
    removed = exploded_count - len(cleaned)
    return cleaned, removed


def main(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    report = []

    # Load base tables
    players = pd.read_csv(
        os.path.join(input_dir, CSV_FILES['players']),
        dtype={'playerid': int}
    )
    games = pd.read_csv(
        os.path.join(input_dir, CSV_FILES['games']),
        dtype={'gameid': int}
    )

    # 1. Prices
    prices = pd.read_csv(
        os.path.join(input_dir, CSV_FILES['prices']),
        dtype={'gameid': int}
    )
    prices_clean, rem_prices = clean_prices(games, prices)
    prices_clean.to_csv(
        os.path.join(output_dir, 'prices' + CLEANED_SUFFIX),
        index=False
    )
    report.append(f"prices: removed {rem_prices} of {len(prices)} records")

    # 2. Achievements
    achievements = pd.read_csv(
        os.path.join(input_dir, CSV_FILES['achievements']),
        dtype={'gameid': int}
    )
    ach_clean, rem_ach = clean_achievements(games, achievements)
    ach_clean.to_csv(
        os.path.join(output_dir, 'achievements' + CLEANED_SUFFIX),
        index=False
    )
    report.append(f"achievements: removed {rem_ach} of {len(achievements)} records")

    # 3. History
    history = pd.read_csv(
        os.path.join(input_dir, CSV_FILES['history']),
        dtype={'playerid': int, 'achievementid': str}
    )
    hist_clean, rem_hist = clean_history(players, ach_clean, history)
    hist_clean.to_csv(
        os.path.join(output_dir, 'history' + CLEANED_SUFFIX),
        index=False
    )
    report.append(f"history: removed {rem_hist} of {len(history)} records")

    # 4. Library (purchased_games)
    library = pd.read_csv(
        os.path.join(input_dir, CSV_FILES['library']),
        dtype={'playerid': int, 'library': str}
    )
    lib_clean, rem_lib = clean_library(players, games, library)
    lib_clean.to_csv(
        os.path.join(output_dir, 'player_games' + CLEANED_SUFFIX),
        index=False
    )
    report.append(
        f"purchased_games: removed {rem_lib} of {
            lib_clean.shape[0] + rem_lib
        } exploded records"
    )

    # Write report
    with open(os.path.join(output_dir, MISSING_REPORT), 'w') as f:
        f.write("Data cleaning report:\n")
        f.write("\n".join(report))

    print("Cleaning complete. Report:")
    for line in report:
        print(" -", line)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Clean CSVs for benchmark import'
    )
    parser.add_argument(
        '--input-dir', default='.',
        help='Directory with raw CSV files'
    )
    parser.add_argument(
        '--output-dir', default='./cleaned',
        help='Directory to write cleaned CSVs'
    )
    args = parser.parse_args()
    main(args.input_dir, args.output_dir)
