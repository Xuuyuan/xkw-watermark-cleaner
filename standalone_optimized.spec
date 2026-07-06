# -*- mode: python ; coding: utf-8 -*-
"""独立版精简打包 spec — onedir + 排除无用模块 + 构建后清理"""
import os
from pathlib import Path

PROJECT_DIR = Path(os.environ.get('PROJECT_DIR', os.getcwd()))

EXCLUDE_MODULES = [
    # PySide6 不需要的模块
    'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
    'PySide6.QtWebEngineQuick', 'PySide6.QtQuick', 'PySide6.QtQml',
    'PySide6.QtDesigner', 'PySide6.QtQuick3D', 'PySide6.QtQuickWidgets',
    'PySide6.QtCharts', 'PySide6.QtDataVisualization',
    'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets',
    'PySide6.QtBluetooth', 'PySide6.QtPositioning', 'PySide6.QtLocation',
    'PySide6.QtSensors', 'PySide6.QtSerialPort', 'PySide6.QtSerialBus',
    'PySide6.QtSql', 'PySide6.QtTest', 'PySide6.QtUiTools',
    'PySide6.QtWebChannel', 'PySide6.QtWebSockets', 'PySide6.QtXml',
    'PySide6.QtPrintSupport', 'PySide6.QtSvgWidgets',
    'PySide6.Qt3DCore', 'PySide6.Qt3DRender', 'PySide6.Qt3DInput',
    'PySide6.Qt3DLogic', 'PySide6.Qt3DAnimation', 'PySide6.Qt3DExtras',
    'PySide6.QtConcurrent', 'PySide6.QtHelp', 'PySide6.QtHttpServer',
    'PySide6.QtRemoteObjects', 'PySide6.QtScxml', 'PySide6.QtStateMachine',
    'PySide6.QtOpenGL', 'PySide6.QtOpenGLWidgets',
    'PySide6.QtPdf', 'PySide6.QtPdfWidgets',
    'PySide6.QtNetwork',
    # 网络/HTTP 库（GUI 不联网）
    'curl_cffi', 'curl_cffi.cffi', 'curl_cffi.ffi',
    'requests', 'urllib3', 'certifi', 'chardet', 'idna',
    # YAML（不用）
    'yaml', 'pyyaml',
    # 标准库不需要的
    'tkinter', 'unittest', 'pydoc', 'doctest',
    # win32ui MFC 界面不需要（我们只用 win32com.client）
    'win32ui', 'win32uiole', 'pywin',
]

a = Analysis(
    ['xkw_gui.py'],
    pathex=[str(PROJECT_DIR)],
    datas=[
        ('config.json', '.'),
        ('clean_watermark.py', '.'),
        ('clean_watermark_doc.py', '.'),
        ('clean_watermark_docx.py', '.'),
        ('clean_watermark_pdf.py', '.'),
        ('cleaner_config.py', '.'),
        ('context_menu_handler.py', '.'),
    ],
    hiddenimports=[
        'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets',
        'docx', 'fitz', 'win32com.client',
    ],
    excludes=EXCLUDE_MODULES,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='xkw_standalone',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=['vcruntime140.dll', 'python3.dll', 'VCRUNTIME140_1.dll'],
    upx_flags='--best --lzma',
    console=False,
    disable_windowed_traceback=False,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=['vcruntime140.dll', 'python3.dll', 'VCRUNTIME140_1.dll'],
    upx_flags='--best --lzma',
    name='xkw_standalone',
)
