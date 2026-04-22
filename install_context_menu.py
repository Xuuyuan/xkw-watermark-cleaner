import sys
import winreg
from pathlib import Path


MENU_TEXT = "清除学科网水印"
MENU_KEY_NAME = "xkw-watermark-cleaner"
TARGET_EXTENSIONS = [".doc", ".docx", ".pdf"]


def set_registry_value(root, subkey, name, value):
    key = winreg.CreateKeyEx(root, subkey, 0, winreg.KEY_SET_VALUE)
    try:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
    finally:
        winreg.CloseKey(key)


def install_for_extension(extension, command):
    base_key = fr"Software\Classes\SystemFileAssociations\{extension}\shell\{MENU_KEY_NAME}"
    set_registry_value(winreg.HKEY_CURRENT_USER, base_key, "", MENU_TEXT)
    set_registry_value(winreg.HKEY_CURRENT_USER, base_key, "Icon", sys.executable)
    set_registry_value(winreg.HKEY_CURRENT_USER, base_key + r"\command", "", command)


def main():
    repo_dir = Path(__file__).resolve().parent
    handler_path = repo_dir / "context_menu_handler.py"
    pythonw_path = Path(sys.executable).with_name("pythonw.exe")
    python_path = pythonw_path if pythonw_path.exists() else Path(sys.executable)

    command = f'"{python_path}" "{handler_path}" "%1"'

    for extension in TARGET_EXTENSIONS:
        install_for_extension(extension, command)

    print("右键菜单安装完成。")
    print("支持文件类型: .doc .docx .pdf")
    print(f"菜单名称: {MENU_TEXT}")


if __name__ == "__main__":
    main()
