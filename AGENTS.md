# AGENTS.md

## Project
svwb-data-collector

## Purpose
Shadowverse: Worlds Beyond のカード情報について、公式詳細ページをもとに全件再取得し、  
**ChatGPT 5.4 Thinking がハルシネーションを起こしにくい一次資料**を生成する。

このプロジェクトの目的は、常時監視ツールを作ることではない。  
**新弾追加時・エラッタ時に手動実行し、信頼できるカード資料一式を再生成すること**を目的とする。

---

## Top Priority
1. `card_id` 入力ベースの `official_cards` 再生成ツールを成立させる
2. 正本JSONを安定生成できるようにする
3. 分析補助JSONの枠組みを生成できるようにする
4. LLM参照用Markdownを生成できるようにする
5. 差分レポートを確認用として生成できるようにする
6. その後に必要なら分析補助層の詳細を拡張する

---

## Hard Rules
- **一覧 discovery はやらない**
- **portal / WB cardslist / robots 回避前提の source investigation を今は進めない**
- **入力は手動の card_id 一覧または詳細URL一覧に限定する**
- **更新は手動実行のみ。定期実行は不要**
- **毎回全件再取得して全出力を再生成する**
- **差分は更新本体ではなく確認用出力としてのみ扱う**
- **related cards は単一の `related_card_ids` のみ保持する**
- **関連の意味づけは正本ではやらない**
- **分析値を正本JSONに混ぜない**
- **LLM参照用MDは人間可読性より ChatGPT 5.4 Thinking の参照効率を優先する**
- **svoc / rage / unofficial / decklist / 環境分析には進まない**
- **Playwright は入れない**
- **差分は常に最小に保つ**
- **README と実装がずれたら、README か実装のどちらかを必ず修正する**
- **生成物は Git 管理しない**

---

## Current State Policy
このフェーズでは `official_cards` を **manual card_id mode** で実装する。

### official_cards の原則
- 入力は `card_id` 一覧ファイル
- 一覧ページの自動収集はしない
- 詳細ページURLは `card_id` から正規構築する
- 1カード = 1レコードで正本JSONを生成する
- 正本JSONから分析補助JSONを生成する
- 正本JSON + 分析補助JSON から LLM参照用MDを生成する
- 前回snapshotがあれば差分レポートを生成する

### 詳細URL
詳細ページURLは次を正規形とする。

`https://shadowverse-wb.com/ja/deck/cardslist/card/?card_id={card_id}`

今回のフェーズでは、この形式の直取得だけを対象とする。

---

## Input Policy
入力は最初は YAML を前提とする。

### 想定入力例
```yaml
snapshot_id: 2026-03-12
update_type: new_release
card_ids:
  - "10551120"
  - "10551121"
  - "10551122"
```

### Required fields
- `snapshot_id`
- `update_type`
- `card_ids`

### update_type
- `new_release`
- `errata`

`update_type` は差分レポートや記録用メタ情報に使う。  
取得処理自体はどちらも **全件再生成** で統一する。

---

## Output Policy
生成対象は以下の4つに固定する。

1. `cards_snapshot_latest.json`
2. `cards_features_latest.json`
3. `cards_reference_latest.md`
4. `cards_diff_latest.md`

### 1. cards_snapshot_latest.json
役割:
- 一次情報の正本
- 正誤確認の基準
- 差分比較の基準

### 2. cards_features_latest.json
役割:
- 正本から自動生成する分析補助レイヤー
- 後から項目追加できる拡張用出力

### 3. cards_reference_latest.md
役割:
- ChatGPT 5.4 Thinking が低負荷で参照するための整形済みビュー
- 人間向け読みやすさは優先しない
- 正本JSON + 分析補助JSON から生成する

### 4. cards_diff_latest.md
役割:
- 前回版との差分確認
- 更新の本体ではなく確認用

---

## Canonical JSON Schema Policy
正本JSONの1カード分スキーマは、最低限以下を守る。

```json
{
  "card_id": "10551120",
  "name": "カード名",
  "class": "エルフ",
  "cost": 3,
  "rarity": "ゴールド",
  "kind": "フォロワー",
  "types": ["学園"],
  "stats": {
    "attack": 2,
    "defense": 3
  },
  "effect": "能力テキスト全文",
  "pack": "第1弾",
  "is_token": false,
  "related_card_ids": [],
  "source_url": "https://shadowverse-wb.com/ja/deck/cardslist/card/?card_id=10551120",
  "fetched_at": "2026-03-12T12:34:56Z",
  "source_hash": "sha256:..."
}
```

### JSON rules
- `card_id` は string
- `cost` は integer
- `types` は array[string]、無ければ `[]`
- `stats` は常に object を持つ
- `stats.attack` / `stats.defense` は取れない場合 `null`
- `related_card_ids` は array[string]、無ければ `[]`
- `related_card_ids` は公式詳細ページに載る関連カードIDのみ
- `source_url` / `fetched_at` / `source_hash` は必須
- 正本には分析値を入れない

---

## Related Card Policy
関連カードは単一フィールドで扱う。

### Keep
- `related_card_ids`

### Do not do
- creates / references / related の分類
- 関連意味の推論
- 独自の関係付け

必要なら関連の意味づけは後で分析補助層に追加する。

---

## Feature Layer Policy
分析補助層は正本とは分離した別出力とする。

### Role
- 正本から自動生成する補助情報
- 構築議論やリソース議論に使うための土台
- 後から項目追加できるようにする

### Current phase requirement
- 枠組みだけ実装する
- 今回は詳細ロジックを作り込まない
- 最低限 `analysis.status` を持てばよい
- 後から `hand_delta_self` などを追加しやすい構造にする

### Minimum example
```json
{
  "card_id": "10551120",
  "analysis": {
    "status": "pending"
  }
}
```

### Allowed status
- `pending`
- `ready`
- `error`

---

## LLM Reference Markdown Policy
`cards_reference_latest.md` は人間向け資料ではなく、  
**ChatGPT 5.4 Thinking の参照効率を優先した生成物**とする。

### Format rules
- 1カード1ブロック
- 項目順固定
- `fact` と `analysis` を分ける
- YAMLライクな固定構造
- キー短縮は今はやらない
- 自然文の説明は増やさない
- 省略よりも構造安定を優先する

### Minimum template
```md
## card:{card_id}
fact:
  card_id: "{card_id}"
  name: "{name}"
  class: "{class}"
  cost: {cost}
  rarity: "{rarity}"
  kind: "{kind}"
  types: [{types}]
  stats:
    attack: {attack_or_null}
    defense: {defense_or_null}
  effect: "{effect}"
  pack: "{pack}"
  is_token: {true_or_false}
  related_card_ids: [{related_card_ids}]
  source_url: "{source_url}"
  fetched_at: "{fetched_at}"
  source_hash: "{source_hash}"

analysis:
  status: "{pending_or_ready_or_error}"
```

---

## Diff Policy
差分は更新のためではなく確認のためだけに出す。

### Rules
- 旧 `cards_snapshot_latest.json` が存在する場合のみ比較する
- 最低限、以下を出せればよい
  - `added card_ids`
  - `changed card_ids`
  - `removed card_ids`
- `new_release` / `errata` はヘッダやメタ情報に使うだけでよい
- 差分更新ロジックは作らない

---

## Execution Policy
### Mode
- 手動CLI実行のみ
- scheduler や定期実行は不要

### Requirements
- 入力ファイルパスを指定できる
- 出力先を指定できる
- 全件再生成できる
- 失敗した `card_id` 一覧を最後に出せる

### Error handling
- 1件失敗しても可能な限り全体継続
- 失敗した `card_id` と `source_url` が分かる
- 成功件数 / 失敗件数が最後に分かる

---

## Testing Rules
修正時は最低限以下を維持または追加すること。

### Required
- 入力ファイルを読んで詳細URLを構築するテスト
- 詳細ページ fixture から正本JSONレコードを作るテスト
- 分析補助JSONの最低限出力テスト
- `cards_reference_latest.md` の1カード分生成テスト
- 旧snapshotありで diff を生成する最低限テスト
- 既存 smoke test

### Commands
- `./setup.sh`
- `python -m unittest discover -s tests -v`
- `svwb-collect --help`

---

## Git / Artifact Policy
- 正本JSON / 分析補助JSON / 参照MD / diff は生成物
- 生成物は Git にコミットしない
- `.gitignore` を守る
- PR にバイナリを含めない

---

## README Policy
README には常に以下を反映すること。

- このツールは manual card_id mode であること
- 一覧 discovery はこのフェーズではやらないこと
- 入力ファイル形式
- 4出力の役割
- 手動実行方法
- 失敗時の確認方法
- 既知の制約

README が理想を書くだけで、実装が追いついていない状態を作らないこと。

---

## Reporting Format
作業完了時は必ず以下の形式で報告すること。

- verdict: pass / partial / fail
- 今回触った対象
- input file format
- generated files
- success_count
- failed_card_ids
- changed_files
- summary
- next_step
- can_move_to_svoc

---

## Handoff File Policy
毎回の作業完了時に、ChatGPT へ状態を引き継ぐための handoff ファイルを必ず更新すること。

### Required outputs
- `reports/assistant_handoff.md`
- `reports/assistant_handoff.json`

### Minimum fields
- `task`
- `verdict`
- `input_mode`
- `generated_files`
- `success_count`
- `failed_card_ids`
- `changed_files`
- `summary`
- `next_step`
- `can_move_to_svoc`

### Rule
- handoff の内容は最終報告と一致させる
- 実装変更がなくても、調査だけしたら最新状態で更新する
- 古い状態を残さず上書きする

---

## Scope Exclusions
現段階ではやらないこと:

- 一覧 discovery
- portal 調査
- source investigation の継続
- svoc
- rage
- unofficial source
- decklist
- 環境分析
- マッチアップ分析
- 分析補助層の詳細完成
- LLM参照用MDの圧縮最適化
- キー短縮

---

## Decision Rules
### If manual card_id pipeline is not complete
次にやるべきことは、この pipeline の完成であり、他テーマに進まない。

### If this pipeline becomes pass
次は分析補助層の中身を詰めるか、入力運用を整備する。

### If implementation drifts toward discovery
今回の範囲外なので止める。

---

## Definition of Done for the current phase
現フェーズの完了条件は次の通り。

- `card_id` 一覧ファイルを入力できる
- 各 `card_id` から正規詳細URLを構築できる
- 詳細ページから正本JSONを生成できる
- 分析補助JSONを生成できる
- LLM参照用MDを生成できる
- 前回版があれば差分レポートを生成できる
- 失敗した `card_id` 一覧を出せる
- README と実装が整合している

この条件を満たすまでは、現フェーズは未完了とみなす。
