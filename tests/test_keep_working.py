"""Tests for hooks/keep_working.py: blocks with open items, lets the turn end when paused, empty or spinning."""

from __future__ import annotations

import datetime as dt
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks"))
import keep_working as kw  # noqa: E402

TODO = """# TODO

## Open
- [ ] item outside the queue

## Autonomous queue
- [ ] first queue item
- [ ] [waiting] item waiting for the CEO
  - [ ] sub-item that does not count
- [x] done item

## Done
- [ ] item outside the section
"""


def repo(tmp_path: Path, todo: str = TODO) -> Path:
    """Creates a git repository with a TODO and one commit."""
    (tmp_path / "TODO.md").write_text(todo, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    commit(tmp_path, "first")
    return tmp_path


def commit(folder: Path, message: str) -> None:
    """Adds an empty commit."""
    subprocess.run(["git", "-C", str(folder), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q",
                    "--allow-empty", "-m", message], check=True)


def test_open_items_only_from_the_queue(tmp_path: Path) -> None:
    (tmp_path / "TODO.md").write_text(TODO, encoding="utf-8")
    assert kw.open_items(tmp_path / "TODO.md") == ["first queue item"]


def test_blocks_with_the_first_item(tmp_path: Path) -> None:
    answer = kw.decide({"cwd": str(repo(tmp_path))})
    assert answer is not None and answer["decision"] == "block"
    assert "first queue item" in answer["reason"]


def test_lets_the_turn_end_when_paused(tmp_path: Path) -> None:
    folder = repo(tmp_path)
    (folder / ".claude").mkdir()
    (folder / ".claude" / "queue_paused").write_text("", encoding="utf-8")
    assert kw.decide({"cwd": str(folder)}) is None


def test_lets_the_turn_end_when_empty_or_all_waiting(tmp_path: Path) -> None:
    folder = repo(tmp_path, "## Autonomous queue\n- [x] done\n- [ ] [waiting] for a supplier\n")
    assert kw.decide({"cwd": str(folder)}) is None


def test_lets_the_turn_end_without_a_todo(tmp_path: Path) -> None:
    assert kw.decide({"cwd": str(tmp_path)}) is None


def test_spinning_warns_then_lets_go(tmp_path: Path) -> None:
    folder = repo(tmp_path)
    t = dt.datetime(2026, 10, 8, 16, 0)
    answers = [kw.decide({"cwd": str(folder)}, t + dt.timedelta(minutes=i)) for i in range(5)]
    assert [a["decision"] if a else None for a in answers] == ["block", "block", "block", "block", None]
    assert answers[3] is not None and "without a new commit" in answers[3]["reason"]


def test_a_new_commit_resets_the_count(tmp_path: Path) -> None:
    folder = repo(tmp_path)
    t = dt.datetime(2026, 10, 8, 16, 0)
    for i in range(3):
        kw.decide({"cwd": str(folder)}, t + dt.timedelta(minutes=i))
    commit(folder, "item done")
    answer = kw.decide({"cwd": str(folder)}, t + dt.timedelta(minutes=4))
    assert answer is not None and "first queue item" in answer["reason"]


def test_a_new_turn_after_a_pause_resets_the_count(tmp_path: Path) -> None:
    folder = repo(tmp_path)
    t = dt.datetime(2026, 10, 8, 16, 0)
    for i in range(4):
        kw.decide({"cwd": str(folder)}, t + dt.timedelta(minutes=i))
    answer = kw.decide({"cwd": str(folder)}, t + dt.timedelta(minutes=60))
    assert answer is not None and "first queue item" in answer["reason"]
