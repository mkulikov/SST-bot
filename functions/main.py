import pytz
import httpx
from datetime import datetime

from firebase_functions import https_fn, scheduler_fn
from firebase_functions.params import SecretParam
from firebase_admin import initialize_app, firestore
from google.cloud.firestore_v1 import ArrayUnion, ArrayRemove

initialize_app()

BOT_TOKEN = SecretParam("BOT_TOKEN")

REGION = "Artvin"
TZ = pytz.timezone("Asia/Tbilisi")

# ---------------------------------------------------------------------------
# i18n
# ---------------------------------------------------------------------------

STRINGS = {
    "en": {
        "start": (
            "🤖 Bot started!\n\n"
            "⏰ All times are in Georgia time (UTC+4)\n\n"
            "/time HH:MM — set delivery time\n"
            "/add <station_id> — add station\n"
            "/list — list stations\n"
            "/del <number from /list> — remove station\n"
            "/clear — remove all stations\n"
            "/send — send report now\n"
            "/status — bot status\n"
            "/on — enable delivery\n"
            "/off — disable delivery"
        ),
        "time_set": "⏰ Time set to {time} (UTC+4)",
        "time_example": "Example: /time 09:00",
        "station_added": "✅ Station {id} added",
        "station_add_example": "Example: /add 12345",
        "station_removed": "🗑 Station {station} removed",
        "station_del_example": "Example: /del 1",
        "stations_cleared": "🧹 All stations removed",
        "stations_empty": "Stations list is empty",
        "delivery_on": "✅ Delivery enabled",
        "delivery_off": "❌ Delivery disabled",
        "user_not_found": "User not found. Send /start first.",
        "fetch_error": "Error fetching data: {error}",
        "no_data": "No data available",
        "another_stations": "Another {region} stations: {ids}",
        "status_header": "📊 *Bot status*\n\n",
        "status_delivery": "Delivery: {status}\n",
        "status_time": "Time: {time} (UTC+4)\n",
        "status_count": "Stations: {count}\n",
        "status_list_header": "\n📍 Stations:\n",
        "status_enabled": "✅ enabled",
        "status_disabled": "❌ disabled",
        "stations_available": "📡 Available stations in {region}:\n\n{list}\n\nUse /add <id> to subscribe.",
        "stations_all": "📡 All sea stations:\n\n{list}\n\nUse /add <id> to subscribe.",
        "stations_fetch_error": "Error fetching stations: {error}",
    },
    "ru": {
        "start": (
            "🤖 Бот запущен!\n\n"
            "⏰ Всё время указывается по Грузии (UTC+4)\n\n"
            "/time HH:MM — время рассылки\n"
            "/add <id_станции> — добавить станцию\n"
            "/list — список станций\n"
            "/del <номер из /list> — удалить станцию\n"
            "/clear — удалить все станции\n"
            "/send — отправить отчёт сейчас\n"
            "/status — статус бота\n"
            "/on — включить рассылку\n"
            "/off — выключить рассылку"
        ),
        "time_set": "⏰ Время установлено: {time} (UTC+4)",
        "time_example": "Пример: /time 09:00",
        "station_added": "✅ Станция {id} добавлена",
        "station_add_example": "Пример: /add 12345",
        "station_removed": "🗑 Станция {station} удалена",
        "station_del_example": "Пример: /del 1",
        "stations_cleared": "🧹 Все станции удалены",
        "stations_empty": "Список станций пуст",
        "delivery_on": "✅ Рассылка включена",
        "delivery_off": "❌ Рассылка выключена",
        "user_not_found": "Пользователь не найден. Отправьте /start.",
        "fetch_error": "Ошибка получения данных: {error}",
        "no_data": "Нет данных",
        "another_stations": "Другие станции {region}: {ids}",
        "status_header": "📊 *Статус бота*\n\n",
        "status_delivery": "Рассылка: {status}\n",
        "status_time": "Время: {time} (UTC+4)\n",
        "status_count": "Станций: {count}\n",
        "status_list_header": "\n📍 Станции:\n",
        "status_enabled": "✅ включена",
        "status_disabled": "❌ выключена",
        "stations_available": "📡 Доступные станции в регионе {region}:\n\n{list}\n\nДобавить: /add <id>",
        "stations_all": "📡 Все морские станции:\n\n{list}\n\nДобавить: /add <id>",
        "stations_fetch_error": "Ошибка получения станций: {error}",
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    strings = STRINGS.get(lang, STRINGS["en"])
    template = strings.get(key, STRINGS["en"][key])
    return template.format(**kwargs) if kwargs else template


def resolve_lang(language_code: str | None) -> str:
    if language_code and language_code.startswith("ru"):
        return "ru"
    return "en"


# ---------------------------------------------------------------------------
# Telegram helpers
# ---------------------------------------------------------------------------

def tg_send(token: str, chat_id: int, text: str, parse_mode: str = None):
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    httpx.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json=payload,
        timeout=10,
    )


# ---------------------------------------------------------------------------
# SST data
# ---------------------------------------------------------------------------

def fetch_sst_data() -> list:
    with httpx.Client(
        timeout=10,
        verify=False,
        headers={"Origin": "https://mgm.gov.tr"},
    ) as client:
        r = client.get("https://servis.mgm.gov.tr/web/sondurumlar/denizler")
        r.raise_for_status()
        return r.json()


def list_available_stations(lang: str = "en") -> str:
    data = fetch_sst_data()
    regional = [s for s in data if s.get("il") == REGION]
    if regional:
        lines = [f"{s.get('istNo')} — {s.get('ilce')}/{s.get('il')}" for s in regional]
        return t(lang, "stations_available", region=REGION, list="\n".join(lines))
    # fallback — show all
    lines = [f"{s.get('istNo')} — {s.get('ilce')}/{s.get('il')}" for s in data]
    return t(lang, "stations_all", list="\n".join(lines))


def build_report(station_ids: list, lang: str = "en") -> str:
    data = fetch_sst_data()
    lines = []
    other = []
    for s in data:
        if s.get("istNo") in station_ids:
            lines.append(
                f"{s.get('istNo')} {s.get('ilce')}/{s.get('il')} {s.get('denizSicaklik')}°C"
            )
        elif s.get("il") == REGION:
            other.append(str(s.get("istNo")))
    report = "\n".join(lines) if lines else t(lang, "no_data")
    if other:
        report += "\n" + t(lang, "another_stations", region=REGION, ids=" ".join(other))
    return report


# ---------------------------------------------------------------------------
# Firestore helpers
# ---------------------------------------------------------------------------

def get_user(db, chat_id: int) -> dict | None:
    doc = db.collection("users").document(str(chat_id)).get()
    return doc.to_dict() if doc.exists else None


def ensure_user(db, chat_id: int, lang: str = "en"):
    ref = db.collection("users").document(str(chat_id))
    if not ref.get().exists:
        ref.set({"time": "12:00", "enabled": True, "stations": [], "lang": lang})
    else:
        ref.update({"lang": lang})


# ---------------------------------------------------------------------------
# Webhook handler — all Telegram commands
# ---------------------------------------------------------------------------

@https_fn.on_request(secrets=[BOT_TOKEN])
def telegram_webhook(req: https_fn.Request) -> https_fn.Response:
    token = BOT_TOKEN.value
    db = firestore.client()

    data = req.get_json(silent=True)
    if not data:
        return https_fn.Response("OK")

    message = data.get("message") or data.get("edited_message")
    if not message or "text" not in message:
        return https_fn.Response("OK")

    chat_id: int = message["chat"]["id"]
    lang = resolve_lang(message.get("from", {}).get("language_code"))
    parts: list[str] = message["text"].split()
    if not parts or not parts[0].startswith("/"):
        return https_fn.Response("OK")

    cmd = parts[0].split("@")[0].lower()

    if cmd == "/start":
        ensure_user(db, chat_id, lang)
        tg_send(token, chat_id, t(lang, "start"))

    elif cmd == "/time":
        try:
            time_str = parts[1]
            datetime.strptime(time_str, "%H:%M")
            ensure_user(db, chat_id, lang)
            db.collection("users").document(str(chat_id)).update({"time": time_str})
            tg_send(token, chat_id, t(lang, "time_set", time=time_str))
        except (IndexError, ValueError):
            tg_send(token, chat_id, t(lang, "time_example"))

    elif cmd == "/add":
        try:
            station_id = int(parts[1])
            ensure_user(db, chat_id, lang)
            db.collection("users").document(str(chat_id)).update(
                {"stations": ArrayUnion([station_id])}
            )
            tg_send(token, chat_id, t(lang, "station_added", id=station_id))
        except (IndexError, ValueError):
            tg_send(token, chat_id, t(lang, "station_add_example"))

    elif cmd == "/del":
        try:
            index = int(parts[1]) - 1
            user = get_user(db, chat_id)
            if not user:
                tg_send(token, chat_id, t(lang, "user_not_found"))
                return https_fn.Response("OK")
            stations = user.get("stations", [])
            if index < 0 or index >= len(stations):
                raise IndexError
            station = stations[index]
            db.collection("users").document(str(chat_id)).update(
                {"stations": ArrayRemove([station])}
            )
            tg_send(token, chat_id, t(lang, "station_removed", station=station))
        except (IndexError, ValueError):
            tg_send(token, chat_id, t(lang, "station_del_example"))

    elif cmd == "/clear":
        ensure_user(db, chat_id, lang)
        db.collection("users").document(str(chat_id)).update({"stations": []})
        tg_send(token, chat_id, t(lang, "stations_cleared"))

    elif cmd == "/list":
        user = get_user(db, chat_id)
        stations = user.get("stations", []) if user else []
        if not stations:
            tg_send(token, chat_id, t(lang, "stations_empty"))
        else:
            tg_send(token, chat_id, "\n".join(f"{i+1}. {s}" for i, s in enumerate(stations)))

    elif cmd == "/send":
        user = get_user(db, chat_id)
        stations = user.get("stations", []) if user else []
        if not stations:
            tg_send(token, chat_id, t(lang, "stations_empty"))
        else:
            try:
                tg_send(token, chat_id, build_report(stations, lang))
            except Exception as e:
                tg_send(token, chat_id, t(lang, "fetch_error", error=e))

    elif cmd == "/stations":
        try:
            tg_send(token, chat_id, list_available_stations(lang))
        except Exception as e:
            tg_send(token, chat_id, t(lang, "stations_fetch_error", error=e))

    elif cmd == "/on":
        ensure_user(db, chat_id, lang)
        db.collection("users").document(str(chat_id)).update({"enabled": True})
        tg_send(token, chat_id, t(lang, "delivery_on"))

    elif cmd == "/off":
        ensure_user(db, chat_id, lang)
        db.collection("users").document(str(chat_id)).update({"enabled": False})
        tg_send(token, chat_id, t(lang, "delivery_off"))

    elif cmd == "/status":
        user = get_user(db, chat_id)
        if not user:
            tg_send(token, chat_id, t(lang, "user_not_found"))
            return https_fn.Response("OK")
        stations = user.get("stations", [])
        status = t(lang, "status_enabled") if user.get("enabled") else t(lang, "status_disabled")
        text = (
            t(lang, "status_header")
            + t(lang, "status_delivery", status=status)
            + t(lang, "status_time", time=user.get("time", "12:00"))
            + t(lang, "status_count", count=len(stations))
        )
        if stations:
            text += t(lang, "status_list_header") + "\n".join(f"- {s}" for s in stations)
        tg_send(token, chat_id, text, parse_mode="Markdown")

    return https_fn.Response("OK")


# ---------------------------------------------------------------------------
# Scheduled function — runs every minute, sends reports to matching users
# ---------------------------------------------------------------------------

@scheduler_fn.on_schedule(schedule="* * * * *", secrets=[BOT_TOKEN])
def send_daily_reports(event: scheduler_fn.ScheduledEvent) -> None:
    token = BOT_TOKEN.value
    db = firestore.client()

    now = datetime.now(TZ)
    current_time = now.strftime("%H:%M")

    docs = (
        db.collection("users")
        .where("enabled", "==", True)
        .where("time", "==", current_time)
        .stream()
    )

    for doc in docs:
        user = doc.to_dict()
        chat_id = int(doc.id)
        stations = user.get("stations", [])
        if not stations:
            continue
        lang = user.get("lang", "en")
        try:
            tg_send(token, chat_id, build_report(stations, lang))
        except Exception as e:
            print(f"Error sending report to {chat_id}: {e}")
