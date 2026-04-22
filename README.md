# xkw-watermark-cleaner 学科网下载文件水印清理工具

用于清理从学科网下载的 `DOC`、`DOCX`、`PDF` 文件中的相关水印。

## 声明

- 本项目仅供学习、研究与技术交流参考。
- 请勿将本项目用于任何非法用途、侵权用途或违反平台规则的用途。
- 因使用本项目产生的风险与后果，由使用者自行承担。

当前仓库提供统一入口脚本和按格式拆分的处理模块：

- `clean_watermark.py`
- `clean_watermark_doc.py`
- `clean_watermark_docx.py`
- `clean_watermark_pdf.py`
- `context_menu_handler.py`
- `install_context_menu.py`
- `uninstall_context_menu.py`

## 功能

- 清理页眉、页脚中的学科网相关文字或对象
- 清理正文中的动态水印标记
- 清理 `DOCX` 中绘图对象的隐藏描述属性
- 清理 `DOCX` 自定义属性中的残留字段
- 清理 `PDF` 的 `/Info`、XMP 等底层元数据
- 支持批量处理 `doc`、`docx`、`pdf`
- 支持 Windows 右键菜单“清除学科网水印”

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

## 右键菜单集成

### 安装右键菜单

```bash
python install_context_menu.py
```

安装完成后，在 Windows 资源管理器中右键这些文件类型时，会出现：

- `.doc`
- `.docx`
- `.pdf`

菜单项名称：

- `清除学科网水印`
- `清除学科网水印（覆盖）`

### 卸载右键菜单

```bash
python uninstall_context_menu.py
```

### 右键菜单行为

- `清除学科网水印`
  - 在原文件目录下原地生成对应的清理后文件
  - 输出文件命名遵循 `(cleaned)` 规则
- `清除学科网水印（覆盖）`
  - 对 `docx` / `pdf`：直接覆盖源文件
  - 对 `doc`：不会回写原始 `doc`，仍然生成对应的 `(cleaned).docx`
- 会在同目录追加写入 `xkw-watermark-cleaner.log`
- 日志会记录每一条清理提示，便于回溯处理过程

## 说明

- 脚本会自动跳过已经带有 `(cleaned)` 标记的文件
- `DOC` 文件会先转换为 `DOCX`，再执行深度清理
- `DOC` 处理依赖本机已安装 Microsoft Word
- 右键菜单注册到当前用户注册表 `HKCU`，不会影响系统中的其他用户
- 右键菜单默认调用当前 Python 环境中的 `pythonw.exe`；若不存在则回退到 `python.exe`
- 如果资源管理器没有立即显示右键菜单，刷新文件夹或重新打开资源管理器窗口即可
- `xkw-watermark-cleaner.log` 为追加写入，不会在每次运行时覆盖旧记录
