import contextlib
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

from clean_watermark import clean_one_file


LOG_FILENAME = "xkw-watermark-cleaner.log"


def append_log_header(log_file, target_file):
    log_file.write("\n")
    log_file.write("=" * 72 + "\n")
    log_file.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    log_file.write(f"文件: {target_file}\n")
    log_file.write("=" * 72 + "\n")
    log_file.flush()


def main():
    if len(sys.argv) < 2:
        return 1

    target_path = Path(sys.argv[1]).resolve()
    log_path = target_path.parent / LOG_FILENAME

    with open(log_path, "a", encoding="utf-8", errors="ignore") as log_file:
        append_log_header(log_file, target_path)

        with contextlib.redirect_stdout(log_file), contextlib.redirect_stderr(log_file):
            try:
                print(f"开始处理: {target_path}")
                output_path = clean_one_file(target_path)
                print(f"处理完成: {output_path}")
                return 0
            except Exception as exc:
                print(f"处理失败: {target_path}")
                print(f"原因: {exc}")
                traceback.print_exc()
                return 1


if __name__ == "__main__":
    raise SystemExit(main())
