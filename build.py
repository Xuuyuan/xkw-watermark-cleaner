#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unified build script - build full + simplified versions.

Usage:
    python build.py              # build all
    python build.py full         # build full version only
    python build.py simplified   # build simplified version only

Full version (PySide6, onedir):
    -> body/ (exe + dlls)

Simplified version (tkinter, onefile):
    -> body_simplified/ (single exe)
"""
import subprocess
import sys
import shutil
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent


def _find_build_python():
    """返回一个能同时导入 PySide6 与 PyInstaller 的 Python 解释器路径。

    优先使用当前解释器；若缺少依赖，则按候选路径逐个尝试。
    """
    candidates = [sys.executable]
    home = Path.home()
    candidates += [
        r"D:\My Program\Python313\python.exe",
        str(home / r".workbuddy\binaries\python\envs\default\Scripts\python.exe"),
        str(home / r"..\D:\Users\Com-DESKTOP-9N69UEQ\.workbuddy\binaries\python\envs\default\Scripts\python.exe"),
        r"D:\Users\Com-DESKTOP-9N69UEQ\.workbuddy\binaries\python\envs\default\Scripts\python.exe",
        r"C:\Users\Com-DESKTOP-9N69UEQ\.workbuddy\binaries\python\versions\3.13.12\python.exe",
    ]
    seen = set()
    for exe in candidates:
        exe_path = Path(exe)
        key = str(exe_path.resolve()) if exe_path.exists() else str(exe_path)
        if key in seen:
            continue
        seen.add(key)
        if not exe_path.exists():
            continue
        try:
            result = subprocess.run(
                [str(exe_path), "-c", "import PySide6, PyInstaller; print('OK')"],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0 and "OK" in result.stdout:
                return str(exe_path)
        except Exception:
            continue
    return sys.executable


PYTHON = _find_build_python()

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
    """Remove a directory or file, retrying a few times (handles briefly-locked files)."""
    p = PROJECT_DIR / name
    if not p.exists():
        return
    for attempt in range(5):
        try:
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
            return
        except (OSError, PermissionError):
            if attempt == 4:
                raise
            time.sleep(1)


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
    print("\n>> Step 1/5: PyInstaller build...")
    run([PYTHON, "-m", "PyInstaller", "--noconfirm", "standalone_optimized.spec"])

    # Step 2: Move to body/
    print("\n>> Step 2/5: Moving to body/...")
    clean_path("body")
    # 安全网：若旧 body 因文件被占用而未能完全删除，先把残留移走，
    # 避免新构建被 move 嵌套进旧目录（导致产物体积翻倍）。
    if body_dir.exists():
        stale = PROJECT_DIR / f"_body_stale_{int(time.time())}"
        try:
            shutil.move(str(body_dir), str(stale))
            print(f"  [WARN] 旧 body 未能完全删除，已移走: {stale.name}")
        except Exception:
            pass
    src = PROJECT_DIR / "dist" / FULL_NAME
    dst = body_dir
    if src.exists():
        shutil.move(str(src), str(dst))
        print("  Moved -> body/")
    else:
        print("  [WARN] dist output not found")

    # Step 3: Post-build cleanup (remove curl_cffi, numpy, PIL, etc.)
    print("\n>> Step 3/5: Post-build cleanup (post_clean.py)...")
    run([PYTHON, str(PROJECT_DIR / "post_clean.py")])

    # Step 4: Selective UPX compression (skip Qt files)
    print("\n>> Step 4/5: Selective UPX compression (skip Qt files)...")
    run([PYTHON, str(PROJECT_DIR / "upx_compress.py")])

    # Step 5: Remove .bak files
    print("\n>> Step 5/5: Removing .bak files...")
    bak_count = 0
    if body_dir.exists():
        for f in body_dir.rglob("*.bak"):
            f.unlink(missing_ok=True)
            bak_count += 1
    print(f"  Removed {bak_count} .bak files")

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

    if body_dir.exists():
        print(f"  Full:        body/ ({dir_size_mb(body_dir):.1f} MB)")
    if simp_exe.exists():
        print(f"  Simplified:  body_simplified/ ({simp_exe.stat().st_size / 1048576:.1f} MB)")
    print()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            input("\nPress Enter to close...")
        except EOFError:
            # 非交互环境（如管道 / 自动化调用）无 stdin，直接退出，不算失败
            pass
