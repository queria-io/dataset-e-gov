# e-Gov

デジタル庁が e-Gov で公開するデータを SQL で検索できるテーブルにしたデータセットです。今は e-Gov 法令検索の法令データを収録しています。

## 法令（laws）

[e-Gov 法令検索](https://laws.e-gov.go.jp/)に収録されている憲法・法律・政令・勅令・府省令・規則の一覧、法令ごとの改正の履歴、本文を条ごとに分けたテーブルです。廃止・失効した法令と、施行日が来ていない改正も含みます。毎週、最新のデータを取得します。

| テーブル | 内容 |
| --- | --- |
| `laws.laws` | 1 行が 1 法令。法令名・法令番号・分類・廃止の状態と、取得した日の時点で施行されている法令履歴 |
| `laws.revisions` | 1 行が 1 法令履歴。新規制定・改正・廃止のたびに行ができます |
| `laws.articles` | 1 行が 1 条。現行と未施行の法令履歴の本文を、本則・附則ごとに条で分けています |

- `law_id`（法令 ID）は法令ごとに付く 15 桁の ID で、改正しても変わりません
- `law_revision_id`（法令履歴 ID）は `<法令 ID>_<施行日>_<改正法令の法令 ID>` の形です
- 改正法令も 1 つの法令として `laws.laws` にあります。`laws.revisions.amendment_law_id` から結合できます

## 使い方

ある法律の改正の履歴:

```sql
SELECT amendment_enforcement_date, amendment_law_num, amendment_law_title, current_revision_status
FROM e_gov.laws.revisions
WHERE law_id = '129AC0000000089'  -- 民法
ORDER BY amendment_enforcement_date;
```

現行の本文から語を含む条を検索する:

```sql
SELECT l.law_title, a.article_title, a.caption, a.text
FROM e_gov.laws.articles AS a
JOIN e_gov.laws.laws AS l USING (law_revision_id)
WHERE a.text LIKE '%オープンデータ%';
```

## 出典と利用条件

[e-Gov 法令 API Version 2](https://laws.e-gov.go.jp/api/2/swagger-ui) の法令一覧取得 API・法令履歴一覧取得 API と、[XML 一括ダウンロード](https://laws.e-gov.go.jp/bulkdownload/)の「すべての法令データ」を取得して加工しています。

- e-Gov 法令検索のコンテンツは[公共データ利用規約（第1.0版）](https://www.digital.go.jp/resources/open_data/public_data_license_v1.0)で提供されています（[利用規約](https://laws.e-gov.go.jp/terms/)）。法令の条文そのものは著作権法第 13 条により著作権の目的になりません
- 使うときは「e-Gov 法令検索（デジタル庁）（https://laws.e-gov.go.jp/）を加工して作成」のように、出典と加工したことを明記してください

## 収録範囲の注意

- 告示・通達・条例は含みません
- `laws.articles` は現行と未施行の法令履歴の本文です。過去の法令履歴と廃止した法令の本文は含みません
- 別表・様式・図は `laws.articles` に含みません。条の中の表は、セルの文字を続けて本文に入れています
- 条の無い本則・附則は、項をまとめて 1 行にし、`article_num` を NULL にしています

## ビルド

```bash
uv sync
uv run python main.py           # 取得して手元で dbt build（profiles.yml の環境変数が要る）
scripts/build.sh                # 取得・ビルドして Queria に公開する
```

`.github/workflows/sync.yml` が毎週月曜に作り直します。改正の履歴は法令ごとに API を呼ぶので、取得に 15 分ほどかかります。
