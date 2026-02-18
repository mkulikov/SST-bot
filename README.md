# 🌊 SST Telegram Bot

Telegram bot that sends daily Sea Surface Temperature (SST) reports for selected stations.

Built with:

- Python 3.11+
- aiogram 3
- aiohttp
- aiosqlite
- APScheduler
- Docker & Docker Compose

---

## ⚙️ Environment Configuration

Create file:
```
.env
```
Example:
```dotenv
BOT_TOKEN=123456789:ABCDEF
```

---

## 🐳 Docker Deployment

### Build and run
```bash
docker compose up -d --build
```
### View logs
```bash
docker compose logs -f bot
```
### Stop
```bash
docker compose down
```

---

## 🤖 Bot Commands

| Command           | Description             |
|-------------------|-------------------------|
| /start            | Start the bot           |
| /time HH:MM       | Set daily report time   |
| /add <station_id> | Add station             |
| /list             | Show stations           |
| /del \<number\>   | Delete station          |
| /clear            | Remove all stations     |
| /send             | Send report immediately |
| /status           | Show current status     |
| /on               | Enable notifications    |
| /off              | Disable notifications   |

---