# AGENTS.md

## Project
svwb-data-collector

## Purpose
Shadowverse: Worlds Beyond の公開情報を収集し、信頼できる情報源として再利用可能な形で保存する。

このプロジェクトでは、まず **official_cards** を成立させることを最優先とする。
大会データや環境分析は後段であり、カード収集基盤が未完成の間は優先しない。

---

## Top Priority
1. official_cards を安定取得できる状態にする
2. GitHub Actions の Summary だけで成功/partial を判定できる状態を維持する
3. SQLite / JSON / latest_summary.md の3成果物を毎回生成する
4. その後に svoc
5. さらに後で rage / unofficial
6. 環境分析ロジックは最後

---

## Hard Rules
- **official_cards が十分な件数で取得確認できるまで、svoc に進まない**
- **rage / unofficial / 分析機能は、official_cards と svoc が安定するまで追加しない**
- **非公式サイトは source of truth にしない**
- **robots で拒否されるURLは通常フローから除外する**
- **0件取得は success にしない**
- **non-zero でも明らかに少なすぎる件数は pass にしない**
- **生成物（sqlite, cache, pyc など）は Git 管理しない**
- **差分は常に最小に保つ**
- **README と実装がずれたら、README か実装のどちらかを必ず修正する**
- **Playwright は最後の手段。まず requests / BeautifulSoup / 埋め込みJSON解析で解決を試みる**

---

## Current State Policy
official_cards は「一覧ページ → 詳細ページ」方式で実装する。

### official_cards の原則
- 一覧ページは **discovery 用**
- 詳細ページは **source of truth**
- 一覧ページの初期表示リンク数は信用しない
- `<a href>` のみではなく、`<script>` 内の埋め込み JSON や構造化データも見る
- card_id が取れるなら、それを正とする

### official_cards の正式方針
1. 一覧ページから card_id または detail_url を列挙する
2. detail_url がなければ `card_id` から詳細URLを正規構築する
3. 詳細ページを1件ずつ取得する
4. 詳細ページHTMLから必要項目を抽出する
5. SQLite / JSON / latest_summary.md に保存する

### 詳細URL
WB の詳細ページURLは次を正規形とする。

`https://shadowverse-wb.com/ja/deck/cardslist/card/?card_id={card_id}`

この形式以外の fallback を作る場合も、最終的にこの正規形へ寄せること。

---

## official_cards Success Criteria
official_cards を pass 扱いにする条件は以下。

- external reachable environment で実行できる
- discovered card count が non-zero
- fetched detail count が non-zero
- saved item count が non-zero
- blocked source ではない
- source_url が明示されている
- 詳細ページ由来の項目が実際に保存される
- 件数が「初期表示の一部リンクだけ取れた状態」より明確に大きい
- `saved item count <= 10` のような明らかに少数の状態は **partial** とする

### official_cards Result Policy
- `success`:
  - saved item count > 0
  - blocked source なし
  - 件数が妥当
- `partial`:
  - 0件
  - blocked source あり
  - 件数が不自然に少ない
  - discovery はできたが detail fetch が成立していない
- `fail`:
  - 実行自体が壊れて成果物も出ない
  - CLI / workflow / setup が壊れている

---

## Data Fields
official_cards で最低限保存する項目:

- name
- cost
- class
- rarity
- kind
- type
- stats
- effect
- pack
- is_token
- source_url
- fetched_at

不足がある場合は warning または empty value で扱い、無言で捨てない。

---

## Workflow Rules
### When working on official_cards
必ずこの順で進める:

1. discovery を確認
2. detail URL の正規化を確認
3. detail parser を確認
4. 保存処理を確認
5. Summary / README を整合させる
6. その後に only-small-change で修正する

### Do not jump ahead
以下は official_cards 完了前にはやらない:

- svoc の本実装
- rage の本実装
- unofficial source の拡張
- 環境分析
- Playwright 導入
- UI 追加
- 大規模リファクタ

---

## Testing Rules
修正時は、最低限以下を維持または追加すること。

### Required
- smoke test
- discovery fixture test
- detail page parser fixture test
- embedded JSON extraction test
- URL normalization test

### Commands
- `./setup.sh`
- `python -m unittest discover -s tests -v`

### If touching CLI
- `svwb-collect --help` を壊さない

### If touching workflow
- Job Summary に以下を出す
  - result
  - run_status
  - source_url
  - discovered card count
  - fetched detail count
  - saved item count
  - warnings
  - blocked source
  - generated files

---

## Git / Artifact Policy
- SQLite, JSON, latest_summary.md は **artifact で確認する**
- 実行生成物は Git にコミットしない
- `.gitignore` を守る
- PR にバイナリを含めない

---

## README Policy
README には常に以下を反映すること。

- 現在の official_cards の方式
- 正式な source_url
- blocked 扱いのURL
- 実行方法
- manual workflow の確認方法
- Summary の見方
- 既知の制約
- 暫定状態ならその旨

README が理想を書くだけで、実装が追いついていない状態を作らないこと。

---

## Reporting Format
作業完了時は必ず以下の形式で報告すること。

- 検証結果: pass / partial / fail
- 今回触った対象
- source_url
- discovered card count
- fetched detail count
- saved item count
- blocked の有無
- warnings の要点
- 変更したファイル
- 残っている制約
- 次に svoc へ進めてよいかどうか

---

## Decision Rules
### If official_cards is still partial
次にやるべきことは official_cards の改善であり、svoc へ進まない。

### If official_cards becomes pass
次は svoc を **official_cards と同じ最小方針** で進める。

### If Summary says SUCCESS but saved count is suspiciously low
見かけ上の success でも、実質 partial として扱う。

---

## Definition of Done for the current phase
現フェーズの完了条件は次の通り。

- official_cards が external reachable environment で安定実行できる
- 件数が妥当
- 詳細ページ由来の項目が保存される
- Actions Summary だけで一次判定できる
- README と workflow と実装が整合している

この条件を満たすまでは、official_cards フェーズは未完了とみなす。
