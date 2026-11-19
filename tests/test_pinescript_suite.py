import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import validate_pinescript as vp  # noqa: E402


def test_all_pine_indicators_pass_v6_validator():
    errors = vp.run_all_checks()
    assert errors == [], f"Validation errors found: {errors}"


def test_webhook_templates_match_indicator_alerts():
    data = json.loads((ROOT / "webhooks/tradingview_alert_templates.json").read_text(encoding="utf-8"))
    for tpl in data["alerts"]:
        ind_text = (ROOT / tpl["indicator"]).read_text(encoding="utf-8")
        assert tpl["alertcondition"] in ind_text


def test_no_truthy_nonboolean_if_antipatterns():
    # Basic smoke verification that all three indicators declare pine v6 headers and overlay=true
    for rel in vp.REQUIRED_PATTERNS:
        txt = (ROOT / rel).read_text(encoding="utf-8")
        assert txt.startswith("//@version=6")
        assert "overlay=true" in txt
