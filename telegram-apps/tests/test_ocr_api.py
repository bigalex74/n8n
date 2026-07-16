import os
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from starlette.requests import Request

import main
from tests.test_telegram_webapp_auth import BOT_TOKEN, signed_init_data


def request_with_init_data(value=""):
    headers = []
    if value:
        headers.append((b"x-telegram-init-data", value.encode()))
    return Request({"type": "http", "method": "POST", "path": "/", "headers": headers})


class OcrApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_start_rejects_unsigned_request(self):
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": BOT_TOKEN}, clear=False):
            with self.assertRaises(HTTPException) as caught:
                await main.start_ocr(request_with_init_data())
        self.assertEqual(caught.exception.status_code, 401)

    async def test_start_forwards_verified_telegram_user(self):
        response = MagicMock()
        response.raise_for_status.return_value = None
        client = MagicMock()
        client.post = AsyncMock(return_value=response)
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=client)
        context.__aexit__ = AsyncMock(return_value=False)

        with patch.dict(
            os.environ,
            {
                "TELEGRAM_BOT_TOKEN": BOT_TOKEN,
                "OCR_BATCH_TRIGGER_TOKEN": "ocr-test-secret",
            },
            clear=False,
        ), patch.object(
            main, "ocr_service_health", AsyncMock(return_value={"ready": True})
        ), patch.object(main.httpx, "AsyncClient", return_value=context):
            result = await main.start_ocr(
                request_with_init_data(signed_init_data(auth_date=int(time.time())))
            )

        self.assertTrue(result["accepted"])
        call = client.post.await_args
        self.assertEqual(call.kwargs["json"]["chat_id"], 923741104)
        self.assertEqual(call.kwargs["json"]["requested_by"], 923741104)
        self.assertEqual(call.kwargs["headers"]["X-OCR-Token"], "ocr-test-secret")


if __name__ == "__main__":
    unittest.main()
