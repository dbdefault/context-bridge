# context-bridge — session memory for AI coding agents

**Index. Retrieve.** A local-first context layer for the agents you already use.

[![CI](https://github.com/yunaremaia/context-bridge/actions/workflows/ci.yml/badge.svg)](https://github.com/yunaremaia/context-bridge/actions/workflows/ci.yml) [![License](https://img.shields.io/github/license/yunaremaia/context-bridge)](https://github.com/yunaremaia/context-bridge/blob/main/LICENSE) [![Stars](https://img.shields.io/github/stars/yunaremaia/context-bridge)](https://github.com/yunaremaia/context-bridge) [![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/) [![Release](https://img.shields.io/github/v/release/yunaremaia/context-bridge)](https://github.com/yunaremaia/context-bridge/releases/latest)

---

## The problem

Every AI coding agent forgets between sessions. You re-explain the project, restate architecture decisions, and re-teach preferences every time you start a new one. Notes scattered across sessions are hard to search.

## What it does

`context-bridge` reads the session logs your agent already writes, indexes them into a local SQLite database, and retrieves the relevant context when you start a new session.

It is a **manual, offline** tool:

- you run `index` yourself, when you want — nothing is captured automatically;
- it never phones home — no cloud, no API keys, no vendor lock-in;
- the database stays in your home directory.

## Supported log formats

| Agent | Format | Recognised by |
|---|---|---|
| Claude Code | `.jsonl`, one JSON object per line | `type` is `user` or `assistant` |
| Codex | `.json`, one document with an `entries` list | `entries` is a list |
| OpenCode | `.jsonl`, one JSON object per line | a top-level `message` object |
| Hermes | markdown or plain text | any non-`.json`/`.jsonl` suffix |

Format detection reads the file's **content**, not its path: living under `.hermes/` does not make a file a Hermes log. A file whose format cannot be recognised raises an error instead of being silently read as the wrong format.

## Limits

- **Per-event cap.** Each event's text is truncated to **10 000 characters** before it is stored. A very long response is indexed only in part.
- **Only text is indexed.** Non-text blocks — tool calls, images — are dropped.
- **Unparsable lines are skipped, with a warning.** A half-written trailing line in a `.jsonl` file is normal for an agent that was killed; the good lines are still indexed and the bad one is named.
- **Indexing is not automatic.** Run `context-bridge index <path>` when you want your sessions searchable.

## Quick start

_Get started in 5 minutes_:

```bash
pip install git+https://github.com/yunaremaia/context-bridge.git

# Initialize in your project
context-bridge init

# Index existing agent sessions (a Claude Code project)
context-bridge index ~/.claude/projects/

# Query memory
context-bridge recall "How did we handle authentication?"

# Print the retrieved context for a new session
context-bridge inject --agent claude
```

> **Not yet on PyPI.** Install from git with the line above. The command you run
> is `context-bridge`; the distribution name is `context-bridge-py`, because the
> short `context-bridge` name on PyPI belongs to an unrelated project by another
> author and is not used here.

## A bounded example

```bash
# Index one Claude Code project's logs
context-bridge index ~/.claude/projects/-home-you-code

# Ask about a decision made in an earlier session
context-bridge recall "why did we pin the dependency"

# Print the retrieved context for a new Claude Code session
context-bridge inject --agent claude
```

## Architecture

```
~/.context-bridge/
├── sessions/           # Captured session transcripts
├── index.db            # SQLite FTS + metadata
├── memories/           # Consolidated memories
└── config.yaml         # Per-project config
```

## Related tools

- **[driftcheck](https://github.com/yunaremaia/driftcheck)** — detect version drift between docs and toolchain files
- **[mcp-guard](https://github.com/yunaremaia/mcp-guard)** — audit MCP servers for unsafe permissions
- **[memwatch](https://github.com/yunaremaia/memwatch)** — health-check and prune agent memory stores
- **[agent-workspace](https://github.com/yunaremaia/agent-workspace)** — isolated workspaces per AI agent session

Part of a family of focused, single-purpose developer tools — each one does one thing
and does it well.

## Sponsoring

`context-bridge` is MIT licensed and free to use. If it earns a permanent place in your setup, you can support continued maintenance via GitHub Sponsors or by sending SOL to the project treasury wallet:

```text
Eeztv1nCYUt1fwGWpzKC948gaWfjejYCAuLtUMgzDWbW
```

Funding platforms are configured in [`.github/FUNDING.yml`](.github/FUNDING.yml).

If this tool is useful to you, a star helps other people find it.

## License

MIT
