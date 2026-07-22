from __future__ import annotations

import argparse
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = PROJECT_ROOT / "skills" / "product-user-comment-data-merge-cleaning"

SCRIPT_FILES = (
    "cleanup_intermediate_outputs.py",
    "clean_excel_comments.py",
    "compare_cleaned_workbooks.py",
    "csv_excel_compat.py",
    "merge_excel_workbooks.py",
    "hash_id_project_store.py",
    "hash_id_pseudonymizer.py",
    "output_file_naming.py",
    "output_path_safety.py",
    "standardize_excel_headers.py",
    "strip_bilibili_reply_prefixes.py",
)

CONFIG_FILES = (
    "comment-cleaner.json",
    "hash-id.json",
    "header-standardizer.json",
)


def iter_bundle_files() -> tuple[tuple[Path, Path], ...]:
    script_pairs = tuple(
        (PROJECT_ROOT / "tools" / name, SKILL_ROOT / "scripts" / name)
        for name in SCRIPT_FILES
    )
    config_pairs = tuple(
        (PROJECT_ROOT / "config" / name, SKILL_ROOT / "config" / name)
        for name in CONFIG_FILES
    )
    return script_pairs + config_pairs


def stale_files() -> list[Path]:
    stale: list[Path] = []
    for source, destination in iter_bundle_files():
        if not destination.is_file() or source.read_bytes() != destination.read_bytes():
            stale.append(destination)
    return stale


def sync_bundle() -> None:
    for source, destination in iter_bundle_files():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="同步或检查可独立分发的 Agent Skill 脚本与配置")
    parser.add_argument("--check", action="store_true", help="只检查，不写入文件")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.check:
        stale = stale_files()
        if stale:
            for path in stale:
                print(f"STALE: {path.relative_to(PROJECT_ROOT)}")
            return 1
        print("Skill bundle scripts and configs are synchronized.")
        return 0

    sync_bundle()
    print(f"Synchronized {len(iter_bundle_files())} files into {SKILL_ROOT.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
