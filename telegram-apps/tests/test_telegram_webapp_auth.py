import hashlib
import hmac
import json
import unittest
from urllib.parse import urlencode

from telegram_webapp_auth import TelegramInitDataError, verify_telegram_init_data


BOT_TOKEN = "123456:test-token"
NOW = 1_800_000_000


def signed_init_data(*, user_id=923741104, auth_date=NOW, username=None):
    user = {"id": user_id, "first_name": "Test"}
    if username:
        user["username"] = username
    values = {
        "auth_date": str(auth_date),
        "query_id": "AAExample",
        "user": json.dumps(user, separators=(",", ":")),
    }
    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(values.items())
    )
    secret_key = hmac.new(
        b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256
    ).digest()
    values["hash"] = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()
    return urlencode(values)


class TelegramWebAppAuthTests(unittest.TestCase):
    def test_accepts_valid_signed_user(self):
        user = verify_telegram_init_data(
            signed_init_data(), BOT_TOKEN, max_age_seconds=3600, now=NOW
        )
        self.assertEqual(user["id"], 923741104)

    def test_rejects_tampered_user(self):
        payload = signed_init_data().replace("923741104", "111")
        with self.assertRaises(TelegramInitDataError):
            verify_telegram_init_data(payload, BOT_TOKEN, now=NOW)

    def test_rejects_expired_data(self):
        with self.assertRaisesRegex(TelegramInitDataError, "expired"):
            verify_telegram_init_data(
                signed_init_data(auth_date=NOW - 3601),
                BOT_TOKEN,
                max_age_seconds=3600,
                now=NOW,
            )

    def test_rejects_missing_signature(self):
        with self.assertRaises(TelegramInitDataError):
            verify_telegram_init_data("auth_date=1&user=%7B%7D", BOT_TOKEN, now=NOW)

    def test_rejects_malformed_data(self):
        with self.assertRaisesRegex(TelegramInitDataError, "malformed"):
            verify_telegram_init_data("not-a-query-field", BOT_TOKEN, now=NOW)


if __name__ == "__main__":
    unittest.main()
