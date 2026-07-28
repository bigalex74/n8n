import os
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import BackgroundTasks, HTTPException
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

    async def test_ai_health_exposes_oauth_failure_for_ui(self):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "ready": False,
            "status": "unavailable",
            "engine": "Codex CLI",
            "auth": "missing",
            "error_code": "codex_oauth_unavailable",
            "detail": "Codex OAuth session is unavailable; sign in again",
        }
        client = MagicMock()
        client.get = AsyncMock(return_value=response)
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=client)
        context.__aexit__ = AsyncMock(return_value=False)

        with patch.object(main.httpx, "AsyncClient", return_value=context):
            result = await main.ai_ocr_service_health()

        self.assertFalse(result["ready"])
        self.assertEqual(result["error_code"], "codex_oauth_unavailable")
        self.assertIn("Авторизация AI OCR", result["user_message"])

    async def test_ai_start_reports_oauth_failure_in_plain_language(self):
        with patch.dict(
            os.environ,
            {
                "TELEGRAM_BOT_TOKEN": BOT_TOKEN,
                "OCR_BATCH_TRIGGER_TOKEN": "ocr-test-secret",
            },
            clear=False,
        ), patch.object(
            main,
            "ai_ocr_service_health",
            AsyncMock(
                return_value={
                    "ready": False,
                    "auth": "missing",
                    "error_code": "codex_oauth_unavailable",
                }
            ),
        ):
            with self.assertRaises(HTTPException) as caught:
                await main.start_ocr(
                    request_with_init_data(signed_init_data(auth_date=int(time.time()))),
                    main.OcrStartRequest(
                        engine="ai",
                        model="gpt-5.6-luna",
                        prompt="Распознай весь видимый текст без перевода.",
                    ),
                )

        self.assertEqual(caught.exception.status_code, 503)
        self.assertIn("Авторизация AI OCR", caught.exception.detail)

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

    async def test_merge_txt_sends_verified_content_to_requesting_operator(self):
        merged_text = "one\n\ntwo"
        merged_bytes = merged_text.encode("utf-8")
        merged_hash = main.hashlib.sha256(merged_bytes).hexdigest()
        source_listing = {"images": ["1.png", "2.png"], "files": {}}
        with patch.dict(
            os.environ,
            {
                "TELEGRAM_BOT_TOKEN": BOT_TOKEN,
                "OCR_OWNER_ID": "923741104",
                "OCR_OPERATOR_IDS": "1011396552",
            },
            clear=False,
        ), patch.object(
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
                request_with_init_data(
                    signed_init_data(user_id=1011396552, auth_date=int(time.time()))
                ),
                main.OcrMergeTxtRequest(confirmation="MERGE_CURRENT_OCR_TXT"),
            )

        self.assertTrue(result["verified"])
        self.assertEqual(result["source_count"], 2)
        self.assertEqual(result["sha256"], merged_hash)
        self.assertTrue(result["delivered_to_telegram"])
        self.assertEqual(result["telegram_message_id"], 456)
        send_document.assert_awaited_once_with(
            1011396552,
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

    async def test_review_candidates_processes_all_unique_selected_files(self):
        async def fake_single(payload):
            return {"review": {"source_name": payload.source_name, "status": "needs_review"}}

        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": BOT_TOKEN}, clear=False), patch.object(
            main, "create_single_ocr_review_candidate", AsyncMock(side_effect=fake_single)
        ) as create_single, patch.object(
            main, "latest_ocr_batch", return_value={"status": "done"}
        ), patch.object(
            main, "latest_ocr_review_batch", return_value=None
        ), patch.object(
            main, "create_ocr_review_batch", return_value={"id": 77}
        ), patch.object(
            main, "update_ocr_review_batch"
        ), patch.object(
            main, "finish_ocr_review_batch"
        ), patch.object(
            main, "ai_ocr_service_health", AsyncMock(return_value={"ready": True})
        ):
            background_tasks = BackgroundTasks()
            result = await main.create_ocr_review_candidates(
                request_with_init_data(signed_init_data(auth_date=int(time.time()))),
                main.OcrReviewCandidatesRequest(
                    source_names=["145.png", "146.png", "145.PNG", "147.png"],
                    model="gpt-5.6-terra",
                    prompt="Распознай корейский текст точно, без перевода и домыслов.",
                ),
                background_tasks,
            )
            await background_tasks()

        self.assertEqual(result["requested"], 3)
        self.assertEqual(result["queued"], 3)
        self.assertEqual(result["completed"], 0)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["run_id"], 77)
        self.assertEqual(
            [call.args[0].source_name for call in create_single.await_args_list],
            ["145.png", "146.png", "147.png"],
        )

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

    async def test_files_marks_ai_review_status_blue_and_failed_red(self):
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
            },
            {
                "source_public_key": "public-key",
                "source_name": "146.png",
                "status": "failed",
                "attempts": 2,
                "completed_at": None,
                "confidence": None,
                "min_confidence": None,
                "ocr_engine": "PaddleOCR",
                "error_message": "boom",
            },
        ]
        connection = MagicMock()
        connection.cursor.return_value = cursor
        reviews = {
            "145.png": {"id": 5, "source_name": "145.png", "source_md5": "m1", "status": "needs_review"},
        }
        listing = {
            "images": ["145.png", "146.png"],
            "txt_names": {"145.txt"},
            "files": {"145.png": {"md5": "m1"}},
        }

        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": BOT_TOKEN}, clear=False), patch.object(
            main, "get_conn_pg", return_value=connection
        ), patch.object(
            main, "latest_reviews_by_source", return_value=reviews
        ), patch.object(
            main, "current_ocr_source_listing", AsyncMock(return_value=listing)
        ):
            result = await main.get_ocr_files(
                request_with_init_data(signed_init_data(auth_date=int(time.time())))
            )

        by_name = {row["source_name"]: row for row in result["files"]}
        self.assertEqual(by_name["145.png"]["quality"], "ai")
        self.assertEqual(by_name["145.png"]["quality_label"], "обработано ИИ — ждёт проверки")
        self.assertEqual(by_name["145.png"]["review_status"], "needs_review")
        self.assertEqual(by_name["146.png"]["quality"], "error")
        self.assertEqual(by_name["146.png"]["quality_label"], "ошибка OCR")

    async def test_files_ignores_stale_review_when_image_md5_changed(self):
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
        reviews = {
            "145.png": {"id": 5, "source_name": "145.png", "source_md5": "old-md5", "status": "accepted"},
        }
        listing = {
            "images": ["145.png"],
            "txt_names": {"145.txt"},
            "files": {"145.png": {"md5": "new-md5"}},
        }

        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": BOT_TOKEN}, clear=False), patch.object(
            main, "get_conn_pg", return_value=connection
        ), patch.object(
            main, "latest_reviews_by_source", return_value=reviews
        ), patch.object(
            main, "current_ocr_source_listing", AsyncMock(return_value=listing)
        ):
            result = await main.get_ocr_files(
                request_with_init_data(signed_init_data(auth_date=int(time.time())))
            )

        self.assertIsNone(result["files"][0]["review_status"])
        self.assertEqual(result["files"][0]["quality"], "ok")

    async def test_reject_with_edited_text_publishes_and_saves_new_baseline(self):
        review_row = {
            "id": 7,
            "source_name": "145.png",
            "source_md5": "image-md5",
            "status": "needs_review",
            "baseline_text": "старый текст",
            "candidate_text": "вариант ИИ",
            "created_at": None,
            "updated_at": None,
            "accepted_at": None,
        }
        updated_row = dict(review_row, status="rejected", baseline_text="исправленный текст")
        cursor = MagicMock()
        cursor.fetchone.side_effect = [review_row, updated_row]
        connection = MagicMock()
        connection.cursor.return_value = cursor
        publish = AsyncMock(
            return_value={"sha256": main.hashlib.sha256("исправленный текст".encode()).hexdigest()}
        )

        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": BOT_TOKEN}, clear=False), patch.object(
            main, "get_conn_pg", return_value=connection
        ), patch.object(
            main, "latest_ocr_job", return_value={"source_md5": "image-md5"}
        ), patch.object(main, "publish_review_text", publish):
            result = await main.act_on_ocr_review(
                7,
                request_with_init_data(signed_init_data(auth_date=int(time.time()))),
                main.OcrReviewActionRequest(action="reject", edited_text="исправленный текст"),
            )

        publish.assert_awaited_once_with("145.png", "исправленный текст")
        self.assertEqual(result["review"]["status"], "rejected")
        update_sql = cursor.execute.call_args.args[0]
        self.assertIn("baseline_text = COALESCE", update_sql)
        update_params = cursor.execute.call_args.args[1]
        self.assertEqual(update_params[1], "исправленный текст")

    async def test_reject_without_edits_does_not_publish(self):
        review_row = {
            "id": 7,
            "source_name": "145.png",
            "source_md5": "image-md5",
            "status": "needs_review",
            "baseline_text": "старый текст",
            "candidate_text": "вариант ИИ",
            "created_at": None,
            "updated_at": None,
            "accepted_at": None,
        }
        updated_row = dict(review_row, status="rejected")
        cursor = MagicMock()
        cursor.fetchone.side_effect = [review_row, updated_row]
        connection = MagicMock()
        connection.cursor.return_value = cursor
        publish = AsyncMock()

        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": BOT_TOKEN}, clear=False), patch.object(
            main, "get_conn_pg", return_value=connection
        ), patch.object(
            main, "latest_ocr_job", return_value={"source_md5": "image-md5"}
        ), patch.object(main, "publish_review_text", publish):
            result = await main.act_on_ocr_review(
                7,
                request_with_init_data(signed_init_data(auth_date=int(time.time()))),
                main.OcrReviewActionRequest(action="reject", edited_text="старый текст"),
            )

        publish.assert_not_awaited()
        self.assertEqual(result["review"]["status"], "rejected")

    async def test_accept_with_edited_candidate_publishes_and_saves_candidate(self):
        review_row = {
            "id": 8,
            "source_name": "145.png",
            "source_md5": "image-md5",
            "status": "candidate_ready",
            "baseline_text": "старый текст",
            "candidate_text": "вариант ИИ",
            "created_at": None,
            "updated_at": None,
            "accepted_at": None,
        }
        updated_row = dict(review_row, status="accepted", candidate_text="исправленный вариант ИИ")
        cursor = MagicMock()
        cursor.fetchone.side_effect = [review_row, updated_row]
        connection = MagicMock()
        connection.cursor.return_value = cursor
        publish = AsyncMock(
            return_value={"sha256": main.hashlib.sha256("исправленный вариант ИИ".encode()).hexdigest()}
        )

        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": BOT_TOKEN}, clear=False), patch.object(
            main, "get_conn_pg", return_value=connection
        ), patch.object(
            main, "latest_ocr_job", return_value={"source_md5": "image-md5"}
        ), patch.object(main, "publish_review_text", publish):
            result = await main.act_on_ocr_review(
                8,
                request_with_init_data(signed_init_data(auth_date=int(time.time()))),
                main.OcrReviewActionRequest(
                    action="accept",
                    edited_candidate_text="исправленный вариант ИИ",
                ),
            )

        publish.assert_awaited_once_with("145.png", "исправленный вариант ИИ")
        self.assertEqual(result["review"]["status"], "accepted")
        update_sql = cursor.execute.call_args.args[0]
        self.assertIn("candidate_text = COALESCE", update_sql)
        update_params = cursor.execute.call_args.args[1]
        self.assertEqual(update_params[3], "исправленный вариант ИИ")

    async def test_publish_text_file_retries_transient_yandex_publish_failure(self):
        failed_response = MagicMock()
        failed_response.raise_for_status.side_effect = main.httpx.HTTPStatusError(
            "server error",
            request=main.httpx.Request("POST", main.OCR_REVIEW_PUBLISH_WEBHOOK_URL),
            response=main.httpx.Response(500),
        )
        ok_response = MagicMock()
        ok_response.raise_for_status.return_value = None
        ok_response.json.return_value = {"published": True, "sha256": "digest"}
        client = MagicMock()
        client.post = AsyncMock(side_effect=[failed_response, ok_response])
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=client)
        context.__aexit__ = AsyncMock(return_value=False)

        with patch.dict(
            os.environ, {"OCR_BATCH_TRIGGER_TOKEN": "ocr-test-secret"}, clear=False
        ), patch.object(main.httpx, "AsyncClient", return_value=context), patch.object(
            main.asyncio, "sleep", AsyncMock()
        ) as sleep:
            result = await main.publish_text_file("145.txt", "текст")

        self.assertTrue(result["published"])
        self.assertEqual(client.post.await_count, 2)
        sleep.assert_awaited_once_with(3)

    async def test_publish_text_file_explains_yandex_publish_failure_after_retries(self):
        failed_response = MagicMock()
        failed_response.raise_for_status.side_effect = main.httpx.HTTPStatusError(
            "server error",
            request=main.httpx.Request("POST", main.OCR_REVIEW_PUBLISH_WEBHOOK_URL),
            response=main.httpx.Response(500),
        )
        client = MagicMock()
        client.post = AsyncMock(return_value=failed_response)
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=client)
        context.__aexit__ = AsyncMock(return_value=False)

        with patch.dict(
            os.environ, {"OCR_BATCH_TRIGGER_TOKEN": "ocr-test-secret"}, clear=False
        ), patch.object(main.httpx, "AsyncClient", return_value=context), patch.object(
            main.asyncio, "sleep", AsyncMock()
        ):
            with self.assertRaises(HTTPException) as caught:
                await main.publish_text_file("145.txt", "текст")

        self.assertEqual(caught.exception.status_code, 502)
        self.assertIn("Yandex Disk временно не принял TXT", caught.exception.detail)
        self.assertEqual(client.post.await_count, 3)

    async def test_clear_all_requires_exact_confirmation(self):
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": BOT_TOKEN}, clear=False):
            with self.assertRaises(HTTPException) as caught:
                await main.clear_ocr_folder(
                    request_with_init_data(signed_init_data(auth_date=int(time.time()))),
                    main.OcrClearAllRequest(confirmation="DELETE_ALL_OCR_TXT"),
                )
        self.assertEqual(caught.exception.status_code, 400)

    async def test_clear_all_moves_png_and_txt_to_trash_and_verifies_empty(self):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"deleted_count": 4}
        client = MagicMock()
        client.post = AsyncMock(return_value=response)
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=client)
        context.__aexit__ = AsyncMock(return_value=False)
        with patch.dict(
            os.environ,
            {"TELEGRAM_BOT_TOKEN": BOT_TOKEN, "OCR_BATCH_TRIGGER_TOKEN": "ocr-test-secret"},
            clear=False,
        ), patch.object(main, "latest_ocr_batch", return_value=None), patch.object(
            main.httpx, "AsyncClient", return_value=context
        ), patch.object(main, "latest_ocr_public_key", return_value="public-key"), patch.object(
            main,
            "current_ocr_source_listing",
            AsyncMock(side_effect=[
                {"images": ["1.png", "2.png"], "txt_names": {"1.txt", "2.txt"}},
                {"images": [], "txt_names": set()},
            ]),
        ):
            result = await main.clear_ocr_folder(
                request_with_init_data(signed_init_data(auth_date=int(time.time()))),
                main.OcrClearAllRequest(confirmation="DELETE_ALL_OCR_FILES"),
            )

        self.assertEqual(result["deleted_count"], 4)
        self.assertTrue(result["verified_absent"])
        self.assertEqual(result["previous_images"], 2)
        sent = client.post.call_args.kwargs["json"]
        self.assertEqual(sent["scope"], "all")
        self.assertEqual(sent["confirmation"], "DELETE_ALL_OCR_FILES")

    async def test_text_endpoint_returns_current_txt_or_absence(self):
        listing = {
            "images": ["145.png"],
            "txt_names": {"145.txt"},
            "files": {"145.txt": {"name": "145.txt", "file": "https://example/text"}},
        }
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": BOT_TOKEN}, clear=False), patch.object(
            main, "latest_ocr_public_key", return_value="public-key"
        ), patch.object(
            main, "current_ocr_source_listing", AsyncMock(return_value=listing)
        ), patch.object(
            main, "download_public_text", AsyncMock(return_value="распознанный текст")
        ):
            found = await main.get_ocr_text(
                "145.png",
                request_with_init_data(signed_init_data(auth_date=int(time.time()))),
            )
            missing = await main.get_ocr_text(
                "999.png",
                request_with_init_data(signed_init_data(auth_date=int(time.time()))),
            )

        self.assertTrue(found["exists"])
        self.assertEqual(found["text"], "распознанный текст")
        self.assertFalse(missing["exists"])
        self.assertEqual(missing["txt_name"], "999.txt")

    async def test_image_endpoint_streams_current_image_and_rejects_traversal(self):
        listing = {
            "images": ["145.png"],
            "txt_names": set(),
            "files": {"145.png": {"name": "145.png", "file": "https://example/image", "mime_type": "image/png"}},
        }
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": BOT_TOKEN}, clear=False), patch.object(
            main, "latest_ocr_public_key", return_value="public-key"
        ), patch.object(
            main, "current_ocr_source_listing", AsyncMock(return_value=listing)
        ), patch.object(
            main, "download_public_bytes", AsyncMock(return_value=b"png-bytes")
        ):
            response = await main.get_ocr_image(
                "145.png",
                request_with_init_data(signed_init_data(auth_date=int(time.time()))),
            )
            with self.assertRaises(HTTPException) as caught:
                await main.get_ocr_image(
                    "../secret.png",
                    request_with_init_data(signed_init_data(auth_date=int(time.time()))),
                )

        self.assertEqual(response.body, b"png-bytes")
        self.assertEqual(response.media_type, "image/png")
        self.assertEqual(caught.exception.status_code, 400)

    async def test_tgs_convert_processes_all_svg_files(self):
        listing = {
            "folder_path": "/Yulia/+ Test/tgs",
            "files": [],
            "svg": [
                {"name": "row1-03.svg", "path": "disk:/Yulia/+ Test/tgs/row1-03.svg"},
                {"name": "row1-04.svg", "path": "disk:/Yulia/+ Test/tgs/row1-04.svg"},
            ],
            "tgs": [],
        }
        upload = AsyncMock()
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": BOT_TOKEN}, clear=False), patch.object(
            main, "current_tgs_folder_listing", AsyncMock(return_value=listing)
        ), patch.object(
            main, "yandex_download_resource", AsyncMock(side_effect=[b"<svg/>", b"<svg/>"])
        ), patch.object(
            main, "convert_svg_bytes_to_tgs", side_effect=[b"tgs-1", b"tgs-2"]
        ), patch.object(main, "yandex_upload_resource", upload):
            result = await main.convert_tgs_folder(
                request_with_init_data(signed_init_data(auth_date=int(time.time())))
            )

        self.assertEqual(result["converted_count"], 2)
        self.assertEqual(upload.await_count, 2)
        self.assertEqual(upload.await_args_list[0].args[0], "disk:/Yulia/+ Test/tgs/row1-03.tgs")
        self.assertEqual(upload.await_args_list[1].args[0], "disk:/Yulia/+ Test/tgs/row1-04.tgs")

    async def test_tgs_delete_requires_confirmation_and_moves_selected_scope_to_trash(self):
        listing = {
            "folder_path": "/Yulia/+ Test/tgs",
            "files": [],
            "svg": [{"name": "row1-03.svg", "path": "disk:/Yulia/+ Test/tgs/row1-03.svg"}],
            "tgs": [{"name": "row1-03.tgs", "path": "disk:/Yulia/+ Test/tgs/row1-03.tgs"}],
        }
        trash = AsyncMock()
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": BOT_TOKEN}, clear=False), patch.object(
            main, "current_tgs_folder_listing", AsyncMock(return_value=listing)
        ), patch.object(main, "yandex_trash_resource", trash):
            with self.assertRaises(HTTPException) as caught:
                await main.delete_tgs_files(
                    request_with_init_data(signed_init_data(auth_date=int(time.time()))),
                    main.TgsDeleteRequest(scope="svg", confirmation="WRONG"),
                )
            result = await main.delete_tgs_files(
                request_with_init_data(signed_init_data(auth_date=int(time.time()))),
                main.TgsDeleteRequest(scope="svg", confirmation="DELETE_ALL_SVG"),
            )

        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(result["deleted_count"], 1)
        trash.assert_awaited_once_with("disk:/Yulia/+ Test/tgs/row1-03.svg")


if __name__ == "__main__":
    unittest.main()
