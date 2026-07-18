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

### Full command surface (webapi)

```bash
# Text / image / doc
python gemini.py "prompt" -i img.png -f doc.pdf -o out.md --json

# Multi-turn
python gemini.py -m pro -c /tmp/session.json --new -f code.py "Review this" -o /tmp/r1.md
python gemini.py -m pro -c /tmp/session.json -f code.py "Follow up" -o /tmp/r2.md

# Streaming
python gemini.py -S "tell me a joke"

# Gems (custom system prompts)
python gemini.py --list-gems
python gemini.py --gem-info <ID_OR_NAME> --json
echo "You are a code reviewer." | python gemini.py --create-gem "Reviewer" -d "code help"
python gemini.py --edit-gem Reviewer -n "Reviewer v2" -p "Be very concise."
python gemini.py --delete-gem Reviewer
python gemini.py -g <GEM_ID> "chat with the gem"

# Deep research (long-running)
python gemini.py --deep-research "your research question" -o report.md

# Chat management
python gemini.py --list-chats
python gemini.py --read-chat <CID> --limit 20
python gemini.py --delete-chat <CID>

# Account / models
python gemini.py --account-status
python gemini.py --list-models
```

**Limitations:** Gem knowledge upload (files / GitHub code / NotebookLM) is a
Gemini web-UI feature and is NOT exposed by `gemini_webapi` — do it in the
browser. Deep research may not complete on all accounts (see skill pitfalls).

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
