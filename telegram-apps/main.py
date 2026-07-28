from fastapi import FastAPI, HTTPException, UploadFile, File, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import requests
import httpx
import docx
import shutil
import json
import re
import hashlib
import asyncio
import base64
import logging
import gzip
import subprocess
import tempfile
import socket
import telegram_polling
import invest_logic
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from urllib.parse import parse_qs, quote, urlparse
from telegram_webapp_auth import TelegramInitDataError, verify_telegram_init_data
from ocr_review import compare_ocr_texts

app = FastAPI(title="bigalexn8n Apps Hub")
logger = logging.getLogger("apps_hub")
# telegram_polling.start_bot()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

OWNER_CHAT_ID = int(os.getenv("OWNER_CHAT_ID", "923741104"))

N8N_WEBHOOK_URL = "https://bigalexn8n.ru/webhook/trigger-translation"
OCR_BATCH_WEBHOOK_URL = os.getenv(
    "OCR_BATCH_WEBHOOK_URL",
    "http://127.0.0.1:5678/webhook/ocr-yandex-korean-batch",
)
OCR_DELETE_TXT_WEBHOOK_URL = os.getenv(
    "OCR_DELETE_TXT_WEBHOOK_URL",
    "http://127.0.0.1:5678/webhook/ocr-yandex-delete-txt",
)
OCR_REVIEW_PUBLISH_WEBHOOK_URL = os.getenv(
    "OCR_REVIEW_PUBLISH_WEBHOOK_URL",
    "http://127.0.0.1:5678/webhook/ocr-yandex-review-publish",
)
OCR_MERGED_OUTPUT_NAME = os.getenv("OCR_MERGED_OUTPUT_NAME", "ocr_merged.txt")
OCR_SERVICE_HEALTH_URL = os.getenv(
    "OCR_SERVICE_HEALTH_URL", "http://127.0.0.1:8765/health"
)
AI_OCR_SERVICE_HEALTH_URL = os.getenv(
    "AI_OCR_SERVICE_HEALTH_URL", "http://127.0.0.1:8766/health"
)
YANDEX_PUBLIC_RESOURCE_URL = "https://cloud-api.yandex.net/v1/disk/public/resources"
YANDEX_DISK_API_URL = "https://cloud-api.yandex.net/v1/disk"
TGS_FOLDER_PATH = os.getenv("TGS_FOLDER_PATH", "/Yulia/+ Test/tgs")
TGS_CONVERTER_BIN = os.getenv("TGS_CONVERTER_BIN", "lottie_convert.py")
AI_OCR_MODELS = {
    "gpt-5.6-luna": "Luna — быстрое массовое распознавание",
    "gpt-5.6-terra": "Terra — баланс скорости и качества",
    "gpt-5.6-sol": "Sol — максимальное качество",
}
AI_OCR_DEFAULT_MODEL = "gpt-5.6-luna"
AI_OCR_DEFAULT_PROMPT = """Ты — точный OCR-движок. Распознай весь видимый текст на изображении, преимущественно на корейском языке.

Верни только распознанный текст в UTF-8, без пояснений, Markdown и служебных фраз.
Сохраняй порядок чтения, исходные переносы строк, пустые строки, абзацы и границы реплик настолько точно, насколько позволяет изображение.
Точно сохраняй кавычки, скобки, дефисы, тире, многоточия и остальные знаки пунктуации в их визуальной позиции. Не переноси многоточие за закрывающую кавычку и не превращай кавычки или точки в случайные латинские символы вроде f1, I или l.
Сохраняй корейские слоги, латиницу, цифры и специальные символы как в источнике.
Не переводи, не пересказывай, не исправляй стиль или грамматику, не дополняй обрезанный или неразборчивый текст догадками.
Если фрагмент нельзя уверенно прочитать, передай только различимую часть; не выдумывай отсутствующие символы."""
TELEGRAM_INIT_DATA_MAX_AGE = int(
    os.getenv("TELEGRAM_INIT_DATA_MAX_AGE", str(24 * 60 * 60))
)
DB_CONFIG_POSTGRES = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "database": os.getenv("DB_NAME", "postgres"),
    "user": os.getenv("DB_USER", "n8n_user"),
    "password": os.getenv("DB_PASSWORD", ""),
    "port": int(os.getenv("DB_PORT", 5432))
}

def get_conn_pg(): return psycopg2.connect(**DB_CONFIG_POSTGRES)


def telegram_proxy_url() -> Optional[str]:
    configured = os.getenv("TELEGRAM_PROXY_URL") or os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
    if configured:
        return configured
    try:
        with socket.create_connection(("127.0.0.1", 10809), timeout=0.2):
            return "http://127.0.0.1:10809/"
    except OSError:
        return None

DB_CONFIG_RESEARCH = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "database": "market_research",
    "user": os.getenv("DB_USER", "n8n_user"),
    "password": os.getenv("DB_PASSWORD", ""),
    "port": int(os.getenv("DB_PORT", 5432))
}

def get_conn_research(): return psycopg2.connect(**DB_CONFIG_RESEARCH)

@app.middleware("http")
async def no_cache_ui(request: Request, call_next):
    response = await call_next(request)
    content_type = response.headers.get("content-type", "")
    if content_type.startswith("text/html"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

class StartTranslationRequest(BaseModel):
    file_id: Optional[str] = ""; file_name: Optional[str] = ""; chat_id: Optional[int] = None
    bp_file_id: Optional[str] = None; bp_file_name: Optional[str] = None
    pp_file_id: Optional[str] = None; pp_file_name: Optional[str] = None
    glossary_id: Optional[str] = None; glossary_file_name: Optional[str] = None
    create_glossary: bool = False

class TelegramCallbackRequest(BaseModel):
    callback_query: dict


class OcrStartRequest(BaseModel):
    force_files: List[str] = Field(default_factory=list)
    engine: str = Field(default="paddle", max_length=16)
    model: Optional[str] = Field(default=None, max_length=64)
    prompt: Optional[str] = Field(default=None, max_length=12000)


class OcrDeleteTxtRequest(BaseModel):
    confirmation: str = Field(default="", max_length=64)


class OcrClearAllRequest(BaseModel):
    confirmation: str = Field(default="", max_length=64)


class OcrMergeTxtRequest(BaseModel):
    confirmation: str = Field(default="", max_length=64)


class OcrReviewCandidateRequest(BaseModel):
    source_name: str = Field(min_length=1, max_length=512)
    model: str = Field(default="gpt-5.6-terra", max_length=64)
    prompt: Optional[str] = Field(default=None, max_length=12000)


class OcrReviewCandidatesRequest(BaseModel):
    source_names: List[str] = Field(default_factory=list)
    model: str = Field(default="gpt-5.6-terra", max_length=64)
    prompt: Optional[str] = Field(default=None, max_length=12000)


class OcrReviewActionRequest(BaseModel):
    action: str = Field(min_length=1, max_length=32)
    edited_text: Optional[str] = Field(default=None, max_length=2_000_000)
    edited_candidate_text: Optional[str] = Field(default=None, max_length=2_000_000)


class TgsDeleteRequest(BaseModel):
    scope: str = Field(min_length=1, max_length=16)
    confirmation: str = Field(default="", max_length=64)


def verified_telegram_user(request: Request) -> dict:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        raise HTTPException(status_code=503, detail="Telegram authentication is unavailable")
    try:
        return verify_telegram_init_data(
            request.headers.get("X-Telegram-Init-Data", ""),
            bot_token,
            max_age_seconds=TELEGRAM_INIT_DATA_MAX_AGE,
        )
    except TelegramInitDataError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def is_ocr_owner(user: dict) -> bool:
    expected_id = int(os.getenv("OCR_OWNER_ID", "923741104"))
    expected_username = os.getenv("OCR_OWNER_USERNAME", "bigalex_an").strip().lstrip("@").casefold()
    actual_username = str(user.get("username") or "").strip().lstrip("@").casefold()
    return int(user.get("id", 0)) == expected_id or bool(
        expected_username and actual_username == expected_username
    )


def is_ocr_operator(user: dict) -> bool:
    if is_ocr_owner(user):
        return True
    operator_ids = {
        value.strip()
        for value in os.getenv("OCR_OPERATOR_IDS", "").split(",")
        if value.strip()
    }
    return str(int(user.get("id", 0))) in operator_ids


def latest_ocr_batch() -> Optional[dict]:
    conn = get_conn_pg()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute(
                """
                WITH latest AS (
                    SELECT *
                    FROM ocr_batch_runs
                    ORDER BY started_at DESC
                    LIMIT 1
                ), live AS (
                    SELECT
                        count(j.id)::int AS total_discovered,
                        count(j.id) FILTER (
                            WHERE j.last_batch_process_requested IS TRUE
                              AND j.status = 'done'
                        )::int AS processed_count,
                        count(j.id) FILTER (
                            WHERE j.last_batch_process_requested IS NOT TRUE
                              AND j.status = 'done'
                        )::int AS skipped_count,
                        count(j.id) FILTER (
                            WHERE j.last_batch_process_requested IS TRUE
                              AND j.status IN ('retry', 'failed')
                        )::int AS failed_count,
                        count(j.id) FILTER (
                            WHERE j.last_batch_process_requested IS TRUE
                        )::int AS progress_total,
                        count(j.id) FILTER (
                            WHERE j.last_batch_process_requested IS TRUE
                              AND j.status = 'done'
                        )::int AS progress_completed,
                        count(j.id) FILTER (
                            WHERE j.last_batch_process_requested IS TRUE
                              AND j.status IN ('retry', 'failed')
                        )::int AS progress_failed,
                        max(j.source_name) FILTER (
                            WHERE j.status = 'processing'
                        ) AS progress_current_file
                    FROM latest b
                    LEFT JOIN ocr_jobs j ON j.last_batch_id = b.id
                )
                SELECT
                    b.id, b.status, b.chat_id, b.requested_by,
                    b.ocr_engine, b.ai_model,
                    b.started_at, b.finished_at,
                    CASE WHEN b.status = 'running' THEN live.total_discovered ELSE b.total_discovered END AS total_discovered,
                    CASE WHEN b.status = 'running' THEN live.processed_count ELSE b.processed_count END AS processed_count,
                    CASE WHEN b.status = 'running' THEN live.skipped_count ELSE b.skipped_count END AS skipped_count,
                    CASE WHEN b.status = 'running' THEN live.failed_count ELSE b.failed_count END AS failed_count,
                    b.failed_files,
                    b.cancel_requested,
                    b.cancel_requested_at,
                    CASE WHEN b.status = 'running' THEN live.progress_total ELSE b.progress_total END AS progress_total,
                    CASE WHEN b.status = 'running' THEN live.progress_completed ELSE b.progress_completed END AS progress_completed,
                    CASE WHEN b.status = 'running' THEN live.progress_failed ELSE b.progress_failed END AS progress_failed,
                    CASE WHEN b.status = 'running' THEN live.progress_current_file ELSE b.progress_current_file END AS progress_current_file,
                    b.updated_at
                FROM latest b CROSS JOIN live
                """
            )
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            cur.close()
    finally:
        conn.close()


def latest_ocr_review_batch() -> Optional[dict]:
    """Return the latest AI-review run in the same shape as an OCR batch."""
    conn = get_conn_pg()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute(
                """
                SELECT id, status, requested_by, ai_model, started_at, finished_at,
                       total_count AS progress_total,
                       completed_count AS progress_completed,
                       failed_count AS progress_failed,
                       skipped_count,
                       current_file AS progress_current_file,
                       total_count AS total_discovered,
                       completed_count AS processed_count,
                       0::integer AS skipped_ocr_count,
                       failed_count,
                       last_error,
                       updated_at,
                       'review'::text AS run_type,
                       'ai'::text AS ocr_engine
                FROM ocr_review_batch_runs
                ORDER BY started_at DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            cur.close()
    finally:
        conn.close()


def create_ocr_review_batch(requested_by: int, total_count: int, model: str) -> dict:
    conn = get_conn_pg()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute(
                """
                INSERT INTO ocr_review_batch_runs (requested_by, total_count, ai_model)
                VALUES (%s, %s, %s)
                RETURNING *
                """,
                (requested_by, total_count, model),
            )
            row = dict(cur.fetchone())
            conn.commit()
            return row
        except psycopg2.IntegrityError as exc:
            conn.rollback()
            raise HTTPException(status_code=409, detail="AI review batch is already running") from exc
        finally:
            cur.close()
    finally:
        conn.close()


def update_ocr_review_batch(run_id: int, *, current_file: Optional[str] = None,
                            completed: bool = False, failed: bool = False,
                            last_error: Optional[str] = None, stop_remaining: bool = False) -> None:
    """Persist every completed file so a restart never turns a batch into silence."""
    conn = get_conn_pg()
    try:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                UPDATE ocr_review_batch_runs
                SET current_file = %s,
                    completed_count = completed_count + %s,
                    failed_count = failed_count + %s,
                    skipped_count = skipped_count + CASE
                        WHEN %s THEN GREATEST(0, total_count - completed_count - failed_count - 1)
                        ELSE 0 END,
                    last_error = COALESCE(%s, last_error),
                    updated_at = now()
                WHERE id = %s AND status = 'running'
                """,
                (current_file, int(completed), int(failed), stop_remaining, last_error, run_id),
            )
            conn.commit()
        finally:
            cur.close()
    finally:
        conn.close()


def finish_ocr_review_batch(run_id: int) -> None:
    conn = get_conn_pg()
    try:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                UPDATE ocr_review_batch_runs
                SET status = CASE
                        WHEN completed_count = total_count THEN 'done'
                        WHEN completed_count = 0 THEN 'failed'
                        ELSE 'partial'
                    END,
                    current_file = NULL, finished_at = now(), updated_at = now()
                WHERE id = %s AND status = 'running'
                """,
                (run_id,),
            )
            conn.commit()
        finally:
            cur.close()
    finally:
        conn.close()


async def ocr_service_health() -> dict:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(OCR_SERVICE_HEALTH_URL)
            response.raise_for_status()
            payload = response.json()
            return {
                "reachable": True,
                "ready": bool(payload.get("ready")),
                "status": payload.get("status", "unknown"),
                "engine": payload.get("engine"),
                "engine_version": payload.get("engine_version"),
                "language": payload.get("language"),
            }
    except (httpx.HTTPError, ValueError):
        return {"reachable": False, "ready": False, "status": "unavailable"}


async def ai_ocr_service_health() -> dict:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(AI_OCR_SERVICE_HEALTH_URL)
            response.raise_for_status()
            payload = response.json()
            result = {
                "reachable": True,
                "ready": bool(payload.get("ready")),
                "status": payload.get("status", "unknown"),
                "engine": payload.get("engine", "Codex CLI"),
                "auth": payload.get("auth", "unknown"),
            }
            if payload.get("error_code"):
                result["error_code"] = payload.get("error_code")
            if payload.get("detail"):
                result["detail"] = payload.get("detail")
            if result.get("error_code") == "codex_oauth_unavailable":
                result["user_message"] = (
                    "Авторизация AI OCR истекла. Требуется повторный вход Codex."
                )
            return result
    except (httpx.HTTPError, ValueError):
        return {"reachable": False, "ready": False, "status": "unavailable"}


def ocr_service_unavailable_detail(engine: str, service: dict) -> str:
    if engine == "ai":
        if service.get("error_code") == "codex_oauth_unavailable" or service.get("auth") == "missing":
            return "Авторизация AI OCR истекла. Требуется повторный вход Codex."
        return service.get("user_message") or "AI OCR сейчас недоступен."
    return "PaddleOCR сейчас недоступен."


def ai_ocr_response_error_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        body = {}
    detail = str(body.get("detail") or "")
    error_code = str(body.get("error_code") or "")
    if (
        response.status_code == 503
        and (
            error_code == "codex_oauth_unavailable"
            or "oauth" in detail.lower()
            or "sign in again" in detail.lower()
        )
    ):
        return "Авторизация AI OCR истекла. Требуется повторный вход Codex."
    return "AI OCR candidate could not be created"


def natural_ocr_name_key(name: str):
    return [
        (0, int(part)) if part.isdigit() else (1, part.casefold())
        for part in re.split(r"(\d+)", name)
    ]


async def current_ocr_source_listing(public_key: str) -> dict:
    image_names = []
    txt_names = []
    files = {}
    offset = 0
    total = None
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            while total is None or offset < total:
                response = await client.get(
                    YANDEX_PUBLIC_RESOURCE_URL,
                    params={
                        "public_key": public_key,
                        "limit": 1000,
                        "offset": offset,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                if payload.get("type") != "dir":
                    raise ValueError("OCR source is not a directory")
                embedded = payload.get("_embedded") or {}
                items = embedded.get("items") or []
                for item in items:
                    if item.get("type") == "file" and item.get("name"):
                        files[item["name"].casefold()] = {
                            "name": item["name"],
                            "file": item.get("file"),
                            "md5": item.get("md5"),
                            "mime_type": item.get("mime_type"),
                            "size": item.get("size"),
                        }
                total = int(embedded.get("total", len(items)))
                image_names.extend(
                    item["name"]
                    for item in items
                    if item.get("type") == "file"
                    and re.fullmatch(
                        r"image/(png|jpeg|webp|tiff)",
                        item.get("mime_type", ""),
                        re.IGNORECASE,
                    )
                )
                txt_names.extend(
                    item["name"]
                    for item in items
                    if item.get("type") == "file"
                    and re.search(r"\.txt$", item.get("name", ""), re.IGNORECASE)
                )
                if not items:
                    break
                offset += len(items)
    except (httpx.HTTPError, TypeError, ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Current OCR source file list is unavailable",
        ) from exc
    return {
        "images": sorted(set(image_names), key=natural_ocr_name_key),
        "txt_names": {name.casefold() for name in txt_names},
        "files": files,
    }


async def current_ocr_image_names(public_key: str) -> List[str]:
    return (await current_ocr_source_listing(public_key))["images"]


def yandex_oauth_token() -> str:
    token = os.getenv("YANDEX_OAUTH_TOKEN", "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="Yandex Disk access is not configured")
    return token


def yandex_auth_headers() -> dict:
    return {"Authorization": f"OAuth {yandex_oauth_token()}"}


def natural_file_name_key(name: str):
    return [
        (0, int(part)) if part.isdigit() else (1, part.casefold())
        for part in re.split(r"(\d+)", name)
    ]


async def current_tgs_folder_listing() -> dict:
    files = []
    offset = 0
    total = None
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            while total is None or offset < total:
                response = await client.get(
                    f"{YANDEX_DISK_API_URL}/resources",
                    headers=yandex_auth_headers(),
                    params={
                        "path": TGS_FOLDER_PATH,
                        "limit": 1000,
                        "offset": offset,
                        "fields": "_embedded.total,_embedded.items.name,_embedded.items.path,_embedded.items.type,_embedded.items.size,_embedded.items.mime_type,name,path,type",
                    },
                )
                response.raise_for_status()
                payload = response.json()
                if payload.get("type") != "dir":
                    raise ValueError("TGS source is not a directory")
                embedded = payload.get("_embedded") or {}
                items = embedded.get("items") or []
                for item in items:
                    if item.get("type") == "file" and item.get("name") and item.get("path"):
                        files.append(
                            {
                                "name": item["name"],
                                "path": item["path"],
                                "size": item.get("size"),
                                "mime_type": item.get("mime_type"),
                            }
                        )
                total = int(embedded.get("total", len(items)))
                if not items:
                    break
                offset += len(items)
    except (httpx.HTTPError, TypeError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=503, detail="TGS folder file list is unavailable") from exc
    files = sorted(files, key=lambda item: natural_file_name_key(item["name"]))
    return {
        "folder_path": TGS_FOLDER_PATH,
        "files": files,
        "svg": [item for item in files if item["name"].lower().endswith(".svg")],
        "tgs": [item for item in files if item["name"].lower().endswith(".tgs")],
    }


async def yandex_download_resource(path: str) -> bytes:
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        response = await client.get(
            f"{YANDEX_DISK_API_URL}/resources/download",
            headers=yandex_auth_headers(),
            params={"path": path},
        )
        response.raise_for_status()
        href = response.json()["href"]
        file_response = await client.get(href)
        file_response.raise_for_status()
        return file_response.content


async def yandex_upload_resource(path: str, content: bytes, content_type: str = "application/gzip") -> None:
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.get(
            f"{YANDEX_DISK_API_URL}/resources/upload",
            headers=yandex_auth_headers(),
            params={"path": path, "overwrite": "true"},
        )
        response.raise_for_status()
        href = response.json()["href"]
        upload_response = await client.put(
            href,
            content=content,
            headers={"Content-Type": content_type},
        )
        upload_response.raise_for_status()


async def yandex_trash_resource(path: str) -> None:
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.delete(
            f"{YANDEX_DISK_API_URL}/resources",
            headers=yandex_auth_headers(),
            params={"path": path, "permanently": "false"},
        )
        response.raise_for_status()


def convert_svg_bytes_to_tgs(svg_content: bytes, source_name: str) -> bytes:
    with tempfile.TemporaryDirectory(prefix="svg2tgs-") as tmp_dir:
        tmp_path = Path(tmp_dir)
        source_path = tmp_path / source_name
        output_path = tmp_path / f"{Path(source_name).stem}.tgs"
        source_path.write_bytes(svg_content)
        proc = subprocess.run(
            [TGS_CONVERTER_BIN, str(source_path), str(output_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
            check=False,
        )
        if proc.returncode != 0 or not output_path.exists():
            detail = (proc.stderr or proc.stdout or "TGS conversion failed").strip()[:500]
            raise HTTPException(status_code=502, detail=detail)
        tgs_content = output_path.read_bytes()
    validate_tgs_content(tgs_content, source_name)
    return tgs_content


def validate_tgs_content(content: bytes, source_name: str) -> None:
    if len(content) > 64 * 1024:
        raise HTTPException(status_code=422, detail=f"{source_name}: TGS is larger than 64 KB")
    try:
        payload = json.loads(gzip.decompress(content).decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=f"{source_name}: invalid TGS gzip/json") from exc
    if payload.get("tgs") != 1:
        raise HTTPException(status_code=422, detail=f"{source_name}: missing tgs=1")
    if int(payload.get("w") or 0) != 512 or int(payload.get("h") or 0) != 512:
        raise HTTPException(status_code=422, detail=f"{source_name}: TGS canvas must be 512x512")
    if int(payload.get("fr") or 0) != 60:
        raise HTTPException(status_code=422, detail=f"{source_name}: TGS fps must be 60")


def tgs_remote_path_for_svg(svg_item: dict) -> str:
    path = str(svg_item["path"])
    folder, _, name = path.rpartition("/")
    return f"{folder}/{Path(name).stem}.tgs"


def latest_ocr_job(source_name: str) -> dict:
    conn = get_conn_pg()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute(
                """
                SELECT * FROM ocr_jobs
                WHERE lower(source_name) = lower(%s)
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (source_name,),
            )
            row = cur.fetchone()
        finally:
            cur.close()
    finally:
        conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="OCR file is unknown")
    return dict(row)


def latest_ocr_public_key() -> str:
    conn = get_conn_pg()
    try:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT source_public_key
                FROM ocr_jobs
                WHERE source_public_key IS NOT NULL
                  AND source_public_key <> ''
                ORDER BY updated_at DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()
        finally:
            cur.close()
    finally:
        conn.close()
    if not row or not row[0]:
        raise HTTPException(status_code=503, detail="OCR source is not configured")
    return str(row[0])


def latest_reviews_by_source() -> dict:
    conn = get_conn_pg()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute(
                """
                SELECT DISTINCT ON (lower(source_name))
                       id, source_name, source_md5, status, updated_at
                FROM ocr_postprocess_reviews
                ORDER BY lower(source_name), updated_at DESC, id DESC
                """
            )
            rows = [dict(row) for row in cur.fetchall()]
        finally:
            cur.close()
    finally:
        conn.close()
    return {str(row["source_name"]).casefold(): row for row in rows}


def existing_ocr_review(job: dict) -> Optional[dict]:
    conn = get_conn_pg()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute(
                """
                SELECT * FROM ocr_postprocess_reviews
                WHERE ocr_job_id = %s AND source_md5 = %s
                LIMIT 1
                """,
                (job["id"], job["source_md5"]),
            )
            row = cur.fetchone()
        finally:
            cur.close()
    finally:
        conn.close()
    return dict(row) if row else None


async def download_public_bytes(url: str, max_bytes: int = 20_000_000) -> bytes:
    if not url:
        raise HTTPException(status_code=409, detail="TXT download link is unavailable")
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            if len(response.content) > max_bytes:
                raise HTTPException(status_code=413, detail="TXT is too large")
            return response.content
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="TXT could not be downloaded") from exc


async def download_public_text(url: str) -> str:
    try:
        return (await download_public_bytes(url, max_bytes=2_000_000)).decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="TXT is not valid UTF-8") from exc


async def build_merged_ocr_text(listing: dict) -> dict:
    sources = []
    for image_name in sorted(listing.get("images") or [], key=natural_ocr_name_key):
        txt_name = re.sub(r"\.[^.]+$", ".txt", image_name)
        item = (listing.get("files") or {}).get(txt_name.casefold())
        if item and item.get("file"):
            sources.append((txt_name, item["file"]))
    if not sources:
        raise HTTPException(status_code=409, detail="No current recognized TXT files to merge")

    downloaded = []
    for index in range(0, len(sources), 8):
        chunk = sources[index:index + 8]
        downloaded.extend(await asyncio.gather(*(download_public_text(url) for _, url in chunk)))

    parts = []
    total_bytes = 0
    for text in downloaded:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = text.rstrip("\n")
        total_bytes += len(text.encode("utf-8"))
        if total_bytes > 20_000_000:
            raise HTTPException(status_code=413, detail="Merged TXT is too large")
        parts.append(text)
    merged_text = "\n\n".join(parts)
    if not merged_text.strip():
        raise HTTPException(status_code=422, detail="Current TXT files are empty")
    merged_bytes = merged_text.encode("utf-8")
    return {
        "text": merged_text,
        "source_names": [name for name, _ in sources],
        "size": len(merged_bytes),
        "sha256": hashlib.sha256(merged_bytes).hexdigest(),
    }


def serialize_review(row: dict) -> dict:
    result = dict(row)
    for key in ("created_at", "updated_at", "accepted_at"):
        if result.get(key) is not None:
            result[key] = result[key].isoformat()
    return result


def write_review_state(
    job: dict,
    baseline: str,
    model: str,
    prompt: str,
    *,
    status: str,
    candidate: Optional[str] = None,
    analysis: Optional[dict] = None,
    error: Optional[str] = None,
) -> dict:
    baseline_hash = hashlib.sha256(baseline.encode("utf-8")).hexdigest()
    candidate_hash = (
        hashlib.sha256(candidate.encode("utf-8")).hexdigest() if candidate is not None else None
    )
    conn = get_conn_pg()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute(
                """
                INSERT INTO ocr_postprocess_reviews (
                    ocr_job_id, source_name, source_md5, baseline_text,
                    baseline_sha256, candidate_text, candidate_sha256,
                    model, prompt, status, decision_reason, diff_json, error_message
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                ON CONFLICT (ocr_job_id, source_md5) DO UPDATE SET
                    baseline_text = EXCLUDED.baseline_text,
                    baseline_sha256 = EXCLUDED.baseline_sha256,
                    candidate_text = EXCLUDED.candidate_text,
                    candidate_sha256 = EXCLUDED.candidate_sha256,
                    model = EXCLUDED.model,
                    prompt = EXCLUDED.prompt,
                    status = EXCLUDED.status,
                    decision_reason = EXCLUDED.decision_reason,
                    diff_json = EXCLUDED.diff_json,
                    error_message = EXCLUDED.error_message,
                    updated_at = now()
                RETURNING *
                """,
                (
                    job["id"], job["source_name"], job["source_md5"], baseline,
                    baseline_hash, candidate, candidate_hash, model, prompt, status,
                    (analysis or {}).get("reason"),
                    json.dumps(analysis, ensure_ascii=False) if analysis is not None else None,
                    error,
                ),
            )
            row = dict(cur.fetchone())
            conn.commit()
        finally:
            cur.close()
    finally:
        conn.close()
    return row


async def publish_text_file(output_name: str, text: str) -> dict:
    trigger_token = os.getenv("OCR_BATCH_TRIGGER_TOKEN", "")
    if not trigger_token:
        raise HTTPException(status_code=503, detail="OCR review publishing is not configured")
    encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    last_error: Optional[Exception] = None
    for attempt, delay in enumerate((0, 3, 8)):
        if delay:
            await asyncio.sleep(delay)
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    OCR_REVIEW_PUBLISH_WEBHOOK_URL,
                    headers={"X-OCR-Token": trigger_token},
                    json={"output_name": output_name, "content_base64": encoded, "sha256": digest},
                )
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
            if attempt == 2:
                break
    raise HTTPException(
        status_code=502,
        detail="Yandex Disk временно не принял TXT. Нажмите «Принять» ещё раз через несколько секунд.",
    ) from last_error


async def publish_review_text(source_name: str, text: str) -> dict:
    output_name = re.sub(r"\.[^.]+$", ".txt", source_name)
    return await publish_text_file(output_name, text)


async def send_telegram_text_document(
    chat_id: int,
    output_name: str,
    text: str,
    caption: str,
) -> dict:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        raise HTTPException(status_code=503, detail="Telegram delivery is not configured")
    content = text.encode("utf-8")
    proxy_url = telegram_proxy_url()
    last_error: Optional[Exception] = None
    for attempt, delay in enumerate((0, 3, 8)):
        if delay:
            await asyncio.sleep(delay)
        try:
            async with httpx.AsyncClient(timeout=120.0, proxy=proxy_url) as client:
                response = await client.post(
                    f"https://api.telegram.org/bot{bot_token}/sendDocument",
                    data={"chat_id": str(chat_id), "caption": caption},
                    files={"document": (output_name, content, "text/plain; charset=utf-8")},
                )
                response.raise_for_status()
                payload = response.json()
                break
        except httpx.HTTPStatusError as exc:
            detail = "Merged TXT could not be sent to Telegram"
            try:
                error_payload = exc.response.json()
                detail = error_payload.get("description") or detail
            except ValueError:
                pass
            raise HTTPException(status_code=502, detail=detail) from exc
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
            if attempt == 2:
                raise HTTPException(
                    status_code=502,
                    detail="Merged TXT could not be sent to Telegram",
                ) from last_error
    if not payload.get("ok"):
        raise HTTPException(
            status_code=502,
            detail=payload.get("description") or "Telegram rejected the merged TXT",
        )
    message = payload.get("result") or {}
    document = message.get("document") or {}
    if document.get("file_size") is not None and int(document["file_size"]) != len(content):
        raise HTTPException(status_code=502, detail="Telegram TXT size verification failed")
    return {
        "message_id": message.get("message_id"),
        "file_id": document.get("file_id"),
        "file_size": int(document.get("file_size") or len(content)),
    }


@app.get("/api/ocr/status")
async def get_ocr_status(request: Request):
    verified_telegram_user(request)
    batch = latest_ocr_batch()
    review_batch = latest_ocr_review_batch()
    service = await ocr_service_health()
    ai_service = await ai_ocr_service_health()
    is_running = bool(batch and batch.get("status") == "running")
    review_running = bool(review_batch and review_batch.get("status") == "running")
    return {
        "source_folder": "протокол",
        "service": service,
        "services": {"paddle": service, "ai": ai_service},
        "batch": batch,
        "review_batch": review_batch,
        "can_start": bool(service.get("ready") or ai_service.get("ready")) and not is_running and not review_running,
        "can_stop": is_running and not bool(batch.get("cancel_requested")),
    }


@app.get("/api/ocr/config")
async def get_ocr_config(request: Request):
    verified_telegram_user(request)
    return {
        "engines": [
            {"id": "paddle", "label": "PaddleOCR — локально"},
            {"id": "ai", "label": "ИИ через Codex CLI"},
        ],
        "ai_models": [
            {"id": model_id, "label": label}
            for model_id, label in AI_OCR_MODELS.items()
        ],
        "default_ai_model": AI_OCR_DEFAULT_MODEL,
        "default_ai_prompt": AI_OCR_DEFAULT_PROMPT,
    }


@app.post("/api/ocr/start", status_code=202)
async def start_ocr(request: Request, payload: Optional[OcrStartRequest] = None):
    user = verified_telegram_user(request)
    trigger_token = os.getenv("OCR_BATCH_TRIGGER_TOKEN", "")
    if not trigger_token:
        raise HTTPException(status_code=503, detail="OCR launch is unavailable")

    payload = payload or OcrStartRequest()
    engine = payload.engine.strip().lower()
    if engine not in {"paddle", "ai"}:
        raise HTTPException(status_code=400, detail="Unsupported OCR engine")
    model = payload.model or AI_OCR_DEFAULT_MODEL
    prompt = (payload.prompt or AI_OCR_DEFAULT_PROMPT).strip()
    if engine == "ai" and model not in AI_OCR_MODELS:
        raise HTTPException(status_code=400, detail="Unsupported AI OCR model")
    if engine == "ai" and len(prompt) < 20:
        raise HTTPException(status_code=400, detail="AI OCR prompt is too short")

    service = await (ai_ocr_service_health() if engine == "ai" else ocr_service_health())
    if not service.get("ready"):
        raise HTTPException(status_code=503, detail=ocr_service_unavailable_detail(engine, service))
    review_batch = latest_ocr_review_batch()
    if review_batch and review_batch.get("status") == "running":
        raise HTTPException(status_code=409, detail="AI review batch is already running")

    force_files = list(dict.fromkeys(payload.force_files))
    if len(force_files) > 1000:
        raise HTTPException(status_code=400, detail="Select no more than 1000 images")
    if any(not name or "/" in name or "\\" in name for name in force_files):
        raise HTTPException(status_code=400, detail="Invalid OCR image name")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                OCR_BATCH_WEBHOOK_URL,
                headers={"X-OCR-Token": trigger_token},
                json={
                    "chat_id": user["id"],
                    "requested_by": user["id"],
                    "force_files": force_files,
                    "engine": engine,
                    "model": model if engine == "ai" else None,
                    "prompt": prompt if engine == "ai" else None,
                },
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="n8n did not accept OCR launch") from exc

    return {
        "accepted": True,
        "message": "OCR batch accepted",
        "force_files": force_files,
        "engine": engine,
        "model": model if engine == "ai" else None,
    }


@app.get("/api/ocr/files")
async def get_ocr_files(request: Request):
    verified_telegram_user(request)
    conn = get_conn_pg()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute(
                """
                SELECT source_public_key, source_name, status, attempts, completed_at,
                       confidence, min_confidence, ocr_engine, error_message
                FROM ocr_jobs
                ORDER BY NULLIF(regexp_replace(source_name, '\\D', '', 'g'), '')::bigint NULLS LAST,
                         source_name
                """
            )
            rows = [dict(row) for row in cur.fetchall()]
        finally:
            cur.close()
    finally:
        conn.close()
    if not rows:
        return {"files": []}
    public_key = next(
        (row["source_public_key"] for row in reversed(rows) if row.get("source_public_key")),
        None,
    )
    if not public_key:
        raise HTTPException(status_code=503, detail="OCR source is not configured")
    source_listing = await current_ocr_source_listing(public_key)
    current_names = source_listing["images"]
    txt_names = source_listing["txt_names"]
    jobs = {row["source_name"].casefold(): row for row in rows}
    reviews = latest_reviews_by_source()
    files = []
    for name in current_names:
        job = jobs.get(name.casefold())
        expected_txt = re.sub(r"\.[^.]+$", ".txt", name).casefold()
        output_exists = expected_txt in txt_names
        status = job["status"] if job else "new"
        if status == "done" and not output_exists:
            status = "new"
        quality = "unrecognized"
        quality_label = "не распознан"
        if status == "done":
            confidence = float(job["confidence"]) if job.get("confidence") is not None else None
            min_confidence = float(job["min_confidence"]) if job.get("min_confidence") is not None else None
            is_scored_ocr = (job.get("ocr_engine") or "").casefold() == "paddleocr"
            has_quality_warning = is_scored_ocr and (
                confidence is None
                or min_confidence is None
                or confidence < 0.95
                or min_confidence < 0.60
            )
            quality = "warning" if has_quality_warning else "ok"
            quality_label = "нужна проверка" if has_quality_warning else "без автопредупреждений"
        elif status in {"retry", "failed"}:
            quality = "error"
            quality_label = "ошибка OCR"
        elif status in {"pending", "processing"}:
            quality = "processing"
            quality_label = "обрабатывается"
        review = reviews.get(name.casefold())
        review_status = None
        if review and output_exists:
            listing_item = (source_listing.get("files") or {}).get(name.casefold()) or {}
            current_md5 = listing_item.get("md5")
            if not current_md5 or review.get("source_md5") == current_md5:
                review_status = review["status"]
                if review_status == "processing":
                    quality, quality_label = "ai", "обрабатывается ИИ"
                elif review_status in {"candidate_ready", "needs_review", "deferred"}:
                    quality, quality_label = "ai", "обработано ИИ — ждёт проверки"
                elif review_status == "accepted":
                    quality, quality_label = "ok", "принят вариант ИИ"
                elif review_status == "rejected":
                    quality, quality_label = "ok", "оставлен исходный"
                elif review_status == "failed":
                    quality, quality_label = "error", "ошибка ИИ"
        files.append(
            {
                "source_name": name,
                "status": status,
                "quality": quality,
                "quality_label": quality_label,
                "attempts": job["attempts"] if job else 0,
                "completed_at": job["completed_at"] if job else None,
                "output_exists": output_exists,
                "review_status": review_status,
            }
        )
    return {"files": files}


def validated_ocr_source_name(source_name: str) -> str:
    name = source_name.strip()
    if not name or len(name) > 512 or "/" in name or "\\" in name or name.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid OCR file name")
    return name


@app.get("/api/ocr/image/{source_name}")
async def get_ocr_image(source_name: str, request: Request):
    verified_telegram_user(request)
    name = validated_ocr_source_name(source_name)
    listing = await current_ocr_source_listing(latest_ocr_public_key())
    item = (listing.get("files") or {}).get(name.casefold())
    if not item or not item.get("file"):
        raise HTTPException(status_code=404, detail="Current image was not found")
    if not re.fullmatch(r"image/\w+", item.get("mime_type") or "", re.IGNORECASE):
        raise HTTPException(status_code=415, detail="Requested file is not an image")
    content = await download_public_bytes(item["file"])
    return Response(
        content=content,
        media_type=item.get("mime_type") or "application/octet-stream",
        headers={"Cache-Control": "private, max-age=600"},
    )


@app.get("/api/ocr/text/{source_name}")
async def get_ocr_text(source_name: str, request: Request):
    verified_telegram_user(request)
    name = validated_ocr_source_name(source_name)
    listing = await current_ocr_source_listing(latest_ocr_public_key())
    txt_name = re.sub(r"\.[^.]+$", ".txt", name)
    item = (listing.get("files") or {}).get(txt_name.casefold())
    if not item or not item.get("file"):
        return {"exists": False, "txt_name": txt_name, "text": ""}
    text = await download_public_text(item["file"])
    return {"exists": True, "txt_name": item["name"], "text": text}


@app.post("/api/ocr/delete-txt", status_code=200)
async def delete_ocr_txt(request: Request, payload: OcrDeleteTxtRequest):
    user = verified_telegram_user(request)
    if not is_ocr_operator(user):
        raise HTTPException(status_code=403, detail="Only an OCR operator can delete TXT files")
    if payload.confirmation != "DELETE_ALL_OCR_TXT":
        raise HTTPException(status_code=400, detail="TXT deletion was not confirmed")
    batch = latest_ocr_batch()
    if batch and batch.get("status") == "running":
        raise HTTPException(status_code=409, detail="Stop the active OCR batch before deleting TXT files")
    trigger_token = os.getenv("OCR_BATCH_TRIGGER_TOKEN", "")
    if not trigger_token:
        raise HTTPException(status_code=503, detail="OCR deletion is not configured")
    public_key = latest_ocr_public_key()
    before_listing = await current_ocr_source_listing(public_key)
    before_count = len(before_listing["txt_names"])
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                OCR_DELETE_TXT_WEBHOOK_URL,
                headers={"X-OCR-Token": trigger_token},
                json={"confirmation": payload.confirmation, "dry_run": False},
            )
            response.raise_for_status()
            result = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="TXT files could not be deleted") from exc
    remaining_count = before_count
    for attempt in range(6):
        listing = await current_ocr_source_listing(public_key)
        remaining_count = len(listing["txt_names"])
        if remaining_count == 0:
            break
        if attempt < 5:
            await asyncio.sleep(1)
    if remaining_count:
        raise HTTPException(
            status_code=502,
            detail=f"Yandex Disk still contains {remaining_count} TXT files after deletion",
        )
    return {
        "deleted_count": int(result.get("deleted_count", 0)),
        "moved_to_trash": True,
        "verified_absent": True,
        "previous_count": before_count,
    }


@app.post("/api/ocr/clear-all", status_code=200)
async def clear_ocr_folder(request: Request, payload: OcrClearAllRequest):
    user = verified_telegram_user(request)
    if not is_ocr_operator(user):
        raise HTTPException(status_code=403, detail="Only an OCR operator can clear the folder")
    if payload.confirmation != "DELETE_ALL_OCR_FILES":
        raise HTTPException(status_code=400, detail="Full clear was not confirmed")
    batch = latest_ocr_batch()
    if batch and batch.get("status") == "running":
        raise HTTPException(status_code=409, detail="Stop the active OCR batch before clearing the folder")
    trigger_token = os.getenv("OCR_BATCH_TRIGGER_TOKEN", "")
    if not trigger_token:
        raise HTTPException(status_code=503, detail="OCR deletion is not configured")
    public_key = latest_ocr_public_key()
    before = await current_ocr_source_listing(public_key)
    before_images = len(before["images"])
    before_txt = len(before["txt_names"])
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                OCR_DELETE_TXT_WEBHOOK_URL,
                headers={"X-OCR-Token": trigger_token},
                json={"confirmation": payload.confirmation, "scope": "all", "dry_run": False},
            )
            response.raise_for_status()
            result = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Folder could not be cleared") from exc
    remaining = before_images + before_txt
    for attempt in range(6):
        listing = await current_ocr_source_listing(public_key)
        remaining = len(listing["images"]) + len(listing["txt_names"])
        if remaining == 0:
            break
        if attempt < 5:
            await asyncio.sleep(1)
    if remaining:
        raise HTTPException(
            status_code=502,
            detail=f"Yandex Disk still contains {remaining} files after full clear",
        )
    return {
        "deleted_count": int(result.get("deleted_count", 0)),
        "moved_to_trash": True,
        "verified_absent": True,
        "previous_images": before_images,
        "previous_txt": before_txt,
    }


@app.post("/api/ocr/merge-txt", status_code=200)
async def merge_ocr_txt(request: Request, payload: OcrMergeTxtRequest):
    user = verified_telegram_user(request)
    if not is_ocr_operator(user):
        raise HTTPException(status_code=403, detail="Only an OCR operator can merge TXT files")
    if payload.confirmation != "MERGE_CURRENT_OCR_TXT":
        raise HTTPException(status_code=400, detail="TXT merge was not confirmed")
    batch = latest_ocr_batch()
    if batch and batch.get("status") == "running":
        raise HTTPException(status_code=409, detail="Stop the active OCR batch before merging TXT files")

    public_key = latest_ocr_public_key()
    merged = await build_merged_ocr_text(await current_ocr_source_listing(public_key))
    content = merged["text"].encode("utf-8")
    if len(content) != merged["size"] or hashlib.sha256(content).hexdigest() != merged["sha256"]:
        raise HTTPException(status_code=500, detail="Merged TXT integrity verification failed")
    delivery = await send_telegram_text_document(
        int(user["id"]),
        OCR_MERGED_OUTPUT_NAME,
        merged["text"],
        f"Объединённый OCR: {len(merged['source_names'])} TXT",
    )

    return {
        "merged": True,
        "delivered_to_telegram": True,
        "output_name": OCR_MERGED_OUTPUT_NAME,
        "source_count": len(merged["source_names"]),
        "first_source": merged["source_names"][0],
        "last_source": merged["source_names"][-1],
        "size": merged["size"],
        "sha256": merged["sha256"],
        "telegram_message_id": delivery.get("message_id"),
        "verified": True,
    }


@app.get("/api/ocr/reviews")
async def get_ocr_reviews(request: Request):
    user = verified_telegram_user(request)
    if not is_ocr_operator(user):
        raise HTTPException(status_code=403, detail="Only an OCR operator can review TXT files")
    conn = get_conn_pg()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute(
                """
                SELECT * FROM ocr_postprocess_reviews
                ORDER BY updated_at DESC, id DESC
                LIMIT 200
                """
            )
            rows = [serialize_review(dict(row)) for row in cur.fetchall()]
        finally:
            cur.close()
    finally:
        conn.close()
    if rows:
        listing = await current_ocr_source_listing(latest_ocr_public_key())
        for row in rows:
            source = listing["files"].get(str(row["source_name"]).casefold())
            row["source_url"] = source.get("file") if source else None
    return {"reviews": rows}


@app.post("/api/ocr/reviews/candidate")
async def create_ocr_review_candidate(request: Request, payload: OcrReviewCandidateRequest):
    user = verified_telegram_user(request)
    if not is_ocr_operator(user):
        raise HTTPException(status_code=403, detail="Only an OCR operator can run review OCR")
    review_batch = latest_ocr_review_batch()
    if review_batch and review_batch.get("status") == "running":
        raise HTTPException(status_code=409, detail="AI review batch is already running")
    return await create_single_ocr_review_candidate(payload)


async def create_single_ocr_review_candidate(payload: OcrReviewCandidateRequest):
    if payload.model not in AI_OCR_MODELS:
        raise HTTPException(status_code=400, detail="Unsupported AI OCR model")
    prompt = (payload.prompt or AI_OCR_DEFAULT_PROMPT).strip()
    if len(prompt) < 20:
        raise HTTPException(status_code=400, detail="AI OCR prompt is too short")
    batch = latest_ocr_batch()
    if batch and batch.get("status") == "running":
        raise HTTPException(status_code=409, detail="Stop the active OCR batch before review")
    job = latest_ocr_job(payload.source_name)
    public_key = job.get("source_public_key")
    listing = await current_ocr_source_listing(public_key)
    image = listing["files"].get(payload.source_name.casefold())
    txt_name = re.sub(r"\.[^.]+$", ".txt", payload.source_name)
    txt = listing["files"].get(txt_name.casefold())
    if not image or not image.get("file"):
        raise HTTPException(status_code=404, detail="Current image is no longer present")
    if not txt or not txt.get("file"):
        raise HTTPException(status_code=409, detail="Baseline TXT is missing")
    if image.get("md5") and job.get("source_md5") != image.get("md5"):
        raise HTTPException(status_code=409, detail="Image changed after OCR; run baseline OCR first")

    existing = existing_ocr_review(job)
    if existing and existing.get("status") not in {"queued", "processing", "failed"}:
        return {"review": serialize_review(existing), "resumed": True}

    service = await ai_ocr_service_health()
    if not service.get("ready"):
        raise HTTPException(status_code=503, detail=ocr_service_unavailable_detail("ai", service))

    baseline = await download_public_text(txt["file"])
    write_review_state(job, baseline, payload.model, prompt, status="processing")
    try:
        async with httpx.AsyncClient(timeout=360.0) as client:
            response = await client.post(
                AI_OCR_SERVICE_HEALTH_URL.replace("/health", "/ocr-url"),
                json={
                    "url": image["file"],
                    "source_name": payload.source_name,
                    "model": payload.model,
                    "prompt": prompt,
                },
            )
            response.raise_for_status()
            candidate = str(response.json().get("text") or "").strip()
        if not candidate:
            raise ValueError("AI OCR returned empty text")
        analysis = compare_ocr_texts(baseline, candidate)
        row = write_review_state(
            job,
            baseline,
            payload.model,
            prompt,
            status=analysis["verdict"],
            candidate=candidate,
            analysis=analysis,
        )
        return {"review": serialize_review(row)}
    except httpx.HTTPStatusError as exc:
        detail = ai_ocr_response_error_detail(exc.response)
        write_review_state(
            job,
            baseline,
            payload.model,
            prompt,
            status="failed",
            error=detail,
        )
        status_code = 503 if "Авторизация AI OCR" in detail else 502
        raise HTTPException(status_code=status_code, detail=detail) from exc
    except (httpx.HTTPError, ValueError) as exc:
        detail = "AI OCR candidate could not be created"
        write_review_state(
            job,
            baseline,
            payload.model,
            prompt,
            status="failed",
            error=detail,
        )
        raise HTTPException(status_code=502, detail=detail) from exc


async def process_ocr_review_candidate_batch(run_id: int, source_names: List[str], model: str, prompt: Optional[str]):
    for source_name in source_names:
        try:
            update_ocr_review_batch(run_id, current_file=source_name)
            await create_single_ocr_review_candidate(
                OcrReviewCandidateRequest(
                    source_name=source_name,
                    model=model,
                    prompt=prompt,
                )
            )
            update_ocr_review_batch(run_id, completed=True)
        except HTTPException as exc:
            auth_failed = exc.status_code == 503 and "Авторизация AI OCR" in str(exc.detail)
            update_ocr_review_batch(
                run_id,
                failed=True,
                last_error=str(exc.detail),
                stop_remaining=auth_failed,
            )
            logger.warning(
                "OCR review candidate failed for %s: %s",
                source_name,
                exc.detail,
            )
            if auth_failed:
                break
        except Exception:
            update_ocr_review_batch(run_id, failed=True, last_error="Неожиданная ошибка AI OCR")
            logger.exception("OCR review candidate crashed for %s", source_name)
    finish_ocr_review_batch(run_id)


@app.post("/api/ocr/reviews/candidates")
async def create_ocr_review_candidates(
    request: Request,
    payload: OcrReviewCandidatesRequest,
    background_tasks: BackgroundTasks,
):
    user = verified_telegram_user(request)
    if not is_ocr_operator(user):
        raise HTTPException(status_code=403, detail="Only an OCR operator can run review OCR")
    if payload.model not in AI_OCR_MODELS:
        raise HTTPException(status_code=400, detail="Unsupported AI OCR model")
    prompt = (payload.prompt or AI_OCR_DEFAULT_PROMPT).strip()
    if len(prompt) < 20:
        raise HTTPException(status_code=400, detail="AI OCR prompt is too short")
    ordered_names = []
    seen = set()
    for source_name in payload.source_names:
        clean_name = str(source_name or "").strip()
        key = clean_name.casefold()
        if clean_name and key not in seen:
            ordered_names.append(clean_name)
            seen.add(key)
    if not ordered_names:
        raise HTTPException(status_code=400, detail="No files selected")
    batch = latest_ocr_batch()
    if batch and batch.get("status") == "running":
        raise HTTPException(status_code=409, detail="Stop the active OCR batch before review")
    review_batch = latest_ocr_review_batch()
    if review_batch and review_batch.get("status") == "running":
        raise HTTPException(status_code=409, detail="AI review batch is already running")
    service = await ai_ocr_service_health()
    if not service.get("ready"):
        raise HTTPException(status_code=503, detail=ocr_service_unavailable_detail("ai", service))

    run = create_ocr_review_batch(int(user["id"]), len(ordered_names), payload.model)
    background_tasks.add_task(process_ocr_review_candidate_batch, run["id"], ordered_names, payload.model, prompt)

    return {
        "accepted": True,
        "requested": len(ordered_names),
        "queued": len(ordered_names),
        "completed": 0,
        "failed": 0,
        "reviews": [],
        "errors": [],
        "run_id": run["id"],
    }


@app.post("/api/ocr/reviews/{review_id}/action")
async def act_on_ocr_review(review_id: int, request: Request, payload: OcrReviewActionRequest):
    user = verified_telegram_user(request)
    if not is_ocr_operator(user):
        raise HTTPException(status_code=403, detail="Only an OCR operator can decide reviews")
    action = payload.action.strip().lower()
    if action not in {"accept", "reject", "defer", "rollback"}:
        raise HTTPException(status_code=400, detail="Unsupported review action")
    conn = get_conn_pg()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute("SELECT * FROM ocr_postprocess_reviews WHERE id = %s", (review_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Review was not found")
            row = dict(row)
            job = latest_ocr_job(row["source_name"])
            if job.get("source_md5") != row.get("source_md5"):
                raise HTTPException(status_code=409, detail="Image changed; this review is stale")
            publish_text = None
            new_baseline = None
            new_candidate = None
            next_status = {"reject": "rejected", "defer": "deferred"}.get(action)
            if action == "accept":
                if row.get("status") not in {"candidate_ready", "needs_review", "deferred"}:
                    raise HTTPException(status_code=409, detail="Candidate is not ready")
                edited_candidate = payload.edited_candidate_text
                if (
                    edited_candidate is not None
                    and edited_candidate.strip()
                    and edited_candidate != (row.get("candidate_text") or "")
                ):
                    publish_text = edited_candidate
                    new_candidate = edited_candidate
                else:
                    publish_text = row.get("candidate_text")
                next_status = "accepted"
            elif action == "reject":
                edited = payload.edited_text
                if (
                    edited is not None
                    and edited.strip()
                    and edited != (row.get("baseline_text") or "")
                ):
                    publish_text = edited
                    new_baseline = edited
            elif action == "rollback":
                if row.get("status") != "accepted":
                    raise HTTPException(status_code=409, detail="Only an accepted review can be rolled back")
                publish_text = row.get("baseline_text")
                next_status = "rolled_back"
            if publish_text is not None:
                result = await publish_review_text(row["source_name"], publish_text)
                expected_hash = hashlib.sha256(publish_text.encode("utf-8")).hexdigest()
                if result.get("sha256") != expected_hash:
                    raise HTTPException(status_code=502, detail="Published TXT could not be verified")
            new_baseline_hash = (
                hashlib.sha256(new_baseline.encode("utf-8")).hexdigest()
                if new_baseline is not None
                else None
            )
            new_candidate_hash = (
                hashlib.sha256(new_candidate.encode("utf-8")).hexdigest()
                if new_candidate is not None
                else None
            )
            cur.execute(
                """
                UPDATE ocr_postprocess_reviews
                SET status = %s,
                    baseline_text = COALESCE(%s, baseline_text),
                    baseline_sha256 = COALESCE(%s, baseline_sha256),
                    candidate_text = COALESCE(%s, candidate_text),
                    candidate_sha256 = COALESCE(%s, candidate_sha256),
                    accepted_at = CASE WHEN %s = 'accepted' THEN now() ELSE accepted_at END,
                    updated_at = now()
                WHERE id = %s
                RETURNING *
                """,
                (
                    next_status,
                    new_baseline,
                    new_baseline_hash,
                    new_candidate,
                    new_candidate_hash,
                    next_status,
                    review_id,
                ),
            )
            updated = dict(cur.fetchone())
            conn.commit()
        finally:
            cur.close()
    finally:
        conn.close()
    return {"review": serialize_review(updated)}


@app.post("/api/ocr/stop", status_code=202)
async def stop_ocr(request: Request):
    user = verified_telegram_user(request)
    conn = get_conn_pg()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute(
                """
                UPDATE ocr_batch_runs
                SET cancel_requested = true,
                    cancel_requested_at = coalesce(cancel_requested_at, now()),
                    updated_at = now()
                WHERE status = 'running'
                RETURNING id, cancel_requested, cancel_requested_at
                """
            )
            row = cur.fetchone()
            conn.commit()
        finally:
            cur.close()
    finally:
        conn.close()
    if not row:
        raise HTTPException(status_code=409, detail="OCR batch is not running")
    return {
        "accepted": True,
        "message": "OCR stop requested",
        "batch_id": row["id"],
        "requested_by": user["id"],
    }

# --- INVEST API ---
@app.get("/api/invest/offers")
async def get_invest_offers():
    return invest_logic.get_current_offers()

@app.get("/api/invest/portfolio")
async def get_portfolio(user_id: int):
    return invest_logic.get_user_portfolio(user_id)

@app.post("/api/invest/portfolio")
async def add_to_portfolio(data: dict):
    invest_logic.add_to_portfolio(data['user_id'], data['offer_id'], data['amount'])
    return {"status": "success"}

@app.delete("/api/invest/portfolio/{item_id}")
async def delete_from_portfolio(item_id: int, user_id: int):
    success = invest_logic.remove_from_portfolio(user_id, item_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete")
    return {"status": "success"}

@app.post("/api/invest/update")
async def update_invest_offers():
    success = await invest_logic.update_invest_offers()
    return {"status": "success" if success else "error"}

# --- OTHER API ---
@app.get("/api/get-form-data")
async def get_form_data(chat_id: int):
    if chat_id == 0: chat_id = OWNER_CHAT_ID
    conn = get_conn_pg()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute("""
                SELECT type, lang, name, file_id
                FROM (
                    SELECT DISTINCT ON (message->'document'->>'file_id')
                        type,
                        lang,
                        message->'document'->>'file_name' as name,
                        message->'document'->>'file_id' as file_id,
                        date_time
                    FROM telegram_messages
                    WHERE (message->'chat'->>'id')::bigint = %s
                      AND message->'document' IS NOT NULL
                      AND (is_translate IS NULL OR is_translate = false)
                    ORDER BY message->'document'->>'file_id', date_time DESC
                ) latest_files
                ORDER BY date_time DESC
            """, (chat_id,))
            all_items = cur.fetchall()
        finally:
            cur.close()
    finally:
        conn.close()
    return {"files_ko": [f for f in all_items if f['lang'] == 'ko'], "glossaries": [f for f in all_items if f['type'] == 'xlsx'], "prompts_ru": [f for f in all_items if f['lang'] == 'ru']}

@app.post("/api/files/hide")
async def hide_files(data: dict):
    file_ids = data.get("file_ids", []); chat_id = data.get("chat_id")
    conn = get_conn_pg()
    try:
        cur = conn.cursor()
        try:
            cur.execute("UPDATE telegram_messages SET is_translate = true WHERE message->'document'->>'file_id' = ANY(%s) AND (message->'chat'->>'id')::bigint = %s", (file_ids, chat_id))
            conn.commit()
        finally:
            cur.close()
    finally:
        conn.close()
    return {"status": "success"}

@app.post("/api/telegram-callback")
async def save_telegram_callback(data: TelegramCallbackRequest):
    callback = data.callback_query or {}
    callback_data = (callback.get("data") or "").strip()
    from_user = callback.get("from") or {}
    message = callback.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = from_user.get("id") or chat.get("id")

    if not callback_data:
        raise HTTPException(status_code=400, detail="callback_query.data is empty")
    if not chat_id:
        raise HTTPException(status_code=400, detail="callback chat id is missing")

    conn = get_conn_pg()
    try:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO telegram_messages(chat, message, callback_data, date_time, is_translate)
                VALUES (%s, %s::json, %s, now(), false)
                RETURNING id
                """,
                (str(chat_id), json.dumps(callback, ensure_ascii=False), callback_data),
            )
            row_id = cur.fetchone()[0]
            conn.commit()
        finally:
            cur.close()
    finally:
        conn.close()
    return {"status": "success", "id": row_id}

def chat_id_from_request(data: dict, request: Request):
    chat_id = data.get("chat_id")
    if not chat_id:
        referrer = request.headers.get("referer", "")
        if referrer:
            query = parse_qs(urlparse(referrer).query)
            chat_id = (query.get("chat_id") or [None])[0]
    try:
        chat_id = int(chat_id or 0)
    except (TypeError, ValueError):
        chat_id = 0
    return OWNER_CHAT_ID if chat_id == 0 else chat_id

def resolve_translation_file(
    chat_id: int,
    file_name: Optional[str] = None,
    file_id: Optional[str] = None,
):
    conn = get_conn_pg()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            params = [chat_id]
            file_filters = []
            if file_name:
                file_filters.append("message->'document'->>'file_name' = %s")
                params.append(file_name)
            if file_id:
                file_filters.append("message->'document'->>'file_id' = %s")
                params.append(file_id)
            file_filter = ""
            if file_filters:
                file_filter = "AND (" + " OR ".join(file_filters) + ")"
            cur.execute(f"""
                SELECT
                    message->'document'->>'file_name' AS file_name,
                    message->'document'->>'file_id' AS file_id
                FROM telegram_messages
                WHERE (message->'chat'->>'id')::bigint = %s
                  AND message->'document' IS NOT NULL
                  AND type IN ('docx', 'txt')
                  AND lang = 'ko'
                  AND (is_translate IS NULL OR is_translate = false)
                  {file_filter}
                ORDER BY date_time DESC
                LIMIT 1
            """, params)
            row = cur.fetchone()
        finally:
            cur.close()
    finally:
        conn.close()
    return row

@app.get("/api/prompts")
async def get_prompts_db():
    conn = get_conn_pg()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute("SELECT id, name, prompt FROM translate_prompts ORDER BY name")
            data = cur.fetchall()
        finally:
            cur.close()
    finally:
        conn.close()
    return data

@app.post("/api/prompts")
async def create_prompt(data: dict):
    conn = get_conn_pg()
    try:
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO translate_prompts (name, prompt) VALUES (%s, %s)", (data['name'], data['prompt']))
            conn.commit()
        finally:
            cur.close()
    finally:
        conn.close()
    return {"status": "success"}

@app.put("/api/prompts/{prompt_id}")
async def update_prompt(prompt_id: int, data: dict):
    conn = get_conn_pg()
    try:
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO translate_prompts_history (prompt_id, name, prompt, version_date) SELECT id, name, prompt, CURRENT_TIMESTAMP FROM translate_prompts WHERE id = %s", (prompt_id,))
            cur.execute("UPDATE translate_prompts SET name = %s, prompt = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s", (data['name'], data['prompt'], prompt_id))
            conn.commit()
        finally:
            cur.close()
    finally:
        conn.close()
    return {"status": "success"}

@app.delete("/api/prompts/{prompt_id}")
async def delete_prompt(prompt_id: int):
    conn = get_conn_pg()
    try:
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM translate_prompts WHERE id = %s", (prompt_id,))
            conn.commit()
        finally:
            cur.close()
    finally:
        conn.close()
    return {"status": "success"}

@app.get("/api/prompts/{prompt_id}/history")
async def get_prompt_history(prompt_id: int):
    conn = get_conn_pg()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute("SELECT id, prompt_id, name, prompt, version_date FROM translate_prompts_history WHERE prompt_id = %s ORDER BY version_date DESC", (prompt_id,))
            data = cur.fetchall()
        finally:
            cur.close()
    finally:
        conn.close()
    return data

LIGHTRAG_URL = os.getenv("LIGHTRAG_URL", "http://localhost:9624/query")
LIGHTRAG_USER = os.getenv("LIGHTRAG_USER", "")
LIGHTRAG_PASSWORD = os.getenv("LIGHTRAG_PASSWORD", "")


async def get_global_risk():
    try:
        auth = (LIGHTRAG_USER, LIGHTRAG_PASSWORD) if LIGHTRAG_USER else None
        async with httpx.AsyncClient() as client:
            resp = await client.post(LIGHTRAG_URL, json={"query": "Summary of current global market risk level (GREEN, YELLOW, ORANGE, RED).", "mode": "hybrid"}, 
                                    auth=auth, timeout=5.0)
            if resp.status_code == 200:
                text = resp.json().get("response", "GREEN").upper()
                if "RED" in text: return "RED", True
                if "ORANGE" in text: return "ORANGE", True
                if "YELLOW" in text: return "YELLOW", False
                return "GREEN", False
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        logger.warning("get_global_risk failed: %s", exc)
    return "UNKNOWN", False

@app.get("/api/trade/league")
async def get_trade_league(division: str = "moex"):
    try:
        db_name = "market_research" if division == "moex" else "crypto_research"
        config = DB_CONFIG_RESEARCH.copy()
        config["database"] = db_name
        conn = psycopg2.connect(**config)
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            try:
                cur.execute("SELECT p.trader_name, p.cash_balance, c.learned_traits as memory FROM trading.portfolio p LEFT JOIN trading.trader_config c ON p.trader_name = c.trader_name ORDER BY p.trader_name")
                portfolios = cur.fetchall()
                cur.execute("SELECT trader_name, secid, quantity, avg_entry_price FROM trading.position WHERE quantity != 0")
                positions = cur.fetchall()
            finally:
                cur.close()
        finally:
            conn.close()
        risk_level, storm_active = await get_global_risk()
        return {"division": division, "traders": portfolios, "positions": positions, "risk": risk_level, "storm_mode": storm_active, "server_time": datetime.now().strftime("%H:%M:%S")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/start-translation")
async def start_translation(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}

    chat_id = chat_id_from_request(data, request)
    try:
        req = StartTranslationRequest(**data)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Некорректные данные формы: {exc}")

    req.chat_id = req.chat_id or chat_id
    req.file_id = (req.file_id or "").strip()
    req.file_name = (req.file_name or "").strip()

    if not req.file_id or not req.file_name:
        recovered = resolve_translation_file(
            chat_id,
            req.file_name or None,
            req.file_id or None,
        )
        if recovered:
            req.file_id = req.file_id or recovered["file_id"]
            req.file_name = req.file_name or recovered["file_name"]

    if not req.file_id or not req.file_name:
        raise HTTPException(status_code=400, detail="Не выбран файл для перевода. Закройте окно приложения, откройте его заново из сообщения бота и выберите файл.")

    if not req.glossary_id and not req.create_glossary:
        req.create_glossary = True

    last_status = None
    async with httpx.AsyncClient() as client:
        for _ in range(3):
            try:
                resp = await client.post(N8N_WEBHOOK_URL, json=req.dict(), timeout=10.0)
                last_status = resp.status_code
                if 200 <= resp.status_code < 300:
                    return {"status": "success"}
            except httpx.HTTPError:
                last_status = "network"

    raise HTTPException(status_code=502, detail=f"n8n не принял запуск перевода. Ответ: {last_status}")

@app.post("/api/upload-file")
async def upload_file(file: UploadFile = File(...)):
    try:
        if file.filename.endswith(".docx"):
            with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
                shutil.copyfileobj(file.file, tmp)
                tmp_path = tmp.name
            try:
                doc = docx.Document(tmp_path)
                full_text = "\n".join([para.text for para in doc.paragraphs])
            finally:
                os.remove(tmp_path)
            return {"text": full_text}
        else:
            content = await file.read()
            return {"text": content.decode("utf-8")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """Health check endpoint for monitoring."""
    db_ok = False
    try:
        conn = get_conn_pg()
        try:
            cur = conn.cursor()
            try:
                cur.execute("SELECT 1")
                db_ok = cur.fetchone() is not None
            finally:
                cur.close()
        finally:
            conn.close()
    except Exception:
        pass
    status = "healthy" if db_ok else "degraded"
    code = 200 if db_ok else 503
    if not db_ok:
        raise HTTPException(status_code=code, detail={"status": status, "database": db_ok})
    return {"status": status, "database": db_ok}


@app.get("/api/tgs/status")
async def get_tgs_status(request: Request):
    user = verified_telegram_user(request)
    if not is_ocr_operator(user):
        raise HTTPException(status_code=403, detail="Only an operator can manage TGS files")
    listing = await current_tgs_folder_listing()
    return {
        "folder_path": listing["folder_path"],
        "svg_count": len(listing["svg"]),
        "tgs_count": len(listing["tgs"]),
        "files": [
            {"name": item["name"], "size": item.get("size")}
            for item in listing["files"]
            if item["name"].lower().endswith((".svg", ".tgs"))
        ],
    }


@app.post("/api/tgs/convert")
async def convert_tgs_folder(request: Request):
    user = verified_telegram_user(request)
    if not is_ocr_operator(user):
        raise HTTPException(status_code=403, detail="Only an operator can convert TGS files")
    listing = await current_tgs_folder_listing()
    converted = []
    errors = []
    for item in listing["svg"]:
        try:
            svg_content = await yandex_download_resource(item["path"])
            tgs_content = convert_svg_bytes_to_tgs(svg_content, item["name"])
            output_path = tgs_remote_path_for_svg(item)
            await yandex_upload_resource(output_path, tgs_content)
            converted.append({"source": item["name"], "output": Path(output_path).name})
        except HTTPException as exc:
            errors.append({"source": item["name"], "error": str(exc.detail)})
        except (httpx.HTTPError, OSError, subprocess.SubprocessError, ValueError) as exc:
            errors.append({"source": item["name"], "error": str(exc)[:500]})
    if errors:
        raise HTTPException(
            status_code=502,
            detail={
                "message": f"Converted {len(converted)} SVG, failed {len(errors)}",
                "converted": converted,
                "errors": errors,
            },
        )
    return {
        "converted_count": len(converted),
        "converted": converted,
        "message": f"Все SVG сконвертированы в TGS: {len(converted)}",
    }


@app.post("/api/tgs/delete")
async def delete_tgs_files(request: Request, payload: TgsDeleteRequest):
    user = verified_telegram_user(request)
    if not is_ocr_operator(user):
        raise HTTPException(status_code=403, detail="Only an operator can delete TGS files")
    confirmations = {
        "svg": "DELETE_ALL_SVG",
        "tgs": "DELETE_ALL_TGS",
        "all": "CLEAR_TGS_FOLDER",
    }
    if payload.scope not in confirmations:
        raise HTTPException(status_code=400, detail="Unsupported delete scope")
    if payload.confirmation != confirmations[payload.scope]:
        raise HTTPException(status_code=400, detail="Deletion was not confirmed")
    listing = await current_tgs_folder_listing()
    if payload.scope == "svg":
        targets = listing["svg"]
    elif payload.scope == "tgs":
        targets = listing["tgs"]
    else:
        targets = [
            item
            for item in listing["files"]
            if item["name"].lower().endswith((".svg", ".tgs"))
        ]
    deleted = []
    for item in targets:
        await yandex_trash_resource(item["path"])
        deleted.append(item["name"])
    return {
        "deleted_count": len(deleted),
        "moved_to_trash": True,
        "deleted": deleted,
    }

# --- HTML PAGES ---
@app.get("/", response_class=HTMLResponse)
async def main_hub():
    with open("static/index.html", "r", encoding="utf-8") as f: return f.read()

@app.get("/files", response_class=HTMLResponse)
async def files_page():
    with open("static/files/index.html", "r", encoding="utf-8") as f: return f.read()

@app.get("/manage-menu", response_class=HTMLResponse)
async def manage_menu():
    with open("static/manage-menu.html", "r", encoding="utf-8") as f: return f.read()

@app.get("/manage", response_class=HTMLResponse)
async def manage_page():
    with open("static/manage/index.html", "r", encoding="utf-8") as f: return f.read()

@app.get("/prompts", response_class=HTMLResponse)
async def prompts_page():
    with open("static/prompts/index.html", "r", encoding="utf-8") as f: return f.read()

@app.get("/trade", response_class=HTMLResponse)
async def trade_page():
    with open("static/trade/index.html", "r", encoding="utf-8") as f: return f.read()

@app.get("/invest", response_class=HTMLResponse)
async def invest_page():
    with open("static/invest/index.html", "r", encoding="utf-8") as f: return f.read()

@app.get("/ocr", response_class=HTMLResponse)
async def ocr_page():
    with open("static/ocr/index.html", "r", encoding="utf-8") as f: return f.read()

@app.get("/tgs", response_class=HTMLResponse)
async def tgs_page():
    with open("static/tgs/index.html", "r", encoding="utf-8") as f: return f.read()

app.mount("/static", StaticFiles(directory="static"), name="static")
