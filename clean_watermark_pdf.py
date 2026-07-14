import os
import re
import atexit
import tempfile
import multiprocessing as mp
import queue as _queue

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


def clean_page_content(doc, keywords, remove_all_header=False):
    print("正在扫描并清理动态标记...")
    for page_index, page in enumerate(doc, start=1):
        words = page.get_text("words")
        height = page.rect.height

        for word in words:
            text_content = word[4]
            if ID_PATTERN.search(text_content):
                rect = fitz.Rect(word[:4])
                page.add_redact_annot(rect, fill=(1, 1, 1))
                print(f"已定位并清除第 {page_index} 页动态 ID: {text_content}")

        if remove_all_header:
            header_limit = height * 0.1
            for word in words:
                if word[1] < header_limit:
                    rect = fitz.Rect(word[:4])
                    page.add_redact_annot(rect, fill=(1, 1, 1))
            print(f"已清除第 {page_index} 页页眉区域全部内容")

        for keyword in keywords:
            for inst in page.search_for(keyword):
                if inst.y1 > height * 0.9 or inst.y0 < height * 0.1:
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


def _deep_clean_core(source_path, target_path, config):
    """真正执行底层元数据深度清理（在子进程中运行，可被超时强杀）。

    失败时直接抛异常，由调用方决定降级策略；自身不负责回退。
    """
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
                    try:
                        deep_doc.xref_set_key(xref, key, "null")
                        print(f"已定位并清除底层元数据 xref={xref} key={key}: {value}")
                    except ValueError as set_err:
                        # 个别对象（如含非法字符键名的脏键、位于压缩对象流中的对象）
                        # 不支持直接修改，跳过该键以保证整个文件处理不中断。
                        print(f"跳过无法修改的底层元数据 xref={xref} key={key}: {set_err}")

        # 注意：之前用 garbage=4 + clean=True，对损坏/增量更新的 PDF 会卡死，
        # 或把页面对象误清导致 "cannot save with zero pages"。改为更温和的 garbage=1，
        # 不再强制重建结构，避免这两种故障。
        deep_doc.save(temp_target, garbage=1, deflate=True)
        deep_doc.close()
        os.replace(temp_target, target_path)
    finally:
        if os.path.exists(temp_target):
            try:
                os.remove(temp_target)
            except OSError:
                pass


def _fallback_to_source(source_path, target_path):
    """deep clean 失败/超时时，用已清页眉的版本（source_path）作为最终结果，
    保证文件至少完成了页眉/正文水印清理，且不会被损坏。
    """
    if os.path.exists(source_path):
        try:
            os.replace(source_path, target_path)
        except OSError:
            pass


def _deep_clean_worker_loop(job_q, result_q):
    """子进程入口：循环接收 deep clean 任务并执行。"""
    while True:
        item = job_q.get()
        if item is None:
            break
        source_path, target_path, config = item
        try:
            _deep_clean_core(source_path, target_path, config)
            result_q.put(("ok", None))
        except Exception as exc:
            result_q.put(("err", f"{type(exc).__name__}: {exc}"))


class _DeepCleanPool:
    """持久子进程池（大小为 1）：正常文件零额外开销；遇到挂死文件可在超时后
    强杀子进程并重建，从而保护整个批处理不被单个坏文件拖垮。
    """

    def __init__(self, timeout=90):
        self.timeout = timeout
        self._start()

    def _start(self):
        ctx = mp.get_context("spawn")
        self.job_q = ctx.Queue()
        self.result_q = ctx.Queue()
        self.proc = ctx.Process(
            target=_deep_clean_worker_loop,
            args=(self.job_q, self.result_q),
            daemon=True,
        )
        self.proc.start()

    def run(self, source_path, target_path, config):
        self.job_q.put((source_path, target_path, config))
        try:
            status, err = self.result_q.get(timeout=self.timeout)
        except _queue.Empty:
            # 超时：子进程极可能卡死，强制杀掉并重建，后续文件不受影响。
            try:
                self.proc.kill()
            except Exception:
                pass
            self.proc.join()
            self._start()
            return ("timeout", None)
        return (status, err)

    def close(self):
        try:
            self.job_q.put(None)
        except Exception:
            pass
        try:
            self.proc.kill()
        except Exception:
            pass
        try:
            self.proc.join(timeout=5)
        except Exception:
            pass


_deep_pool = None
_pool_disabled = False


def _get_pool():
    global _deep_pool, _pool_disabled
    if _pool_disabled:
        return None
    if _deep_pool is None:
        try:
            _deep_pool = _DeepCleanPool(timeout=90)
        except Exception:
            _pool_disabled = True
            return None
    return _deep_pool


@atexit.register
def _close_deep_pool():
    global _deep_pool
    if _deep_pool is not None:
        try:
            _deep_pool.close()
        except Exception:
            pass
        _deep_pool = None


def deep_clean_pdf_metadata(source_path, target_path, config):
    """带超时保护的底层元数据深度清理入口。

    - 正常：子进程完成清理并写回 target_path。
    - 超时/异常：降级为「仅保留页眉清理结果」（用 source_path 覆盖 target_path），
      并在日志中提示，绝不让单个坏文件卡住整个批处理。
    """
    pool = _get_pool()
    if pool is None:
        # 子进程池不可用时的降级路径（无超时保护，但至少失败时回退不损坏文件）。
        try:
            _deep_clean_core(source_path, target_path, config)
        except Exception as exc:
            print(f"⚠ 底层元数据深度清理失败: {exc}，保留页眉清理结果")
            _fallback_to_source(source_path, target_path)
        return

    status, err = pool.run(source_path, target_path, config)
    if status == "ok":
        return
    if status == "timeout":
        print(f"⚠ 底层元数据深度清理超时({pool.timeout}s)，跳过该文件元数据清理（保留页眉清理结果）: {target_path}")
    else:
        print(f"⚠ 底层元数据深度清理失败: {err}，保留页眉清理结果: {target_path}")
    _fallback_to_source(source_path, target_path)


def clean_pdf(input_path, output_path=None, remove_all_header=None):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"找不到文件: {input_path}")

    if output_path is None:
        output_path = build_output_path(input_path)

    config = load_config()
    if remove_all_header is not None:
        config["remove_all_header_content"] = remove_all_header
    if not config["metadata_keywords"]:
        config["metadata_keywords"] = DEFAULT_KEYWORDS

    doc = fitz.open(input_path)
    clean_page_content(doc, config["metadata_keywords"], remove_all_header=config.get("remove_all_header_content", False))
    clean_standard_metadata(doc, config)

    output_dir = os.path.dirname(os.path.abspath(output_path)) or os.getcwd()
    temp_fd, temp_output = tempfile.mkstemp(suffix=".pdf", dir=output_dir)
    os.close(temp_fd)

    try:
        doc.save(temp_output, garbage=1, deflate=True, clean=True)
        doc.close()
        deep_clean_pdf_metadata(temp_output, output_path, config)
    finally:
        if os.path.exists(temp_output):
            try:
                os.remove(temp_output)
            except OSError:
                pass

    return output_path


if __name__ == "__main__":
    source = "水印语文试题.pdf"
    result = clean_pdf(source)
    print(f"\n清理完成！保存至: {result}")
