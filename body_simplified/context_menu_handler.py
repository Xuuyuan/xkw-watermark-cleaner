import contextlib
import os
import shutil
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path

from clean_watermark import clean_one_file, clean_one_file_overwrite, collect_files


LOG_FILENAME = "xkw-watermark-cleaner.log"
ARCHIVE_EXTENSIONS = {".zip", ".rar", ".7z"}


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


def process_file(target_path, overwrite, remove_headers, log_file):
    """处理单个文件。"""
    try:
        print(f"开始处理: {target_path}")
        if overwrite:
            output_path = clean_one_file_overwrite(target_path, remove_all_header=remove_headers)
        else:
            output_path = clean_one_file(target_path, remove_all_header=remove_headers)
        print(f"处理完成: {output_path}")
        return True
    except Exception as exc:
        print(f"处理失败: {target_path}")
        print(f"原因: {exc}")
        traceback.print_exc()
        return False


def process_directory(target_path, overwrite, remove_headers, log_file):
    """扫描文件夹内所有支持的文件并逐一处理。"""
    files = collect_files([target_path], recursive=True)
    if not files:
        print(f"文件夹内没有找到可处理的 DOC / DOCX / PDF 文件: {target_path}")
        return True

    print(f"共发现 {len(files)} 个待处理文件。")
    success_count = 0
    for file_path in files:
        if process_file(file_path, overwrite, remove_headers, log_file):
            success_count += 1

    print(f"\n文件夹处理完成。成功 {success_count} 个，失败 {len(files) - success_count} 个。")
    return success_count == len(files)


def find_extractor(archive_suffix):
    """根据压缩包类型查找对应的解压程序路径。
    查找顺序：PATH → 自定义环境变量 → 已知安装路径 → 回退。
    """
    if archive_suffix == ".rar":
        exe_names = ["WinRAR.exe", "UnRAR.exe"]
        env_var_names = ["WinRAR", "WINRAR", "WinRar"]
        known_paths = [
            Path(r"C:\Program Files\WinRAR\WinRAR.exe"),
            Path(r"C:\Program Files (x86)\WinRAR\WinRAR.exe"),
            Path(r"D:\My Program\WinRAR\WinRAR.exe"),
            Path(r"D:\Program\WinRAR\WinRAR.exe"),
            Path(r"D:\WinRAR\WinRAR.exe"),
        ]
        fallback = "WinRAR.exe"
        tool_name = "WinRAR"
    else:
        # .zip / .7z 使用 Bandizip
        exe_names = ["Bandizip.exe", "bz.exe"]
        env_var_names = ["Bandzip", "Bandizip", "BANDIZIP"]
        known_paths = [
            Path(r"C:\Program Files\Bandizip\Bandizip.exe"),
            Path(r"C:\Program Files\Bandizip\bz.exe"),
            Path(r"D:\My Program\Bandzip\Bandizip.exe"),
            Path(r"D:\Program\Bandzip\Bandizip.exe"),
            Path(r"D:\Bandzip\Bandizip.exe"),
        ]
        fallback = "Bandizip.exe"
        tool_name = "Bandizip"

    # 1) 通过 PATH 搜索
    for name in exe_names:
        resolved = shutil.which(name)
        if resolved:
            return resolved, tool_name

    # 2) 通过自定义环境变量搜索（如 WinRAR=..., Bandzip=...）
    for var_name in env_var_names:
        var_val = os.environ.get(var_name, "")
        if var_val:
            for name in exe_names:
                candidate = Path(var_val) / name
                if candidate.exists():
                    return str(candidate), tool_name

    # 3) 检查已知安装路径
    for path in known_paths:
        if path.exists():
            return str(path), tool_name

    # 4) 回退（大概率会报 FileNotFoundError）
    return fallback, tool_name


def extract_archive(archive_path, dest_dir):
    """解压单个压缩包到目标目录（静默、无需确认）。"""
    archive_path = Path(archive_path)
    suffix = archive_path.suffix.lower()
    exe_path, tool = find_extractor(suffix)

    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    if tool == "WinRAR":
        # x=保留目录结构  -ibck=后台运行(无界面)  -y=全部确认
        cmd = [exe_path, "x", "-ibck", "-y", str(archive_path), str(dest_dir) + "\\"]
    else:
        # Bandizip: x=解压  -o=输出目录  -y=全部确认
        cmd = [exe_path, "x", "-o:" + str(dest_dir), "-y", str(archive_path)]

    print(f"正在解压: {archive_path.name} -> {dest_dir}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0 and result.stderr:
        print(f"解压警告 (exit={result.returncode}): {result.stderr.strip()}")
    else:
        print(f"解压完成: {archive_path.name}")
    return dest_dir


def find_archives_in_dir(dir_path):
    """递归查找目录下所有压缩包文件。"""
    archives = []
    for ext in ARCHIVE_EXTENSIONS:
        archives.extend(Path(dir_path).rglob(f"*{ext}"))
    return archives


def process_archive(archive_path, remove_headers, log_file):
    """处理压缩包：解压（含嵌套）→ 水印清理。"""
    archive_path = Path(archive_path).resolve()
    parent_dir = archive_path.parent
    archive_stem = archive_path.stem  # 不含扩展名的文件名
    extract_root = parent_dir / archive_stem

    print(f"开始处理压缩包: {archive_path}")

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
    success = process_directory(extract_root, overwrite=True, remove_headers=remove_headers, log_file=log_file)

    print(f"\n压缩包处理完成: {archive_path}")
    return success


def main():
    if len(sys.argv) < 2:
        return 1

    target_path = Path(sys.argv[1]).resolve()
    overwrite = "--overwrite" in sys.argv
    remove_headers = True
    is_dir = target_path.is_dir()
    is_archive = target_path.suffix.lower() in ARCHIVE_EXTENSIONS

    log_path = target_path.parent / LOG_FILENAME

    with open(log_path, "a", encoding="utf-8", errors="ignore") as log_file:
        append_log_header(log_file, target_path, overwrite, remove_headers, is_dir=is_dir)

        with contextlib.redirect_stdout(log_file), contextlib.redirect_stderr(log_file):
            if is_archive:
                result = process_archive(target_path, remove_headers, log_file)
            elif is_dir:
                result = process_directory(target_path, overwrite, remove_headers, log_file)
            else:
                result = process_file(target_path, overwrite, remove_headers, log_file)
            return 0 if result else 1


if __name__ == "__main__":
    raise SystemExit(main())
