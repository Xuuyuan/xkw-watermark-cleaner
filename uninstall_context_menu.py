import winreg


MENU_KEY_NAME = "xkw-watermark-cleaner"
TARGET_EXTENSIONS = [".doc", ".docx", ".pdf"]


def delete_tree(root, subkey):
    try:
        with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
            while True:
                try:
                    child = winreg.EnumKey(key, 0)
                    delete_tree(root, subkey + "\\" + child)
                except OSError:
                    break
        winreg.DeleteKey(root, subkey)
    except FileNotFoundError:
        pass


def main():
    for extension in TARGET_EXTENSIONS:
        subkey = fr"Software\Classes\SystemFileAssociations\{extension}\shell\{MENU_KEY_NAME}"
        delete_tree(winreg.HKEY_CURRENT_USER, subkey)

    print("右键菜单卸载完成。")


if __name__ == "__main__":
    main()
