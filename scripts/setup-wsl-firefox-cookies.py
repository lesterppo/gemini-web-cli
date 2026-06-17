#!/usr/bin/env python3
"""Set up WSL Firefox profile so browser_cookie3.firefox finds Windows Firefox cookies.

On WSL, browser_cookie3.firefox looks for profiles under ~/.mozilla/firefox/ but
the actual Firefox profiles live on the Windows side. This script auto-detects the
Windows Firefox directory and creates a WSL profile dir with symlinks so
browser_cookie3.firefox works seamlessly.

Usage:
    python3 setup-wsl-firefox-cookies.py                    # auto-detect & setup all
    python3 setup-wsl-firefox-cookies.py --profile <name>   # specific profile only
    python3 setup-wsl-firefox-cookies.py --list             # list available profiles
"""
import argparse
import os
import sys
import shutil
from pathlib import Path


def _find_windows_firefox() -> list[Path]:
    """Auto-detect Windows Firefox profiles directory via /mnt/c/Users/."""
    users_dir = Path("/mnt/c/Users")
    if not users_dir.exists():
        return []

    for user_dir in sorted(users_dir.iterdir()):
        if not user_dir.is_dir() or user_dir.name in (
            "Public", "Default", "Default User", "All Users"
        ):
            continue
        ff = user_dir / "AppData" / "Roaming" / "Mozilla" / "Firefox" / "Profiles"
        if ff.exists():
            return [ff]
    return []


def _discover_profiles(win_firefox: Path) -> list[tuple[str, float]]:
    """Return [(dir_name, size_mb), ...] for profiles with cookies.sqlite."""
    profiles = []
    for d in sorted(win_firefox.iterdir()):
        if d.is_dir():
            db = d / "cookies.sqlite"
            if db.exists() and db.stat().st_size > 0:
                size_mb = db.stat().st_size / (1024 * 1024)
                profiles.append((d.name, size_mb))
    return profiles


def setup_profile(
    win_firefox: Path, win_dir_name: str, wsl_name: str | None = None
) -> Path:
    """Create a WSL Firefox profile symlinked to a Windows profile."""
    cookies_db = win_firefox / win_dir_name / "cookies.sqlite"
    if not cookies_db.exists():
        raise FileNotFoundError(f"No cookies.sqlite at {cookies_db}")

    wsl_firefox = Path.home() / ".mozilla" / "firefox"
    wsl_firefox.mkdir(parents=True, exist_ok=True)

    wsl_name = wsl_name or win_dir_name
    wsl_profile = wsl_firefox / wsl_name
    wsl_profile.mkdir(exist_ok=True)

    target = wsl_profile / "cookies.sqlite"
    if target.exists() or target.is_symlink():
        target.unlink()

    try:
        os.symlink(str(cookies_db), str(target))
        print(f"  symlink: {target} -> {cookies_db}")
    except OSError:
        shutil.copy2(cookies_db, target)
        print(f"  copied:  {target} <- {cookies_db}")

    return wsl_profile


def write_profiles_ini(profiles: list[tuple[str, Path]]) -> None:
    """Write Firefox profiles.ini pointing to WSL profile dirs."""
    wsl_firefox = Path.home() / ".mozilla" / "firefox"
    wsl_firefox.mkdir(parents=True, exist_ok=True)

    lines = []
    for i, (name, path) in enumerate(profiles):
        lines.append(f"[Profile{i}]")
        lines.append(f"Name={name}")
        lines.append("IsRelative=0")
        lines.append(f"Path={path}")
        lines.append(f"Default={'1' if i == 0 else '0'}")
        lines.append("")

    lines.append("[General]")
    lines.append("StartWithLastProfile=1")
    lines.append("Version=2")

    ini_path = wsl_firefox / "profiles.ini"
    ini_path.write_text("\n".join(lines))
    print(f"  profiles.ini written ({len(profiles)} profile(s))")


def verify() -> bool:
    """Test that browser_cookie3.firefox can read cookies."""
    try:
        import browser_cookie3
        cj = browser_cookie3.firefox(domain_name=".google.com")
        print(f"\n  Verification: {len(cj)} Google cookies found — OK!")
        return True
    except Exception as e:
        print(f"\n  Verification failed: {e}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Setup WSL Firefox profiles for browser_cookie3"
    )
    parser.add_argument(
        "--profile", "-p",
        help="Windows Firefox profile dir name (e.g. tv0zh0s7.default-release)",
    )
    parser.add_argument(
        "--name", "-n",
        help="Friendly name for the WSL profile dir",
    )
    parser.add_argument(
        "--list", "-l", action="store_true",
        help="List available Windows Firefox profiles and exit",
    )
    args = parser.parse_args()

    # Auto-detect Windows Firefox
    win_firefox_list = _find_windows_firefox()
    if not win_firefox_list:
        print("ERROR: No Windows Firefox profiles found under /mnt/c/Users/")
        print("Is the C: drive mounted? Is Firefox installed on Windows?")
        sys.exit(1)

    win_firefox = win_firefox_list[0]
    available = _discover_profiles(win_firefox)

    if not available:
        print(f"No Firefox profiles with cookies.sqlite found in {win_firefox}")
        sys.exit(1)

    print(f"Windows Firefox: {win_firefox}")
    print(f"Found {len(available)} profile(s):")
    for name, size in available:
        print(f"  {name}  ({size:.1f} MB)")

    if args.list:
        return

    profiles = []
    if args.profile:
        matches = [n for n, _ in available if args.profile in n]
        if not matches:
            print(f"Profile '{args.profile}' not found.")
            print(f"Available: {[n for n, _ in available]}")
            sys.exit(1)
        wsl_name = args.name or matches[0]
        wsl_profile = setup_profile(win_firefox, matches[0], wsl_name)
        profiles.append((wsl_name, wsl_profile))
    else:
        for name, _ in available:
            wsl_profile = setup_profile(win_firefox, name)
            profiles.append((name, wsl_profile))

    write_profiles_ini(profiles)
    verify()


if __name__ == "__main__":
    main()
