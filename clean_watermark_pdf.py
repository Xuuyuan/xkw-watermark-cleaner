import os
import re
import tempfile

import fitz

from cleaner_config import load_config


DEFAULT_KEYWORDS = ["学科网", "zxxk.com", "rbm.xkw.com", "xkw"]
ID_PATTERN = re.compile(r"\{#\{[A-Za-z0-9+/=]+\}#\}")


def build_output_path(input_path):
    root, _ = os.path.splitext(input_path)
    return f"{root}(cleaned).pdf"


def contains_keyword(value, keywords):
    if value is None:
        return False
    lower_value = str(value).lower()
    return any(keyword.lower() in lower_value for keyword in keywords)


def clean_page_content(doc, keywords):
    print("正在扫描并清理动态标记...")
    for page_index, page in enumerate(doc, start=1):
        words = page.get_text("words")

        for word in words:
            text_content = word[4]
            if ID_PATTERN.search(text_content):
                rect = fitz.Rect(word[:4])
                page.add_redact_annot(rect, fill=(1, 1, 1))
                print(f"已定位并清除第 {page_index} 页动态 ID: {text_content}")

        for keyword in keywords:
            for inst in page.search_for(keyword):
                if inst.y1 > page.rect.height * 0.9 or inst.y0 < page.rect.height * 0.1:
                    page.add_redact_annot(inst, fill=(1, 1, 1))
                    print(f"已定位并清除第 {page_index} 页页边关键词: {keyword}")

        page.apply_redactions()


def clean_standard_metadata(doc, config):
    pdf_config = config["pdf_metadata"]
    keywords = config["metadata_keywords"]
    override_enabled = pdf_config["override_enabled"]
    configured_values = pdf_config["values"]
    cleaned_metadata = dict(doc.metadata or {})

    if override_enabled:
        for key, configured_value in configured_values.items():
            if configured_value == "-":
                continue
            current_value = cleaned_metadata.get(key, "") or ""
            if current_value != configured_value:
                print(f"已按配置重写 PDF 标准元数据 {key}: {current_value}")
            cleaned_metadata[key] = configured_value
        doc.set_metadata(cleaned_metadata)
        return

    for key, value in (doc.metadata or {}).items():
        if value and contains_keyword(value, keywords):
            print(f"已定位并清除标准元数据 {key}: {value}")
            cleaned_metadata[key] = ""
    doc.set_metadata(cleaned_metadata)


def should_clear_xmp_metadata(doc, config):
    clear_mode = config["pdf_metadata"]["clear_xmp_metadata"]
    if clear_mode == "never":
        return False
    if clear_mode == "always":
        return True

    try:
        xml_metadata = doc.get_xml_metadata()
    except Exception:
        return False

    return contains_keyword(xml_metadata, config["metadata_keywords"])


def clear_xmp_metadata(doc):
    try:
        doc.del_xml_metadata()
        print("已定位并清除 XMP 元数据")
        return
    except Exception:
        pass

    try:
        doc.set_xml_metadata("")
        print("已定位并清除 XMP 元数据")
    except Exception:
        pass


def deep_clean_pdf_metadata(source_path, target_path, config):
    output_dir = os.path.dirname(os.path.abspath(target_path)) or os.getcwd()
    temp_fd, temp_target = tempfile.mkstemp(suffix=".pdf", dir=output_dir)
    os.close(temp_fd)

    try:
        deep_doc = fitz.open(source_path)
        clean_standard_metadata(deep_doc, config)

        if should_clear_xmp_metadata(deep_doc, config):
            clear_xmp_metadata(deep_doc)

        for xref in range(1, deep_doc.xref_length()):
            try:
                keys = deep_doc.xref_get_keys(xref)
            except Exception:
                continue

            if not keys:
                continue

            for key in keys:
                try:
                    _, value = deep_doc.xref_get_key(xref, key)
                except Exception:
                    continue

                if contains_keyword(value, config["metadata_keywords"]):
                    deep_doc.xref_set_key(xref, key, "null")
                    print(f"已定位并清除底层元数据 xref={xref} key={key}: {value}")

        deep_doc.save(temp_target, garbage=4, deflate=True, clean=True)
        deep_doc.close()
        os.replace(temp_target, target_path)
    finally:
        if os.path.exists(temp_target):
            os.remove(temp_target)


def clean_pdf(input_path, output_path=None):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"找不到文件: {input_path}")

    if output_path is None:
        output_path = build_output_path(input_path)

    config = load_config()
    if not config["metadata_keywords"]:
        config["metadata_keywords"] = DEFAULT_KEYWORDS

    doc = fitz.open(input_path)
    clean_page_content(doc, config["metadata_keywords"])
    clean_standard_metadata(doc, config)

    output_dir = os.path.dirname(os.path.abspath(output_path)) or os.getcwd()
    temp_fd, temp_output = tempfile.mkstemp(suffix=".pdf", dir=output_dir)
    os.close(temp_fd)

    try:
        doc.save(temp_output, garbage=4, deflate=True, clean=True)
        doc.close()
        deep_clean_pdf_metadata(temp_output, output_path, config)
    finally:
        if os.path.exists(temp_output):
            os.remove(temp_output)

    return output_path


if __name__ == "__main__":
    source = "水印语文试题.pdf"
    result = clean_pdf(source)
    print(f"\n清理完成！保存至: {result}")
