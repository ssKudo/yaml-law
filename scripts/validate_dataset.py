#!/usr/bin/env python3
"""Validate the local yaml-law dataset without network access or third-party packages."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


DATA_ROOT = Path("data")
DATASETS_FILE = DATA_ROOT / "datasets.yaml"


def metadata(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if not match:
            continue
        value = match.group(2).strip()
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        result[match.group(1)] = value
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()

    root = args.root.resolve()
    data_root = root / DATA_ROOT
    datasets_file = root / DATASETS_FILE
    errors: list[str] = []
    warnings: list[str] = []
    incomplete_by_dataset: dict[str, int] = {}

    if not datasets_file.exists():
        print(f"ERROR: missing {datasets_file}")
        return 1

    entries = dataset_entries_from(datasets_file)
    registered: set[str] = set()
    for entry in entries:
        slug = entry.get("dataset", "")
        registered.add(slug)
        dataset_dir = root / entry.get("path", "")
        article_dir = dataset_dir / "articles"
        text_dir = dataset_dir / "texts"
        raw_dir = dataset_dir / "raw"
        if not slug or not dataset_dir.exists():
            errors.append(f"{slug or '<missing dataset>'}: registered path does not exist")
            continue
        articles = sorted(article_dir.glob("*.yaml"))
        texts = sorted(text_dir.glob("*.txt"))
        if len(articles) != len(texts):
            errors.append(f"{slug}: articles={len(articles)} texts={len(texts)}")
        expected_count = entry.get("article_count")
        if expected_count and expected_count.isdigit() and int(expected_count) != len(articles):
            errors.append(f"{slug}: registered article_count={expected_count} actual={len(articles)}")
        if not list(raw_dir.glob("*.xml")):
            errors.append(f"{slug}: no raw XML snapshot")
        for article_path in articles:
            info = metadata(article_path)
            text_path_value = info.get("text_path", "")
            text_path = (article_path.parent / text_path_value).resolve()
            if not text_path.exists():
                errors.append(f"{article_path}: missing text_path {text_path_value}")
            if info.get("description") == "" or info.get("keywords") == "[]":
                incomplete_by_dataset[slug] = incomplete_by_dataset.get(slug, 0) + 1

    actual_dirs = {path.name for path in data_root.iterdir() if path.is_dir() and path.name != "links"}
    for slug in sorted(actual_dirs - registered):
        warnings.append(f"data/{slug}: directory is not registered in datasets.yaml")

    for slug, count in sorted(incomplete_by_dataset.items()):
        warnings.append(f"{slug}: {count} article metadata files need enrichment")
    validate_link_files(root, errors)
    print(f"datasets={len(entries)} errors={len(errors)} warnings={len(warnings)}")
    for message in errors:
        print(f"ERROR: {message}")
    for message in warnings:
        print(f"WARNING: {message}")
    return 1 if errors else 0


def validate_link_files(root: Path, errors: list[str]) -> None:
    links_root = root / DATA_ROOT / "links"
    checks = {
        "article_links.yaml": "link_count",
        "scope_links.yaml": "scope_link_count",
    }
    for filename, count_key in checks.items():
        path = links_root / filename
        if not path.exists():
            errors.append(f"links: missing {path}")
            continue
        text = path.read_text(encoding="utf-8")
        count_match = re.search(rf"^{re.escape(count_key)}:\s*\"?(\d+)\"?\s*$", text, re.M)
        if not count_match:
            errors.append(f"{path}: missing {count_key}")
            continue
        actual = len(re.findall(r"^  - from:", text, re.M))
        expected = int(count_match.group(1))
        if actual != expected:
            errors.append(f"{path}: {count_key}={expected} but entries={actual}")
        for source_path in re.findall(r'^\s+source_path:\s*"([^"]+)"\s*$', text, re.M):
            if not (root / source_path).exists():
                errors.append(f"{path}: missing source_path {source_path}")

    summary_path = links_root / "article_links_summary.yaml"
    if summary_path.exists():
        summary = summary_path.read_text(encoding="utf-8")
        for key, expected_file in (("link_count", "article_links.yaml"), ("scope_link_count", "scope_links.yaml")):
            summary_match = re.search(rf"^{re.escape(key)}:\s*\"?(\d+)\"?\s*$", summary, re.M)
            file_text = (links_root / expected_file).read_text(encoding="utf-8") if (links_root / expected_file).exists() else ""
            file_match = re.search(rf"^(?:link_count|scope_link_count):\s*\"?(\d+)\"?\s*$", file_text, re.M)
            if summary_match and file_match and summary_match.group(1) != file_match.group(1):
                errors.append(f"{summary_path}: {key} disagrees with {expected_file}")


def dataset_entries_from(path: Path) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("  - "):
            if current:
                entries.append(current)
            current = {}
            line = "    " + line[4:]
        if current is not None:
            match = re.match(r"^\s{4}([A-Za-z_]+):\s*\"(.*)\"\s*$", line)
            if match:
                current[match.group(1)] = match.group(2)
    if current:
        entries.append(current)
    return entries


if __name__ == "__main__":
    sys.exit(main())
