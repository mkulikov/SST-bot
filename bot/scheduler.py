from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import TZ
from db import get_user_stations, get_active_users
from http_client import fetch_sst_data
from report_builder import build_sst_report

scheduler = AsyncIOScheduler(timezone=TZ)


async def send_daily_report(bot: Bot, chat_id: int):
    stations = await get_user_stations(chat_id)
    if not stations:
        return
    sst_data = await fetch_sst_data()
    sst_report = build_sst_report(sst_data, stations)
    await bot.send_message(chat_id, sst_report)


async def schedule_daily_report(bot: Bot, chat_id: int, time_str: str):
    hour, minute = map(int, time_str.split(":"))
    scheduler.add_job(
        send_daily_report,
        trigger="cron",
        hour=hour,
        minute=minute,
        args=[bot, chat_id],
        id=str(chat_id),
        replace_existing=True
    )


async def restore_scheduled_reports(bot):
    users = await get_active_users()
    for chat_id, time_str in users:
        await schedule_daily_report(bot, chat_id, time_str)