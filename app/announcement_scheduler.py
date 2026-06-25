from apscheduler.schedulers.asyncio import AsyncIOScheduler
from asyncio import Lock

from app.bot import bot
from app.database.db import cursor, conn
from app.utils.settings import get_setting

lock = Lock()


async def send_next_announcement():

    async with lock:

        group_id = get_setting("group_id")

        if not group_id:
            print("❗ group_id не настроен")
            return

        try:
            group_id = int(group_id)
        except Exception:
            print("❗ group_id некорректный")
            return
        print("QUEUE SIZE:", cursor.execute(
        "SELECT COUNT(*) FROM pending_announcements"
        ).fetchone()[0])
        # =========================
        # берём ПАЧКУ сообщений
        # =========================
        cursor.execute("""
            SELECT id, text
            FROM pending_announcements
            ORDER BY id
            LIMIT 5
        """)

        rows = cursor.fetchall()

        if not rows:
            return

        sent_ids = []

        # =========================
        # отправка пачки
        # =========================
        for announcement_id, text in rows:
            try:
                await bot.send_message(group_id, text)
                sent_ids.append(announcement_id)

            except Exception as e:
                print(f"❗ Ошибка отправки: {e}")

        # =========================
        # удаляем только успешно отправленные
        # =========================
        if sent_ids:
            cursor.executemany("""
                DELETE FROM pending_announcements
                WHERE id = ?
            """, [(i,) for i in sent_ids])

            conn.commit()


scheduler = AsyncIOScheduler()

scheduler.add_job(
    send_next_announcement,
    trigger="cron",
    hour=12,
    minute=0,
    max_instances=1,
    coalesce=True
)