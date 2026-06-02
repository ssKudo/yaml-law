# yaml-law | RAG向け建築基準法・施行令構造化データセット

**RAG（Retrieval-Augmented Generation）などのLLMアプリケーション開発に最適化された、日本の建築基準法および建築基準法施行令の構造化データセットです。**

e-Gov法令APIから取得した最新のXMLデータをパースし、「軽量なメタデータYAML」「本文テキストファイル」「条文間の参照関係を示すリンクグラフ」に分割・整理しています。これにより、低コストかつ高精度な法律RAGの開発が可能になります。

---

## 🌟 特徴・意義（RAG開発におけるメリット）

1. **RAGのチャンク設計に完全対応 (条文単位の分割)**
   - 巨大な法律テキストをそのまま読み込ませるのではなく、1条文ごとに `articles/article_xxx.yaml`（メタデータ）と `texts/article_xxx.txt`（本文）のペアに分割。
   - ベクトル検索エンジンに登録する際、不要なノイズを含まないクリアなチャンク作成が可能です。
2. **高速スキャン用の超軽量メタデータ**
   - YAMLファイルには本文データを含めていません。章・節・条文番号・見出し（キャプション）などのメタデータのみを記録しているため、まずはYAMLだけで全件スキャンやキーワードマッチ、フィルタリングを安価かつ超高速に行えます。
3. **条文間の参照関係（リンクグラフ）を構築済み**
   - 法律文書に頻出する「第A条第B項」「前条」「法第C条」といった内部参照を解析し、隣接リスト形式のデータ（`data/links/article_links.yaml`）および逆引きデータ（`referenced_by.yaml`）を自動生成しています。
   - LLMが回答する際に、参照元の条文だけでなく、参照先の条文もプロンプトに動的に追加することで、法解釈のハルシネーション（嘘の回答）を防ぐコンテキスト拡張が容易になります。

---

## 📅 データセットの範囲と基準日

* **基準日（データ取得日）**: 2026年5月30日
* **状態**: 取得日時点で施行中の現行法令（e-Gov法令API現行法令データより）
* **対象データ**: **本則のみ**（附則は含みません）
* **収録法令**:
  | 法令名 | 法令ID | 法令番号 | 条文数 | ディレクトリ |
  | :--- | :--- | :--- | :--- | :--- |
  | **建築基準法** | `325AC0000000201` | 昭和二十五年法律第二百一号 | 291 | [`data/building_standard_act`](file:///c:/Users/owner/git-projects/yaml-law/data/building_standard_act) |
  | **建築基準法施行令** | `325CO0000000338` | 昭和二十五年政令第三百三十八号 | 371 | [`data/building_standard_act_enforcement_order`](file:///c:/Users/owner/git-projects/yaml-law/data/building_standard_act_enforcement_order) |

---

## 📁 ディレクトリ構成

リポジトリ内の主要な構成は以下の通りです。

```text
data/
  datasets.yaml                    # 全データセットのインデックス
  building_standard_act/           # 建築基準法データ
    dataset.yaml                   # 法令全体のメタデータ
    articles/                      # 条文メタデータ（YAML）※本文は含まない
      article_001.yaml
      ...
    texts/                         # 条文本文（TXT）
      article_001.txt
      ...
    raw/                           # e-Govから取得した生XML
      325AC0000000201.xml
  building_standard_act_enforcement_order/ # 建築基準法施行令データ（構成は同上）
  
  links/                           # 参照関係（リンクグラフ）
    article_links.yaml             # 条文から条文への参照エッジ（フラットリスト）
    referenced_by.yaml             # 被参照（逆引き）インデックス
    scope_links.yaml               # 「この章」「第3章から第5章まで」などの範囲参照
    article_links_summary.yaml     # リンク抽出の集計・統計情報
```

---

## 🔍 メタデータYAMLの構造例

`data/building_standard_act/articles/article_002.yaml` の例：
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
article_num: "2"
article_title: "第二条"
article_caption: "（用語の定義）"
description: ""                             # RAG用の概要文（将来的な拡張用）
text_path: "../texts/article_002.txt"       # 本文ファイルへの相対パス
```

対応する本文 `data/building_standard_act/texts/article_002.txt` の内容：
```text
（用語の定義）
第二条
この法律において次の各号に掲げる用語の意義は、当該各号に定めるところによる。
一　建築物　土地に定着する工作物のうち、屋根及び柱若しくは壁を有するもの...
二　特殊建築物　学校（専修学校及び各種学校を含む。以下同様とする。）、体育館、病院...
...
```

---

## 🔗 リンクグラフの仕様

`data/links/article_links.yaml` には、条文から他の条文への直接参照が記述されています。

* **抽出ルール**:
  - `法第...条`（施行令から法への参照）の自動解決
  - 同一法令内の `第...条` 参照の解決
  - `前条` `次条` の順序解決
  - `第A条から第B条まで` の範囲参照の個別展開（例: A条、A+1条、... B条それぞれへのリンク）
  - ※ 自己リンクは除外されます。また、「同条」「同項」などの文脈依存の曖昧な参照、および本データセット外の法令（都市計画法など）へのリンクは現在未対応です。
  - ※ 「この章」「前節」などの範囲・スコープ指定の参照は `scope_links.yaml` に分けて保存しています。

---

## 🛠 再生成方法（データ更新手順）

法令データの再取得や、法改正時のリンク再生成は以下のスクリプトで実行可能です。

```bash
# 建築基準法の再取得
python scripts/fetch_egov_law.py --law-id 325AC0000000201 --slug building_standard_act

# 建築基準法施行令の再取得
python scripts/fetch_egov_law.py --law-id 325CO0000000338 --slug building_standard_act_enforcement_order

# リンクグラフの再構築
python scripts/build_link_graph.py
```

---

## 🤖 使用モデル

本データセットの構築・加工には、以下のAIモデルを使用しています。

- **法令データの取得・パース、およびYAML・本文テキストの作成**: `GPT-5.5-Middle`
- **YAMLメタデータの概要文（description）および関連キーワードの生成**: `Gemini 3.5 Flash`

---

## ⚖️ 出典とライセンス

### データの出典
本データセット内の法令データは、デジタル庁の**e-Gov法令API**より取得したデータを加工して作成しています。
- **出典**: e-Gov法令検索（[https://laws.e-gov.go.jp/](https://laws.e-gov.go.jp/)）

### ライセンス
- **データセットの作成コード・スクリプト**: **MITライセンス**（詳細は [LICENSE](file:///c:/Users/owner/git-projects/yaml-law/LICENSE) をご参照ください。商用利用・改変・再配布含め自由にご利用いただけます）
- **法令データ自体**: 日本の著作権法第13条（権利の目的とならない著作物）に基づき、法令データ自体は著作権の対象外（パブリックドメイン）となります。
