#!/usr/bin/env python3
"""从指定 Git 提交制作可校验的精简源码发行包，不读取本地依赖或凭据。"""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {"_convert", "_lms_convert", "cypress", ".github", ".gitmodules"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--output", type=Path, default=ROOT / "release-dist")
    args = parser.parse_args()
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", args.version):
        parser.error("版本格式应为 v2026.10.17 或 v1.0.0")
    commit = subprocess.check_output(
        ["git", "rev-parse", "--verify", f"{args.ref}^{{commit}}"], cwd=ROOT, text=True
    ).strip()
    timestamp = int(subprocess.check_output(
        ["git", "show", "-s", "--format=%ct", commit], cwd=ROOT, text=True
    ))
    source = subprocess.check_output(["git", "archive", "--format=tar", commit], cwd=ROOT)
    entries = []
    with tarfile.open(fileobj=io.BytesIO(source)) as archive:
        for member in archive:
            path = member.name
            if path.split("/")[0] in EXCLUDED or path.startswith("docs/qa/"):
                continue
            if not member.isfile():
                continue
            entries.append((path, archive.extractfile(member).read(), member.mode))
    metadata = {"version": args.version, "commit": commit, "type": "source", "prebuilt_assets": False}
    entries.append(("RELEASE.json", (json.dumps(metadata, indent=2) + "\n").encode(), 0o644))
    entries.sort()
    args.output.mkdir(parents=True, exist_ok=True)
    name = f"JWLCode-frappe-{args.version}"
    tar_path = args.output / f"{name}.tar.gz"
    zip_path = args.output / f"{name}.zip"
    with tar_path.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=timestamp) as gz:
            with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as tar:
                for path, data, mode in entries:
                    info = tarfile.TarInfo(f"{name}/{path}")
                    info.size, info.mode, info.mtime = len(data), mode, timestamp
                    tar.addfile(info, io.BytesIO(data))
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, data, mode in entries:
            info = zipfile.ZipInfo(f"{name}/{path}", (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (0o100000 | mode) << 16
            archive.writestr(info, data)
    lines = []
    for path in (tar_path, zip_path):
        lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n")
        print(f"{path}: {path.stat().st_size / 1048576:.2f} MiB")
    (args.output / "SHA256SUMS").write_text("".join(lines))
    print(f"Commit: {commit}; files: {len(entries)}")


if __name__ == "__main__":
    main()
