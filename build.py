#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unified build script - build full + simplified versions.

Usage:
    python build.py              # build all
    python build.py full         # build full version only
    python build.py simplified   # build simplified version only

Full version (PySide6, onedir):
    -> body/ (exe + dlls)
    -> body_standalone.7z

Simplified version (tkinter, onefile):
    -> body_simplified/ (single exe)
"""
import subprocess
import sys
import shutil
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable

# Output names defined in spec files (must match)
FULL_NAME = "xkw_standalone"
LITE_NAME = "xkw_simplified"


def run(cmd):
    """Run a command, exit on failure."""
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, cwd=str(PROJECT_DIR))
    if result.returncode != 0:
        print(f"\n[ERROR] Command failed (exit={result.returncode})")
        sys.exit(1)
    return result.returncode


def clean_path(name):
    """Remove a directory or file."""
    p = PROJECT_DIR / name
    if p.is_dir():
        shutil.rmtree(p, ignore_errors=True)
    elif p.is_file():
        p.unlink(missing_ok=True)


def dir_size_mb(path):
    """Calculate total directory size in MB."""
    if not path.exists():
        return 0.0
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return total / 1048576


# ============================================================
# Full version (PySide6, onedir)
# ============================================================
def build_full():
    print("\n" + "=" * 60)
    print("  [1/2] Build Full Version (PySide6, onedir)")
    print("=" * 60)

    body_dir = PROJECT_DIR / "body"

    # Clean old cache
    print("\n>> Cleaning old cache...")
    clean_path("build")
    clean_path("__pycache__")

    # Step 1: PyInstaller
    print("\n>> Step 1/6: PyInstaller build...")
    run([PYTHON, "-m", "PyInstaller", "--noconfirm", "standalone_optimized.spec"])

    # Step 2: Move to body/
    print("\n>> Step 2/6: Moving to body/...")
    clean_path("body")
    src = PROJECT_DIR / "dist" / FULL_NAME
    dst = body_dir
    if src.exists():
        shutil.move(str(src), str(dst))
        print("  Moved -> body/")
    else:
        print("  [WARN] dist output not found")

    # Step 3: Post-build cleanup (remove curl_cffi, numpy, PIL, etc.)
    print("\n>> Step 3/6: Post-build cleanup (post_clean.py)...")
    run([PYTHON, str(PROJECT_DIR / "post_clean.py")])

    # Step 4: Selective UPX compression (skip Qt files)
    print("\n>> Step 4/6: Selective UPX compression (skip Qt files)...")
    run([PYTHON, str(PROJECT_DIR / "upx_compress.py")])

    # Step 5: Remove .bak files
    print("\n>> Step 5/6: Removing .bak files...")
    bak_count = 0
    if body_dir.exists():
        for f in body_dir.rglob("*.bak"):
            f.unlink(missing_ok=True)
            bak_count += 1
    print(f"  Removed {bak_count} .bak files")

    # Step 6: Pack 7z distribution archive
    print("\n>> Step 6/6: Packing 7z distribution archive...")
    run([PYTHON, str(PROJECT_DIR / "pack_dist.py")])

    # Clean cache
    clean_path("build")
    clean_path("__pycache__")

    # Result
    print("\n" + "-" * 60)
    if body_dir.exists():
        size = dir_size_mb(body_dir)
        print(f"  [OK] Full version: body/ ({size:.1f} MB)")
    else:
        print("  [WARN] Full version: body/ not found")
    z = PROJECT_DIR / "body_standalone.7z"
    if z.exists():
        print(f"  [OK] 7z package: {z.name} ({z.stat().st_size / 1048576:.1f} MB)")
    else:
        print("  [WARN] 7z package: not found")
    print("-" * 60)
    print("[1/2] Full version build complete.")


# ============================================================
# Simplified version (tkinter, onefile)
# ============================================================
def build_simplified():
    print("\n" + "=" * 60)
    print("  [2/2] Build Simplified Version (tkinter, onefile)")
    print("=" * 60)

    simp_dir = PROJECT_DIR / "body_simplified"
    simp_dir.mkdir(exist_ok=True)
    simp_exe = simp_dir / f"{LITE_NAME}.exe"

    # Clean old build
    print("\n>> Cleaning old build...")
    if simp_exe.exists():
        simp_exe.unlink()
    clean_path("build")
    clean_path("__pycache__")

    # PyInstaller
    print("\n>> PyInstaller build (simplified spec)...")
    run([PYTHON, "-m", "PyInstaller", "--noconfirm", "standalone_simplified.spec"])

    # Move exe
    print("\n>> Moving exe to body_simplified/...")
    src = PROJECT_DIR / "dist" / f"{LITE_NAME}.exe"
    if src.exists():
        shutil.move(str(src), str(simp_exe))
        print("  Moved -> body_simplified/")
    else:
        print("  [WARN] dist output not found")

    # Clean cache
    clean_path("build")
    clean_path("__pycache__")
    clean_path("dist")

    # Result
    print("\n" + "-" * 60)
    if simp_exe.exists():
        size = simp_exe.stat().st_size / 1048576
        print(f"  [OK] Simplified: body_simplified/ ({size:.1f} MB)")
    else:
        print("  [WARN] Simplified: not found")
    print("-" * 60)
    print("[2/2] Simplified version build complete.")


# ============================================================
# Main entry
# ============================================================
def main():
    target = ""
    if len(sys.argv) > 1:
        target = sys.argv[1].lower().lstrip("-")

    print("=" * 60)
    print("  xkw-watermark-cleaner - Build")
    print("=" * 60)

    if target in ("", "all"):
        build_full()
        build_simplified()
    elif target in ("full", "standalone", "complete"):
        build_full()
    elif target in ("simplified", "lite"):
        build_simplified()
    else:
        print(f"Unknown argument: {target}")
        print("Usage: python build.py [full|simplified]")
        sys.exit(1)

    # Summary
    print("\n" + "=" * 60)
    print("  Build Complete!")
    print("=" * 60)
    body_dir = PROJECT_DIR / "body"
    simp_exe = PROJECT_DIR / "body_simplified" / f"{LITE_NAME}.exe"
    z = PROJECT_DIR / "body_standalone.7z"

    if body_dir.exists():
        print(f"  Full:        body/ ({dir_size_mb(body_dir):.1f} MB)")
    if z.exists():
        print(f"  7z package:  {z.name} ({z.stat().st_size / 1048576:.1f} MB)")
    if simp_exe.exists():
        print(f"  Simplified:  body_simplified/ ({simp_exe.stat().st_size / 1048576:.1f} MB)")
    print()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        input("\nPress Enter to close...")
