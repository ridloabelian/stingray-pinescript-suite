#!/usr/bin/env python3
"""Static validator for TradingView Pine Script v6 files and webhook JSON schemas."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_PATTERNS = {
    "indicators/stingray_harmonic_prz.pine": [
        r"//@version=6",
        r"indicator\(",
        r"1\.272",
        r"0\.886",
        r"0\.786",
        r"1\.618",
        r"1\.13",
        r"0\.382",
        r"0\.50",
        r"0\.618",
        r"alertcondition\(",
    ],
    "indicators/halte_vs_terminal_3mode.pine": [
        r"//@version=6",
        r"indicator\(",
        r"Mode 1: Pure SMC",
        r"Mode 2: Fibo Golden Pullback",
        r"Mode 3: Indicator Halte \+ Regime Filter",
        r"Body Close",
        r"Wick Break",
        r"NO-TRADE / DIAM",
        r"0\.786",
        r"25",
        r"50",
        r"100",
        r"200",
    ],
    "indicators/mtf_scalp_alignment_hud.pine": [
        r"//@version=6",
        r"indicator\(",
        r"request\.security\(",
        r"0600-1400",
        r"1500-1900",
        r"Asia/Jakarta",
        r"alertcondition\(",
    ],
}

FORBIDDEN_DEPRECATED = [
    (r"\bstudy\s*\(", "Deprecated v4 study() call; use indicator()"),
    (r"(?<!request\.)\bsecurity\s*\(", "Deprecated v4 security() call; use request.security()"),
    (r"\btransp\s*=", "Deprecated transp= argument; use color.new()"),
]


def strip_comments_and_strings(text: str) -> str:
    """Strip Pine line comments and string literals before delimiter balancing."""
    out = []
    for line in text.splitlines():
        no_comment = re.sub(r"//.*$", "", line)
        no_str = re.sub(r'"(?:\\.|[^"\\])*"', '""', no_comment)
        out.append(no_str)
    return "\n".join(out)


def check_delimiters(text: str, rel_path: str) -> list[str]:
    errors: list[str] = []
    cleaned = strip_comments_and_strings(text)
    pairs = {"(": ")", "[": "]"}
    stack: list[tuple[str, int]] = []
    for line_no, line in enumerate(cleaned.splitlines(), 1):
        for ch in line:
            if ch in pairs:
                stack.append((ch, line_no))
            elif ch in pairs.values():
                if not stack:
                    errors.append(f"{rel_path}:{line_no}: unexpected closing '{ch}'")
                else:
                    open_ch, open_line = stack.pop()
                    if pairs[open_ch] != ch:
                        errors.append(
                            f"{rel_path}:{line_no}: mismatched '{open_ch}' (line {open_line}) with '{ch}'"
                        )
    for open_ch, open_line in stack:
        errors.append(f"{rel_path}:{open_line}: unclosed '{open_ch}'")
    return errors


def validate_pine_file(rel_path: str) -> list[str]:
    path = ROOT / rel_path
    if not path.exists():
        return [f"Missing file: {rel_path}"]
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []

    if not text.lstrip().startswith("//@version=6"):
        errors.append(f"{rel_path}: must start with //@version=6")

    for pat, msg in FORBIDDEN_DEPRECATED:
        if re.search(pat, text):
            errors.append(f"{rel_path}: {msg}")

    for req in REQUIRED_PATTERNS.get(rel_path, []):
        if not re.search(req, text):
            errors.append(f"{rel_path}: missing required pattern '{req}'")

    errors.extend(check_delimiters(text, rel_path))
    return errors


def validate_webhooks() -> list[str]:
    path = ROOT / "webhooks/tradingview_alert_templates.json"
    if not path.exists():
        return ["Missing webhooks/tradingview_alert_templates.json"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"Invalid JSON in tradingview_alert_templates.json: {exc}"]
    alerts = data.get("alerts")
    if not isinstance(alerts, list) or len(alerts) < 4:
        return ["Expected at least 4 webhook alert templates"]
    errors: list[str] = []
    for item in alerts:
        if not all(k in item for k in ("id", "indicator", "alertcondition", "payload")):
            errors.append(f"Incomplete webhook template: {item}")
        elif not (ROOT / item["indicator"]).exists():
            errors.append(f"Webhook template references missing indicator: {item['indicator']}")
    return errors


def run_all_checks() -> list[str]:
    errors: list[str] = []
    for rel_path in REQUIRED_PATTERNS:
        errors.extend(validate_pine_file(rel_path))
    errors.extend(validate_webhooks())
    return errors


def main() -> int:
    errors = run_all_checks()
    if errors:
        for err in errors:
            print(f"[FAIL] {err}", file=sys.stderr)
        return 1
    print(f"[OK] Validated {len(REQUIRED_PATTERNS)} Pine Script v6 indicators and webhook templates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
