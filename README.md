# usage-receipt

Print a small receipt for Claude Code or Codex token usage, including estimated API cost when the model price is known.

## Install

```bash
git clone git@github.com:leo9827/usage-receipt.git
cd usage-receipt
./setup.sh
```

The setup script does three things:

1. Creates a `usage-receipt` command symlink in `~/.local/bin`.
2. Adds a Claude Code `SessionEnd` hook in `~/.claude/settings.json`.
3. Enables Codex hooks and adds a Codex `SessionEnd` hook in `~/.codex/config.toml` and `~/.codex/hooks.json`.

If `~/.local/bin` is not on `PATH`, setup adds a small managed block to your shell rc file for new shells.

Useful options:

```bash
./setup.sh --dry-run
./setup.sh --force
./setup.sh --bin-dir /usr/local/bin
./setup.sh --skip-claude
./setup.sh --skip-codex
./setup.sh --skip-command
./setup.sh --codex-event Stop
```

## Use

```bash
usage-receipt claude
usage-receipt codex
usage-receipt claude --list
usage-receipt codex --date today
usage-receipt claude --last 7d
```

The default hooks run when the Claude Code or Codex session ends, then print one receipt for that session.

## Manual Setup

If you do not want to run `setup.sh`, create the command link yourself:

```bash
mkdir -p ~/.local/bin
ln -sf "$PWD/usage-receipt" ~/.local/bin/usage-receipt
```

Claude Code user settings:

```json
{
  "hooks": {
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "'/absolute/path/to/usage-receipt/session-end-hook.sh' claude",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

Codex needs hooks enabled in `~/.codex/config.toml`:

```toml
[features]
codex_hooks = true
```

Then add `~/.codex/hooks.json`:

```json
{
  "hooks": {
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "'/absolute/path/to/usage-receipt/session-end-hook.sh' codex",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

Claude Code and Codex both pass hook input as JSON on stdin. The hook script reads the transcript path when available, falls back to the session id, asks `usage-receipt` to render that local session, and writes the output to the terminal.

## For Agents

When installing this repo for a user, prefer:

```bash
git clone git@github.com:leo9827/usage-receipt.git
cd usage-receipt
./setup.sh
usage-receipt --help
```

Do not hand-edit the user config unless `setup.sh` fails. Use `./setup.sh --dry-run` first when you need to inspect the intended changes.

## Notes

Pricing is an estimate based on `pricing.json`, not subscription billing. You can customize pricing with:

```bash
usage-receipt --setup
usage-receipt --update-pricing
```

References: Claude Code hooks are configured in `~/.claude/settings.json`, and Codex lifecycle hooks require `codex_hooks = true` in `config.toml`.
