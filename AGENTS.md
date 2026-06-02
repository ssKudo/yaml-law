# エージェント向けメモ (Agent Notes)

本リポジトリは、将来的なRAG（Retrieval-Augmented Generation）開発に向けて、日本の建築基準法および施行令のデータセットを格納しています。現在のデータセットはe-Gov法令APIの現行法令XMLから生成されており、軽量なメタデータYAMLファイルと、個別の条文本文テキストファイルに分割されています。

## ディレクトリ構成

```text
data/
  datasets.yaml                    # 全データセットのインデックス
  links/                           # 参照関係（リンクグラフ）
    article_links.yaml             # 条文間の参照関係（フラットリスト）
    referenced_by.yaml             # 被参照（逆引き）インデックス
    scope_links.yaml               # 章・節などの範囲参照リンク
    article_links_summary.yaml     # リンク抽出の集計・統計情報
  building_standard_act/           # 建築基準法データ
    dataset.yaml                   # 基準法全体のメタデータ
    articles/                      # 条文メタデータ（YAML）※本文は含まない
      article_001.yaml
      article_002.yaml
      ...
    texts/                         # 条文本文（TXT）
      article_001.txt
      article_002.txt
      ...
    raw/                           # e-Govから取得した生XML
      325AC0000000201.xml
  building_standard_act_enforcement_order/ # 建築基準法施行令データ（構成は同上）
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
scripts/                           # データ生成・管理スクリプト
  fetch_egov_law.py                # e-Gov APIからデータを取得・分割するスクリプト
  build_link_graph.py              # 条文間の参照関係（リンクグラフ）を構築するスクリプト
```

## データセット

- `building_standard_act`
  - 法令名: 建築基準法
  - 法令ID: `325AC0000000201`
  - 情報源: e-Gov法令API 現行法令データ
  - 収録範囲: 本則のみ
  - 除外範囲: 附則

- `building_standard_act_enforcement_order`
  - 法令名: 建築基準法施行令
  - 法令ID: `325CO0000000338`
  - 情報源: e-Gov法令API 現行法令データ
  - 収録範囲: 本則のみ
  - 除外範囲: 附則

`data/datasets.yaml` は最上位のレジストリ（目次）です。また、各データセットのフォルダ内にも個別の `dataset.yaml` があり、ソースURL、取得日時、条文数、メタデータディレクトリ、本文ディレクトリ、および生のXMLパスが記録されています。

## メタデータYAMLと本文テキストファイル

各条文は以下の2つのファイルで表現されます：

```text
articles/article_001.yaml
texts/article_001.txt
```

YAMLファイルは意図的に軽量化されており、条文の本文は含みません。これは高速なスキャンや検索候補の絞り込みを低コストで行うことを目的としています。

例：

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
description: "建築物の敷地、構造、設備、用途に関する最低の基準を定めることで、国民の生命、健康、財産の保護を図り、公共の福祉の増進に資するという建築基準法の目的を定めた条文。"
text_path: "../texts/article_001.txt"
```

テキストファイルには、条文の本文テキスト全体が含まれます：

```text
（目的）
第一条
この法律は、...
```

`description`（説明文）フィールドは、検索に適した短い要約文や概要を記述するためのものです。本文のテキストファイルではなく、このメタデータYAMLファイル内に保持してください。

## 想定されるRAGの利用フロー

YAMLファイルを第一段階の検索・スキャン対象として使用します：

1. `data/datasets.yaml` を読み込み、利用可能なデータセットを特定する。
2. `articles/*.yaml` をスキャンし、法令名、章、節、条文タイトル、条文キャプション（見出し）、および `description` を対象に検索を行う。
3. マッチする可能性の高い条文のメタデータファイル（YAML）を選択する。
4. YAML内の `text_path` を頼りに、対応する本文テキストファイルを特定する（パスはYAMLファイルからの相対パス）。
5. 選択された `texts/*.txt` ファイルのみをロードし、完全な法的テキストとしてLLMのコンテキストに投入する。

これにより、検索処理を安価に保ち、必要な場合を除いて長い条文本文をパース・ロードすることを避けることができます。

## 参照リンク関係（リンクグラフ）

`data/links/` には、機械的に抽出された条文同士の参照関係が格納されています：

- `article_links.yaml`: 条文から他の条文への直接の参照エッジを示すフラットリスト。
- `referenced_by.yaml`: 被参照（逆引き）用のインデックス。どの条文がどの条文から参照されているかをグループ化。
- `scope_links.yaml`: 条文から特定の「章」や「節」といった範囲全体への参照リンク。
- `article_links_summary.yaml`: リンクのカウント数や生成時のノート。

現在の抽出ルールは意図的に堅実に設計されています：

- 施行令（enforcement_order）内の `法第...条` は、親法である建築基準法（building_standard_act）への参照として解決されます。
- 単なる `第...条` という記述は、同一法令内の条文参照として解決されます。
- `前条` および `次条` は、同一法令内で生成された条文の順序に基づいて解決されます。
- `第A条から第B条まで` は、同一法令内の個別の条文リンクへ自動展開されます。
- `この章`、`この節`、`前章`、`次章`、`前節`、`次節`、`第...章`、`第...節` は `scope_links.yaml` に記録され、デフォルトではコンテキストに直接展開されません（必要に応じて遅延ロードするため）。
- リンク先となる対象条文が、生成されたデータセット内に存在する場合のみリンクとして登録されます。
- 自己参照リンク（自分自身へのリンク）は除外されます。
- `同条`、`同項`、`同号` などの文脈依存の曖昧な参照は現在解決されません。
- 都市計画法や建築士法など、他法令への正式な参照は、それらのデータセットが追加されるまではリンクとして解決されません。

リンクグラフはメタデータYAMLとは完全に分離して生成されるため、手動で編集された `description` フィールドを上書きすることなく、いつでも再構築できます。

RAGのトークンコストを抑えるため、`article_links.yaml` は直接的な検索ヒントとして使用し、`scope_links.yaml` は遅延展開用のヒントとして扱ってください。スコープリンクは数十の条文に及ぶことがあるため、必要と判断されるまではコンテキストにすべてをロードしないようにしてください。

## 再生成・アップデート手順

e-Gov法令APIから最新データを再取得してデータセットを更新するには、`scripts/fetch_egov_law.py` を使用します。

建築基準法（基準法）の更新：

```bash
python scripts/fetch_egov_law.py \
  --law-id 325AC0000000201 \
  --slug building_standard_act
```

建築基準法施行令（施行令）の更新：

```bash
python scripts/fetch_egov_law.py \
  --law-id 325CO0000000338 \
  --slug building_standard_act_enforcement_order
```

スクリプトを実行すると、以下のファイルが書き出されます：
- `articles/*.yaml`
- `texts/*.txt`
- `raw/{law_id}.xml`
- 各フォルダの `dataset.yaml`
- 最上位の `data/datasets.yaml`

条文参照関係（リンクグラフ）の再構築：

```bash
python scripts/build_link_graph.py
```

これにより、`data/links/article_links.yaml`、`data/links/referenced_by.yaml`、`data/links/scope_links.yaml`、`data/links/article_links_summary.yaml` が再生成されます。

**注意**: 取得スクリプトを実行すると、対象ディレクトリ内の自動生成された `.yaml` ファイルや `.txt` ファイルは一度クリアされてから再書き出しされます。手動で編集したファイルがある場合は、上書きされて消えてしまうため実行前に退避させてください。

## ファイル名の命名規則

条文のファイル名はASCII文字で構成され、ソート可能な形式になっています：

- `第1条` -> `article_001.yaml` および `article_001.txt`
- `第6条の2` -> `article_006_2.yaml` および `article_006_2.txt`
- `第17条及び第18条` -> `article_017_18.yaml` および `article_017_18.txt`

`article_num` フィールドは、e-Gov XML内の数値形式（例：`"6_2"`, `"17_18"`）を保持します。日本語の条文タイトル（例：`"第六条の二"`, `"第十七条及び第十八条"`）は、`article_title` フィールドに格納されます。

## 重要なルール・規約

- 現在のデータセットには `MainProvision`（本則）のみが含まれます。
- `SupplementaryProvision`（附則）は現在、意図的に除外されています。
- 条文の本文テキストをメタデータ YAML ファイル（`articles/*.yaml`）の中に書き戻さないでください。
- AIエージェントが各フィールドを迅速に走査できるよう、YAMLファイル内では `description` フィールドを `text_path` フィールドの手前に配置してください。
- 法改正の差分調査や再現性のために、取得元の生のe-Gov XMLファイルを `raw/` フォルダ配下に保管し続けてください。
- 本リポジトリはGitリポジトリとして構成されています（歴史的経緯により記述をアップデート）。
