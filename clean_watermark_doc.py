import os
import tempfile

from win32com.client import DispatchEx

from clean_watermark_docx import clean_docx


class SkipFile(Exception):
    """文件因环境原因（如本机未安装 Word/WPS）无法处理，应跳过而非记为失败。"""
    pass


# 候选 COM 组件：Microsoft Word 优先，WPS Office 兜底（WPS 的 COM 接口与 Word 兼容）。
_WORD_PROG_IDS = ("Word.Application", "Kwps.Application")
_word_prog_id_cache = None


def detect_word_prog_id():
    """检测本机可用于 .doc 转 .docx 的 COM 组件 ProgID。

    优先尝试 Microsoft Word，其次尝试 WPS Office（其 COM 接口兼容 Word，
    常见 ProgID 为 Kwps.Application）。返回可用的 ProgID 字符串；若都不可用返回
    None。结果缓存，整个进程只探测一次。
    """
    global _word_prog_id_cache
    if _word_prog_id_cache is not None:
        return _word_prog_id_cache
    found = None
    for prog_id in _WORD_PROG_IDS:
        try:
            app = DispatchEx(prog_id)
            app.Quit()
            found = prog_id
            break
        except Exception:
            continue
    _word_prog_id_cache = found
    return found


# 文件格式常量（与 Word VBA 一致，WPS 同样兼容）
WD_FORMAT_XML_DOCUMENT = 12   # wdFormatXMLDocument（.docx）
WD_FORMAT_BINARY_DOCUMENT = 0  # wdFormatDocument（.doc）


def build_output_path(input_path):
    root, _ = os.path.splitext(input_path)
    return f"{root}(cleaned).docx"


def _open_app(prog_id):
    """创建 COM 应用实例：置为不可见并抑制保存格式等警告弹窗。"""
    app = DispatchEx(prog_id)
    app.Visible = False
    try:
        app.DisplayAlerts = 0  # wdAlertsNone：避免转换时弹出兼容性警告
    except Exception:
        pass
    return app


def convert_doc_to_docx(input_doc_path, output_docx_path, prog_id):
    """用指定的 COM 组件将 .doc 转换为 .docx。"""
    word = None
    document = None
    try:
        print(f"正在将 DOC 转换为 DOCX（{prog_id}）: {input_doc_path}")
        word = _open_app(prog_id)
        document = word.Documents.Open(os.path.abspath(input_doc_path), ReadOnly=True)
        document.SaveAs(os.path.abspath(output_docx_path), FileFormat=WD_FORMAT_XML_DOCUMENT)
    finally:
        if document is not None:
            try:
                document.Close(False)
            except Exception:
                pass
        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass


def convert_docx_to_doc(input_docx_path, output_doc_path, prog_id):
    """（备用）将清理后的 .docx 写回为 .doc。"""
    word = None
    document = None
    try:
        print(f"正在将清理结果写回 DOC（{prog_id}）: {output_doc_path}")
        word = _open_app(prog_id)
        document = word.Documents.Open(os.path.abspath(input_docx_path), ReadOnly=True)
        document.SaveAs(os.path.abspath(output_doc_path), FileFormat=WD_FORMAT_BINARY_DOCUMENT)
    finally:
        if document is not None:
            try:
                document.Close(False)
            except Exception:
                pass
        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass


def clean_doc(input_path, output_path=None, remove_all_header=None):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"找不到文件: {input_path}")

    if output_path is None:
        output_path = build_output_path(input_path)

    prog_id = detect_word_prog_id()
    if prog_id is None:
        raise SkipFile(
            "本机未安装 Word 或 WPS Office（COM 组件不可用），无法转换 .doc 文件，已跳过"
            "（请安装 Microsoft Word 或 WPS Office 后重试）"
        )

    print(f"正在扫描并清理 DOC 水印（使用 {prog_id}）...")
    output_dir = os.path.dirname(os.path.abspath(output_path)) or os.getcwd()
    temp_fd, temp_docx_path = tempfile.mkstemp(suffix=".docx", dir=output_dir)
    os.close(temp_fd)

    try:
        convert_doc_to_docx(input_path, temp_docx_path, prog_id)
        return clean_docx(temp_docx_path, output_path, remove_all_header=remove_all_header)
    finally:
        if os.path.exists(temp_docx_path):
            os.remove(temp_docx_path)


if __name__ == "__main__":
    source = "水印历史答题卡.doc"
    result = clean_doc(source)
    print(f"清理成功！已生成：{result}")
