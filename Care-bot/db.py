import aiosqlite

DB_PATH = "carebot.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS emotions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            text TEXT,
            sentiment TEXT,
            score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        await db.commit()

async def save_emotion(user_id: int, username: str, text: str, sentiment: str, score: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO emotions (user_id, username, text, sentiment, score) VALUES (?, ?, ?, ?, ?)",
            (user_id, username, text, sentiment, score)
        )
        await db.commit()

async def get_recent(user_id: int, limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT text, sentiment, score, created_at FROM emotions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        )
        rows = await cur.fetchall()
        return rows
