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
    def test_owner_matches_stable_id_or_configured_username(self):
        with patch.dict(
            os.environ,
            {"OCR_OWNER_ID": "923741104", "OCR_OWNER_USERNAME": "bigalex_an"},
            clear=False,
        ):
            self.assertTrue(main.is_ocr_owner({"id": 923741104}))
            self.assertTrue(main.is_ocr_owner({"id": 7, "username": "BigAlex_An"}))
            self.assertFalse(main.is_ocr_owner({"id": 7, "username": "someone_else"}))

    def test_operator_allows_owner_and_explicit_id_but_rejects_stranger(self):
        with patch.dict(
            os.environ,
            {
                "OCR_OWNER_ID": "923741104",
                "OCR_OWNER_USERNAME": "bigalex_an",
                "OCR_OPERATOR_IDS": "1011396552, 77",
            },
            clear=False,
        ):
            self.assertTrue(main.is_ocr_operator({"id": 923741104}))
            self.assertTrue(main.is_ocr_operator({"id": 1011396552}))
            self.assertTrue(main.is_ocr_operator({"id": 77}))
            self.assertFalse(main.is_ocr_operator({"id": 8, "username": "someone_else"}))

    async def test_delete_allows_explicit_operator_id(self):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"deleted_count": 2}
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
                "OCR_OPERATOR_IDS": "1011396552",
            },
            clear=False,
        ), patch.object(main, "latest_ocr_batch", return_value=None), patch.object(
            main.httpx, "AsyncClient", return_value=context
        ), patch.object(main, "latest_ocr_public_key", return_value="public-key"), patch.object(
            main,
            "current_ocr_source_listing",
            AsyncMock(side_effect=[{"txt_names": {"1.txt", "2.txt"}}, {"txt_names": set()}]),
        ):
            result = await main.delete_ocr_txt(
                request_with_init_data(
                    signed_init_data(user_id=1011396552, auth_date=int(time.time()))
                ),
                main.OcrDeleteTxtRequest(confirmation="DELETE_ALL_OCR_TXT"),
            )

        self.assertEqual(result["deleted_count"], 2)
        self.assertTrue(result["verified_absent"])

    async def test_delete_allows_configured_owner_username_when_id_drifted(self):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"deleted_count": 3}
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
                "OCR_OWNER_ID": "923741104",
                "OCR_OWNER_USERNAME": "bigalex_an",
            },
            clear=False,
        ), patch.object(main, "latest_ocr_batch", return_value=None), patch.object(
            main.httpx, "AsyncClient", return_value=context
        ), patch.object(main, "latest_ocr_public_key", return_value="public-key"), patch.object(
            main,
            "current_ocr_source_listing",
            AsyncMock(side_effect=[{"txt_names": {"1.txt", "2.txt", "3.txt"}}, {"txt_names": set()}]),
        ):
            result = await main.delete_ocr_txt(
                request_with_init_data(
                    signed_init_data(
                        user_id=7,
                        username="bigalex_an",
                        auth_date=int(time.time()),
                    )
                ),
                main.OcrDeleteTxtRequest(confirmation="DELETE_ALL_OCR_TXT"),
            )
        self.assertEqual(result["deleted_count"], 3)
        self.assertTrue(result["verified_absent"])

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
        self.assertEqual(call.kwargs["json"]["force_files"], [])
        self.assertEqual(call.kwargs["json"]["engine"], "paddle")
        self.assertIsNone(call.kwargs["json"]["model"])
        self.assertEqual(call.kwargs["headers"]["X-OCR-Token"], "ocr-test-secret")

    async def test_start_forwards_selected_files_for_reprocessing(self):
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
                request_with_init_data(signed_init_data(auth_date=int(time.time()))),
                main.OcrStartRequest(force_files=["106.png", "145.png", "106.png"]),
            )

        self.assertEqual(result["force_files"], ["106.png", "145.png"])
        self.assertEqual(
            client.post.await_args.kwargs["json"]["force_files"],
            ["106.png", "145.png"],
        )

    async def test_ai_start_validates_service_and_forwards_model_and_prompt(self):
        response = MagicMock()
        response.raise_for_status.return_value = None
        client = MagicMock()
        client.post = AsyncMock(return_value=response)
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=client)
        context.__aexit__ = AsyncMock(return_value=False)
        prompt = "Распознай видимый корейский текст без перевода и пояснений."

        with patch.dict(
            os.environ,
            {
                "TELEGRAM_BOT_TOKEN": BOT_TOKEN,
                "OCR_BATCH_TRIGGER_TOKEN": "ocr-test-secret",
            },
            clear=False,
        ), patch.object(
            main, "ai_ocr_service_health", AsyncMock(return_value={"ready": True})
        ), patch.object(main.httpx, "AsyncClient", return_value=context):
            result = await main.start_ocr(
                request_with_init_data(signed_init_data(auth_date=int(time.time()))),
                main.OcrStartRequest(
                    engine="ai",
                    model="gpt-5.6-terra",
                    prompt=prompt,
                    force_files=["106.png"],
                ),
            )

        sent = client.post.await_args.kwargs["json"]
        self.assertEqual(result["engine"], "ai")
        self.assertEqual(sent["model"], "gpt-5.6-terra")
        self.assertEqual(sent["prompt"], prompt)

    async def test_ai_start_rejects_unapproved_model(self):
        with patch.dict(
            os.environ,
            {
                "TELEGRAM_BOT_TOKEN": BOT_TOKEN,
                "OCR_BATCH_TRIGGER_TOKEN": "ocr-test-secret",
            },
            clear=False,
        ):
            with self.assertRaises(HTTPException) as caught:
                await main.start_ocr(
                    request_with_init_data(signed_init_data(auth_date=int(time.time()))),
                    main.OcrStartRequest(
                        engine="ai",
                        model="made-up-model",
                        prompt="Распознай весь видимый текст без перевода.",
                    ),
                )
        self.assertEqual(caught.exception.status_code, 400)

    async def test_config_requires_signed_telegram_request(self):
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": BOT_TOKEN}, clear=False):
            with self.assertRaises(HTTPException) as caught:
                await main.get_ocr_config(request_with_init_data())
        self.assertEqual(caught.exception.status_code, 401)

    async def test_files_lists_only_images_currently_present_in_source(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {
                "source_public_key": "public-key",
                "source_name": "1.png",
                "status": "done",
                "attempts": 1,
                "completed_at": "old",
                "confidence": 0.99,
                "min_confidence": 0.91,
                "ocr_engine": "PaddleOCR",
                "error_message": None,
            },
            {
                "source_public_key": "public-key",
                "source_name": "101.png",
                "status": "done",
                "attempts": 1,
                "completed_at": "now",
                "confidence": 0.97,
                "min_confidence": 0.72,
                "ocr_engine": "PaddleOCR",
                "error_message": None,
            }
        ]
        connection = MagicMock()
        connection.cursor.return_value = cursor

        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": BOT_TOKEN}, clear=False), patch.object(
            main, "get_conn_pg", return_value=connection
        ), patch.object(
            main,
            "current_ocr_source_listing",
            AsyncMock(return_value={"images": ["101.png", "222.png"], "txt_names": {"101.txt"}}),
        ):
            result = await main.get_ocr_files(
                request_with_init_data(signed_init_data(auth_date=int(time.time())))
            )

        self.assertEqual(
            [item["source_name"] for item in result["files"]],
            ["101.png", "222.png"],
        )
        self.assertEqual(result["files"][1]["status"], "new")
        self.assertEqual(result["files"][0]["quality"], "ok")
        self.assertEqual(result["files"][1]["quality"], "unrecognized")

    async def test_files_marks_low_confidence_result_for_review(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {
                "source_public_key": "public-key",
                "source_name": "145.png",
                "status": "done",
                "attempts": 1,
                "completed_at": "now",
                "confidence": 0.93,
                "min_confidence": 0.39,
                "ocr_engine": "PaddleOCR",
                "error_message": None,
            }
        ]
        connection = MagicMock()
        connection.cursor.return_value = cursor

        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": BOT_TOKEN}, clear=False), patch.object(
            main, "get_conn_pg", return_value=connection
        ), patch.object(
            main,
            "current_ocr_source_listing",
            AsyncMock(return_value={"images": ["145.png"], "txt_names": {"145.txt"}}),
        ):
            result = await main.get_ocr_files(
                request_with_init_data(signed_init_data(auth_date=int(time.time())))
            )

        self.assertEqual(result["files"][0]["quality"], "warning")
        self.assertEqual(result["files"][0]["quality_label"], "нужна проверка")

    async def test_files_marks_done_job_unrecognized_when_txt_was_deleted(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {
                "source_public_key": "public-key",
                "source_name": "145.png",
                "status": "done",
                "attempts": 1,
                "completed_at": "now",
                "confidence": 0.99,
                "min_confidence": 0.90,
                "ocr_engine": "PaddleOCR",
                "error_message": None,
            }
        ]
        connection = MagicMock()
        connection.cursor.return_value = cursor

        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": BOT_TOKEN}, clear=False), patch.object(
            main, "get_conn_pg", return_value=connection
        ), patch.object(
            main,
            "current_ocr_source_listing",
            AsyncMock(return_value={"images": ["145.png"], "txt_names": set()}),
        ):
            result = await main.get_ocr_files(
                request_with_init_data(signed_init_data(auth_date=int(time.time())))
            )

        self.assertEqual(result["files"][0]["status"], "new")
        self.assertEqual(result["files"][0]["quality"], "unrecognized")
        self.assertFalse(result["files"][0]["output_exists"])

    async def test_delete_txt_requires_exact_confirmation(self):
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": BOT_TOKEN}, clear=False):
            with self.assertRaises(HTTPException) as caught:
                await main.delete_ocr_txt(
                    request_with_init_data(signed_init_data(auth_date=int(time.time()))),
                    main.OcrDeleteTxtRequest(confirmation="yes"),
                )
        self.assertEqual(caught.exception.status_code, 400)

    async def test_delete_txt_moves_outputs_to_yandex_trash(self):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"deleted_count": 121}
        client = MagicMock()
        client.post = AsyncMock(return_value=response)
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=client)
        context.__aexit__ = AsyncMock(return_value=False)

        with patch.dict(
            os.environ,
            {"TELEGRAM_BOT_TOKEN": BOT_TOKEN, "OCR_BATCH_TRIGGER_TOKEN": "ocr-test-secret"},
            clear=False,
        ), patch.object(main, "latest_ocr_batch", return_value={"status": "done"}), patch.object(
            main.httpx, "AsyncClient", return_value=context
        ), patch.object(main, "latest_ocr_public_key", return_value="public-key"), patch.object(
            main,
            "current_ocr_source_listing",
            AsyncMock(side_effect=[{"txt_names": {f"{index}.txt" for index in range(121)}}, {"txt_names": set()}]),
        ):
            result = await main.delete_ocr_txt(
                request_with_init_data(signed_init_data(auth_date=int(time.time()))),
                main.OcrDeleteTxtRequest(confirmation="DELETE_ALL_OCR_TXT"),
            )

        self.assertEqual(
            result,
            {
                "deleted_count": 121,
                "moved_to_trash": True,
                "verified_absent": True,
                "previous_count": 121,
            },
        )
        call = client.post.await_args
        self.assertEqual(call.kwargs["json"]["confirmation"], "DELETE_ALL_OCR_TXT")
        self.assertFalse(call.kwargs["json"]["dry_run"])
        self.assertEqual(call.kwargs["headers"]["X-OCR-Token"], "ocr-test-secret")

    async def test_merge_builds_current_txt_in_natural_image_order(self):
        listing = {
            "images": ["10.png", "2.png", "1.png", "3.png"],
            "files": {
                "1.txt": {"file": "https://example/1"},
                "2.txt": {"file": "https://example/2"},
                "10.txt": {"file": "https://example/10"},
            },
        }
        with patch.object(
            main,
            "download_public_text",
            AsyncMock(side_effect=["one\n", "two\r\n", "ten"]),
        ):
            result = await main.build_merged_ocr_text(listing)

        self.assertEqual(result["source_names"], ["1.txt", "2.txt", "10.txt"])
        self.assertEqual(result["text"], "one\n\ntwo\n\nten")
        self.assertEqual(result["size"], len(result["text"].encode("utf-8")))

    async def test_merge_txt_sends_verified_content_to_telegram_without_publishing(self):
        merged_text = "one\n\ntwo"
        merged_bytes = merged_text.encode("utf-8")
        merged_hash = main.hashlib.sha256(merged_bytes).hexdigest()
        source_listing = {"images": ["1.png", "2.png"], "files": {}}
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": BOT_TOKEN}, clear=False), patch.object(
            main, "latest_ocr_batch", return_value={"status": "done"}
        ), patch.object(main, "latest_ocr_public_key", return_value="public-key"), patch.object(
            main,
            "current_ocr_source_listing",
            AsyncMock(return_value=source_listing),
        ), patch.object(
            main,
            "build_merged_ocr_text",
            AsyncMock(return_value={
                "text": merged_text,
                "source_names": ["1.txt", "2.txt"],
                "size": len(merged_bytes),
                "sha256": merged_hash,
            }),
        ), patch.object(
            main,
            "send_telegram_text_document",
            AsyncMock(return_value={"message_id": 456, "file_size": len(merged_bytes)}),
        ) as send_document:
            result = await main.merge_ocr_txt(
                request_with_init_data(signed_init_data(auth_date=int(time.time()))),
                main.OcrMergeTxtRequest(confirmation="MERGE_CURRENT_OCR_TXT"),
            )

        self.assertTrue(result["verified"])
        self.assertEqual(result["source_count"], 2)
        self.assertEqual(result["sha256"], merged_hash)
        self.assertTrue(result["delivered_to_telegram"])
        self.assertEqual(result["telegram_message_id"], 456)
        send_document.assert_awaited_once_with(
            923741104,
            main.OCR_MERGED_OUTPUT_NAME,
            merged_text,
            "Объединённый OCR: 2 TXT",
        )

    async def test_send_telegram_text_document_uses_in_memory_upload(self):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "ok": True,
            "result": {
                "message_id": 456,
                "document": {"file_id": "telegram-file", "file_size": 5},
            },
        }
        client = MagicMock()
        client.post = AsyncMock(return_value=response)
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=client)
        context.__aexit__ = AsyncMock(return_value=False)
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "secret-token"}, clear=False), patch.object(
            main.httpx, "AsyncClient", return_value=context
        ):
            result = await main.send_telegram_text_document(
                923741104, "ocr_merged.txt", "hello", "caption"
            )

        self.assertEqual(result["message_id"], 456)
        kwargs = client.post.await_args.kwargs
        self.assertEqual(kwargs["data"]["chat_id"], "923741104")
        self.assertEqual(kwargs["files"]["document"], (
            "ocr_merged.txt", b"hello", "text/plain; charset=utf-8"
        ))

    async def test_merge_txt_requires_exact_confirmation(self):
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": BOT_TOKEN}, clear=False):
            with self.assertRaises(HTTPException) as caught:
                await main.merge_ocr_txt(
                    request_with_init_data(signed_init_data(auth_date=int(time.time()))),
                    main.OcrMergeTxtRequest(confirmation="yes"),
                )
        self.assertEqual(caught.exception.status_code, 400)

    async def test_review_candidate_resumes_completed_state_without_ai_rerun(self):
        job = {
            "id": 12,
            "source_name": "145.png",
            "source_md5": "image-md5",
            "source_public_key": "public-key",
        }
        existing = {
            "id": 5,
            "ocr_job_id": 12,
            "source_name": "145.png",
            "source_md5": "image-md5",
            "status": "needs_review",
            "created_at": None,
            "updated_at": None,
            "accepted_at": None,
        }
        listing = {
            "files": {
                "145.png": {"file": "https://example/image", "md5": "image-md5"},
                "145.txt": {"file": "https://example/text"},
            }
        }
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": BOT_TOKEN}, clear=False), patch.object(
            main, "latest_ocr_batch", return_value={"status": "done"}
        ), patch.object(main, "latest_ocr_job", return_value=job), patch.object(
            main, "current_ocr_source_listing", AsyncMock(return_value=listing)
        ), patch.object(main, "existing_ocr_review", return_value=existing), patch.object(
            main, "download_public_text", AsyncMock()
        ) as download:
            result = await main.create_ocr_review_candidate(
                request_with_init_data(signed_init_data(auth_date=int(time.time()))),
                main.OcrReviewCandidateRequest(source_name="145.png"),
            )

        self.assertTrue(result["resumed"])
        self.assertEqual(result["review"]["status"], "needs_review")
        download.assert_not_awaited()

    async def test_stop_marks_running_batch_for_cooperative_cancellation(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = {
            "id": 9,
            "cancel_requested": True,
            "cancel_requested_at": "now",
        }
        connection = MagicMock()
        connection.cursor.return_value = cursor

        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": BOT_TOKEN}, clear=False), patch.object(
            main, "get_conn_pg", return_value=connection
        ):
            result = await main.stop_ocr(
                request_with_init_data(signed_init_data(auth_date=int(time.time())))
            )

        self.assertTrue(result["accepted"])
        self.assertEqual(result["batch_id"], 9)
        self.assertIn("cancel_requested = true", cursor.execute.call_args.args[0])
        connection.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
