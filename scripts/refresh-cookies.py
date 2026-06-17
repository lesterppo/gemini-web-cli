#!/usr/bin/env python3
"""Refresh Gemini auth cookies from browser and save to ~/.gemini-cli/auth.json.

Extracts __Secure-1PSID and __Secure-1PSIDTS from the preferred browser (respects
GEMINI_BROWSER env var, defaults to platform-specific order). Saves to auth.json
for use with gemini-cli.

Usage:
    python3 scripts/refresh-cookies.py              # auto-detect browser
    GEMINI_BROWSER=firefox python3 scripts/refresh-cookies.py
"""
import json
import os
import sys
from collections.abc import Callable
from pathlib import Path

import browser_cookie3

AUTH_FILE = Path.home() / ".gemini-cli" / "auth.json"


def _get_browser_order() -> list[tuple[str, Callable]]:
    """Return browser order based on platform."""
    if sys.platform == "win32":
        return [
            ("firefox", browser_cookie3.firefox),
            ("chrome", browser_cookie3.chrome),
            ("edge", browser_cookie3.edge),
            ("safari", browser_cookie3.safari),
        ]
    else:
        return [
            ("chrome", browser_cookie3.chrome),
            ("firefox", browser_cookie3.firefox),
            ("edge", browser_cookie3.edge),
            ("safari", browser_cookie3.safari),
        ]


def extract_cookies(preferred: str | None = None) -> tuple[str, str]:
    """Extract Gemini auth cookies from browser. Returns (sid, ts)."""
    browser_order = _get_browser_order()

    if preferred:
        pref_lower = preferred.lower()
        for i, (name, _) in enumerate(browser_order):
            if name == pref_lower:
                browser_order.insert(0, browser_order.pop(i))
                print(f"Browser preference: {pref_lower} (first)")
                break
        else:
            print(
                f"Unknown browser '{preferred}'; "
                f"available: {', '.join(n for n, _ in browser_order)}"
            )

    for name, fetch_func in browser_order:
        try:
            cj = fetch_func(domain_name=".google.com")
            sid, ts = None, None
            for c in cj:
                if c.name == "__Secure-1PSID":
                    sid = c.value
                elif c.name == "__Secure-1PSIDTS":
                    ts = c.value
            if sid:
                print(f"Cookies from {name}")
                return sid, ts or ""
        except Exception as e:
            print(f"  {name}: {e}")
            continue

    return "", ""


def main() -> None:
    preferred = os.getenv("GEMINI_BROWSER")

    sid, ts = extract_cookies(preferred)

    if not sid:
        print("ERROR: No __Secure-1PSID cookie found in any browser.")
        print("Sign in at gemini.google.com and close the browser, then retry.")
        print("Or run: gemini-cli -l")
        sys.exit(1)

    auth = {
        "__Secure-1PSID": sid,
        "__Secure-1PSIDTS": ts,
        "browser": preferred or "auto",
    }

    AUTH_FILE.parent.mkdir(exist_ok=True)
    AUTH_FILE.write_text(json.dumps(auth, indent=2))

    status = "OK" if ts else "MISSING"
    print(f"\nSaved to {AUTH_FILE}")
    print(f"  SID: {'FOUND'}  TS: {status}")

    if not ts:
        print("\nWARNING: __Secure-1PSIDTS is missing.")
        print("Visit gemini.google.com in your browser to generate it,")
        print("close the browser, then run this script again.")


if __name__ == "__main__":
    main()
