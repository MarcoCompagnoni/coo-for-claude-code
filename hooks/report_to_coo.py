"""Stop hook for project sessions: nothing left in the chat after the report to the COO.

The problem it solves: a project session sends its report to the COO, then keeps writing in its own chat:
a proposal, a question, a result. The CEO never opens that chat, so whatever was written there is lost.

The rule: the report to the COO is the last thing of the turn and it contains everything.

No model is called. The hook blocks the end of the turn only when all three hold:
- the turn was started by a message from the COO (not by the CEO, not by another session);
- during the turn the session already sent a message to the COO;
- after that, the session wrote more than a short closing line in the chat.

When it blocks, the session is told to send that text to the COO too. On the second attempt
(`stop_hook_active`) it always lets the turn end, so it can never loop.

Configuration: `coo.config.json` at the repository root, or the path in the COO_CONFIG environment
variable. Keys: `coo_session_id`, `coo_names`, `report_threshold_chars`.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

WINDOWS: tuple[int, ...] = (4 << 20, 32 << 20, 256 << 20)  # bytes read from the end: transcripts grow to hundreds of MB
UNDECIDED = -1


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
COO_ID: str = CONFIG.get("coo_session_id", "")
COO_NAMES: tuple[str, ...] = tuple(CONFIG.get("coo_names", ["COO"]))
COO_MARK = f'<cross-session-message from="{COO_ID}"'
THRESHOLD: int = int(CONFIG.get("report_threshold_chars", 300))

INSTRUCTION = (
    "You wrote in the chat after your report to the COO. Rule: the report to the COO is the last thing of the "
    "turn and it contains everything, because the CEO only reads what goes through the COO. If the text you just "
    "wrote contains proposals, questions or results that are not in the report, send them to the COO now with "
    f"SendMessage (to: {COO_ID or 'the COO'}) and close with a single line. If it does not, close with a single line."
)


def text_of(content: Any) -> str:
    """Returns the text of a message, whether a string or a list of blocks; tool results are skipped.

    Args:
        content: the `content` field of a transcript message.

    Returns:
        The concatenated text blocks.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""


def only_tool_results(content: Any) -> bool:
    """Tells whether a user message carries nothing but tool results.

    Args:
        content: the `content` field of a transcript message.

    Returns:
        True if every block is a tool result.
    """
    return isinstance(content, list) and bool(content) and all(
        isinstance(b, dict) and b.get("type") == "tool_result" for b in content
    )


def tail_lines(path: str, window: int) -> tuple[list[dict[str, Any]], bool]:
    """Parses the last `window` bytes of a transcript.

    Args:
        path: the transcript (.jsonl) path.
        window: how many bytes to read from the end.

    Returns:
        The parsed lines, and whether they cover the whole file.
    """
    with open(path, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        start = max(0, size - window)
        f.seek(start)
        raw = f.read()
    chunks = raw.split(b"\n")
    if start > 0:
        chunks = chunks[1:]  # the first one is cut in half
    lines: list[dict[str, Any]] = []
    for chunk in chunks:
        try:
            lines.append(json.loads(chunk.decode("utf-8")))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
    return lines, start == 0


def turn_origin(lines: list[dict[str, Any]], whole_file: bool = True) -> int | None:
    """Finds the message that opened the current turn, if it came from the COO.

    Walks backwards. Tool results, background-task notifications and other system messages do not open
    a turn and are skipped. The first real message decides.

    Args:
        lines: the parsed transcript lines.
        whole_file: whether `lines` covers the whole transcript.

    Returns:
        The index of the COO message; None if the turn was opened by someone else; UNDECIDED if the
        window ends before the opening message is found.
    """
    for index in range(len(lines) - 1, -1, -1):
        entry = lines[index]
        if entry.get("type") != "user":
            continue
        content = (entry.get("message") or {}).get("content")
        if only_tool_results(content):
            continue
        text = text_of(content)
        if COO_ID and COO_MARK in text:
            return index
        if "<cross-session-message" in text:
            return None
        if entry.get("isMeta") or "<task-notification" in text or not text.strip():
            continue
        return None
    return None if whole_file else UNDECIDED


def wrote_to_coo(lines: list[dict[str, Any]], since: int) -> bool:
    """Tells whether the session sent a message to the COO after a given line.

    Args:
        lines: the parsed transcript lines.
        since: index of the line that opened the turn.

    Returns:
        True if a SendMessage to the COO appears after `since`.
    """
    targets = {COO_ID, *COO_NAMES}
    for entry in lines[since:]:
        if entry.get("type") != "assistant":
            continue
        for block in (entry.get("message") or {}).get("content") or []:
            if (
                isinstance(block, dict)
                and block.get("type") == "tool_use"
                and block.get("name") == "SendMessage"
                and str((block.get("input") or {}).get("to", "")).split(" [")[0] in targets
            ):
                return True
    return False


def should_block(data: dict[str, Any]) -> bool:
    """Decides whether the end of the turn must be blocked.

    Args:
        data: the JSON that Claude Code passes to Stop hooks.

    Returns:
        True to block and send the instruction back to the session.
    """
    if data.get("stop_hook_active") or not COO_ID:
        return False
    last = (data.get("last_assistant_message") or "").strip()
    if len(last) <= THRESHOLD:
        return False
    path = data.get("transcript_path")
    if not path:
        return False
    for window in WINDOWS:
        lines, whole = tail_lines(path, window)
        start = turn_origin(lines, whole)
        if start != UNDECIDED:
            return start is not None and wrote_to_coo(lines, start)
    return False


def main() -> int:
    """Entry point for Claude Code.

    Returns:
        2 to block the end of the turn (the instruction goes to stderr), 0 otherwise.
    """
    try:
        # Explicit UTF-8: on Windows stdin and stderr would otherwise be cp1252.
        data = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        block = should_block(data)
    except Exception:  # a bug in the check must never stop a session
        return 0
    if block:
        sys.stderr.buffer.write(INSTRUCTION.encode("utf-8"))
        sys.stderr.flush()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
