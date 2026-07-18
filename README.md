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
| Gems (custom system prompts) | `-g GEM`, `--list-gems`, `--setup-search-gem` |
| Gem lifecycle (webapi) | `--gem-info ID`, `--create-gem NAME`, `--edit-gem ID`, `--delete-gem ID` |
| Streaming output | `-S` / `--stream` |
| Deep research | `--deep-research PROMPT` (long-running) |
| Chat management | `--list-chats`, `--read-chat CID`, `--delete-chat CID` |
| Account status | `--account-status` |
| Download generated images | `--save-images DIR` |
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

### Gem Lifecycle (webapi)

Full Gem CRUD via `gemini-webapi` (no browser automation needed):

```bash
# List all gems (system + user)
python gemini.py --list-gems

# Show full info (name, id, prompt, description) by id or name
python gemini.py --gem-info <GEM_ID_OR_NAME> --json

# Create a custom Gem (system prompt via -p or stdin; -d for description)
echo "You are a helpful coding tutor. Be concise." | python gemini.py --create-gem "My Tutor" -d "coding help"
python gemini.py --create-gem "My Tutor" -p "You are a helpful coding tutor." -d "coding help"

# Edit a custom Gem (rename via -n, new prompt via -p/stdin, new desc via -d)
python gemini.py --edit-gem <GEM_ID_OR_NAME> -n "My Tutor v2" -p "Be very concise."
#   Predefined/system gems (e.g. "Writing editor") are protected and rejected.

# Delete a custom Gem by id or name
python gemini.py --delete-gem <GEM_ID_OR_NAME>

# Chat with any Gem (system or custom)
python gemini.py -g <GEM_ID_OR_NAME> "Explain Big-O notation in one sentence"
```

**Limitations (by design of `gemini-webapi`):** the web API surface exposes
Gem CRUD + chat but **not** knowledge-file upload. `--create-gem` / `--edit-gem`
have no `files=` slot, so uploading documents/images *into a Gem's knowledge
base at creation* is unsupported through this CLI — do that in the Gemini web UI
(`gemini.google.com/app`) or via a CDP-driven tool. Image generation in a Gem
chat returns a CDN URL; use `--save-images DIR` to download the bytes to disk.

### Streaming

`-S` / `--stream` prints tokens as they arrive (no `-o`/`--json` wrapping):

```bash
echo "Explain Big-O in one sentence." | python gemini.py -S
# tokens appear live on stdout
```

### Chat Management

List, read, and delete conversations (chats) stored in your Gemini account:

```bash
# List recent conversations (cid, title, timestamp)
python gemini.py --list-chats

# Read a conversation's history by cid (last N turns via --limit)
python gemini.py --read-chat c_24e06f62cd43a307 --limit 20

# Delete a conversation by cid
python gemini.py --delete-chat c_24e06f62cd43a307
```

### Deep Research

`--deep-research PROMPT` runs a multi-step research task and waits for the
final report. This is long-running (can take minutes). The web API requires an
explicit confirmation step; the CLI handles plan → confirm → wait automatically:

```bash
python gemini.py --deep-research "Compare Z-score vs OCF/NI for bankruptcy prediction" -o report.md
```

> **Known limitation:** `gemini-webapi` (2.0.x) does not surface the
> `research_id` after the confirmation step, so `wait_for_deep_research` cannot
> always poll to completion on every account. If you see
> `Cannot poll deep research status: plan.research_id is missing`, the task did
> not start server-side — retry, or run deep research in the Gemini web UI.

### Account Status

Probe account capabilities (deep-research availability, quota, caps):

```bash
python gemini.py --account-status
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

## gemini-search — Google Search via Gemini Web

Built on top of gemini-cli, `gemini-search` triggers Gemini's native Google Search grounding and returns token-optimized JSON for downstream AI agents. Auto-sets up a Search Grounding Proxy Gem on first use.

```bash
# Structured search with AI synthesis
./gemini-search "latest breakthroughs in fusion energy 2026"

# Ultra-dense positional-array mode via Gem (auto-setup)
./gemini-search "AI regulation updates" -g "Gemini search"

# Image search — returns real CDN URLs
./gemini-search "aurora borealis 2026 photos" -g "Gemini search"

# Use stronger model, write to file
./gemini-search "complex analysis" -m pro -o results.json
```

**Token efficiency:** Gem mode outputs ~350-1,400 bytes vs 1,500-5,700 in default mode. Positional arrays `[0,"fact"]` save ~30% over keyed objects. See [gemini-search/README.md](gemini-search/README.md) for full docs.

## AI Agent Skills

**For AI coding agents (Claude Code, Hermes, Codex, etc.):** Load the `gemini-web-cli` skill from your skill registry for the full canonical procedures, pitfalls, WSL setup, and develop-review loop workflow.

If you're an AI agent reading this repo directly: start with `AGENTS.md` and `skills/gemini-cli/SKILL.md`.

The `skills/` directory contains reusable skill definitions that describe how to invoke this CLI with optimal token efficiency.
