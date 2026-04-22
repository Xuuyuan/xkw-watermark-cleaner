import sys
import winreg
from pathlib import Path


MENU_TEXT = "清除学科网水印"
OVERWRITE_MENU_TEXT = "清除学科网水印（覆盖）"
MENU_KEY_NAME = "xkw-watermark-cleaner"
OVERWRITE_MENU_KEY_NAME = "xkw-watermark-cleaner-overwrite"
TARGET_EXTENSIONS = [".doc", ".docx", ".pdf"]


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


def main():
    repo_dir = Path(__file__).resolve().parent
    handler_path = repo_dir / "context_menu_handler.py"
    pythonw_path = Path(sys.executable).with_name("pythonw.exe")
    python_path = pythonw_path if pythonw_path.exists() else Path(sys.executable)

    command = f'"{python_path}" "{handler_path}" "%1"'
    overwrite_command = f'"{python_path}" "{handler_path}" "%1" --overwrite'

    for extension in TARGET_EXTENSIONS:
        install_for_extension(extension, MENU_KEY_NAME, MENU_TEXT, command)
        install_for_extension(extension, OVERWRITE_MENU_KEY_NAME, OVERWRITE_MENU_TEXT, overwrite_command)

    print("右键菜单安装完成。")
    print("支持文件类型: .doc .docx .pdf")
    print(f"菜单名称: {MENU_TEXT}")
    print(f"菜单名称: {OVERWRITE_MENU_TEXT}")


if __name__ == "__main__":
    main()
