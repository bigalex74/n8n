# Telegram Application Development - Professional Guide

## 📚 Содержание
1. [Архитектура и паттерны проектирования](#архитектура-и-паттерны-проектирования)
2. [Telegram Bot API - методы и типы](#telegram-bot-api---методы-и-типы)
3. [FSM и управление состояниями](#fsm-и-управление-состояниями)
4. [Клавиатуры и кнопки](#клавиатуры-и-кнопки)
5. [Inline Mode](#inline-mode)
6. [Webhook и Long Polling](#webhook-и-long-polling)
7. [Mini Apps (Web Apps)](#mini-apps-web-apps)
8. [Payments API](#payments-api)
9. [Безопасность](#безопасность)
10. [Тестирование](#тестирование)
11. [Обработка ошибок](#обработка-ошибок)
12. [Логирование](#логирование)
13. [Масштабирование](#масштабирование)
14. [Ресурсы для решения проблем](#ресурсы-для-решения-проблем)
15. [Хорошие и плохие примеры](#хорошие-и-плохие-примеры)
16. [Чеклист перед деплоем](#чеклист-перед-деплоем)

---

## Архитектура и паттерны проектирования

### Паттерн 1: Chain of Responsibility (Цепочка обязанностей)
- Все обновления от Telegram API поступают в единую точку
- Каждый обработчик сам решает: обрабатывать обновление или пропустить
- Обработчики объединяются в список и проходят последовательно
- **Ключевое отличие от веб-роутинга:** обработчик сам принимает решение, а не внешний маршрутизатор

### Паттерн 2: FSM (Конечный автомат)
- Состояние хранится ИСКЛЮЧИТЕЛЬНО на сервере
- Направленный граф состояний с предопределёнными переходами
- Переходы чётко разделены: успешные (валидный ввод) и неуспешные (невалидный ввод/ошибки)
- Контекст привязывается к сущности: пользователь в ЛС, группа или конкретный участник

### Комбинированный подход (Рекомендуется)
```
Обновление → Chain of Responsibility → FSM State Transition → Сохранение состояния → Цикл
```

### Правила архитектуры
✅ **ХОРОШО:**
- Изолированные обработчики, самостоятельно фильтрующие обновления
- Серверный граф состояний с явными правилами переходов
- Гарантия, что на одно обновление реагирует только один обработчик
- Явная передача контекста: каждый обработчик принимает `Update` и `Current State`
- Атомарность: только один обработчик финализирует обновление

❌ **ПЛОХО:**
- Попытка внедрить веб-роутинг (Django/Node.js style) для Telegram
- Внешняя маршрутизация обновлений
- Отсутствие серверного контекста
- Параллельная обработка одним обновлением несколькими обработчиками
- Попытка хранить состояние в клиенте

---

## Telegram Bot API - методы и типы

### Базовый формат запроса
```
https://api.telegram.org/bot<token>/METHOD_NAME
```
Параметры передаются через:
- URL query string
- `application/x-www-form-urlencoded`
- `application/json`
- `multipart/form-data` (для файлов)

### Методы получения обновлений
- **getUpdates** - Long Polling (offset, limit 1-100, timeout, allowed_updates)
- **setWebhook** - Webhook с URL и secret_token
- **deleteWebhook** - Удаление webhook
- **getWebhookInfo** - Информация о текущем webhook

### Типы сообщений (Message)
**Медиа:** text, photo, animation, video, audio, document, voice, video_note, sticker
**Платный контент:** paid_media, is_paid_post
**Интерактив:** poll (опросы/квизы), dice (кубики), game, checklist, story
**Геолокация:** location, venue, contact
**Сервисные:** new_chat_members, chat_owner_left, pinned_message, forum_topic_*, giveaway, gift

### MessageEntity (форматирование текста)
bold, italic, underline, strikethrough, code, pre, text_link, text_mention, custom_emoji, spoiler, blockquote, date_time

---

## FSM и управление состояниями

### Принципы FSM
1. Определить все возможные состояния (constants)
2. Определить переходы между состояниями
3. Валидировать ввод перед переходом
4. Сохранять состояние в хранилище (Redis, SQLite, PostgreSQL)
5. Очищать состояние при завершении диалога

### Пример состояний (aiogram)
```python
class UserStates(StatesGroup):
    WAITING_NAME = State()
    WAITING_EMAIL = State()
    WAITING_AGE = State()
    CONFIRMATION = State()
```

### Правила работы с состоянием
✅ Всегда очищать состояние после завершения диалога
✅ Использовать timeout для автоматического сброса состояния
✅ Сохранять промежуточные данные в FSM data
✅ Валидировать данные перед переходом к следующему состоянию

❌ Не хранить состояние в глобальных переменных
❌ Не позволять пользователю "застрять" в состоянии без выхода
❌ Не хранить чувствительные данные в состоянии без шифрования

---

## Клавиатуры и кнопки

### ReplyKeyboardMarkup
Кастомная клавиатура, привязанная к полю ввода.
- `resize_keyboard` - изменить размер
- `one_time_keyboard` - скрыть после использования
- `selective` - показ только выбранным пользователям

### KeyboardButton
Кнопки могут содержать:
- Текст (отправляется как сообщение)
- `request_contact` - запрос контакта
- `request_location` - запрос геолокации
- `request_poll` - запрос опроса
- `request_users`, `request_chat` - запрос сущностей
- `web_app` - запуск Web App
- Стили: `"danger"` (красный), `"success"` (зеленый), `"primary"` (синий)
- `icon_custom_emoji_id` - кастомный эмодзи перед текстом

### InlineKeyboardMarkup
Кнопки под сообщением (не занимают поле ввода).
- `InlineKeyboardButton` с callback_data для обработки нажатий
- `url` - открытие ссылки
- `web_app` - запуск Mini App
- `switch_inline_query` - переход в inline режим

### Лучшие практики для клавиатур
✅ Использовать inline-кнопки для навигации и действий
✅ Использовать reply-клавиатуру только для быстрого ввода
✅ Всегда добавлять кнопку "Отмена" или "Назад"
✅ Ограничивать размер клавиатуры (не более 8 кнопок)

---

## Inline Mode

### Как работает
- Пользователь вводит `@username_бота` и пробел
- Бот получает `inline_query` обновление
- Бот отвечает через `answerInlineQuery` с массивом результатов
- При выборе: бот получает `chosen_inline_result` (требует включения в BotFather)

### Настройка
1. Включить в BotFather: `/setinline`
2. Задать placeholder (текст-подсказка)
3. Включить Inline Feedback для отслеживания выборов

### InlineQueryResult типы
- `InlineQueryResultArticle` - статья с текстом
- `InlineQueryResultPhoto` - фото
- `InlineQueryResultVideo` - видео
- `InlineQueryResultAudio` - аудио
- `InlineQueryResultDocument` - документ
- И другие...

### Кэширование
`cache_time` - сколько секунд Telegram хранит результаты для одинаковых запросов

### Ленивая загрузка (Lazy Loading)
Если загрузка ресурсоемка: выдавать превью, а после выбора (через Inline Feedback) подгружать полный контент.

### Трюк с редактированием
Бот может редактировать inline-сообщение, ТОЛЬКО если в нем есть Inline-кнопки (иначе не передается `message_id`).

### Пример (aiogram)
```python
@dp.inline_query()
async def handle_inline(query: InlineQuery):
    result = InlineQueryResultArticle(
        id='1',
        title='Option 1',
        description='Description',
        input_message_content=InputTextMessageContent(
            message_text='Text to send'
        )
    )
    await query.answer(results=[result], cache_time=1)
```

---

## Webhook и Long Polling

### Long Polling (getUpdates)
✅ Для разработки и тестирования
✅ Для небольших проектов
❌ Задержки в получении обновлений
❌Higher resource usage on client side

### Webhook (setWebhook)
✅ Для продакшена
✅ Мгновенная доставка обновлений
❌ Требует HTTPS и публичный URL

### Настройка Webhook с секретным токеном
```json
{
  "url": "https://yourdomain.com/webhook",
  "secret_token": "A1b2C3d4_SECRET"
}
```
Токен отправляется в заголовке `X-Telegram-Bot-Api-Secret-Token`

### Правила Webhook
✅ Использовать HTTPS обязательно (TLS 1.3)
✅ Установить secret_token для верификации
✅ Валидировать заголовок на сервере
✅ Использовать константное по времени сравнение токена

❌ Не использовать HTTP без TLS
❌ Не хардкодить secret_token в коде
❌ Не обрабатывать запросы без валидации токена

---

## Mini Apps (Web Apps)

### Инициализация
```html
<script src="https://telegram.org/js/telegram-web-app.js?59"></script>
```
```javascript
const tg = window.Telegram.WebApp;
tg.ready();    // Уведомление о готовности
tg.expand();   // Развернуть на полную высоту
```

### Данные пользователя
```javascript
// НЕБЕЗОПАСНО (только для UI)
const user = tg.initDataUnsafe.user; // id, first_name, username

// БЕЗОПАСНО - отправлять на сервер для валидации
const initData = tg.initData; // строка подписанных данных
```

⚠️ **ВАЖНО:** Никогда не доверять `initDataUnsafe` для авторизации! Проверять подпись `initData` и `auth_date` на бэкенде.

### MainButton и BackButton
```javascript
// MainButton (нижняя кнопка)
tg.MainButton.setText('Send').show();
tg.MainButton.onClick(() => { ... });
tg.MainButton.showProgress();
tg.MainButton.hideProgress();

// BackButton (кнопка в шапке)
tg.BackButton.show();
tg.BackButton.onClick(() => { tg.close(); });
```

### События
```javascript
tg.onEvent('activated', callback);
tg.onEvent('deactivated', callback);
tg.onEvent('mainButtonClicked', callback);
tg.onEvent('backButtonClicked', callback);
tg.onEvent('themeChanged', callback);
```

### Интеграция темы
```javascript
const colorScheme = tg.colorScheme; // "light" или "dark"
const themeParams = tg.themeParams; // объект с цветами

tg.onEvent('themeChanged', () => {
  // Обновить CSS-стили
});
```

### Хранение данных
- `tg.CloudStorage` - асинхронное хранилище для настроек (setItem/getItem)
- `SecureStorage` - для секретов и токенов

### Тактильная обратная связь
```javascript
tg.HapticFeedback.impactOccurred('light');
tg.HapticFeedback.notificationOccurred('success');
tg.HapticFeedback.selectionChanged();
```

### Правила Mini Apps
✅ Только HTTPS для всех запросов
✅ Валидировать initData на сервере
✅ Проверять auth_date на актуальность
✅ Использовать тактильную обратную связь
✅ Адаптировать под тему Telegram

❌ Не доверять initDataUnsafe для авторизации
❌ Не хранить секреты на клиенте
❌ Не использовать HTTP

---

## Payments API

### Типы сообщений
- `invoice` - счёт на оплату
- `successful_payment` - успешная оплата
- `refunded_payment` - возврат

### Обновления
- `shipping_query` - запрос вариантов доставки
- `pre_checkout_query` - финальная проверка перед оплатой

### Платежи в Telegram
- Оплата звездами (Stars) для цифровых товаров
- Платные посты в каналах
- Поддержка провайдеров платежей

---

## Безопасность

### 1. Webhook Security
**Secret Token:**
- Генерировать случайную строку (32–256 символов)
- Передавать в `setWebhook`
- Валидировать заголовок `X-Telegram-Bot-Api-Secret-Token`
- При несовпадении возвращать `HTTP 401`
- Использовать константное по времени сравнение (защита от side-channel атак)

**IP-фильтрация:**
- НЕ РЕКОМЕНДУЕТСЯ - IP-адреса Telegram динамически меняются
- `secret_token` - достаточный механизм аутентификации

**HTTPS:**
- Обязательно TLS 1.3
- Включить HSTS
- Валидный SSL-сертификат (Let's Encrypt)
- Настроить автообновление сертификатов

### 2. Токен бота
✅ Хранить в environment variables
✅ Использовать .env файл (не коммитить в git)
✅ Регулярно ротировать токен через BotFather
✅ Минимальные права доступа

❌ НЕ хардкодить в коде
❌ НЕ коммитить в репозиторий
❌ НЕ логировать

### 3. Валидация ввода
✅ Валидировать все пользовательские данные
✅ Санитизировать текст перед обработкой
✅ Ограничивать длину ввода
✅ Проверять типы данных

### 4. Rate Limiting
✅ Ограничивать частоту запросов от пользователя
✅ Использовать middleware для rate limiting
✅ Игнорировать сообщения во время обработки предыдущего

### 5. Данные Mini Apps
✅ Валидировать initData на сервере
✅ Проверять auth_date (не старше 1 часа)
✅ Использовать HMAC-SHA256 для проверки подписи
✅ Только HTTPS

---

## Тестирование

### Стратегия тестирования

**E2E тесты (Рекомендуется):**
- Использовать РЕАЛЬНЫЙ Telegram API, не моки
- Имитировать действия реального пользователя
- Отдельный тестовый бот и аккаунт

**Unit тесты:**
- Тестирование бизнес-логики
- Тестирование валидации
- Тестирование FSM переходов

### Настройка E2E тестов

**Зависимости:**
```
pytest, pytest-asyncio, telethon, python-dotenv
```

**Credentials:**
1. Токен бота через BotFather
2. `api_id` и `api_hash` из Telegram Developer Portal
3. Сгенерировать `StringSession` через telethon

### Ключевые фикстуры (conftest.py)
```python
@pytest.fixture(scope="session")
def bot():
    """Запускает бот в отдельном потоке"""
    stop_event = threading.Event()
    # Запуск бота
    yield bot
    stop_event.set()  # Graceful shutdown
    thread.join()

@pytest.fixture
def conv():
    """Открывает Conversation с ботом"""
    # Отправка /start
    # Потребление приветственных сообщений
    yield conversation
```

### Примеры тестов
```python
@pytest.mark.asyncio
async def test_command_my_lists(conv: Conversation):
    """Проверка базовой команды и inline-кнопок"""
    await conv.send_message("/my_lists")
    response = await conv.get_response()
    
    assert "Choose list" in response.text
    assert get_button_with_text(response, "Create new") is not None

@pytest.mark.asyncio
async def test_create_list_item(conv: Conversation):
    """Сценарий: создание → добавление → проверка"""
    list_name = await create_list(conv)
    await open_list(conv, list_name)
    
    item_name = random_string()
    await conv.send_message(item_name)
    
    await conv.get_response()
    list_contents = await conv.get_response()
    
    assert get_button_with_text(list_contents, item_name) is not None
```

### Лучшие практики тестирования
✅ Реальный API > моки для E2E
✅ Graceful shutdown через threading.Event
✅ Уникальные данные для избежания коллизий
✅ Добавлять wait() 0.3-0.5 сек между отправкой/ожиданием
✅ Хранить credentials в .env или CI секретах
✅ Генерировать уникальные имена (random_string)
✅ Выносить хелперы в отдельный модуль

❌ Не использовать моки для E2E тестов
❌ Не коммитить credentials в репозиторий
❌ Не очищать БД между тестами (лучше уникальные имена)
❌ Не тестировать каждую ветку через E2E (только критические сценарии)

### Хелперы для тестов
```python
def get_button_with_text(message, text):
    """Поиск кнопки с текстом в сообщении"""
    for row in message.reply_markup.inline_keyboard:
        for button in row:
            if button.text == text:
                return button
    return None

def random_string(length=8):
    """Генерация уникальной строки"""
    return ''.join(random.choices(string.ascii_lowercase, k=length))

def wait(seconds=0.5):
    """Фиксированная пауза для стабильности"""
    time.sleep(seconds)
```

---

## Обработка ошибок

### Рекомендуемый подход (aiogram 3)

**Локальная обработка:**
- Использовать `try-except` внутри хендлеров для точечного контроля

**Глобальная обработка:**
- `@router.error(...)` - перехват ошибок в роутере
- `@dp.error(...)` - перехват ошибок во всех роутерах (диспетчер)

### Примеры кода
```python
import logging
from aiogram import Router, F
from aiogram.types import Message, ErrorEvent
from aiogram.filters import ExceptionTypeFilter

router = Router()
logger = logging.getLogger(__name__)

# Обработка конкретной ошибки
@router.error(ExceptionTypeFilter(MyCustomException), F.update.message.as_("message"))
async def handle_custom_error(event: ErrorEvent, message: Message):
    await message.answer("⚠️ Произошла ошибка. Попробуйте позже.")

# Глобальный перехват всех ошибок
@router.error()
async def global_error_handler(event: ErrorEvent):
    logger.critical("Критическая ошибка: %s", event.exception, exc_info=True)
    # Очистка FSM-состояния
    # Уведомление админа
```

### Типы исключений (aiogram.exceptions)
**Базовые:** AiogramError, DetailedAiogramError
**FSM:** CallbackAnswerException, SceneException
**API & Сеть:** TelegramAPIError, TelegramNetworkError, TelegramBadRequest, TelegramNotFound, TelegramUnauthorizedError
**Контроль частоты:** TelegramRetryAfter, TelegramMigrateToChat

### Правила обработки ошибок
✅ Всегда информировать пользователя о ошибке
✅ Логировать с exc_info=True для полного стектрейса
✅ Очищать FSM-состояние при критических ошибках
✅ Уведомлять админа о критических сбоях
✅ Предоставлять пользователю способ повторить действие

❌ Не оставлять пользователя без ответа
❌ Не показывать технические детали пользователю
❌ Не игнорировать исключения
❌ Не логировать токены и чувствительные данные

---

## Логирование

### Настройка
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
```

### Уровни логирования
- **DEBUG** - детальная информация для отладки
- **INFO** - стандартные события (запуск бота, команды пользователей)
- **WARNING** - предупреждения (rate limit, недопустимый ввод)
- **ERROR** - ошибки обработки (с exc_info=True)
- **CRITICAL** - фатальные сбои (с exc_info=True)

### Примеры
```python
logger.info("Бот запущен")
logger.info("Пользователь %s отправил /start", user_id)
logger.warning("Rate limit для пользователя %s", user_id)
logger.error("Ошибка в хендлере: %s", event.exception, exc_info=True)
logger.critical("Сбой диспетчера: %s", event.exception, exc_info=True)
```

---

## Масштабирование

### Паттерны масштабирования

**1. Redis для FSM**
- Хранить состояния в Redis вместо in-memory
- Позволяет горизонтальное масштабирование
- Поддержка сессий между перезапусками

**2. Очереди задач (Celery, RQ)**
- Для долгих операций (отправка файлов, внешние API)
- Асинхронная обработка без блокировки

**3. Балансировка нагрузки**
- Несколько инстансов бота с общим Redis
- Webhook для мгновенной доставки обновлений

**4. Кеширование**
- Кешировать ответы внешних API
- Использовать `cache_time` для inline queries

### Архитектура для продакшена
```
Telegram API → Reverse Proxy (Nginx/Caddy) → Webhook Handler → Bot Application
                                                                    ↓
                                                              Redis (FSM)
                                                                    ↓
                                                              Database (PostgreSQL/SQLite)
                                                                    ↓
                                                              Task Queue (Celery)
```

---

## Ресурсы для решения проблем

### Официальная документация
- **Telegram Bot API:** https://core.telegram.org/bots/api
- **Telegram Mini Apps:** https://core.telegram.org/bots/webapps
- **BotFather команды:** https://core.telegram.org/bots#6-botfather

### Фреймворки и библиотеки
- **aiogram 3.x (Python):** https://docs.aiogram.dev
- **python-telegram-bot:** https://docs.python-telegram-bot.org
- **node-telegram-bot-api (Node.js):** https://github.com/yagop/node-telegram-bot-api
- **grammY (TypeScript/JavaScript):** https://grammy.dev
- **Telegraf (Node.js):** https://telegraf.js.org

### Сообщества и форумы
- **Stack Overflow:** https://stackoverflow.com/questions/tagged/telegram-bot
- **Telegram Bot SDK Community:** https://telegram-bot-sdk.com/community/support/
- **GitHub Issues aiogram:** https://github.com/aiogram/aiogram/issues
- **GitHub Issues python-telegram-bot:** https://github.com/python-telegram-bot/python-telegram-bot/issues
- **Reddit r/Telegram:** https://www.reddit.com/r/Telegram/
- **DEV Community:** https://dev.to/t/telegram

### YouTube каналы
- Aiogram 3 tutorials (поиск "aiogram 3 tutorial")
- Python Telegram Bot official tutorials

### Инструменты
- **ngrok** - локальный тест webhook
- **Postman** - тестирование API методов
- **Telethon** - E2E тестирование ботов
- **Mockoon** - мок Telegram Bot API

---

## Хорошие и плохие примеры

### ✅ ХОРОШО: Правильная архитектура
```python
# Изолированные обработчики с FSM
from aiogram.fsm.state import StatesGroup, State
from aiogram import Router, F

class OrderStates(StatesGroup):
    waiting_name = State()
    waiting_phone = State()
    confirmation = State()

router = Router()

@router.message(Command("order"))
async def start_order(message: Message, state: FSMContext):
    await message.answer("Введите ваше имя:")
    await state.set_state(OrderStates.waiting_name)

@router.message(OrderStates.waiting_name)
async def process_name(message: Message, state: FSMContext):
    if len(message.text) < 2:
        await message.answer("Имя слишком короткое. Попробуйте снова:")
        return
    await state.update_data(name=message.text)
    await message.answer("Введите телефон:")
    await state.set_state(OrderStates.waiting_phone)
```

### ❌ ПЛОХО: Спагетти-код
```python
# ПЛОХО: Всё в одном хендлере, без FSM, без валидации
@router.message()
async def handle_everything(message: Message):
    if message.text == "/start":
        await message.answer("Привет!")
    elif message.text == "купить":
        # Вся бизнес-логика здесь
        data = message.text  # без валидации
        process(data)  # без обработки ошибок
        await message.answer("Готово!")  # без проверки результата
```

### ✅ ХОРОШО: Обработка ошибок
```python
@router.message(Command("api_call"))
async def make_api_call(message: Message):
    try:
        result = await external_api.get_data()
        await message.answer(f"Данные: {result}")
    except ExternalAPIError as e:
        logger.error("Ошибка внешнего API: %s", e, exc_info=True)
        await message.answer("Сервис временно недоступен. Попробуйте позже.")
    except Exception as e:
        logger.critical("Неожиданная ошибка: %s", e, exc_info=True)
        await message.answer("Произошла ошибка. Мы уже работаем над ней.")
```

### ❌ ПЛОХО: Без обработки ошибок
```python
@router.message(Command("api_call"))
async def make_api_call(message: Message):
    result = await external_api.get_data()  # может упасть
    await message.answer(f"Данные: {result}")  # бот крашнется
```

### ✅ ХОРОШО: Безопасность
```python
# Токен из environment
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен!")

# Валидация webhook
@app.post("/webhook")
async def webhook(request: Request):
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if not hmac.compare_digest(secret, EXPECTED_SECRET):
        raise HTTPException(status_code=401)
    return await process_update(await request.json())
```

### ❌ ПЛОХО: Небезопасно
```python
# Хардкод токена
BOT_TOKEN = "123456:ABC-DEF..."

# Без валидации webhook
@app.post("/webhook")
async def webhook(request: Request):
    return await process_update(await request.json())
```

### ✅ ХОРОШО: Валидация ввода
```python
@router.message(OrderStates.waiting_email)
async def process_email(message: Message, state: FSMContext):
    email = message.text.strip()
    if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
        await message.answer("❌ Неверный формат email. Попробуйте снова:")
        return
    await state.update_data(email=email)
    await message.answer("✅ Email принят!")
```

---

## Чеклист перед деплоем

### Безопасность
- [ ] Токен бота в environment variable (не в коде)
- [ ] Webhook использует HTTPS с валидным сертификатом
- [ ] Установлен и валидируется secret_token
- [ ] Валидация пользовательского ввода
- [ ] Rate limiting настроен
- [ ] Логи не содержат токенов и чувствительных данных

### Архитектура
- [ ] FSM используется для диалогов
- [ ] Глобальный error handler настроен
- [ ] Логирование настроено (INFO + ERROR)
- [ ] Код разделён на модули/роутеры
- [ ] Нет спагетти-кода

### Тестирование
- [ ] E2E тесты для критических сценариев
- [ ] Unit тесты для бизнес-логики
- [ ] Проверка всех FSM переходов
- [ ] Тесты на обработку ошибок

### Функциональность
- [ ] Все команды работают корректно
- [ ] Клавиатуры отображаются правильно
- [ ] Inline режим работает (если используется)
- [ ] Payments работают (если используется)
- [ ] Mini App открывается и работает (если используется)

### Мониторинг
- [ ] Логирование ошибок
- [ ] Уведомления админа о критических ошибках
- [ ] Health check endpoint
- [ ] Мониторинг uptime

### Документация
- [ ] README с инструкцией по запуску
- [ ] .env.example с переменными
- [ ] Документация команд бота
- [ ] Список зависимостей

### Деплой
- [ ] Dockerfile (если используется)
- [ ] docker-compose.yml (если используется)
- [ ] CI/CD pipeline (опционально)
- [ ] Backup базы данных настроен

---

## 🎯 Золотые правила разработки Telegram-приложений

1. **Состояние на сервере** - никогда не хранить в клиенте
2. **Валидация всего** - пользовательский ввод, webhook, данные Mini App
3. **Graceful degradation** - бот должен работать даже при сбоях
4. **Понятные сообщения об ошибках** - пользователь не должен видеть технические детали
5. **Тестирование критических сценариев** - команды, платежи, FSM переходы
6. **Безопасность прежде всего** - токены, HTTPS, secret_token
7. **Модульная архитектура** - роутеры, мидлвари, хелперы
8. **Документирование** - код, команды, API endpoints
9. **Логирование** - достаточно для отладки, но без чувствительных данных
10. **Пользовательский опыт** - клавиатуры, подсказки, возможность отмены

---

*Документ создан: 2025-04-06*
*Версия: 1.0.0*
