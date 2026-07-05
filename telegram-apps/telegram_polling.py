import os
import re
import telebot
import requests
import json
import time
import logging
import threading
from datetime import date
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TMA-Polling-Raw")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
N8N_WEBHOOK = "http://127.0.0.1:5678/webhook/trigger-translation"
APPS_HUB_CALLBACK_URL = "http://127.0.0.1:8000/api/telegram-callback"
PROXY = {"https": "http://127.0.0.1:10808"}
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
MY_CHAT_ID = 923741104

# Shared dir mounted in both tg-polling and apps-hub containers at /app
APPROVALS_DIR = Path('/app/data/task-approvals')
TASKS_DIR = Path('/home/user/.openclaw/workspace/projects/daily-tasks')


def _get_masha_token() -> str:
    """Read Masha bot token from openclaw.json (on host, accessible from host-network container)."""
    try:
        import json as _json
        cfg = _json.loads(Path('/home/user/.openclaw/openclaw.json').read_text())
        return cfg['channels']['telegram']['botToken']
    except Exception:
        return BOT_TOKEN or ''


MASHA_TOKEN = _get_masha_token()


def send_message(chat_id: int, text: str) -> None:
    try:
        requests.post(
            f"https://api.telegram.org/bot{MASHA_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            proxies=PROXY, timeout=10
        )
    except Exception as e:
        logger.error(f"send_message error: {e}")


def answer_callback(callback_id: str, text: str) -> None:
    try:
        requests.post(
            f"{BASE_URL}/answerCallbackQuery",
            json={"callback_query_id": callback_id, "text": text, "show_alert": False},
            proxies=PROXY,
            timeout=10,
        )
    except Exception as e:
        logger.error(f"answer_callback error: {e}")


def handle_callback_query(callback_query: dict) -> None:
    callback_id = callback_query.get("id")
    callback_data = callback_query.get("data", "")
    from_user = callback_query.get("from") or {}
    logger.info(
        "Forwarding callback query: data=%r from=%s",
        callback_data,
        from_user.get("id"),
    )
    try:
        response = requests.post(
            APPS_HUB_CALLBACK_URL,
            json={"callback_query": callback_query},
            timeout=15,
        )
        response.raise_for_status()
        if callback_id:
            answer_callback(callback_id, "Принято")
    except Exception as e:
        logger.error(f"callback_query forwarding error: {e}")
        if callback_id:
            answer_callback(callback_id, "Не удалось обработать кнопку")


def parse_task_numbers(tokens: list) -> set:
    nums = set()
    for token in tokens:
        for part in re.split(r'[,\s]+', token):
            if part.isdigit():
                nums.add(int(part))
    return nums


def handle_tasks_command(text: str, chat_id: int) -> bool:
    """Handle /tasks command. Returns True if handled (don't forward to n8n)."""
    parts = text.strip().split()
    if not parts or parts[0].lower().lstrip('/') != 'tasks':
        return False

    args = parts[1:]
    lower_args = [a.lower() for a in args]
    today = date.today().isoformat()
    task_file = TASKS_DIR / f'{today}.md'
    sentinel = APPROVALS_DIR / f'{today}.approved'

    # /tasks or /tasks status
    if not args or (len(args) == 1 and lower_args[0] == 'status'):
        if not task_file.exists():
            send_message(chat_id, 'Файл задач на сегодня не найден. Планировщик запускается в 09:00 Пн-Пт.')
            return True
        content = task_file.read_text(encoding='utf-8')
        total = len(re.findall(r'## Задача \d+:', content))
        done = len(re.findall(r'\*\*Статус:\*\* done', content))
        pending = len(re.findall(r'\*\*Статус:\*\* pending', content))
        approved = sentinel.exists() or 'Статус: одобрено' in content
        status_str = 'одобрено' if approved else 'ожидает одобрения'
        send_message(chat_id,
            f'Задачи на {today} | {status_str}\n'
            f'Выполнено: {done} | Ожидают: {pending} | Всего: {total}\n\n'
            f'Утвердить все: /tasks ok\n'
            f'Утвердить часть: /tasks 1,2 3 ok'
        )
        return True

    # /tasks [numbers] ok
    if 'ok' in lower_args:
        num_tokens = [a for a in args if a.lower() != 'ok']
        selected = parse_task_numbers(num_tokens)

        if not task_file.exists():
            send_message(chat_id, 'Файл задач на сегодня не найден.')
            return True
        if sentinel.exists():
            send_message(chat_id, 'Задачи уже были утверждены ранее.')
            return True

        APPROVALS_DIR.mkdir(parents=True, exist_ok=True)
        content = task_file.read_text(encoding='utf-8')
        total_nums = set(int(m) for m in re.findall(r'## Задача (\d+):', content))

        if selected:
            skipped = total_nums - selected
            for n in skipped:
                content = re.sub(
                    rf'(## Задача {n}: .+?\n\*\*Статус:\*\* )pending(\n)',
                    rf'\1skipped\2', content
                )
            approved_list = sorted(selected & total_nums)
            skipped_list = sorted(skipped)
            reply = f'Утверждены задачи: {", ".join(str(n) for n in approved_list)}'
            if skipped_list:
                reply += f'\nПропущены: {", ".join(str(n) for n in skipped_list)}'
        else:
            approved_list = sorted(total_nums)
            reply = f'Утверждены все задачи: {", ".join(str(n) for n in approved_list)}'

        content = content.replace('Статус: ожидает одобрения', 'Статус: одобрено')
        task_file.write_text(content, encoding='utf-8')
        sentinel.write_text(','.join(str(n) for n in approved_list))

        send_message(chat_id, reply + '\nИсполнитель возьмёт первую задачу в ближайший час.')
        return True

    return False


def run_polling():
    telebot.apihelper.proxy = {'https': PROXY['https']}
    bot = telebot.TeleBot(BOT_TOKEN)
    logger.info("Raw polling bot started...")

    offset = 0
    while True:
        try:
            url = f"{BASE_URL}/getUpdates?offset={offset}&timeout=60"
            resp = requests.get(url, proxies=PROXY, timeout=70)
            data = resp.json()

            if data.get("ok") and data.get("result"):
                for update in data["result"]:
                    offset = update["update_id"] + 1
                    callback_query = update.get("callback_query")
                    if callback_query:
                        handle_callback_query(callback_query)
                        continue

                    message = update.get("message")
                    if message:
                        text = message.get("text", "")
                        chat_id = message["chat"]["id"]
                        if text.lower().startswith("/tasks"):
                            logger.info(f"Handling /tasks command locally: {text!r}")
                            handle_tasks_command(text, chat_id)
                        else:
                            logger.info(f"Forwarding msg ID: {message.get('message_id')}")
                            requests.post(N8N_WEBHOOK, json={"message": message}, timeout=15)
        except Exception as e:
            # Никогда не логируем токен: вырезаем bot<digits>:<secret> из текста ошибки
            safe_err = re.sub(r'bot\d+:[A-Za-z0-9_-]+', 'bot<redacted>', str(e))
            logger.error(f"Polling error: {safe_err}")
            time.sleep(10)

def start_bot():
    threading.Thread(target=run_polling, daemon=True).start()
