"""Checks the shape of the COO board and of the CEO desk. Run it before every commit of the board.

Board: every row of the table has four columns, every cell stays under a character cap (the board says
the state, not the history) and the last column says who is being waited for: «waiting session: …»,
«waiting CEO: …» or «nothing in flight».

Desk: the sections «Decide», «Do», «Decided by COO» and «What's running», in this order. Every item has a
code `<project letter><R|Y><n>`: R for the first two sections (they wait for the CEO), Y for «Decided by
COO» (yellow: decided by the COO, the CEO can cancel it).
- A red item in «Decide» stays under 600 characters, says «Recommend …», says «If no answer: …» and has an
  http link to a published page, never a file path.
- An item in «Do» says the minutes, stays under 600 characters and is one self-contained unit of work,
  never a sequence with waits in the middle.
- A yellow item is a single line with the date «(DD/MM)» and disappears at the next day's update.
- No «Done» inside items: what is done lives in the board and in the TODOs.
- The optional «To clean» line gives, for each session, the context percentage and /clear or /compact.

Exits with 1 and the list of defects if something is off.

Usage:
    python scripts/check_board.py [BOARD.md] [CEO_DESK.md]
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path
from typing import Any

CODE = re.compile(r"`([A-Z][RY]\d+)`")
COLUMNS = 4
CAP = 400
CAP_ITEM = 600
WHO_WE_WAIT_FOR = ("waiting session", "waiting ceo", "nothing in flight")
SECTIONS = ("decide", "do", "decided by coo", "whats running")
DATE = re.compile(r"\((\d{2})/(\d{2})\)")
MINUTES = re.compile(r"\b\d+ ?(?:min|minutes|h|hours?)\b")
LINK = re.compile(r"https?://\S+")
DONE = re.compile(r"^\s+- \*{0,2}Done", re.M)
PERCENT = re.compile(r"\d{1,3} ?%")


def load_config() -> dict[str, Any]:
    """Reads the shared configuration file.

    Returns:
        The configuration, or an empty dict if the file is missing or invalid.
    """
    default = Path(__file__).resolve().parents[1] / "coo.config.json"
    path = Path(os.environ.get("COO_CONFIG", str(default)))
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def table_rows(text: str) -> Iterator[tuple[int, str | None]]:
    """Yields the rows of the board table, header and separator excluded.

    Args:
        text: the board file.

    Yields:
        (line number, row); the row is None if the table is interrupted by text outside it.
    """
    inside = False
    for number, line in enumerate(text.splitlines(), start=1):
        if line.startswith("| Project |"):
            inside = True
            continue
        if not inside:
            continue
        if not line.startswith("|"):
            if line.strip():
                yield number, None
            return
        if line.startswith("|---"):
            continue
        yield number, line


def cells_of(row: str) -> list[str]:
    """Splits a table row into trimmed cells.

    Args:
        row: a markdown table row.

    Returns:
        The cells, without the outer pipes.
    """
    return [c.strip() for c in row.strip().strip("|").split("|")]


def board_defects(text: str) -> list[str]:
    """Finds the defects of the board table.

    Args:
        text: the board file.

    Returns:
        One message per defect.
    """
    found: list[str] = []
    for number, row in table_rows(text):
        if row is None:
            found.append(f"line {number}: the table is interrupted by text outside it")
            break
        if not row.rstrip().endswith("|"):
            found.append(f"line {number}: the row does not end with «|» (line break inside a cell?)")
            continue
        cells = cells_of(row)
        if len(cells) != COLUMNS:
            found.append(f"line {number}: {len(cells)} columns instead of {COLUMNS}")
            continue
        for index, cell in enumerate(cells[1:], start=2):
            if len(cell) > CAP:
                found.append(f"line {number} ({cells[0]}), column {index}: {len(cell)} characters, cap {CAP}")
        if not any(who in cells[3].lower() for who in WHO_WE_WAIT_FOR):
            found.append(
                f"line {number} ({cells[0]}): the status does not say who we are waiting for "
                "(«waiting session: …», «waiting CEO: …» or «nothing in flight»)"
            )
    return found


def desk_sections(desk: str) -> list[tuple[str, list[str]]]:
    """Splits the desk into its «## » sections.

    Args:
        desk: the desk file.

    Returns:
        (name in lower case without emoji or punctuation, lines) for each section, in file order.
    """
    out: list[tuple[str, list[str]]] = []
    for line in desk.splitlines():
        if line.startswith("## "):
            name = re.sub(r"[^\w ]", "", line[3:]).strip().lower()
            out.append((name, []))
        elif out:
            out[-1][1].append(line)
    return out


def items(section_lines: list[str]) -> list[str]:
    """Groups top-level items («- ») with their indented sub-lines.

    Args:
        section_lines: the lines of one section.

    Returns:
        Each item as a single text.
    """
    out: list[list[str]] = []
    for line in section_lines:
        if line.startswith("- "):
            out.append([line])
        elif out and line.strip() and line[0] in " \t":
            out[-1].append(line)
    return ["\n".join(i) for i in out]


def _date_of(dd: str, mm: str, today: date) -> date:
    """Turns a DD/MM pair into a date close to today.

    Args:
        dd: day.
        mm: month.
        today: the reference date.

    Returns:
        The date, in last year if the month is well after the current one.
    """
    day, month = int(dd), int(mm)
    year = today.year - 1 if month > today.month + 1 else today.year
    try:
        return date(year, month, day)
    except ValueError:
        return today


def desk_defects(desk: str, today: date | None = None) -> list[str]:
    """Finds the shape defects of the desk.

    Args:
        desk: the desk file.
        today: the reference date, for tests.

    Returns:
        One message per defect.
    """
    today = today or date.today()
    found: list[str] = []
    sections = desk_sections(desk)
    names = [n for n, _ in sections]
    for s in SECTIONS:
        if s not in names:
            found.append(f"desk: section «{s}» is missing")
    present = [n for n in names if n in SECTIONS]
    if present != [s for s in SECTIONS if s in present]:
        found.append("desk: sections are not in the order Decide, Do, Decided by COO, What's running")
    for name, lines in sections:
        if name == "to clean":
            text = " ".join(line for line in lines if line.strip())
            if not (PERCENT.search(text) and ("/clear" in text or "/compact" in text)):
                found.append("desk «To clean»: every session with its context percentage and /clear or /compact")
            continue
        if name not in SECTIONS or name == "whats running":
            continue
        for item in items(lines):
            first = item.splitlines()[0]
            match = CODE.search(first)
            if not match:
                found.append(f"desk «{name}»: item without a code: {first[:60]}")
                continue
            code = match.group(1)
            if DONE.search(item):
                found.append(f"desk «{name}» {code}: «Done» inside the item, it belongs in the board or the TODO")
            if name == "decide":
                if code[1] != "R":
                    found.append(f"desk «Decide» {code}: a red item has an R code")
                if len(item) > CAP_ITEM:
                    found.append(f"desk «Decide» {code}: {len(item)} characters, cap {CAP_ITEM}")
                if "recommend" not in item.lower():
                    found.append(f"desk «Decide» {code}: «Recommend …» is missing")
                if "if no answer" not in item.lower():
                    found.append(f"desk «Decide» {code}: «If no answer: …» is missing")
                if not LINK.search(item):
                    found.append(f"desk «Decide» {code}: the http link is missing (a published page, not a path)")
            elif name == "do":
                if code[1] != "R":
                    found.append(f"desk «Do» {code}: an action for the CEO has an R code")
                if not MINUTES.search(item):
                    found.append(f"desk «Do» {code}: the minutes are missing")
                if len(item) > CAP_ITEM:
                    found.append(
                        f"desk «Do» {code}: {len(item)} characters, cap {CAP_ITEM}: an item is one unit of work"
                    )
            elif name == "decided by coo":
                if code[1] != "Y":
                    found.append(f"desk «Decided by COO» {code}: a yellow item has a Y code")
                if "\n" in item:
                    found.append(f"desk «Decided by COO» {code}: a yellow item is a single line")
                when = DATE.search(item)
                if not when:
                    found.append(f"desk «Decided by COO» {code}: the date (DD/MM) is missing")
                elif _date_of(when.group(1), when.group(2), today) < today - timedelta(days=1):
                    found.append(
                        f"desk «Decided by COO» {code}: from {when.group(1)}/{when.group(2)}, expired: remove it"
                    )
    return found


def main(argv: list[str]) -> int:
    """Checks the board and the desk named on the command line or in the configuration.

    Args:
        argv: command-line arguments after the script name.

    Returns:
        1 if there are defects, 0 otherwise.
    """
    config = load_config()
    board = Path(argv[0] if argv else config.get("board", "coo/BOARD.md"))
    desk = Path(argv[1] if len(argv) > 1 else config.get("desk", "coo/CEO_DESK.md"))
    found = board_defects(board.read_text(encoding="utf-8")) if board.exists() else [f"{board}: not found"]
    if desk.exists():
        found += desk_defects(desk.read_text(encoding="utf-8"))
    for defect in found:
        print(defect)
    if not found:
        print("board and desk ok")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
