import os
import tempfile
import zipfile

from docx import Document
from docx.shared import Inches
from lxml import etree


SIZE_THRESHOLD = Inches(0.2)
HEADER_FOOTER_KEYWORDS = ["学科网", "zxxk.com", "北京）股份有限公司"]
BODY_TEXT_KEYWORDS = [
    "zxxk.com",
    "学科网（北京）股份有限公司",
    "学科网(北京)股份有限公司",
    "北京）股份有限公司",
]
METADATA_KEYWORDS = ["学科网", "zxxk.com", "rbm.xkw.com", "xkw"]
BODY_DRAWING_KEYWORDS = ["学科网", "zxxk.com", "rbm.xkw.com", "xkw"]
CUSTOM_PROPERTY_NS = {
    "cp": "http://schemas.openxmlformats.org/officeDocument/2006/custom-properties"
}


def build_output_path(input_path):
    root, _ = os.path.splitext(input_path)
    return f"{root}(cleaned).docx"


def has_keyword_text(text, keywords):
    return any(keyword.lower() in text.lower() for keyword in keywords)


def first_matched_keyword(text, keywords):
    lower_text = text.lower()
    for keyword in keywords:
        if keyword.lower() in lower_text:
            return keyword
    return None


def iter_extents(element):
    return element.xpath('.//*[local-name()="extent"]')


def iter_drawings(container_element):
    return container_element.xpath('.//*[local-name()="drawing"]')


def iter_shapes(container_element):
    return container_element.xpath('.//*[local-name()="shape"]')


def is_tiny_element(element):
    try:
        for ext in iter_extents(element):
            width = int(ext.get("cx", 0))
            height = int(ext.get("cy", 0))
            if 0 < width < SIZE_THRESHOLD and 0 < height < SIZE_THRESHOLD:
                return True
    except Exception:
        return False
    return False


def is_target_element(element, keywords=None):
    try:
        xml_str = etree.tostring(element, encoding="unicode")
        if keywords and has_keyword_text(xml_str, keywords):
            return True
    except Exception:
        return False
    return is_tiny_element(element)


def remove_element(element, message=None):
    parent = element.getparent()
    if parent is not None:
        parent.remove(element)
        if message:
            print(message)


def scrub_descr_attributes(element, keywords, location_label):
    for node in element.iter():
        for attr_name in ("descr", "title"):
            attr_value = node.get(attr_name)
            if attr_value and has_keyword_text(attr_value, keywords):
                node.set(attr_name, "")
                print(f"已定位并清除{location_label}隐藏属性 {attr_name}: {attr_value}")


def clean_header_footer_container(container, location_label):
    for drawing in iter_drawings(container._element):
        if is_target_element(drawing, HEADER_FOOTER_KEYWORDS):
            remove_element(drawing, f"已定位并清除{location_label}绘图对象水印")

    for shape in iter_shapes(container._element):
        if is_target_element(shape, HEADER_FOOTER_KEYWORDS):
            remove_element(shape, f"已定位并清除{location_label}形状对象水印")

    for paragraph in container.paragraphs:
        if has_keyword_text(paragraph.text, HEADER_FOOTER_KEYWORDS):
            print(f"已定位并清除{location_label}文本水印: {paragraph.text}")
            paragraph.text = ""


def clean_section_headers_and_footers(doc):
    for section in doc.sections:
        containers = [
            ("页眉", section.header),
            ("页脚", section.footer),
            ("首页页眉", section.first_page_header),
            ("首页页脚", section.first_page_footer),
            ("偶数页页眉", section.even_page_header),
            ("偶数页页脚", section.even_page_footer),
        ]
        for location_label, container in containers:
            clean_header_footer_container(container, location_label)


def clean_body_paragraph(paragraph, paragraph_index):
    for drawing in iter_drawings(paragraph._element):
        if is_tiny_element(drawing):
            remove_element(drawing, f"已定位并清除正文段落 {paragraph_index} 中的微小绘图水印")
        else:
            scrub_descr_attributes(drawing, BODY_DRAWING_KEYWORDS, f"正文段落 {paragraph_index} 的绘图对象")

    for shape in iter_shapes(paragraph._element):
        if is_tiny_element(shape):
            remove_element(shape, f"已定位并清除正文段落 {paragraph_index} 中的微小形状水印")
        else:
            scrub_descr_attributes(shape, BODY_DRAWING_KEYWORDS, f"正文段落 {paragraph_index} 的形状对象")

    if has_keyword_text(paragraph.text, BODY_TEXT_KEYWORDS):
        print(f"已定位并清除正文段落 {paragraph_index} 文本水印: {paragraph.text}")
        paragraph.text = ""


def clean_document_body(doc):
    for index, paragraph in enumerate(doc.paragraphs, start=1):
        clean_body_paragraph(paragraph, index)


def clean_core_properties(doc):
    try:
        props = doc.core_properties
        if props.author:
            print(f"已定位并重写核心属性 author: {props.author}")
        props.author = "User"
        if props.comments:
            print(f"已定位并清除核心属性 comments: {props.comments}")
        props.comments = ""
        if props.title:
            print(f"已定位并重写核心属性 title: {props.title}")
        props.title = "清理后的文档"
        if props.subject:
            print(f"已定位并重写核心属性 subject: {props.subject}")
        props.subject = ""
        if props.keywords:
            print(f"已定位并清除核心属性 keywords: {props.keywords}")
        props.keywords = ""
    except Exception:
        pass


def clean_custom_properties_xml(xml_bytes, keywords):
    root = etree.fromstring(xml_bytes)
    for prop in list(root.findall("cp:property", CUSTOM_PROPERTY_NS)):
        prop_text = "".join(prop.itertext())
        if has_keyword_text(prop_text, keywords):
            print(f"已定位并清除自定义属性 {prop.get('name')}: {prop_text}")
            root.remove(prop)
    return etree.tostring(root, encoding="utf-8", xml_declaration=True, standalone="yes")


def rebuild_docx_without_custom_property_residue(source_docx_path, target_docx_path, keywords):
    if not os.path.exists(source_docx_path):
        return

    output_dir = os.path.dirname(os.path.abspath(target_docx_path)) or os.getcwd()
    temp_fd, temp_path = tempfile.mkstemp(suffix=".docx", dir=output_dir)
    os.close(temp_fd)

    try:
        with zipfile.ZipFile(source_docx_path, "r") as src, zipfile.ZipFile(temp_path, "w") as dst:
            for item in src.infolist():
                data = src.read(item.filename)
                if item.filename == "docProps/custom.xml":
                    data = clean_custom_properties_xml(data, keywords)
                dst.writestr(item, data)

        os.replace(temp_path, target_docx_path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def save_cleaned_docx(doc, output_path):
    output_dir = os.path.dirname(os.path.abspath(output_path)) or os.getcwd()
    temp_doc_fd, temp_doc_path = tempfile.mkstemp(suffix=".docx", dir=output_dir)
    os.close(temp_doc_fd)

    try:
        doc.save(temp_doc_path)
        rebuild_docx_without_custom_property_residue(temp_doc_path, output_path, METADATA_KEYWORDS)
    finally:
        if os.path.exists(temp_doc_path):
            os.remove(temp_doc_path)


def clean_docx(input_path, output_path=None):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"找不到文件: {input_path}")

    if output_path is None:
        output_path = build_output_path(input_path)

    print("正在扫描并清理 DOCX 水印...")
    doc = Document(input_path)
    clean_section_headers_and_footers(doc)
    clean_document_body(doc)
    clean_core_properties(doc)
    save_cleaned_docx(doc, output_path)
    return output_path


if __name__ == "__main__":
    source = "水印语文试题.docx"
    target = build_output_path(source)
    result = clean_docx(source, target)
    print(f"清理成功！已生成：{result}")
