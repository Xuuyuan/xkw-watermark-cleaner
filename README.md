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

## 功能

- 清理页眉、页脚中的学科网相关文字或对象
- 清理正文中的动态水印标记
- 清理 `DOCX` 中绘图对象的隐藏描述属性
- 清理 `DOCX` 自定义属性中的残留字段
- 清理 `PDF` 的 `/Info`、XMP 等底层元数据
- 支持批量处理 `doc`、`docx`、`pdf`

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

## 说明

- 脚本会自动跳过已经带有 `(cleaned)` 标记的文件
- `DOC` 文件会先转换为 `DOCX`，再执行深度清理
