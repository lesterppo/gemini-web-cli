#!/usr/bin/env python3
import os
import sys
import json
import asyncio
import argparse
import re
import time
import webbrowser
from pathlib import Path

import loguru
loguru.logger.remove()
loguru.logger.add(sys.stderr, level="ERROR", format="<red>[critic]</red> {message}")

import browser_cookie3
from gemini_webapi import GeminiClient

AUTH_EXPIRED_PATTERNS = [
    "UNAUTHENTICATED",
    "cookies have expired",
    "session is not authenticated",
    "error code: 1100",
    "User is not authenticated",
]

DEFAULT_PROMPT = (
    "You are an elite Full-Stack and UI/UX expert. Review this product screenshot, "
    "identify the 3 most critical visual or interactive issues, and provide the exact "
    "native CSS/JS or framework code needed to fix them."
)

BRIEF_PROMPT = (
    "You are an elite Full-Stack and UI/UX expert. Review this product screenshot. "
    "Identify the 3 most critical visual or interactive issues. For each issue, provide "
    "a one-line description and the exact fix code. Be concise — no introductory text, "
    "no closing remarks. Just: Issue, Fix, Code."
)


class AINativeCLI:
    def __init__(self):
        self.client = None

    def log(self, message: str):
        print(f"[critic] {message}", file=sys.stderr)

    def fail(self, code: str, reason: str):
        print(json.dumps({"ok": False, "err": code, "msg": reason}, ensure_ascii=False))
        sys.exit(1)

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
                for cookie in cj:
                    if cookie.name == '__Secure-1PSID':
                        sid = cookie.value
                    elif cookie.name == '__Secure-1PSIDTS':
                        ts = cookie.value
                if sid and ts:
                    self.log(f"Cookies from {name}")
                    return sid, ts
            except Exception:
                continue
        return None, None

    def is_auth_error(self, error_msg: str) -> bool:
        upper = error_msg.upper()
        return any(p.upper() in upper for p in AUTH_EXPIRED_PATTERNS)

    async def try_generate(self, sid: str, ts: str, prompt: str, image_path: str):
        if self.client is None:
            self.client = GeminiClient(secure_1psid=sid, secure_1psidts=ts)
            await self.client.init()
        try:
            response = await self.client.generate_content(
                prompt=prompt, files=[image_path]
            )
            return True, response.text
        except Exception as e:
            return False, str(e)

    def parse_code_blocks(self, text: str) -> list:
        pattern = r"```(\w*)\n(.*?)```"
        blocks = re.findall(pattern, text, re.DOTALL)
        return [{"lang": b[0], "code": b[1].strip()} for b in blocks]

    async def run(self):
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')

        parser = argparse.ArgumentParser(description="AI-Native Visual Critic for Gemini")
        parser.add_argument("image", type=str, help="Path to the product screenshot")
        parser.add_argument("--prompt", type=str, default=DEFAULT_PROMPT, help="Custom Prompt")
        parser.add_argument("--json", action="store_true", help="Structured JSON for agent consumption")
        parser.add_argument("-o", "--output", type=str, metavar="FILE",
            help="Write response to FILE instead of stdout (stdout gets only a pointer JSON)")
        parser.add_argument("-q", "--quiet", action="store_true",
            help="Suppress progress messages on stderr")
        parser.add_argument("--no-retry", action="store_true",
            help="Disable automatic cookie refresh and retry")
        parser.add_argument("--brief", action="store_true",
            help="Ask Gemini for a concise, token-efficient response")
        args = parser.parse_args()

        # Validate asset first (cheap)
        img_path = Path(args.image)
        if not img_path.exists():
            self.fail("FILE_NOT_FOUND", f"File not found: {args.image}")

        prompt = BRIEF_PROMPT if args.brief else args.prompt

        # Get initial cookies
        sid = os.getenv("GEMINI_SID")
        ts = os.getenv("GEMINI_TS")
        cookie_source = "env"
        if not sid or not ts:
            sid, ts = self.extract_cookies()
            cookie_source = "browser"
        if not sid or not ts:
            self.fail("AUTH_EXPIRED",
                "No Gemini cookies. Set GEMINI_SID/GEMINI_TS env vars or log into gemini.google.com.")

        # Attempt generation with auto-retry on auth failure
        max_rounds = 3 if not args.no_retry else 1
        browser_opened = False

        for attempt in range(max_rounds):
            if not args.quiet:
                self.log(f"Attempt {attempt + 1}/{max_rounds}...")

            ok, result = await self.try_generate(sid, ts, prompt, str(img_path))

            if ok:
                self._emit(result, args)
                return

            if not self.is_auth_error(result):
                self.fail("REQUEST_FAILED", result)

            if not args.quiet:
                self.log(f"Auth expired ({result[:80]}...)")

            if attempt == max_rounds - 1:
                break

            if not args.quiet:
                self.log("Re-scanning browser cookies...")

            if cookie_source == "env":
                new_sid, new_ts = self.extract_cookies()
                if new_sid and new_sid != sid:
                    sid, ts = new_sid, new_ts
                    cookie_source = "browser"
                    self.client = None
                    if not args.quiet:
                        self.log("Found fresher cookies in browser, retrying...")
                    continue

            if not browser_opened and cookie_source != "env":
                if not args.quiet:
                    self.log("Opening gemini.google.com for re-authentication...")
                webbrowser.open("https://gemini.google.com")
                browser_opened = True

                if not args.quiet:
                    self.log("Waiting for fresh cookies (polling every 5s, 60s timeout)...")
                for _ in range(12):
                    time.sleep(5)
                    new_sid, new_ts = self.extract_cookies()
                    if new_sid and new_sid != sid:
                        sid, ts = new_sid, new_ts
                        self.client = None
                        if not args.quiet:
                            self.log("Fresh cookies detected, retrying...")
                        break
                else:
                    if not args.quiet:
                        self.log("No fresh cookies found in 60s, giving up.")

        self.fail("AUTH_EXPIRED",
            "Gemini session expired. Re-login at gemini.google.com and retry.")

    def _emit(self, text: str, args):
        """Route output. File mode: write to disk, stdout gets a 50-byte pointer.
           Stdout mode: print the full response."""
        code_blocks = self.parse_code_blocks(text)

        if args.output:
            out_path = Path(args.output)
            ext = out_path.suffix.lower()

            if ext == ".json":
                payload = {"ok": True, "text": text, "code": code_blocks}
                out_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            else:
                out_path.write_text(text, encoding="utf-8")

            pointer = {"ok": True, "file": str(out_path.resolve()),
                       "size": out_path.stat().st_size, "blocks": len(code_blocks)}
            print(json.dumps(pointer, ensure_ascii=False))

        elif args.json:
            print(json.dumps({"ok": True, "text": text, "code": code_blocks}, ensure_ascii=False))
        else:
            print(text)


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    cli = AINativeCLI()
    asyncio.run(cli.run())
