from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from apscheduler.jobstores.base import JobLookupError
from datetime import datetime

from config import TZ
from db import ensure_user, update_user, add_station, get_user_stations, delete_station, clear_stations, \
    get_user_settings
from http_client import fetch_sst_data
from report_builder import build_sst_report
from scheduler import scheduler, schedule_daily_report

dp = Dispatcher()


@dp.message(Command("start"))
async def start_command(message: Message):
    await ensure_user(message.chat.id)
    user_settings = await get_user_settings(message.chat.id)
    time_str, enabled = user_settings
    if enabled:
        await schedule_daily_report(message.bot, message.chat.id, time_str)
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
        await schedule_daily_report(message.bot, message.chat.id, time_str)
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
    sst_data = await fetch_sst_data()
    sst_report = build_sst_report(sst_data, stations)
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
    user_settings = await get_user_settings(message.chat.id)
    if not user_settings:
        return await message.answer("User not found")
    time_str, enabled = user_settings
    await schedule_daily_report(message.bot, message.chat.id, time_str)
    return await message.answer("✅ Delivery enabled")


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
