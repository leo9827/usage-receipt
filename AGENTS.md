# Agent Notes

This repository installs a local token usage receipt tool for Claude Code and Codex.

When a user asks you to install it on their machine, use the setup script instead of hand-editing config:

```bash
git clone git@github.com:leo9827/usage-receipt.git
cd usage-receipt
./setup.sh
```

The setup script:

- creates a `usage-receipt` symlink in `~/.local/bin`;
- installs a Claude Code `SessionEnd` hook in `~/.claude/settings.json`;
- leaves Codex exit receipts to the shell wrapper in this dotfiles repo.

Use `./setup.sh --dry-run` to inspect changes before writing. Use `./setup.sh --force` only when replacing an existing `usage-receipt` command is intended. This tool installs the receipt command and the Claude Code hook; Codex receipts are handled by the shell wrapper in the dotfiles repo.

After install, verify with:

```bash
usage-receipt --help
usage-receipt claude --list
```
