from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.bot import bot
from app.database.db import cursor, conn
from app.config import GROUP_ID


async def send_next_announcement():

    cursor.execute("""
        SELECT id, text
        FROM pending_announcements
        ORDER BY id
        LIMIT 1
    """)

    row = cursor.fetchone()

    if not row:
        return

    announcement_id, text = row

    await bot.send_message(
        GROUP_ID,
        text
    )

    cursor.execute("""
        DELETE FROM pending_announcements
        WHERE id = ?
    """, (announcement_id,))

    conn.commit()


scheduler = AsyncIOScheduler()

scheduler.add_job(
    send_next_announcement,
    trigger="cron",
    hour=12,
    minute=0
)

#==========================
# For testing purposes, send announcements every minute
"""
scheduler.add_job(
    send_next_announcement,
    trigger="interval",
    minutes=1
)"""