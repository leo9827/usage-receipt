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
3. Leaves Codex receipt printing to your shell wrapper; this repo does not install a Codex hook.

If `~/.local/bin` is not on `PATH`, setup adds a small managed block to your shell rc file for new shells.

Useful options:

```bash
./setup.sh --dry-run
./setup.sh --force
./setup.sh --bin-dir /usr/local/bin
./setup.sh --skip-claude
./setup.sh --skip-command
```

## Use

```bash
usage-receipt claude
usage-receipt codex
usage-receipt claude --list
usage-receipt codex --date today
usage-receipt claude --last 7d
```

The Claude Code hook runs when the session ends. On shells with the wrapper in this dotfiles repo, Codex prints a receipt after the CLI exits.

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

Claude Code passes hook input as JSON on stdin. The hook script reads the transcript path when available, falls back to the session id, asks `usage-receipt` to render that local session, and writes the output to the terminal.

For Codex, the exit-time receipt is printed by the `codex()` shell wrapper in this dotfiles repo, not by a Codex lifecycle hook.

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

References: Claude Code hooks are configured in `~/.claude/settings.json`. Codex exit receipts are handled by the shell wrapper in `~/.zshrc`, not by a Codex lifecycle hook.
