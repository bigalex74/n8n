from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path
from statistics import fmean, median
from typing import Any

import requests
import cv2
from fastapi import FastAPI, HTTPException
from paddleocr import PaddleOCR
from PIL import Image, ImageOps, ImageStat, UnidentifiedImageError
from pydantic import BaseModel, Field, HttpUrl

from .text_layout import DotRun, OcrLine, render_text, restore_dot_runs


LOG = logging.getLogger("ocr-service")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

MAX_IMAGE_BYTES = int(os.getenv("OCR_MAX_IMAGE_BYTES", str(20 * 1024 * 1024)))
DOWNLOAD_TIMEOUT = float(os.getenv("OCR_DOWNLOAD_TIMEOUT", "45"))
OCR_LANG = os.getenv("OCR_LANG", "korean")
OCR_VERSION = os.getenv("OCR_VERSION", "PP-OCRv5")
OCR_DETECTION_MODEL = os.getenv("OCR_DETECTION_MODEL", "PP-OCRv5_mobile_det")
OCR_RECOGNITION_MODEL = os.getenv(
    "OCR_RECOGNITION_MODEL", "korean_PP-OCRv5_mobile_rec"
)
MIN_SCORE = float(os.getenv("OCR_MIN_SCORE", "0.35"))
MAX_CONCURRENCY = int(os.getenv("OCR_MAX_CONCURRENCY", "1"))


class OcrUrlRequest(BaseModel):
    url: HttpUrl
    source_name: str = Field(default="image", max_length=512)


class OcrResponse(BaseModel):
    text: str
    confidence: float
    min_confidence: float
    line_count: int
    duration_ms: int
    engine: str = "PaddleOCR"
    engine_version: str = OCR_VERSION
    language: str = OCR_LANG
    preprocessed: bool


class Runtime:
    engine: PaddleOCR | None = None
    ready = False
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)


runtime = Runtime()


def _init_engine() -> PaddleOCR:
    LOG.info(
        "Initializing PaddleOCR engine lang=%s version=%s detector=%s recognizer=%s",
        OCR_LANG,
        OCR_VERSION,
        OCR_DETECTION_MODEL,
        OCR_RECOGNITION_MODEL,
    )
    engine = PaddleOCR(
        lang=OCR_LANG,
        ocr_version=OCR_VERSION,
        device="cpu",
        # paddlepaddle 3.3.1 CPU: oneDNN + PIR падает с
        # "ConvertPirAttribute2RuntimeAttribute not support", поэтому mkldnn выключен
        enable_mkldnn=False,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        text_detection_model_name=OCR_DETECTION_MODEL,
        text_recognition_model_name=OCR_RECOGNITION_MODEL,
    )
    LOG.info("PaddleOCR engine is ready")
    return engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    runtime.engine = await asyncio.to_thread(_init_engine)
    runtime.ready = True
    yield
    runtime.ready = False


app = FastAPI(title="Korean OCR service", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok" if runtime.ready else "starting",
        "ready": runtime.ready,
        "engine": "PaddleOCR",
        "engine_version": OCR_VERSION,
        "language": OCR_LANG,
        "detection_model": OCR_DETECTION_MODEL,
        "recognition_model": OCR_RECOGNITION_MODEL,
    }


def _download_image(url: str, destination: Path) -> str:
    try:
        with requests.get(url, stream=True, timeout=(10, DOWNLOAD_TIMEOUT), allow_redirects=True) as response:
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
            if content_type and not content_type.startswith("image/"):
                raise HTTPException(status_code=415, detail="Downloaded resource is not an image")
            total = 0
            with destination.open("wb") as output:
                for chunk in response.iter_content(64 * 1024):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > MAX_IMAGE_BYTES:
                        raise HTTPException(status_code=413, detail="Image exceeds size limit")
                    output.write(chunk)
            if total == 0:
                raise HTTPException(status_code=422, detail="Downloaded image is empty")
            return content_type
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail="Unable to download source image") from exc


def _prepare_image(source: Path, destination: Path) -> bool:
    try:
        with Image.open(source) as image:
            image.load()
            rgb = image.convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=415, detail="Unsupported or corrupt image") from exc

    grayscale = ImageOps.grayscale(rgb)
    mean_luma = float(ImageStat.Stat(grayscale).mean[0])
    processed = mean_luma < 115
    if processed:
        grayscale = ImageOps.invert(grayscale)
    grayscale = ImageOps.autocontrast(grayscale, cutoff=1)

    width, height = grayscale.size
    longest = max(width, height)
    if longest < 1800:
        scale = min(2.0, 1800 / max(1, longest))
        grayscale = grayscale.resize(
            (round(width * scale), round(height * scale)),
            Image.Resampling.LANCZOS,
        )
        processed = True

    grayscale.save(destination, format="PNG", optimize=True)
    return processed


def _result_payload(result: Any) -> dict[str, Any]:
    payload = getattr(result, "json", {})
    if callable(payload):
        payload = payload()
    if not isinstance(payload, dict):
        return {}
    nested = payload.get("res")
    return nested if isinstance(nested, dict) else payload


def _detect_dot_runs(path: Path, lines: list[OcrLine]) -> list[DotRun]:
    boxed = [line for line in lines if line.box is not None and len(line.box) >= 4]
    if not boxed:
        return []
    typical_height = median(
        max(1.0, float(line.box[3]) - float(line.box[1])) for line in boxed
    )
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        return []
    _, foreground = cv2.threshold(image, 180, 255, cv2.THRESH_BINARY_INV)
    _, _, stats, _ = cv2.connectedComponentsWithStats(foreground, 8)
    candidates: list[tuple[float, float, float, float]] = []
    for x, y, width, height, area in stats[1:]:
        if not (typical_height * 0.045 <= width <= typical_height * 0.18):
            continue
        if not (typical_height * 0.045 <= height <= typical_height * 0.18):
            continue
        if not (0.55 <= width / max(height, 1) <= 1.7):
            continue
        if area < width * height * 0.45:
            continue
        candidates.append((float(x), float(y), float(x + width), float(y + height)))

    candidates.sort(key=lambda item: ((item[1] + item[3]) / 2, item[0]))
    groups: list[list[tuple[float, float, float, float]]] = []
    for component in candidates:
        center_y = (component[1] + component[3]) / 2
        match = None
        for group in reversed(groups):
            group_center = sum((item[1] + item[3]) / 2 for item in group) / len(group)
            horizontal_gap = component[0] - group[-1][2]
            if (
                abs(center_y - group_center) <= max(3.0, typical_height * 0.06)
                and 0 <= horizontal_gap <= typical_height * 0.25
            ):
                match = group
                break
        if match is None:
            groups.append([component])
        else:
            match.append(component)

    return [
        DotRun(
            left=min(item[0] for item in group),
            top=min(item[1] for item in group),
            right=max(item[2] for item in group),
            bottom=max(item[3] for item in group),
            count=len(group),
        )
        for group in groups
        if len(group) >= 3
    ]


def _recognize(path: Path) -> tuple[str, list[float]]:
    if runtime.engine is None:
        raise RuntimeError("OCR engine is not initialized")

    results = runtime.engine.predict(str(path))
    lines: list[OcrLine] = []
    scores: list[float] = []
    for result in results:
        payload = _result_payload(result)
        texts = payload.get("rec_texts") or []
        raw_scores = payload.get("rec_scores") or []
        boxes = payload.get("rec_boxes") or []
        for index, text in enumerate(texts):
            score = float(raw_scores[index]) if index < len(raw_scores) else 0.0
            if score < MIN_SCORE or not str(text).strip():
                continue
            box = boxes[index] if index < len(boxes) else None
            lines.append(OcrLine(text=str(text), score=score, box=box))
            scores.append(score)

    lines = restore_dot_runs(lines, _detect_dot_runs(path, lines))
    return render_text(lines), scores


def _process(url: str) -> OcrResponse:
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="ocr-", dir="/tmp/ocr") as directory:
        temp_dir = Path(directory)
        source = temp_dir / "source"
        prepared = temp_dir / "prepared.png"
        _download_image(url, source)
        was_preprocessed = _prepare_image(source, prepared)
        text, scores = _recognize(prepared)

    if not text.strip() or not scores:
        raise HTTPException(status_code=422, detail="OCR returned no text")

    return OcrResponse(
        text=text,
        confidence=round(fmean(scores), 6),
        min_confidence=round(min(scores), 6),
        line_count=len(scores),
        duration_ms=round((time.monotonic() - started) * 1000),
        preprocessed=was_preprocessed,
    )


@app.post("/ocr-url", response_model=OcrResponse)
async def ocr_url(request: OcrUrlRequest) -> OcrResponse:
    if not runtime.ready:
        raise HTTPException(status_code=503, detail="OCR engine is starting")
    async with runtime.semaphore:
        try:
            return await asyncio.to_thread(_process, str(request.url))
        except HTTPException:
            raise
        except Exception as exc:
            LOG.exception("OCR failed for source_name=%s", request.source_name)
            raise HTTPException(status_code=500, detail="OCR processing failed") from exc
