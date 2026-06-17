---
name: gemini-web-cli
description: Zero-config Gemini CLI via browser-cookie auth. No API key needed. Load this skill to use gemini-cli for text, image, document prompts, and multi-turn conversations.
---

# gemini-web-cli Skill

Zero-config Python CLI at `gemini.py` for Google Gemini via browser-cookie auth. No API key needed.

**Repo:** https://github.com/lesterppo/gemini-web-cli

**Canonical skill:** Load `gemini-web-cli` from your AI agent's skill registry for full procedures, pitfalls, WSL setup, multi-turn patterns, and the develop-review loop. This file is the repo-bundled summary.

## Quick Start (from repo)

```bash
cd <repo> && python gemini.py -l "Hello"          # first run: login via browser
python gemini.py "Explain quantum computing"       # text prompt
python gemini.py -i chart.png "What trend?"        # image analysis
python gemini.py -f report.pdf "Summarize"          # document analysis
python gemini.py -c chat.json "Remember X"          # multi-turn (persist state)
python gemini.py -c chat.json "What did I say?"     # continues conversation
```

## Agent-Optimized Invocation (always use -o)

```bash
python gemini.py -i ui.png "Review this" --json -o result.md
# stdout: {"ok": true, "f": "./result.md", "s": 450, "b": 2}
# ~15-20 tokens. Full response on disk.
```

## Flags

| Flag | Purpose |
|---|---|
| `-i FILE` | Attach image (repeatable) |
| `-f FILE` | Attach document (repeatable) |
| `-m MODEL` | `flash`, `pro`, `thinking`, or full ID |
| `-c FILE` | Multi-turn conversation state file |
| `--new` | Start fresh conversation |
| `-o FILE` | Write response to file, stdout gets token pointer |
| `--json` | Structured JSON output |
| `-l` / `--login` | Open browser to sign in, auto-capture cookies |
| `--browser` | Preferred browser: `firefox`, `chrome`, `edge`, `safari` |
| `--list-models` | Print available models |
| `--brief` | Ask for concise response (opt-in only) |
| `-q` | Suppress stderr progress |

## Auth

- **Windows:** Firefox → Chrome → Edge → Safari
- **Linux/macOS/WSL:** Chrome → Firefox → Edge → Safari
- Override with `--browser <name>` or `GEMINI_BROWSER` env var
- Fallback: `GEMINI_SID` / `GEMINI_TS` env vars

### WSL Firefox Setup

On WSL, `browser_cookie3.firefox` cannot find Windows Firefox profiles. Run:

```bash
python scripts/setup-wsl-firefox-cookies.py           # auto-detect & setup all
python scripts/setup-wsl-firefox-cookies.py --list    # list available profiles
```

This creates a symlinked `~/.mozilla/firefox/` profile pointing to your Windows Firefox cookies. After visiting gemini.google.com in Firefox, close Firefox so cookies flush to disk, then:

```bash
python scripts/refresh-cookies.py                     # extract & save to auth.json
```

## Pitfalls

- **`__Secure-1PSIDTS` required:** The Token Server cookie is generated only during active Gemini use. Visit gemini.google.com in the browser first, close the browser, then extract cookies. Without TS, API calls time out.
- **Firefox must be closed** before cookie extraction — Firefox writes cookies lazily to SQLite.
- **Gemini cannot access local files** unless uploaded with `-f`.
- **`-f` from subprocess with empty stdin:** Fixed — now fails fast with NO_PROMPT error.
- **Timeout with large prompts + files:** Trim prompt to essentials, let files carry context.

## Dependencies

```bash
pip install gemini-webapi browser-cookie3 pillow
```
