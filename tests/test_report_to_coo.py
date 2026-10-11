"""Tests for hooks/report_to_coo.py: blocks only a COO turn with text left after the report."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks"))
import report_to_coo as rc  # noqa: E402

COO = "local_test-coo"
LONG = "x" * 400


def setup_module() -> None:
    """Points the hook at a fake COO id, whatever the local configuration says."""
    rc.COO_ID = COO
    rc.COO_MARK = f'<cross-session-message from="{COO}"'
    rc.THRESHOLD = 300


def user(text: str) -> dict[str, Any]:
    """A user line of the transcript."""
    return {"type": "user", "message": {"content": text}}


def send(to: str) -> dict[str, Any]:
    """An assistant line with a SendMessage call."""
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": "SendMessage", "input": {"to": to, "message": "report"}}]}}


def transcript(tmp_path: Path, lines: list[dict[str, Any]]) -> str:
    """Writes a transcript and returns its path."""
    path = tmp_path / "t.jsonl"
    path.write_text("\n".join(json.dumps(line) for line in lines), encoding="utf-8")
    return str(path)


def test_blocks_text_after_the_report_in_a_coo_turn(tmp_path: Path) -> None:
    path = transcript(tmp_path, [user(f'<cross-session-message from="{COO}">do X'), send("COO [abc123]")])
    assert rc.should_block({"transcript_path": path, "last_assistant_message": LONG})


def test_a_short_closing_line_is_fine(tmp_path: Path) -> None:
    path = transcript(tmp_path, [user(f'<cross-session-message from="{COO}">do X'), send(COO)])
    assert not rc.should_block({"transcript_path": path, "last_assistant_message": "Sent."})


def test_a_turn_opened_by_the_ceo_is_left_alone(tmp_path: Path) -> None:
    path = transcript(tmp_path, [user("please do X"), send(COO)])
    assert not rc.should_block({"transcript_path": path, "last_assistant_message": LONG})


def test_no_report_sent_means_nothing_to_enforce(tmp_path: Path) -> None:
    path = transcript(tmp_path, [user(f'<cross-session-message from="{COO}">do X')])
    assert not rc.should_block({"transcript_path": path, "last_assistant_message": LONG})


def test_tool_results_do_not_open_a_turn(tmp_path: Path) -> None:
    tool_result = {"type": "user", "message": {"content": [{"type": "tool_result", "content": "ok"}]}}
    path = transcript(tmp_path, [user(f'<cross-session-message from="{COO}">do X'), send(COO), tool_result])
    assert rc.should_block({"transcript_path": path, "last_assistant_message": LONG})


def test_second_attempt_always_lets_go(tmp_path: Path) -> None:
    path = transcript(tmp_path, [user(f'<cross-session-message from="{COO}">do X'), send(COO)])
    assert not rc.should_block({"transcript_path": path, "last_assistant_message": LONG, "stop_hook_active": True})
