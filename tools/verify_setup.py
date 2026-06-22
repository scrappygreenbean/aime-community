#!/usr/bin/env python3
"""Verify all required tools and env vars for the AIME video toolkit."""

import os
import shutil
import subprocess
import sys

RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"

def ok(label): print(f"  {GREEN}✓{RESET}  {label}")
def fail(label): print(f"  {RED}✗{RESET}  {label}")
def warn(label): print(f"  {YELLOW}⚠{RESET}  {label}")


def check_binary(name, min_version=None, version_flag="--version"):
    path = shutil.which(name)
    if not path:
        fail(f"{name} not found in PATH")
        return False
    if min_version:
        try:
            out = subprocess.check_output([name, version_flag], stderr=subprocess.STDOUT, text=True)
            ok(f"{name} ({out.splitlines()[0].strip()[:60]})")
        except Exception:
            ok(f"{name} found at {path}")
    else:
        ok(f"{name} found at {path}")
    return True


def check_env(var, required=True, hint=""):
    val = os.environ.get(var)
    if val:
        masked = val[:6] + "..." if len(val) > 6 else "***"
        ok(f"{var} = {masked}")
        return True
    if required:
        fail(f"{var} not set{(' — ' + hint) if hint else ''}")
    else:
        warn(f"{var} not set (optional){(' — ' + hint) if hint else ''}")
    return not required


def check_python_pkg(pkg):
    try:
        __import__(pkg.replace("-", "_"))
        ok(f"Python: {pkg}")
        return True
    except ImportError:
        fail(f"Python: {pkg} not installed  →  pip install {pkg}")
        return False


def main():
    test_mode = "--test" in sys.argv
    print(f"\n{BOLD}AIME Video Toolkit — Setup Verification{RESET}\n")
    errors = 0

    # ── Binaries ──────────────────────────────────────────────────────────────
    print(f"{BOLD}Binaries{RESET}")
    if not check_binary("python3"): errors += 1
    if not check_binary("node", version_flag="--version"): errors += 1
    if not check_binary("npx"): errors += 1
    if not check_binary("ffmpeg"): errors += 1

    # ── Python packages ───────────────────────────────────────────────────────
    print(f"\n{BOLD}Python packages{RESET}")
    for pkg in ["fastapi", "uvicorn", "anthropic", "boto3", "dotenv"]:
        if not check_python_pkg(pkg): errors += 1

    # ── HyperFrames CLI ───────────────────────────────────────────────────────
    print(f"\n{BOLD}HyperFrames CLI{RESET}")
    try:
        out = subprocess.check_output(
            ["npx", "--yes", "hyperframes@0.7.0", "--version"],
            stderr=subprocess.STDOUT, text=True, timeout=30
        )
        ok(f"hyperframes ({out.strip()})")
    except Exception as e:
        fail(f"hyperframes CLI — {e}")
        errors += 1

    # ── Environment variables ─────────────────────────────────────────────────
    print(f"\n{BOLD}Environment variables{RESET}")
    if not check_env("ANTHROPIC_API_KEY", hint="get from console.anthropic.com"):
        errors += 1
    check_env("R2_ACCOUNT_ID", required=False, hint="Cloudflare R2 (optional — videos served locally without it)")
    check_env("R2_ACCESS_KEY_ID", required=False)
    check_env("R2_SECRET_ACCESS_KEY", required=False)
    check_env("R2_BUCKET", required=False)
    check_env("R2_PUBLIC_URL", required=False, hint="CDN URL prefix for the R2 bucket")

    # ── Result ────────────────────────────────────────────────────────────────
    print()
    if errors == 0:
        print(f"{GREEN}{BOLD}All checks passed — you're ready to run the server.{RESET}")
        print(f"  uvicorn api_server:app --reload\n")
        sys.exit(0)
    else:
        print(f"{RED}{BOLD}{errors} issue(s) found — fix them before starting.{RESET}\n")
        if test_mode:
            sys.exit(1)
        sys.exit(1)


if __name__ == "__main__":
    main()
