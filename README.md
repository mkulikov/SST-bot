# SST Bot

Telegram-бот для ежедневной рассылки температуры морской воды (SST) по выбранным станциям Турецкой метеослужбы (mgm.gov.tr).

Работает на **Firebase Functions** (Python 3.12) + **Firestore**.

## Архитектура

- `telegram_webhook` — HTTPS-функция, принимает обновления от Telegram
- `send_daily_reports` — scheduled-функция (каждую минуту), рассылает отчёты пользователям в их указанное время

## Требования

- Node.js 18+
- Python 3.12
- Firebase CLI: `npm install -g firebase-tools`
- Аккаунт Google с Firebase-проектом на **Blaze (pay-as-you-go)** плане

## Деплой на свой Firebase проект

### 1. Создать проект Firebase

1. Зайди на [console.firebase.google.com](https://console.firebase.google.com)
2. Создай новый проект
3. Перейди в **Firestore Database** → нажми **Create database** → выбери регион → Start in production mode
4. Переключи проект на **Blaze** план: Project Settings → Usage and billing → Modify plan

### 2. Включить необходимые API

В [Google Cloud Console](https://console.cloud.google.com) для своего проекта включи:
- [Cloud Firestore API](https://console.developers.google.com/apis/api/firestore.googleapis.com)

Остальные API Firebase CLI включит автоматически при деплое.

### 3. Склонировать репозиторий

```bash
git clone <repo-url>
cd SST-bot
```

### 4. Подключить Firebase CLI к проекту

```bash
firebase login
firebase use <your-project-id>
```

### 5. Создать виртуальное окружение

```bash
cd functions
python3.12 -m venv venv
venv/bin/pip install -r requirements.txt
cd ..
```

> venv нужен только локально для Firebase CLI — в прод не едет.

### 6. Сохранить токен бота в Secret Manager

Получи токен у [@BotFather](https://t.me/BotFather), затем:

```bash
firebase functions:secrets:set BOT_TOKEN
```

Введи токен когда появится запрос.

### 7. Задеплоить

```bash
firebase deploy --only functions,firestore
```

После деплоя в консоли появится URL вида:
```
Function URL (telegram_webhook): https://us-central1-<project-id>.cloudfunctions.net/telegram_webhook
```

### 8. Настроить Telegram Webhook

```bash
curl "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=https://us-central1-<project-id>.cloudfunctions.net/telegram_webhook"
```

Должен вернуться ответ `{"ok":true,"result":true}`.

### 9. Выставить команды бота

```bash
curl "https://api.telegram.org/bot<BOT_TOKEN>/setMyCommands" \
  -H "Content-Type: application/json" \
  -d '{
    "commands": [
      {"command": "start", "description": "Запустить бота"},
      {"command": "stations", "description": "Список доступных станций"},
      {"command": "send", "description": "Отправить отчёт сейчас"},
      {"command": "add", "description": "Добавить станцию: /add <id>"},
      {"command": "list", "description": "Мои станции"},
      {"command": "del", "description": "Удалить станцию: /del <номер>"},
      {"command": "clear", "description": "Удалить все станции"},
      {"command": "time", "description": "Время рассылки: /time HH:MM (UTC+4)"},
      {"command": "status", "description": "Статус и настройки"},
      {"command": "on", "description": "Включить рассылку"},
      {"command": "off", "description": "Выключить рассылку"}
    ]
  }'
```

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Запустить бота |
| `/stations` | Список доступных станций в регионе |
| `/add <id>` | Добавить станцию по ID |
| `/list` | Мои станции |
| `/del <номер>` | Удалить станцию по номеру из `/list` |
| `/clear` | Удалить все станции |
| `/send` | Отправить отчёт сейчас |
| `/time HH:MM` | Время рассылки (UTC+4, Грузия) |
| `/status` | Статус и настройки |
| `/on` / `/off` | Включить / отключить рассылку |

## Структура проекта

```
SST-bot/
├── firebase.json           # конфиг Firebase
├── .firebaserc             # привязка к проекту
├── firestore.rules         # правила доступа Firestore
├── firestore.indexes.json  # индексы Firestore
└── functions/
    ├── main.py             # код функций
    └── requirements.txt    # Python зависимости
```

## Регион и часовой пояс

По умолчанию используется регион **Artvin** (Турция) и часовой пояс **Asia/Tbilisi (UTC+4)**.
Чтобы изменить — отредактируй константы `REGION` и `TZ` в [functions/main.py](functions/main.py).
