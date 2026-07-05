#!/usr/bin/env python3
"""
学科网水印清理工具 - 精简版启动器
检测本机 Python 环境与依赖库，通过后调用系统 Python 运行 GUI。
"""

import os
import sys
import subprocess
import importlib.util
from pathlib import Path

# --- 依赖检查 ---
REQUIRED_PACKAGES = {
    "PySide6": "PySide6.QtWidgets",
    "PyMuPDF": "fitz",
    "python-docx": "docx",
}

def find_system_python():
    """查找系统 Python（优先 python，其次 py launcher）。"""
    candidates = []
    if sys.executable and Path(sys.executable).exists():
        candidates.append(sys.executable)
    # py launcher
    try:
        result = subprocess.run(
            ["py", "-3", "-c", "import sys; print(sys.executable)"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            candidates.append(result.stdout.strip())
    except Exception:
        pass
    # python / python3
    for name in ["python", "python3"]:
        try:
            result = subprocess.run(
                [name, "-c", "import sys; print(sys.executable)"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                candidates.append(result.stdout.strip())
        except Exception:
            pass

    # 去重，过滤当前 exe 自身
    seen = set()
    unique = []
    for c in candidates:
        c_resolved = str(Path(c).resolve())
        if c_resolved not in seen and c_resolved != str(Path(sys.executable).resolve()):
            seen.add(c_resolved)
            unique.append(c)
    return unique


def check_packages(python_exe):
    """用指定 Python 检查依赖包是否已安装。返回 (已安装列表, 缺失列表)。"""
    installed = []
    missing = []
    for pkg_name, import_name in REQUIRED_PACKAGES.items():
        try:
            result = subprocess.run(
                [python_exe, "-c", f"import {import_name}; print('OK')"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and "OK" in result.stdout:
                installed.append(pkg_name)
            else:
                missing.append(pkg_name)
        except Exception:
            missing.append(pkg_name)
    return installed, missing


def install_packages(python_exe, packages):
    """尝试用 pip 安装缺失的包。"""
    install_cmd = [python_exe, "-m", "pip", "install"] + packages
    try:
        result = subprocess.run(install_cmd, capture_output=True, text=True, timeout=120)
        return result.returncode == 0
    except Exception:
        return False


def main():
    # 如果是打包成 exe，源码在同级目录或子目录
    if getattr(sys, 'frozen', False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).resolve().parent

    gui_script = base_dir / "xkw_gui.py"
    if not gui_script.exists():
        # 尝试在脚本同级目录找
        gui_script = base_dir / "xkw_gui.py"

    # 使用 tkinter 做提示（因为 tkinter 是内置的）
    try:
        import tkinter as tk
        from tkinter import messagebox, simpledialog
        has_tk = True
    except ImportError:
        has_tk = False

    def show_msg(title, message, icon="info"):
        if has_tk:
            root = tk.Tk()
            root.withdraw()
            getattr(messagebox, "showinfo" if icon == "info" else "showwarning" if icon == "warning" else "showerror")(
                title, message
            )
            root.destroy()
        else:
            print(f"[{title}] {message}")

    def ask_yesno(title, message):
        if has_tk:
            root = tk.Tk()
            root.withdraw()
            result = messagebox.askyesno(title, message)
            root.destroy()
            return result
        else:
            return input(f"{title}: {message} (y/n): ").lower().startswith("y")

    # 1. 查找系统 Python
    pythons = find_system_python()
    if not pythons:
        msg = (
            "未检测到系统 Python 环境。\n\n"
            "精简版需要本机已安装 Python 3.8+。\n\n"
            "请前往 https://www.python.org/downloads/ 下载安装，\n"
            "安装时请勾选「Add Python to PATH」。\n\n"
            "或使用独立版（无需 Python）。"
        )
        show_msg("环境检测失败", msg, "error")
        return 1

    python_exe = pythons[0]

    # 2. 检查依赖
    installed, missing = check_packages(python_exe)

    if missing:
        msg = (
            f"检测到 Python: {python_exe}\n\n"
            f"缺失依赖库: {', '.join(missing)}\n\n"
            "是否立即自动安装？"
        )
        if ask_yesno("依赖缺失", msg):
            # pip install
            pip_packages = {
                "PySide6": "PySide6",
                "PyMuPDF": "PyMuPDF",
                "python-docx": "python-docx",
            }
            to_install = [pip_packages.get(p, p) for p in missing]
            ok = install_packages(python_exe, to_install)
            if ok:
                show_msg("安装成功", f"已安装: {', '.join(to_install)}", "info")
            else:
                show_msg(
                    "安装失败",
                    f"自动安装失败，请手动执行：\n\n"
                    f'"{python_exe}" -m pip install {" ".join(to_install)}',
                    "error",
                )
                return 1
        else:
            show_msg(
                "请手动安装",
                f"请手动执行以下命令安装依赖：\n\n"
                f'"{python_exe}" -m pip install PySide6 PyMuPDF python-docx',
                "warning",
            )
            return 1

    # 3. 启动 GUI
    if not gui_script.exists():
        show_msg(
            "文件缺失",
            f"找不到 GUI 主程序: {gui_script}\n\n"
            "请确保 xkw_gui.py 与本程序在同一目录。",
            "error",
        )
        return 1

    try:
        proc = subprocess.run([python_exe, str(gui_script)])
        return proc.returncode
    except Exception as e:
        show_msg("启动失败", f"启动 GUI 失败: {e}", "error")
        return 1


if __name__ == "__main__":
    sys.exit(main())
