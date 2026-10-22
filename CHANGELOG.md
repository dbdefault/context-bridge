# Changelog

## [Unreleased]

### Fixed
- **Parsers reject oversized session files before reading them.**
  `parse_hermes_log` and `parse_codex_json` used to load the whole file with
  no size check, so a multi-GB log could OOM the process. Every public parser
  and `auto_detect_parser` now enforce a configurable limit (default
  100 MiB) and raise `FileTooLargeError` with the path and sizes.
  `context-bridge index --max-file-size` exposes the same guard, and oversized
  files are reported instead of being swallowed by the generic parse
  `except`. Hermes logs are walked line by line so a large-but-allowed file
  never has to sit in memory whole.

## [0.3.0] - 2026-10-08

### Fixed
- **`context-bridge index` no longer picks a parser from a substring of the
  absolute path.** `auto_detect_parser` tested `"hermes" in str(parent)`, so a
  log at `/srv/hermes-data/plain.jsonl` was parsed as a Hermes markdown log, no
  sessions were found in it, and the run reported success with the session
  silently unindexed — the same failure mode #117 removed for corrupt lines,
  one level up. Routing now follows the markers inside the file (`type` for
  Claude Code, `entries` for Codex, `message` for OpenCode), and a JSON file
  carrying no marker raises `ParserNotDetectedError` instead of falling through
  to a default parser. `index` names every file it could not route.

  Behaviour change: a marker-less JSON file used to be handed to the Claude Code
  parser by default and index nothing; it is now reported as unroutable, and a
  caller that wants it parsed can call the parser directly.
- **Corrupt JSONL lines are now reported instead of dropped silently.** The
  parsers log a warning with the file path, line number, and the offending
  content, so a partially-written session file no longer loses its tail without
  any indication.
- **Non-dict top-level JSON elements are skipped gracefully.** A JSONL file
  containing a bare string, number, or array at the top level no longer crashes
  the parser; the element is skipped and the rest of the file is processed.
- **`session_id` collisions are fixed by using the resolved file path.** Two
  session files with the same basename in different directories no longer
  overwrite each other in the index; the resolved absolute path is used as the
  session identifier.
- **`index` now stores all events from each session file.** Previously only a
  subset of events was persisted; the full event list is now written to the
  index.
- **Memories are populated from sessions during `index`.** The `index` command
  now extracts and stores memories from session files in a single pass, so a
  separate `populate` step is no longer required.

### Changed
- **CI: `actions/checkout` and `actions/setup-python` bumped to v7.**
- **CI: publish workflow now supports manual dispatch** so a failed
  trusted-publish run can be retried without pushing a new commit.
- **Added Python 3.13 and 3.14 classifiers.**
- **Added Code of Conduct and Security pointers to CONTRIBUTING.md.**

## [0.2.0] - 2026-10-02

### Changed
- **BREAKING (install name only): the distribution is renamed to
  `context-bridge-py`.** The bare `context-bridge` name on PyPI belongs to
  Ganzzi/context_bridge, an unrelated RAG documentation crawler, so this
  project could never be published under its own name and a documented
  `pip install context-bridge` silently installed that other author's
  package. The import package (`context_bridge`) and the console script
  (`context-bridge`) are unchanged.

## [0.1.0] - 2026-09-26

### Added
- Initial release