"""The templates pass the same checks a real board and desk must pass."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "hooks"))
from check_board import board_defects, desk_defects  # noqa: E402
from keep_working import open_items  # noqa: E402

TEMPLATES = ROOT / "templates"
TEMPLATE_DAY = date(2026, 10, 11)


def test_board_template_passes() -> None:
    assert board_defects((TEMPLATES / "BOARD.md").read_text(encoding="utf-8")) == []


def test_desk_template_passes() -> None:
    assert desk_defects((TEMPLATES / "CEO_DESK.md").read_text(encoding="utf-8"), TEMPLATE_DAY) == []


def test_todo_template_queue_skips_waiting_items() -> None:
    found = open_items(TEMPLATES / "TODO.md")
    assert len(found) == 3 and not any("[waiting]" in item for item in found)


def test_settings_template_is_valid_json_with_both_hooks() -> None:
    settings = json.loads((TEMPLATES / "settings.local.json").read_text(encoding="utf-8"))
    commands = [h["command"] for group in settings["hooks"]["Stop"] for h in group["hooks"]]
    assert any("report_to_coo.py" in c for c in commands) and any("keep_working.py" in c for c in commands)


def test_example_config_is_valid_json() -> None:
    config = json.loads((ROOT / "coo.config.example.json").read_text(encoding="utf-8"))
    assert config["coo_session_id"].startswith("local_")
