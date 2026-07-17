from __future__ import annotations

import difflib
import re
import unicodedata


def normalize_for_compare(text: str) -> str:
    return unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))


def _metrics(text: str) -> dict:
    normalized = normalize_for_compare(text)
    lines = normalized.splitlines()
    hangul = len(re.findall(r"[\uac00-\ud7a3]", normalized))
    latin_tokens = re.findall(r"(?i)(?<![A-Za-z])[A-Za-z0-9]{1,3}(?![A-Za-z])", normalized)
    suspicious = [token for token in latin_tokens if token.casefold() in {"f1", "i", "l", "ll", "ii"}]
    return {
        "characters": len(normalized),
        "lines": len(lines),
        "nonempty_lines": sum(bool(line.strip()) for line in lines),
        "blank_lines": sum(not line.strip() for line in lines),
        "hangul": hangul,
        "quotes": sum(normalized.count(mark) for mark in ('"', "'", "“", "”", "‘", "’")),
        "ellipsis": len(re.findall(r"(?:\.{3,}|…+)", normalized)),
        "stars": len(re.findall(r"\*+", normalized)),
        "suspicious_latin": suspicious,
    }


def compare_ocr_texts(baseline: str, candidate: str) -> dict:
    left = normalize_for_compare(baseline)
    right = normalize_for_compare(candidate)
    baseline_metrics = _metrics(left)
    candidate_metrics = _metrics(right)
    ratio = difflib.SequenceMatcher(None, left, right, autojunk=False).ratio()
    line_ratio = difflib.SequenceMatcher(
        None, left.splitlines(), right.splitlines(), autojunk=False
    ).ratio()
    lost_nonempty_lines = max(
        0, baseline_metrics["nonempty_lines"] - candidate_metrics["nonempty_lines"]
    )
    punctuation_delta = sum(
        abs(baseline_metrics[key] - candidate_metrics[key])
        for key in ("quotes", "ellipsis", "stars")
    )
    hangul_loss = max(0, baseline_metrics["hangul"] - candidate_metrics["hangul"])
    baseline_artifacts = len(baseline_metrics["suspicious_latin"])
    candidate_artifacts = len(candidate_metrics["suspicious_latin"])
    artifact_improvement = baseline_artifacts - candidate_artifacts

    ready = (
        ratio >= 0.90
        and lost_nonempty_lines == 0
        and abs(baseline_metrics["nonempty_lines"] - candidate_metrics["nonempty_lines"]) <= 1
        and punctuation_delta <= 2
        and hangul_loss <= max(1, baseline_metrics["hangul"] // 100)
        and candidate_artifacts <= baseline_artifacts
    )
    if ready:
        reason = "Варианты близки; строки и пунктуационная структура сохранены"
        if artifact_improvement > 0:
            reason += ", подозрительных латинских артефактов стало меньше"
        verdict = "candidate_ready"
    else:
        reasons = []
        if ratio < 0.90:
            reasons.append("существенное посимвольное расхождение")
        if lost_nonempty_lines or abs(baseline_metrics["nonempty_lines"] - candidate_metrics["nonempty_lines"]) > 1:
            reasons.append("изменилась структура или потеряны строки")
        if punctuation_delta > 2:
            reasons.append("изменилась пунктуационная структура")
        if hangul_loss > max(1, baseline_metrics["hangul"] // 100):
            reasons.append("возможна потеря корейского текста")
        if candidate_artifacts > baseline_artifacts:
            reasons.append("добавились подозрительные латинские артефакты")
        reason = "; ".join(reasons) or "Требуется визуальная проверка"
        verdict = "needs_review"

    diff = list(
        difflib.unified_diff(
            left.splitlines(),
            right.splitlines(),
            fromfile="baseline",
            tofile="candidate",
            lineterm="",
            n=2,
        )
    )
    return {
        "verdict": verdict,
        "reason": reason,
        "similarity": round(ratio, 4),
        "line_similarity": round(line_ratio, 4),
        "lost_nonempty_lines": lost_nonempty_lines,
        "punctuation_delta": punctuation_delta,
        "hangul_loss": hangul_loss,
        "baseline": baseline_metrics,
        "candidate": candidate_metrics,
        "diff": diff[:500],
        "diff_truncated": len(diff) > 500,
    }
