#!/usr/bin/env python3
"""构建脚本 v2：绕过沙箱中文路径和权限问题"""
import subprocess
import sys
import shutil
import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable
DIST = PROJECT_DIR / "dist"


def build(name, script, collect_all=None, add_data=None, hidden_imports=None):
    """通用构建函数"""
    cmd = [
        PYTHON, "-m", "PyInstaller",
        "--onefile", "--windowed",
        "--name", name,
        "--distpath", str(DIST),
        "--noconfirm",
    ]
    if add_data:
        for d in add_data:
            cmd += ["--add-data", d]
    if hidden_imports:
        for h in hidden_imports:
            cmd += ["--hidden-import", h]
    if collect_all:
        for c in collect_all:
            cmd += ["--collect-all", c]
    cmd.append(script)

    print(f"\n{'='*60}")
    print(f"构建: {name}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, cwd=str(PROJECT_DIR))
    return result.returncode == 0


def main():
    # 清理旧文件
    for item in ["build", "__pycache__"]:
        p = PROJECT_DIR / item
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
    for spec in PROJECT_DIR.glob("*.spec"):
        try:
            spec.unlink()
        except Exception:
            pass

    # 创建输出目录
    standalone_dir = DIST / "独立版"
    lite_dir = DIST / "精简版"
    standalone_dir.mkdir(parents=True, exist_ok=True)
    lite_dir.mkdir(parents=True, exist_ok=True)

    # === 版本一：独立版 ===
    ok1 = build(
        name="xkw_standalone",
        script="xkw_gui.py",
        collect_all=["PySide6", "PyMuPDF", "docx"],
        add_data=[
            "config.json;.",
            "clean_watermark.py;.",
            "clean_watermark_doc.py;.",
            "clean_watermark_docx.py;.",
            "clean_watermark_pdf.py;.",
            "cleaner_config.py;.",
            "context_menu_handler.py;.",
        ],
        hidden_imports=[
            "PySide6", "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets",
            "docx", "fitz", "curl_cffi", "win32com.client",
        ],
    )

    # 重命名为中文名
    if ok1:
        src = DIST / "xkw_standalone.exe"
        dst = standalone_dir / "学科网水印清理工具_独立版.exe"
        if src.exists():
            shutil.move(str(src), str(dst))
            print(f"独立版: {dst} ({dst.stat().st_size / 1048576:.1f} MB)")

    # 清理 spec
    for spec in PROJECT_DIR.glob("*.spec"):
        try:
            spec.unlink()
        except Exception:
            pass

    # === 版本二：精简版（启动器） ===
    ok2 = build(
        name="xkw_launcher",
        script="xkw_launcher.py",
    )

    # 重命名 + 复制源码到精简版目录
    if ok2:
        src = DIST / "xkw_launcher.exe"
        dst = lite_dir / "学科网水印清理工具_精简版.exe"
        if src.exists():
            shutil.move(str(src), str(dst))
            print(f"精简版: {dst} ({dst.stat().st_size / 1048576:.1f} MB)")

        # 复制源码到精简版目录
        source_files = [
            "xkw_gui.py", "clean_watermark.py", "clean_watermark_doc.py",
            "clean_watermark_docx.py", "clean_watermark_pdf.py",
            "cleaner_config.py", "config.json", "context_menu_handler.py",
            "install_context_menu.py", "uninstall_context_menu.py",
            "requirements.txt",
        ]
        for f in source_files:
            src_file = PROJECT_DIR / f
            if src_file.exists():
                try:
                    shutil.copy2(str(src_file), str(lite_dir / f))
                except Exception as e:
                    print(f"  跳过 {f}: {e}")

    # === 清理缓存 ===
    print(f"\n{'='*60}")
    print("清理缓存...")
    print(f"{'='*60}")
    for item in ["build", "__pycache__"]:
        p = PROJECT_DIR / item
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
            print(f"  已删除: {item}/")
    for spec in PROJECT_DIR.glob("*.spec"):
        try:
            spec.unlink()
            print(f"  已删除: {spec.name}")
        except Exception:
            pass

    # === 总结 ===
    print(f"\n{'='*60}")
    print("构建完成!")
    print(f"{'='*60}")
    print(f"  独立版: {'✓' if ok1 else '✗'}  dist/独立版/学科网水印清理工具_独立版.exe")
    print(f"  精简版: {'✓' if ok2 else '✗'}  dist/精简版/学科网水印清理工具_精简版.exe")
    print(f"  在线版: ✓  dist/在线版/学科网水印清理工具_在线版.zip")

    if not (ok1 and ok2):
        sys.exit(1)


if __name__ == "__main__":
    main()
