import logging
import os
import pytz


BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_NAME = os.getenv("DB_NAME")
REGION = os.getenv("REGION")
TZ = pytz.timezone(os.getenv("TZ"))

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

