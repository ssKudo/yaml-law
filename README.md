# yaml-law | RAG向け日本法令構造化データセット

**二級建築士である作者が、RAG（Retrieval-Augmented Generation）などのLLMアプリケーション開発に向けて、主に実務で使用される建築・都市計画・消防・不動産取引・民事関連法令を条文単位で整理した構造化データセットです。**

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

- **エディション**: 2026年6月版パッケージ（2026年6月時点の現行法令のスナップショットとして固定）
- **対象部分**: 本則のみ
- **除外部分**: 附則

> [!NOTE]
> 本リポジトリは、法改正に対して動的に追従してデータを上書き更新するのではなく、書籍のように「2026年6月版」としてデータを固定するパッケージ方式を採用しています。将来の法改正への対応や別時点のデータセットは、別エディション（別ブランチや別リポジトリなど）として管理・提供する方針です。

## データセット一覧

全データセットの一覧は [`data/datasets.yaml`](data/datasets.yaml) に登録されています。


| 法令名 | 法令番号 | 収録されている最新施行日 | 条文数 | 整備状況 |
| :--- | :--- | :--- | ---: | :--- |
| [建築基準法](data/building_standard_act) | 昭和25年法律第201号 | R8.4.1 | 291 | 完了 |
| [建築基準法施行令](data/building_standard_act_enforcement_order) | 昭和25年政令第338号 | R7.12.1 | 371 | ベースライン整備済み（要精査） |
| [建築基準法施行規則](data/building_standard_act_enforcement_regulation) | 昭和25年建設省令第40号 | R8.4.1 | 189 | 完了 |
| [都市計画法](data/city_planning_act) | 昭和43年法律第100号 | R8.4.1 | 164 | 完了 |
| [都市計画法施行令](data/city_planning_act_enforcement_order) | 昭和44年政令第158号 | R8.4.1 | 102 | 完了 |
| [消防法](data/fire_service_act) | 昭和23年法律第186号 | R5.6.16 | 263 | ベースライン整備済み（要精査） |
| [消防法施行令](data/fire_service_act_enforcement_order) | 昭和36年政令第37号 | R7.10.1 | 92 | ベースライン整備済み（要精査） |
| [バリアフリー法](data/barrier_free_act) | 平成18年法律第91号 | R7.4.1 | 88 | ベースライン整備済み（要精査） |
| [民法](data/civil_code) | 明治29年法律第89号 | R8.4.1 | 1173 | ベースライン整備済み（要精査） |
| [住宅品確法](data/housing_quality_assurance_act) | 平成11年法律第81号 | R6.4.1 | 113 | ベースライン整備済み（要精査） |
| [宅地建物取引業法](data/real_estate_brokerage_act) | 昭和27年法律第176号 | R8.4.1 | 201 | ベースライン整備済み（要精査） |

整備状況は、条文メタデータの `description` と `keywords` の入力状況を示します。本文・条文YAML・raw XMLが存在していても、この2項目が空の場合は「本文収録・メタデータ未整備」とします。件数は [`scripts/validate_dataset.py`](scripts/validate_dataset.py) で確認できます。

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

エージェントAI/RAG向けの配布に必要な中心部分は `data/`、`scripts/`、`README.md`、`LICENSE` です。ルートの `index.html` は紹介用の任意ページであり、データセット利用に必須ではありません。

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

再生成・編集後の整合性確認:

```bash
python3 scripts/validate_dataset.py
```

注意: `fetch_egov_law.py` は対象データセットの `articles/*.yaml` と `texts/*.txt` を再生成します。同じ条文番号の既存 `description` と `keywords` は保持されますが、新規条文のメタデータは空で生成されるため、再生成後に [`scripts/validate_dataset.py`](scripts/validate_dataset.py) を実行してください。

---

## ⚠️ 本設計の制約（弱点）と実運用上の推奨アプローチ

本データセットは、RAGシステムとしての「メンテナンス性」や「データの取り回しの良さ」を最優先し、条文ごとに軽量なメタデータYAML（概要・キーワード）と本文テキストを分離する設計を採用しています。この設計には以下の制約（弱点）があるため、開発・運用の際には下記のアプローチを推奨します。

### 1. メタデータ検索の限界と「クエリ拡張」の推奨
- **制約**: YAML内の `description` や `keywords` を用いたキーワード一致検索（またはメタデータスキャン）を想定した構成のため、ユーザーが入力した質問の表現と言葉づかいが完全一致しない場合にヒットしにくいという弱点があります。
- **推奨アプローチ**: ユーザーの質問から検索クエリを生成する際、検索システム側で**「クエリ拡張（Query Expansion）」**（質問文から類義語、同義語、関連する法定義語を展開する処理）を挟むことを強く推奨します。これにより、検索漏れを大幅に低減できます。

### 2. LLMによる自動生成メタデータの精度とフィードバックループ
- **制約**: 整備済み条文の `description` および `keywords` には、LLM（Gemini 3.5 Flash）による生成分と、[`scripts/enrich_metadata.py`](scripts/enrich_metadata.py) による見出し・本文冒頭ベースの生成分が含まれます。そのため、重要キーワードの抜け漏れや、要約の不十分さによってヒットしないケースが起こり得ます。後者は検索用のベースラインであり、法的判断のための要約ではありません。
- **推奨アプローチ**: 広大な法令範囲を考慮すると、初期段階ですべての条文を手動でつぶさに校正・整備するのはコスト的に非現実的です。
  そのため、まずはLLMで一括して自動生成したデータセットをベースとし、**「実際のRAGシステムの回答状況や検索のログを監視しながら、ヒットしなかったキーワードをピンポイントで肉付け・更新していく」**というフィードバックループ型の運用を行うことを推奨します。

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

## 免責事項

本データセットは、RAG（検索拡張生成）などのAIアプリケーション開発に向けた実験的なデータ整理を目的として公開されています。利用にあたっては以下の事項をご了承ください。

1. **正確性・完全性について**
   法令データはe-Gov法令APIより取得・加工したものであり、また概要（`description`）およびキーワード（`keywords`）はLLM（AI）によって自動生成されたものです。データの完全性、正確性、適合性、または最新性について、作者は一切の保証を行いません。
2. **責任の制限**
   本データセット（およびこれを利用したシステム）の利用によって生じた直接的、間接的、または偶発的な損害、損失、不利益について、作者は一切の責任を負いません。実務上での法的な判断や設計行為を行う際は、必ず公式のe-Gov法令検索、官報、または関係行政機関へご確認いただくか、しかるべき専門家にご相談ください。

---

## 出典とライセンス

### データの出典

本データセット内の法令データは、デジタル庁のe-Gov法令APIより取得したデータを加工して作成しています。

- e-Gov法令検索: https://laws.e-gov.go.jp/

### ライセンス

- 作成コード・スクリプト: MITライセンス。詳細は [`LICENSE`](LICENSE) を参照してください。
- 法令データ自体: 日本の著作権法第13条に基づき、法令データ自体は著作権の対象外です。
