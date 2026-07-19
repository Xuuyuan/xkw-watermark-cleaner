import contextlib
import os
import shutil
import sys
import traceback
import zipfile
from datetime import datetime
from pathlib import Path

from clean_watermark import clean_one_file, clean_one_file_overwrite, collect_files
from clean_watermark_doc import SkipFile
from stable_process import (
    profile_file,
    needs_supervision,
    process_file_supervised,
    process_large_files_concurrent,
)


LOG_FILENAME = "xkw-watermark-cleaner.log"
ARCHIVE_EXTENSIONS = {".zip"}

# 文件名含此字段时，处理后把该字段从文件名里去掉（重命名，不删文件）
MARKER_FIELD = "精品解析："


def _strip_marker(path):
    """若文件名含 MARKER_FIELD，去除该字段并重命名文件（保留扩展名），返回最终路径。

    覆盖模式（原地处理）与非覆盖模式（保留 _cleaned 副本）都适用。
    """
    p = Path(path)
    if MARKER_FIELD not in p.name:
        return p
    new_name = p.name.replace(MARKER_FIELD, "")
    if not new_name:
        # 极端情况：文件名整个就是该字段，补一个默认名避免空文件名
        new_name = "文件" + p.suffix
    dest = p.with_name(new_name)
    # 同名冲突保护：不覆盖已有文件，改用带序号的名字
    if dest.exists() and dest.absolute() != p.absolute():
        base = p.stem.replace(MARKER_FIELD, "")
        suffix = p.suffix
        i = 1
        while True:
            candidate = p.with_name(f"{base}_{i}{suffix}")
            if not candidate.exists():
                dest = candidate
                break
            i += 1
    if dest.absolute() == p.absolute():
        return p
    try:
        p.rename(dest)
        print(f"文件名含『{MARKER_FIELD}』，已重命名为: {dest.name}")
        return dest
    except Exception as exc:
        print(f"重命名含『{MARKER_FIELD}』文件失败: {p.name} ({exc})")
        return p


def _strip_marker_both(original_path, output_path):
    """清理完成后：把输出文件名的 MARKER_FIELD 去掉；非覆盖模式下原文件仍在，
    也一并去掉其名里的字段。返回输出最终路径。
    """
    out = _strip_marker(output_path)
    orig = Path(original_path)
    try:
        if orig.exists() and orig.absolute() != Path(output_path).absolute():
            _strip_marker(orig)
    except Exception:
        pass
    return out


def _strip_marker_in_tree(root):
    """递归去除目录树内所有文件/文件夹名里的 MARKER_FIELD（重命名，不删）。

    压缩包解压后，其内部的文件夹或文件名可能自带『精品解析：』，单文件处理只改了
    被处理过的文件、未触及文件夹与未处理的文件，这里统一兜底清理整棵目录树。
    最深优先，避免父目录改名后破坏子项路径。
    """
    root = Path(root)
    if not root.exists():
        return
    entries = [p for p in root.rglob("*") if MARKER_FIELD in p.name]
    # 从最深层到最浅层，保证先处理子项、再处理父目录
    entries.sort(key=lambda p: len(p.relative_to(root).parts), reverse=True)
    for p in entries:
        new_name = p.name.replace(MARKER_FIELD, "")
        if not new_name:
            new_name = "文件" + p.suffix
        dest = p.with_name(new_name)
        if dest.absolute() == p.absolute():
            continue
        # 同名冲突保护：改用带前缀的名字防覆盖
        if dest.exists():
            base = p.parent / new_name
            i = 1
            while dest.exists():
                stem, suffix = os.path.splitext(new_name)
                dest = p.parent / f"{stem}__{i}{suffix}"
                i += 1
        try:
            p.rename(dest)
            print(f"已去除目录树中的『{MARKER_FIELD}』: {p.name} -> {dest.name}")
        except Exception as exc:
            print(f"重命名失败: {p.name} ({exc})")


def append_log_header(log_file, target, overwrite, remove_headers, is_dir=False):
    target_path = Path(target)
    if is_dir:
        mode_text = "生成清理后文件"
    else:
        suffix = target_path.suffix.lower()
        if overwrite and suffix in {".docx", ".pdf"}:
            mode_text = "覆盖源文件"
        elif overwrite and suffix == ".doc":
            mode_text = "覆盖模式（DOC 将生成清理后 DOCX，不回写源 DOC）"
        else:
            mode_text = "生成清理后文件"

    if remove_headers:
        mode_text += " + 删除页眉"

    log_file.write("\n")
    log_file.write("=" * 72 + "\n")
    log_file.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    log_file.write(f"目标: {target_path}\n")
    log_file.write(f"模式: {mode_text}\n")
    log_file.write("=" * 72 + "\n")
    log_file.flush()


def process_file(target_path, overwrite, remove_headers, log_file, strip_marker=True):
    """处理单个文件。返回 True=成功 / False=失败 / "skip"=环境原因跳过。

    大文件 / 风险文件（如需要 COM 自动化的 .doc）走「监督子进程 + 超时强杀」，
    单个文件挂死也不会卡住全局。
    """
    prof = profile_file(target_path)
    if needs_supervision(prof):
        print(f"开始处理(监督): {target_path}")
        status, output_path, note = process_file_supervised(
            target_path, overwrite=overwrite, remove_headers=remove_headers)
        if status == "ok":
            print(f"处理完成: {output_path}")
            if strip_marker:
                _strip_marker_both(target_path, output_path)
            return True
        elif status == "skip":
            print(f"跳过: {target_path}")
            print(f"原因: {note}")
            return "skip"
        elif status == "timeout":
            # 超时按跳过计，不计入失败，避免单文件拖垮整批
            print(f"处理超时跳过: {target_path}")
            print(f"原因: {note}")
            return "skip"
        else:
            print(f"处理失败: {target_path}")
            print(f"原因: {note}")
            return False

    # 普通文件：原有内联逻辑
    try:
        print(f"开始处理: {target_path}")
        if overwrite:
            output_path = clean_one_file_overwrite(target_path, remove_all_header=remove_headers)
        else:
            output_path = clean_one_file(target_path, remove_all_header=remove_headers)
        print(f"处理完成: {output_path}")
        if strip_marker:
            _strip_marker_both(target_path, output_path)
        return True
    except SkipFile as skip_exc:
        # 环境原因（如本机未安装 Word）无法处理，记为跳过而非失败，避免刷屏。
        print(f"跳过: {target_path}")
        print(f"原因: {skip_exc}")
        return "skip"
    except Exception as exc:
        print(f"处理失败: {target_path}")
        print(f"原因: {exc}")
        traceback.print_exc()
        return False


def flatten_subfolders(target_path):
    """把 target 下所有层级的子文件夹内容整体上移到 target，并删除已清空的子文件夹。

    用于「平铺」场景：处理完文件夹后，原本分散在各子文件夹里的文件都集中到顶层文件夹，
    整棵目录树被压平。同名冲突自动改名（{子文件夹名}__ 前缀）避免覆盖已处理内容。
    按「从最深层到最浅层」顺序处理，保证嵌套子文件夹也能正确上移、不会提前删父目录。
    """
    target = Path(target_path)
    # 收集所有子目录（不含 target 自身）
    subdirs = [p for p in target.rglob("*") if p.is_dir() and p != target]
    # 最深的先处理：先把最里层的文件上移，再处理外层，避免父目录被提前删
    subdirs.sort(key=lambda p: len(p.parts), reverse=True)
    moved = 0
    for d in subdirs:
        if not d.exists():
            continue
        for item in list(d.iterdir()):
            dest = target / item.name
            if dest.exists():
                # 同名冲突：改名并入，避免覆盖已处理内容
                dest = target / f"{d.name}__{item.name}"
            try:
                shutil.move(str(item), str(dest))
                moved += 1
            except Exception as exc:
                print(f"平铺子文件夹内容失败: {item.name} ({exc})")
        # 删除该子文件夹（rmtree 以防仍有残留空目录/隐藏文件）
        try:
            shutil.rmtree(d)
        except Exception:
            pass
    if moved:
        print(f"已平铺 {moved} 项子文件夹内容到当前文件夹，并移除原子文件夹。")


def process_directory(target_path, overwrite, remove_headers, log_file, flatten=True,
                      strip_marker=True):
    """扫描文件夹内所有支持的文件，先检测后分类处理。

    - 检测阶段：profile_file 判定大文件 / 风险文件。
    - 常规文件：串行内联处理（快）。
    - 大文件 / 风险文件：进程池并发监督处理，单文件超时强杀，互不阻塞。
    - flatten=True（默认，平铺）：压缩包内容提取到当前文件夹，且子文件夹内容也整体上移、
      子文件夹被移除，整棵目录树被压平。flatten=False：压缩包解压到同名子文件夹，
      子文件夹保持原样。
    """
    # 先收集松散的 DOC/DOCX/PDF 文件（此刻压缩包尚未解压，不会被扫到）。
    files = collect_files([target_path], recursive=True)
    # 文件夹内的压缩包（.zip）。先记录下来，等松散文件处理完再解压清理，
    # 避免刚解压出的内容被上面的 collect_files 重复扫描。
    archives = find_archives_in_dir(target_path)

    if not files and not archives:
        print(f"文件夹内没有找到可处理的 DOC / DOCX / PDF / 压缩包文件: {target_path}")
        return True

    success_count = 0
    skip_count = 0
    failed_count = 0

    # ---------- 第一部分：松散的 DOC/DOCX/PDF 文件 ----------
    if files:
        print(f"共发现 {len(files)} 个待处理文件。")
        # 检测阶段：分类
        normal, heavy = [], []
        for f in files:
            prof = profile_file(f)
            if needs_supervision(prof):
                heavy.append(f)
            else:
                normal.append(f)
        print(f"检测完成：常规 {len(normal)} 个，大文件/风险 {len(heavy)} 个（并发稳定处理）。")

        # 常规文件串行
        for file_path in normal:
            result = process_file(file_path, overwrite, remove_headers, log_file,
                                  strip_marker=strip_marker)
            if result is True:
                success_count += 1
            elif result == "skip":
                skip_count += 1
            else:
                failed_count += 1

        # 大文件 / 风险文件：并发监督处理（带超时）
        for f, status, output_path, note in process_large_files_concurrent(
                heavy, overwrite=overwrite, remove_headers=remove_headers):
            if status == "ok":
                print(f"处理完成: {output_path}")
                if strip_marker:
                    _strip_marker_both(f, output_path)
                success_count += 1
            elif status == "skip":
                print(f"跳过: {f}")
                print(f"原因: {note}")
                skip_count += 1
            elif status == "timeout":
                print(f"处理超时跳过: {f}")
                print(f"原因: {note}")
                skip_count += 1
            else:
                print(f"处理失败: {f}")
                print(f"原因: {note}")
                failed_count += 1

    # ---------- 第二部分：文件夹内的压缩包（解压 + 清理） ----------
    archive_ok = 0
    archive_fail = 0
    if archives:
        print(f"\n发现 {len(archives)} 个压缩包，开始逐个解压并清理...")
        for arc in archives:
            try:
                if process_archive(arc, remove_headers, log_file, flatten=flatten,
                                   overwrite=overwrite, strip_marker=strip_marker):
                    archive_ok += 1
                else:
                    archive_fail += 1
            except Exception as exc:
                print(f"压缩包处理失败: {arc}")
                print(f"原因: {exc}")
                traceback.print_exc()
                archive_fail += 1

    # ---------- 第三部分：平铺模式 —— 把子文件夹内容整体上移到当前文件夹 ----------
    if flatten:
        flatten_subfolders(target_path)

    print(
        f"\n文件夹处理完成。"
        f"文件：成功 {success_count} 个，跳过 {skip_count} 个，失败 {failed_count} 个"
        + (f"；压缩包：成功 {archive_ok} 个，失败 {archive_fail} 个" if archives else "")
        + "。"
    )
    return failed_count == 0 and archive_fail == 0


def extract_archive(archive_path, dest_dir):
    """使用 Python 内置 zipfile 解压 .zip 压缩包到目标目录。"""
    archive_path = Path(archive_path)
    suffix = archive_path.suffix.lower()

    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    print(f"正在解压: {archive_path.name} -> {dest_dir}")

    if suffix == ".zip":
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(dest_dir)
    else:
        raise ValueError(f"不支持的压缩包格式: {suffix}")

    print(f"解压完成: {archive_path.name}")
    return dest_dir


def find_archives_in_dir(dir_path):
    """递归查找目录下所有压缩包文件。"""
    archives = []
    for ext in ARCHIVE_EXTENSIONS:
        archives.extend(Path(dir_path).rglob(f"*{ext}"))
    return archives


def process_archive(archive_path, remove_headers, log_file, flatten=False, overwrite=False,
                    strip_marker=True):
    """处理压缩包：解压（含嵌套）→ 水印清理。

    flatten=False（默认，原行为）：解压到「同名子文件夹」(parent/stem)，清理后保留子文件夹。
    flatten=True（平铺）：先解压到临时子文件夹，清理后再把内容整体平铺到「压缩包所在文件夹」，
        与文件夹内其它零散文件同级。用于「一整个文件夹内既有零散文件又有压缩包」的场景，
        且不会重复处理文件夹内原有零散文件。
    """
    # 用 absolute() 保留 Explorer 传入的原始盘符，避免 resolve() 经卷挂载点
    # 把 C:\Users 改写为 D:\Users 导致跨盘符 os.replace 拒绝访问。
    archive_path = Path(archive_path).absolute()
    parent_dir = archive_path.parent
    archive_stem = archive_path.stem  # 不含扩展名的文件名

    # 平铺模式：先解压到临时子文件夹，清理完再整体平铺到 parent，避免重复处理 parent 内已有文件
    extract_root = (parent_dir / f"_xkw_extract_{archive_stem}") if flatten else (parent_dir / archive_stem)

    print(f"开始处理压缩包: {archive_path}" + ("（平铺到文件夹）" if flatten else ""))

    # 步骤1: 解压主压缩包
    try:
        extract_archive(archive_path, extract_root)
    except Exception as exc:
        print(f"解压失败: {archive_path}")
        print(f"原因: {exc}")
        traceback.print_exc()
        return False

    # 步骤2: 递归解压嵌套压缩包（解压后删除原压缩包，防无限循环）
    while True:
        nested = find_archives_in_dir(extract_root)
        if not nested:
            break
        print(f"发现 {len(nested)} 个嵌套压缩包，正在解压...")
        for nested_archive in nested:
            nested_stem = nested_archive.stem
            nested_dest = nested_archive.parent / nested_stem
            try:
                extract_archive(nested_archive, nested_dest)
            except Exception as exc:
                print(f"解压嵌套压缩包失败: {nested_archive}")
                print(f"原因: {exc}")
                continue
            # 解压完成后删除原压缩包，释放空间并防止下次扫描再次匹配
            try:
                nested_archive.unlink()
                print(f"已删除嵌套压缩包: {nested_archive.name}")
            except Exception as exc:
                print(f"删除嵌套压缩包失败: {nested_archive.name} ({exc})")
            # 将解压出的所有文件/文件夹平铺到根目录
            for item in nested_dest.iterdir():
                target_item = extract_root / item.name
                try:
                    shutil.move(str(item), str(target_item))
                    item_type = "文件夹" if target_item.is_dir() else "文件"
                    print(f"已平铺到根目录: {nested_archive.name} -> {item.name} ({item_type})")
                except Exception as exc:
                    print(f"平铺失败: {item.name} ({exc})")
            # 删除已清空的临时目录
            try:
                nested_dest.rmdir()
                print(f"已删除空目录: {nested_dest.name}")
            except Exception:
                pass

    # 步骤3: 对解压后的文件夹执行水印清理
    print(f"\n开始对解压后的文件夹执行水印清理: {extract_root}")
    success = process_directory(extract_root, overwrite=True, remove_headers=remove_headers,
                                log_file=log_file, flatten=flatten, strip_marker=strip_marker)

    # 若开启去字段，且解压根目录名（含临时目录或同名子文件夹）带『精品解析：』字段，
    # 先把根目录名也去掉。否则会出现不一致：原压缩包改名成「x.zip」，
    # 而解压出的文件夹却仍叫「精品解析：x」，留下一个残留的带字段文件夹。
    if strip_marker and MARKER_FIELD in extract_root.name:
        extract_root = _strip_marker(extract_root)

    # 步骤3.5: 递归去除解压目录树内所有文件/文件夹名里的『精品解析：』字段
    # （单文件处理只改了被处理的文件，未触及内部文件夹与未处理的文件，这里兜底）
    if strip_marker:
        _strip_marker_in_tree(extract_root)

    # 步骤4: 平铺模式 —— 把清理后的内容从临时目录移动到压缩包所在文件夹
    if flatten:
        for item in list(extract_root.iterdir()):
            target = parent_dir / item.name
            try:
                if target.exists():
                    # 同名文件已存在（通常为文件夹内原有零散文件）：改名并入，避免覆盖已处理内容
                    renamed = parent_dir / f"{archive_stem}__{item.name}"
                    shutil.move(str(item), str(renamed))
                    item_type = "文件夹" if renamed.is_dir() else "文件"
                    print(f"已平铺(改名防冲突): {item.name} -> {renamed.name} ({item_type})")
                else:
                    shutil.move(str(item), str(target))
                    item_type = "文件夹" if target.is_dir() else "文件"
                    print(f"已平铺到文件夹: {item.name} ({item_type})")
            except Exception as exc:
                print(f"平铺失败: {item.name} ({exc})")
        # 删除已清空的临时解压目录
        try:
            extract_root.rmdir()
            print(f"已删除临时解压目录: {extract_root.name}")
        except Exception:
            pass

    print(f"\n压缩包处理完成: {archive_path}")

    # 覆盖模式：删除原始压缩包，避免既留 zip 又留解压内容。
    if success and overwrite:
        try:
            archive_path.unlink()
            print(f"已删除原始压缩包: {archive_path.name}")
        except Exception as exc:
            print(f"删除原始压缩包失败: {archive_path.name} ({exc})")
    # 非覆盖模式 + 开启去字段 + 文件名含『精品解析：』字段：重命名去掉字段（不删文件）
    elif success and strip_marker and (MARKER_FIELD in archive_path.name):
        _strip_marker(archive_path)

    return success


def main():
    if len(sys.argv) < 2:
        return 1

    # 注意：不要用 resolve()，它会通过卷挂载点把 C:\Users 改写为 D:\Users，
    # 导致临时文件与目标文件落到不同盘符路径，os.replace 时触发拒绝访问。
    # 这里用 absolute() 保留 Explorer 传入的原始盘符。
    target_path = Path(sys.argv[1]).absolute()
    overwrite = "--overwrite" in sys.argv
    strip_marker = "--no-strip-marker" not in sys.argv
    remove_headers = True
    is_dir = target_path.is_dir()
    is_archive = target_path.suffix.lower() in ARCHIVE_EXTENSIONS

    # 文件夹处理时，把日志写到「文件夹自身内部」，方便用户直接看到处理结果；
    # 单文件 / 压缩包则保持原行为，写到目标同级目录（压缩包不能往 zip 里写）。
    if is_dir:
        log_path = target_path / LOG_FILENAME
    else:
        log_path = target_path.parent / LOG_FILENAME

    with open(log_path, "a", encoding="utf-8", errors="ignore") as log_file:
        append_log_header(log_file, target_path, overwrite, remove_headers, is_dir=is_dir)

        with contextlib.redirect_stdout(log_file), contextlib.redirect_stderr(log_file):
            if is_archive:
                result = process_archive(target_path, remove_headers, log_file,
                                         overwrite=overwrite, strip_marker=strip_marker)
            elif is_dir:
                result = process_directory(target_path, overwrite, remove_headers, log_file,
                                           flatten=True, strip_marker=strip_marker)
            else:
                result = process_file(target_path, overwrite, remove_headers, log_file,
                                      strip_marker=strip_marker)
            return 0 if result else 1


if __name__ == "__main__":
    raise SystemExit(main())
