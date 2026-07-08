import os
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


def install_for_extension(extension, menu_key_name, menu_text, command):
    base_key = fr"Software\Classes\SystemFileAssociations\{extension}\shell\{menu_key_name}"
    set_registry_value(winreg.HKEY_CURRENT_USER, base_key, "", menu_text)
    set_registry_value(winreg.HKEY_CURRENT_USER, base_key, "Icon", sys.executable)
    set_registry_value(winreg.HKEY_CURRENT_USER, base_key + r"\command", "", command)


def install_for_directory(menu_key_name, menu_text, command):
    base_key = fr"Software\Classes\Directory\shell\{menu_key_name}"
    set_registry_value(winreg.HKEY_CURRENT_USER, base_key, "", menu_text)
    set_registry_value(winreg.HKEY_CURRENT_USER, base_key, "Icon", sys.executable)
    set_registry_value(winreg.HKEY_CURRENT_USER, base_key + r"\command", "", command)


def main():
    repo_dir = Path(__file__).resolve().parent
    handler_path = repo_dir / "context_menu_handler.py"
    pythonw_path = Path(sys.executable).with_name("pythonw.exe")
    python_path = pythonw_path if pythonw_path.exists() else Path(sys.executable)

    command = f'"{python_path}" "{handler_path}" "%1"'
    overwrite_command = f'"{python_path}" "{handler_path}" "%1" --overwrite'

    # 文件右键菜单
    for extension in TARGET_EXTENSIONS:
        install_for_extension(extension, MENU_KEY_NAME, FILE_MENU_TEXT, command)
        install_for_extension(extension, OVERWRITE_MENU_KEY_NAME, FILE_OVERWRITE_MENU_TEXT, overwrite_command)

    # 文件夹右键菜单
    install_for_directory(MENU_KEY_NAME, DIR_MENU_TEXT, command)
    install_for_directory(OVERWRITE_MENU_KEY_NAME, DIR_OVERWRITE_MENU_TEXT, overwrite_command)

    # 压缩包右键菜单（使用 Python 内置 zipfile 解压，无需外部工具）
    for extension in ARCHIVE_EXTENSIONS:
        install_for_extension(extension, ARCHIVE_MENU_KEY_NAME, ARCHIVE_MENU_TEXT, command)

    print("右键菜单安装完成。")
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
