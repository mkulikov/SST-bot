import asyncio
import logging

from aiogram import Bot

from config import BOT_TOKEN, LOG_LEVEL
from dispatcher import dp
from http_client import close_http_session, init_http_session
from scheduler import restore_scheduled_reports, scheduler


async def main():
    logging.basicConfig(level=LOG_LEVEL)
    bot = Bot(BOT_TOKEN)
    await init_http_session()
    scheduler.start()
    await restore_scheduled_reports(bot)
    try:
        await dp.start_polling(bot)
    finally:
        await close_http_session()


if __name__ == "__main__":
    asyncio.run(main())
