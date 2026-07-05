#!/usr/bin/env python3
"""打包在线版 zip：前端 dist + 后端 dist + backend node_modules + config + 启动脚本"""
import os
import zipfile
import shutil
from pathlib import Path

WEB_DIR = Path(__file__).resolve().parent.parent
ZIP_PATH = WEB_DIR / "学科网水印清理工具_在线版.zip"

# 删除旧 zip
if ZIP_PATH.exists():
    ZIP_PATH.unlink()

# 收集要打包的文件
files_to_zip = []

# 1. 前端构建产物
frontend_dist = WEB_DIR / "frontend" / "dist"
if frontend_dist.exists():
    for root, dirs, files in os.walk(frontend_dist):
        for f in files:
            full = Path(root) / f
            rel = Path("frontend/dist") / full.relative_to(frontend_dist)
            files_to_zip.append((full, rel))

# 2. 后端构建产物
backend_dist = WEB_DIR / "backend" / "dist"
if backend_dist.exists():
    for root, dirs, files in os.walk(backend_dist):
        for f in files:
            full = Path(root) / f
            rel = Path("backend/dist") / full.relative_to(backend_dist)
            files_to_zip.append((full, rel))

# 3. 后端 node_modules（生产依赖）
backend_nm = WEB_DIR / "backend" / "node_modules"
if backend_nm.exists():
    for root, dirs, files in os.walk(backend_nm):
        # 跳过 .cache, .bin 等不必要的目录
        dirs[:] = [d for d in dirs if d not in ('.cache', '.bin', '.package-lock.json')]
        for f in files:
            full = Path(root) / f
            rel = Path("backend/node_modules") / full.relative_to(backend_nm)
            files_to_zip.append((full, rel))

# 4. 后端 package.json
pkg_json = WEB_DIR / "backend" / "package.json"
if pkg_json.exists():
    files_to_zip.append((pkg_json, Path("backend/package.json")))

# 5. config.json
config_json = WEB_DIR / "backend" / "config.json"
if config_json.exists():
    files_to_zip.append((config_json, Path("backend/config.json")))

# 6. 启动脚本
start_bat = WEB_DIR / "start_web.bat"
if start_bat.exists():
    files_to_zip.append((start_bat, Path("启动服务.bat")))

# 7. README
readme = WEB_DIR / "README.md"
if readme.exists():
    files_to_zip.append((readme, Path("README.md")))

# 写 zip
print(f"打包 {len(files_to_zip)} 个文件...")
with zipfile.ZipFile(ZIP_PATH, 'w', zipfile.ZIP_DEFLATED) as zf:
    for src, rel in files_to_zip:
        zf.write(src, str(rel).replace('\\', '/'))

size_mb = ZIP_PATH.stat().st_size / 1024 / 1024
print(f"\n打包完成: {ZIP_PATH}")
print(f"大小: {size_mb:.1f} MB")
