from app.database.db import conn, cursor
from app.data import players, player_ratings

def init_database():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        name TEXT UNIQUE,
        rating INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_date TEXT,
        red_score INTEGER DEFAULT 0,
        green_score INTEGER DEFAULT 0,
        winner TEXT,
        status TEXT DEFAULT 'active',
        is_active INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS match_players (
        match_id INTEGER,
        player_id INTEGER,
        team TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id INTEGER,
        scorer_id INTEGER,
        team TEXT
    )
    """)

    conn.commit()


def seed_database():
    for player in players:
        cursor.execute(
            "INSERT OR IGNORE INTO players (name) VALUES (?)",
            (player,)
        )

    for name, rating in player_ratings.items():
        cursor.execute("""
        UPDATE players
        SET rating = ?
        WHERE name = ?
        """, (rating, name))

    conn.commit()

def is_db_empty():
    cursor.execute("SELECT COUNT(*) FROM players")
    return cursor.fetchone()[0] == 0