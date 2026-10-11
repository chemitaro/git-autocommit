# git-autocommit

[English](README.en.md) | 日本語

ステージ済みの差分（`git diff --cached`）から、高速で安価なモデルで [Conventional Commits](https://www.conventionalcommits.org/) 形式のコミットメッセージを生成し、そのままコミットまで行う CLI です。モデルは [Codex CLI](https://github.com/openai/codex) または [Claude Code](https://github.com/anthropics/claude-code) 経由で呼び出します。

## なぜ必要か

高性能なモデルで作業中のコーディングエージェントにコミットメッセージを書かせると、メッセージ1つのためにコスト・時間・コンテキストを消費します。`git-autocommit` はこの作業を安価なモデルへ委譲し、エージェントは `git add` のあとにコマンドを1回実行するだけでコミットを完了できます。

```console
$ git add src/calc.py
$ git-autocommit
Generating a commit message with primary: codex / gpt-6-luna (low)...
feat: 加算関数を追加

- 2つの値を加算する add 関数を追加
[main 7f8a3e3] feat: 加算関数を追加
 1 file changed, 2 insertions(+)
```

## 特徴

- **第一優先・第二優先の2段構え**: primary が理由を問わず失敗したら secondary で再試行します（例: Codex → Claude）。
- **フックを迂回しない**: 本物の `git commit` を実行し、pre-commit などの Git フックは有効なままです。`--no-verify` はありません。
- **`git add` はしない**: コミット対象は呼び出し側が明示的にステージします。
- **サブスクリプション認証で動作**: 子プロセスには `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` を渡さないため、API の従量課金ではなく各 CLI のログイン（ChatGPT / Claude のサブスクリプション）を使います。
- **大きな差分に対応**: 上限を超える差分は、ファイル一覧・統計・各ファイルの抜粋に要約して渡します。
- **外部ライブラリなし**: Python 標準ライブラリのみで動作します。

## ⚠️ 送信されるデータ

ステージ済み差分の内容（大きい場合は抜粋）は、設定したプロバイダーの CLI を通じて **OpenAI または Anthropic に送信されます**。秘密情報や送信できないコードがステージされていないことを確認してから実行してください。データの扱いは各サービスの規約に従います。

## 必要なもの

- Git
- Python 3.11 以上と [uv](https://docs.astral.sh/uv/)
- 使うプロバイダーの CLI（ログイン済み）
  - `codex`: `codex login` 済みの [Codex CLI](https://github.com/openai/codex)
  - `claude`: ログイン済みの [Claude Code](https://github.com/anthropics/claude-code)

動作確認環境: macOS、Git 2.54.0、Python 3.12.6、codex-cli 0.162.1、Claude Code 2.1.296。Linux でも動作する想定ですが未検証です。Windows は対象外です。

## 導入

```bash
git clone https://github.com/chemitaro/git-autocommit.git
cd git-autocommit
uv tool install -e .     # ~/.local/bin/git-autocommit に導入
mkdir -p ~/.config/git-autocommit
cp config.example.toml ~/.config/git-autocommit/config.toml   # 任意（なければ既定値）
```

`git-autocommit` という名前で PATH に入るため、`git autocommit` としても実行できます。PyPI には公開していません。

- 更新: `git pull`（`-e` で導入しているため、再インストールは不要です）
- 削除: `uv tool uninstall git-autocommit`

## 使い方

```bash
git add <paths>
git-autocommit             # メッセージを生成して、そのままコミット
git-autocommit --confirm   # 生成後に y/N で確認してからコミット
git-autocommit --dry-run   # メッセージを表示するだけでコミットしない
```

- 生成したメッセージは stdout、進捗とエラーは stderr に出ます。
- 両方のプロバイダーが失敗した場合はコミットせず、終了コード 1 で終わります。
- `--confirm` は端末（TTY）が必要です。TTY がない場合はモデルを呼ばずに中止します。

### コーディングエージェントから使う

`CLAUDE.md` や `AGENTS.md` に次のような指示を書くと、エージェントは自分でメッセージを書かずにこのツールへ委譲します。

```markdown
## コミット
- 対象ファイルを `git add -- <paths>` で明示的にステージしてから `git-autocommit` を実行する。
- コミットメッセージは自分で書かない。`git-autocommit` が失敗したら、その出力を報告して止まる。
```

## 設定

`~/.config/git-autocommit/config.toml`（例: [`config.example.toml`](config.example.toml)）。ファイルがなければ既定値を使います。

```toml
[primary]
provider = "codex"
model = "gpt-6-luna"
reasoning_effort = "low"

[secondary]
provider = "claude"
model = "claude-haiku-5-5"
reasoning_effort = "low"
```

| キー | 既定値 | 内容 |
|---|---|---|
| `[primary]` | `codex` / `gpt-6-luna` / `low` | `provider`（`codex` / `claude`）、`model`、`reasoning_effort` |
| `[secondary]` | `claude` / `claude-haiku-5-5` / `low` | 同上 |
| `[identity]` | なし | `name` / `email`。設定した場合だけ author / committer を検証し、一致しなければコミットを拒否します |
| `language` | `日本語` | 件名と本文の言語（type は常に英語） |
| `max_diff_bytes` | `250000` | 差分の全文を渡す上限（バイト）。超えると要約に切り替えます |

- 利用できるモデル名や `reasoning_effort` の値は、各 CLI のバージョンとアカウントによって異なります。既定のモデルが使えない場合は設定で変更してください。
- 各呼び出しのタイムアウトは 180 秒です。

## 仕組み

1. ステージ済み差分を取得します（なければ終了）。
2. 差分（または要約）とメッセージ形式の指示をプロンプトにまとめます。
3. プロバイダーの CLI を、リポジトリ外の一時ディレクトリから非対話モードで実行します。
   - Codex: `codex exec --sandbox read-only --ephemeral ...`
   - Claude Code: `claude -p --tools "" --no-session-persistence ...`
4. 出力を整形し、`git commit -F -` でコミットします。

呼び出しのたびに、各 CLI のユーザーフック（通知や外部連携など）を無効化します（Codex: `-c features.hooks=false`、Claude Code: `--settings '{"disableAllHooks": true}'`）。フックがあると1回ごとに通知などの副作用が起き、所要時間もほぼ倍になるためです。この上書きはその呼び出しの間だけで、設定ファイルは変更しません。生成はツールを使わずテキストを返すだけなので、安全チェック用のフックがなくても問題ないと判断しています。Git のフックは無効化しません。

## 終了コード

| コード | 意味 |
|---|---|
| 0 | コミット成功、`--dry-run` 成功、または `--confirm` で中止 |
| 1 | Git リポジトリ外、ステージなし、身元不一致、生成失敗、TTY なしで `--confirm` |
| 2 | 設定ファイルまたは引数が不正 |
| その他 | `git commit` の終了コード（フック失敗など） |

## 制限事項

- 安価なモデルを使うため、差分の誤読などメッセージの精度には限界があります。重要なコミットは `--confirm` や `--dry-run` で確認してください。
- 生成されるメッセージの形式（件名1行と、箇条書き最大3行の本文）は固定です。

## 開発

```text
git-autocommit/
├── pyproject.toml        # パッケージ定義・ruff / mypy / pytest の設定
├── config.example.toml   # 設定ファイルの例
├── docs/design.md        # 設計メモ（作者の環境での経緯を含む）
├── src/git_autocommit/   # 実装
└── tests/                # テスト（偽の codex / claude を使い、モデルは呼びません）
```

```bash
uv sync                  # 開発環境の構築
uv run pytest            # テスト
uv run ruff check .      # Lint
uv run ruff format .     # 整形
uv run mypy              # 型チェック
uv run git-autocommit    # ローカル実行
```

Issue や Pull Request は歓迎します。

## ライセンス

[The Unlicense](LICENSE)（パブリックドメイン）。無保証で提供します。
