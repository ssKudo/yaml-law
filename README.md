# yaml-law | RAG向け日本法令構造化データセット

**RAG（Retrieval-Augmented Generation）などのLLMアプリケーション開発に向けて、日本の建築・都市計画・消防・不動産取引・民事関連法令を条文単位で整理した構造化データセットです。**

e-Gov法令APIから取得した現行法令XMLをパースし、「軽量なメタデータYAML」「本文テキストファイル」「条文間の参照関係を示すリンクグラフ」に分割しています。長大な法令本文を常時読み込まず、必要な条文だけを検索・ロードできる構成です。

---

## 特徴

1. **条文単位のチャンク設計**
   - 各条文を `articles/article_xxx.yaml`（メタデータ）と `texts/article_xxx.txt`（本文）のペアに分割しています。
   - ベクトル検索やキーワード検索の候補単位を、法令実務で自然な「条文」に揃えられます。
2. **高速スキャン用の軽量メタデータ**
   - YAMLファイルには本文を含めず、法令名、章・節、条文番号、見出し、`description`、`keywords`、本文パスだけを保持します。
   - まずYAMLだけをスキャンし、候補条文の本文だけを後から読む設計にできます。
3. **リンクグラフを構築済み**
   - `第...条`、`前条`、`次条`、`法第...条`、`令第...条`、範囲参照などを抽出し、`data/links/` に保存しています。
   - 回答時に参照先・被参照条文を追加ロードすることで、RAGの文脈不足を減らせます。

---

## データセットの範囲

- **状態**: e-Gov法令APIで取得した取得日時点の現行法令
- **対象部分**: 本則のみ
- **除外部分**: 附則
- **データセット一覧**: [`data/datasets.yaml`](data/datasets.yaml)

| 法令名 | 法令ID | 法令番号 | 条文数 | ディレクトリ |
| :--- | :--- | :--- | ---: | :--- |
| 建築基準法 | `325AC0000000201` | 昭和二十五年法律第二百一号 | 291 | [`data/building_standard_act`](data/building_standard_act) |
| 建築基準法施行令 | `325CO0000000338` | 昭和二十五年政令第三百三十八号 | 371 | [`data/building_standard_act_enforcement_order`](data/building_standard_act_enforcement_order) |
| 建築基準法施行規則 | `325M50004000040` | 昭和二十五年建設省令第四十号 | 189 | [`data/building_standard_act_enforcement_regulation`](data/building_standard_act_enforcement_regulation) |
| 都市計画法 | `343AC0000000100` | 昭和四十三年法律第百号 | 164 | [`data/city_planning_act`](data/city_planning_act) |
| 都市計画法施行令 | `344CO0000000158` | 昭和四十四年政令第百五十八号 | 102 | [`data/city_planning_act_enforcement_order`](data/city_planning_act_enforcement_order) |
| 消防法 | `323AC1000000186` | 昭和二十三年法律第百八十六号 | 263 | [`data/fire_service_act`](data/fire_service_act) |
| 消防法施行令 | `336CO0000000037` | 昭和三十六年政令第三十七号 | 92 | [`data/fire_service_act_enforcement_order`](data/fire_service_act_enforcement_order) |
| 高齢者、障害者等の移動等の円滑化の促進に関する法律 | `418AC0000000091` | 平成十八年法律第九十一号 | 88 | [`data/barrier_free_act`](data/barrier_free_act) |
| 民法 | `129AC0000000089` | 明治二十九年法律第八十九号 | 1173 | [`data/civil_code`](data/civil_code) |
| 住宅の品質確保の促進等に関する法律 | `411AC0000000081` | 平成十一年法律第八十一号 | 113 | [`data/housing_quality_assurance_act`](data/housing_quality_assurance_act) |
| 宅地建物取引業法 | `327AC1000000176` | 昭和二十七年法律第百七十六号 | 201 | [`data/real_estate_brokerage_act`](data/real_estate_brokerage_act) |

---

## ディレクトリ構成

```text
data/
  datasets.yaml
  <dataset_slug>/
    dataset.yaml
    articles/
      article_001.yaml
      ...
    texts/
      article_001.txt
      ...
    raw/
      <law_id>.xml
  links/
    article_links.yaml
    referenced_by.yaml
    scope_links.yaml
    article_links_summary.yaml
scripts/
  fetch_egov_law.py
  build_link_graph.py
```

---

## メタデータYAMLの例

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
keywords: ["目的", "最低基準", "生命保護", "健康保護", "財産保護", "公共の福祉"]
text_path: "../texts/article_001.txt"
```

対応する本文は `text_path` の先にあります。

```text
（目的）
第一条
この法律は、建築物の敷地、構造、設備及び用途に関する最低の基準を定めて、国民の生命、健康及び財産の保護を図り、もつて公共の福祉の増進に資することを目的とする。
```

`description` と `keywords` は検索補助フィールドです。新規追加データセットでは空のまま生成されているものがあります。

---

## RAGでの利用フロー

1. [`data/datasets.yaml`](data/datasets.yaml) を読み込み、利用可能なデータセットを確認する。
2. 質問分野に応じて、スキャン対象の法令群を絞る。
3. `articles/*.yaml` を対象に、法令名、章、節、条文タイトル、見出し、`description`、`keywords` を検索する。
4. 候補条文の `text_path` を解決し、対応する `texts/*.txt` だけをロードする。
5. 必要に応じて [`data/links/article_links.yaml`](data/links/article_links.yaml) や [`data/links/referenced_by.yaml`](data/links/referenced_by.yaml) から関連条文を追加する。
6. 範囲参照が必要な場合だけ [`data/links/scope_links.yaml`](data/links/scope_links.yaml) を遅延展開する。

---

## リンクグラフ

現在のリンクグラフ概要:

- article links: 5771
- scope links: 250
- summary: [`data/links/article_links_summary.yaml`](data/links/article_links_summary.yaml)

抽出対象:

- 同一法令内の `第...条`
- `前条` / `次条`
- `第A条から第B条まで`
- 施行令・施行規則内の `法第...条`
- 建築基準法施行規則内の `令第...条`
- `この章`、`この節`、`前章`、`次章`、`前節`、`次節`、`第...章`、`第...節`

未解決:

- `同条`、`同項`、`同号` などの文脈依存参照
- データセットに存在しない他法令への参照

---

## 再生成方法

法令データの再取得:

```bash
python3 scripts/fetch_egov_law.py --law-id 325AC0000000201 --slug building_standard_act
python3 scripts/fetch_egov_law.py --law-id 325CO0000000338 --slug building_standard_act_enforcement_order
python3 scripts/fetch_egov_law.py --law-id 325M50004000040 --slug building_standard_act_enforcement_regulation
python3 scripts/fetch_egov_law.py --law-id 343AC0000000100 --slug city_planning_act
python3 scripts/fetch_egov_law.py --law-id 344CO0000000158 --slug city_planning_act_enforcement_order
python3 scripts/fetch_egov_law.py --law-id 323AC1000000186 --slug fire_service_act
python3 scripts/fetch_egov_law.py --law-id 336CO0000000037 --slug fire_service_act_enforcement_order
python3 scripts/fetch_egov_law.py --law-id 418AC0000000091 --slug barrier_free_act
python3 scripts/fetch_egov_law.py --law-id 129AC0000000089 --slug civil_code
python3 scripts/fetch_egov_law.py --law-id 411AC0000000081 --slug housing_quality_assurance_act
python3 scripts/fetch_egov_law.py --law-id 327AC1000000176 --slug real_estate_brokerage_act
```

リンクグラフの再構築:

```bash
python3 scripts/build_link_graph.py
```

注意: `fetch_egov_law.py` は対象データセットの `articles/*.yaml` と `texts/*.txt` を再生成します。手動編集した `description` や `keywords` は上書きされるため、再取得前に退避してください。

---

## 🤖 AIエージェント/LLMへの検索指示プロンプト例（道筋の立て方）

本データセットの構造（軽量YAMLと本文テキストの分離、およびリンクグラフ）を最大限に活かして、AIエージェントやローカルLLM（RAG）に効率的に探索・回答させるための指示テンプレートとアプローチ例です。

### 1. Claude Code / Cline / Agentic IDE 等のAIエージェントへの指示例
AIエージェントに対して直接質問をする際、以下のプロンプトをカスタムシステムプロンプトに組み込むか、質問の冒頭に添えて使用することで、エージェントが余計なトークン消費を抑えながら正確な条文を探し出せるようになります。

> **AIエージェントへの指示テンプレート**
> 
> あなたは日本の法令（建築、都市計画、消防、民法、不動産取引等）に精通した優秀なアシスタントです。ユーザーの質問に回答するにあたり、以下のステップに従って本リポジトリの構造化データを探索してください。
> 
> **【探索ステップ】**
> 1. まず `data/datasets.yaml` を読み込み、利用可能な法令データセットのパスを確認します。
> 2. 次に `data/<法令ディレクトリ>/articles/*.yaml` をスキャンし、質問に関連する `description`、`keywords`、`article_caption`（見出し）を持つ条文メタデータ（YAML）を特定します。
> 3. 特定した条文の `text_path` を参照し、対応する本文テキストファイル（`texts/*.txt`）を読み込んでコンテキストに含めます。
> 4. 必要に応じて、`data/links/article_links.yaml`（参照リンク）や `data/links/referenced_by.yaml`（被参照リンク）を確認し、読み込んだ条文が参照している（または参照されている）他の条文本文も追加ロードしてください。
> 5. 最終的に、読み込んだ本文テキストのみに基づいて、正確な条文番号を明記してユーザーの質問に回答してください。
> 
> **【質問】**
> 〇〇について、どのような制限や規定がありますか？

### 2. ローカルモデルでのRAGシステム開発における展望
メモリやリソースの限られたローカル環境において、Llama 3やMistralなどのオープンモデルを用いてRAG（検索拡張生成）システムを構築する際の実装ガイドラインです。

- **メタデータ事前スキャン (Router / Filtering)**:
  ローカルの処理負荷を抑えるため、まずは `articles/*.yaml` の `description` と `keywords` のテキスト埋め込み（Embeddings）を作成し、ローカルのベクトルデータベース（Chroma、FAISS等）にインデックスします。質問に対して、まずこのメタデータインデックスを検索して関連する条文ID（例：`building_standard_act:article_002`）をトップk件抽出します。
- **コンテキストの動的拡張 (Link Graph Integration)**:
  抽出されたYAMLの `text_path` にある本文を読み込むとともに、`data/links/article_links.yaml` から該当条文の「参照先（`targets`）」の条文本文もローカルDBから引いて結合し、LLMに渡します。

これにより、ローカルモデルの限られたコンテキストウィンドウでも、法的な文脈（条文の参照関係）を崩さずに、かつノイズを排して正確な回答を生成可能です。

---

## 出典とライセンス

### データの出典

本データセット内の法令データは、デジタル庁のe-Gov法令APIより取得したデータを加工して作成しています。

- e-Gov法令検索: https://laws.e-gov.go.jp/

### ライセンス

- 作成コード・スクリプト: MITライセンス。詳細は [`LICENSE`](LICENSE) を参照してください。
- 法令データ自体: 日本の著作権法第13条に基づき、法令データ自体は著作権の対象外です。
