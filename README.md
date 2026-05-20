# gemini-web-cli

Zero-config, cross-platform CLI for Google Gemini via browser-cookie authentication. **No API key needed.** Works on Windows, Linux, macOS, and WSL.

Uses your existing Gemini web session (Firefox/Chrome/Edge cookies) to send prompts, images, and documents — with multi-turn conversations, dynamic model selection, and token-optimized output designed for both human and AI agent consumption.

## Install

```bash
pip install gemini-webapi browser-cookie3 pillow
```

Log into [gemini.google.com](https://gemini.google.com) in Firefox (recommended — no admin needed on Windows), Chrome, or Edge.

## Quick Start

```bash
# First run (or after logout) — opens browser for login, auto-captures cookies
python gemini.py -l "Hello"

# Text prompt
python gemini.py "Explain quantum computing in 3 bullet points"

# Image analysis
python gemini.py -i chart.png "What trend does this show?"

# Document analysis
python gemini.py -f report.pdf "Summarize this"

# Multi-turn conversations
python gemini.py -c chat.json "My favorite color is blue."
python gemini.py -c chat.json "What color did I say?"

# Pipe from stdin
echo "What is 2+2?" | python gemini.py
```

## Features

| Feature | Flag |
|---|---|
| Text prompts | positional args, `-p`, or stdin |
| Image attachments | `-i FILE` (repeatable) |
| Document attachments | `-f FILE` (repeatable) |
| Multi-turn conversations | `-c FILE`, `--new` |
| Model selection | `-m flash/pro/thinking` |
| Thinking level | `--thinking standard/plus/extended` |
| Dynamic model discovery | `--list-models` |
| JSON output | `--json` |
| File output (agent-optimized) | `-o FILE` |
| Concise mode | `--brief` |
| Silent mode | `-q` |
| Browser login flow | `-l` / `--login` |
| Auto-retry on auth expiry | default (disable with `--no-retry`) |
| Zero-config auth | browser cookies or env vars |

### Model Selection

Models are discovered at runtime — no hardcoded names. Survives Google's model updates.

```bash
# See what's available
python gemini.py --list-models

# Use shorthands (auto-resolved to current model IDs)
python gemini.py -m flash "fast answer"
python gemini.py -m pro "deep analysis"
python gemini.py -m thinking "logic puzzle"
```

### Multi-Turn Conversations

Conversation state is stored in a JSON file. The CLI passes the chat ID and metadata to Gemini, preserving full context across calls.

```bash
python gemini.py -c chat.json "Remember: secret code is 42."
python gemini.py -c chat.json "What was the secret code?"
# → "The secret code you told me is 42."

python gemini.py -c chat.json --new "Start fresh"
```

## Agent-Optimized Output

For AI agent consumption, use `-o` to write responses to disk. The CLI returns only a tiny pointer on stdout:

```bash
python gemini.py -i ui.png "Review this" --json -o result.md

# stdout: {"ok": true, "f": "./result.md", "s": 450, "b": 2}
# ~15-20 tokens to read. The full response is in result.md.
```

| Mode | Agent token cost |
|---|---|
| `-o result.md` | ~15-20 |
| `-o result.md -c chat.json` | ~25-35 |
| `--json` (long response) | ~500-1,500 |
| Error | ~20-30 |

Auto-quiet automatically suppresses stderr logs when stdout is piped (agent/subprocess mode). No `-q` flag needed.

## Auth

1. **Primary:** Auto-scans browser cookie databases for `__Secure-1PSID` and `__Secure-1PSIDTS`
   - **Linux/macOS/WSL:** Chrome first, then Firefox, Edge, Safari
   - **Windows:** Firefox first (no admin needed), then Chrome, Edge, Safari
2. **First-run:** `-l` / `--login` opens browser for login, polls every 3s for 120s until cookies appear, then continues automatically
3. **Fallback:** `GEMINI_SID` and `GEMINI_TS` environment variables
4. **Auto-retry:** On session expiry, re-scans cookies, then opens browser for re-auth

## Dependencies

- [gemini-webapi](https://github.com/HanaokaYuzu/Gemini-WebAPI) — unofficial Gemini web API client
- [browser-cookie3](https://github.com/borisbabic/browser_cookie3) — cross-browser cookie extraction
- [pillow](https://python-pillow.org/) — image handling

## Platform Support

| Platform | Browser Priority | Notes |
|---|---|---|
| Windows | Firefox → Chrome → Edge | Firefox needs no admin to install |
| Linux / WSL | Chrome → Firefox → Edge | Install Chrome user-level via `~/.local/bin` |
| macOS | Chrome → Firefox → Safari | — |

All platforms support `-l`/`--login` for first-run browser auth and `GEMINI_SID`/`GEMINI_TS` env vars as fallback.

## AI Agent Skills

The `skills/` directory contains reusable skill definitions for AI coding agents (Claude Code, Hermes, etc.) that describe how to invoke this tool with optimal token efficiency.
