#!/usr/bin/env python3
"""
学科网水印清理工具 - 图形用户界面 (PySide6)
界面风格参考 PDFGuru，左侧导航 + 右侧主内容区。
"""

import io
import json
import os
import shutil
import subprocess
import sys
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
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from clean_watermark import clean_one_file, clean_one_file_overwrite, collect_files
from cleaner_config import load_config, DEFAULT_METADATA_KEYWORDS

# ─── 常量 ─────────────────────────────────────────────
ARCHIVE_EXTENSIONS = {".zip", ".rar", ".7z"}
DOC_EXTENSIONS = {".doc", ".docx", ".pdf"}
SUPPORTED_EXTS_STR = ".doc  .docx  .pdf  .zip  .rar  .7z"

# PDFGuru 风格配色
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

    def __init__(self, docs, archives, overwrite, remove_headers):
        super().__init__()
        self.docs = docs
        self.archives = archives
        self.overwrite = overwrite
        self.remove_headers = remove_headers

    def run(self):
        success = 0
        fail = 0
        total = len(self.docs) + len(self.archives)
        current = 0

        # 处理普通文档
        for doc_path in self.docs:
            current += 1
            self.progress_signal.emit(current, total)
            self.file_status_signal.emit(str(doc_path), "处理中...", PRIMARY)
            self.log_signal.emit(f"[{datetime.now():%H:%M:%S}] 开始处理: {doc_path}", TEXT_SECONDARY)

            try:
                if self.overwrite:
                    output = clean_one_file_overwrite(str(doc_path),
                                                       remove_all_header=self.remove_headers)
                else:
                    output = clean_one_file(str(doc_path),
                                            remove_all_header=self.remove_headers)
                self.log_signal.emit(f"[{datetime.now():%H:%M:%S}] 处理完成: {output}", SUCCESS_COLOR)
                self.file_status_signal.emit(str(doc_path), "已完成", SUCCESS_COLOR)
                success += 1
            except Exception as exc:
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
                self._process_single_archive(archive_path)
                self.file_status_signal.emit(str(archive_path), "已完成", SUCCESS_COLOR)
                success += 1
            except Exception as exc:
                self.log_signal.emit(
                    f"[{datetime.now():%H:%M:%S}] 压缩包处理失败: {archive_path}\n原因: {exc}",
                    ERROR_COLOR)
                self.file_status_signal.emit(str(archive_path), "失败", ERROR_COLOR)
                fail += 1

        self.log_signal.emit(
            f"\n全部处理完成！成功 {success}，失败 {fail}",
            SUCCESS_COLOR if fail == 0 else WARNING_COLOR)
        self.done_signal.emit(success, fail)

    def _process_single_archive(self, archive_path: Path):
        from context_menu_handler import extract_archive, find_archives_in_dir

        archive_path = archive_path.resolve()
        extract_root = archive_path.parent / archive_path.stem

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
            try:
                clean_one_file_overwrite(str(fp), remove_all_header=self.remove_headers)
                self.log_signal.emit(f"[{datetime.now():%H:%M:%S}] 处理完成: {fp}", SUCCESS_COLOR)
            except Exception as exc:
                self.log_signal.emit(f"[{datetime.now():%H:%M:%S}] 处理失败: {fp} ({exc})",
                                     ERROR_COLOR)

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
        subtitle = QLabel("支持 DOC / DOCX / PDF 水印清理，含压缩包批量处理")
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
        for cb in [self.overwrite_cb, self.remove_headers_cb]:
            cb.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 12px;")
        opts_layout.addWidget(self.overwrite_cb)
        opts_layout.addWidget(self.remove_headers_cb)
        opts_layout.addStretch()
        layout.addWidget(opts)

        # 文件列表标题
        list_header = QWidget()
        list_header.setStyleSheet("background: transparent;")
        list_header_layout = QHBoxLayout(list_header)
        list_header_layout.setContentsMargins(0, 4, 0, 2)
        self.file_count_label = QLabel("文件列表（共 0 个）")
        self.file_count_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {TEXT_PRIMARY};")
        btn_clear = QPushButton("清空列表")
        btn_clear.setStyleSheet(LINK_BTN)
        btn_clear.setCursor(Qt.PointingHandCursor)
        btn_clear.clicked.connect(self._clear_files)
        list_header_layout.addWidget(self.file_count_label)
        list_header_layout.addStretch()
        list_header_layout.addWidget(btn_clear)
        layout.addWidget(list_header)

        # 文件 Tree
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabels(["", "文件名", "类型", "状态"])
        self.file_tree.setColumnWidth(0, 30)
        self.file_tree.setColumnWidth(1, 320)
        self.file_tree.setColumnWidth(2, 60)
        self.file_tree.setColumnWidth(3, 80)
        self.file_tree.setAlternatingRowColors(True)
        self.file_tree.setRootIsDecorated(False)
        self.file_tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.file_tree.itemDoubleClicked.connect(self._toggle_check)
        # Delete 键删除
        self.file_tree.keyPressEvent = self._tree_key_press
        layout.addWidget(self.file_tree, stretch=1)

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
        layout.addWidget(action_row)

        # 日志区标题
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
        layout.addWidget(log_header)

        # 日志 Text
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(160)
        layout.addWidget(self.log_text)

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
            "所有支持格式 (*.doc *.docx *.pdf *.zip *.rar *.7z);;"
            "Word 文档 (*.doc *.docx);;PDF (*.pdf);;压缩包 (*.zip *.rar *.7z);;所有文件 (*)"
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
        item.setText(0, "☐")
        item.setText(1, str(path))
        item.setText(2, type_str)
        item.setText(3, "待处理")
        item.setData(0, Qt.UserRole, str(path))
        item.setCheckState(0, Qt.Unchecked)
        self.file_tree.addTopLevelItem(item)
        self.file_paths[key] = path

    def _update_file_count(self):
        self.file_count_label.setText(f"文件列表（共 {self.file_tree.topLevelItemCount()} 个）")

    def _toggle_check(self, item, col):
        """双击切换复选框。"""
        if col == 0:
            current = item.text(0)
            item.setText(0, "☑" if current == "☐" else "☐")

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
            if item.text(0) != "☑":
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

        self._set_status(f"正在处理...（共 {len(checked_docs) + len(checked_archives)} 项）")

        self.worker = ProcessWorker(checked_docs, checked_archives, overwrite, remove_headers)
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
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
