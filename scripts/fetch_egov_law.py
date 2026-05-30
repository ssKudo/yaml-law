#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.request import urlopen
from xml.etree import ElementTree as ET


DEFAULT_LAW_ID = "325AC0000000201"
DEFAULT_SLUG = "building_standard_act"
SOURCE_URL_BASE = "https://laws.e-gov.go.jp/api/1/lawdata"


@dataclass(frozen=True)
class Context:
    part: str = "本則"
    chapter: str | None = None
    section: str | None = None
    subsection: str | None = None
    division: str | None = None


@dataclass(frozen=True)
class ArticleRecord:
    law_id: str
    law_title: str
    law_num: str
    source_url: str
    article_num: str
    article_title: str
    article_caption: str | None
    context: Context
    text: str


def fetch_xml(law_id: str) -> bytes:
    with urlopen(f"{SOURCE_URL_BASE}/{law_id}", timeout=60) as response:
        return response.read()


def compact_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def element_text(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return compact_text("".join(element.itertext()))


def yaml_quote(value: object) -> str:
    if value is None:
        return "null"
    text = str(value)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def yaml_block(value: str, indent: int = 2) -> str:
    prefix = " " * indent
    if not value:
        return f"{prefix}\n"
    lines = value.splitlines()
    return "".join(f"{prefix}{line}\n" if line else f"{prefix}\n" for line in lines)


def write_yaml(path: Path, data: dict[str, object]) -> None:
    lines: list[str] = []
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{key}:")
            for child_key, child_value in value.items():
                lines.append(f"  {child_key}: {yaml_quote(child_value)}")
        elif isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                if isinstance(item, dict):
                    first = True
                    for child_key, child_value in item.items():
                        bullet = "-" if first else " "
                        lines.append(f"  {bullet} {child_key}: {yaml_quote(child_value)}")
                        first = False
                else:
                    lines.append(f"  - {yaml_quote(item)}")
        elif isinstance(value, str) and ("\n" in value or (key == "text" and value)):
            lines.append(f"{key}: |")
            lines.append(yaml_block(value).rstrip("\n"))
        else:
            lines.append(f"{key}: {yaml_quote(value)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_existing_dataset_entries(path: Path, dataset_slug: str) -> list[dict[str, str]]:
    if not path.exists():
        return []
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if line.startswith("  - "):
            if current and current.get("dataset") != dataset_slug:
                entries.append(current)
            current = {}
            key, value = line[4:].split(":", 1)
            current[key] = parse_simple_yaml_value(value)
        elif current is not None and line.startswith("    ") and ":" in line:
            key, value = line.strip().split(":", 1)
            current[key] = parse_simple_yaml_value(value)
    if current and current.get("dataset") != dataset_slug:
        entries.append(current)
    return entries


def parse_simple_yaml_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return value


def paragraph_lines(paragraph: ET.Element) -> list[str]:
    lines: list[str] = []
    paragraph_num = element_text(paragraph.find("ParagraphNum"))
    sentences = [element_text(sentence) for sentence in paragraph.findall("./ParagraphSentence//Sentence")]
    sentence_text = "".join(sentences)
    if sentence_text:
        lines.append(f"{paragraph_num}{sentence_text}" if paragraph_num else sentence_text)

    for item in paragraph.findall("Item"):
        lines.extend(item_lines(item, 0))
    return lines


def item_lines(item: ET.Element, depth: int) -> list[str]:
    lines: list[str] = []
    title = element_text(item.find("ItemTitle"))
    sentence_element = item.find("ItemSentence")
    sentence_text = sentence_content(sentence_element)
    prefix = "  " * depth
    if title or sentence_text:
        lines.append(f"{prefix}{title}　{sentence_text}".rstrip())

    child_tags = {
        "Subitem1",
        "Subitem2",
        "Subitem3",
        "Subitem4",
        "Subitem5",
        "Subitem6",
        "Subitem7",
        "Subitem8",
        "Subitem9",
        "Subitem10",
    }
    for child in item:
        if child.tag in child_tags:
            lines.extend(subitem_lines(child, depth + 1))
    return lines


def subitem_lines(item: ET.Element, depth: int) -> list[str]:
    lines: list[str] = []
    title = ""
    sentence_text = ""
    for child in item:
        if child.tag.endswith("Title"):
            title = element_text(child)
        elif child.tag.endswith("Sentence"):
            sentence_text = sentence_content(child)
    prefix = "  " * depth
    if title or sentence_text:
        lines.append(f"{prefix}{title}　{sentence_text}".rstrip())

    for child in item:
        if child.tag.startswith("Subitem") and child.tag != item.tag:
            lines.extend(subitem_lines(child, depth + 1))
    return lines


def sentence_content(sentence_element: ET.Element | None) -> str:
    if sentence_element is None:
        return ""
    columns = sentence_element.findall("./Column")
    if columns:
        return "　".join(element_text(column) for column in columns if element_text(column))
    return "".join(element_text(sentence) for sentence in sentence_element.findall(".//Sentence"))


def article_text(article: ET.Element) -> str:
    lines: list[str] = []
    caption = element_text(article.find("ArticleCaption"))
    title = element_text(article.find("ArticleTitle"))
    if caption:
        lines.append(caption)
    if title:
        lines.append(title)
    for paragraph in article.findall("Paragraph"):
        lines.extend(paragraph_lines(paragraph))
    return "\n".join(line for line in lines if line).strip()


def article_filename(article_num: str) -> str:
    parts = article_num.split("_")
    if parts and parts[0].isdigit():
        parts[0] = parts[0].zfill(3)
    safe = "_".join(parts)
    return f"article_{safe}.yaml"


def walk_articles(element: ET.Element, context: Context) -> Iterable[tuple[ET.Element, Context]]:
    next_context = context
    if element.tag == "Chapter":
        next_context = Context(
            part=context.part,
            chapter=element_text(element.find("ChapterTitle")),
            section=None,
            subsection=None,
            division=None,
        )
    elif element.tag == "Section":
        next_context = Context(
            part=context.part,
            chapter=context.chapter,
            section=element_text(element.find("SectionTitle")),
            subsection=None,
            division=None,
        )
    elif element.tag == "Subsection":
        next_context = Context(
            part=context.part,
            chapter=context.chapter,
            section=context.section,
            subsection=element_text(element.find("SubsectionTitle")),
            division=None,
        )
    elif element.tag == "Division":
        next_context = Context(
            part=context.part,
            chapter=context.chapter,
            section=context.section,
            subsection=context.subsection,
            division=element_text(element.find("DivisionTitle")),
        )
    elif element.tag == "Article":
        yield element, context
        return

    for child in element:
        yield from walk_articles(child, next_context)


def parse_articles(xml_bytes: bytes, law_id: str, source_url: str) -> tuple[str, str, list[ArticleRecord]]:
    root = ET.fromstring(xml_bytes)
    code = element_text(root.find("./Result/Code"))
    if code and code != "0":
        message = element_text(root.find("./Result/Message"))
        raise RuntimeError(f"e-Gov API returned code={code}: {message}")

    law = root.find(".//Law")
    if law is None:
        raise RuntimeError("Law element was not found in e-Gov response.")
    law_num = element_text(law.find("LawNum"))
    law_body = law.find("LawBody")
    if law_body is None:
        raise RuntimeError("LawBody element was not found.")
    law_title = element_text(law_body.find("LawTitle"))
    main = law_body.find("MainProvision")
    if main is None:
        raise RuntimeError("MainProvision element was not found.")

    articles: list[ArticleRecord] = []
    for article, context in walk_articles(main, Context()):
        article_num = article.attrib.get("Num", "")
        title = element_text(article.find("ArticleTitle"))
        caption = element_text(article.find("ArticleCaption")) or None
        articles.append(
            ArticleRecord(
                law_id=law_id,
                law_title=law_title,
                law_num=law_num,
                source_url=source_url,
                article_num=article_num,
                article_title=title,
                article_caption=caption,
                context=context,
                text=article_text(article),
            )
        )
    return law_title, law_num, articles


def clean_output_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for generated_file in path.iterdir():
        if generated_file.is_file() and generated_file.suffix in {".yaml", ".txt"}:
            generated_file.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch current e-Gov law XML and split main provisions into article YAML files.")
    parser.add_argument("--law-id", default=DEFAULT_LAW_ID)
    parser.add_argument("--slug", default=DEFAULT_SLUG)
    parser.add_argument("--output-dir", default="data")
    args = parser.parse_args()

    source_url = f"{SOURCE_URL_BASE}/{args.law_id}"
    output_root = Path(args.output_dir) / args.slug
    article_dir = output_root / "articles"
    text_dir = output_root / "texts"
    raw_dir = output_root / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    xml_bytes = fetch_xml(args.law_id)
    raw_xml_path = raw_dir / f"{args.law_id}.xml"
    raw_xml_path.write_bytes(xml_bytes)

    law_title, law_num, articles = parse_articles(xml_bytes, args.law_id, source_url)
    clean_output_dir(article_dir)
    clean_output_dir(text_dir)

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    for article in articles:
        yaml_name = article_filename(article.article_num)
        text_name = yaml_name.replace(".yaml", ".txt")
        (text_dir / text_name).write_text(article.text + "\n", encoding="utf-8")
        write_yaml(
            article_dir / yaml_name,
            {
                "law_id": article.law_id,
                "law_title": article.law_title,
                "law_num": article.law_num,
                "source": "e-Gov法令検索",
                "source_url": article.source_url,
                "part": article.context.part,
                "chapter": article.context.chapter,
                "section": article.context.section,
                "subsection": article.context.subsection,
                "division": article.context.division,
                "article_num": article.article_num,
                "article_title": article.article_title,
                "article_caption": article.article_caption,
                "description": "",
                "text_path": f"../texts/{text_name}",
            },
        )

    write_yaml(
        output_root / "dataset.yaml",
        {
            "dataset": args.slug,
            "law_id": args.law_id,
            "law_title": law_title,
            "law_num": law_num,
            "source": "e-Gov法令検索",
            "source_url": source_url,
            "api_version": "1",
            "fetched_at": generated_at,
            "effective_scope": "e-Gov法令APIで取得した取得日時点の現在施行中の現行法令",
            "included_parts": ["本則"],
            "excluded_parts": ["附則"],
            "unit": "Article",
            "article_count": len(articles),
            "article_metadata_dir": str(article_dir),
            "article_text_dir": str(text_dir),
            "raw_xml": str(raw_xml_path),
        },
    )

    dataset_entry = {
        "dataset": args.slug,
        "law_id": args.law_id,
        "law_title": law_title,
        "law_num": law_num,
        "source_url": source_url,
        "fetched_at": generated_at,
        "effective_scope": "e-Gov法令APIで取得した取得日時点の現在施行中の現行法令",
        "included_parts": "本則",
        "article_count": len(articles),
        "path": str(output_root),
    }
    datasets_path = Path(args.output_dir) / "datasets.yaml"
    dataset_entries = read_existing_dataset_entries(datasets_path, args.slug)
    dataset_entries.append(dataset_entry)
    dataset_entries.sort(key=lambda item: item["dataset"])

    write_yaml(
        datasets_path,
        {
            "generated_at": generated_at,
            "datasets": dataset_entries,
        },
    )

    print(f"Wrote {len(articles)} article files to {article_dir}")


if __name__ == "__main__":
    main()
