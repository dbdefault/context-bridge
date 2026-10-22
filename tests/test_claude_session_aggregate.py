"""Regression tests for Claude Code multi-event session aggregation (#112).

Claude Code writes one JSONL file per conversation. Every event shares the
same ``session_id``. The parser used to yield one ``Session`` per event, so
``INSERT OR IGNORE`` on ``UNIQUE(session_id)`` kept only the first event and
``index`` still reported a success count. Events are now joined into one
``Session`` per ``session_id``, and a successful insert marks ``indexed``.
"""

import json
import re
import sqlite3

from click.testing import CliRunner

from context_bridge.cli import cli
from context_bridge.parsers import parse_claude_code_jsonl
from context_bridge.store import MemoryStore


def _plain(text: str) -> str:
    """Strip ANSI color codes so Rich CliRunner output is searchable."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _event(i: int, session_id: str = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"):
    return {
        "type": "assistant" if i % 2 else "user",
        "session_id": session_id,
        "cwd": "/tmp/cbrepro",
        "timestamp": f"2025-01-0{i + 1}T10:00:00.000Z",
        "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": f"event {i} secretword tok{i}"}],
        },
    }


def test_parser_aggregates_six_events_into_one_session(tmp_path):
    f = tmp_path / "s.jsonl"
    f.write_text("\n".join(json.dumps(_event(i)) for i in range(6)) + "\n")

    sessions = list(parse_claude_code_jsonl(f))
    assert len(sessions) == 1
    assert sessions[0].session_id == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    for i in range(6):
        assert f"event {i} secretword tok{i}" in sessions[0].content


def test_index_persists_all_event_text_and_marks_indexed(tmp_path):
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "s.jsonl").write_text(
        "\n".join(json.dumps(_event(i)) for i in range(6)) + "\n"
    )
    db = tmp_path / "d1.db"

    runner = CliRunner()
    result = runner.invoke(cli, ["--db", str(db), "index", str(logs)])
    assert result.exit_code == 0, result.output
    assert "Indexed 1 sessions" in _plain(result.output)

    store = MemoryStore(db)
    assert store.get_stats()["total_sessions"] == 1
    assert store.is_indexed("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    store.close()

    conn = sqlite3.connect(str(db))
    row = conn.execute("SELECT content FROM sessions").fetchone()
    assert row is not None
    for i in range(6):
        assert f"event {i} secretword tok{i}" in row[0]
    memories = conn.execute("SELECT content FROM memories").fetchall()
    assert len(memories) == 1
    for i in range(6):
        assert f"event {i} secretword tok{i}" in memories[0][0]
    conn.close()

    # Re-run must stay honest: still one session, still report 0 new inserts.
    result2 = runner.invoke(cli, ["--db", str(db), "index", str(logs)])
    assert result2.exit_code == 0, result2.output
    assert "Indexed 0 sessions" in _plain(result2.output)
    store = MemoryStore(db)
    assert store.get_stats()["total_sessions"] == 1
    store.close()


def test_distinct_session_ids_in_one_file_stay_separate(tmp_path):
    f = tmp_path / "mixed.jsonl"
    lines = [json.dumps(_event(i, "sid-a")) for i in range(2)]
    lines += [json.dumps(_event(i, "sid-b")) for i in range(2)]
    f.write_text("\n".join(lines) + "\n")

    sessions = list(parse_claude_code_jsonl(f))
    assert {s.session_id for s in sessions} == {"sid-a", "sid-b"}
    assert len(sessions) == 2
