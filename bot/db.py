import aiosqlite

from config import DB_PATH


async def ensure_user(chat_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (chat_id) VALUES (?)", (chat_id,)
        )
        await db.commit()


async def update_user(chat_id: int, **kwargs):
    async with aiosqlite.connect(DB_PATH) as db:
        for k, v in kwargs.items():
            await db.execute(
                f"UPDATE users SET {k} = ? WHERE chat_id = ?", (v, chat_id)
            )
        await db.commit()


async def get_active_users():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
                "SELECT chat_id, time FROM users WHERE enabled = 1"
        ) as cursor:
            return await cursor.fetchall()


async def add_station(chat_id: int, station: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO stations (chat_id, station) VALUES (?, ?)", (chat_id, station)
        )
        await db.commit()


async def delete_station(chat_id: int, station: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM stations WHERE chat_id = ? AND station = ?", (chat_id, station)
        )
        await db.commit()


async def clear_stations(chat_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM stations WHERE chat_id = ?",
            (chat_id,)
        )
        await db.commit()


async def get_user_stations(chat_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
                "SELECT station FROM stations WHERE chat_id = ?", (chat_id,)
        ) as cursor:
            return [row[0] for row in await cursor.fetchall()]


async def get_user_settings(chat_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT time, enabled FROM users WHERE chat_id = ?", (chat_id,)
        ) as cursor:
            return await cursor.fetchone()
