from app.database.db import conn, cursor
from app.data import players, player_ratings

def init_database():
    # creating tables in the database
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        name TEXT UNIQUE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_date TEXT,
        red_score INTEGER DEFAULT 0,
        green_score INTEGER DEFAULT 0,
        winner TEXT,
        status TEXT DEFAULT 'active'       
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

    # need this because I need to save match Id in database not in memory
    try:
        cursor.execute("""
        ALTER TABLE matches
        ADD COLUMN is_active INTEGER DEFAULT 0
        """)
    except:
        pass

    # moving player ratings to db
    try:
        cursor.execute("""
        ALTER TABLE players
        ADD COLUMN rating INTEGER DEFAULT 0
        """)
    except:
        pass

    conn.commit()

    # helper function for DB to add player
    for player in players:
        cursor.execute(
            "INSERT OR IGNORE INTO players (name) VALUES (?)",
            (player,))
    conn.commit()

    # moving rating to DB
    for player_name, rating in player_ratings.items():

        cursor.execute("""
        UPDATE players
        SET rating = ?
        WHERE name = ?
        """, (rating, player_name))

    conn.commit()
