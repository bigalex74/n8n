import psycopg2
from psycopg2.extras import RealDictCursor
import os
import logging
import re
import httpx

logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "database": os.getenv("DB_NAME", "n8n_database"),
    "user": os.getenv("DB_USER", "n8n_user"),
    "password": os.getenv("DB_PASSWORD", ""),
    "port": int(os.getenv("DB_PORT", 5432))
}

FIRECRAWL_URL = "http://localhost:3002"
OLLAMA_URL = "http://localhost:11434/api/generate"

INVEST_CATEGORIES = [
    "Вклады", "Накопительные счета", "Облигации", "ВДО", "Дивидендные акции", 
    "Акции роста", "Золото", "Недвижимость", "Краудлендинг", "Краудфакторинг",
    "ЦФА", "Валюта", "Драгметаллы", "Налоговые льготы", "Альтернативные инвестиции",
    "Крипто-активы", "Валютные инструменты", "Бриллианты"
]

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

async def classify_offer(title, description):
    prompt = f"Классифицируй инвестиционное предложение по одной из категорий: {', '.join(INVEST_CATEGORIES)}.\nЗаголовок: {title}\nОписание: {description}\nВерни ТОЛЬКО название категории."
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(OLLAMA_URL, json={"model": "llama3.2:latest", "prompt": prompt, "stream": False}, timeout=10.0)
            if resp.status_code == 200:
                cat = resp.json().get("response", "").strip()
                for known_cat in INVEST_CATEGORIES:
                    if known_cat.lower() in cat.lower(): return known_cat
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        logger.warning("classify_offer failed: %s", exc)
    return "Облигации"

async def update_invest_offers():
    query = "актуальные инвестиции РФ 2026 доходность новости"
    url = f"{FIRECRAWL_URL}/v1/search"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json={"query": query, "limit": 10, "lang": "ru"}, timeout=60.0)
            if response.status_code == 200:
                results = response.json().get("data", [])
                conn = get_db_connection()
                try:
                    cur = conn.cursor()
                    try:
                        for item in results:
                            category = await classify_offer(item['title'], item['description'])
                            yield_matches = re.findall(r'(\d+[.,]?\d*)\s*%', item['title'] + " " + item['description'])
                            yield_val = max([float(y.replace(',', '.')) for y in yield_matches if float(y.replace(',', '.')) < 35.0]) if yield_matches else 14.0
                            clean_title = item['title'].split('|')[0].strip()
                            cur.execute("INSERT INTO invest_offers (title, category, yield_percent, description, link) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (link) DO UPDATE SET yield_percent = EXCLUDED.yield_percent, updated_at = CURRENT_TIMESTAMP", (clean_title[:100], category, yield_val, item['description'][:200], item['url']))
                        conn.commit()
                    finally:
                        cur.close()
                finally:
                    conn.close()
                return True
    except Exception as exc:
        logger.error("update_invest_offers failed: %s", exc)
    return False

def get_current_offers():
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute("SELECT * FROM invest_offers ORDER BY yield_percent DESC")
            return cur.fetchall()
        finally:
            cur.close()
    finally:
        conn.close()

def add_to_portfolio(user_id, offer_id, amount):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        try:
            cur.execute("SELECT title, link FROM invest_offers WHERE id = %s", (int(offer_id),))
            offer = cur.fetchone()
            if offer:
                cur.execute("""
                    INSERT INTO user_portfolio (user_id, offer_id, title, amount, link)
                    VALUES (%s, %s, %s, %s, %s)
                """, (int(user_id), int(offer_id), offer[0], float(amount), offer[1]))
                conn.commit()
                logger.debug("add_to_portfolio: saved user=%s offer=%s", user_id, offer_id)
            else:
                logger.warning("add_to_portfolio: offer %s not found", offer_id)
            return True
        finally:
            cur.close()
    except Exception as exc:
        logger.error("add_to_portfolio failed: %s", exc)
        return False
    finally:
        conn.close()

def get_user_portfolio(user_id):
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute("SELECT * FROM user_portfolio WHERE user_id = %s ORDER BY created_at DESC", (int(user_id),))
            return cur.fetchall()
        finally:
            cur.close()
    finally:
        conn.close()

def remove_from_portfolio(user_id, item_id):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM user_portfolio WHERE id = %s AND user_id = %s", (int(item_id), int(user_id)))
            conn.commit()
            return True
        finally:
            cur.close()
    except Exception as exc:
        logger.error("remove_from_portfolio failed: %s", exc)
        return False
    finally:
        conn.close()
