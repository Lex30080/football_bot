import sqlite3
import os

DB_PATH = "data/football.db"

os.makedirs("data", exist_ok=True)

conn = sqlite3.connect(
    DB_PATH,
    check_same_thread=False
)

cursor = conn.cursor()