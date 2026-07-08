# -*- mode: python ; coding: utf-8 -*-
import os

#
# 精简版 spec — tkinter GUI，无 PySide6
# 输出单 exe，约 10-15 MB
#

# 数据文件
datas = [
    ('config.json', '.'),
]

# 排除 PySide6 和所有不需要的模块
excludes = [
    'PySide6', 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets', 'shiboken6',
    'numpy', 'numpy.libs',
    'PIL', 'Pillow',
    'yaml', 'pyyaml',
    'curl_cffi', 'cffi',
    'certifi', 'requests', 'urllib3', 'httpx',
]

# tkinter 是内置库，不需要打包；但 hiddenimports 帮助 PyInstaller 找到它
hiddenimports = [
    'tkinter', 'tkinter.ttk', 'tkinter.filedialog',
    'tkinter.messagebox', 'tkinter.scrolledtext',
    'docx', 'fitz',
    'win32com', 'win32com.client',
    'clean_watermark', 'cleaner_config',
    'clean_watermark_docx', 'clean_watermark_pdf', 'clean_watermark_doc',
]

a = Analysis(
    ['xkw_gui_tk.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='xkw_simplified',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='xkw.ico' if os.path.exists('xkw.ico') else None,
)
