#!/usr/bin/env python3
from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


DATA_ROOT = Path("data")
LINKS_DIR = DATA_ROOT / "links"

DATASETS = {
    "building_standard_act": {
        "law_id": "325AC0000000201",
        "law_title": "建築基準法",
        "short_law_aliases": {},
    },
    "building_standard_act_enforcement_order": {
        "law_id": "325CO0000000338",
        "law_title": "建築基準法施行令",
        "short_law_aliases": {
            "法": "325AC0000000201",
        },
    },
    "building_standard_act_enforcement_regulation": {
        "law_id": "325M50004000040",
        "law_title": "建築基準法施行規則",
        "short_law_aliases": {
            "法": "325AC0000000201",
            "令": "325CO0000000338",
        },
    },
    "city_planning_act": {
        "law_id": "343AC0000000100",
        "law_title": "都市計画法",
        "short_law_aliases": {},
    },
    "city_planning_act_enforcement_order": {
        "law_id": "344CO0000000158",
        "law_title": "都市計画法施行令",
        "short_law_aliases": {
            "法": "343AC0000000100",
        },
    },
    "fire_service_act": {
        "law_id": "323AC1000000186",
        "law_title": "消防法",
        "short_law_aliases": {},
    },
    "fire_service_act_enforcement_order": {
        "law_id": "336CO0000000037",
        "law_title": "消防法施行令",
        "short_law_aliases": {
            "法": "323AC1000000186",
        },
    },
    "barrier_free_act": {
        "law_id": "418AC0000000091",
        "law_title": "高齢者、障害者等の移動等の円滑化の促進に関する法律",
        "short_law_aliases": {},
    },
    "civil_code": {
        "law_id": "129AC0000000089",
        "law_title": "民法",
        "short_law_aliases": {},
    },
    "housing_quality_assurance_act": {
        "law_id": "411AC0000000081",
        "law_title": "住宅の品質確保の促進等に関する法律",
        "short_law_aliases": {},
    },
    "real_estate_brokerage_act": {
        "law_id": "327AC1000000176",
        "law_title": "宅地建物取引業法",
        "short_law_aliases": {},
    },
}

LAW_ID_TO_SLUG = {value["law_id"]: key for key, value in DATASETS.items()}

KANJI_NUM = "〇零一二三四五六七八九十百千万壱弐参拾"
ARTICLE_REF = rf"第([{KANJI_NUM}]+)(?:条の([{KANJI_NUM}]+)|条)"
SHORT_ALIAS_REF = re.compile(rf"(?<![一-龥ぁ-んァ-ヶ])(?P<alias>法|令){ARTICLE_REF}")
BARE_ARTICLE_REF = re.compile(ARTICLE_REF)
ARTICLE_RANGE_REF = re.compile(rf"{ARTICLE_REF}から{ARTICLE_REF}まで")
RELATIVE_ARTICLE_REF = re.compile(r"(?P<label>前条|次条)")
SCOPE_REF = re.compile(rf"(?P<label>この章|この節|前章|次章|前節|次節|第[{KANJI_NUM}]+章|第[{KANJI_NUM}]+節)")


def yaml_quote(value: object) -> str:
    if value is None:
        return "null"
    text = str(value)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def write_yaml(path: Path, data: dict[str, object]) -> None:
    lines = yaml_lines(data, 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def yaml_lines(value: object, indent: int) -> list[str]:
    prefix = " " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, child in value.items():
            if isinstance(child, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.extend(yaml_lines(child, indent + 2))
            else:
                lines.append(f"{prefix}{key}: {yaml_quote(child)}")
        return lines
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, dict):
                item_lines = yaml_lines(item, indent + 2)
                if item_lines:
                    lines.append(f"{prefix}- {item_lines[0].lstrip()}")
                    lines.extend(item_lines[1:])
                else:
                    lines.append(f"{prefix}-")
            elif isinstance(item, list):
                lines.append(f"{prefix}-")
                lines.extend(yaml_lines(item, indent + 2))
            else:
                lines.append(f"{prefix}- {yaml_quote(item)}")
        return lines
    return [f"{prefix}{yaml_quote(value)}"]


def read_metadata(path: Path) -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith(" ") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if value == "null":
            result[key] = None
        elif len(value) >= 2 and value[0] == '"' and value[-1] == '"':
            result[key] = value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        else:
            result[key] = value
    return result


def kanji_to_int(text: str) -> int:
    normalized = (
        text.replace("零", "〇")
        .replace("壱", "一")
        .replace("弐", "二")
        .replace("参", "三")
        .replace("拾", "十")
    )
    digit_map = {
        "〇": 0,
        "一": 1,
        "二": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
    }
    unit_map = {"十": 10, "百": 100, "千": 1000}
    total = 0
    current = 0
    for char in normalized:
        if char in digit_map:
            current = digit_map[char]
        elif char in unit_map:
            unit = unit_map[char]
            total += (current or 1) * unit
            current = 0
        elif char == "万":
            total = (total + current) * 10000
            current = 0
        else:
            raise ValueError(f"Unsupported Japanese numeral: {text}")
    return total + current


def article_num_from_match(match: re.Match[str], offset: int = 1) -> str:
    base = kanji_to_int(match.group(offset))
    branch = match.group(offset + 1)
    if branch:
        return f"{base}_{kanji_to_int(branch)}"
    return str(base)


def load_articles() -> tuple[dict[tuple[str, str], dict[str, str | None]], dict[str, dict[str, str]]]:
    articles: dict[tuple[str, str], dict[str, str | None]] = {}
    law_titles: dict[str, dict[str, str]] = {}
    for slug, config in DATASETS.items():
        law_id = config["law_id"]
        law_titles[law_id] = {"slug": slug, "law_title": config["law_title"]}
        for metadata_path in sorted((DATA_ROOT / slug / "articles").glob("*.yaml")):
            metadata = read_metadata(metadata_path)
            article_num = str(metadata["article_num"])
            metadata["metadata_path"] = str(metadata_path)
            articles[(law_id, article_num)] = metadata
    return articles, law_titles


def articles_by_law(articles: dict[tuple[str, str], dict[str, str | None]]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    for law_id, article_num in articles:
        result[law_id].append(article_num)
    for law_id in result:
        result[law_id].sort(key=natural_article_key)
    return result


def scope_index(articles: dict[tuple[str, str], dict[str, str | None]]) -> dict[str, dict[str, dict[str, list[str]]]]:
    index: dict[str, dict[str, dict[str, list[str]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for (law_id, article_num), metadata in articles.items():
        for level in ("chapter", "section", "subsection", "division"):
            title = metadata.get(level)
            if title:
                index[law_id][level][str(title)].append(article_num)
    for law_id in index:
        for level in index[law_id]:
            for title in index[law_id][level]:
                index[law_id][level][title].sort(key=natural_article_key)
    return index


def text_without_heading(text_path: Path) -> str:
    lines = text_path.read_text(encoding="utf-8").splitlines()
    if len(lines) >= 2 and lines[1].startswith("第"):
        return "\n".join(lines[2:])
    return "\n".join(lines)


def add_link(
    links: dict[tuple[str, str, str, str, str], dict[str, object]],
    *,
    from_law_id: str,
    from_article_num: str,
    to_law_id: str,
    to_article_num: str,
    label: str,
    kind: str,
    confidence: str,
    source_path: str,
) -> None:
    if from_law_id == to_law_id and from_article_num == to_article_num:
        return
    key = (from_law_id, from_article_num, to_law_id, to_article_num, label)
    links[key] = {
        "from": {"law_id": from_law_id, "article_num": from_article_num},
        "to": {"law_id": to_law_id, "article_num": to_article_num},
        "kind": kind,
        "confidence": confidence,
        "label": label,
        "source_path": source_path,
    }


def add_scope_link(
    scope_links: dict[tuple[str, str, str, str, str], dict[str, object]],
    *,
    from_law_id: str,
    from_article_num: str,
    to_law_id: str,
    scope_level: str,
    scope_title: str,
    target_articles: list[str],
    label: str,
    kind: str,
    confidence: str,
    source_path: str,
) -> None:
    if not target_articles:
        return
    key = (from_law_id, from_article_num, to_law_id, scope_level, scope_title)
    scope_links[key] = {
        "from": {"law_id": from_law_id, "article_num": from_article_num},
        "to": {
            "law_id": to_law_id,
            "scope_level": scope_level,
            "scope_title": scope_title,
            "article_start": target_articles[0],
            "article_end": target_articles[-1],
            "article_count": len(target_articles),
        },
        "kind": kind,
        "confidence": confidence,
        "label": label,
        "source_path": source_path,
    }


def build_links() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    articles, _law_titles = load_articles()
    ordered_articles = articles_by_law(articles)
    scopes = scope_index(articles)
    links: dict[tuple[str, str, str, str, str], dict[str, object]] = {}
    scope_links: dict[tuple[str, str, str, str, str], dict[str, object]] = {}

    for slug, config in DATASETS.items():
        from_law_id = config["law_id"]
        aliases = config["short_law_aliases"]
        law_article_order = ordered_articles[from_law_id]
        for metadata_path in sorted((DATA_ROOT / slug / "articles").glob("*.yaml")):
            metadata = read_metadata(metadata_path)
            from_article_num = str(metadata["article_num"])
            text_path = metadata_path.parent / str(metadata["text_path"])
            text = text_without_heading(text_path.resolve())
            source_path = str(text_path.resolve().relative_to(Path.cwd()))

            alias_spans: list[tuple[int, int]] = []
            for match in SHORT_ALIAS_REF.finditer(text):
                alias = match.group("alias")
                to_law_id = aliases.get(alias)
                if not to_law_id:
                    continue
                to_article_num = article_num_from_match(match, 2)
                if (to_law_id, to_article_num) not in articles:
                    continue
                alias_spans.append(match.span())
                add_link(
                    links,
                    from_law_id=from_law_id,
                    from_article_num=from_article_num,
                    to_law_id=to_law_id,
                    to_article_num=to_article_num,
                    label=match.group(0),
                    kind="short_law_article_reference",
                    confidence="high",
                    source_path=source_path,
                )

            range_spans: list[tuple[int, int]] = []
            for match in ARTICLE_RANGE_REF.finditer(text):
                start_article = article_num_from_match(match, 1)
                end_article = article_num_from_match(match, 3)
                for to_article_num in article_range(law_article_order, start_article, end_article):
                    add_link(
                        links,
                        from_law_id=from_law_id,
                        from_article_num=from_article_num,
                        to_law_id=from_law_id,
                        to_article_num=to_article_num,
                        label=match.group(0),
                        kind="same_law_article_range_reference",
                        confidence="medium",
                        source_path=source_path,
                    )
                range_spans.append(match.span())

            for match in RELATIVE_ARTICLE_REF.finditer(text):
                to_article_num = relative_article(law_article_order, from_article_num, match.group("label"))
                if not to_article_num:
                    continue
                add_link(
                    links,
                    from_law_id=from_law_id,
                    from_article_num=from_article_num,
                    to_law_id=from_law_id,
                    to_article_num=to_article_num,
                    label=match.group(0),
                    kind="same_law_relative_article_reference",
                    confidence="medium",
                    source_path=source_path,
                )

            for match in BARE_ARTICLE_REF.finditer(text):
                if any(start <= match.start() < end for start, end in alias_spans):
                    continue
                if any(start <= match.start() < end for start, end in range_spans):
                    continue
                if match.start() > 0 and text[match.start() - 1] in "法令規則":
                    continue
                to_article_num = article_num_from_match(match)
                if (from_law_id, to_article_num) not in articles:
                    continue
                add_link(
                    links,
                    from_law_id=from_law_id,
                    from_article_num=from_article_num,
                    to_law_id=from_law_id,
                    to_article_num=to_article_num,
                    label=match.group(0),
                    kind="same_law_article_reference",
                    confidence="medium",
                    source_path=source_path,
                )

            for match in SCOPE_REF.finditer(text):
                resolved = resolve_scope_reference(scopes, metadata, from_law_id, match.group("label"))
                if not resolved:
                    continue
                scope_level, scope_title, target_articles = resolved
                add_scope_link(
                    scope_links,
                    from_law_id=from_law_id,
                    from_article_num=from_article_num,
                    to_law_id=from_law_id,
                    scope_level=scope_level,
                    scope_title=scope_title,
                    target_articles=target_articles,
                    label=match.group("label"),
                    kind="same_law_scope_reference",
                    confidence="medium",
                    source_path=source_path,
                )

    sorted_links = sorted(
        links.values(),
        key=lambda link: (
            str(link["from"]["law_id"]),
            natural_article_key(str(link["from"]["article_num"])),
            str(link["to"]["law_id"]),
            natural_article_key(str(link["to"]["article_num"])),
            str(link["label"]),
        ),
    )
    sorted_scope_links = sorted(
        scope_links.values(),
        key=lambda link: (
            str(link["from"]["law_id"]),
            natural_article_key(str(link["from"]["article_num"])),
            str(link["to"]["scope_level"]),
            str(link["to"]["scope_title"]),
        ),
    )
    return sorted_links, sorted_scope_links


def article_range(ordered_articles: list[str], start_article: str, end_article: str) -> list[str]:
    try:
        start = ordered_articles.index(start_article)
        end = ordered_articles.index(end_article)
    except ValueError:
        return []
    if start > end:
        start, end = end, start
    return ordered_articles[start : end + 1]


def relative_article(ordered_articles: list[str], current_article: str, label: str) -> str | None:
    try:
        index = ordered_articles.index(current_article)
    except ValueError:
        return None
    if label == "前条" and index > 0:
        return ordered_articles[index - 1]
    if label == "次条" and index < len(ordered_articles) - 1:
        return ordered_articles[index + 1]
    return None


def resolve_scope_reference(
    scopes: dict[str, dict[str, dict[str, list[str]]]],
    metadata: dict[str, str | None],
    law_id: str,
    label: str,
) -> tuple[str, str, list[str]] | None:
    if label == "この章":
        title = metadata.get("chapter")
        level = "chapter"
    elif label == "この節":
        title = metadata.get("section")
        level = "section"
    elif label in {"前章", "次章"}:
        return relative_scope(scopes, law_id, "chapter", str(metadata.get("chapter") or ""), -1 if label == "前章" else 1)
    elif label in {"前節", "次節"}:
        return relative_scope(scopes, law_id, "section", str(metadata.get("section") or ""), -1 if label == "前節" else 1)
    elif label.endswith("章"):
        title = scope_title_by_prefix(scopes, law_id, "chapter", label)
        level = "chapter"
    elif label.endswith("節"):
        title = scope_title_by_prefix(scopes, law_id, "section", label)
        level = "section"
    else:
        return None
    if not title:
        return None
    target_articles = scopes[law_id][level].get(str(title), [])
    return level, str(title), target_articles


def relative_scope(
    scopes: dict[str, dict[str, dict[str, list[str]]]],
    law_id: str,
    level: str,
    current_title: str,
    delta: int,
) -> tuple[str, str, list[str]] | None:
    titles = list(scopes[law_id][level].keys())
    if current_title not in titles:
        return None
    index = titles.index(current_title) + delta
    if index < 0 or index >= len(titles):
        return None
    title = titles[index]
    return level, title, scopes[law_id][level][title]


def scope_title_by_prefix(
    scopes: dict[str, dict[str, dict[str, list[str]]]],
    law_id: str,
    level: str,
    label: str,
) -> str | None:
    for title in scopes[law_id][level]:
        if title.startswith(label):
            return title
    return None


def natural_article_key(article_num: str) -> tuple[int, int]:
    article_num = article_num.split(":", 1)[0]
    parts = article_num.split("_", 1)
    base = int(parts[0])
    branch = int(parts[1]) if len(parts) > 1 else 0
    return base, branch


def write_graph_files(links: list[dict[str, object]], scope_links: list[dict[str, object]]) -> None:
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    write_yaml(
        LINKS_DIR / "article_links.yaml",
        {
            "generated_at": generated_at,
            "link_count": len(links),
            "links": links,
        },
    )

    write_yaml(
        LINKS_DIR / "scope_links.yaml",
        {
            "generated_at": generated_at,
            "scope_link_count": len(scope_links),
            "scope_links": scope_links,
        },
    )

    inbound: dict[str, list[dict[str, object]]] = defaultdict(list)
    outbound: dict[str, list[dict[str, object]]] = defaultdict(list)
    kind_counts: dict[str, int] = defaultdict(int)
    for link in links:
        from_key = f"{link['from']['law_id']}:{link['from']['article_num']}"
        to_key = f"{link['to']['law_id']}:{link['to']['article_num']}"
        inbound[to_key].append(
            {
                "law_id": link["from"]["law_id"],
                "article_num": link["from"]["article_num"],
                "label": link["label"],
                "kind": link["kind"],
                "confidence": link["confidence"],
            }
        )
        outbound[from_key].append(
            {
                "law_id": link["to"]["law_id"],
                "article_num": link["to"]["article_num"],
                "label": link["label"],
                "kind": link["kind"],
                "confidence": link["confidence"],
            }
        )
        kind_counts[str(link["kind"])] += 1

    referenced_by = []
    for target_key, sources in sorted(inbound.items()):
        law_id, article_num = target_key.split(":", 1)
        referenced_by.append(
            {
                "target": {"law_id": law_id, "article_num": article_num},
                "source_count": len(sources),
                "sources": sorted(
                    sources,
                    key=lambda source: (
                        str(source["law_id"]),
                        natural_article_key(str(source["article_num"])),
                        str(source["label"]),
                    ),
                ),
            }
        )

    write_yaml(
        LINKS_DIR / "referenced_by.yaml",
        {
            "generated_at": generated_at,
            "target_article_count": len(referenced_by),
            "referenced_by": referenced_by,
        },
    )

    write_yaml(
        LINKS_DIR / "article_links_summary.yaml",
        {
            "generated_at": generated_at,
            "link_count": len(links),
            "kind_counts": dict(sorted(kind_counts.items())),
            "source_article_count": len(outbound),
            "target_article_count": len(inbound),
            "links_path": str(LINKS_DIR / "article_links.yaml"),
            "referenced_by_path": str(LINKS_DIR / "referenced_by.yaml"),
            "scope_links_path": str(LINKS_DIR / "scope_links.yaml"),
            "scope_link_count": len(scope_links),
            "note": "Article links are direct article-to-article edges. Scope links point to chapter/section ranges and should be expanded only when needed to control RAG context size. Context-dependent references such as 同条 and 同項 are not resolved.",
        },
    )


def main() -> None:
    links, scope_links = build_links()
    write_graph_files(links, scope_links)
    print(f"Wrote {len(links)} article links to {LINKS_DIR / 'article_links.yaml'}")
    print(f"Wrote {len(scope_links)} scope links to {LINKS_DIR / 'scope_links.yaml'}")


if __name__ == "__main__":
    main()
