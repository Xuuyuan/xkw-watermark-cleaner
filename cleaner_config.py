import json
import os


CONFIG_FILENAME = "config.json"
DEFAULT_METADATA_KEYWORDS = ["学科网", "zxxk.com", "zxxk", "rbm.xkw.com", "xkw"]
DEFAULT_CONFIG = {
    "remove_all_header_content": False,
    "metadata_keywords": DEFAULT_METADATA_KEYWORDS,
    "docx_core_properties": {
        "override_enabled": False,
        "values": {
            "author": "User",
            "comments": "",
            "title": "清理后的文档",
            "subject": "",
            "keywords": "",
        },
    },
    "pdf_metadata": {
        "override_enabled": False,
        "clear_xmp_metadata": "if_keyword",
        "values": {
            "title": "",
            "author": "",
            "subject": "",
            "keywords": "",
            "creator": "-",
            "producer": "-",
            "creationDate": "-",
            "modDate": "-",
        },
    },
}


def normalize_text_value(value):
    if value is None:
        return ""
    return str(value)


def merge_property_config(config, user_config, section_name):
    section = user_config.get(section_name)
    if not isinstance(section, dict):
        return

    override_enabled = section.get("override_enabled")
    if isinstance(override_enabled, bool):
        config[section_name]["override_enabled"] = override_enabled

    if section_name == "pdf_metadata":
        clear_xmp_metadata = section.get("clear_xmp_metadata")
        if clear_xmp_metadata in {"always", "if_keyword", "never"}:
            config[section_name]["clear_xmp_metadata"] = clear_xmp_metadata

    values = section.get("values")
    if isinstance(values, dict):
        for key in config[section_name]["values"]:
            if key in values:
                config[section_name]["values"][key] = normalize_text_value(values[key])


def build_default_config():
    return {
        "remove_all_header_content": DEFAULT_CONFIG["remove_all_header_content"],
        "metadata_keywords": list(DEFAULT_CONFIG["metadata_keywords"]),
        "docx_core_properties": {
            "override_enabled": DEFAULT_CONFIG["docx_core_properties"]["override_enabled"],
            "values": dict(DEFAULT_CONFIG["docx_core_properties"]["values"]),
        },
        "pdf_metadata": {
            "override_enabled": DEFAULT_CONFIG["pdf_metadata"]["override_enabled"],
            "clear_xmp_metadata": DEFAULT_CONFIG["pdf_metadata"]["clear_xmp_metadata"],
            "values": dict(DEFAULT_CONFIG["pdf_metadata"]["values"]),
        },
    }


def load_config():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILENAME)
    config = build_default_config()

    if not os.path.exists(config_path):
        return config

    try:
        with open(config_path, "r", encoding="utf-8") as config_file:
            user_config = json.load(config_file)
    except Exception as exc:
        print(f"读取配置文件失败，使用默认配置: {exc}")
        return config

    remove_all_header = user_config.get("remove_all_header_content")
    if isinstance(remove_all_header, bool):
        config["remove_all_header_content"] = remove_all_header

    metadata_keywords = user_config.get("metadata_keywords")
    if isinstance(metadata_keywords, list) and metadata_keywords:
        config["metadata_keywords"] = [normalize_text_value(item) for item in metadata_keywords]

    merge_property_config(config, user_config, "docx_core_properties")
    merge_property_config(config, user_config, "pdf_metadata")
    return config


def save_config(config):
    """保存配置到 config.json"""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILENAME)
    # 只保存需要的字段（简化版）
    simple_config = {
        "metadata_keywords": config.get("metadata_keywords", DEFAULT_METADATA_KEYWORDS),
        "remove_headers": config.get("remove_headers", True),
        "clean_metadata": config.get("clean_metadata", True),
        "remove_all_images": config.get("remove_all_images", False),
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(simple_config, f, ensure_ascii=False, indent=2)
    return True
