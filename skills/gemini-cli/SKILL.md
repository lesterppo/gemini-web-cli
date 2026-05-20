---
name: gemini-web-cli
description: Use when sending prompts, images, or documents to Google Gemini via zero-config browser-cookie CLI. Multi-turn conversations, dynamic model discovery, agent-optimized output. Triggered by: Gemini, visual review, screenshot analysis, image analysis, document analysis.
---

# gemini-web-cli — Zero-Config Gemini CLI

Zero-config Python CLI for Google Gemini via browser-cookie auth. No API key needed.

Repo: https://github.com/lesterppo/gemini-web-cli

## Platform Paths

| Platform | Command |
|---|---|
| **Any** | `python gemini.py` (from repo directory) |
| **Linux/WSL** | `gemini-cli` (after adding wrapper to PATH) |

## Quick Start

```bash
# First run — opens browser for login
gemini-cli -l "Hello"

# Text prompt
gemini-cli "Explain quantum computing in 3 bullet points"

# Image analysis
gemini-cli -i chart.png "What trend does this show?"

# Document analysis
gemini-cli -f report.pdf "Summarize this"

# Compare multiple images
gemini-cli -i before.png -i after.png "What changed?"

# Stdin pipe
echo "What is 2+2?" | gemini-cli
```

## Agent-Optimized Invocation (always use -o)

```bash
# Token cost: ~15-20 token pointer, response on disk
gemini-cli -i ui.png "Review this" --json -o result.md

# stdout: {"ok": true, "f": "./result.md", "s": 450, "b": 2}
```

Read the output file only when needed. The pointer includes `b` (code block count) so the agent can decide whether to open it.

**Do NOT use `--brief` by default.** Gemini should give full, natural responses. Reserve `--brief` only when the user explicitly asks for concise answers.

## Flags

| Flag | Purpose |
|---|---|
| `-i FILE` | Attach image (repeatable) |
| `-f FILE` | Attach document — PDF, TXT, CSV, etc. (repeatable) |
| `-p TEXT` | Prompt via flag instead of positional |
| `[prompt ...]` | Prompt as positional arguments (concatenated) |
| *(stdin)* | Prompt piped from stdin |
| `-c FILE` | Conversation state file for multi-turn chats |
| `--new` | Start fresh conversation even if `-c` file exists |
| `-m MODEL` | Model: `flash`, `pro`, `thinking`, or full ID. Auto-discovered at runtime |
| `--thinking TIER` | Thinking level: `standard`, `plus`, `extended` [experimental] |
| `--list-models` | Print available models and exit |
| `--json` | Structured JSON output |
| `-o FILE` | Write response to FILE, stdout gets ~15-20 token pointer |
| `-l` / `--login` | Open browser to sign in and auto-capture cookies (for first-run or re-auth) |
| `--brief` | Ask Gemini for concise responses (opt-in only) |
| `-q` / `--quiet` | Suppress stderr progress (auto-enabled when piped) |
| `--no-retry` | Disable auto-retry on auth expiry |

## Multi-Turn Conversations

```bash
gemini-cli -c chat.json "My favorite color is blue."
gemini-cli -c chat.json "What color did I say?"
# → "The secret code you told me is 42."

gemini-cli -c chat.json --new "Start fresh"
```

## Model Selection

```bash
gemini-cli -m flash "fast answer"
gemini-cli -m pro "deep analysis"
gemini-cli --list-models
```

Models are discovered at runtime via `client.list_models()`. No hardcoded model names.

## Auth Architecture

- **Windows:** Firefox first (no admin needed), then Chrome, Edge, Safari
- **Linux/macOS/WSL:** Chrome first, then Firefox, Edge, Safari
- **Fallback:** `GEMINI_SID` / `GEMINI_TS` env vars
- **First-run:** `-l`/`--login` opens browser for login, polls every 3s for 120s
- **Auto-retry:** On session expiry, re-scans cookies, then opens browser for re-auth

## Output Pointer Format

```json
{"ok": true, "f": "./result.md", "s": 450, "b": 2}
```

| Key | Meaning |
|---|---|
| `f` | File path (relative when under cwd) |
| `s` | Response size in bytes |
| `b` | Number of extracted code blocks |
| `c` | Conversation ID (only with `-c`) |
| `t` | Turn number (only with `-c`) |

## Token Budget (for AI agent planning)

| Invocation | Agent token cost |
|---|---|
| `-o result.md` | ~15-20 tokens (pointer only) |
| `-o result.md -c chat.json` | ~25-35 tokens |
| `--json` (long response) | ~500-1,500 tokens (avoid in agent loops) |
| Error | ~20-30 tokens |

## Dependencies

```bash
pip install gemini-webapi browser-cookie3 pillow
```
