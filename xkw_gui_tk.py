#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学科网水印清理工具 - 图形用户界面 (tkinter)
左侧导航 + 右侧主内容区。
打包后 exe 约 10MB（tkinter 是 Python 内置库，无需额外依赖）。
"""
import json
import os
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# 确保项目根目录在 sys.path 中
PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from clean_watermark import clean_one_file, clean_one_file_overwrite, collect_files
from cleaner_config import load_config, save_config, DEFAULT_METADATA_KEYWORDS

# ─── 常量 ─────────────────────────────────────────────
ARCHIVE_EXTENSIONS = {".zip"}
DOC_EXTENSIONS = {".doc", ".docx", ".pdf"}
SUPPORTED_EXTS_STR = ".doc  .docx  .pdf  .zip"

# 风格配色（tkinter 用 dict 存储，通过 configure 应用）
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

# ─── 样式工具 ─────────────────────────────────────────

def setup_styles(root):
    """配置 ttk 样式，蓝色主题。"""
    style = ttk.Style(root)
    # 尝试使用 clam 主题（支持更多自定义）
    try:
        style.theme_use("clam")
    except Exception:
        pass

    # 按钮
    style.configure("Primary.TButton",
                    background=PRIMARY, foreground="white",
                    padding=(16, 8), font=("Microsoft YaHei", 10, "bold"),
                    borderwidth=0, relief="flat")
    style.map("Primary.TButton",
              background=[("active", PRIMARY_HOVER), ("pressed", "#0958D9")])

    style.configure("Success.TButton",
                    background="#52C41A", foreground="white",
                    padding=(16, 8), font=("Microsoft YaHei", 10, "bold"),
                    borderwidth=0, relief="flat")
    style.map("Success.TButton",
              background=[("active", "#73D13D"), ("pressed", "#389E0D")])

    style.configure("Outline.TButton",
                    background=BG_CARD, foreground=PRIMARY,
                    padding=(16, 8), font=("Microsoft YaHei", 10),
                    borderwidth=1, relief="solid")
    style.map("Outline.TButton",
              background=[("active", PRIMARY_LIGHT), ("pressed", "#BAD8F5")])

    # 侧边栏按钮
    style.configure("Sidebar.TButton",
                    background=BG_SIDEBAR, foreground=TEXT_PRIMARY,
                    padding=(20, 12), font=("Microsoft YaHei", 11),
                    borderwidth=0, anchor="w", relief="flat")
    style.map("Sidebar.TButton",
              background=[("active", "#F0F5FF")],
              foreground=[("active", PRIMARY)])

    style.configure("SidebarActive.TButton",
                    background=PRIMARY_LIGHT, foreground=PRIMARY,
                    padding=(20, 12), font=("Microsoft YaHei", 11, "bold"),
                    borderwidth=0, anchor="w", relief="flat")

    # 复选框
    style.configure("TCheckbutton", font=("Microsoft YaHei", 10),
                    background=BG_CARD, foreground=TEXT_PRIMARY)

    # 进度条
    style.configure("Blue.Horizontal.TProgressbar",
                    background=PRIMARY, troughcolor=BG_MAIN,
                    borderwidth=0, thickness=8)

    # 输入框
    style.configure("TEntry", padding=6, relief="flat",
                    fieldbackground=BG_CARD, bordercolor=BORDER)
    style.configure("TLabel", background=BG_CARD, foreground=TEXT_PRIMARY,
                    font=("Microsoft YaHei", 10))
    style.configure("Title.TLabel", font=("Microsoft YaHei", 16, "bold"),
                    background=BG_CARD, foreground=TEXT_PRIMARY)
    style.configure("Subtitle.TLabel", font=("Microsoft YaHei", 11),
                    background=BG_CARD, foreground=TEXT_SECONDARY)
    style.configure("Hint.TLabel", font=("Microsoft YaHei", 10),
                    background=BG_MAIN, foreground=TEXT_HINT)


# ─── 日志管理器 ─────────────────────────────────────────

class LogManager:
    """管理日志输出（同时写入 GUI 和文件）。"""
    def __init__(self, text_widget: scrolledtext.ScrolledText):
        self.widget = text_widget
        self.file = None
        self.log_path = None

    def set_log_file(self, path: Path):
        self.log_path = path
        self.file = open(path, "a", encoding="utf-8")

    def log(self, msg: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        color_map = {
            "INFO": "#1F1F1F",
            "SUCCESS": "#52C41A",
            "WARNING": "#FAAD14",
            "ERROR": "#FF4D4F",
            "DEBUG": "#666666",
        }
        color = color_map.get(level, "#1F1F1F")
        display = f"[{timestamp}] {msg}\n"

        self.widget.insert("end", display)
        # 颜色标记
        line_start = self.widget.index("end - 2 lines")
        line_end = self.widget.index("end - 1 lines")
        self.widget.tag_add(level, line_start, line_end)
        self.widget.tag_config(level, foreground=color)
        self.widget.see("end")

        if self.file:
            self.file.write(display)
            self.file.flush()

        # 同时打印到控制台
        print(f"[{level}] {msg}")

    def info(self, msg):    self.log(msg, "INFO")
    def success(self, msg): self.log(msg, "SUCCESS")
    def warning(self, msg): self.log(msg, "WARNING")
    def error(self, msg):   self.log(msg, "ERROR")
    def debug(self, msg):   self.log(msg, "DEBUG")

    def close(self):
        if self.file:
            self.file.close()


# ─── 处理线程 ─────────────────────────────────────────

class ProcessThread(threading.Thread):
    """后台处理线程，不阻塞 GUI。"""
    def __init__(self, files, mode, config, log_manager, progress_callback):
        super().__init__(daemon=True)
        self.files = files
        self.mode = mode  # "new_file" or "overwrite"
        self.config = config
        self.logger = log_manager
        self.progress_callback = progress_callback
        self.success = 0
        self.failed = 0

    def run(self):
        total = len(self.files)
        for i, fpath in enumerate(self.files, 1):
            try:
                self.logger.info(f"处理 ({i}/{total}): {Path(fpath).name}")
                if self.mode == "overwrite":
                    result = clean_one_file_overwrite(
                        fpath,
                        remove_all_header=self.config.get("remove_all_header_content", True),
                    )
                else:
                    result = clean_one_file(
                        fpath,
                        remove_all_header=self.config.get("remove_all_header_content", True),
                    )
                if result and result.get("success"):
                    self.success += 1
                    self.logger.success(f"  ✓ 完成: {result.get('output_path', fpath)}")
                else:
                    self.failed += 1
                    self.logger.error(f"  ✗ 失败: {result.get('error', '未知错误') if result else '返回空'}")
            except Exception as e:
                self.failed += 1
                self.logger.error(f"  ✗ 异常: {e}")
                traceback.print_exc()

            # 更新进度
            pct = int(i / total * 100)
            self.progress_callback(pct)

        self.logger.info(f"处理完成: 成功 {self.success}，失败 {self.failed}")
        self.progress_callback(100)


# ─── 主页 ─────────────────────────────────────────

class HomePage(ttk.Frame):
    def __init__(self, parent, main_app):
        super().__init__(parent, style="Card.TFrame")
        self.main_app = main_app
        self.selected_files = []
        self.process_mode = tk.StringVar(value="new_file")
        self.create_widgets()

    def create_widgets(self):
        # 标题区
        header = ttk.Frame(self, style="Card.TFrame")
        header.pack(fill="x", padx=24, pady=(24, 12))
        ttk.Label(header, text="学科网水印清理工具", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="支持 .doc / .docx / .pdf / .zip", style="Subtitle.TLabel").pack(anchor="w", pady=(4, 0))

        # 拖放/选择区（模拟）
        drop_zone = tk.Frame(self, bg=BG_CARD, highlightbackground=PRIMARY,
                             highlightcolor=PRIMARY, highlightthickness=2,
                             bd=0, relief="flat", height=100)
        drop_zone.pack(fill="x", padx=24, pady=12)
        drop_zone.pack_propagate(False)

        drop_label = tk.Label(drop_zone, text="点击选择文件，或拖放文件到此区域",
                               bg=BG_CARD, fg=TEXT_HINT,
                               font=("Microsoft YaHei", 11))
        drop_label.place(relx=0.5, rely=0.5, anchor="center")

        # 绑定点击事件
        for widget in (drop_zone, drop_label):
            widget.bind("<Button-1>", lambda e: self.select_files())

        # 按钮区
        btn_frame = ttk.Frame(self, style="Card.TFrame")
        btn_frame.pack(fill="x", padx=24, pady=(0, 12))
        ttk.Button(btn_frame, text="选择文件", command=self.select_files,
                   style="Primary.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(btn_frame, text="选择文件夹", command=self.select_folder,
                   style="Outline.TButton").pack(side="left", padx=8)

        # 模式选择
        mode_frame = ttk.Frame(self, style="Card.TFrame")
        mode_frame.pack(fill="x", padx=24, pady=(0, 12))
        ttk.Radiobutton(mode_frame, text="生成 (cleaned) 文件（不覆盖原文件）",
                         variable=self.process_mode, value="new_file",
                         style="TCheckbutton").pack(side="left", padx=(0, 20))
        ttk.Radiobutton(mode_frame, text="覆盖原文件",
                         variable=self.process_mode, value="overwrite",
                         style="TCheckbutton").pack(side="left")

        # 文件列表
        list_frame = ttk.LabelFrame(self, text="已选择文件", style="Card.TLabelframe")
        list_frame.pack(fill="both", expand=True, padx=24, pady=12)

        cols = ("#", "文件名", "路径", "大小")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=8)
        for col, w in zip(cols, (40, 200, 350, 80)):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)

        # 进度条
        self.progress = ttk.Progressbar(self, style="Blue.Horizontal.TProgressbar",
                                         mode="determinate", maximum=100)
        self.progress.pack(fill="x", padx=24, pady=(0, 8))
        self.status_label = ttk.Label(self, text="就绪", style="Subtitle.TLabel")
        self.status_label.pack(anchor="w", padx=24, pady=(0, 12))

        # 开始按钮
        ttk.Button(self, text="开始处理", command=self.start_process,
                   style="Success.TButton").pack(padx=24, pady=(0, 24), ipadx=20, ipady=8)

    def select_files(self):
        files = filedialog.askopenfilenames(
            title="选择文件",
            filetypes=[("支持的文件", "*.doc *.docx *.pdf *.zip"), ("所有文件", "*.*")]
        )
        if files:
            self.selected_files.extend(files)
            self.refresh_list()

    def select_folder(self):
        folder = filedialog.askdirectory(title="选择文件夹")
        if folder:
            # 扫描文件夹下的支持文件（非递归）
            exts = DOC_EXTENSIONS | ARCHIVE_EXTENSIONS
            found = [str(p) for p in Path(folder).iterdir()
                     if p.suffix.lower() in exts and p.is_file()]
            if found:
                self.selected_files.extend(found)
                self.refresh_list()
            else:
                messagebox.showinfo("提示", "该文件夹下没有支持的文件。")

    def refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        for i, f in enumerate(self.selected_files, 1):
            p = Path(f)
            size = p.stat().st_size if p.exists() else 0
            size_str = f"{size/1024:.1f} KB" if size < 1048576 else f"{size/1048576:.1f} MB"
            self.tree.insert("", "end", values=(i, p.name, str(p.parent), size_str))

    def update_progress(self, pct):
        self.progress["value"] = pct
        self.status_label.config(text=f"处理中... {pct}%")
        self.update_idletasks()

    def start_process(self):
        if not self.selected_files:
            messagebox.showwarning("提示", "请先选择文件！")
            return
        if self.main_app.is_processing:
            messagebox.showwarning("提示", "正在处理中，请等待...")
            return

        # 初始化日志
        log_dir = Path(self.selected_files[0]).parent if self.selected_files else PROJECT_DIR
        log_path = log_dir / f"clean_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        self.main_app.logger.set_log_file(log_path)
        self.main_app.logger.info(f"开始处理 {len(self.selected_files)} 个文件")
        self.main_app.logger.info(f"日志文件: {log_path}")

        self.main_app.is_processing = True
        self.status_label.config(text="处理中...")
        config = load_config()

        self.thread = ProcessThread(
            self.selected_files,
            self.process_mode.get(),
            config,
            self.main_app.logger,
            self.update_progress
        )
        self.thread.start()
        # 定期检查线程是否完成
        self.after(500, self._check_thread)

    def _check_thread(self):
        if self.thread.is_alive():
            self.after(500, self._check_thread)
        else:
            self.main_app.is_processing = False
            self.status_label.config(text="处理完成")
            messagebox.showinfo("完成", "处理完成！")


# ─── 设置页 ─────────────────────────────────────────

class SettingsPage(ttk.Frame):
    def __init__(self, parent, main_app):
        super().__init__(parent, style="Card.TFrame")
        self.main_app = main_app
        self.keyword_var = tk.StringVar()
        self.create_widgets()
        self.load_settings()

    def create_widgets(self):
        ttk.Label(self, text="设置", style="Title.TLabel").pack(anchor="w", padx=24, pady=(24, 12))

        # 关键词设置
        kw_frame = ttk.LabelFrame(self, text="PDF 元数据关键词（每行一个）",
                                   style="Card.TLabelframe")
        kw_frame.pack(fill="x", padx=24, pady=12)

        self.kw_text = scrolledtext.ScrolledText(kw_frame, height=6, font=("Consolas", 10),
                                                   bg=BG_CARD, fg=TEXT_PRIMARY,
                                                   insertbackground=TEXT_PRIMARY)
        self.kw_text.pack(fill="x", padx=8, pady=8)

        # 选项
        opt_frame = ttk.LabelFrame(self, text="处理选项", style="Card.TLabelframe")
        opt_frame.pack(fill="x", padx=24, pady=12)

        self.var_remove_headers = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt_frame, text="删除页眉（默认开启）",
                         variable=self.var_remove_headers, style="TCheckbutton").pack(anchor="w", padx=8, pady=4)

        self.var_clean_metadata = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt_frame, text="清理 PDF 元数据（默认开启）",
                         variable=self.var_clean_metadata, style="TCheckbutton").pack(anchor="w", padx=8, pady=4)

        self.var_remove_images = tk.BooleanVar(value=False)
        ttk.Checkbutton(opt_frame, text="删除所有图片（谨慎使用）",
                         variable=self.var_remove_images, style="TCheckbutton").pack(anchor="w", padx=8, pady=4)

        # 保存按钮
        ttk.Button(self, text="保存设置", command=self.save_settings,
                   style="Primary.TButton").pack(padx=24, pady=24, ipadx=20, ipady=8)

    def load_settings(self):
        config = load_config()
        keywords = config.get("metadata_keywords", DEFAULT_METADATA_KEYWORDS)
        self.kw_text.delete("1.0", "end")
        self.kw_text.insert("1.0", "\n".join(keywords))
        self.var_remove_headers.set(config.get("remove_headers", True))
        self.var_clean_metadata.set(config.get("clean_metadata", True))
        self.var_remove_images.set(config.get("remove_all_images", False))

    def save_settings(self):
        keywords = [line.strip() for line in self.kw_text.get("1.0", "end").splitlines() if line.strip()]
        config = {
            "metadata_keywords": keywords,
            "remove_headers": self.var_remove_headers.get(),
            "clean_metadata": self.var_clean_metadata.get(),
            "remove_all_images": self.var_remove_images.get(),
        }
        save_config(config)
        messagebox.showinfo("保存成功", "设置已保存！")


# ─── 关于页 ─────────────────────────────────────────

class AboutPage(ttk.Frame):
    def __init__(self, parent, main_app):
        super().__init__(parent, style="Card.TFrame")
        self.create_widgets()

    def create_widgets(self):
        ttk.Label(self, text="关于", style="Title.TLabel").pack(anchor="w", padx=24, pady=(24, 12))

        info = (
            "学科网水印清理工具\n\n"
            "版本：1.0.0\n"
            "功能：\n"
            "  • 清理 DOCX 文档中的学科网水印（页眉/微小元素/文本水印/属性）\n"
            "  • 清理 PDF 文件中的学科网水印（白色矩形覆盖 + 元数据清理）\n"
            "  • 支持批量处理和压缩包解压\n\n"
            "技术栈：Python + python-docx + PyMuPDF + tkinter\n"
        )
        ttk.Label(self, text=info, style="Subtitle.TLabel",
                  justify="left").pack(anchor="w", padx=24, pady=12)


# ─── 主窗口 ─────────────────────────────────────────

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.is_processing = False
        self.logger = None

        self.title("学科网水印清理工具")
        self.geometry("900x650")
        self.configure(bg=BG_MAIN)
        self.minsize(800, 550)

        # 设置图标（如果存在）
        try:
            if os.path.exists("xkw.ico"):
                self.iconbitmap("xkw.ico")
        except Exception:
            pass

        setup_styles(self)
        self.create_widgets()

        # 初始化日志（绑定到日志页的 text widget）
        self.logger = LogManager(self.log_text)

    def create_widgets(self):
        # 主容器：左侧导航 + 右侧内容
        main = ttk.Frame(self, style="Card.TFrame")
        main.pack(fill="both", expand=True, padx=8, pady=8)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        # 左侧导航
        sidebar = tk.Frame(main, bg=BG_SIDEBAR, width=160)
        sidebar.grid(row=0, column=0, sticky="ns", padx=(0, 1))
        sidebar.grid_propagate(False)

        ttk.Label(sidebar, text="  xkw 工具", font=("Microsoft YaHei", 13, "bold"),
                  background=BG_SIDEBAR, foreground=PRIMARY).pack(anchor="w", padx=16, pady=(16, 24))

        self.nav_buttons = {}
        for text, page_key in [("首页", "home"), ("设置", "settings"), ("关于", "about")]:
            btn = tk.Button(sidebar, text=f"  {text}",
                             bg=BG_SIDEBAR, fg=TEXT_PRIMARY,
                             font=("Microsoft YaHei", 11),
                             bd=0, anchor="w", padx=16, pady=10,
                             activebackground=PRIMARY_LIGHT,
                             activeforeground=PRIMARY,
                             command=lambda k=page_key: self.switch_page(k))
            btn.pack(fill="x", pady=2)
            self.nav_buttons[page_key] = btn

        # 右侧内容区
        content = ttk.Frame(main, style="Card.TFrame")
        content.grid(row=0, column=1, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)

        # 页面栈（共用同一个 grid 位置，通过 tkraise 切换）
        self.pages = {}
        self.page_keys = []

        for text, page_key in [("首页", "home"), ("设置", "settings"), ("关于", "about")]:
            if page_key == "home":
                page = HomePage(content, self)
            elif page_key == "settings":
                page = SettingsPage(content, self)
            else:
                page = AboutPage(content, self)
            page.grid(row=0, column=0, sticky="nsew")
            self.pages[page_key] = page
            self.page_keys.append(page_key)

        # 底部日志区
        log_frame = ttk.LabelFrame(main, text="实时日志", style="Card.TLabelframe")
        log_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))

        self.log_text = scrolledtext.ScrolledText(log_frame, height=6, font=("Consolas", 10),
                                                    bg=BG_CARD, fg=TEXT_PRIMARY,
                                                    insertbackground=TEXT_PRIMARY)
        self.log_text.pack(fill="x", padx=4, pady=4)

        # 显示首页
        self.switch_page("home")

    def switch_page(self, key):
        if key in self.pages:
            self.pages[key].tkraise()
        # 更新导航按钮样式
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.config(bg=PRIMARY_LIGHT, fg=PRIMARY, font=("Microsoft YaHei", 11, "bold"))
            else:
                btn.config(bg=BG_SIDEBAR, fg=TEXT_PRIMARY, font=("Microsoft YaHei", 11))

    def destroy(self):
        if self.logger:
            self.logger.close()
        super().destroy()


# ─── 入口 ─────────────────────────────────────────

if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
