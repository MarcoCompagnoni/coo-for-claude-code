"""Tests for scripts/check_board.py: board table defects and desk shape."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_board import board_defects, desk_defects  # noqa: E402

HEAD = "| Project | Today | Done | Status |\n|---|---|---|---|\n"
TODAY = date(2026, 10, 6)

DESK_OK = """# CEO desk

*Updated by the COO on 06/10/2026 at 10:00.*

## To clean

Shop (82%, `/clear`: TODO up to date, nothing in flight).

## Decide

- `TR1` **Invoicing · A or B?** Recommend A. If no answer: nothing happens (31/10). http://localhost:8000/tr1.html. Write `TR1 A` or `TR1 B`.

## Do

- `MR1` **Marketing · 2 min · grant access to the hosting account.** Unblocks the invoice. `MR1 done`.

## Decided by COO

- `GY1` **Research · switched the data source from today** (06/10). `GY1 no` to cancel.

## What's running

| Project | What's running | Waiting for |
|---|---|---|
| Shop | Price cuts | the session |
"""


def board(*statuses: str) -> str:
    """A board with one row per status."""
    return HEAD + "".join(f"| P{i} | r | f | {s} |\n" for i, s in enumerate(statuses))


def test_status_without_who_we_wait_for_is_a_defect() -> None:
    assert any("who we are waiting for" in d for d in board_defects(board("in flight · msg 27/09 19:49")))


def test_status_with_who_we_wait_for_passes() -> None:
    assert board_defects(board("Waiting CEO: UR1 · msg 26/09 13:04", "nothing in flight")) == []


def test_cell_over_the_cap_is_a_defect() -> None:
    assert any("cap 400" in d for d in board_defects(board("nothing in flight " + "x" * 400)))


def test_well_formed_desk_passes() -> None:
    assert desk_defects(DESK_OK, TODAY) == []


def test_missing_section() -> None:
    desk = DESK_OK.replace("## Do\n", "## Other\n")
    assert any("section «do» is missing" in d for d in desk_defects(desk, TODAY))


def test_red_item_without_if_no_answer() -> None:
    desk = DESK_OK.replace(" If no answer: nothing happens (31/10).", "")
    assert any("If no answer" in d for d in desk_defects(desk, TODAY))


def test_red_item_without_recommendation_or_link() -> None:
    desk = DESK_OK.replace("Recommend A.", "I'd say A.").replace(" http://localhost:8000/tr1.html.", "")
    found = desk_defects(desk, TODAY)
    assert any("Recommend" in d for d in found) and any("link" in d for d in found)


def test_a_file_path_is_not_a_link() -> None:
    desk = DESK_OK.replace("http://localhost:8000/tr1.html", "`invoicing/TODO.md`")
    assert any("link" in d for d in desk_defects(desk, TODAY))


def test_red_item_too_long() -> None:
    desk = DESK_OK.replace("Write `TR1 A` or `TR1 B`.", "Write `TR1 A` or `TR1 B`. " + "x" * 600)
    assert any("cap 600" in d for d in desk_defects(desk, TODAY))


def test_wrong_letters_for_red_and_yellow() -> None:
    desk = DESK_OK.replace("`TR1` **Invoicing", "`TY1` **Invoicing").replace("`GY1` **Research", "`GR1` **Research")
    found = desk_defects(desk, TODAY)
    assert any("R code" in d for d in found) and any("Y code" in d for d in found)


def test_do_item_without_minutes() -> None:
    desk = DESK_OK.replace("Marketing · 2 min · ", "Marketing · ")
    assert any("minutes" in d for d in desk_defects(desk, TODAY))


def test_do_item_too_long_is_not_one_unit() -> None:
    desk = DESK_OK.replace("`MR1 done`.", "`MR1 done`.\n  1. " + "x" * 300 + "\n  2. " + "y" * 300)
    assert any("one unit of work" in d for d in desk_defects(desk, TODAY))


def test_yellow_expires_the_day_after_next() -> None:
    assert not any("expired" in d for d in desk_defects(DESK_OK, date(2026, 10, 7)))
    assert any("expired" in d for d in desk_defects(DESK_OK, date(2026, 10, 8)))


def test_yellow_without_date_or_on_several_lines() -> None:
    desk = DESK_OK.replace(" (06/10).", ".\n  - sub-line")
    found = desk_defects(desk, TODAY)
    assert any("date" in d for d in found) and any("single line" in d for d in found)


def test_done_inside_an_item() -> None:
    desk = DESK_OK.replace("Write `TR1 A` or `TR1 B`.", "Write `TR1 A` or `TR1 B`.\n  - **Done by X:** y")
    assert any("«Done»" in d for d in desk_defects(desk, TODAY))


def test_item_without_a_code() -> None:
    desk = DESK_OK.replace("- `MR1` **Marketing", "- **Marketing")
    assert any("without a code" in d for d in desk_defects(desk, TODAY))


def test_to_clean_without_percentage() -> None:
    desk = DESK_OK.replace("(82%, `/clear`: TODO up to date, nothing in flight)", "(`/clear`)")
    assert any("To clean" in d for d in desk_defects(desk, TODAY))
