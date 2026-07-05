import os
import shutil
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
ARCHIVE_EXTENSIONS = [".zip", ".rar", ".7z"]


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


def check_extractors():
    """检查压缩包解压工具是否可用。返回 (found_list, missing_list)。
    found_list 每项为 (名称, 路径, 来源)，来源为 "PATH" / "环境变量" / "额外检测"。
    """
    found = []
    missing = []

    def _resolve(exe_names, env_var_names, known_paths):
        """三级查找：PATH → 自定义环境变量 → 已知安装路径。"""
        # 1) PATH
        for name in exe_names:
            resolved = shutil.which(name)
            if resolved:
                return resolved, "PATH"
        # 2) 自定义环境变量（如 WinRAR=..., Bandzip=...）
        for var_name in env_var_names:
            var_val = os.environ.get(var_name, "")
            if var_val:
                for name in exe_names:
                    candidate = Path(var_val) / name
                    if candidate.exists():
                        return str(candidate), "环境变量"
        # 3) 已知安装路径
        for p in known_paths:
            if p.exists():
                return str(p), "额外检测"
        return None, None

    # 检查 Bandizip（处理 .zip / .7z）
    bandi, src = _resolve(
        exe_names=["Bandizip.exe", "bz.exe"],
        env_var_names=["Bandzip", "Bandizip", "BANDIZIP"],
        known_paths=[
            Path(r"D:\My Program\Bandzip\Bandizip.exe"),
            Path(r"C:\Program Files\Bandizip\Bandizip.exe"),
            Path(r"C:\Program Files\Bandizip\bz.exe"),
            Path(r"D:\Program\Bandzip\Bandizip.exe"),
            Path(r"D:\Bandzip\Bandizip.exe"),
        ],
    )
    if bandi:
        found.append(("Bandizip (.zip/.7z)", bandi, src))
    else:
        missing.append("Bandizip (处理 .zip / .7z)")

    # 检查 WinRAR（处理 .rar）
    rar, src = _resolve(
        exe_names=["WinRAR.exe", "UnRAR.exe"],
        env_var_names=["WinRAR", "WINRAR", "WinRar"],
        known_paths=[
            Path(r"C:\Program Files\WinRAR\WinRAR.exe"),
            Path(r"C:\Program Files (x86)\WinRAR\WinRAR.exe"),
            Path(r"D:\My Program\WinRAR\WinRAR.exe"),
            Path(r"D:\Program\WinRAR\WinRAR.exe"),
            Path(r"D:\WinRAR\WinRAR.exe"),
        ],
    )
    if rar:
        found.append(("WinRAR (.rar)", rar, src))
    else:
        missing.append("WinRAR (处理 .rar)")

    return found, missing


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

    # 压缩包右键菜单 — 先检查解压工具
    found, missing = check_extractors()
    print("解压工具检测结果：")
    if found:
        for name, path, source in found:
            print(f"  ✓ {name}: {path}  [来源: {source}]")
    else:
        print("  （未检测到任何解压工具）")
    print()
    if missing:
        print("=" * 56)
        print("⚠ 警告：以下解压工具未在系统 PATH 中找到：")
        for m in missing:
            print(f"  - {m}")
        print()
        print("压缩包右键菜单仍会安装，但需手动配置 PATH 才能正常使用。")
        print()
        print("配置方法（以 Bandizip 为例）：")
        print("  1. 找到 Bandizip 安装目录（如 D:\\My Program\\Bandzip）")
        print("  2. 打开「系统属性」→「环境变量」（Win10及Win11可通过Windows徽标键+S/Q呼出搜索菜单搜索环境变量）")
        print("  3. 在「系统变量」中找到 Path，点击「编辑」")
        print("  4. 新增一条，填入 Bandizip 所在目录路径，确定保存")
        print("  5. 同理配置 WinRAR 目录（如 C:\\Program Files\\WinRAR）")
        print("  6. 重新打开终端或资源管理器即可生效")
        print("=" * 56)
        print()

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
