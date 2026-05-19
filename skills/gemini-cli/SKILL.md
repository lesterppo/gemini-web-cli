---
name: gemini-cli
description: Use when sending prompts, images, or documents to Google Gemini via zero-config browser-cookie CLI. Triggered by: Gemini, visual review, screenshot analysis, image analysis, document analysis, multi-turn chat.
---

# gemini-cli — AI-Native Gemini CLI Tools

Two zero-config Python CLIs at `C:\Users\Peter\` for Google Gemini via browser-cookie auth. No API key needed — auto-detects credentials from Firefox/Chrome/Edge.

## Tools

| Tool | Purpose |
|---|---|
| `C:\Users\Peter\gemini.py` | General multimodal CLI — arbitrary prompts, images, documents, multi-turn conversations |
| `C:\Users\Peter\critic.py` | Fixed UI/UX visual critic — upload screenshot, get CSS/JS fixes |

## Quick Start

```bash
# General text prompt
python C:/Users/Peter/gemini.py "Explain quantum computing in 3 bullet points"

# Image analysis
python C:/Users/Peter/gemini.py -i chart.png "What trend does this show?"

# Document analysis
python C:/Users/Peter/gemini.py -f report.pdf "Summarize this"

# Compare multiple images
python C:/Users/Peter/gemini.py -i before.png -i after.png "What changed?"

# Stdin pipe
echo "What is 2+2?" | python C:/Users/Peter/gemini.py

# UI/UX review of a screenshot
python C:/Users/Peter/critic.py screenshot.png --json -o review.md -q
```

## Agent-Optimized Invocation (always use -o)

```bash
# Minimal token cost: ~15-20 token pointer, response on disk
python C:/Users/Peter/gemini.py -i ui.png "Review this" --json -o result.md

# stdout: {"ok": true, "f": "./result.md", "s": 450, "b": 2}

# With --brief for shorter responses
python C:/Users/Peter/gemini.py -i ui.png "Review this" --brief --json -o result.md
```

The agent should `Read` the output file selectively. The pointer includes `b` (code block count) so the agent can decide whether to open it.

## gemini.py Flags

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
| `--brief` | Ask Gemini for concise responses |
| `-q` / `--quiet` | Suppress stderr progress (auto-enabled when piped) |
| `--no-retry` | Disable auto-retry on auth expiry |

## Multi-Turn Conversations

```bash
# Start a conversation
python C:/Users/Peter/gemini.py -c chat.json "My favorite color is blue."

# Continue — Gemini remembers context
python C:/Users/Peter/gemini.py -c chat.json "What color did I say?"

# With file output (agent mode)
python C:/Users/Peter/gemini.py -c chat.json "What color?" --json -o turn2.md
# stdout: {"ok": true, "f": "./turn2.md", "s": 120, "b": 0, "c": "c_abc123...", "t": 2}

# Start fresh, discarding history
python C:/Users/Peter/gemini.py -c chat.json --new "Different topic"
```

## Model Selection

```bash
# Fast model
python C:/Users/Peter/gemini.py -m flash "quick question"

# Deep reasoning
python C:/Users/Peter/gemini.py -m pro "complex analysis"

# Flash-thinking variant
python C:/Users/Peter/gemini.py -m thinking "logic puzzle"

# See available models (runtime discovery, no hardcoded names)
python C:/Users/Peter/gemini.py --list-models
```

Models are discovered at runtime via `client.list_models()`. No hardcoded model names — survives Google's model updates automatically.

## Output Pointer Format

Agent-optimized pointer uses short keys to minimize token cost:

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

Error pointer:
```json
{"ok": false, "err": "AUTH_EXPIRED", "msg": "No Gemini cookies..."}
```

## Auth Architecture

- **Primary:** Auto-scans browser cookie databases (Firefox first — no admin on Windows, then Chrome, Edge, Safari)
- **Fallback:** `GEMINI_SID` / `GEMINI_TS` env vars
- **Auto-retry:** Re-scans cookies on auth failure, opens `gemini.google.com` for re-auth, polls every 5s for 60s
- Cookies: `__Secure-1PSID` and `__Secure-1PSIDTS` from `.google.com` domain

## Token Budget (for AI agent planning)

| Invocation | Agent token cost |
|---|---|
| `-o result.md` | ~15-20 tokens (pointer only) |
| `-o result.md -c chat.json` | ~25-35 tokens (pointer + conversation) |
| `--json` (short response) | ~30-100 tokens |
| `--json` (long response) | ~500-1,500 tokens (avoid in agent loops) |
| Error | ~20-30 tokens |

## Dependencies

```bash
pip install gemini-webapi browser-cookie3 pillow
```
