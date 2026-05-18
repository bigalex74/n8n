import psycopg2
from psycopg2.extras import RealDictCursor
import os
import httpx
import json

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "database": os.getenv("DB_NAME", "n8n_database"),
    "user": os.getenv("DB_USER", "n8n_user"),
    "password": os.getenv("DB_PASSWORD", "n8n_db_password"),
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
    except: pass
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
                cur = conn.cursor()
                for item in results:
                    category = await classify_offer(item['title'], item['description'])
                    import re
                    yield_matches = re.findall(r'(\d+[.,]?\d*)\s*%', item['title'] + " " + item['description'])
                    yield_val = max([float(y.replace(',', '.')) for y in yield_matches if float(y.replace(',', '.')) < 35.0]) if yield_matches else 14.0
                    clean_title = item['title'].split('|')[0].strip()
                    cur.execute("INSERT INTO invest_offers (title, category, yield_percent, description, link) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (link) DO UPDATE SET yield_percent = EXCLUDED.yield_percent, updated_at = CURRENT_TIMESTAMP", (clean_title[:100], category, yield_val, item['description'][:200], item['url']))
                conn.commit()
                cur.close(); conn.close()
                return True
    except Exception as e: print(f"Error Scraper: {e}")
    return False

def get_current_offers():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM invest_offers ORDER BY yield_percent DESC")
    offers = cur.fetchall()
    cur.close(); conn.close()
    return offers

def add_to_portfolio(user_id, offer_id, amount):
    print(f"DEBUG: Adding to portfolio - User: {user_id}, Offer: {offer_id}, Amount: {amount}")
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT title, link FROM invest_offers WHERE id = %s", (int(offer_id),))
        offer = cur.fetchone()
        if offer:
            cur.execute("""
                INSERT INTO user_portfolio (user_id, offer_id, title, amount, link)
                VALUES (%s, %s, %s, %s, %s)
            """, (int(user_id), int(offer_id), offer[0], float(amount), offer[1]))
            conn.commit()
            print("DEBUG: Successfully saved to DB")
        else:
            print(f"DEBUG: Offer with ID {offer_id} not found!")
        cur.close(); conn.close()
        return True
    except Exception as e:
        print(f"DEBUG: DB Error in add_to_portfolio: {e}")
        return False

def get_user_portfolio(user_id):
    print(f"DEBUG: Getting portfolio for User: {user_id}")
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM user_portfolio WHERE user_id = %s ORDER BY created_at DESC", (int(user_id),))
    data = cur.fetchall()
    cur.close(); conn.close()
    return data

def remove_from_portfolio(user_id, item_id):
    print(f"DEBUG: Removing item {item_id} for User: {user_id}")
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM user_portfolio WHERE id = %s AND user_id = %s", (int(item_id), int(user_id)))
        conn.commit()
        cur.close(); conn.close()
        return True
    except Exception as e:
        print(f"DEBUG: DB Error in remove_from_portfolio: {e}")
        return False
