import aiohttp
import aiosqlite
import asyncio
import logging
import os
import pytz


from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.base import JobLookupError
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_NAME = "/app/data/bot.db"
REGION = os.getenv("REGION")
TZ = pytz.timezone(os.getenv("TZ"))

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

bot = Bot(BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone=TZ)

http_session: aiohttp.ClientSession | None = None


async def init_http_session():
    global http_session
    if http_session is None:
        http_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            headers={"Origin": "https://mgm.gov.tr"}
        )


async def close_http_session():
    global http_session
    if http_session is not None:
        await http_session.close()
        http_session = None


async def fetch_sst_data():
    if http_session is None:
        raise RuntimeError("HTTP session is not initialized")
    async with http_session.get(
        "https://servis.mgm.gov.tr/web/sondurumlar/denizler",
        ssl=False,
    ) as response:
        response.raise_for_status()
        return await response.json()


async def build_sst_report(station_ids):
    sst_data = await fetch_sst_data()
    report_lines = []
    another_stations = []
    for station in sst_data:
        if station.get("istNo") in station_ids:
            temp = station.get("denizSicaklik")
            county = station.get("il")
            city = station.get("ilce")
            station_id = station.get("istNo")
            report_lines.append(f"{station_id} {city}/{county} {temp}°C")
        elif station.get("il") == REGION:
            another_stations.append(f"{station.get('istNo')}")
    report = "\n".join(report_lines) if report_lines else "No data available"
    if another_stations:
        report += f"\nAnother {REGION} stations: " + " ".join(another_stations)
    return report


async def ensure_user(chat_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (chat_id) VALUES (?)", (chat_id,)
        )
        await db.commit()


async def update_user(chat_id: int, **kwargs):
    async with aiosqlite.connect(DB_NAME) as db:
        for k, v in kwargs.items():
            await db.execute(
                f"UPDATE users SET {k} = ? WHERE chat_id = ?", (v, chat_id)
            )
        await db.commit()


async def get_active_users():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
                "SELECT chat_id, time FROM users WHERE enabled = 1"
        ) as cursor:
            return await cursor.fetchall()


async def add_station(chat_id: int, station: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO stations (chat_id, station) VALUES (?, ?)", (chat_id, station)
        )
        await db.commit()


async def delete_station(chat_id: int, station: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "DELETE FROM stations WHERE chat_id = ? AND station = ?", (chat_id, station)
        )
        await db.commit()


async def clear_stations(chat_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "DELETE FROM stations WHERE chat_id = ?",
            (chat_id,)
        )
        await db.commit()


async def get_user_stations(chat_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
                "SELECT station FROM stations WHERE chat_id = ?", (chat_id,)
        ) as cursor:
            return [row[0] for row in await cursor.fetchall()]


async def get_user_settings(chat_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT time, enabled FROM users WHERE chat_id = ?", (chat_id,)
        ) as cursor:
            return await cursor.fetchone()


async def send_daily_report(chat_id: int):
    stations = await get_user_stations(chat_id)
    if not stations:
        return
    sst_report = await build_sst_report(stations)
    await bot.send_message(chat_id, sst_report)


async def schedule_daily_report(chat_id: int, time_str: str):
    hour, minute = map(int, time_str.split(":"))
    scheduler.add_job(
        send_daily_report,
        trigger="cron",
        hour=hour,
        minute=minute,
        args=[chat_id],
        id=str(chat_id),
        replace_existing=True
    )


async def restore_scheduled_reports():
    scheduler.remove_all_jobs()
    users = await get_active_users()
    for chat_id, time_str in users:
        await schedule_daily_report(chat_id, time_str)


@dp.message(Command("start"))
async def start_command(message: Message):
    await ensure_user(message.chat.id)
    await restore_scheduled_reports()
    await message.answer(
        "🤖 Bot started!\n"
        f"⏰ All times are in {TZ.zone} time \n"
        "/time HH:MM — set delivery time\n"
        "/add <station_id> — add station\n"
        "/list — list stations\n"
        "/del <number from /list> — remove station\n"
        "/clear — remove all stations\n"
        "/send — send report now\n"
        "/status — bot status\n"
        "/on — enable delivery\n"
        "/off — disable delivery"
    )


@dp.message(Command("time"))
async def set_time_command(message: Message):
    try:
        time_str = message.text.split()[1]
        datetime.strptime(time_str, "%H:%M")
        await update_user(message.chat.id, time=time_str)
        await restore_scheduled_reports()
        await message.answer(f"⏰ Time set to {time_str} ({TZ.zone})")
    except (IndexError, ValueError):
        await message.answer("Example: /time 09:00")


@dp.message(Command("add"))
async def add_station_command(message: Message):
    try:
        station_id = int(message.text.split()[1])
        await add_station(message.chat.id, station_id)
        await message.answer(f"✅ Station {station_id} added")
    except (IndexError, ValueError):
        await message.answer("Example: /add 12345")


@dp.message(Command("del"))
async def delete_station_command(message: Message):
    try:
        index = int(message.text.split()[1]) - 1
        stations = await get_user_stations(message.chat.id)
        station = stations[index]
        await delete_station(message.chat.id, station)
        await message.answer(f"🗑 Station {station} removed")
    except (IndexError, ValueError):
        await message.answer("Example: /del 1")


@dp.message(Command("clear"))
async def clear_stations_command(message: Message):
    await clear_stations(message.chat.id)
    await message.answer("🧹 All stations removed")


@dp.message(Command("list"))
async def get_stations_command(message: Message):
    stations = await get_user_stations(message.chat.id)
    if not stations:
        return await message.answer("Stations list is empty")
    stations_report = "\n".join(f"{i+1}. {station}" for i, station in enumerate(stations))
    return await message.answer(stations_report)


@dp.message(Command("send"))
async def send_report_command(message: Message):
    stations = await get_user_stations(message.chat.id)
    if not stations:
        return await message.answer("Stations list is empty")
    sst_report = await build_sst_report(stations)
    return await message.answer(sst_report)


@dp.message(Command("off"))
async def disable_send_command(message: Message):
    await update_user(message.chat.id, enabled=0)
    try:
        scheduler.remove_job(str(message.chat.id))
    except JobLookupError:
        pass
    await message.answer("❌ Delivery disabled")


@dp.message(Command("on"))
async def enable_send_command(message: Message):
    await update_user(message.chat.id, enabled=1)
    await restore_scheduled_reports()
    await message.answer("✅ Delivery enabled")


@dp.message(Command("status"))
async def status_command(message: Message):
    user_settings = await get_user_settings(message.chat.id)
    if not user_settings:
        return await message.answer("User not found")
    time_str, enabled = user_settings
    stations = await get_user_stations(message.chat.id)
    status_text = "✅ enabled" if enabled else "❌ disabled"
    status_report = (
        "📊 *Bot status*\n"
        f"Delivery: {status_text}\n"
        f"Time: {time_str} ({TZ.zone})\n"
        f"Stations: {len(stations)}\n"
    )
    if stations:
        status_report += "\n📍 Stations:\n"
        status_report += "\n".join(f"- {s}" for s in stations)
    return await message.answer(status_report, parse_mode="Markdown")


async def main():
    await init_http_session()
    scheduler.start()
    await restore_scheduled_reports()
    try:
        await dp.start_polling(bot)
    finally:
        await close_http_session()


if __name__ == "__main__":
    asyncio.run(main())
