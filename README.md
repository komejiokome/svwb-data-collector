# svwb-data-collector

Shadowverse: Worlds Beyond の公開情報を定期取得し、**SQLite + JSON + 差分サマリー**としてローカル保存する Python ツールです。

## 目的
- 公式カード一覧 / Deck Portal を優先収集
- 公式大会結果（Shadowverse Online Championship）を優先収集
- 公式公開デッキ情報（RAGE Shadowverse Pro League）を優先収集
- 非公式サイトは補助扱いで保存（`is_official=false` ラベル）
- 実行ごとの差分を検知して `latest_summary.md` を生成

## ソース優先順位
1. 公式カード一覧 / Deck Portal (`official_cards`)
2. Shadowverse Online Championship (`svoc`)
3. RAGE Shadowverse Pro League (`rage`)
4. 非公式補助ソース (`unofficial_support`)

## セットアップ
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 実行方法
```bash
svwb-collect
```

オプション例:
```bash
svwb-collect --db data/svwb.sqlite --json-out exports/latest.json --summary-out latest_summary.md
```

## 出力
- `data/svwb.sqlite`: 正規化済み保存先
  - `runs`: 実行履歴
  - `sources`: ソース定義（公式/非公式ラベル）
  - `items`: 正規化アイテム
  - `run_diffs`: 実行差分（new/updated）
- `exports/latest.json`: 最新スナップショット
- `latest_summary.md`: 差分サマリー

## 実装方針
- コネクタ分離
  - `official_cards.py`
  - `svoc.py`
  - `rage.py`
  - `unofficial.py`
- `requests + BeautifulSoup` を基本採用（official_cards は一覧 discovery → 詳細巡回の2段階）
- Playwright は v1 では未使用（必要時に追加しやすい構成）
- アクセス配慮
  - `robots.txt` を確認
  - User-Agent を明示
  - リトライ + タイムアウト
  - ホスト単位の最小間隔制御
  - 簡易ファイルキャッシュ（TTL）
- 取得失敗は source 単位で warning にして継続（全停止しない）

## GitHub Actions（1日1回）
`.github/workflows/daily-collect.yml` で毎日1回実行し、生成物を Artifact としてアップロードします（生成物は Git 管理しません）。


## GitHub Actions から official_cards を手動実行する
`manual-official-cards` workflow を使うと、外部到達可能な GitHub Actions 環境で official_cards 単体実行を確認できます。

手順:
1. GitHub の Actions タブで `manual-official-cards` を開く
2. **Run workflow** を実行
3. 実行完了後、まず Job の **Summary** を確認（first check）
4. 必要に応じて Artifacts から `official-cards-run-<run_id>-<run_status>` をダウンロード
5. 中身の `latest_summary.md` と `exports/latest.json` を確認

workflow 内で実行するコマンド:
```bash
./setup.sh
svwb-collect --sources official_cards --timeout 30 --min-interval 1.0
```

成功条件 / partial 条件:
- success: 最新 run の `status=success`
- partial: 最新 run の `status=partial`（例: 取得0件、または blocked）

どちらの場合も artifact はアップロードされます。

Job Summary には次が表示されます。
- run_status と生成ファイル名はコード表示でそのまま読めます。
- run_status
- total_items
- warnings 件数
- blocked source の有無
- source_url
- 生成ファイル名

first check は Summary だけで可能です。詳細が必要な場合のみ artifact を開いてください。

## v1 のスコープ
- 事実収集基盤の構築に集中
- 環境分析やメタゲーム推定ロジックは未実装

## 注意
- 実運用時は各サイトの利用規約・robots・アクセス負荷に必ず従ってください。
- マークアップ変更によりセレクタ調整が必要になる場合があります。

## トラブルシュート
- `pip install -e .` がネットワーク制限で失敗する環境では、到達可能な Python パッケージミラーを設定してください。
- 依存未導入のまま `svwb-collect` を実行すると、エラーメッセージを出して終了します。
- ヘルプ表示のみ確認したい場合は、`python -m svwb_collector.cli --help` でも確認できます。


## 最小検証手順（ローカル）
依存導入後に README 通り実行できることを最小限で確認できます。

```bash
python -m venv .venv
source .venv/bin/activate
./setup.sh
svwb-collect --help
python -m unittest discover -s tests -v
```

- `svwb-collect --help`: console script が正しく登録されているかの smoke test
- `python -m unittest ...`: fixture ベースのパーサ検証（ライブサイトアクセスなし）

## CI で確認していること
`.github/workflows/verify.yml` では以下を自動実行します。

1. Python 3.11 セットアップ
2. 依存導入（`./setup.sh`）
3. `svwb-collect --help`
4. `python -m unittest discover -s tests -v`

## セットアップスクリプト
- `setup.sh`（`scripts/setup.sh` のラッパー）を追加しています。
- Codex の新規 worktree でも同一手順を再利用しやすいよう、依存導入コマンドを 1 箇所に集約しています。


## 実測済みコマンド（official_cards 最小確認）
以下は実際に確認した最小コマンドです。

```bash
./setup.sh
svwb-collect --sources official_cards --timeout 30 --min-interval 1.0
ls -lh data/svwb.sqlite exports/latest.json latest_summary.md
```

## 実際の出力例（この環境での実測）
- `data/svwb.sqlite`: 36KB（`runs=1`, `items=0`, `run_diffs=0`）
- `exports/latest.json`: `total_items=0`
- `latest_summary.md`: `warnings=2`（robots.txt / 接続制約由来）

`official_cards` のみ実行したい場合:
```bash
svwb-collect --sources official_cards
```

## 既知の制約（実測ベース）
- ネットワーク環境によっては外部サイトアクセスが制限され、取得件数が 0 件になる場合があります。
- その場合でも collector 自体は完走し、SQLite/JSON/summary は生成されます。
- `--sources` はカンマ区切りで対象を限定できます（例: `official_cards` のみ）。



## official_cards の取得方式（一覧→詳細）
- 一覧ページは **全件 discovery** のために使います（表示リンク数ではなく、埋め込みデータ/script も探索）。
- discovery で得た `card_id` / 詳細URLを使って詳細ページを巡回します。
- detail URL は WB 公式ドメインの場合に `.../card/?card_id=` へ正規化します。
- 最終的な source of truth は各カードの詳細ページです。

取得項目:
- カード名
- コスト
- クラス
- レアリティ
- 種類
- タイプ
- スタッツ
- 効果
- 収録パック
- トークンかどうか
- source_url
- fetched_at

## official_cards の実際に使う取得元
- discovery 一覧: `https://shadowverse-wb.com/ja/deck/cardslist/`, `https://shadowverse-portal.com/deckbuilder/create/1?lang=ja`
- detail 正規URL: `https://shadowverse-wb.com/ja/deck/cardslist/card/?card_id=<card_id>`

## robots 拒否URLの扱い
- `https://shadowverse-wb.com/ja/cards` は robots/到達性の制約で拒否されるケースがあるため、**主導線から除外**しました。
- 上記 URL は参照用（blocked 想定）として扱い、通常収集フローではアクセスしません。

## run status の扱い（現行）
- `success`: 1件以上取得でき、blocked source がない
- `partial`: 取得件数が 0 件、または source が blocked

`official_cards` が全URLで取得失敗した場合は、warning に加えて `BLOCKED` を明示します。


## 生成物の扱い
- `data/svwb.sqlite` / `exports/latest.json` / `latest_summary.md` は実行時生成物です。
- これらは **Git 管理しません**（`.gitignore` 対象）。
- 確認は GitHub Actions の Artifact を利用してください。


## official_cards は暫定扱い
- official_cards は non-zero 取得経路を確認済みですが、**全件取得確認が完了するまでは暫定扱い**です。
- 現在は `shadowverse-portal.com` の deckbuilder 導線を主導線として採用し、件数拡大を優先しています。
