"""Stop hook for sessions that work on their own: the turn does not end while the queue has open items.

The problem it solves: a session finishes a task, or hits something that needs the CEO, and stops. It sits
idle until someone writes to it, even when its TODO has plenty of work it could do alone.

No model is called. The hook reads the session's TODO.md, section «## Autonomous queue» (configurable): if
there are «- [ ]» items without the waiting mark, it blocks the end of the turn and hands the session the
first open item.

It lets the turn end when:
- the file .claude/queue_paused exists (the session creates it when told «pause», removes it on «resume»);
- the queue is empty, or every item is waiting for someone;
- after N re-runs in a row without a new commit. At run N the session is told to report what is blocking
  it; at the next one it may stop. This is the guard against spinning in place.
The count goes back to zero at every new commit, and after a pause longer than the reset window (a new turn).

Configuration keys (coo.config.json): `queue_section`, `queue_waiting_mark`,
`queue_max_runs_without_commit`, `queue_reset_minutes`.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ITEM_LENGTH = 300


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


CONFIG = load_config()
SECTION: str = CONFIG.get("queue_section", "## Autonomous queue")
WAITING: str = CONFIG.get("queue_waiting_mark", "[waiting]")
MAX_WITHOUT_COMMIT: int = int(CONFIG.get("queue_max_runs_without_commit", 3))
RESET_MINUTES: int = int(CONFIG.get("queue_reset_minutes", 30))

INSTRUCTION = (
    "Autonomous queue: the next open item in your TODO is «{item}». Rule: you do not stop while the queue has "
    "items. Do it, verify it, commit, tick it in the TODO, then move to the next one without ending the turn. If "
    f"an item needs the CEO or a third party, mark it {WAITING} with who it is waiting for, send the question to "
    "the COO in a single message and move on. The red rules do not change: no accounts, spending, publishing, "
    "messages to third parties or heavy jobs on the machine."
)
INSTRUCTION_STUCK = (
    "Autonomous queue: {n} re-runs in a row without a new commit. If you are blocked, tell the COO in a single "
    f"message what is stopping you and on which item, mark the item {WAITING}, then stop. If you are working on a "
    "long item, commit what you have so far and keep going."
)


def open_items(todo: Path) -> list[str]:
    """Returns the top-level open items of the queue section, minus the ones waiting for someone.

    Args:
        todo: path of the session's TODO.md.

    Returns:
        The text of each open item, in file order.
    """
    try:
        text = todo.read_text(encoding="utf-8")
    except OSError:
        return []
    inside, items = False, []
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line.strip() == SECTION
            continue
        if inside and line.startswith("- [ ] ") and WAITING not in line:
            items.append(line[6:].strip())
    return items


def head(folder: Path) -> str:
    """Returns the hash of the last commit.

    Args:
        folder: the session's working folder.

    Returns:
        The commit hash, or an empty string if the folder is not a git repository.
    """
    try:
        result = subprocess.run(["git", "-C", str(folder), "rev-parse", "HEAD"], capture_output=True, text=True,
                                timeout=5)
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def decide(data: dict[str, Any], now: dt.datetime | None = None) -> dict[str, str] | None:
    """Decides whether to block the end of the turn.

    Args:
        data: the JSON that Claude Code passes to Stop hooks (only `cwd` is used).
        now: the current time, for tests.

    Returns:
        The JSON to print to block the turn, or None to let it end.
    """
    now = now or dt.datetime.now()
    folder = Path(data.get("cwd") or ".")
    if (folder / ".claude" / "queue_paused").exists():
        return None
    items = open_items(folder / "TODO.md")
    if not items:
        return None
    state_file = folder / ".claude" / "queue_state.json"
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    current = head(folder)
    last = state.get("when")
    stale = not last or now - dt.datetime.fromisoformat(last) > dt.timedelta(minutes=RESET_MINUTES)
    runs = 0 if stale or current != state.get("head") else int(state.get("runs", 0)) + 1
    new_state = {"head": current, "runs": runs, "when": now.isoformat(timespec="seconds")}
    if runs > MAX_WITHOUT_COMMIT:
        new_state["runs"] = 0
        answer = None
    elif runs == MAX_WITHOUT_COMMIT:
        answer = {"decision": "block", "reason": INSTRUCTION_STUCK.format(n=runs)}
    else:
        answer = {"decision": "block", "reason": INSTRUCTION.format(item=items[0][:ITEM_LENGTH])}
    try:
        state_file.parent.mkdir(exist_ok=True)
        state_file.write_text(json.dumps(new_state), encoding="utf-8")
    except OSError:
        pass
    return answer


def main() -> int:
    """Entry point for Claude Code.

    Returns:
        Always 0; blocking happens through the JSON printed on stdout.
    """
    try:
        data = json.load(sys.stdin)
        answer = decide(data)
    except Exception:  # a bug in the hook must never stop a session
        return 0
    if answer:
        sys.stdout.reconfigure(encoding="utf-8")
        print(json.dumps(answer, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
