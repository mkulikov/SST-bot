import os
import pytz


BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_PATH = os.getenv("DB_PATH")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
REGION = os.getenv("REGION")
TZ = pytz.timezone(os.getenv("TZ"))
