# Forte Business → Telegram Bot

Автоматически парсит курс RUB/KZT с `business.forte.kz` и отдаёт его по команде.

## Установка

```bash
pip install python-telegram-bot playwright httpx beautifulsoup4
playwright install chromium
```

## Настройка

В файле `bot.py` замените:
```python
BOT_TOKEN = "ВАШ_ТОКЕН_ЗДЕСЬ"
```

Или запустите с переменной среды:
```bash
BOT_TOKEN=123456:ABC-токен python bot.py
```

## Команды бота

| Команда    | Описание                          |
|------------|-----------------------------------|
| `/rate`    | Показывает текущий курс RUB/KZT   |
| `/refresh` | Принудительно обновляет курс      |

## Как работает

1. При старте бот делает первый запрос на `business.forte.kz`
2. Курс кешируется на **30 минут**
3. Каждые 30 минут фоновая задача автоматически обновляет кеш
4. При `/rate` — отдаётся из кеша мгновенно
5. При `/refresh` — принудительный запрос в обход кеша

## Структура файлов

```
forte_rates_bot/
├── forte_rates.py   # Парсер + кеш (не трогать)
├── bot.py           # Telegram бот
└── README.md
```

## Изменение интервала обновления

В `bot.py`:
```python
REFRESH_INTERVAL = 1800  # секунды (сейчас 30 мин)
```

В `forte_rates.py`:
```python
rates_cache = RatesCache(ttl=1800)  # время жизни кеша в секундах
```

## Важное замечание

Парсер использует **Playwright** (headless Chromium), потому что сайт ForteBusiness — это
Next.js SPA и данные загружаются через JavaScript. Парсер:
1. Сначала перехватывает API-запросы сайта (быстрее, надёжнее)
2. Если API не перехвачен — парсит отрендеренный HTML

Если сайт изменит структуру — нужно будет обновить функцию `_parse_html` в `forte_rates.py`.
