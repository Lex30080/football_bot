from app.database.db import cursor, conn
from app.utils.helpers import get_player_name


# =========================
# ANNOUNCEMENTS
# =========================
def add_announcement(text):
    cursor.execute("""
        INSERT INTO pending_announcements (text)
        VALUES (?)
    """, (text,))
    conn.commit()


# =========================
# FIFA CORE (единственная точка выдачи наград)
# =========================
def give_achievement(player_id: int, ach_type: str, value: int, text: str):

    cursor.execute("""
        SELECT 1
        FROM player_achievements
        WHERE player_id = ? AND type = ? AND value = ?
    """, (player_id, ach_type, value))

    if cursor.fetchone():
        return

    cursor.execute("""
        INSERT INTO player_achievements (player_id, type, value)
        VALUES (?, ?, ?)
    """, (player_id, ach_type, value))

    conn.commit()

    add_announcement(text)


# =========================
# MAIN ENTRY POINT
# =========================
def check_achievements(match_id):

    check_total_matches()
    check_total_goals()
    check_total_draws()
    check_match_goal_record(match_id)
    check_player_match_goal_record(match_id)

    cursor.execute("""
        SELECT DISTINCT player_id
        FROM match_players
        WHERE match_id = ?
    """, (match_id,))

    players = cursor.fetchall()

    for (player_id,) in players:
        check_player_goals(player_id)
        check_player_wins(player_id)
        check_player_matches(player_id)
        check_first_goal(player_id)


# =========================
# PLAYER GOALS
# =========================
def check_player_goals(player_id):

    cursor.execute("""
        SELECT COUNT(*)
        FROM goals
        WHERE scorer_id = ?
    """, (player_id,))

    goals = cursor.fetchone()[0]

    milestones = [10, 25, 50, 100, 150, 200, 250, 300, 400, 500]

    cursor.execute("SELECT name FROM players WHERE id = ?", (player_id,))
    name = cursor.fetchone()[0]

    for m in milestones:
        if goals >= m:
            give_achievement(
                player_id,
                "goals",
                m,
                f"⚽ {name} достиг {m} голов в карьере!"
            )


# =========================
# PLAYER WINS
# =========================
def check_player_wins(player_id):

    cursor.execute("""
        SELECT COUNT(*)
        FROM match_players mp
        JOIN matches m ON mp.match_id = m.id
        WHERE mp.player_id = ?
        AND (
            (mp.team = 'red' AND m.winner = 'red')
            OR
            (mp.team = 'green' AND m.winner = 'green')
        )
    """, (player_id,))

    wins = cursor.fetchone()[0]

    milestones = [10, 25, 50, 75, 100, 150, 200]

    cursor.execute("SELECT name FROM players WHERE id = ?", (player_id,))
    name = cursor.fetchone()[0]

    for m in milestones:
        if wins >= m:
            give_achievement(
                player_id,
                "wins",
                m,
                f"🏆 {name} достиг {m} побед!"
            )


# =========================
# PLAYER MATCHES
# =========================
def check_player_matches(player_id):

    cursor.execute("""
        SELECT COUNT(*)
        FROM match_players mp
        JOIN matches m ON mp.match_id = m.id
        WHERE mp.player_id = ?
        AND m.status = 'finished'
    """, (player_id,))

    matches = cursor.fetchone()[0]

    milestones = [10, 25, 50, 75, 100, 150, 200, 300, 500]

    cursor.execute("SELECT name FROM players WHERE id = ?", (player_id,))
    name = cursor.fetchone()[0]

    for m in milestones:
        if matches >= m:
            give_achievement(
                player_id,
                "matches",
                m,
                f"🎮 {name} сыграл {m} матчей!"
            )


# =========================
# GLOBAL TOTAL MATCHES
# =========================
def check_total_matches():

    cursor.execute("""
        SELECT COUNT(*)
        FROM matches
        WHERE status = 'finished'
    """)

    total = cursor.fetchone()[0]

    milestones = [10, 25, 50, 100, 150, 200, 300, 500, 1000]

    if total in milestones:
        add_announcement(f"🎊 В истории лиги сыгран {total}-й матч!")


# =========================
# GLOBAL TOTAL GOALS
# =========================
def check_total_goals():

    cursor.execute("""
        SELECT COUNT(*)
        FROM goals
    """)

    total = cursor.fetchone()[0]

    milestones = [100, 250, 500, 1000, 1500, 2000, 3000]

    if total in milestones:
        add_announcement(f"⚽ В истории лиги забит {total}-й гол!")


# =========================
# GLOBAL DRAWS
# =========================
def check_total_draws():

    cursor.execute("""
        SELECT COUNT(*)
        FROM matches
        WHERE winner = 'draw'
    """)

    draws = cursor.fetchone()[0]

    milestones = [10, 25, 50, 100, 150, 200]

    if draws in milestones:
        add_announcement(f"🤝 Зафиксирована {draws}-я ничья в истории лиги!")


# =========================
# MATCH RECORD
# =========================
def check_match_goal_record(match_id):

    cursor.execute("""
        SELECT red_score + green_score
        FROM matches
        WHERE id = ?
    """, (match_id,))

    current = cursor.fetchone()[0]

    cursor.execute("""
        SELECT MAX(red_score + green_score)
        FROM matches
        WHERE id <> ?
        AND status = 'finished'
    """, (match_id,))

    previous = cursor.fetchone()[0] or 0

    if current > previous:
        add_announcement(f"🔥 Новый рекорд матча — {current} голов!")


# =========================
# PLAYER MATCH RECORD
# =========================
def check_player_match_goal_record(match_id):

    cursor.execute("""
        SELECT scorer_id, COUNT(*) as goals
        FROM goals
        WHERE match_id = ?
        GROUP BY scorer_id
        ORDER BY goals DESC
        LIMIT 1
    """, (match_id,))

    row = cursor.fetchone()

    if not row:
        return

    player_id, current_record = row

    cursor.execute("""
        SELECT MAX(goal_count)
        FROM (
            SELECT scorer_id, match_id, COUNT(*) as goal_count
            FROM goals
            WHERE match_id <> ?
            GROUP BY scorer_id, match_id
        )
    """, (match_id,))

    previous_record = cursor.fetchone()[0] or 0

    if current_record > previous_record:
        cursor.execute("SELECT name FROM players WHERE id = ?", (player_id,))
        name = cursor.fetchone()[0]

        add_announcement(
            f"🔥 {name} установил рекорд — {current_record} голов за матч!"
        )


# =========================
# FIRST GOAL
# =========================
def check_first_goal(player_id):

    cursor.execute("""
        SELECT COUNT(*)
        FROM goals
        WHERE scorer_id = ?
    """, (player_id,))

    goals = cursor.fetchone()[0]

    if goals == 0:
        return

    cursor.execute("""
        SELECT 1
        FROM player_achievements
        WHERE player_id = ? AND type = 'first_goal'
    """, (player_id,))

    if cursor.fetchone():
        return

    cursor.execute("""
        INSERT INTO player_achievements (player_id, type, value)
        VALUES (?, 'first_goal', 1)
    """, (player_id,))

    conn.commit()

    cursor.execute("SELECT name FROM players WHERE id = ?", (player_id,))
    name = cursor.fetchone()[0]

    add_announcement(f"🎉 {name} открыл счёт голам в лиге!")