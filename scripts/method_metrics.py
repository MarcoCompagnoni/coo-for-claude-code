"""Measures how well the COO method works, from the COO session's own transcripts. Read only.

Every item the COO raises to the CEO carries a code (`<letter><R|Y><n>`). When the CEO answers, the answer
mentions the code. Pairing the two gives four numbers that say whether the desk is doing its job:

| Measure | Threshold | What it means when it is over |
|---|---|---|
| Rounds per day (an item raised and answered) | under 20 | the CEO is being asked too much |
| Answers that are just «ok» | under 20% | those items could have been yellow: the COO should decide them |
| Answers that are a question | under 15% | items arrive unfinished or not self-contained |
| Rounds that took more than 24 hours | under 5% | items sit on the desk |

It also counts friction (messages of frustration, with a configurable word list), the COO's messages to the
sessions, desk writes and compactions.

Usage:
    python scripts/method_metrics.py list                      who each transcript in the folder is
    python scripts/method_metrics.py analyze PREFIX [PREFIX…]  the COO transcripts, by file-name prefix
    python scripts/method_metrics.py analyze PREFIX --dump DIR also writes the CEO's answers as CSV in DIR

Transcripts are read from `transcripts_dir` in coo.config.json. Lines repeated after a compaction (same
uuid) are counted once. The word lists can be overridden in the configuration (`approve_words`,
`negate_words`, `takeover_words`, `friction_words`), as regular-expression alternations.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_board import load_config  # noqa: E402

CONFIG = load_config()
FOLDER = Path(CONFIG.get("transcripts_dir", "~/.claude/projects")).expanduser()
DESK_NAME = Path(CONFIG.get("desk", "CEO_DESK.md")).name
CODE = re.compile(r"\b([A-Z]{1,2}[RY]\d{1,2})\b")


def _words(key: str, default: str) -> re.Pattern[str]:
    """Builds a case-insensitive whole-word pattern from the configuration or a default.

    Args:
        key: the configuration key.
        default: the alternation to use when the key is missing.

    Returns:
        The compiled pattern.
    """
    return re.compile(r"\b(" + CONFIG.get(key, default) + r")\b", re.I)


APPROVE = _words("approve_words", r"ok|okay|go|yes|done|proceed|approved?|agreed?|confirmed?|fine|right|sure|sent|created")
TAKEOVER = _words("takeover_words", r"i'll do it|i will do it|leave it to me|i'll handle it")
NEGATE = _words("negate_words", r"no|not|instead|wait|wrong|error|stop|cancel")
FRICTION = _words("friction_words", r"i don't understand|what do you mean|why not|still|again|blocked|stuck")


def user_text(message: dict[str, Any]) -> str | None:
    """Returns what the CEO wrote, skipping tool results and system messages.

    Args:
        message: the `message` field of a transcript line.

    Returns:
        The text, or None if the line is not something the CEO typed.
    """
    content = message.get("content")
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
        if not parts:
            return None
        text = "\n".join(parts)
    else:
        return None
    text = text.strip()
    if not text or text[0] in "<[" or text.startswith("This session is being continued"):
        return None
    if any(mark in text for mark in ("<local-command-caveat>", "<command-name>", "<cross-session", "<system-reminder>")):
        return None
    return text


def local_time(timestamp: str) -> datetime:
    """Converts a transcript timestamp to naive local time.

    Args:
        timestamp: ISO timestamp, possibly ending in Z.

    Returns:
        The local time without timezone.
    """
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone().replace(tzinfo=None)


def read(path: Path, seen: set[Any]) -> Iterator[dict[str, Any]]:
    """Yields each transcript line once: after a compaction the file repeats the kept messages.

    Args:
        path: the transcript.
        seen: keys already yielded, shared across files.

    Yields:
        The parsed lines.
    """
    with open(path, encoding="utf-8", errors="replace") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                entry = json.loads(raw)
            except json.JSONDecodeError:
                continue
            key = entry.get("uuid") or (entry.get("timestamp"), entry.get("type"),
                                        json.dumps(entry.get("message"), sort_keys=True)[:400])
            if key in seen:
                continue
            seen.add(key)
            yield entry


def classify(segment: str) -> str:
    """Classifies the part of an answer that follows a code.

    Args:
        segment: the text between a code and the next one.

    Returns:
        One of «approve», «takeover», «question», «correct», «other».
    """
    segment = segment.strip(" :,.;-")
    if not segment:
        return "approve"
    if TAKEOVER.search(segment) and len(segment) < 60:
        return "takeover"
    if "?" in segment:
        return "question"
    if NEGATE.search(segment) and not APPROVE.search(segment[:25]):
        return "correct"
    if APPROVE.search(segment[:40]):
        return "approve"
    return "other"


def segments(text: str) -> list[tuple[str, str]]:
    """Splits a message into (code, text up to the next code).

    Args:
        text: a message from the CEO.

    Returns:
        One pair per code found.
    """
    found = list(CODE.finditer(text))
    out = []
    for i, match in enumerate(found):
        end = found[i + 1].start() if i + 1 < len(found) else len(text)
        out.append((match.group(1), text[match.end():end]))
    return out


def list_transcripts() -> None:
    """Prints one line per transcript in the folder: time span, messages, first words."""
    for path in sorted(FOLDER.glob("*.jsonl")):
        first = last = None
        typed = sends = 0
        opening = ""
        for entry in read(path, set()):
            if entry.get("timestamp"):
                moment = local_time(entry["timestamp"])
                first = first or moment
                last = moment
            message = entry.get("message") or {}
            if entry.get("type") == "user" and not entry.get("isMeta"):
                text = user_text(message)
                if text:
                    typed += 1
                    opening = opening or text[:80].replace("\n", " ")
            elif entry.get("type") == "assistant":
                for block in message.get("content") or []:
                    if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "SendMessage":
                        sends += 1
        if first:
            print(f"{path.name[:8]} {first:%d/%m %H:%M}→{last:%d/%m %H:%M} typed={typed} sends={sends} | {opening}")


def analyze(prefixes: list[str], dump: Path | None = None) -> dict[str, float]:
    """Computes the method measures over the given transcripts and prints them.

    Args:
        prefixes: file-name prefixes of the COO transcripts.
        dump: optional folder where the CEO's answers are written as CSV.

    Returns:
        The four headline measures.
    """
    per_day: dict[str, Counter[str]] = defaultdict(Counter)
    answers: list[tuple[datetime, str, str, str]] = []
    births: dict[str, list[datetime]] = defaultdict(list)
    seen: set[Any] = set()
    for prefix in prefixes:
        for path in sorted(FOLDER.glob(prefix + "*.jsonl")):
            for entry in read(path, seen):
                if not entry.get("timestamp"):
                    continue
                moment = local_time(entry["timestamp"])
                day = moment.strftime("%d/%m")
                message = entry.get("message") or {}
                if entry.get("type") == "user" and not entry.get("isMeta"):
                    content = message.get("content")
                    if isinstance(content, str) and content.startswith("This session is being continued"):
                        per_day[day]["compactions"] += 1
                    text = user_text(message)
                    if not text:
                        continue
                    per_day[day]["ceo_messages"] += 1
                    for code, segment in segments(text):
                        kind = classify(segment)
                        answers.append((moment, code, kind, segment.strip()[:110].replace("\n", " ")))
                        per_day[day]["answer_" + kind] += 1
                    if FRICTION.search(text):
                        per_day[day]["friction"] += 1
                elif entry.get("type") == "assistant":
                    coo_text = ""
                    for block in message.get("content") or []:
                        if not isinstance(block, dict):
                            continue
                        if block.get("type") == "text":
                            coo_text += block.get("text", "")
                            per_day[day]["coo_chat_kchar"] += len(block.get("text", "")) / 1000
                        elif block.get("type") == "tool_use":
                            payload = json.dumps(block.get("input", {}), ensure_ascii=False)
                            if block.get("name") == "SendMessage":
                                per_day[day]["messages_to_sessions"] += 1
                            if DESK_NAME in payload:
                                per_day[day]["desk_writes"] += 1
                                coo_text += payload
                    for code in set(CODE.findall(coo_text)):
                        births[code].append(moment)
    last_answer: dict[str, datetime] = {}
    latencies: list[float] = []
    rounds_per_day: Counter[str] = Counter()
    for moment, code, _, _ in sorted(answers):
        previous = last_answer.get(code)
        candidates = [b for b in births.get(code, []) if b < moment and (previous is None or b > previous)]
        if candidates:
            born = min(candidates)
            latencies.append((moment - born).total_seconds() / 3600)
            rounds_per_day[born.strftime("%d/%m")] += 1
        last_answer[code] = moment
    columns = ["ceo_messages", "answer_approve", "answer_question", "answer_correct", "answer_other", "friction",
               "messages_to_sessions", "desk_writes", "compactions"]
    print("day    rounds " + " ".join(f"{c[:12]:>12}" for c in columns))
    for day in sorted(per_day, key=lambda d: (d[3:], d[:2])):
        print(f"{day:6} {rounds_per_day[day]:>6} " + " ".join(f"{per_day[day][c]:>12.0f}" for c in columns))
    days = max(len(per_day), 1)
    total = max(len(answers), 1)
    kinds = Counter(a[2] for a in answers)
    result = {
        "rounds_per_day": sum(rounds_per_day.values()) / days,
        "share_ok": kinds["approve"] / total,
        "share_questions": kinds["question"] / total,
        "share_over_24h": (sum(1 for x in latencies if x > 24) / len(latencies)) if latencies else 0.0,
    }
    friction = sum(per_day[d]["friction"] for d in per_day) / days
    print(
        "\nRounds per day {rounds_per_day:.0f} (<20) · ok {share_ok:.0%} (<20%) · questions {share_questions:.0%} "
        "(<15%) · over 24h {share_over_24h:.0%} (<5%)".format(**result) + f" · friction per day {friction:.1f}"
    )
    if dump:
        dump.mkdir(parents=True, exist_ok=True)
        with open(dump / "ceo_answers.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["when", "code", "kind", "text"])
            for moment, code, kind, body in sorted(answers):
                writer.writerow([moment.strftime("%d/%m %H:%M"), code, kind, body])
        print("CSV:", dump / "ceo_answers.csv")
    return result


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] not in ("list", "analyze"):
        print(__doc__)
        sys.exit(2)
    if args[0] == "list":
        list_transcripts()
    else:
        out = None
        if "--dump" in args:
            i = args.index("--dump")
            out = Path(args[i + 1])
            args = args[:i] + args[i + 2:]
        analyze(args[1:], out)
