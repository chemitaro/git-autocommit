# git-autocommit

ステージ済みの差分（`git diff --cached`）だけをもとに、高速で安価なモデルで Conventional Commits 形式のコミットメッセージを生成し、コミットまで行う CLI です。

高性能なモデルで作業中のエージェントがコミットメッセージを自分で書くと、コスト・時間・コンテキストを消費します。このツールを実行するだけでコミットが完了する状態を目指します。

- `git add` は行いません。コミット対象は事前にステージしてください。
- 使用するプロバイダー（Codex / Claude など）、モデル、推論レベルは設定ファイルで第一優先・第二優先の2つを定義します。

## 導入

```bash
uv tool install -e ~/workspace/tools/git-autocommit   # ~/.local/bin/git-autocommit
mkdir -p ~/.config/git-autocommit
cp config.example.toml ~/.config/git-autocommit/config.toml   # 任意（なければ既定値）
```

前提: `codex login` 済みの Codex CLI と、ログイン済みの Claude Code CLI（使うプロバイダーのみ）。

## 使い方

```bash
git add <paths>
git-autocommit             # メッセージ生成 → そのままコミット（git autocommit でも可）
git-autocommit --confirm   # 生成後に y/N で確認してからコミット
git-autocommit --dry-run   # メッセージを表示するだけでコミットしない
```

- 生成したメッセージは stdout、進捗とエラーは stderr に出ます。
- primary が理由を問わず失敗したら secondary で再試行します。両方失敗したらコミットせず終了コード 1 で終わります。
- `git commit` はフック有効のまま実行します（`--no-verify` はありません）。
- 子プロセスには `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` を渡さず、サブスクリプション認証で動かします。
- Codex / Claude Code のユーザーフック（通知音、Telegram 通知、Orca 連携など）は呼び出しごとに無効化します（`-c features.hooks=false` / `--settings '{"disableAllHooks": true}'`）。設定ファイルは書き換えないため、通常の対話利用には影響しません。生成はツールを使わないテキスト出力のみで、Codex は読み取り専用サンドボックスでも制限されるため、安全チェック用のフックは不要と判断しています。Git のフック（pre-commit など）は無効化しません。
- ステージ済み差分が `max_diff_bytes`（既定 250000 バイト）を超えると、全文の代わりにファイル一覧・統計・各ファイルの抜粋を渡します。

## 設定

`~/.config/git-autocommit/config.toml`（例: `config.example.toml`）

| キー | 既定値 | 内容 |
|---|---|---|
| `[primary]` | `codex` / `gpt-6-luna` / `low` | `provider`（`codex` / `claude`）、`model`、`reasoning_effort` |
| `[secondary]` | `claude` / `claude-haiku-5-5` / `low` | 同上 |
| `[identity]` | なし | `name` / `email`。設定時のみ author/committer を検証し、不一致ならコミットを拒否 |
| `language` | `日本語` | 件名・本文の言語 |
| `max_diff_bytes` | `250000` | 差分全文を渡す上限 |

## 終了コード

| コード | 意味 |
|---|---|
| 0 | コミット成功、`--dry-run` 成功、または `--confirm` で中止 |
| 1 | Git リポジトリ外、ステージなし、身元不一致、生成失敗、TTY なしで `--confirm` |
| 2 | 設定ファイルまたは引数が不正 |
| その他 | `git commit` の終了コード（フック失敗など） |

## 構成

```text
git-autocommit/
├── pyproject.toml        # パッケージ定義・ruff / mypy / pytest 設定
├── config.example.toml   # 設定ファイルの例
├── docs/design.md        # 合意済みの設計メモ
├── src/git_autocommit/   # 実装コード
└── tests/                # テストコード
```

## 開発

```bash
uv sync                  # 開発環境の構築
uv run pytest            # テスト
uv run ruff check .      # Lint
uv run ruff format .     # 整形
uv run mypy              # 型チェック
uv run git-autocommit    # ローカル実行
```
