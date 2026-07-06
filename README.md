# xkw-watermark-cleaner 学科网下载文件水印清理工具

用于清理从学科网下载的 `DOC`、`DOCX`、`PDF` 文件中的相关水印以及下载的 `ZIP` 压缩包解压后批量处理水印

## 声明

- 本项目仅供学习、研究与技术交流参考。
- 请勿将本项目用于任何非法用途、侵权用途或违反平台规则的用途。
- 因使用本项目产生的风险与后果，由使用者自行承担。

当前仓库提供统一入口脚本和按格式拆分的处理模块：

- `clean_watermark.py`
- `clean_watermark_doc.py`
- `clean_watermark_docx.py`
- `clean_watermark_pdf.py`
- `config.json`
- `context_menu_handler.py`
- `install_context_menu.py`
- `uninstall_context_menu.py`

## 功能

- 清理页眉、页脚中的学科网相关文字或对象
- 支持一键删除页眉中的所有内容（不限关键词）
- 清理正文中的动态水印标记
- 清理 `DOCX` 中绘图对象的隐藏描述属性
- 清理 `DOCX` 自定义属性中的残留字段
- 清理 `PDF` 的 `/Info`、XMP 等底层元数据
- 支持批量处理 `doc`、`docx`、`pdf`
- 支持 Windows 右键菜单"清除学科网水印"

## 环境要求

- Windows
- Python 3.10+
- 已安装 Microsoft Word

其中 `DOC` 处理依赖 Word COM 自动化，因此仅适用于安装了 Word 的 Windows 环境。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 1. 处理单个文件

```bash
python clean_watermark.py 你的文件.docx
python clean_watermark.py 你的文件.doc
python clean_watermark.py 你的文件.pdf
```

输出文件默认生成在原文件同目录下：

- `xxx.doc` -> `xxx(cleaned).docx`
- `xxx.docx` -> `xxx(cleaned).docx`
- `xxx.pdf` -> `xxx(cleaned).pdf`

### 2. 批量处理当前目录

```bash
python clean_watermark.py .
```

### 3. 递归处理目录

```bash
python clean_watermark.py . -r
```

### 4. 指定输出目录

```bash
python clean_watermark.py . -r -o out
```

### 5. 删除页眉全部内容

```bash
python clean_watermark.py 你的文件.docx --remove-headers
python clean_watermark.py . -r --remove-headers
```

添加 `--remove-headers` 参数后，将删除页眉中的所有内容（文本、图片、表格等），而不仅是匹配关键词的水印内容。页脚仍按原逻辑进行关键词匹配清理。

也可以通过配置文件永久开启此功能（见下方配置文件说明）。

> 右键菜单默认就会删除页眉全部内容，无需额外参数。

## 配置文件

`config.json` 用于控制 `DOCX` 核心属性的处理方式：

```json
{
  "remove_all_header_content": false,
  "metadata_keywords": ["学科网", "zxxk.com", "zxxk", "rbm.xkw.com", "xkw"],
  "docx_core_properties": {
    "override_enabled": false,
    "values": {
      "author": "User",
      "comments": "",
      "title": "清理后的文档",
      "subject": "",
      "keywords": ""
    }
  },
  "pdf_metadata": {
    "override_enabled": false,
    "clear_xmp_metadata": "if_keyword",
    "values": {
      "title": "",
      "author": "",
      "subject": "",
      "keywords": "",
      "creator": "-",
      "producer": "-",
      "creationDate": "-",
      "modDate": "-"
    }
  }
}
```

- `remove_all_header_content: false`：默认关闭。设为 `true` 后，每次清理时会删除页眉中的所有内容（不限关键词），页脚仍按关键词匹配清理。也可通过命令行 `--remove-headers` 参数临时启用，优先级高于配置文件。
- `override_enabled: false`：保守模式。`author`、`title` 等核心属性只有在命中 `metadata_keywords` 时才会被清空；没有明显残留则保持原值。
- `override_enabled: true`：覆盖模式。按 `values` 中的值固定重写对应属性。
- `values` 中某个字段设置为 `"-"` 时，即使开启覆盖模式，也不会改动该属性。
- `docProps/custom.xml` 中包含 `metadata_keywords` 的自定义属性仍会被删除。
- `pdf_metadata.clear_xmp_metadata` 可设为 `if_keyword`、`always`、`never`，分别表示命中关键词才清除 XMP、总是清除 XMP、永不清除 XMP。

## 右键菜单集成

### 安装右键菜单

```bash
python install_context_menu.py
```

安装完成后，在 Windows 资源管理器中右键以下目标时，会出现对应菜单项：

**文件右键菜单**（`.doc` `.docx` `.pdf`）：

- `清除学科网水印`
- `清除学科网水印（覆盖）`


**压缩包右键菜单**（`.zip`）:

- `解压缩压缩包`
- `解压缩嵌套压缩包`
- `压缩包内文件平铺至文件夹根目录`
- `执行水印清理`（默认覆盖模式）

**文件夹右键菜单**：

- `清除学科网水印（文件夹内所有文件）`
- `清除学科网水印（文件夹内所有文件，覆盖）`

> 右键菜单执行时会自动删除页眉中的所有内容（不限关键词），同时保留原有的水印清理功能。页脚仍按关键词匹配清理。

### 卸载右键菜单

```bash
python uninstall_context_menu.py
```

### 右键菜单行为

**文件右键：**

- `清除学科网水印`
  - 在原文件目录下原地生成对应的清理后文件
  - 输出文件命名遵循 `(cleaned)` 规则
  - 自动删除页眉全部内容（不限关键词）
- `清除学科网水印（覆盖）`
  - 对 `docx` / `pdf`：直接覆盖源文件
  - 对 `doc`：不会回写原始 `doc`，仍然生成对应的 `(cleaned).docx`
  - 自动删除页眉全部内容（不限关键词）

**文件夹右键：**

- `清除学科网水印（文件夹内所有文件）`
  - 检测文件夹内的 `.doc`、`.docx`、`.pdf` 文件（含子文件夹）
  - 为每个文件原地生成 `(cleaned)` 清理后文件
  - 自动删除页眉全部内容（不限关键词）
- `清除学科网水印（文件夹，覆盖）`
  - 检测文件夹内的 `.doc`、`.docx`、`.pdf` 文件（含子文件夹）
  - 对 `docx` / `pdf` 直接覆盖源文件，`doc` 生成 `(cleaned).docx`
  - 自动删除页眉全部内容（不限关键词）
- 会在文件夹内追加写入 `xkw-watermark-cleaner.log`
- 日志会记录每个文件的清理提示，便于回溯处理过程

**压缩包.zip右键**

-`解压缩压缩包`
-`解压缩嵌套压缩包`
-`压缩包内文件平铺至文件夹根目录`
  - 即压缩包内所有文件解压缩后都仅有最外层一层文件夹，避免嵌套
  - 清除空白文件夹
-`执行水印清理`（默认覆盖模式）

## 说明

- 脚本会自动跳过已经带有 `(cleaned)` 标记的文件
- `DOC` 文件会先转换为 `DOCX`，再执行深度清理
- `DOC` 处理依赖本机已安装 Microsoft Word
- 右键菜单注册到当前用户注册表 `HKCU`，不会影响系统中的其他用户
- 右键菜单默认调用当前 Python 环境中的 `pythonw.exe`；若不存在则回退到 `python.exe`
- 如果资源管理器没有立即显示右键菜单，刷新文件夹或重新打开资源管理器窗口即可
- `xkw-watermark-cleaner.log` 为追加写入，不会在每次运行时覆盖旧记录

## 构建打包

本项目提供 `build.py` 统一构建脚本，可一键打包出两个独立可执行版本。

### 构建环境

- Windows
- Python 3.10+
- 已安装 PyInstaller、py7zr（打包 7z 分发包用）
- 可选：UPX（用于压缩 DLL，减小体积）

安装构建依赖：

```bash
pip install pyinstaller py7zr
```

### 构建命令

```bash
# 构建全部（完整版 + 精简版）
python build.py

# 仅构建完整版
python build.py full

# 仅构建精简版
python build.py simplified
```

### 构建产物

| 版本 | 路径 | 说明 |
|------|------|------|
| 完整版 | `body/学科网水印清理工具_独立版.exe` | PySide6 界面，onedir 模式（文件夹含 exe + dll） |
| 完整版压缩包 | `body_standalone.7z` | 7z 超高压缩分发包，适合分发 |
| 精简版 | `body_simplified/学科网水印清理工具_精简版.exe` | tkinter 界面，onefile 模式（单个 exe） |

### 两个版本的区别

- **完整版**：使用 PySide6（Qt6）界面，功能最完整，启动需加载多个 DLL，首次启动稍慢
- **精简版**：使用 tkinter 界面，单 exe 文件，体积小、启动快，适合快速使用")