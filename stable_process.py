# -*- coding: utf-8 -*-
"""大文件专用稳定处理：先检测后处理。

设计目标：
1. 处理前先「检测」文件特征（大小 / PDF 页数 / xref 对象数 / 是否加密 / 类型），
   判定其是否为「大文件或高风险文件」。
2. 对普通文件走原有内联快速处理；对大文件 / 高风险文件（如需要 COM 自动化的 .doc）
   走「独立子进程 + 超时强杀」的稳定通道，必要时用进程池并发处理，互不阻塞。

为何用「子进程」而非「线程」：Python 线程无法强制终止一个卡死在 C 扩展
（PyMuPDF 的 save、WPS 的 COM 调用）里的调用；只有独立进程能被 kill。
因此「稳定」= 进程级超时强杀，这是真正能从挂死中恢复的唯一办法。
"""

import multiprocessing as mp
import os
import sys
import traceback
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

# 项目根：spawn 出的子进程需要能 import clean_watermark 等模块
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# ---------------- 可调整阈值 ----------------
LARGE_SIZE_BYTES = 5 * 1024 * 1024     # 体积 > 5 MB 视为大文件
LARGE_PDF_PAGES = 50                    # PDF 页数 > 50 视为大文件
LARGE_PDF_XREF = 3000                   # PDF xref 对象数 > 3000 视为大文件
SUPERVISED_TIMEOUT = 120                # 单文件监督处理超时（秒）
CONCURRENT_WORKERS = 2                  # 大文件并发进程数（保守，避免 WPS/COM 抢占）
# --------------------------------------------


def profile_file(path):
    """快速检测文件特征，不修改文件。返回 dict。

    重点：大体积 PDF 不再打开内部对象（避免检测本身变慢/挂死），
    仅依据体积判定；中小 PDF 才打开读取页数 / xref。
    """
    path = Path(path)
    prof = {
        "path": str(path),
        "name": path.name,
        "size": 0,
        "kind": "other",
        "is_large": False,
        "pages": None,
        "xref": None,
        "encrypted": None,
        "note": "",
    }
    try:
        prof["size"] = path.stat().st_size
    except OSError as e:
        prof["note"] = f"无法读取大小: {e}"
        return prof

    ext = path.suffix.lower()
    if ext == ".pdf":
        prof["kind"] = "pdf"
        # 仅对中小体积 PDF 打开内部检测，大 PDF 直接按体积判定
        if prof["size"] <= LARGE_SIZE_BYTES * 4:
            try:
                import fitz
                doc = fitz.open(str(path))
                prof["encrypted"] = doc.is_encrypted
                prof["pages"] = doc.page_count
                # 注意：PyMuPDF 里 xref_length 是「方法」，必须调用才能拿到数量；
                # 若写成 doc.xref_length（漏括号），prof["xref"] 会变成方法对象，
                # 后续与阈值比较时抛 TypeError，进而让整个文件夹检测阶段崩溃。
                prof["xref"] = doc.xref_length()
                doc.close()
            except Exception as e:
                prof["note"] = f"PDF 检测失败: {e}"
        else:
            prof["note"] = "大体积PDF，跳过内部检测"
    elif ext == ".docx":
        prof["kind"] = "docx"
    elif ext == ".doc":
        prof["kind"] = "doc"          # 需要 COM 自动化，属高风险，一律监督处理
    elif ext == ".zip":
        prof["kind"] = "zip"
    else:
        prof["kind"] = "other"

    # 判定是否需要监督处理
    large = prof["size"] > LARGE_SIZE_BYTES
    if prof["kind"] == "pdf":
        if prof["pages"] is not None and prof["pages"] > LARGE_PDF_PAGES:
            large = True
        if prof["xref"] is not None and prof["xref"] > LARGE_PDF_XREF:
            large = True
    prof["is_large"] = large
    return prof


def needs_supervision(prof):
    """是否走监督通道：大文件，或需要 COM 自动化的 .doc（已知易挂死）。"""
    return prof["is_large"] or prof["kind"] == "doc"


# ---------------- 子进程内部工作函数 ----------------
def _inner_worker(q, path_str, overwrite, remove_headers):
    """在 spawn 出的子进程里真正调用 clean_*，结果通过队列回传。"""
    try:
        if PROJECT_ROOT not in sys.path:
            sys.path.insert(0, PROJECT_ROOT)
        import clean_watermark
        from clean_watermark_doc import SkipFile
        func = (clean_watermark.clean_one_file_overwrite
                if overwrite else clean_watermark.clean_one_file)
        out = func(Path(path_str), remove_all_header=remove_headers)
        q.put(("ok", str(out) if out else None, ""))
    except SkipFile as skip_exc:
        # 环境原因（如本机无 Word）无法处理，记为跳过而非失败
        q.put(("skip", None, str(skip_exc)))
    except Exception as e:
        q.put(("error", None, f"{type(e).__name__}: {e}"))


def process_file_supervised(path, overwrite=False, remove_headers=True,
                            timeout=SUPERVISED_TIMEOUT):
    """在独立子进程中处理单文件，带超时保护。

    返回 (status, output_path, note)：
        status: 'ok' | 'error' | 'timeout'
    超时则强杀子进程并标记 'timeout'（不阻塞调用方）。
    """
    ctx = mp.get_context("spawn")
    q = ctx.Queue()
    p = ctx.Process(target=_inner_worker,
                    args=(q, str(path), overwrite, remove_headers))
    p.start()
    p.join(timeout)
    if p.is_alive():
        p.kill()
        p.join()
        return ("timeout", None, f"处理超时({timeout}s)，已跳过并强杀子进程")
    if not q.empty():
        return q.get()
    # 子进程已退出但无返回（极端异常）
    return ("error", None, "子进程异常退出，无返回")


# ---------------- 并发处理大文件 ----------------
def _pool_worker(path_str, overwrite, remove_headers, timeout):
    """进程池工作函数：对单个大文件调用监督处理。"""
    try:
        return process_file_supervised(path_str, overwrite, remove_headers, timeout)
    except Exception as e:
        return ("error", None, f"{type(e).__name__}: {e}")


def process_large_files_concurrent(paths, overwrite=False, remove_headers=True,
                                    timeout=SUPERVISED_TIMEOUT,
                                    max_workers=CONCURRENT_WORKERS):
    """对一批大文件/风险文件用进程池并发稳定处理。

    生成器，逐个 yield (path, status, output_path, note)。
    注意：并发的是「编排层」（进程池），每个文件的实际清理仍在各自
    独立子进程（process_file_supervised）中带超时执行——这样才能在
    单个文件挂死时被强杀而不拖垮其它文件。
    """
    ctx = mp.get_context("spawn")
    paths = list(paths)
    if not paths:
        return
    with ProcessPoolExecutor(max_workers=min(max_workers, len(paths)),
                              mp_context=ctx) as ex:
        futures = {ex.submit(_pool_worker, str(p), overwrite, remove_headers,
                             timeout): p for p in paths}
        # 按提交顺序返回，便于日志有序
        for fut in futures:
            p = futures[fut]
            try:
                status, out, note = fut.result()
            except Exception as e:
                status, out, note = "error", None, f"{type(e).__name__}: {e}"
            yield (p, status, out, note)


if __name__ == "__main__":
    # 简单自测：对传入的文件做检测 + 监督处理
    import time
    for arg in sys.argv[1:]:
        prof = profile_file(arg)
        print(f"[检测] {prof['name']} kind={prof['kind']} "
              f"size={prof['size']} is_large={prof['is_large']} note={prof['note']}")
        t0 = time.time()
        st, out, note = process_file_supervised(arg, overwrite=True,
                                                remove_headers=True)
        print(f"[处理] status={st} out={out} note={note} "
              f"耗时={time.time()-t0:.1f}s")
