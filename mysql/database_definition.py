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
        gameid INTEGER,
        usd DECIMAL(10,2),
        eur DECIMAL(10,2),
        gbp DECIMAL(10,2),
        jpy DECIMAL(10,2),
        rub DECIMAL(10,2),
        date_acquired DATE NOT NULL,
        FOREIGN KEY (gameid) REFERENCES games(gameid) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS achievements (
        achievementid VARCHAR(50) PRIMARY KEY,
        gameid INTEGER,
        title TEXT,
        description TEXT,
        rarity VARCHAR(15) NOT NULL,
        FOREIGN KEY (gameid) REFERENCES games(gameid)
    );

    CREATE TABLE IF NOT EXISTS history (
        playerid INTEGER,
        achievementid VARCHAR(50),
        date_acquired TIMESTAMP,
        FOREIGN KEY (playerid) REFERENCES players(playerid) ON DELETE CASCADE,
        FOREIGN KEY (achievementid) REFERENCES achievements(achievementid) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS developers (
        id INTEGER AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS publishers (
        id INTEGER AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS genres (
        id INTEGER AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS supported_languages (
        id INTEGER AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS player_games (
        playerid INTEGER,
        gameid INTEGER,
        UNIQUE(playerid, gameid),
        FOREIGN KEY (playerid) REFERENCES players(playerid) ON DELETE CASCADE,
        FOREIGN KEY (gameid) REFERENCES games(gameid) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS game_developers (
        game_id INTEGER,
        developer_id INTEGER,
        UNIQUE(game_id, developer_id),
        FOREIGN KEY (game_id) REFERENCES games(gameid) ON DELETE CASCADE,
        FOREIGN KEY (developer_id) REFERENCES developers(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS game_publishers (
        game_id INTEGER,
        publisher_id INTEGER,
        UNIQUE(game_id, publisher_id),
        FOREIGN KEY (game_id) REFERENCES games(gameid) ON DELETE CASCADE,
        FOREIGN KEY (publisher_id) REFERENCES publishers(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS game_genres (
        game_id INTEGER,
        genre_id INTEGER,
        UNIQUE(game_id, genre_id),
        FOREIGN KEY (game_id) REFERENCES games(gameid) ON DELETE CASCADE,
        FOREIGN KEY (genre_id) REFERENCES genres(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS game_supported_languages (
        game_id INTEGER,
        language_id INTEGER,
        UNIQUE(game_id, language_id),
        FOREIGN KEY (game_id) REFERENCES games(gameid) ON DELETE CASCADE,
        FOREIGN KEY (language_id) REFERENCES supported_languages(id) ON DELETE CASCADE
    ); \
"""

# SQL statement to create all indexes in the database
INDEX_DDL: Final[str] = """
    CREATE INDEX idx_prices_gameid ON prices(gameid);
    CREATE INDEX idx_prices_date ON prices(date_acquired);
    CREATE INDEX idx_achievements_gameid ON achievements(gameid);
    CREATE INDEX idx_history_playerid ON history(playerid);
    CREATE INDEX idx_history_achievementid ON history(achievementid);
    CREATE INDEX idx_history_date ON history(date_acquired);
    CREATE INDEX idx_player_games_playerid ON player_games(playerid);
    CREATE INDEX idx_player_games_game_id ON player_games(gameid);
    CREATE INDEX idx_game_developers_game_id ON game_developers(game_id);
    CREATE INDEX idx_game_publishers_game_id ON game_publishers(game_id);
    CREATE INDEX idx_game_genres_game_id ON game_genres(game_id);
    CREATE INDEX idx_game_languages_game_id ON game_supported_languages(game_id); \
"""