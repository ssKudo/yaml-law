# Agent Notes

This repository stores Japanese building regulation datasets for later RAG
work. The current datasets are generated from the e-Gov Law API current-law
XML and are split into lightweight metadata files and separate article text
files.

## Directory Layout

```text
data/
  datasets.yaml
  links/
    article_links.yaml
    referenced_by.yaml
    scope_links.yaml
    article_links_summary.yaml
  building_standard_act/
    dataset.yaml
    articles/
      article_001.yaml
      article_002.yaml
      ...
    texts/
      article_001.txt
      article_002.txt
      ...
    raw/
      325AC0000000201.xml
  building_standard_act_enforcement_order/
    dataset.yaml
    articles/
      article_001.yaml
      article_002.yaml
      ...
    texts/
      article_001.txt
      article_002.txt
      ...
    raw/
      325CO0000000338.xml
scripts/
  fetch_egov_law.py
  build_link_graph.py
```

## Datasets

- `building_standard_act`
  - Law title: 建築基準法
  - Law ID: `325AC0000000201`
  - Source: e-Gov Law API current-law data
  - Included scope: 本則 only
  - Excluded scope: 附則

- `building_standard_act_enforcement_order`
  - Law title: 建築基準法施行令
  - Law ID: `325CO0000000338`
  - Source: e-Gov Law API current-law data
  - Included scope: 本則 only
  - Excluded scope: 附則

`data/datasets.yaml` is the top-level registry. Each dataset also has its own
`dataset.yaml` with source URL, fetch timestamp, article count, metadata
directory, text directory, and raw XML path.

## Metadata YAML And Text Files

Each article is represented by two files:

```text
articles/article_001.yaml
texts/article_001.txt
```

The YAML file is intentionally lightweight and does not contain the article
body. It is meant for fast scanning and candidate selection.

Example:

```yaml
law_id: "325AC0000000201"
law_title: "建築基準法"
law_num: "昭和二十五年法律第二百一号"
source: "e-Gov法令検索"
source_url: "https://laws.e-gov.go.jp/api/1/lawdata/325AC0000000201"
part: "本則"
chapter: "第一章 総則"
section: null
subsection: null
division: null
article_num: "1"
article_title: "第一条"
article_caption: "（目的）"
description: ""
text_path: "../texts/article_001.txt"
```

The text file contains the full article text:

```text
（目的）
第一条
この法律は、...
```

`description` is currently empty by design. It should be filled later with a
short retrieval-oriented description or summary. Keep it in the YAML file, not
in the text file.

## Intended RAG Usage

Use the YAML files as the first-stage scan target:

1. Read `data/datasets.yaml` to find available datasets.
2. Scan `articles/*.yaml` for law title, chapter, section, article title,
   article caption, and `description`.
3. Select likely matching article metadata files.
4. Resolve `text_path` relative to the YAML file.
5. Load only the matched `texts/*.txt` files as the full legal text.

This keeps scanning cheap and avoids parsing long article bodies unless they
are needed.

## Link Graph

`data/links/` contains machine-generated article reference links:

- `article_links.yaml`: flat edge list from one article to another.
- `referenced_by.yaml`: reverse lookup grouped by target article.
- `scope_links.yaml`: links from an article to a chapter/section scope.
- `article_links_summary.yaml`: counts and generation notes.

Current extraction rules are intentionally conservative:

- `法第...条` in 建築基準法施行令 is treated as a reference to 建築基準法.
- Bare `第...条` is treated as a same-law article reference.
- `前条` and `次条` are resolved by generated article order in the same law.
- `第A条から第B条まで` is expanded to same-law article links.
- `この章`, `この節`, `前章`, `次章`, `前節`, `次節`, `第...章`,
  and `第...節` are written to `scope_links.yaml`, not expanded into prompt
  context by default.
- Matches are kept only when the target article exists in the generated
  datasets.
- Self-links are dropped.
- Context-dependent references such as `同条`, `同項`, and `同号` are not
  resolved.
- Formal references to other laws, such as 都市計画法 or 建築士法, are not
  linked unless those laws are added as datasets later.

The graph is generated separately from article metadata so it can be rebuilt
without touching manually edited `description` fields.

For RAG cost control, treat `article_links.yaml` as direct retrieval hints and
`scope_links.yaml` as lazy expansion hints. A scope link may cover dozens of
articles, so do not load the entire scope into the LLM context unless a later
search step narrows it down.

## Regeneration

Use `scripts/fetch_egov_law.py` to regenerate datasets from e-Gov.

Building Standard Act:

```bash
python3 scripts/fetch_egov_law.py \
  --law-id 325AC0000000201 \
  --slug building_standard_act
```

Building Standard Act Enforcement Order:

```bash
python3 scripts/fetch_egov_law.py \
  --law-id 325CO0000000338 \
  --slug building_standard_act_enforcement_order
```

The script writes:

- `articles/*.yaml`
- `texts/*.txt`
- `raw/{law_id}.xml`
- dataset-level `dataset.yaml`
- top-level `data/datasets.yaml`

Article link graph:

```bash
python3 scripts/build_link_graph.py
```

This writes `data/links/article_links.yaml`,
`data/links/referenced_by.yaml`, `data/links/scope_links.yaml`, and
`data/links/article_links_summary.yaml`.

The script clears generated `.yaml` files in the target `articles/` directory
and generated `.txt` files in the target `texts/` directory before writing the
new files. Be careful if manually edited generated files exist there.

## File Naming

Article filenames are ASCII and sortable:

- `第1条` -> `article_001.yaml` and `article_001.txt`
- `第6条の2` -> `article_006_2.yaml` and `article_006_2.txt`

The `article_num` field keeps the e-Gov XML numeric form, such as `"6_2"`.
The Japanese article title is stored in `article_title`, such as
`"第六条の二"`.

## Important Conventions

- Current datasets include only `MainProvision` / 本則.
- Supplementary provisions / 附則 are intentionally excluded for now.
- Do not put full article body text back into `articles/*.yaml`.
- Keep `description` before `text_path` in metadata files so agents can scan
  useful fields quickly.
- Preserve raw e-Gov XML files under `raw/` for reproducibility and later diff
  work around amendments.
- The repository is not currently initialized as a Git repository.
