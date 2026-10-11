# git-autocommit

English | [日本語](README.md)

A CLI that generates a [Conventional Commits](https://www.conventionalcommits.org/) message from your staged diff (`git diff --cached`) with a fast, low-cost model and commits it. Models are called through the [Codex CLI](https://github.com/openai/codex) or [Claude Code](https://github.com/anthropics/claude-code).

## Why

When a coding agent running on an expensive, high-end model writes its own commit messages, every message costs money, time, and context. `git-autocommit` delegates that job to a cheap model, so the agent only has to run one command after `git add`.

```console
$ git add src/calc.py
$ git-autocommit
Generating a commit message with primary: codex / gpt-6-luna (low)...
feat: add an addition function

- Add an add function that sums two values
[main 7f8a3e3] feat: add an addition function
 1 file changed, 2 insertions(+)
```

## Features

- **Primary and secondary models**: if the primary fails for any reason, the secondary is tried (e.g. Codex → Claude).
- **Never bypasses hooks**: runs the real `git commit` with Git hooks such as pre-commit enabled. There is no `--no-verify`.
- **No `git add`**: the caller stages exactly what should be committed.
- **Runs on your subscription**: `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` are not passed to the child process, so each CLI uses its logged-in ChatGPT / Claude subscription instead of metered API billing.
- **Handles large diffs**: diffs over the limit are summarized as a file list, stats, and per-file excerpts.
- **No dependencies**: uses only the Python standard library.

## ⚠️ Data sent to providers

The staged diff (or excerpts of it, for large diffs) is **sent to OpenAI or Anthropic** through the configured provider's CLI. Make sure no secrets or code you cannot share are staged. Data handling follows each service's terms.

## Requirements

- Git
- Python 3.11+ and [uv](https://docs.astral.sh/uv/)
- The CLI for each provider you use, logged in
  - `codex`: [Codex CLI](https://github.com/openai/codex) after `codex login`
  - `claude`: [Claude Code](https://github.com/anthropics/claude-code)

Tested on macOS with Git 2.54.0, Python 3.12.6, codex-cli 0.162.1, and Claude Code 2.1.296. Linux is expected to work but untested. Windows is not supported.

## Installation

```bash
git clone https://github.com/chemitaro/git-autocommit.git
cd git-autocommit
uv tool install -e .     # installs ~/.local/bin/git-autocommit
mkdir -p ~/.config/git-autocommit
cp config.example.toml ~/.config/git-autocommit/config.toml   # optional; defaults apply without it
```

Because the executable is named `git-autocommit`, you can also run it as `git autocommit`. It is not published on PyPI.

- Update: `git pull` (no reinstall needed with `-e`)
- Uninstall: `uv tool uninstall git-autocommit`

## Usage

```bash
git add <paths>
git-autocommit             # generate a message and commit
git-autocommit --confirm   # ask y/N before committing
git-autocommit --dry-run   # print the message only; do not commit
```

- The generated message goes to stdout; progress and errors go to stderr.
- If both providers fail, nothing is committed and the exit code is 1.
- `--confirm` needs a terminal (TTY). Without one it aborts before calling any model.

### Using it from coding agents

Add instructions like these to `CLAUDE.md` or `AGENTS.md` so the agent delegates instead of writing messages itself:

```markdown
## Commits
- Stage files explicitly with `git add -- <paths>`, then run `git-autocommit`.
- Do not write commit messages yourself. If `git-autocommit` fails, report its output and stop.
```

## Configuration

`~/.config/git-autocommit/config.toml` (see [`config.example.toml`](config.example.toml)). Defaults apply when the file does not exist.

```toml
language = "English"

[primary]
provider = "codex"
model = "gpt-6-luna"
reasoning_effort = "low"

[secondary]
provider = "claude"
model = "claude-haiku-5-5"
reasoning_effort = "low"
```

| Key | Default | Description |
|---|---|---|
| `[primary]` | `codex` / `gpt-6-luna` / `low` | `provider` (`codex` / `claude`), `model`, `reasoning_effort` |
| `[secondary]` | `claude` / `claude-haiku-5-5` / `low` | Same as above |
| `[identity]` | none | `name` / `email`. When set, the author / committer must match or the commit is refused |
| `language` | `日本語` (Japanese) | Language of the subject and body (the type is always English). Set `"English"` for English messages |
| `max_diff_bytes` | `250000` | Maximum diff size (bytes) sent in full; larger diffs are summarized |

- Available model names and `reasoning_effort` values depend on each CLI version and your account. Change them if the defaults are unavailable.
- Each provider call times out after 180 seconds.

## How it works

1. Read the staged diff (exit if empty).
2. Build a prompt from the diff (or its summary) and the message-format instructions.
3. Run the provider CLI non-interactively from a temporary directory outside the repository.
   - Codex: `codex exec --sandbox read-only --ephemeral ...`
   - Claude Code: `claude -p --tools "" --no-session-persistence ...`
4. Clean up the output and commit with `git commit -F -`.

Each call disables the CLI's user hooks (notifications, integrations, and so on) with `-c features.hooks=false` for Codex and `--settings '{"disableAllHooks": true}'` for Claude Code. Those hooks caused side effects on every call and roughly doubled the run time. The override applies only to that call; config files are not modified. Generation returns text without using tools, so safety-check hooks are not needed. Git hooks are never disabled.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Committed, `--dry-run` succeeded, or aborted at `--confirm` |
| 1 | Not in a Git repository, nothing staged, identity mismatch, generation failed, or `--confirm` without a TTY |
| 2 | Invalid config file or arguments |
| other | Exit code of `git commit` (e.g. a failing hook) |

## Limitations

- Cheap models can misread diffs, so message quality has limits. Use `--confirm` or `--dry-run` for important commits.
- The message format (a one-line subject and an optional body of up to three bullets) is fixed.

## Development

```text
git-autocommit/
├── pyproject.toml        # packaging and ruff / mypy / pytest settings
├── config.example.toml   # example config file
├── docs/design.md        # design notes in Japanese (includes the author's local setup history)
├── src/git_autocommit/   # implementation
└── tests/                # tests (use fake codex / claude; no models are called)
```

```bash
uv sync                  # set up the dev environment
uv run pytest            # tests
uv run ruff check .      # lint
uv run ruff format .     # format
uv run mypy              # type check
uv run git-autocommit    # run locally
```

Issues and pull requests are welcome.

## License

[The Unlicense](LICENSE) (public domain). Provided without warranty.
