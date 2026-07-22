#!/usr/bin/env python3
"""Fill empty article metadata from the article heading and source text."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


VOCABULARY = (
    "防火対象物",
    "防火管理者",
    "統括防火管理者",
    "消防計画",
    "自衛消防組織",
    "防炎",
    "火気設備",
    "火気器具",
    "避難",
    "消防用設備等",
    "消火",
    "警報",
    "避難器具",
    "誘導",
    "検査",
    "点検",
    "届出",
    "資格",
    "技術基準",
    "収容人員",
    "床面積",
    "用途",
    "構造",
    "設置",
    "維持",
    "管理",
    "条例",
    "性能",
    "消火栓",
    "スプリンクラー",
)


def parse_quoted(value: str) -> str:
    value = value.strip()
    if value == "null":
        return ""
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return value


def yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def article_fields(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^(article_num|article_title|article_caption|text_path|description|keywords):\s*(.*)$", line)
        if match:
            fields[match.group(1)] = match.group(2)
    return fields


def first_sentence(text_path: Path) -> str:
    lines = text_path.read_text(encoding="utf-8").splitlines()
    body = " ".join(lines[2:]).strip() if len(lines) >= 3 else " ".join(lines).strip()
    if not body:
        return ""
    depth = 0
    sentence_end = len(body)
    opening = set("（「【〔［〈《")
    closing = set("）」】〕］〉》")
    for index, character in enumerate(body):
        if character in opening:
            depth += 1
        elif character in closing and depth:
            depth -= 1
        elif character == "。" and depth == 0:
            sentence_end = index + 1
            break
    sentence = body[:sentence_end].strip()
    if len(sentence) > 180:
        sentence = sentence[:180].rstrip() + "…"
    return sentence + ("。" if not sentence.endswith(("。", "…")) else "")


def build_description(law_title: str, fields: dict[str, str], sentence: str) -> str:
    article_num = parse_quoted(fields.get("article_num", ""))
    article_title = parse_quoted(fields.get("article_title", ""))
    caption = parse_quoted(fields.get("article_caption", ""))
    caption = caption.strip("（）() ")
    article_label = article_title or f"第{article_num}条"
    if caption:
        lead = f"{law_title}の{article_label}は「{caption}」を定める。"
    else:
        lead = f"{law_title}の{article_label}の規定。"
    return f"{lead} 本文冒頭: {sentence}" if sentence else lead


def build_keywords(law_title: str, fields: dict[str, str], source_text: str) -> list[str]:
    caption = parse_quoted(fields.get("article_caption", "")).strip("（）() ")
    title = parse_quoted(fields.get("article_title", ""))
    combined = f"{caption} {title} {source_text}"
    keywords = [law_title]
    if caption:
        keywords.append(caption)
    keywords.extend(term for term in VOCABULARY if term in combined)
    result: list[str] = []
    for keyword in keywords:
        if keyword and keyword not in result:
            result.append(keyword)
    return result


def enrich_file(path: Path, law_title: str, force: bool) -> bool:
    fields = article_fields(path)
    text_path = (path.parent / parse_quoted(fields.get("text_path", ""))).resolve()
    if not text_path.exists():
        raise FileNotFoundError(f"{path}: missing {text_path}")
    source_text = text_path.read_text(encoding="utf-8")
    description = parse_quoted(fields.get("description", ""))
    keywords = fields.get("keywords", "")
    has_keywords = bool(keywords and keywords.strip() != "[]")
    if not force and description and has_keywords:
        return False

    new_description = build_description(law_title, fields, first_sentence(text_path))
    new_keywords = build_keywords(law_title, fields, source_text)
    lines = path.read_text(encoding="utf-8").splitlines()
    output: list[str] = []
    wrote_keywords = False
    for line in lines:
        if line.startswith("description:"):
            output.append(f"description: {yaml_quote(new_description)}")
        elif line.startswith("keywords:"):
            output.append("keywords: [" + ", ".join(yaml_quote(item) for item in new_keywords) + "]")
            wrote_keywords = True
        else:
            output.append(line)
    if not wrote_keywords:
        description_index = next((index for index, line in enumerate(output) if line.startswith("description:")), len(output) - 1)
        output.insert(description_index + 1, "keywords: [" + ", ".join(yaml_quote(item) for item in new_keywords) + "]")
    path.write_text("\n".join(output) + "\n", encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--law-title", default="消防法施行令")
    parser.add_argument("--force", action="store_true", help="replace non-empty metadata too")
    parser.add_argument("--dry-run", action="store_true", help="report changes without writing files")
    args = parser.parse_args()

    article_dir = args.root.resolve() / "data" / args.slug / "articles"
    if not article_dir.exists():
        parser.error(f"article directory does not exist: {article_dir}")
    changed = 0
    for path in sorted(article_dir.glob("*.yaml")):
        if args.dry_run:
            fields = article_fields(path)
            if args.force or not parse_quoted(fields.get("description", "")) or fields.get("keywords", "").strip() in {"", "[]"}:
                changed += 1
        elif enrich_file(path, args.law_title, args.force):
            changed += 1
    mode = "would update" if args.dry_run else "updated"
    print(f"{mode} {changed} article metadata files for {args.slug}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
