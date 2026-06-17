from app.database.db import cursor, conn

def set_setting(key: str, value: str):
    cursor.execute("""
        INSERT INTO settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (key, str(value)))
    conn.commit()


def get_setting(key: str):
    cursor.execute("""
        SELECT value FROM settings WHERE key = ?
    """, (key,))
    row = cursor.fetchone()
    return row[0] if row else None