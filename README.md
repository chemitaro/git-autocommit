# git-autocommit

ステージ済みの差分（`git diff --cached`）だけをもとに、高速で安価なモデルで Conventional Commits 形式のコミットメッセージを生成し、コミットまで行う CLI です。

高性能なモデルで作業中のエージェントがコミットメッセージを自分で書くと、コスト・時間・コンテキストを消費します。このツールを実行するだけでコミットが完了する状態を目指します。

- `git add` は行いません。コミット対象は事前にステージしてください。
- 使用するプロバイダー（Codex / Claude など）、モデル、推論レベルは設定ファイルで第一優先・第二優先の2つを定義します。

> 開発中です。元の実装は `~/workspace/tools/scripts/commit-codex` です。

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
