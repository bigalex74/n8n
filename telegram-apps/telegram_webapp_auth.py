import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl


class TelegramInitDataError(ValueError):
    pass


def verify_telegram_init_data(
    init_data: str,
    bot_token: str,
    *,
    max_age_seconds: int = 24 * 60 * 60,
    now: int | None = None,
) -> dict:
    if not init_data:
        raise TelegramInitDataError("Telegram init data is missing")
    if not bot_token:
        raise RuntimeError("Telegram bot token is not configured")

    try:
        pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=True)
    except ValueError as exc:
        raise TelegramInitDataError("Telegram init data is malformed") from exc
    values = dict(pairs)
    if len(values) != len(pairs):
        raise TelegramInitDataError("Telegram init data contains duplicate fields")

    received_hash = values.pop("hash", "")
    if not received_hash:
        raise TelegramInitDataError("Telegram init data hash is missing")

    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(values.items())
    )
    secret_key = hmac.new(
        b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256
    ).digest()
    calculated_hash = hmac.new(
        secret_key, data_check_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(calculated_hash, received_hash):
        raise TelegramInitDataError("Telegram init data signature is invalid")

    try:
        auth_date = int(values["auth_date"])
    except (KeyError, TypeError, ValueError) as exc:
        raise TelegramInitDataError("Telegram auth date is invalid") from exc

    current_time = int(time.time()) if now is None else int(now)
    if auth_date > current_time + 30:
        raise TelegramInitDataError("Telegram auth date is in the future")
    if current_time - auth_date > max_age_seconds:
        raise TelegramInitDataError("Telegram init data has expired")

    try:
        user = json.loads(values["user"])
        user_id = int(user["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise TelegramInitDataError("Telegram user is invalid") from exc
    if user_id <= 0:
        raise TelegramInitDataError("Telegram user is invalid")

    user["id"] = user_id
    return user
