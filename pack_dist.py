# -*- coding: utf-8 -*-
"""Generate 7z ultra-compressed distribution archive."""
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
BODY = PROJECT / "body"
OUTPUT_7Z = PROJECT / "body_standalone.7z"

if not BODY.exists():
    print(f"ERROR: {BODY} not found, run build.py first")
    exit(1)

# Calculate source size
original_size = sum(f.stat().st_size for f in BODY.rglob("*") if f.is_file())
print(f"Source: {BODY}")
print(f"Source size: {original_size/1048576:.1f} MB")

# Pack with py7zr (highest compression)
try:
    import py7zr

    print("Packing with py7zr (LZMA2 ultra)...")
    with py7zr.SevenZipFile(str(OUTPUT_7Z), 'w',
                            filters=[{"id": py7zr.FILTER_LZMA2, "preset": 7, "dict_size": 64*1024*1024}]) as zf:
        for p in BODY.rglob("*"):
            if p.is_file():
                arcname = str(p.relative_to(BODY.parent))
                zf.write(str(p), arcname)

    zip_size = OUTPUT_7Z.stat().st_size
    ratio = zip_size / original_size * 100
    print(f"7z size: {zip_size/1048576:.1f} MB")
    print(f"Compression ratio: {ratio:.1f}%")
    print(f"\nDone! Output: {OUTPUT_7Z}")

except ImportError:
    # Fallback: use zipfile with highest compression
    print("py7zr not found, using zipfile...")
    import zipfile
    OUTPUT_ZIP = PROJECT / "body_standalone.zip"
    with zipfile.ZipFile(OUTPUT_ZIP, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in BODY.rglob("*"):
            if p.is_file():
                arcname = str(p.relative_to(BODY.parent))
                zf.write(str(p), arcname)
    zip_size = OUTPUT_ZIP.stat().st_size
    ratio = zip_size / original_size * 100
    print(f"zip size: {zip_size/1048576:.1f} MB")
    print(f"Compression ratio: {ratio:.1f}%")
    print(f"\nDone! Output: {OUTPUT_ZIP}")
