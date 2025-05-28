"""
Database schema definition module.
Defines SQL statements for creating tables and indexes.
"""
from typing import Final

# SQL statement to create all tables in the database
DDL: Final[str] = """
    CREATE TABLE IF NOT EXISTS players (
        playerid INTEGER PRIMARY KEY,
        nickname VARCHAR(100),
        country VARCHAR(50)
    );

    CREATE TABLE IF NOT EXISTS games (
        gameid INTEGER PRIMARY KEY,
        title VARCHAR(100) NOT NULL,
        platform VARCHAR(20),
        release_date DATE
    );

    CREATE TABLE IF NOT EXISTS prices (
        gameid INTEGER REFERENCES games(gameid) ON DELETE CASCADE,
        usd NUMERIC(10,2),
        eur NUMERIC(10,2),
        gbp NUMERIC(10,2),
        jpy NUMERIC(10,2),
        rub NUMERIC(10,2),
        date_acquired DATE NOT NULL
    );

    CREATE TABLE IF NOT EXISTS achievements (
        achievementid VARCHAR(50) PRIMARY KEY,
        gameid INTEGER REFERENCES games(gameid),
        title TEXT,
        description TEXT,
        rarity VARCHAR(15) NOT NULL
    );

    CREATE TABLE IF NOT EXISTS history (
        playerid INTEGER REFERENCES players(playerid) ON DELETE CASCADE,
        achievementid VARCHAR(50) REFERENCES achievements(achievementid) ON DELETE CASCADE,
        date_acquired TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS developers (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS publishers (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS genres (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS supported_languages (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS player_games (
        playerid INTEGER REFERENCES players(playerid) ON DELETE CASCADE,
        gameid INTEGER REFERENCES games(gameid) ON DELETE CASCADE,
        UNIQUE(playerid, gameid)
    );

    CREATE TABLE IF NOT EXISTS game_developers (
        game_id INTEGER REFERENCES games(gameid) ON DELETE CASCADE,
        developer_id INTEGER REFERENCES developers(id) ON DELETE CASCADE,
        UNIQUE(game_id, developer_id)
    );

    CREATE TABLE IF NOT EXISTS game_publishers (
        game_id INTEGER REFERENCES games(gameid) ON DELETE CASCADE,
        publisher_id INTEGER REFERENCES publishers(id) ON DELETE CASCADE,
        UNIQUE(game_id, publisher_id)
    );

    CREATE TABLE IF NOT EXISTS game_genres (
        game_id INTEGER REFERENCES games(gameid) ON DELETE CASCADE,
        genre_id INTEGER REFERENCES genres(id) ON DELETE CASCADE,
        UNIQUE(game_id, genre_id)
    );

    CREATE TABLE IF NOT EXISTS game_supported_languages (
        game_id INTEGER REFERENCES games(gameid) ON DELETE CASCADE,
        language_id INTEGER REFERENCES supported_languages(id) ON DELETE CASCADE,
        UNIQUE(game_id, language_id)
    ); \
"""

# SQL statement to create all indexes in the database
INDEX_DDL: Final[str] = """
    CREATE INDEX IF NOT EXISTS idx_prices_gameid ON prices(gameid);
    CREATE INDEX IF NOT EXISTS idx_prices_date ON prices(date_acquired);
    CREATE INDEX IF NOT EXISTS idx_achievements_gameid ON achievements(gameid);
    CREATE INDEX IF NOT EXISTS idx_history_playerid ON history(playerid);
    CREATE INDEX IF NOT EXISTS idx_history_achievementid ON history(achievementid);
    CREATE INDEX IF NOT EXISTS idx_history_date ON history(date_acquired);
    CREATE INDEX IF NOT EXISTS idx_player_games_playerid ON player_games(playerid);
    CREATE INDEX IF NOT EXISTS idx_player_games_game_id ON player_games(gameid);
    CREATE INDEX IF NOT EXISTS idx_game_developers_game_id ON game_developers(game_id);
    CREATE INDEX IF NOT EXISTS idx_game_publishers_game_id ON game_publishers(game_id);
    CREATE INDEX IF NOT EXISTS idx_game_genres_game_id ON game_genres(game_id);
    CREATE INDEX IF NOT EXISTS idx_game_languages_game_id ON game_supported_languages(game_id); \
"""