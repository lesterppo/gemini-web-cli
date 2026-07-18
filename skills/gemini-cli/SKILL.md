---
name: gemini-web-cli
description: Zero-config Gemini CLI via browser-cookie auth. No API key needed. Load this skill to use gemini-cli for text, image, document prompts, multi-turn chats, Gem CRUD, deep research, and chat management.
---

# gemini-web-cli Skill

Zero-config Python CLI at `gemini.py` for Google Gemini via browser-cookie auth.
No API key needed. Built on `gemini_webapi` + `browser-cookie3`.

**Repo:** https://github.com/lesterppo/gemini-web-cli

**Canonical skill:** Load `gemini-web-cli` from your AI agent's skill registry for
full procedures, pitfalls, WSL setup, multi-turn patterns, and the
develop-review loop. This file is the repo-bundled summary.

## When to Use

- Send text / image / document prompts to Gemini with no API key (browser session cookies).
- Multi-turn conversations that persist across agent turns (`-c FILE`).
- Create / edit / delete / inspect custom Gems (`--create-gem` etc.).
- Run deep-research tasks (`--deep-research`).
- List / read / delete past conversations (`--list-chats`, `--read-chat`, `--delete-chat`).
- Stream a response token-by-token to stdout (`-S`).
- Download generated images to disk (`--save-images DIR`).

## Quick Start (from repo)

```bash
cd <repo> && python gemini.py -l "Hello"          # first run: login via browser
python gemini.py "Explain quantum computing"       # text prompt
python gemini.py -i chart.png "What trend?"        # image analysis
python gemini.py -f report.pdf "Summarize"         # document analysis
python gemini.py -c chat.json "Remember X"         # multi-turn (persist state)
python gemini.py -c chat.json "What did I say?"    # continues conversation
python gemini.py -S "tell me a joke"              # streaming output
```

## Agent-Optimized Invocation (always use -o)

```bash
python gemini.py -i ui.png "Review this" --json -o result.md
# stdout: {"ok": true, "f": "./result.md", "s": 450, "b": 2}
# ~15-20 tokens. Full response on disk.
```

## Flags (full webapi surface)

| Flag | Purpose |
|---|---|
| `-i FILE` | Attach image (repeatable) |
| `-f FILE` | Attach document (repeatable) |
| `-m MODEL` | `flash`, `pro`, `thinking`, or full ID |
| `--thinking TIER` | `standard`, `plus`, `extended` |
| `-c FILE` / `--new` | Multi-turn conversation state file / start fresh |
| `-o FILE` | Write response to file, stdout gets token pointer |
| `--json` | Structured JSON output |
| `--brief` | Ask for concise response |
| `-q` | Suppress stderr progress |
| `-S` / `--stream` | Stream tokens to stdout (no wrapping) |
| `-g GEM` / `--list-gems` | Use a Gem / list all Gems |
| `--gem-info ID` | Show full Gem info (name, id, prompt, description) |
| `--create-gem NAME` | Create a custom Gem (`-p` prompt, `-d` desc) |
| `--edit-gem ID` | Edit a custom Gem (`-n` name, `-p` prompt, `-d` desc) |
| `--delete-gem ID` | Delete a custom Gem |
| `--setup-search-gem` | Create/update the Google-Search grounding Gem |
| `--save-images DIR` | Download returned images into DIR |
| `--deep-research PROMPT` | Run a deep-research task (long-running) |
| `--list-chats` | List recent conversations |
| `--read-chat CID` | Read a conversation by cid (`--limit N` turns) |
| `--delete-chat CID` | Delete a conversation by cid |
| `--account-status` | Probe account capabilities |
| `--list-models` | Print available models |
| `-l` / `--login` | Open browser to sign in, auto-capture cookies |
| `--browser NAME` | Preferred browser: `firefox`, `chrome`, `edge`, `safari` |
| `--no-retry` | Fail fast on first error |

## Gem CRUD example

```bash
echo "You are a code reviewer. Be concise." | python gemini.py --create-gem "Reviewer" -d "code help"
python gemini.py --edit-gem Reviewer -n "Reviewer v2" -p "Be very concise."
python gemini.py --gem-info Reviewer --json
python gemini.py --delete-gem Reviewer
```

Predefined/system Gems (e.g. "Writing editor") are protected and rejected for edit/delete.

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

This creates a symlinked `~/.mozilla/firefox/` profile pointing to your Windows
Firefox cookies. After visiting gemini.google.com in Firefox, close Firefox so
cookies flush to disk, then:

```bash
python scripts/refresh-cookies.py                     # extract & save to auth.json
```

## Pitfalls

- **`__Secure-1PSIDTS` required:** The Token Server cookie is generated only during active Gemini use. Visit gemini.google.com in the browser first, close the browser, then extract cookies. Without TS, API calls time out.
- **Firefox must be closed** before cookie extraction — Firefox writes cookies lazily to SQLite.
- **Gemini cannot access local files** unless uploaded with `-f`.
- **Gem knowledge upload is NOT supported by `gemini_webapi`.** `--create-gem` / `--edit-gem` take only name/prompt/description. Uploading files / GitHub code / NotebookLM as a Gem's knowledge base is a Gemini web-UI feature (gemini.google.com/app) — do it in the browser, not via this CLI.
- **Deep research may not complete on all accounts.** `gemini_webapi` 2.0.x does not surface the research task id after the confirmation step, so polling to completion can fail with `Cannot poll deep research status: plan.research_id is missing`. Retry, or run deep research in the web UI.
- **Image generation counts against a daily quota.** When exhausted, Gemini returns a "limit reset" message; `--save-images` still works for any images actually returned.
- **`-S` / `--stream` bypasses `-o`/`--json` wrapping** and prints raw tokens — use it for live display, not agent parsing.

## Dependencies

```bash
pip install gemini-webapi browser-cookie3 pillow
```
