from __future__ import annotations

from dataclasses import dataclass
import re
from statistics import median
from typing import Iterable, Sequence


@dataclass(frozen=True)
class OcrLine:
    text: str
    score: float
    box: Sequence[float] | None = None


@dataclass(frozen=True)
class DotRun:
    left: float
    top: float
    right: float
    bottom: float
    count: int


def _height(line: OcrLine) -> float:
    assert line.box is not None
    return max(1.0, float(line.box[3]) - float(line.box[1]))


def _center_y(line: OcrLine) -> float:
    assert line.box is not None
    return (float(line.box[1]) + float(line.box[3])) / 2


def _group_rows(lines: Sequence[OcrLine]) -> list[list[OcrLine]]:
    if not lines:
        return []
    typical_height = median(_height(line) for line in lines)
    rows: list[dict[str, object]] = []
    for line in sorted(lines, key=lambda item: (_center_y(item), float(item.box[0]))):
        top, bottom = float(line.box[1]), float(line.box[3])
        center = _center_y(line)
        best: dict[str, object] | None = None
        best_distance = float("inf")
        for row in rows:
            row_top, row_bottom = float(row["top"]), float(row["bottom"])
            overlap = max(0.0, min(bottom, row_bottom) - max(top, row_top))
            min_height = min(bottom - top, row_bottom - row_top)
            distance = abs(center - float(row["center"]))
            if overlap >= min_height * 0.35 or distance <= typical_height * 0.38:
                if distance < best_distance:
                    best, best_distance = row, distance
        if best is None:
            rows.append({"top": top, "bottom": bottom, "center": center, "items": [line]})
            continue
        items = best["items"]
        assert isinstance(items, list)
        items.append(line)
        best["top"] = min(float(best["top"]), top)
        best["bottom"] = max(float(best["bottom"]), bottom)
        best["center"] = sum(_center_y(item) for item in items) / len(items)

    rows.sort(key=lambda row: (float(row["top"]), float(row["center"])))
    result: list[list[OcrLine]] = []
    for row in rows:
        items = row["items"]
        assert isinstance(items, list)
        result.append(sorted(items, key=lambda item: float(item.box[0])))
    return result


def order_lines(lines: Iterable[OcrLine]) -> list[OcrLine]:
    materialized = [line for line in lines if line.text.strip()]
    if not materialized or any(line.box is None or len(line.box) < 4 for line in materialized):
        return materialized
    return [line for row in _group_rows(materialized) for line in row]


def _deduplicate_overlap(left: str, right: str) -> str:
    for size in range(min(3, len(left), len(right)), 0, -1):
        if left[-size:] == right[:size]:
            return right[size:]
    return right


def _normalize_text(text: str) -> str:
    text = text.translate(str.maketrans({"∗": "*", "⋆": "*", "★": "*"}))
    text = re.sub(r"\s+([.,!?…:;”’])", r"\1", text)
    text = re.sub(r"([“‘(])\s+", r"\1", text)
    # Korean OCR often drops the blank after sentence punctuation even when the
    # screenshot has a visible word gap. Keep decimal numbers untouched.
    text = re.sub(r"(?<!\d)([.!?…,;:])(?=[A-Za-z가-힣0-9])", r"\1 ", text)
    return text


def _insert_dot_run(text: str, line: OcrLine, run: DotRun) -> str:
    if "..." in text:
        return text
    assert line.box is not None
    width = max(1.0, float(line.box[2]) - float(line.box[0]))
    fraction = max(0.0, min(1.0, (run.left - float(line.box[0])) / width))
    index = round(len(text) * fraction)
    return text[:index] + ("." * run.count) + text[index:]


def restore_dot_runs(lines: Iterable[OcrLine], runs: Iterable[DotRun]) -> list[OcrLine]:
    restored = list(lines)
    if not restored:
        return restored
    boxed = [line for line in restored if line.box is not None and len(line.box) >= 4]
    typical_height = median(_height(line) for line in boxed) if boxed else 40.0
    quote_chars = set("\"'“”‘’")

    for run in runs:
        center_y = (run.top + run.bottom) / 2
        containing = [
            line
            for line in boxed
            if float(line.box[0]) <= run.left
            and float(line.box[2]) >= run.right
            and float(line.box[1]) - typical_height * 0.15 <= center_y
            and float(line.box[3]) + typical_height * 0.15 >= center_y
        ]
        if containing:
            host = min(containing, key=lambda line: float(line.box[2]) - float(line.box[0]))
            replacement = OcrLine(
                _insert_dot_run(host.text, host, run), host.score, host.box
            )
            restored[restored.index(host)] = replacement
            boxed[boxed.index(host)] = replacement
            continue

        nearby_quotes = [
            line
            for line in boxed
            if line.text.strip()
            and set(line.text.strip()) <= quote_chars
            and abs(_center_y(line) - center_y) <= typical_height * 0.75
            and float(line.box[2]) >= run.left - typical_height
            and float(line.box[0]) <= run.right + typical_height
        ]
        if nearby_quotes:
            nearby_quotes.sort(key=lambda line: float(line.box[0]))
            left = "".join(line.text.strip() for line in nearby_quotes if float(line.box[0]) < run.left)
            right = "".join(line.text.strip() for line in nearby_quotes if float(line.box[0]) >= run.left)
            for line in nearby_quotes:
                if line in restored:
                    restored.remove(line)
                if line in boxed:
                    boxed.remove(line)
            box = [
                min([run.left] + [float(line.box[0]) for line in nearby_quotes]),
                min([run.top] + [float(line.box[1]) for line in nearby_quotes]),
                max([run.right] + [float(line.box[2]) for line in nearby_quotes]),
                max([run.bottom] + [float(line.box[3]) for line in nearby_quotes]),
            ]
            replacement = OcrLine(left + "." * run.count + right, 1.0, box)
            restored.append(replacement)
            boxed.append(replacement)
            continue

        replacement = OcrLine("." * run.count, 1.0, [run.left, run.top, run.right, run.bottom])
        restored.append(replacement)
        boxed.append(replacement)

    return restored


def render_text(lines: Iterable[OcrLine]) -> str:
    materialized = [line for line in lines if line.text.strip()]
    if not materialized:
        return ""
    if any(line.box is None or len(line.box) < 4 for line in materialized):
        return "\n".join(_normalize_text(line.text.strip()) for line in materialized).strip() + "\n"

    rows = _group_rows(materialized)
    typical_height = median(_height(line) for line in materialized)
    output: list[str] = []
    previous_bottom: float | None = None
    for row in rows:
        top = min(float(line.box[1]) for line in row)
        if previous_bottom is not None and top - previous_bottom > typical_height * 0.9:
            output.append("")
        pieces: list[str] = []
        previous: OcrLine | None = None
        for line in row:
            current = line.text.strip()
            separator = ""
            if previous is not None:
                gap = float(line.box[0]) - float(previous.box[2])
                if gap < 0:
                    current = _deduplicate_overlap(pieces[-1].rstrip(), current).lstrip()
                # Detector boxes are padded and can overlap even when the image
                # has a real word gap, so separate boxes remain space-separated.
                separator = " "
            pieces.append(separator + current)
            previous = line
        output.append(_normalize_text("".join(pieces)))
        previous_bottom = max(float(line.box[3]) for line in row)

    return "\n".join(output).strip() + "\n"
