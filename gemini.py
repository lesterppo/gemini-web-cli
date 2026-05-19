#!/usr/bin/env python3
"""
AI-native CLI for Gemini — flexible multimodal input via browser session.

Examples:
  python gemini.py "Explain quantum computing in 3 bullet points"
  python gemini.py -i chart.png "What trend does this show?"
  python gemini.py -i a.jpg -i b.jpg "Compare these two images"
  python gemini.py -f report.pdf "Summarize this document"
  python gemini.py -f data.csv -i plot.png "Analyze this data"
  cat prompt.txt | python gemini.py -i screenshot.png
  python gemini.py -i ui.png --brief -o review.md -q

Multi-turn conversations:
  python gemini.py -c chat.json "My favorite color is blue."
  python gemini.py -c chat.json "What did I say my favorite color was?"
  python gemini.py -c chat.json --new  "Start a fresh conversation"
"""
import os
import sys
import json
import asyncio
import argparse
import re
import time
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

import loguru
loguru.logger.remove()
loguru.logger.add(sys.stderr, level="ERROR", format="<red>[gemini]</red> {message}")

import browser_cookie3
from gemini_webapi import GeminiClient

AUTH_EXPIRED_PATTERNS = [
    "UNAUTHENTICATED",
    "cookies have expired",
    "session is not authenticated",
    "error code: 1100",
    "User is not authenticated",
]


class ChatRef:
    """Thin wrapper so gemini_webapi can read .metadata from the chat parameter."""
    def __init__(self, metadata: list):
        self.metadata = metadata


class GeminiCLI:
    def __init__(self):
        self.client = None
        self.quiet = False

    def log(self, msg: str):
        if not self.quiet:
            print(f"[gemini] {msg}", file=sys.stderr)

    def fail(self, code: str, reason: str):
        print(json.dumps({"ok": False, "err": code, "msg": reason}, ensure_ascii=False))
        sys.exit(1)

    # ── auth ──────────────────────────────────────────────

    def extract_cookies(self) -> tuple:
        browsers = [
            ('firefox', browser_cookie3.firefox),
            ('chrome', browser_cookie3.chrome),
            ('edge', browser_cookie3.edge),
            ('safari', browser_cookie3.safari),
        ]
        for name, fetch_func in browsers:
            try:
                cj = fetch_func(domain_name='.google.com')
                sid, ts = None, None
                for c in cj:
                    if c.name == '__Secure-1PSID':
                        sid = c.value
                    elif c.name == '__Secure-1PSIDTS':
                        ts = c.value
                if sid and ts:
                    self.log(f"Cookies from {name}")
                    return sid, ts
            except Exception:
                continue
        return None, None

    def is_auth_error(self, error_msg: str) -> bool:
        upper = error_msg.upper()
        return any(p.upper() in upper for p in AUTH_EXPIRED_PATTERNS)

    # ── model resolution ──────────────────────────────────

    # Maps user shorthand to Model enum type component.
    # Thinking tier (--thinking) determines the prefix: BASIC / PLUS / ADVANCED.
    _MODEL_TYPE_ALIASES = {
        "pro": "PRO", "flash": "FLASH", "fast": "FLASH",
        "thinking": "THINKING", "think": "THINKING", "flash-thinking": "THINKING",
        "lite": "LITE",
    }

    _THINKING_ALIASES = {
        "standard": "BASIC", "basic": "BASIC",
        "plus": "PLUS",
        "extended": "ADVANCED", "advanced": "ADVANCED",
    }

    def resolve_model(self, user_input: str | None,
                      thinking: str | None = None):
        """Resolve model selection. Returns a Model enum when thinking tier
           is specified, otherwise a string. No hardcoded model names."""
        if not user_input:
            return None

        # ── Thinking tier specified → construct Model enum ──
        if thinking:
            tier = self._THINKING_ALIASES.get(thinking.lower().strip(), thinking.upper())
            mtype = self._MODEL_TYPE_ALIASES.get(user_input.lower().strip())
            if mtype is None:
                return user_input  # pass through, let server reject
            if mtype == "LITE":
                # Lite doesn't have thinking tiers, return as string
                return self._resolve_string(user_input)
            try:
                from gemini_webapi.client import Model
                return Model[f"{tier}_{mtype}"]
            except KeyError:
                return user_input

        # ── No thinking tier → string resolution (backward compat) ──
        return self._resolve_string(user_input)

    def _resolve_string(self, user_input: str) -> str:
        """Match user shorthand against live model list. Returns string model ID."""
        if self.client is None:
            return user_input
        try:
            available = self.client.list_models()
        except Exception:
            return user_input

        name_map = {str(m).lower(): str(m) for m in available}
        q = user_input.lower().strip()

        if q in name_map:
            return name_map[q]

        # Single substring match
        matches = [v for k, v in name_map.items() if q in k]
        if len(matches) == 1:
            return matches[0]

        # Alias matching
        if q in ("flash", "fast", "speed"):
            flash = [v for k, v in name_map.items() if "flash" in k]
            if flash:
                return flash[0]
        if q in ("pro", "best", "smart"):
            pro = [v for k, v in name_map.items() if "pro" in k]
            if pro:
                return pro[0]
        if q in ("lite", "cheap", "small"):
            lite = [v for k, v in name_map.items() if "lite" in k]
            if lite:
                return lite[0]

        return user_input

    # ── conversation state ────────────────────────────────

    def load_conversation(self, path: str) -> dict | None:
        p = Path(path)
        if not p.exists():
            return None
        try:
            state = json.loads(p.read_text(encoding="utf-8"))
            if state.get("metadata") and len(state["metadata"]) >= 1:
                return state
        except (json.JSONDecodeError, KeyError):
            pass
        return None

    def save_conversation(self, path: str, state: dict):
        state["updated"] = datetime.now(timezone.utc).isoformat()
        Path(path).write_text(json.dumps(state, ensure_ascii=False, indent=2),
                              encoding="utf-8")

    # ── generate ──────────────────────────────────────────

    async def generate(self, sid: str, ts: str, prompt: str, files: list,
                       chat_metadata: list | None = None, model: str | None = None):
        """Returns (ok, response_text, new_metadata)."""
        if self.client is None:
            self.client = GeminiClient(secure_1psid=sid, secure_1psidts=ts)
            await self.client.init()
        try:
            kwargs = {"prompt": prompt}
            if files:
                kwargs["files"] = files
            if chat_metadata:
                kwargs["chat"] = ChatRef(chat_metadata)
            if model:
                kwargs["model"] = model
            response = await self.client.generate_content(**kwargs)
            new_meta = list(response.metadata) if response.metadata else None
            return True, response.text, new_meta
        except Exception as e:
            return False, str(e), None

    # ── output ────────────────────────────────────────────

    def parse_code_blocks(self, text: str) -> list:
        pattern = r"```(\w*)\n(.*?)```"
        return [{"lang": m[0], "code": m[1].strip()}
                for m in re.findall(pattern, text, re.DOTALL)]

    def emit(self, text: str, args, conv_state: dict | None = None):
        code = self.parse_code_blocks(text)

        if args.output:
            out_path = Path(args.output)
            if out_path.suffix.lower() == ".json":
                payload = {"ok": True, "text": text, "code": code}
                if conv_state:
                    payload["conversation"] = conv_state
                out_path.write_text(json.dumps(payload, ensure_ascii=False),
                                    encoding="utf-8")
            else:
                out_path.write_text(text, encoding="utf-8")
            pointer = {"ok": True, "f": self._short_path(out_path),
                       "s": out_path.stat().st_size, "b": len(code)}
            if conv_state:
                pointer["c"] = conv_state.get("cid")
                pointer["t"] = conv_state.get("turns")
            print(json.dumps(pointer, ensure_ascii=False))

        elif args.json:
            payload = {"ok": True, "text": text, "code": code}
            if conv_state:
                payload["conversation"] = conv_state
            print(json.dumps(payload, ensure_ascii=False))
        else:
            print(text)

    @staticmethod
    def _short_path(p: Path) -> str:
        """Return ./relative/path when under cwd, absolute otherwise. Saves bytes."""
        try:
            rel = p.resolve().relative_to(Path.cwd())
            return "./" + str(rel).replace("\\", "/")
        except ValueError:
            return str(p.resolve())

    # ── main ──────────────────────────────────────────────

    async def run(self):
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')

        parser = argparse.ArgumentParser(
            description="AI-native CLI for Gemini — flexible multimodal input via browser session",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""Examples:
  python gemini.py "Explain quantum computing"
  python gemini.py -i chart.png "What trend does this show?"
  python gemini.py -i a.jpg -i b.jpg "Compare these"
  python gemini.py -f report.pdf "Summarize this document"
  echo "Hello in French" | python gemini.py
  python gemini.py -i ui.png --brief -o review.md -q

Multi-turn conversations:
  python gemini.py -c chat.json "My favorite color is blue."
  python gemini.py -c chat.json "What color did I say was my favorite?"
  python gemini.py -c chat.json --new "Start a different topic"

Model selection (auto-discovered at runtime, no hardcoded names):
  python gemini.py --list-models
  python gemini.py "fast answer" -m flash
  python gemini.py -i complex.png "deep analysis" -m pro""")
        parser.add_argument("prompt", nargs="*", type=str,
            help="Prompt text (concatenated with spaces). Reads from stdin if empty.")
        parser.add_argument("-p", "--prompt-text", type=str, dest="prompt_str",
            help="Prompt text (alternative to positional)")
        parser.add_argument("-i", "--image", type=str, action="append", dest="images",
            default=[], metavar="FILE", help="Attach an image file (repeatable)")
        parser.add_argument("-f", "--file", type=str, action="append", dest="files",
            default=[], metavar="FILE", help="Attach a document — PDF, text, CSV, etc. (repeatable)")
        parser.add_argument("-c", "--conversation", type=str, metavar="FILE",
            help="Conversation state file for multi-turn chats")
        parser.add_argument("--new", action="store_true", dest="new_conv",
            help="Start a new conversation even if -c FILE already exists")
        parser.add_argument("-m", "--model", type=str, metavar="MODEL",
            help="Model to use: 'flash', 'pro', 'lite', or a full model ID. Auto-discovered at runtime.")
        parser.add_argument("--thinking", type=str, metavar="TIER",
            choices=["standard", "plus", "extended"],
            help="Thinking level: standard (default), plus, extended. [experimental: may not differ yet via web API]")
        parser.add_argument("--list-models", action="store_true",
            help="Print available models and exit")
        parser.add_argument("-o", "--output", type=str, metavar="FILE",
            help="Write response to FILE instead of stdout (stdout gets a pointer JSON)")
        parser.add_argument("--json", action="store_true",
            help="Structured JSON for agent consumption")
        parser.add_argument("--brief", action="store_true",
            help="Prepend 'Be concise.' to the prompt for shorter responses")
        parser.add_argument("-q", "--quiet", action="store_true",
            help="Suppress progress messages on stderr")
        parser.add_argument("--no-retry", action="store_true",
            help="Disable automatic cookie refresh and retry")
        args = parser.parse_args()

        # Auto-quiet: when stdout is captured by an agent (pipe, subprocess), suppress logs
        if not args.quiet and not sys.stdout.isatty():
            args.quiet = True
        self.quiet = args.quiet

        # ── Build prompt ──
        if args.prompt_str:
            prompt = args.prompt_str
        elif args.prompt:
            prompt = " ".join(args.prompt)
        elif args.list_models:
            prompt = ""  # no prompt needed
        else:
            if not sys.stdin.isatty():
                prompt = sys.stdin.read().strip()
            else:
                self.fail("NO_PROMPT", "No prompt provided. Use positional args, -p, or pipe text via stdin.")

        if args.brief and not prompt.startswith("Be concise"):
            prompt = "Be concise. " + prompt

        # ── Conversation state ──
        conv_state = None
        chat_metadata = None

        if args.conversation:
            if not args.new_conv:
                conv_state = self.load_conversation(args.conversation)
                if conv_state:
                    chat_metadata = conv_state.get("metadata")
                    self.log(f"Continuing conversation {conv_state['cid']} (turn {conv_state.get('turns', 0) + 1})")

            if conv_state is None:
                conv_state = {
                    "cid": None,
                    "metadata": None,
                    "turns": 0,
                    "created": datetime.now(timezone.utc).isoformat(),
                }
                self.log("Starting new conversation")

        # ── Collect files ──
        all_files = []
        for img in args.images:
            p = Path(img)
            if not p.exists():
                self.fail("FILE_NOT_FOUND", f"Image not found: {img}")
            all_files.append(str(p))
        for f in args.files:
            p = Path(f)
            if not p.exists():
                self.fail("FILE_NOT_FOUND", f"File not found: {f}")
            all_files.append(str(p))

        if all_files:
            self.log(f"{len(all_files)} attachment(s): {', '.join(Path(f).name for f in all_files)}")

        # ── Auth ──
        sid = os.getenv("GEMINI_SID")
        ts = os.getenv("GEMINI_TS")
        cookie_source = "env"
        if not sid or not ts:
            sid, ts = self.extract_cookies()
            cookie_source = "browser"
        if not sid or not ts:
            self.fail("AUTH_EXPIRED",
                "No Gemini cookies. Set GEMINI_SID/GEMINI_TS env vars or log into gemini.google.com.")

        # ── Model (init client early so resolve_model can query live list) ──
        if args.model or args.list_models:
            try:
                self.client = GeminiClient(secure_1psid=sid, secure_1psidts=ts)
                await self.client.init()
            except Exception as e:
                self.fail("CLIENT_INIT_FAILED", str(e))

        if args.list_models:
            models = self.client.list_models()
            print(json.dumps({"ok": True, "models": [str(m) for m in models]},
                             ensure_ascii=False))
            return

        model = self.resolve_model(args.model, args.thinking)
        if model:
            label = model.name if hasattr(model, 'name') else model
            tier = f" ({args.thinking})" if args.thinking else ""
            self.log(f"Model: {label}{tier}")

        # ── Generate with retry ──
        max_rounds = 3 if not args.no_retry else 1
        browser_opened = False

        for attempt in range(max_rounds):
            self.log(f"Attempt {attempt + 1}/{max_rounds}...")

            ok, result, new_metadata = await self.generate(
                sid, ts, prompt, all_files, chat_metadata, model)

            if ok:
                # Update conversation state from response metadata
                if args.conversation and new_metadata:
                    conv_state["cid"] = new_metadata[0]
                    conv_state["metadata"] = new_metadata
                    conv_state["turns"] += 1
                    self.save_conversation(args.conversation, conv_state)

                self.emit(result, args, conv_state if args.conversation else None)
                return

            if not self.is_auth_error(result):
                self.fail("REQUEST_FAILED", result)

            self.log(f"Auth expired ({result[:80]}...)")

            if attempt == max_rounds - 1:
                break

            self.log("Re-scanning browser cookies...")

            if cookie_source == "env":
                new_sid, new_ts = self.extract_cookies()
                if new_sid and new_sid != sid:
                    sid, ts = new_sid, new_ts
                    cookie_source = "browser"
                    self.client = None
                    self.log("Found fresher cookies in browser, retrying...")
                    continue

            if not browser_opened and cookie_source != "env":
                self.log("Opening gemini.google.com for re-authentication...")
                webbrowser.open("https://gemini.google.com")
                browser_opened = True

                self.log("Waiting for fresh cookies (polling every 5s, 60s timeout)...")
                for _ in range(12):
                    time.sleep(5)
                    new_sid, new_ts = self.extract_cookies()
                    if new_sid and new_sid != sid:
                        sid, ts = new_sid, new_ts
                        self.client = None
                        self.log("Fresh cookies detected, retrying...")
                        break
                else:
                    self.log("No fresh cookies found in 60s, giving up.")

        self.fail("AUTH_EXPIRED",
            "Gemini session expired. Re-login at gemini.google.com and retry.")


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    cli = GeminiCLI()
    asyncio.run(cli.run())
