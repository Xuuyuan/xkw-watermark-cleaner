#!/usr/bin/env python3
"""
学科网水印清理工具 - 图形用户界面 (PySide6)
左侧导航 + 右侧主内容区。
"""

import io
import json
import os
import shutil
import subprocess
import sys
import contextlib
import time
import traceback
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QSize, QRect
from PySide6.QtGui import QFont, QColor, QPalette, QAction, QIcon, QFontDatabase
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTreeWidget, QTreeWidgetItem, QTextEdit,
    QProgressBar, QCheckBox, QStackedWidget, QFrame, QFileDialog,
    QMessageBox, QScrollArea, QGroupBox, QLineEdit, QHeaderView,
    QSplitter, QSizePolicy, QGridLayout,
)

# 确保项目根目录在 sys.path 中
PROJECT_DIR = Path(__file__).resolve().parent


def _resource_path(rel: str) -> str:
    """解析资源路径：打包后优先用 PyInstaller 的 _MEIPASS，否则用源码目录。"""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, rel)
    return str(PROJECT_DIR / rel)
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from clean_watermark import clean_one_file, clean_one_file_overwrite, collect_files
from cleaner_config import load_config, DEFAULT_METADATA_KEYWORDS
from context_menu_handler import _strip_marker, MARKER_FIELD

# ─── 常量 ─────────────────────────────────────────────
ARCHIVE_EXTENSIONS = {".zip"}
DOC_EXTENSIONS = {".doc", ".docx", ".pdf"}
SUPPORTED_EXTS_STR = ".doc  .docx  .pdf  .zip"

# 风格配色
PRIMARY = "#1677FF"
PRIMARY_HOVER = "#4096FF"
PRIMARY_LIGHT = "#E6F4FF"
BG_MAIN = "#F5F5F5"
BG_CARD = "#FFFFFF"
BG_SIDEBAR = "#FAFAFA"
TEXT_PRIMARY = "#1F1F1F"
TEXT_SECONDARY = "#666666"
TEXT_HINT = "#BFBFBF"
BORDER = "#E8E8E8"
SUCCESS_COLOR = "#52C41A"
WARNING_COLOR = "#FAAD14"
ERROR_COLOR = "#FF4D4F"


def _fmt_size(num_bytes):
    """把字节数格式化为易读字符串（B / KB / MB）。"""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / 1024 / 1024:.2f} MB"


class _GuiLogWriter(io.TextIOBase):
    """把 clean_* 函数内部的 print 实时转发到 GUI 日志面板。

    这些 print 在 GUI 模式下原本会进入 stdout 被丢弃；这里把它们按行缓冲，
    作为「子步骤」缩进显示在日志面板里，让用户看清每个文件到底清了什么。
    """

    def __init__(self, emit):
        self._emit = emit
        self._buf = ""

    def write(self, text):
        self._buf += text
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            if line.strip():
                self._emit("    " + line.rstrip(), TEXT_SECONDARY)
        return len(text)

    def flush(self):
        if self._buf.strip():
            self._emit("    " + self._buf.rstrip(), TEXT_SECONDARY)
        self._buf = ""


# ─── 全局样式 ─────────────────────────────────────────
GLOBAL_STYLE = f"""
QMainWindow {{
    background-color: {BG_MAIN};
}}
QWidget {{
    font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
    font-size: 13px;
    color: {TEXT_PRIMARY};
}}
QTreeWidget {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    background-color: {BG_CARD};
    outline: none;
    alternate-background-color: {BG_MAIN};
}}
QTreeWidget::item {{
    padding: 4px 0px;
    min-height: 28px;
}}
QTreeWidget::item:selected {{
    background-color: {PRIMARY_LIGHT};
    color: {TEXT_PRIMARY};
}}
QTreeWidget::item:hover {{
    background-color: #F0F5FF;
}}
QHeaderView::section {{
    background-color: {BG_MAIN};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 6px 4px;
    font-weight: bold;
    color: {TEXT_SECONDARY};
}}
QTextEdit {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    background-color: {BG_CARD};
    padding: 8px;
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 12px;
}}
QProgressBar {{
    border: none;
    border-radius: 4px;
    background-color: {BORDER};
    height: 6px;
    text-align: center;
    font-size: 0px;
}}
QProgressBar::chunk {{
    background-color: {PRIMARY};
    border-radius: 4px;
}}
QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: 8px;
}}
QScrollBar::handle:vertical {{
    background: #CCCCCC;
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: #AAAAAA;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    border: none;
    background: none;
}}
QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    margin-top: 10px;
    padding-top: 16px;
    background-color: {BG_CARD};
    font-weight: bold;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}}
QLineEdit {{
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 4px 8px;
}}
QLineEdit:focus {{
    border-color: {PRIMARY};
}}
QSplitter::handle {{
    background-color: {BORDER};
    width: 1px;
}}
"""


# ─── 导航按钮样式 ─────────────────────────────────────
NAV_BTN_NORMAL = f"""
QPushButton {{
    text-align: left;
    padding: 10px 16px;
    border: none;
    border-radius: 6px;
    background-color: transparent;
    color: {TEXT_SECONDARY};
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {PRIMARY_LIGHT};
    color: {PRIMARY};
}}
"""

NAV_BTN_ACTIVE = f"""
QPushButton {{
    text-align: left;
    padding: 10px 16px;
    border: none;
    border-radius: 6px;
    background-color: {PRIMARY_LIGHT};
    color: {PRIMARY};
    font-size: 13px;
    font-weight: bold;
}}
"""


# ─── 主按钮样式 ───────────────────────────────────────
PRIMARY_BTN = f"""
QPushButton {{
    background-color: {PRIMARY};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 24px;
    font-size: 14px;
    font-weight: bold;
}}
QPushButton:hover {{
    background-color: {PRIMARY_HOVER};
}}
QPushButton:pressed {{
    background-color: #0958D9;
}}
QPushButton:disabled {{
    background-color: #91CAFF;
    color: #E0E0E0;
}}
"""

SECONDARY_BTN = f"""
QPushButton {{
    background-color: transparent;
    color: {PRIMARY};
    border: 1px solid {PRIMARY};
    border-radius: 6px;
    padding: 6px 16px;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {PRIMARY_LIGHT};
}}
"""

LINK_BTN = f"""
QPushButton {{
    background-color: transparent;
    color: {PRIMARY};
    border: none;
    padding: 4px 8px;
    font-size: 13px;
}}
QPushButton:hover {{
    color: {PRIMARY_HOVER};
}}
"""

CANCEL_BTN = f"""
QPushButton {{
    background-color: transparent;
    color: {TEXT_SECONDARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
}}
QPushButton:hover {{
    border-color: #AAAAAA;
    color: {TEXT_PRIMARY};
}}
"""


# ─── Drop Zone 样式 ───────────────────────────────────
DROP_ZONE_STYLE = f"""
QFrame#dropZone {{
    border: 2px dashed {BORDER};
    border-radius: 12px;
    background-color: {BG_CARD};
}}
QFrame#dropZone:hover {{
    border-color: {PRIMARY};
    background-color: {PRIMARY_LIGHT};
}}
"""


# ─── 工作线程 ─────────────────────────────────────────
class ProcessWorker(QThread):
    """后台处理线程，不阻塞 UI。"""
    log_signal = Signal(str, str)            # message, color
    progress_signal = Signal(int, int)       # current, total
    file_status_signal = Signal(str, str, str)  # path, status, color
    done_signal = Signal(int, int)           # success, fail

    def __init__(self, docs, archives, overwrite, remove_headers, flatten=True,
                 folder_roots=None, strip_marker=True):
        super().__init__()
        self.docs = docs
        self.archives = archives
        self.overwrite = overwrite
        self.remove_headers = remove_headers
        self.flatten = flatten
        self.folder_roots = folder_roots or []
        self.strip_marker = strip_marker

    def run(self):
        # 把 clean_* 内部的 print 实时转发到 GUI 日志面板（作为子步骤显示）
        self._log_writer = _GuiLogWriter(self.log_signal.emit)
        success = 0
        fail = 0
        total = len(self.docs) + len(self.archives)
        current = 0
        t_total_start = time.time()

        # 处理普通文档
        for doc_path in self.docs:
            current += 1
            self.progress_signal.emit(current, total)
            self.file_status_signal.emit(str(doc_path), "处理中...", PRIMARY)
            self.log_signal.emit(f"[{datetime.now():%H:%M:%S}] 开始处理: {doc_path}", TEXT_SECONDARY)

            try:
                size_in = os.path.getsize(doc_path) if os.path.exists(doc_path) else 0
                t0 = time.time()
                with contextlib.redirect_stdout(self._log_writer):
                    if self.overwrite:
                        output = clean_one_file_overwrite(str(doc_path),
                                                           remove_all_header=self.remove_headers)
                    else:
                        output = clean_one_file(str(doc_path),
                                                remove_all_header=self.remove_headers)
                self._log_writer.flush()
                elapsed = time.time() - t0
                size_out = os.path.getsize(output) if output and os.path.exists(output) else 0
                self.log_signal.emit(
                    f"[{datetime.now():%H:%M:%S}] 处理完成: {output}  "
                    f"[输入 {_fmt_size(size_in)} → 输出 {_fmt_size(size_out)}，耗时 {elapsed:.2f}s]",
                    SUCCESS_COLOR)
                self.file_status_signal.emit(str(doc_path), "已完成", SUCCESS_COLOR)
                # 文件名含 MARKER_FIELD：去掉该字段并重命名（不删文件）
                had_marker = (MARKER_FIELD in Path(doc_path).name) or (MARKER_FIELD in Path(output).name)
                if self.strip_marker:
                    _strip_marker(output)
                    if Path(doc_path).exists() and Path(doc_path).absolute() != Path(output).absolute():
                        _strip_marker(doc_path)
                if had_marker and self.strip_marker:
                    self.file_status_signal.emit(str(doc_path), "已重命名", WARNING_COLOR)
                success += 1
            except Exception as exc:
                self._log_writer.flush()
                self.log_signal.emit(
                    f"[{datetime.now():%H:%M:%S}] 处理失败: {doc_path}\n原因: {exc}", ERROR_COLOR)
                self.file_status_signal.emit(str(doc_path), "失败", ERROR_COLOR)
                fail += 1

        # 处理压缩包
        for archive_path in self.archives:
            current += 1
            self.progress_signal.emit(current, total)
            self.file_status_signal.emit(str(archive_path), "处理中...", PRIMARY)
            self.log_signal.emit(f"[{datetime.now():%H:%M:%S}] 开始处理压缩包: {archive_path}",
                                 TEXT_SECONDARY)

            try:
                self._process_single_archive(archive_path, flatten=self.flatten,
                                             strip_marker=self.strip_marker)
                self.file_status_signal.emit(str(archive_path), "已完成", SUCCESS_COLOR)
                # 覆盖模式：删除原始压缩包；文件名含『精品解析：』字段（非覆盖）：重命名去掉字段
                if self.overwrite:
                    if Path(archive_path).exists():
                        try:
                            Path(archive_path).unlink()
                            self.log_signal.emit(
                                f"[{datetime.now():%H:%M:%S}] 已删除原始压缩包: {Path(archive_path).name}",
                                WARNING_COLOR)
                            self.file_status_signal.emit(str(archive_path), "已删除", WARNING_COLOR)
                        except Exception as exc:
                            self.log_signal.emit(
                                f"[{datetime.now():%H:%M:%S}] 删除原始压缩包失败: {Path(archive_path).name} ({exc})",
                                ERROR_COLOR)
                elif self.strip_marker and MARKER_FIELD in Path(archive_path).name:
                    renamed = _strip_marker(archive_path)
                    if Path(renamed).name != Path(archive_path).name:
                        self.log_signal.emit(
                            f"[{datetime.now():%H:%M:%S}] 文件名含『{MARKER_FIELD}』，已重命名为: {Path(renamed).name}",
                            WARNING_COLOR)
                        self.file_status_signal.emit(str(archive_path), "已重命名", WARNING_COLOR)
                success += 1
            except Exception as exc:
                self.log_signal.emit(
                    f"[{datetime.now():%H:%M:%S}] 压缩包处理失败: {archive_path}\n原因: {exc}",
                    ERROR_COLOR)
                self.file_status_signal.emit(str(archive_path), "失败", ERROR_COLOR)
                fail += 1

        total_elapsed = time.time() - t_total_start
        # 平铺模式：把用户添加的文件夹内的子文件夹内容整体上移到顶层文件夹
        if self.flatten and self.folder_roots:
            from context_menu_handler import flatten_subfolders
            for root in self.folder_roots:
                try:
                    flatten_subfolders(Path(root))
                except Exception as exc:
                    self.log_signal.emit(
                        f"[{datetime.now():%H:%M:%S}] 平铺子文件夹失败: {root} ({exc})", ERROR_COLOR)
        self.log_signal.emit(
            f"\n全部处理完成！成功 {success}，失败 {fail}，总耗时 {total_elapsed:.1f}s",
            SUCCESS_COLOR if fail == 0 else WARNING_COLOR)
        self.done_signal.emit(success, fail)

    def _process_single_archive(self, archive_path: Path, flatten=False, strip_marker=True):
        from context_menu_handler import (extract_archive, find_archives_in_dir,
                                          _strip_marker, _strip_marker_in_tree, MARKER_FIELD)

        archive_path = Path(archive_path).absolute()
        parent = archive_path.parent
        stem = archive_path.stem
        # 平铺模式：先解压到临时子文件夹，清理完再整体平铺到 parent（压缩包所在文件夹）
        extract_root = (parent / f"_xkw_extract_{stem}") if flatten else (parent / stem)

        # 解压
        extract_archive(archive_path, extract_root)
        self.log_signal.emit(f"[{datetime.now():%H:%M:%S}] 解压完成: {archive_path.name}",
                             SUCCESS_COLOR)

        # 递归解压嵌套
        while True:
            nested = find_archives_in_dir(extract_root)
            if not nested:
                break
            self.log_signal.emit(f"[{datetime.now():%H:%M:%S}] 发现 {len(nested)} 个嵌套压缩包",
                                 WARNING_COLOR)
            for na in nested:
                nested_dest = na.parent / na.stem
                extract_archive(na, nested_dest)
                na.unlink()
                self.log_signal.emit(
                    f"[{datetime.now():%H:%M:%S}] 已解压并删除嵌套包: {na.name}", SUCCESS_COLOR)
                for item in nested_dest.iterdir():
                    shutil.move(str(item), str(extract_root / item.name))
                    item_type = "文件夹" if (extract_root / item.name).is_dir() else "文件"
                    self.log_signal.emit(
                        f"[{datetime.now():%H:%M:%S}] 已平铺: {na.name} -> {item.name} ({item_type})")
                try:
                    nested_dest.rmdir()
                    self.log_signal.emit(
                        f"[{datetime.now():%H:%M:%S}] 已删除空目录: {nested_dest.name}")
                except Exception:
                    pass

        # 水印清理
        self.log_signal.emit(f"[{datetime.now():%H:%M:%S}] 开始水印清理: {extract_root}",
                             TEXT_SECONDARY)
        files = collect_files([extract_root], recursive=True)
        self.log_signal.emit(f"[{datetime.now():%H:%M:%S}] 发现 {len(files)} 个待处理文件",
                             TEXT_SECONDARY)

        for fp in files:
            size_in = os.path.getsize(fp) if os.path.exists(fp) else 0
            t0 = time.time()
            try:
                with contextlib.redirect_stdout(self._log_writer):
                    clean_one_file_overwrite(str(fp), remove_all_header=self.remove_headers)
                self._log_writer.flush()
                elapsed = time.time() - t0
                self.log_signal.emit(
                    f"[{datetime.now():%H:%M:%S}] 处理完成: {fp}  "
                    f"[输入 {_fmt_size(size_in)}，耗时 {elapsed:.2f}s]",
                    SUCCESS_COLOR)
            except Exception as exc:
                self._log_writer.flush()
                self.log_signal.emit(f"[{datetime.now():%H:%M:%S}] 处理失败: {fp} ({exc})",
                                     ERROR_COLOR)

        # 若开启去字段，且解压根目录名带『精品解析：』，先把根目录名也去掉，
        # 避免解压出的文件夹仍叫「精品解析：x」而原压缩包已改名「x.zip」的不一致。
        if strip_marker and MARKER_FIELD in extract_root.name:
            extract_root = _strip_marker(extract_root)

        # 递归去除解压目录树内所有文件/文件夹名里的『精品解析：』字段（兜底）
        if strip_marker:
            _strip_marker_in_tree(extract_root)
            self.log_signal.emit(
                f"[{datetime.now():%H:%M:%S}] 已清理目录树中的『精品解析：』字段: {extract_root.name}",
                TEXT_SECONDARY)

        # 平铺模式：清理后把内容整体移动到压缩包所在文件夹
        if flatten:
            for item in list(extract_root.iterdir()):
                target = parent / item.name
                try:
                    if target.exists():
                        # 同名文件已存在（通常为文件夹内原有零散文件）：改名并入，避免覆盖已处理内容
                        renamed = parent / f"{stem}__{item.name}"
                        shutil.move(str(item), str(renamed))
                        item_type = "文件夹" if renamed.is_dir() else "文件"
                        self.log_signal.emit(
                            f"[{datetime.now():%H:%M:%S}] 已平铺(改名防冲突): {item.name} -> {renamed.name} ({item_type})")
                    else:
                        shutil.move(str(item), str(target))
                        item_type = "文件夹" if target.is_dir() else "文件"
                        self.log_signal.emit(
                            f"[{datetime.now():%H:%M:%S}] 已平铺到文件夹: {item.name} ({item_type})")
                except Exception as exc:
                    self.log_signal.emit(
                        f"[{datetime.now():%H:%M:%S}] 平铺失败: {item.name} ({exc})", ERROR_COLOR)
            try:
                extract_root.rmdir()
                self.log_signal.emit(
                    f"[{datetime.now():%H:%M:%S}] 已删除临时解压目录: {extract_root.name}")
            except Exception:
                pass

        self.log_signal.emit(f"[{datetime.now():%H:%M:%S}] 压缩包处理完成: {archive_path.name}",
                             SUCCESS_COLOR)


# ─── 主窗口 ───────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("学科网水印清理工具")
        self.resize(1020, 700)
        self.setMinimumSize(820, 560)

        # 数据
        self.config = load_config()
        self.file_paths = {}          # {tree_key: Path}
        self.added_folders = set()    # 用户「选择文件夹」添加的顶层文件夹（用于平铺子文件夹）
        self.is_processing = False
        self._row_counter = 0

        self._build_ui()

    # ── 构建 UI ────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── 顶部 Header ──
        header = QFrame()
        header.setFixedHeight(56)
        header.setStyleSheet(f"background-color: {BG_CARD}; border-bottom: 1px solid {BORDER};")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)

        title = QLabel("学科网水印清理工具")
        title.setStyleSheet(f"""
            font-size: 16px; font-weight: bold; color: {TEXT_PRIMARY}; border: none; background: transparent;
        """)
        subtitle = QLabel("支持 DOC / DOCX / PDF 水印清理，含 ZIP 压缩包批量处理")
        subtitle.setStyleSheet(f"font-size: 10px; color: {TEXT_SECONDARY}; border: none; background: transparent; padding-left: 6px;")
        version = QLabel("v2.1")
        version.setStyleSheet(f"font-size: 10px; color: {TEXT_SECONDARY}; border: none; background: transparent;")

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        header_layout.addStretch()
        header_layout.addWidget(version)
        root_layout.addWidget(header)

        # ── 主体：侧边栏 + Stack ──
        body = QWidget()
        body.setStyleSheet(f"background-color: {BG_MAIN};")
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # 左侧导航
        sidebar = QFrame()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet(f"background-color: {BG_SIDEBAR}; border-right: 1px solid {BORDER};")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(8, 12, 8, 12)
        sidebar_layout.setSpacing(4)

        self.nav_home = QPushButton("  🏠  首页")
        self.nav_settings = QPushButton("  ⚙  设置")
        self.nav_about = QPushButton("  ℹ  关于")
        for btn in [self.nav_home, self.nav_settings, self.nav_about]:
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(40)
            btn.setStyleSheet(NAV_BTN_NORMAL)
            sidebar_layout.addWidget(btn)

        self.nav_home.clicked.connect(lambda: self._switch_page(0))
        self.nav_settings.clicked.connect(lambda: self._switch_page(1))
        self.nav_about.clicked.connect(lambda: self._switch_page(2))

        sidebar_layout.addStretch()

        # Stack 页面
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background-color: {BG_MAIN};")
        self.stack.addWidget(self._build_home_page())
        self.stack.addWidget(self._build_settings_page())
        self.stack.addWidget(self._build_about_page())

        body_layout.addWidget(sidebar)
        body_layout.addWidget(self.stack, stretch=1)
        root_layout.addWidget(body, stretch=1)

        # ── 底部状态栏 ──
        status_bar = QFrame()
        status_bar.setFixedHeight(32)
        status_bar.setStyleSheet(f"background-color: {BG_CARD}; border-top: 1px solid {BORDER};")
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(16, 0, 16, 0)
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet(f"font-size: 10px; color: {TEXT_SECONDARY}; border: none; background: transparent;")
        status_layout.addWidget(self.status_label)
        root_layout.addWidget(status_bar)

        self._switch_page(0)

    # ── 首页 ───────────────────────────────────────────
    def _build_home_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 16, 20, 12)
        layout.setSpacing(8)

        # 拖放区
        drop_zone = QFrame()
        drop_zone.setObjectName("dropZone")
        drop_zone.setAcceptDrops(True)
        drop_zone.dragEnterEvent = self._drag_enter
        drop_zone.dragMoveEvent = self._drag_enter
        drop_zone.dropEvent = self._drop_event
        drop_zone.setStyleSheet(DROP_ZONE_STYLE)
        drop_zone.setMinimumHeight(120)
        drop_zone.setMaximumHeight(140)
        drop_layout = QVBoxLayout(drop_zone)
        drop_layout.setAlignment(Qt.AlignCenter)

        drop_icon = QLabel("📂")
        drop_icon.setStyleSheet("font-size: 28px; border: none; background: transparent;")
        drop_icon.setAlignment(Qt.AlignCenter)
        drop_text = QLabel("将文件或文件夹拖放到此处")
        drop_text.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {TEXT_PRIMARY}; border: none; background: transparent;")
        drop_text.setAlignment(Qt.AlignCenter)
        drop_hint = QLabel(f"支持格式：{SUPPORTED_EXTS_STR}")
        drop_hint.setStyleSheet(f"font-size: 10px; color: {TEXT_HINT}; border: none; background: transparent;")
        drop_hint.setAlignment(Qt.AlignCenter)

        btn_row = QWidget()
        btn_row.setStyleSheet("background: transparent;")
        btn_row_layout = QHBoxLayout(btn_row)
        btn_row_layout.setAlignment(Qt.AlignCenter)
        btn_row_layout.setContentsMargins(0, 0, 0, 0)
        btn_file = QPushButton("选择文件")
        btn_file.setStyleSheet(SECONDARY_BTN)
        btn_file.setCursor(Qt.PointingHandCursor)
        btn_file.clicked.connect(self._select_files)
        btn_folder = QPushButton("选择文件夹")
        btn_folder.setStyleSheet(SECONDARY_BTN)
        btn_folder.setCursor(Qt.PointingHandCursor)
        btn_folder.clicked.connect(self._select_folder)
        btn_row_layout.addWidget(btn_file)
        btn_row_layout.addWidget(btn_folder)

        drop_layout.addWidget(drop_icon)
        drop_layout.addWidget(drop_text)
        drop_layout.addWidget(drop_hint)
        drop_layout.addWidget(btn_row)
        layout.addWidget(drop_zone)

        # 快速选项
        opts = QWidget()
        opts.setStyleSheet("background: transparent;")
        opts_layout = QHBoxLayout(opts)
        opts_layout.setContentsMargins(0, 0, 0, 0)
        self.overwrite_cb = QCheckBox("覆盖源文件（不生成 (cleaned) 副本）")
        self.overwrite_cb.setChecked(True)
        self.remove_headers_cb = QCheckBox("删除页眉全部内容")
        self.remove_headers_cb.setChecked(True)
        self.strip_marker_cb = QCheckBox("删除文件名中的『精品解析：』字段")
        self.strip_marker_cb.setChecked(True)
        self.flatten_cb = QCheckBox("平铺到文件夹（压缩包与子文件夹都展开到当前文件夹）")
        self.flatten_cb.setChecked(True)
        for cb in [self.overwrite_cb, self.remove_headers_cb, self.strip_marker_cb, self.flatten_cb]:
            cb.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 12px;")
        opts_layout.addWidget(self.overwrite_cb)
        opts_layout.addWidget(self.remove_headers_cb)
        opts_layout.addWidget(self.strip_marker_cb)
        opts_layout.addWidget(self.flatten_cb)
        opts_layout.addStretch()
        layout.addWidget(opts)

        # 主内容区：左 = 处理日志（独立面板），右 = 文件列表 + 操作
        content_split = QSplitter(Qt.Horizontal)
        content_split.setHandleWidth(1)
        content_split.setStyleSheet(f"QSplitter::handle {{ background-color: {BORDER}; }}")

        # ── 左：处理日志面板（独立的「候选框」）──
        log_panel = QWidget()
        log_panel.setStyleSheet("background: transparent;")
        log_panel_layout = QVBoxLayout(log_panel)
        log_panel_layout.setContentsMargins(0, 0, 8, 0)
        log_panel_layout.setSpacing(6)

        log_header = QWidget()
        log_header.setStyleSheet("background: transparent;")
        log_header_layout = QHBoxLayout(log_header)
        log_header_layout.setContentsMargins(0, 4, 0, 2)
        log_title = QLabel("处理日志")
        log_title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {TEXT_PRIMARY};")
        btn_clear_log = QPushButton("清空日志")
        btn_clear_log.setStyleSheet(LINK_BTN)
        btn_clear_log.setCursor(Qt.PointingHandCursor)
        btn_clear_log.clicked.connect(self._clear_log)
        log_header_layout.addWidget(log_title)
        log_header_layout.addStretch()
        log_header_layout.addWidget(btn_clear_log)
        log_panel_layout.addWidget(log_header)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_panel_layout.addWidget(self.log_text, stretch=1)

        # ── 右：文件列表面板 ──
        file_panel = QWidget()
        file_panel.setStyleSheet("background: transparent;")
        file_panel_layout = QVBoxLayout(file_panel)
        file_panel_layout.setContentsMargins(8, 0, 0, 0)
        file_panel_layout.setSpacing(6)

        # 文件列表标题
        list_header = QWidget()
        list_header.setStyleSheet("background: transparent;")
        list_header_layout = QHBoxLayout(list_header)
        list_header_layout.setContentsMargins(0, 4, 0, 2)
        self.file_count_label = QLabel("文件列表（共 0 个）")
        self.file_count_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {TEXT_PRIMARY};")

        btn_select_all = QPushButton("全选")
        btn_invert = QPushButton("反选")
        btn_remove = QPushButton("删除选中")
        btn_clear = QPushButton("清空列表")
        for btn in (btn_select_all, btn_invert, btn_remove, btn_clear):
            btn.setStyleSheet(LINK_BTN)
            btn.setCursor(Qt.PointingHandCursor)
        btn_select_all.clicked.connect(self._select_all)
        btn_invert.clicked.connect(self._invert_selection)
        btn_remove.clicked.connect(self._remove_selected)
        btn_clear.clicked.connect(self._clear_files)

        list_header_layout.addWidget(self.file_count_label)
        list_header_layout.addStretch()
        list_header_layout.addWidget(btn_select_all)
        list_header_layout.addWidget(btn_invert)
        list_header_layout.addWidget(btn_remove)
        list_header_layout.addWidget(btn_clear)
        file_panel_layout.addWidget(list_header)

        # 文件 Tree
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabels(["", "文件名", "类型", "状态"])
        self.file_tree.setColumnWidth(0, 30)
        self.file_tree.setColumnWidth(1, 320)
        self.file_tree.setColumnWidth(2, 60)
        self.file_tree.setColumnWidth(3, 80)
        self.file_tree.setMinimumHeight(220)
        self.file_tree.setMaximumHeight(400)
        self.file_tree.setAlternatingRowColors(True)
        self.file_tree.setRootIsDecorated(False)
        self.file_tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.file_tree.itemDoubleClicked.connect(self._toggle_check)
        # Delete 键删除
        self.file_tree.keyPressEvent = self._tree_key_press
        file_panel_layout.addWidget(self.file_tree, stretch=1)

        # 操作按钮 + 进度条
        action_row = QWidget()
        action_row.setStyleSheet("background: transparent;")
        action_layout = QHBoxLayout(action_row)
        action_layout.setContentsMargins(0, 4, 0, 0)

        self.start_btn = QPushButton("▶  开始处理")
        self.start_btn.setStyleSheet(PRIMARY_BTN)
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self._start_process)
        action_layout.addWidget(self.start_btn)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setStyleSheet(CANCEL_BTN)
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self._cancel_process)
        self.cancel_btn.hide()
        action_layout.addWidget(self.cancel_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(180)
        self.progress_bar.setFormat("")
        self.progress_bar.hide()
        action_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel()
        self.progress_label.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY};")
        self.progress_label.hide()
        action_layout.addWidget(self.progress_label)

        action_layout.addStretch()
        file_panel_layout.addWidget(action_row)

        # 左侧=文件列表（占满并可伸缩），右侧=处理日志（固定初始宽）
        content_split.addWidget(file_panel)
        content_split.addWidget(log_panel)
        content_split.setStretchFactor(0, 1)
        content_split.setStretchFactor(1, 0)
        content_split.setSizes([600, 320])
        layout.addWidget(content_split, stretch=1)

        return page

    # ── 设置页 ─────────────────────────────────────────
    def _build_settings_page(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"border: none; background-color: {BG_MAIN};")
        inner = QWidget()
        inner.setStyleSheet(f"background-color: {BG_MAIN};")
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(20, 16, 20, 30)
        layout.setSpacing(14)

        title = QLabel("设置")
        title.setStyleSheet(f"font-size: 17px; font-weight: bold; color: {TEXT_PRIMARY};")
        layout.addWidget(title)

        # 水印关键词
        kw_group = QGroupBox("水印关键词")
        kw_layout = QVBoxLayout(kw_group)
        kw_layout.addWidget(QLabel("每行一个关键词，匹配到即清除。修改后点击保存生效。"))
        self.keywords_text = QTextEdit()
        self.keywords_text.setMaximumHeight(120)
        self.keywords_text.setPlainText("\n".join(
            self.config.get("metadata_keywords", DEFAULT_METADATA_KEYWORDS)))
        kw_layout.addWidget(self.keywords_text)
        layout.addWidget(kw_group)

        # 页眉处理
        header_group = QGroupBox("页眉处理")
        header_layout = QVBoxLayout(header_group)
        self.setting_remove_headers = QCheckBox("删除页眉全部内容（不限于关键词匹配）")
        self.setting_remove_headers.setChecked(
            self.config.get("remove_all_header_content", False))
        header_layout.addWidget(self.setting_remove_headers)
        layout.addWidget(header_group)

        # DOCX 属性
        docx_group = QGroupBox("DOCX 文档属性覆盖")
        docx_grid = QGridLayout(docx_group)
        docx_config = self.config.get("docx_core_properties", {})
        self.docx_override = QCheckBox("启用属性覆盖")
        self.docx_override.setChecked(docx_config.get("override_enabled", False))
        docx_grid.addWidget(self.docx_override, 0, 0, 1, 2)
        self.docx_fields = {}
        docx_values = docx_config.get("values", {})
        for i, (key, label) in enumerate([("author", "作者"), ("title", "标题"),
                                           ("subject", "主题"), ("keywords", "关键词"),
                                           ("comments", "备注")]):
            lbl = QLabel(label + "：")
            lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
            entry = QLineEdit()
            entry.setText(docx_values.get(key, ""))
            entry.setMinimumWidth(250)
            docx_grid.addWidget(lbl, i + 1, 0, Qt.AlignRight)
            docx_grid.addWidget(entry, i + 1, 1)
            self.docx_fields[key] = entry
        layout.addWidget(docx_group)

        # PDF 元数据
        pdf_group = QGroupBox("PDF 元数据覆盖")
        pdf_grid = QGridLayout(pdf_group)
        pdf_config = self.config.get("pdf_metadata", {})
        self.pdf_override = QCheckBox("启用元数据覆盖")
        self.pdf_override.setChecked(pdf_config.get("override_enabled", False))
        pdf_grid.addWidget(self.pdf_override, 0, 0, 1, 2)
        self.pdf_fields = {}
        pdf_values = pdf_config.get("values", {})
        for i, (key, label) in enumerate([("title", "标题"), ("author", "作者"),
                                           ("subject", "主题"), ("keywords", "关键词"),
                                           ("creator", "创建者"), ("producer", "生成器")]):
            lbl = QLabel(label + "：")
            lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
            entry = QLineEdit()
            entry.setText(pdf_values.get(key, ""))
            entry.setMinimumWidth(250)
            pdf_grid.addWidget(lbl, i + 1, 0, Qt.AlignRight)
            pdf_grid.addWidget(entry, i + 1, 1)
            self.pdf_fields[key] = entry
        layout.addWidget(pdf_group)

        # 保存按钮
        save_btn = QPushButton("保存设置")
        save_btn.setStyleSheet(PRIMARY_BTN)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self._save_settings)
        layout.addWidget(save_btn)

        layout.addStretch()
        scroll.setWidget(inner)
        outer.addWidget(scroll)
        return page

    # ── 关于页 ─────────────────────────────────────────
    def _build_about_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)

        icon = QLabel("🛡️")
        icon.setStyleSheet("font-size: 44px; border: none; background: transparent;")
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)

        title = QLabel("学科网水印清理工具")
        title.setStyleSheet(f"font-size: 19px; font-weight: bold; color: {TEXT_PRIMARY};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        ver = QLabel("版本 2.1 · 图形界面版")
        ver.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY};")
        ver.setAlignment(Qt.AlignCenter)
        layout.addWidget(ver)

        desc = QLabel("自动清理 DOC / DOCX / PDF 中的学科网相关水印\n"
                      "支持页眉页脚水印、动态标记、文档属性残留清除\n"
                      "内置压缩包批量处理，右键菜单一键操作")
        desc.setStyleSheet(f"font-size: 12px; color: {TEXT_SECONDARY};")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        tech = QLabel("\n技术栈：Python + PySide6 + python-docx + PyMuPDF")
        tech.setStyleSheet(f"font-size: 10px; color: {TEXT_HINT};")
        tech.setAlignment(Qt.AlignCenter)
        layout.addWidget(tech)

        return page

    # ── 页面切换 ───────────────────────────────────────
    _current_index = 0

    def _switch_page(self, index):
        self.stack.setCurrentIndex(index)
        self._current_index = index
        # 更新导航高亮
        navs = [self.nav_home, self.nav_settings, self.nav_about]
        for i, btn in enumerate(navs):
            btn.setStyleSheet(NAV_BTN_ACTIVE if i == index else NAV_BTN_NORMAL)

    # ── 拖放 ───────────────────────────────────────────
    def _drag_enter(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _drop_event(self, event):
        paths = []
        for url in event.mimeData().urls():
            p = Path(url.toLocalFile())
            if p.exists():
                paths.append(p)
        if paths:
            self._add_paths(paths)

    # ── 文件选择 ───────────────────────────────────────
    def _select_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择文件", "",
            "所有支持格式 (*.doc *.docx *.pdf *.zip);;"
            "Word 文档 (*.doc *.docx);;PDF (*.pdf);;压缩包 (*.zip);;所有文件 (*)"
        )
        if files:
            self._add_paths([Path(f) for f in files])

    def _select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            self._add_paths([Path(folder)])

    def _add_paths(self, paths):
        added = 0
        for p in paths:
            if not p.exists():
                continue
            if p.is_dir():
                self.added_folders.add(str(p))
                files = collect_files([p], recursive=True)
                for fp in files:
                    if str(fp) not in self.file_paths:
                        self._add_file_item(fp)
                        added += 1
            elif p.suffix.lower() in DOC_EXTENSIONS or p.suffix.lower() in ARCHIVE_EXTENSIONS:
                if str(p) not in self.file_paths:
                    self._add_file_item(p)
                    added += 1

        self._update_file_count()
        self._set_status(f"已添加 {added} 个文件")
        self._log(f"已添加 {added} 个文件到列表", TEXT_SECONDARY)

    def _add_file_item(self, path: Path):
        ext = path.suffix.lower()
        type_str = f"📦 {ext}" if ext in ARCHIVE_EXTENSIONS else ext
        key = f"{self._row_counter}|{path}"
        self._row_counter += 1

        item = QTreeWidgetItem()
        # 列 0 使用原生复选框，不再用 "☐/☑" 文本模拟
        item.setCheckState(0, Qt.Checked)
        item.setText(1, str(path))
        item.setText(2, type_str)
        item.setText(3, "待处理")
        item.setData(0, Qt.UserRole, str(path))
        self.file_tree.addTopLevelItem(item)
        self.file_paths[key] = path

    def _update_file_count(self):
        self.file_count_label.setText(f"文件列表（共 {self.file_tree.topLevelItemCount()} 个）")

    def _select_all(self):
        for i in range(self.file_tree.topLevelItemCount()):
            self.file_tree.topLevelItem(i).setCheckState(0, Qt.Checked)

    def _invert_selection(self):
        for i in range(self.file_tree.topLevelItemCount()):
            item = self.file_tree.topLevelItem(i)
            item.setCheckState(0, Qt.Unchecked if item.checkState(0) == Qt.Checked else Qt.Checked)

    def _toggle_check(self, item, col):
        """双击切换复选框。"""
        if col == 0:
            state = item.checkState(0)
            item.setCheckState(0, Qt.Unchecked if state == Qt.Checked else Qt.Checked)

    def _tree_key_press(self, event):
        if event.key() == Qt.Key_Delete:
            self._remove_selected()
        else:
            QTreeWidget.keyPressEvent(self.file_tree, event)

    def _remove_selected(self):
        for item in self.file_tree.selectedItems():
            idx = self.file_tree.indexOfTopLevelItem(item)
            self.file_tree.takeTopLevelItem(idx)
        self._update_file_count()

    def _clear_files(self):
        self.file_tree.clear()
        self.file_paths.clear()
        self._update_file_count()
        self._set_status("列表已清空")

    # ── 处理 ───────────────────────────────────────────
    def _start_process(self):
        if self.is_processing:
            return

        checked_docs = []
        checked_archives = []
        for i in range(self.file_tree.topLevelItemCount()):
            item = self.file_tree.topLevelItem(i)
            # 以原生复选框状态为准
            if item.checkState(0) != Qt.Checked:
                continue
            path = Path(item.data(0, Qt.UserRole) or item.text(1))
            if not path.exists():
                continue
            if path.suffix.lower() in ARCHIVE_EXTENSIONS:
                checked_archives.append(path)
            else:
                checked_docs.append(path)

        if not checked_docs and not checked_archives:
            QMessageBox.information(self, "提示", "请先添加文件并勾选要处理的项。")
            return

        self.is_processing = True
        self.start_btn.setEnabled(False)
        self.cancel_btn.show()
        self.progress_bar.show()
        self.progress_label.show()
        self.progress_bar.setValue(0)
        self.progress_label.setText("")

        overwrite = self.overwrite_cb.isChecked()
        remove_headers = self.remove_headers_cb.isChecked()
        flatten = self.flatten_cb.isChecked()
        strip_marker = self.strip_marker_cb.isChecked()

        self._set_status(f"正在处理...（共 {len(checked_docs) + len(checked_archives)} 项）")

        folder_roots = [Path(f) for f in self.added_folders]
        self.worker = ProcessWorker(checked_docs, checked_archives, overwrite, remove_headers,
                                    flatten, folder_roots, strip_marker)
        self.worker.log_signal.connect(self._log)
        self.worker.progress_signal.connect(self._on_progress)
        self.worker.file_status_signal.connect(self._on_file_status)
        self.worker.done_signal.connect(self._on_done)
        self.worker.start()

    def _on_progress(self, current, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"  {current}/{total}")

    def _on_file_status(self, path_str, status, color):
        for i in range(self.file_tree.topLevelItemCount()):
            item = self.file_tree.topLevelItem(i)
            d = item.data(0, Qt.UserRole)
            text1 = item.text(1)
            if (d and d == path_str) or text1 == path_str:
                item.setText(3, status)
                item.setForeground(3, QColor(color))
                break

    def _on_done(self, success, fail):
        self.is_processing = False
        self.start_btn.setEnabled(True)
        self.cancel_btn.hide()
        self.progress_bar.hide()
        self.progress_label.hide()
        self._set_status(f"处理完成：成功 {success}，失败 {fail}")

    def _cancel_process(self):
        self._log("用户取消了处理", WARNING_COLOR)
        self._on_done(0, 0)

    # ── 日志 ───────────────────────────────────────────
    def _log(self, message, color=TEXT_SECONDARY):
        self.log_text.append(f'<span style="color:{color};">{message}</span>')

    def _clear_log(self):
        self.log_text.clear()

    def _set_status(self, text):
        self.status_label.setText(text)

    # ── 设置保存 ───────────────────────────────────────
    def _save_settings(self):
        try:
            keywords = [k.strip() for k in self.keywords_text.toPlainText().split("\n")
                        if k.strip()]

            config = {
                "remove_all_header_content": self.setting_remove_headers.isChecked(),
                "metadata_keywords": keywords,
                "docx_core_properties": {
                    "override_enabled": self.docx_override.isChecked(),
                    "values": {k: v.text() for k, v in self.docx_fields.items()},
                },
                "pdf_metadata": {
                    "override_enabled": self.pdf_override.isChecked(),
                    "clear_xmp_metadata": self.config.get("pdf_metadata", {}).get(
                        "clear_xmp_metadata", "if_keyword"),
                    "values": {k: v.text() for k, v in self.pdf_fields.items()},
                },
            }

            config_path = PROJECT_DIR / "config.json"
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            self.config = config
            QMessageBox.information(self, "提示", "设置已保存！")
            self._log("设置已保存到 config.json", SUCCESS_COLOR)
            self.remove_headers_cb.setChecked(config["remove_all_header_content"])
        except Exception as exc:
            QMessageBox.critical(self, "错误", f"保存设置失败：{exc}")


# ─── 入口 ─────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(GLOBAL_STYLE)
    # 运行时窗口图标：exe 文件图标已在 spec 中指定，这里让 GUI 窗口标题栏也显示
    _icon_path = _resource_path("xkw.ico")
    if os.path.exists(_icon_path):
        app.setWindowIcon(QIcon(_icon_path))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    # 冻结版（PyInstaller onedir）在 Windows 上以 spawn 方式启动子进程，
    # 必须最先调用 freeze_support()，否则子进程会重新执行本入口而陷入递归 / 挂死，
    # 表现为「文件夹里只处理了少量文件就卡住 / 崩溃」（stable_process 的监督子进程依赖它）。
    import multiprocessing
    multiprocessing.freeze_support()

    # 命令行模式：被右键菜单 / 资源管理器以文件路径参数调用时，
    # 直接走 context_menu_handler 的水印清理逻辑（不显示 GUI），
    # 这样独立版 exe 自带 Python 运行时，无需本机安装 Python 即可处理文件。
    if len(sys.argv) > 1:
        import context_menu_handler
        raise SystemExit(context_menu_handler.main())
    main()
