"""Parsers must refuse oversized session files before reading them.

``parse_hermes_log`` used ``Path.read_text()`` and ``parse_codex_json`` used
``json.load`` with no size check, so a multi-GB log could OOM the process.
The contract pinned here: every public parser (and auto-detection) rejects a
file over the configured limit with ``FileTooLargeError`` *before* loading
its body, files under the limit still parse, and Hermes walks line by line so
a large-but-allowed log never has to sit in memory whole.
"""

import json
import re

import pytest
from click.testing import CliRunner

from context_bridge.cli import cli
from context_bridge.parsers import (
    FileTooLargeError,
    auto_detect_parser,
    parse_claude_code_jsonl,
    parse_codex_json,
    parse_hermes_log,
    parse_opencode_jsonl,
)

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _plain(text: str) -> str:
    """Strip Rich ANSI codes and collapse wrapping whitespace for asserts."""
    return re.sub(r"\s+", " ", _ANSI.sub("", text))


CLAUDE_EVENT = {
    "type": "assistant",
    "timestamp": "2026-01-01T00:00:00Z",
    "session_id": "s1",
    "cwd": "/test",
    "message": {"role": "assistant", "content": "Use SQLite for the index."},
}

CODEX_DOC = {
    "session_id": "codex-1",
    "project_path": "/test",
    "timestamp": "2026-01-01T00:00:00Z",
    "entries": [{"content": "Pin the dependency."}],
}

OPENCODE_EVENT = {
    "message": {"role": "assistant", "content": "Use SQLite for the index."}
}


@pytest.mark.parametrize(
    "writer,parser",
    [
        (
            lambda f: f.write_text(json.dumps(CLAUDE_EVENT) + "\n"),
            parse_claude_code_jsonl,
        ),
        (
            lambda f: f.write_text(json.dumps(CODEX_DOC)),
            parse_codex_json,
        ),
        (
            lambda f: f.write_text(json.dumps(OPENCODE_EVENT) + "\n"),
            parse_opencode_jsonl,
        ),
        (
            lambda f: f.write_text("## Session: s1\nbody line\n"),
            parse_hermes_log,
        ),
    ],
)
def test_parser_rejects_file_over_limit(tmp_path, writer, parser):
    path = tmp_path / "session.dat"
    writer(path)
    assert path.stat().st_size > 1

    with pytest.raises(FileTooLargeError, match="exceeds the 1 byte limit"):
        list(parser(path, max_file_size=1))


def test_parser_accepts_file_under_limit(tmp_path):
    path = tmp_path / "session.jsonl"
    path.write_text(json.dumps(CLAUDE_EVENT) + "\n")

    sessions = list(parse_claude_code_jsonl(path, max_file_size=10_000))

    assert len(sessions) == 1
    assert "SQLite" in sessions[0].content


def test_auto_detect_rejects_oversized_before_routing(tmp_path):
    path = tmp_path / "session.jsonl"
    path.write_text(json.dumps(CLAUDE_EVENT) + "\n")

    with pytest.raises(FileTooLargeError):
        auto_detect_parser(path, max_file_size=1)


def test_hermes_streams_multiple_sessions_line_by_line(tmp_path):
    path = tmp_path / "notes.md"
    path.write_text(
        "preamble ignored\n## Session: first\nalpha\n## Session: second\nbeta\n"
    )

    sessions = list(parse_hermes_log(path))

    assert [s.session_id for s in sessions] == ["first", "second"]
    assert sessions[0].content == "alpha\n"
    assert sessions[1].content == "beta\n"


def test_hermes_without_headers_yields_whole_file(tmp_path):
    path = tmp_path / "notes.md"
    path.write_text("just a note about SQLite\n")

    sessions = list(parse_hermes_log(path))

    assert len(sessions) == 1
    assert sessions[0].content == "just a note about SQLite\n"


def test_index_cli_reports_oversized_file(tmp_path):
    session = tmp_path / "session.jsonl"
    session.write_text(json.dumps(CLAUDE_EVENT) + "\n")
    db = tmp_path / "index.db"

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--db",
            str(db),
            "index",
            str(tmp_path),
            "--max-file-size",
            "1",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    out = _plain(result.output)
    assert "exceeds the 1 byte limit" in out
    assert "Indexed 0 sessions" in out
