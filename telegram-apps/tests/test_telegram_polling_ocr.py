import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import telegram_polling  # noqa: E402


def message(text="/ocr", chat_id=telegram_polling.MY_CHAT_ID, from_id=None):
    return {
        "message_id": 1,
        "text": text,
        "chat": {"id": chat_id, "type": "private"},
        "from": {"id": chat_id if from_id is None else from_id},
    }


class OcrCommandTests(unittest.TestCase):
    def test_accepts_exact_command_and_bot_suffix(self):
        self.assertTrue(telegram_polling.is_ocr_command("/ocr"))
        self.assertTrue(telegram_polling.is_ocr_command("/OCR@Test_bot"))
        self.assertFalse(telegram_polling.is_ocr_command("/ocr now"))
        self.assertFalse(telegram_polling.is_ocr_command("hello"))

    @patch.object(telegram_polling, "send_message")
    @patch.object(telegram_polling.requests, "post")
    def test_forwards_authorized_command(self, post, send):
        post.return_value = Mock(raise_for_status=Mock())

        handled = telegram_polling.handle_ocr_command(message())

        self.assertTrue(handled)
        post.assert_called_once()
        self.assertEqual(post.call_args.kwargs["json"]["message"]["text"], "/ocr")
        send.assert_not_called()

    @patch.object(telegram_polling, "send_message")
    @patch.object(telegram_polling.requests, "post")
    def test_rejects_unauthorized_command(self, post, send):
        handled = telegram_polling.handle_ocr_command(
            message(chat_id=111, from_id=111)
        )

        self.assertTrue(handled)
        post.assert_not_called()
        self.assertIn("только владельцу", send.call_args.args[1])

    @patch.object(telegram_polling, "send_message")
    @patch.object(telegram_polling.requests, "post")
    def test_explains_invalid_syntax_without_forwarding(self, post, send):
        handled = telegram_polling.handle_ocr_command(message(text="/ocr now"))

        self.assertTrue(handled)
        post.assert_not_called()
        self.assertIn("/ocr", send.call_args.args[1])


if __name__ == "__main__":
    unittest.main()
