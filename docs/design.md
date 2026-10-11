# git-autocommit 設計メモ

2026-10-11 のインタビューで合意した仕様です。元の実装は `~/workspace/tools/scripts/commit-codex`（Bash）です。

## 目的

高性能で高価なモデルで作業中のエージェントが、コミットメッセージ生成を高速・安価なモデルへ委譲し、コマンド1回でコミットを完了できるようにする。

## 動作

- 入力はステージ済み差分（`git diff --cached`）のみ。`git add` はしない。ステージ済み差分が空なら終了する。
- 既定は確認なしでコミットまで行う。`--confirm` で Y/N 確認する（TTY がなければ中止）。
- メッセージ生成だけ行いコミットしないオプションを用意する（スキルのメッセージ生成用途）。
- `git commit` は本物の git CLI を `subprocess`（`shell=False`）で呼び、フックを迂回しない。`--no-verify` は提供しない。

## 設定

- 配置先は `~/.config/git-autocommit/config.toml` のみ（リポジトリ別設定・環境変数による上書きはしない）。
- 例は `config.example.toml`。設定ファイルがない場合は既定値を使う。

| キー | 内容 |
|---|---|
| `[primary]` / `[secondary]` | `provider`（`codex` / `claude`）、`model`、`reasoning_effort` |
| `[identity]`（任意） | `name` / `email`。設定時のみ author/committer を検証し、不一致ならコミットを拒否 |
| `language`（任意） | メッセージ本文の言語。既定は日本語 |

既定値（最安・最速優先。どちらの CLI も `low` が最小の推論レベル）:

- primary: `codex` / `gpt-6-luna` / `low`
- secondary: `claude` / `claude-haiku-5-5` / `low`

## プロバイダー

- codex: `codex exec --model <m> --config model_reasoning_effort="<e>" --sandbox read-only -`
- claude: `claude -p --model <m> --effort <e>`（ツールは使わせない）
- 子プロセスには `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` を渡さず、サブスクリプション認証で動かす。
- 両 CLI のユーザーフックは呼び出しごとに無効化する（codex: `--config features.hooks=false`、claude: `--settings '{"disableAllHooks": true}'`）。通知音・Telegram 通知・Orca 連携が1回ごとに動き、所要時間がほぼ倍になっていたため（2026-10-11 実測）。
- primary が失敗したら（異常終了・未ログイン・タイムアウト・空出力など理由を問わず）secondary で再試行する。

## メッセージ形式

Conventional Commits。type は英語、件名と箇条書きの本文は `language` の言語。

## 大きな差分

上限以内なら差分全体を渡す。超えたら `--stat` / `--name-status` と各ファイルの抜粋を渡す。エージェントに自分で読ませる方式は採用しない。設定項目は最小限にする。

## 導入と移行

- `uv tool install -e .` で `~/.local/bin/git-autocommit` に導入する。
- 動作確認後、スキル `git-commit` を `git-autocommit` 前提に書き換え、`/usr/local/bin/commit-codex` のリンクを外す。

2026-10-11 に移行済み: スキル `git-commit`（`~/.agents`）と Codex の実行許可ルール（`~/.codex/rules/user.rules`）を `git-autocommit` に切り替え、`commit-codex` のリンクを削除した。スクリプト本体 `~/workspace/tools/scripts/commit-codex` は残している。
