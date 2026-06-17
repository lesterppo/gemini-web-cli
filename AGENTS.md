# AGENTS.md — For AI Coding Agents

This repo is a CLI tool. You are an AI agent reading this file because you've been directed to this repository (cloned, opened, or referenced).

## What this repo is

`gemini-web-cli` — Zero-config Python CLI for Google Gemini via browser-cookie auth. No API key needed. It sends prompts, images, and documents to Gemini using your existing browser session cookies.

## How to use this tool

**Load the `gemini-web-cli` skill** from your skill registry first — it contains the full canonical procedures, pitfalls, WSL setup instructions, multi-turn patterns, and the develop-review loop workflow. This AGENTS.md is a pointer.

If you don't have the skill in your registry, the minimal quick-start is in `skills/gemini-cli/SKILL.md`.

### Invocation (agent-optimized)

Always use `-o <file>` to write the response to disk. stdout gets a ~15-20 token pointer:

```bash
cd <repo> && python gemini.py -m flash "your prompt" --json -o /tmp/result.md
# stdout: {"ok": true, "f": "/tmp/result.md", "s": 450, "b": 2}
```

Read the output file only when needed. The pointer's `b` field tells you how many code blocks the response contains.

### Multi-turn conversations

```bash
python gemini.py -m pro -c /tmp/session.json --new -f code.py "Review this" -o /tmp/r1.md
python gemini.py -m pro -c /tmp/session.json -f code.py "Follow up" -o /tmp/r2.md
```

## Key files

| File | Purpose |
|---|---|
| `gemini.py` | Main CLI — self-contained, zero install beyond pip deps |
| `gemini-search` | Google Search via Gemini with AI synthesis |
| `scripts/setup-wsl-firefox-cookies.py` | WSL Firefox cookie extraction setup |
| `scripts/refresh-cookies.py` | Extract and save Gemini auth cookies |
| `skills/gemini-cli/SKILL.md` | Skill definition for AI agents |
| `search-gem-prompt.txt` | Prompt template for Gemini Search Grounding |

## Platform notes

- **Windows:** Firefox first (no admin), then Chrome, Edge
- **Linux/macOS/WSL:** Chrome first, then Firefox, Edge
- **WSL + Firefox:** Run `scripts/setup-wsl-firefox-cookies.py` first — browser_cookie3 can't natively find Windows Firefox profiles on WSL
- **Auth fallback:** `GEMINI_SID` / `GEMINI_TS` env vars
- First run: `python gemini.py -l "prompt"` opens browser for login
