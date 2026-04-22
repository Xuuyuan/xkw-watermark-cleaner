import os
import tempfile

from win32com.client import DispatchEx

from clean_watermark_docx import clean_docx


WD_FORMAT_XML_DOCUMENT = 12
WD_FORMAT_BINARY_DOCUMENT = 0


def build_output_path(input_path):
    root, _ = os.path.splitext(input_path)
    return f"{root}(cleaned).docx"


def convert_doc_to_docx(input_doc_path, output_docx_path):
    word = None
    document = None

    try:
        print(f"正在将 DOC 转换为 DOCX: {input_doc_path}")
        word = DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        document = word.Documents.Open(os.path.abspath(input_doc_path), ReadOnly=True)
        document.SaveAs(os.path.abspath(output_docx_path), FileFormat=WD_FORMAT_XML_DOCUMENT)
    finally:
        if document is not None:
            document.Close(False)
        if word is not None:
            word.Quit()


def convert_docx_to_doc(input_docx_path, output_doc_path):
    word = None
    document = None

    try:
        print(f"正在将清理结果写回 DOC: {output_doc_path}")
        word = DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        document = word.Documents.Open(os.path.abspath(input_docx_path), ReadOnly=True)
        document.SaveAs(os.path.abspath(output_doc_path), FileFormat=WD_FORMAT_BINARY_DOCUMENT)
    finally:
        if document is not None:
            document.Close(False)
        if word is not None:
            word.Quit()


def clean_doc(input_path, output_path=None):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"找不到文件: {input_path}")

    if output_path is None:
        output_path = build_output_path(input_path)

    print("正在扫描并清理 DOC 水印...")
    output_dir = os.path.dirname(os.path.abspath(output_path)) or os.getcwd()
    temp_fd, temp_docx_path = tempfile.mkstemp(suffix=".docx", dir=output_dir)
    os.close(temp_fd)

    try:
        convert_doc_to_docx(input_path, temp_docx_path)
        return clean_docx(temp_docx_path, output_path)
    finally:
        if os.path.exists(temp_docx_path):
            os.remove(temp_docx_path)


if __name__ == "__main__":
    source = "水印历史答题卡.doc"
    result = clean_doc(source)
    print(f"清理成功！已生成：{result}")
