from __future__ import annotations

from dataclasses import dataclass
from itertools import groupby
import re
from statistics import median
from typing import Iterable, Sequence


@dataclass(frozen=True)
class OcrLine:
    text: str
    score: float
    box: Sequence[float] | None = None


def _row_tolerance(lines: Sequence[OcrLine]) -> float:
    heights = [max(1.0, float(line.box[3]) - float(line.box[1])) for line in lines]
    return max(4.0, median(heights) * 0.55)


def _row_key(line: OcrLine, row_tolerance: float) -> tuple[int, float]:
    assert line.box is not None
    center_y = (float(line.box[1]) + float(line.box[3])) / 2
    return (round(center_y / row_tolerance), float(line.box[0]))


def order_lines(lines: Iterable[OcrLine]) -> list[OcrLine]:
    materialized = [line for line in lines if line.text.strip()]
    if not materialized or any(line.box is None or len(line.box) < 4 for line in materialized):
        return materialized

    row_tolerance = _row_tolerance(materialized)
    return sorted(materialized, key=lambda line: _row_key(line, row_tolerance))


def render_text(lines: Iterable[OcrLine]) -> str:
    ordered = order_lines(lines)
    if not ordered:
        return ""

    if any(line.box is None or len(line.box) < 4 for line in ordered):
        return "\n".join(line.text.strip() for line in ordered).strip() + "\n"

    row_tolerance = _row_tolerance(ordered)
    typical_height = median(
        max(1.0, float(line.box[3]) - float(line.box[1])) for line in ordered
    )

    # Боксы одного визуального ряда склеиваются пробелом, ряды — переводами строк,
    # большой вертикальный зазор между рядами становится пустой строкой (абзацем).
    output: list[str] = []
    previous_bottom: float | None = None
    for _, group in groupby(ordered, key=lambda line: _row_key(line, row_tolerance)[0]):
        row = list(group)
        top = min(float(line.box[1]) for line in row)
        if previous_bottom is not None and top - previous_bottom > typical_height * 0.9:
            output.append("")
        text = " ".join(line.text.strip() for line in row)
        text = re.sub(r"\s+([.,!?…:;”’)])", r"\1", text)
        text = re.sub(r"([“‘(])\s+", r"\1", text)
        output.append(text)
        previous_bottom = max(float(line.box[3]) for line in row)

    return "\n".join(output).strip() + "\n"
