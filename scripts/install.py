#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path


TOOL_NAME = "usage-receipt"
PATH_BLOCK_START = "# >>> usage-receipt setup >>>"
PATH_BLOCK_END = "# <<< usage-receipt setup <<<"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install usage-receipt command and Claude hook.")
    parser.add_argument("--repo-dir", default=str(Path(__file__).resolve().parents[1]), help=argparse.SUPPRESS)
    parser.add_argument("--bin-dir", help="Directory where the usage-receipt command symlink is created.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned changes without writing files.")
    parser.add_argument("--force", action="store_true", help="Replace an existing usage-receipt command symlink/file.")
    parser.add_argument("--skip-command", action="store_true", help="Do not create the global usage-receipt command.")
    parser.add_argument("--skip-claude", action="store_true", help="Do not install the Claude Code hook.")
    parser.add_argument("--claude-event", default="SessionEnd", help="Claude Code hook event to install.")
    parser.add_argument("--no-path-update", action="store_true", help="Do not edit shell rc files when bin dir is not on PATH.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_dir = Path(args.repo_dir).expanduser().resolve()
    installer = Installer(repo_dir=repo_dir, dry_run=args.dry_run, force=args.force)
    installer.install(
        bin_dir=Path(args.bin_dir).expanduser() if args.bin_dir else default_bin_dir(),
        install_command=not args.skip_command,
        install_claude=not args.skip_claude,
        claude_event=args.claude_event,
        update_path=not args.no_path_update,
    )
    return 0


class Installer:
    def __init__(self, repo_dir: Path, dry_run: bool, force: bool) -> None:
        self.repo_dir = repo_dir
        self.dry_run = dry_run
        self.force = force

    @property
    def cli_path(self) -> Path:
        return self.repo_dir / TOOL_NAME

    @property
    def hook_path(self) -> Path:
        return self.repo_dir / "session-end-hook.sh"

    def install(
        self,
        bin_dir: Path,
        install_command: bool,
        install_claude: bool,
        claude_event: str,
        update_path: bool,
    ) -> None:
        self.require_repo_file(self.cli_path)
        self.require_repo_file(self.hook_path)
        self.ensure_executable(self.cli_path)
        self.ensure_executable(self.hook_path)

        if install_command:
            self.install_command(bin_dir)
            self.ensure_bin_dir_on_path(bin_dir, update_path)
        if install_claude:
            self.install_claude_hook(claude_event)

        self.say("usage-receipt setup complete.")

    def install_command(self, bin_dir: Path) -> None:
        link_path = bin_dir / TOOL_NAME
        self.mkdir(bin_dir)

        if link_path.is_symlink() and link_path.resolve() == self.cli_path:
            self.say(f"Command already linked: {link_path} -> {self.cli_path}")
            return

        if link_path.exists() or link_path.is_symlink():
            if not self.force:
                raise SystemExit(
                    f"{link_path} already exists. Re-run with --force to replace it, "
                    "or use --bin-dir to choose another directory."
                )
            self.unlink(link_path)

        self.symlink(self.cli_path, link_path)
        self.say(f"Command linked: {link_path} -> {self.cli_path}")

    def install_claude_hook(self, event: str) -> None:
        settings_path = Path.home() / ".claude" / "settings.json"
        settings = self.load_json_object(settings_path)
        changed = add_event_hook(settings, event, hook_command(self.hook_path, "claude"))
        if changed:
            self.write_json(settings_path, settings)
            self.say(f"Claude {event} hook installed: {settings_path}")
        else:
            self.say(f"Claude {event} hook already installed: {settings_path}")

    def ensure_bin_dir_on_path(self, bin_dir: Path, update_path: bool) -> None:
        if path_contains(bin_dir):
            return
        if not update_path:
            self.say(f"PATH unchanged. Add this directory to PATH manually: {bin_dir}")
            return

        rc_path = shell_rc_path()
        block = path_block(bin_dir)
        existing = read_text_if_exists(rc_path)
        if PATH_BLOCK_START in existing:
            self.say(f"PATH block already present: {rc_path}")
            return
        suffix = "" if not existing or existing.endswith("\n") else "\n"
        self.write_text(rc_path, existing + suffix + block)
        self.say(f"PATH updated for new shells: {rc_path}")

    def require_repo_file(self, path: Path) -> None:
        if not path.exists():
            raise SystemExit(f"Required file is missing: {path}")

    def ensure_executable(self, path: Path) -> None:
        mode = path.stat().st_mode
        if mode & 0o111:
            return
        self.chmod(path, mode | 0o755)

    def load_json_object(self, path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path} is not valid JSON. Fix it first, then re-run setup. {exc}") from exc
        if not isinstance(data, dict):
            raise SystemExit(f"{path} must contain a JSON object.")
        return data

    def write_json(self, path: Path, data: dict) -> None:
        self.write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    def write_text(self, path: Path, content: str) -> None:
        self.mkdir(path.parent)
        if path.exists() and read_text_if_exists(path) == content:
            return
        self.backup(path)
        if self.dry_run:
            self.say(f"Would write: {path}")
            return
        path.write_text(content, encoding="utf-8")

    def backup(self, path: Path) -> None:
        if self.dry_run or not path.exists():
            return
        backup_path = path.with_name(path.name + ".usage-receipt.bak")
        if not backup_path.exists():
            shutil.copy2(path, backup_path)

    def mkdir(self, path: Path) -> None:
        if self.dry_run:
            self.say(f"Would create directory: {path}")
            return
        path.mkdir(parents=True, exist_ok=True)

    def chmod(self, path: Path, mode: int) -> None:
        if self.dry_run:
            self.say(f"Would make executable: {path}")
            return
        path.chmod(mode)

    def symlink(self, target: Path, link_path: Path) -> None:
        if self.dry_run:
            self.say(f"Would link: {link_path} -> {target}")
            return
        link_path.symlink_to(target)

    def unlink(self, path: Path) -> None:
        if self.dry_run:
            self.say(f"Would replace existing path: {path}")
            return
        path.unlink()

    def say(self, message: str) -> None:
        print(message)


def add_event_hook(settings: dict, event: str, command: str) -> bool:
    hooks = settings.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise SystemExit("Existing hooks value must be a JSON object.")

    event_groups = hooks.setdefault(event, [])
    if not isinstance(event_groups, list):
        raise SystemExit(f"Existing hooks.{event} value must be a JSON array.")

    for group in event_groups:
        if not isinstance(group, dict):
            continue
        for hook in group.get("hooks", []):
            if isinstance(hook, dict) and hook.get("command") == command:
                return False

    event_groups.append(
        {
            "hooks": [
                {
                    "type": "command",
                    "command": command,
                    "timeout": 30,
                }
            ]
        }
    )
    return True


def default_bin_dir() -> Path:
    env_dir = os.environ.get("USAGE_RECEIPT_BIN_DIR")
    if env_dir:
        return Path(env_dir).expanduser()
    return Path.home() / ".local" / "bin"


def path_contains(bin_dir: Path) -> bool:
    target = str(bin_dir.expanduser())
    return any(str(Path(item).expanduser()) == target for item in os.environ.get("PATH", "").split(os.pathsep) if item)


def shell_rc_path() -> Path:
    env_path = os.environ.get("USAGE_RECEIPT_SHELL_RC")
    if env_path:
        return Path(env_path).expanduser()
    shell_name = Path(os.environ.get("SHELL", "")).name
    if shell_name == "bash":
        return Path.home() / ".bashrc"
    if shell_name == "zsh":
        return Path.home() / ".zshrc"
    return Path.home() / ".profile"


def path_block(bin_dir: Path) -> str:
    return f"{PATH_BLOCK_START}\nexport PATH=\"{display_path(bin_dir)}:$PATH\"\n{PATH_BLOCK_END}\n"


def display_path(path: Path) -> str:
    text = str(path.expanduser())
    home = str(Path.home())
    if text == home:
        return "$HOME"
    if text.startswith(home + os.sep):
        return "$HOME" + text[len(home):]
    return text


def hook_command(hook_path: Path, client: str) -> str:
    return f"{single_quote(hook_path)} {client}"


def single_quote(path: Path) -> str:
    return "'" + str(path).replace("'", "'\"'\"'") + "'"


def read_text_if_exists(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
