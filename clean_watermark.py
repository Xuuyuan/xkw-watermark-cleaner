import argparse
import os
import tempfile
from pathlib import Path

from clean_watermark_doc import clean_doc
from clean_watermark_docx import clean_docx
from clean_watermark_pdf import clean_pdf


SUPPORTED_EXTENSIONS = {".doc", ".docx", ".pdf"}
SKIP_MARKERS = ("(cleaned)",)


def should_skip(path):
    return any(marker in path.stem for marker in SKIP_MARKERS)


def collect_files(input_paths, recursive=False):
    results = []

    for raw_path in input_paths:
        path = Path(raw_path)
        if not path.exists():
            print(f"跳过不存在的路径: {path}")
            continue

        if path.is_file():
            if path.suffix.lower() in SUPPORTED_EXTENSIONS and not should_skip(path):
                results.append(path)
            continue

        iterator = path.rglob("*") if recursive else path.glob("*")
        for candidate in iterator:
            if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_EXTENSIONS and not should_skip(candidate):
                results.append(candidate)

    unique_results = []
    seen = set()
    for item in results:
        key = str(item.resolve()).lower()
        if key not in seen:
            seen.add(key)
            unique_results.append(item)
    return sorted(unique_results)


def build_output_path(input_path, output_dir=None):
    input_path = Path(input_path)
    if input_path.suffix.lower() == ".pdf":
        output_name = f"{input_path.stem}(cleaned).pdf"
    else:
        output_name = f"{input_path.stem}(cleaned).docx"

    if output_dir:
        return str((Path(output_dir) / output_name).resolve())
    return str(input_path.with_name(output_name).resolve())


def clean_one_file(path, output_dir=None):
    suffix = path.suffix.lower()
    output_path = build_output_path(path, output_dir)

    if suffix == ".doc":
        return clean_doc(str(path), output_path)
    if suffix == ".docx":
        return clean_docx(str(path), output_path)
    if suffix == ".pdf":
        return clean_pdf(str(path), output_path)

    raise ValueError(f"不支持的文件类型: {path}")


def clean_one_file_overwrite(path):
    path = Path(path).resolve()
    suffix = path.suffix.lower()
    output_dir = path.parent

    if suffix == ".doc":
        output_path = build_output_path(path)
        print("DOC 文件不支持覆盖写回，将生成对应的清理后 DOCX 文件。")
        return clean_doc(str(path), output_path)

    if suffix == ".docx":
        temp_fd, temp_output = tempfile.mkstemp(suffix=".docx", dir=output_dir)
        os.close(temp_fd)
        try:
            clean_docx(str(path), temp_output)
            os.replace(temp_output, path)
            print(f"已覆盖源文件: {path}")
            return str(path)
        finally:
            if os.path.exists(temp_output):
                os.remove(temp_output)

    if suffix == ".pdf":
        temp_fd, temp_output = tempfile.mkstemp(suffix=".pdf", dir=output_dir)
        os.close(temp_fd)
        try:
            clean_pdf(str(path), temp_output)
            os.replace(temp_output, path)
            print(f"已覆盖源文件: {path}")
            return str(path)
        finally:
            if os.path.exists(temp_output):
                os.remove(temp_output)

    raise ValueError(f"不支持的文件类型: {path}")


def main():
    parser = argparse.ArgumentParser(description="统一清理 DOC / DOCX / PDF 中的学科网相关水印。")
    parser.add_argument("paths", nargs="*", default=["."], help="待处理的文件或目录，默认当前目录。")
    parser.add_argument("-r", "--recursive", action="store_true", help="递归扫描目录。")
    parser.add_argument("-o", "--output-dir", help="统一输出目录；不填则输出到原文件同目录。")
    args = parser.parse_args()

    files = collect_files(args.paths, recursive=args.recursive)
    if not files:
        print("没有找到可处理的 DOC / DOCX / PDF 文件。")
        return

    if args.output_dir:
        Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    print(f"共发现 {len(files)} 个待处理文件。")
    success_count = 0

    for file_path in files:
        print(f"\n开始处理: {file_path}")
        try:
            output_path = clean_one_file(file_path, args.output_dir)
            print(f"处理完成: {output_path}")
            success_count += 1
        except Exception as exc:
            print(f"处理失败: {file_path}")
            print(f"原因: {exc}")

    print(f"\n完成。成功 {success_count} 个，失败 {len(files) - success_count} 个。")


if __name__ == "__main__":
    main()
