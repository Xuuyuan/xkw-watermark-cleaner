# -*- coding: utf-8 -*-
"""Selective UPX compression for DLL/PYD files, skipping Qt files (to avoid breaking GUARD_CF)."""
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
BODY = PROJECT_DIR / "body"
UPX_CANDIDATES = [
    Path(sys.executable).parent / "Scripts" / "upx.exe",
    Path(sys.executable).parent / "upx.exe",
    PROJECT_DIR / "upx.exe",
    Path("upx.exe"),
]

# Skip these file/dir patterns (Qt related)
SKIP_PATTERNS = [
    "Qt6",               # Qt6 core DLLs
    "pyside6.abi3.dll",  # PySide6 bridge DLL
    r"plugins\platforms",  # platform plugins
    r"plugins\iconengines",  # icon engine plugins
]


def find_upx():
    for c in UPX_CANDIDATES:
        try:
            r = subprocess.run([str(c), "--version"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                return str(c)
        except Exception:
            pass
    return None


def should_compress(path: Path) -> bool:
    s = str(path).lower()
    for p in SKIP_PATTERNS:
        if p.lower() in s:
            return False
    return True


def main():
    upx = find_upx()
    if not upx:
        print("WARNING: UPX not found, skipping compression")
        sys.exit(0)
    print(f"Using UPX: {upx}")

    targets = []
    for ext in ("*.dll", "*.pyd"):
        for f in BODY.rglob(ext):
            if should_compress(f):
                targets.append(f)
            else:
                print(f"  skip {f.relative_to(BODY)}")

    print(f"Compressing {len(targets)} files...")
    # Batch calls to avoid command line too long
    BATCH = 50
    ok = failed = 0
    for i in range(0, len(targets), BATCH):
        batch = targets[i:i + BATCH]
        cmd = [upx, "--best", "--lzma", "--quiet"] + [str(f) for f in batch]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            ok += len(batch)
        else:
            failed += len(batch)
            print(f"  batch {i//BATCH + 1} failed: {r.stderr[:200]}")

    print(f"UPX done: {ok} ok, {failed} failed")


if __name__ == "__main__":
    main()
