# -*- coding: utf-8 -*-
"""安装右键菜单：使用运行本脚本的 Python 解释器注册菜单命令。

不再扫描本机所有 Python 做依赖检测，直接用当前运行 install 的解释器
（静默模式优先用同目录 pythonw.exe）。请确保运行本脚本的 Python 已安装
所需依赖：pywin32 / python-docx / PyMuPDF。
"""
import sys
import winreg
from pathlib import Path

FILE_MENU_TEXT = "清除学科网水印"
FILE_OVERWRITE_MENU_TEXT = "清除学科网水印（覆盖）"
DIR_MENU_TEXT = "清除学科网水印（文件夹内所有文件）"
DIR_OVERWRITE_MENU_TEXT = "清除学科网水印（文件夹，覆盖）"
ARCHIVE_MENU_TEXT = "学科网压缩包批量处理"
MENU_KEY_NAME = "xkw-watermark-cleaner"
OVERWRITE_MENU_KEY_NAME = "xkw-watermark-cleaner-overwrite"
ARCHIVE_MENU_KEY_NAME = "xkw-watermark-cleaner-archive"
TARGET_EXTENSIONS = [".doc", ".docx", ".pdf"]
ARCHIVE_EXTENSIONS = [".zip"]


def set_registry_value(root, subkey, name, value):
    key = winreg.CreateKeyEx(root, subkey, 0, winreg.KEY_SET_VALUE)
    try:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
    finally:
        winreg.CloseKey(key)


def install_for_extension(extension, menu_key_name, menu_text, command, icon):
    base_key = fr"Software\Classes\SystemFileAssociations\{extension}\shell\{menu_key_name}"
    set_registry_value(winreg.HKEY_CURRENT_USER, base_key, "", menu_text)
    set_registry_value(winreg.HKEY_CURRENT_USER, base_key, "Icon", str(icon))
    set_registry_value(winreg.HKEY_CURRENT_USER, base_key + r"\command", "", command)


def install_for_directory(menu_key_name, menu_text, command, icon):
    base_key = fr"Software\Classes\Directory\shell\{menu_key_name}"
    set_registry_value(winreg.HKEY_CURRENT_USER, base_key, "", menu_text)
    set_registry_value(winreg.HKEY_CURRENT_USER, base_key, "Icon", str(icon))
    set_registry_value(winreg.HKEY_CURRENT_USER, base_key + r"\command", "", command)


def main():
    repo_dir = Path(__file__).resolve().parent
    handler_path = repo_dir / "context_menu_handler.py"

    # 直接使用运行本安装脚本的 Python 解释器（不再扫描本机所有解释器做依赖检测）。
    # 静默模式优先使用同目录的 pythonw.exe，避免右键点击时弹出黑色控制台窗口。
    python_exe = Path(sys.executable)
    pythonw = python_exe.parent / "pythonw.exe"
    python_path = pythonw if pythonw.exists() else python_exe
    print(f"使用 Python 解释器: {python_path}")
    print(f"  版本: {sys.version_info[0]}.{sys.version_info[1]}")

    command = f'"{python_path}" "{handler_path}" "%1"'
    overwrite_command = f'"{python_path}" "{handler_path}" "%1" --overwrite'

    # 文件右键菜单
    for extension in TARGET_EXTENSIONS:
        install_for_extension(extension, MENU_KEY_NAME, FILE_MENU_TEXT, command, python_path)
        install_for_extension(extension, OVERWRITE_MENU_KEY_NAME, FILE_OVERWRITE_MENU_TEXT, overwrite_command, python_path)

    # 文件夹右键菜单
    install_for_directory(MENU_KEY_NAME, DIR_MENU_TEXT, command, python_path)
    install_for_directory(OVERWRITE_MENU_KEY_NAME, DIR_OVERWRITE_MENU_TEXT, overwrite_command, python_path)

    # 压缩包右键菜单（使用 Python 内置 zipfile 解压，无需外部工具）
    for extension in ARCHIVE_EXTENSIONS:
        install_for_extension(extension, ARCHIVE_MENU_KEY_NAME, ARCHIVE_MENU_TEXT, command, python_path)

    print("\n右键菜单安装完成。")
    print("文件右键菜单:")
    for ext in TARGET_EXTENSIONS:
        print(f"  {ext} -> {FILE_MENU_TEXT}（含删除页眉）")
        print(f"  {ext} -> {FILE_OVERWRITE_MENU_TEXT}（含删除页眉）")
    print("文件夹右键菜单:")
    print(f"  文件夹 -> {DIR_MENU_TEXT}（含删除页眉）")
    print(f"  文件夹 -> {DIR_OVERWRITE_MENU_TEXT}（含删除页眉）")
    print("压缩包右键菜单:")
    for ext in ARCHIVE_EXTENSIONS:
        print(f"  {ext} -> {ARCHIVE_MENU_TEXT}（解压→去水印）")


if __name__ == "__main__":
    main()
    input("\n按回车键退出...")
