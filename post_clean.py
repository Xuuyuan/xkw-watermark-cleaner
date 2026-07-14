# -*- coding: utf-8 -*-
"""Post-build cleanup: remove unnecessary files to reduce size."""
import shutil
from pathlib import Path

BODY_ROOT = Path(__file__).resolve().parent / "body"
# PyInstaller 6.x 默认把依赖放进 body/_internal；若 spec 里设了 contents_directory='.'
# 则为扁平布局（dll 直接散在 body/ 根，无 _internal 子目录）。两种情况都兼容：
# 优先使用 _internal，不存在则回退到 body 根目录。
BODY = BODY_ROOT / "_internal" if (BODY_ROOT / "_internal").exists() else BODY_ROOT

# Files to delete (both in _internal/ and _internal/PySide6/)
DELETE_FILES = [
    # QML/Quick - not used
    "Qt6Quick.dll", "Qt6Qml.dll", "Qt6QmlModels.dll",
    "Qt6QmlMeta.dll", "Qt6QmlWorkerScript.dll",
    "Qt6Quick3D.dll", "Qt6Quick3DRuntimeRender.dll",
    # PDF - not used
    "Qt6Pdf.dll", "Qt6PdfWidgets.dll",
    # VirtualKeyboard - not used
    "Qt6VirtualKeyboard.dll",
    # opengl32sw - software rendering fallback, not needed with GPU
    "opengl32sw.dll",
    # Network - GUI does not use network
    "Qt6Network.dll", "Qt6NetworkAuth.dll",
    # SVG Widgets - not used
    "Qt6SvgWidgets.dll", "Qt6Svg.dll",
    # ShaderTools - only for Quick
    "Qt6ShaderTools.dll",
    # Test/UiTools
    "Qt6Test.dll", "Qt6UiTools.dll",
    # Qt6OpenGL - not used, QtWidgets has its own renderer
    "Qt6OpenGL.dll",
    "Qt6OpenGLWidgets.dll",
]

DELETE_DIRS = [
    "translations",       # translation files
    "resources",          # Qt resources
    "qml",                # QML runtime
    "metatypes",          # meta types
    "examples",           # examples
    "designer",           # Qt Designer
    "help",               # Qt Help
    # unnecessary plugins
    "plugins/generic",
    "plugins/platforminputcontexts",
    "plugins/scenegraph",
    "plugins/renderers",
    "plugins/styles",
    # win32 MFC
    "Pythonwin",          # win32ui MFC UI
    # unnecessary Python packages
    "curl_cffi",
    "curl_cffi.libs",
    "yaml",
    "pyyaml",
    "certifi",
    "requests",
    "urllib3",
    "chardet",
    "idna",
    # numpy - PyMuPDF optional dependency, we only use text API
    "numpy",
    "numpy.libs",
    "numpy-2.3.1.dist-info",
    # PIL - python-docx and fitz basic functions don't need it
    "PIL",
]

# imageformats: keep only common jpeg/gif/ico/png/bmp, remove others
IMAGEFORMATS_DELETE = [
    "qpdf.dll",
    "qsvg.dll",
    "qtga.dll",
    "qtiff.dll",
    "qwbmp.dll",
    "qwebp.dll",
    "qjp2.dll",
    "qicns.dll",
    "qtga.dll",
]


def delete_files(directory, patterns):
    count = 0
    for p in directory.rglob("*"):
        if p.is_file() and p.name in patterns:
            try:
                p.unlink()
                count += 1
            except Exception:
                pass
    return count


def delete_dirs(directory, dir_names):
    count = 0
    for name in dir_names:
        for p in directory.rglob(name):
            if p.is_dir():
                try:
                    shutil.rmtree(p, ignore_errors=True)
                    count += 1
                except Exception:
                    pass
                break
    return count


if not BODY.exists():
    print(f"ERROR: {BODY} not found")
    exit(1)

print("=== Cleaning _internal/ ===")
f1 = delete_files(BODY, DELETE_FILES)
d1 = delete_dirs(BODY, DELETE_DIRS)
print(f"  deleted {f1} files, {d1} dirs")

# PySide6 directory
pyside = BODY / "PySide6"
if pyside.exists():
    print("\n=== Cleaning _internal/PySide6/ ===")
    f2 = delete_files(pyside, DELETE_FILES)
    d2 = delete_dirs(pyside, DELETE_DIRS)
    print(f"  deleted {f2} files, {d2} dirs")

    # imageformats cleanup
    imgfmt = pyside / "plugins" / "imageformats"
    if imgfmt.exists():
        print("\n=== Cleaning imageformats plugins ===")
        f3 = delete_files(imgfmt, IMAGEFORMATS_DELETE)
        print(f"  deleted {f3} imageformat plugins")

# Final size
total = sum(f.stat().st_size for f in BODY.rglob("*") if f.is_file())
print(f"\nFinal _internal size: {total/1048576:.1f} MB")
