# Telegram Developer Resources - Quick Reference

## 📖 Официальная документация
- **Telegram Bot API:** https://core.telegram.org/bots/api
- **Telegram Mini Apps (Web Apps):** https://core.telegram.org/bots/webapps
- **Introduction to Bots:** https://core.telegram.org/bots
- **BotFather Commands:** https://core.telegram.org/bots#6-botfather

## 🛠 Фреймворки

### Python
- **aiogram 3.x:** https://docs.aiogram.dev (современный, асинхронный)
- **python-telegram-bot:** https://docs.python-telegram-bot.org (классический)

### JavaScript/TypeScript
- **grammY:** https://grammy.dev (рекомендуется)
- **Telegraf:** https://telegraf.js.org
- **node-telegram-bot-api:** https://github.com/yagop/node-telegram-bot-api

### PHP
- **Telegram Bot SDK:** https://telegram-bot-sdk.com

## 💬 Сообщества и поддержка
- **Stack Overflow:** https://stackoverflow.com/questions/tagged/telegram-bot
- **Telegram Bot SDK Community:** https://telegram-bot-sdk.com/community/support/
- **GitHub Issues (aiogram):** https://github.com/aiogram/aiogram/issues
- **GitHub Issues (python-telegram-bot):** https://github.com/python-telegram-bot/python-telegram-bot/issues
- **Reddit r/Telegram:** https://www.reddit.com/r/Telegram/
- **DEV Community:** https://dev.to/t/telegram

## 🧪 Инструменты тестирования
- **ngrok:** https://ngrok.com (локальный тест webhook)
- **Postman:** https://www.postman.com (тестирование API)
- **Telethon:** https://docs.telethon.dev (E2E тестирование)
- **Mockoon:** https://mockoon.com (мок Telegram Bot API)
- **pytest:** https://pytest.org (Python тесты)
- **pytest-asyncio:** https://pytest-asyncio.readthedocs.io

## 🔐 Безопасность
- **Telegram Server IPs:** Динамически меняются - НЕ использовать IP-фильтрацию
- **secret_token:** Основной механизм аутентификации webhook
- **Mini App initData:** Валидировать HMAC на сервере
- **Токен бота:** ТОЛЬКО в environment variables

## 📚 Полезные статьи
- **Two Design Patterns for Telegram Bots:** https://dev.to/madhead/two-design-patterns-for-telegram-bots
- **End-to-end tests for Telegram bots:** https://shallowdepth.online/posts/2021/12/end-to-end-tests-for-telegram-bots
- **How to Write Integration Tests:** https://blog.1a23.com/2020/03/06/how-to-write-integration-tests-for-a-telegram-bot/

## 🎓 Обучение
- **YouTube:** Поиск "aiogram 3 tutorial"
- **YouTube:** Python Telegram Bot official tutorials
- **Context7:** use library /aiogram/aiogram для актуальной документации

## 🚀 Деплой
- **Docker:** Контейнеризация бота
- **Docker Compose:** Оркестрация с Redis/PostgreSQL
- **Reverse Proxy:** Nginx/Caddy для webhook
- **Hosting:** Heroku, Railway, DigitalOcean, VPS

---

*Используй Context7 для получения актуальной документации:*
- `use library /aiogram/aiogram for documentation`
- `use library /python-telegram-bot/python-telegram-bot for documentation`
- `use library /grammyjs/grammY for documentation`
