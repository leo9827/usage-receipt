#!/usr/bin/env python3
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any
from urllib.request import urlopen


MILLION = Decimal("1000000")
MONEY_QUANT = Decimal("0.0001")

_BUNDLED_PRICING: dict = {
    "schema": 1,
    "currency": "USD",
    "unit": "per_1m_tokens",
    "updated_at": "2026-05-13",
    "update_url": "https://raw.githubusercontent.com/leo9827/usage-receipt/main/pricing.json",
    "models": [
        {"provider": "anthropic", "model": "claude-opus-4-5", "aliases": ["Claude Opus 4.5", "Opus 4.5", "claude-opus-4-5-20251101"], "input": 5.0, "cached_input": 0.5, "cache_write_5m": 6.25, "cache_write_1h": 10.0, "output": 25.0, "source": "https://www.anthropic.com/news/claude-opus-4-5"},
        {"provider": "anthropic", "model": "claude-opus-4", "aliases": ["Claude Opus 4", "Opus 4", "Claude-Opus-4.6", "mco-4"], "input": 15.0, "cached_input": 1.5, "cache_write_5m": 18.75, "cache_write_1h": 30.0, "output": 75.0, "source": "https://platform.claude.com/docs/en/about-claude/pricing"},
        {"provider": "anthropic", "model": "claude-sonnet-4-6", "aliases": ["Claude Sonnet 4.6", "Sonnet 4.6", "claude-sonnet-4-6-20260217"], "input": 3.0, "cached_input": 0.3, "cache_write_5m": 3.75, "cache_write_1h": 6.0, "output": 15.0, "source": "https://www.anthropic.com/news/claude-sonnet-4-6"},
        {"provider": "anthropic", "model": "claude-sonnet-4-5", "aliases": ["Claude Sonnet 4.5", "Sonnet 4.5"], "input": 3.0, "cached_input": 0.3, "cache_write_5m": 3.75, "cache_write_1h": 6.0, "output": 15.0, "source": "https://www.anthropic.com/news/claude-sonnet-4-6"},
        {"provider": "anthropic", "model": "claude-sonnet-4", "aliases": ["Claude Sonnet 4", "Sonnet 4", "mcs-5"], "input": 3.0, "cached_input": 0.3, "cache_write_5m": 3.75, "cache_write_1h": 6.0, "output": 15.0, "source": "https://platform.claude.com/docs/en/about-claude/pricing"},
        {"provider": "anthropic", "model": "claude-haiku-4-5", "aliases": ["Claude Haiku 4.5", "Haiku 4.5"], "input": 1.0, "cached_input": 0.1, "cache_write_5m": 1.25, "cache_write_1h": 2.0, "output": 5.0, "source": "https://www.anthropic.com/news/claude-haiku-4-5"},
        {"provider": "openai", "model": "gpt-5.5", "aliases": ["GPT-5.5", "gpt-5.5-2026-04-23"], "input": 5.0, "cached_input": 0.5, "cache_write_5m": None, "cache_write_1h": None, "output": 30.0, "source": "https://developers.openai.com/api/docs/models/gpt-5.5"},
        {"provider": "openai", "model": "gpt-5.4", "aliases": ["GPT-5.4"], "input": 2.5, "cached_input": 0.25, "cache_write_5m": None, "cache_write_1h": None, "output": 15.0, "source": "https://developers.openai.com/api/docs/models/gpt-5.4"},
        {"provider": "openai", "model": "gpt-5.4-mini", "aliases": ["GPT-5.4 mini", "gpt-5.4 mini"], "input": 0.75, "cached_input": 0.075, "cache_write_5m": None, "cache_write_1h": None, "output": 4.5, "source": "https://developers.openai.com/api/docs/models/gpt-5.4-mini"},
        {"provider": "moonshot", "model": "kimi-k2.6", "aliases": ["Kimi K2.6", "kimi-k2-6"], "input": 0.95, "cached_input": 0.16, "cache_write_5m": None, "cache_write_1h": None, "output": 4.0, "source": "https://platform.moonshot.ai/"},
        {"provider": "moonshot", "model": "kimi-k2.5", "aliases": ["Kimi K2.5", "kimi-k2-5"], "input": 0.6, "cached_input": 0.1, "cache_write_5m": None, "cache_write_1h": None, "output": 3.0, "source": "https://platform.moonshot.ai/"},
        {"provider": "moonshot", "model": "kimi-k2", "aliases": ["Kimi K2", "kimi-k2-0905-preview", "kimi-k2-turbo-preview", "kimi-k2-thinking", "kimi-k2-thinking-turbo"], "input": 0.6, "cached_input": 0.15, "cache_write_5m": None, "cache_write_1h": None, "output": 2.5, "source": "https://platform.moonshot.ai/"},
        {"provider": "zai", "model": "GLM-5.1", "aliases": ["glm-5.1"], "input": 1.4, "cached_input": 0.26, "cache_write_5m": None, "cache_write_1h": None, "output": 4.4, "source": "https://docs.z.ai/guides/overview/pricing"},
        {"provider": "zai", "model": "GLM-4.5-Air", "aliases": ["glm-4.5-air"], "input": 0.2, "cached_input": 0.03, "cache_write_5m": None, "cache_write_1h": None, "output": 1.1, "source": "https://docs.z.ai/guides/overview/pricing"},
    ],
}


@dataclass(frozen=True)
class Usage:
    provider: str
    client: str
    session_id: str
    source: str
    model_id: str
    model_display: str
    cwd: str
    project_dir: str
    timestamp: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int | None = None
    cache_write_5m_tokens: int | None = None
    cache_write_1h_tokens: int | None = None
    reasoning_output_tokens: int | None = None
    current_input_tokens: int | None = None
    current_output_tokens: int | None = None
    current_cached_input_tokens: int | None = None
    current_reasoning_output_tokens: int | None = None
    context_window_size: int | None = None
    context_used_percentage: Decimal | None = None
    context_remaining_percentage: Decimal | None = None
    five_hour_limit_percentage: Decimal | None = None
    weekly_limit_percentage: Decimal | None = None


@dataclass(frozen=True)
class LineItem:
    label: str
    tokens: int
    cost: Decimal | None
    price: Decimal | None


@dataclass(frozen=True)
class PricedUsage:
    usage: Usage
    model_key: str | None
    pricing: dict[str, Any] | None
    line_items: tuple[LineItem, ...]
    total_tokens: int
    total_cost: Decimal | None
    tokens_only: bool = False


@dataclass(frozen=True)
class AggregateGroup:
    model_label: str
    session_count: int
    priced: PricedUsage


@dataclass(frozen=True)
class AggregateReceipt:
    provider: str
    client: str
    label_name: str
    label: str
    source: str
    session_count: int
    groups: tuple[AggregateGroup, ...]
    total_tokens: int
    total_cost: Decimal | None
    tokens_only: bool = False


@dataclass(frozen=True)
class SessionInfo:
    session_id: str
    cwd: str
    timestamp: str
    size_bytes: int
    path: Path


def script_dir() -> Path:
    return Path(__file__).resolve().parent


def user_config_dir() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "usage-receipt"


def default_pricing_path() -> Path:
    return Path(os.environ.get("USAGE_RECEIPT_PRICING", script_dir() / "pricing.json"))


def default_state_path() -> Path:
    if os.environ.get("USAGE_RECEIPT_STATE"):
        return Path(os.environ["USAGE_RECEIPT_STATE"])
    state_home = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return state_home / "llm-usage-receipt" / "claude-latest.json"


def default_codex_sessions_glob() -> str:
    if os.environ.get("USAGE_RECEIPT_CODEX_SESSIONS_GLOB"):
        return os.environ["USAGE_RECEIPT_CODEX_SESSIONS_GLOB"]
    return str(Path.home() / ".codex" / "sessions" / "**" / "*.jsonl")


def default_claude_sessions_glob() -> str:
    if os.environ.get("USAGE_RECEIPT_CLAUDE_SESSIONS_GLOB"):
        return os.environ["USAGE_RECEIPT_CLAUDE_SESSIONS_GLOB"]
    return str(Path.home() / ".claude" / "projects" / "*" / "*.jsonl")


def load_pricing(path: str | Path | None = None) -> dict[str, Any]:
    if path is not None:
        pricing_path = Path(path)
        if not pricing_path.exists():
            raise SystemExit(f"usage-receipt: pricing file not found: {pricing_path}")
        with pricing_path.open(encoding="utf-8") as pricing_file:
            data = json.load(pricing_file)
        models = data.get("models", [])
        if not isinstance(models, list):
            raise ValueError("pricing file must contain a models array")
        return data

    candidates = []
    env_path = os.environ.get("USAGE_RECEIPT_PRICING")
    if env_path:
        candidates.append(Path(env_path))
    candidates.append(user_config_dir() / "pricing.json")
    candidates.append(script_dir() / "pricing.json")

    for candidate in candidates:
        try:
            with candidate.open(encoding="utf-8") as pricing_file:
                data = json.load(pricing_file)
            models = data.get("models", [])
            if not isinstance(models, list):
                continue
            return data
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            continue

    return _BUNDLED_PRICING


def _path(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _timestamp(value: Any) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return datetime.now().astimezone().isoformat(timespec="seconds")


def parse_usage(payload: dict[str, Any]) -> Usage:
    context_window = payload.get("context_window") if isinstance(payload.get("context_window"), dict) else {}
    current_usage = context_window.get("current_usage") if isinstance(context_window.get("current_usage"), dict) else {}

    model = payload.get("model") if isinstance(payload.get("model"), dict) else {}
    model_id = str(payload.get("model_id") or model.get("id") or "").strip()
    model_display = str(payload.get("model_display") or model.get("display_name") or model_id or "unknown").strip()

    current_input = _int(payload.get("current_input_tokens"))
    if current_input is None:
        current_input = _int(current_usage.get("input_tokens"))
    current_output = _int(payload.get("current_output_tokens"))
    if current_output is None:
        current_output = _int(current_usage.get("output_tokens"))

    input_tokens = _int(payload.get("input_tokens"))
    if input_tokens is None:
        input_tokens = _int(context_window.get("total_input_tokens"))
    if input_tokens is None:
        input_tokens = current_input or 0

    output_tokens = _int(payload.get("output_tokens"))
    if output_tokens is None:
        output_tokens = _int(context_window.get("total_output_tokens"))
    if output_tokens is None:
        output_tokens = current_output or 0

    cache_read = _first_int(
        payload.get("cache_read_tokens"),
        payload.get("cache_read_input_tokens"),
        current_usage.get("cache_read_input_tokens"),
        context_window.get("cache_read_input_tokens"),
    )
    cache_write_5m = _first_int(
        payload.get("cache_write_5m_tokens"),
        current_usage.get("cache_write_5m_input_tokens"),
        context_window.get("cache_write_5m_input_tokens"),
    )
    cache_write_1h = _first_int(
        payload.get("cache_write_1h_tokens"),
        current_usage.get("cache_write_1h_input_tokens"),
        context_window.get("cache_write_1h_input_tokens"),
    )

    cache_creation = _first_int(
        payload.get("cache_write_tokens"),
        payload.get("cache_creation_input_tokens"),
        current_usage.get("cache_creation_input_tokens"),
        context_window.get("cache_creation_input_tokens"),
    )
    if cache_write_5m is None:
        cache_write_5m = cache_creation

    return Usage(
        provider=str(payload.get("provider") or "claude").strip() or "claude",
        client=str(payload.get("client") or "claude-code").strip() or "claude-code",
        session_id=str(payload.get("session_id") or "").strip(),
        source=str(payload.get("source") or "").strip(),
        model_id=model_id,
        model_display=model_display,
        cwd=str(payload.get("cwd") or _path(payload, "workspace", "current_dir") or "").strip(),
        project_dir=str(payload.get("project_dir") or _path(payload, "workspace", "project_dir") or "").strip(),
        timestamp=_timestamp(payload.get("timestamp") or payload.get("created_at")),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_tokens=cache_read,
        cache_write_5m_tokens=cache_write_5m,
        cache_write_1h_tokens=cache_write_1h,
        reasoning_output_tokens=_int(payload.get("reasoning_output_tokens")),
        current_input_tokens=current_input,
        current_output_tokens=current_output,
        current_cached_input_tokens=_int(payload.get("current_cached_input_tokens")),
        current_reasoning_output_tokens=_int(payload.get("current_reasoning_output_tokens")),
        context_window_size=_int(context_window.get("context_window_size")),
        context_used_percentage=_decimal(context_window.get("used_percentage")),
        context_remaining_percentage=_decimal(context_window.get("remaining_percentage")),
        five_hour_limit_percentage=_decimal(payload.get("five_hour_limit_percentage")),
        weekly_limit_percentage=_decimal(payload.get("weekly_limit_percentage")),
    )


def load_codex_session(path: str | Path) -> dict[str, Any]:
    session_path = Path(path)
    token_event: dict[str, Any] | None = None
    turn_context: dict[str, Any] = {}
    session_meta: dict[str, Any] = {}

    with session_path.open(encoding="utf-8") as session_file:
        for line in session_file:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
            if event.get("type") == "session_meta":
                session_meta = payload
            elif event.get("type") == "turn_context":
                turn_context = payload
            elif event.get("type") == "event_msg" and payload.get("type") == "token_count":
                total_usage = _path(payload, "info", "total_token_usage")
                if isinstance(total_usage, dict) and total_usage:
                    token_event = event

    if token_event is None:
        raise SystemExit(f"usage-receipt: no Codex token_count event found in {session_path}")

    payload = token_event.get("payload", {})
    info = payload.get("info", {})
    total = info.get("total_token_usage", {})
    last = info.get("last_token_usage", {})
    total_input = _int(total.get("input_tokens")) or 0
    total_cached = _int(total.get("cached_input_tokens")) or 0
    last_input = _int(last.get("input_tokens"))
    last_cached = _int(last.get("cached_input_tokens"))
    rate_limits = payload.get("rate_limits", {})
    primary = rate_limits.get("primary", {})
    secondary = rate_limits.get("secondary", {})
    timestamp = str(token_event.get("timestamp") or "")
    session_id = str(session_meta.get("id") or session_path.stem)

    return {
        "provider": "codex",
        "client": "codex",
        "session_id": session_id,
        "source": str(session_path),
        "timestamp": timestamp or str(session_meta.get("timestamp") or ""),
        "model_id": str(turn_context.get("model") or ""),
        "model_display": str(turn_context.get("model") or "Codex"),
        "cwd": str(turn_context.get("cwd") or session_meta.get("cwd") or ""),
        "input_tokens": max(total_input - total_cached, 0),
        "cache_read_tokens": total_cached,
        "output_tokens": _int(total.get("output_tokens")) or 0,
        "reasoning_output_tokens": _int(total.get("reasoning_output_tokens")),
        "current_input_tokens": None if last_input is None else max(last_input - (last_cached or 0), 0),
        "current_cached_input_tokens": last_cached,
        "current_output_tokens": _int(last.get("output_tokens")),
        "current_reasoning_output_tokens": _int(last.get("reasoning_output_tokens")),
        "context_window": {
            "context_window_size": _int(info.get("model_context_window")),
        },
        "five_hour_limit_percentage": _decimal(primary.get("used_percent")),
        "weekly_limit_percentage": _decimal(secondary.get("used_percent")),
    }


_CLAUDE_MODEL_ENV_MAP = {
    "mco": "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "mcs": "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "mch": "ANTHROPIC_DEFAULT_HAIKU_MODEL",
}


def _resolve_claude_model_display(model_id: str) -> str:
    prefix = model_id.rsplit("-", 1)[0] if "-" in model_id else model_id
    env_key = _CLAUDE_MODEL_ENV_MAP.get(prefix)
    if env_key:
        env_val = os.environ.get(env_key, "").strip()
        if env_val:
            return env_val
        settings_val = _claude_settings_env(env_key)
        if settings_val:
            return settings_val
    return model_id


def _claude_settings_env(key: str) -> str:
    try:
        settings_path = Path.home() / ".claude" / "settings.json"
        data = json.loads(settings_path.read_text(encoding="utf-8"))
        return str(data.get("env", {}).get(key, "")).strip()
    except (OSError, json.JSONDecodeError, AttributeError):
        return ""


def load_claude_session(
    path: str | Path,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[Usage]:
    session_path = Path(path)
    session_id = session_path.stem
    cwd = ""
    project_dir = ""
    latest_timestamp = ""
    seen_message_ids: set[str] = set()
    groups: dict[str, dict[str, Any]] = {}

    with session_path.open(encoding="utf-8") as session_file:
        for line_number, line in enumerate(session_file, start=1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue

            session_id = str(event.get("sessionId") or session_id)
            cwd = str(event.get("cwd") or cwd)
            project_dir = str(event.get("cwd") or project_dir)
            event_timestamp = str(event.get("timestamp") or "")
            event_dt = parse_datetime(event_timestamp)

            message = event.get("message") if isinstance(event.get("message"), dict) else {}
            usage = message.get("usage") if isinstance(message.get("usage"), dict) else None
            if usage is None:
                continue
            if start is not None and (event_dt is None or event_dt < start):
                continue
            if end is not None and (event_dt is None or event_dt >= end):
                continue

            message_id = str(message.get("id") or event.get("uuid") or f"{session_path}:{line_number}")
            if message_id in seen_message_ids:
                continue
            seen_message_ids.add(message_id)

            model_id = str(message.get("model") or "unknown").strip() or "unknown"
            token_usage = _claude_usage_tokens(usage)
            if token_usage["total"] <= 0:
                continue

            latest_timestamp = event_timestamp or latest_timestamp
            group = groups.setdefault(
                model_id,
                {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_read_tokens": 0,
                    "cache_write_5m_tokens": 0,
                    "cache_write_1h_tokens": 0,
                    "timestamp": event_timestamp,
                },
            )
            group["input_tokens"] += token_usage["input_tokens"]
            group["output_tokens"] += token_usage["output_tokens"]
            group["cache_read_tokens"] += token_usage["cache_read_tokens"]
            group["cache_write_5m_tokens"] += token_usage["cache_write_5m_tokens"]
            group["cache_write_1h_tokens"] += token_usage["cache_write_1h_tokens"]
            group["timestamp"] = event_timestamp or group["timestamp"]

    usages = []
    for model_id, totals in groups.items():
        usages.append(
            Usage(
                provider="claude",
                client="claude-code",
                session_id=session_id,
                source=str(session_path),
                model_id=model_id,
                model_display=_resolve_claude_model_display(model_id),
                cwd=cwd,
                project_dir=project_dir,
                timestamp=str(totals.get("timestamp") or latest_timestamp),
                input_tokens=int(totals["input_tokens"]),
                output_tokens=int(totals["output_tokens"]),
                cache_read_tokens=int(totals["cache_read_tokens"]),
                cache_write_5m_tokens=int(totals["cache_write_5m_tokens"]),
                cache_write_1h_tokens=int(totals["cache_write_1h_tokens"]),
            )
        )
    return usages


def _claude_usage_tokens(usage: dict[str, Any]) -> dict[str, int]:
    cache_creation = usage.get("cache_creation") if isinstance(usage.get("cache_creation"), dict) else {}
    if "ephemeral_5m_input_tokens" in cache_creation:
        cache_write_5m = _int(cache_creation.get("ephemeral_5m_input_tokens")) or 0
    else:
        cache_write_5m = _int(usage.get("cache_creation_input_tokens")) or 0

    return {
        "input_tokens": _int(usage.get("input_tokens")) or 0,
        "output_tokens": _int(usage.get("output_tokens")) or 0,
        "cache_read_tokens": _int(usage.get("cache_read_input_tokens")) or 0,
        "cache_write_5m_tokens": cache_write_5m,
        "cache_write_1h_tokens": _int(cache_creation.get("ephemeral_1h_input_tokens")) or 0,
        "total": sum(
            [
                _int(usage.get("input_tokens")) or 0,
                _int(usage.get("output_tokens")) or 0,
                _int(usage.get("cache_read_input_tokens")) or 0,
                cache_write_5m,
                _int(cache_creation.get("ephemeral_1h_input_tokens")) or 0,
            ]
        ),
    }


def latest_codex_session() -> Path:
    matches = [Path(path) for path in glob.glob(default_codex_sessions_glob(), recursive=True)]
    if not matches:
        raise SystemExit("usage-receipt: no Codex sessions found under ~/.codex/sessions")
    return max(matches, key=lambda path: path.stat().st_mtime)


def iter_session_paths(client: str) -> list[Path]:
    pattern = default_codex_sessions_glob() if client == "codex" else default_claude_sessions_glob()
    return sorted(Path(path) for path in glob.glob(pattern, recursive=True))


def resolve_session_path(client: str, query: str) -> Path:
    matches: list[tuple[str, Path]] = []
    exact_matches: list[tuple[str, Path]] = []
    for path in iter_session_paths(client):
        for session_id in session_identity_values(client, path):
            if session_id == query:
                exact_matches.append((session_id, path))
            elif session_id.startswith(query):
                matches.append((session_id, path))

    candidates = exact_matches or matches
    unique = _unique_session_matches(candidates)
    if len(unique) == 1:
        return unique[0][1]
    if not unique:
        raise SystemExit(f"usage-receipt: no {client} session found matching {query!r}")

    lines = [f"{session_id} {path}" for session_id, path in unique[:10]]
    more = "" if len(unique) <= 10 else f"\n... {len(unique) - 10} more"
    raise SystemExit(f"usage-receipt: multiple {client} sessions match {query!r}:\n" + "\n".join(lines) + more)


def _unique_session_matches(matches: list[tuple[str, Path]]) -> list[tuple[str, Path]]:
    seen: set[Path] = set()
    unique = []
    for session_id, path in matches:
        if path in seen:
            continue
        seen.add(path)
        unique.append((session_id, path))
    return unique


def session_identity_values(client: str, path: Path) -> list[str]:
    values = [path.stem]
    if client == "codex":
        session_id = codex_session_meta_id(path)
        if session_id:
            values.insert(0, session_id)
    return values


def codex_session_meta_id(path: Path) -> str:
    try:
        with path.open(encoding="utf-8") as session_file:
            for line in session_file:
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("type") != "session_meta":
                    continue
                payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
                return str(payload.get("id") or "")
    except OSError:
        return ""
    return ""


def claude_session_meta(path: Path) -> SessionInfo:
    session_id = path.stem
    cwd = ""
    timestamp = ""
    try:
        with path.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(event, dict):
                    continue
                session_id = str(event.get("sessionId") or session_id)
                cwd = str(event.get("cwd") or cwd)
                timestamp = str(event.get("timestamp") or timestamp)
                if session_id and cwd and timestamp:
                    break
    except OSError:
        pass
    return SessionInfo(
        session_id=session_id, cwd=cwd, timestamp=timestamp,
        size_bytes=_file_size(path), path=path,
    )


def codex_session_meta(path: Path) -> SessionInfo:
    session_id = path.stem
    cwd = ""
    timestamp = ""
    try:
        with path.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("type") != "session_meta":
                    continue
                payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
                session_id = str(payload.get("id") or session_id)
                cwd = str(payload.get("cwd") or "")
                timestamp = str(payload.get("timestamp") or event.get("timestamp") or "")
                break
    except OSError:
        pass
    return SessionInfo(
        session_id=session_id, cwd=cwd, timestamp=timestamp,
        size_bytes=_file_size(path), path=path,
    )


def _file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def list_sessions(client: str) -> list[SessionInfo]:
    extractor = codex_session_meta if client == "codex" else claude_session_meta
    sessions = [extractor(p) for p in iter_session_paths(client)]
    sessions.sort(key=lambda s: s.timestamp or "", reverse=True)
    return sessions


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes}B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}K"
    return f"{size_bytes / (1024 * 1024):.1f}M"


def _format_local_time(timestamp_str: str) -> str:
    dt = parse_datetime(timestamp_str)
    if dt is None:
        return "-"
    return dt.strftime("%Y-%m-%d %H:%M")


def _shorten_cwd(cwd: str, width: int) -> str:
    if not cwd or len(cwd) <= width:
        return cwd or "-"
    home = str(Path.home())
    if cwd.startswith(home):
        cwd = "~" + cwd[len(home):]
    if len(cwd) <= width:
        return cwd
    return "~" + cwd[-(width - 1):]


def render_session_list(sessions: list[SessionInfo], client: str) -> str:
    width = 72
    strong_sep = "=" * width
    sep = "-" * width
    title = f"{client.upper()} SESSIONS"
    lines = [
        "LLM TOKEN MART".center(width),
        title.center(width),
        strong_sep,
        f"  {'ID':<38}{'TIME':<18}{'SIZE':>7}",
        f"  {'CWD':<68}",
        sep,
    ]
    shown = sessions[:50]
    for s in shown:
        sid = _trim_text(s.session_id, 38)
        ts = _format_local_time(s.timestamp)
        size = _format_size(s.size_bytes)
        cwd = _shorten_cwd(s.cwd, 68)
        lines.append(f"  {sid:<38}{ts:<18}{size:>7}")
        lines.append(f"  {cwd}")
    lines.append(sep)
    lines.append(f"  TOTAL: {len(sessions)} sessions")
    if len(sessions) > 50:
        lines.append(f"  (showing first 50)")
    lines.append(strong_sep)
    return "\n".join(lines)


def run_list_sessions(args: argparse.Namespace) -> str:
    client = selected_client(args)
    sessions = list_sessions(client)
    if not sessions:
        raise SystemExit(f"usage-receipt: no {client} sessions found")
    return render_session_list(sessions, client)


def parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=local_timezone())
    return parsed.astimezone(local_timezone())


def local_timezone():
    return datetime.now().astimezone().tzinfo


def range_bounds(args: argparse.Namespace) -> tuple[datetime, datetime, str]:
    selectors = sum(bool(value) for value in (args.date, args.last, args.since or args.until))
    if selectors != 1:
        raise SystemExit("usage-receipt: choose exactly one range selector: --date, --last, or --since/--until")
    if args.date:
        day = parse_date_selector(args.date)
        start = datetime.combine(day, time.min, tzinfo=local_timezone())
        end = start + timedelta(days=1)
        return start, end, day.isoformat()
    if args.last:
        end = datetime.now(local_timezone())
        delta = parse_last_delta(args.last)
        start = end - delta
        return start, end, f"last {args.last}"

    start = parse_boundary(args.since, is_end=False) if args.since else datetime.min.replace(tzinfo=local_timezone())
    end = parse_boundary(args.until, is_end=True) if args.until else datetime.now(local_timezone())
    return start, end, f"{args.since or '-infinity'}..{args.until or 'now'}"


def parse_date_selector(value: str) -> date:
    lowered = value.strip().lower()
    today = datetime.now(local_timezone()).date()
    if lowered == "today":
        return today
    if lowered == "yesterday":
        return today - timedelta(days=1)
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(f"usage-receipt: invalid date {value!r}; use today, yesterday, or YYYY-MM-DD") from exc


def parse_last_delta(value: str) -> timedelta:
    match = re.fullmatch(r"(\d+)([dwm])", value.strip().lower())
    if not match:
        raise SystemExit("usage-receipt: --last expects Nd, Nw, or Nm, for example 30d or 1m")
    count = int(match.group(1))
    unit = match.group(2)
    days = count if unit == "d" else count * 7 if unit == "w" else count * 30
    return timedelta(days=days)


def parse_boundary(value: str, is_end: bool) -> datetime:
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value.strip()):
        day = date.fromisoformat(value)
        start = datetime.combine(day, time.min, tzinfo=local_timezone())
        return start + timedelta(days=1) if is_end else start
    parsed = parse_datetime(value)
    if parsed is None:
        raise SystemExit(f"usage-receipt: invalid timestamp {value!r}")
    return parsed


def _first_int(*values: Any) -> int | None:
    for value in values:
        parsed = _int(value)
        if parsed is not None:
            return parsed
    return None


def normalize_model_name(name: str) -> str:
    normalized = name.strip().lower()
    normalized = re.sub(r"[\s_]+", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized)
    return normalized.strip("-")


def _strip_snapshot_suffix(name: str) -> str:
    stripped = name
    for pattern in (r"-\d{8}$", r"-\d{4}-\d{2}-\d{2}$"):
        stripped = re.sub(pattern, "", stripped)
    return stripped


def _pricing_index(pricing: dict[str, Any]) -> dict[str, str]:
    index: dict[str, str] = {}
    for model in pricing.get("models", []):
        if not isinstance(model, dict):
            continue
        key = str(model.get("model", "")).strip()
        if not key:
            continue
        for alias in [key, *model.get("aliases", [])]:
            index[normalize_model_name(str(alias))] = key
    return index


def resolve_model_key(model_name: str, pricing: dict[str, Any]) -> str | None:
    if not model_name:
        return None

    index = _pricing_index(pricing)
    normalized = normalize_model_name(model_name)
    candidates = [
        normalized,
        _strip_snapshot_suffix(normalized),
    ]
    for candidate in candidates:
        if candidate in index:
            return index[candidate]
    return None


def pricing_for(model_key: str | None, pricing: dict[str, Any]) -> dict[str, Any] | None:
    if model_key is None:
        return None
    for model in pricing.get("models", []):
        if isinstance(model, dict) and model.get("model") == model_key:
            return model
    return None


def price_usage(usage: Usage, pricing: dict[str, Any], tokens_only: bool = False) -> PricedUsage:
    model_key = resolve_model_key(usage.model_id, pricing)
    if model_key is None:
        model_key = resolve_model_key(usage.model_display, pricing)
    model_pricing = pricing_for(model_key, pricing)

    items = [
        _line("Input", usage.input_tokens, model_pricing, "input", tokens_only),
        _line("Output", usage.output_tokens, model_pricing, "output", tokens_only),
        _optional_line("Cache read", usage.cache_read_tokens, model_pricing, "cached_input", tokens_only),
    ]
    if usage.reasoning_output_tokens is not None:
        items.append(_line("Reasoning out", usage.reasoning_output_tokens, model_pricing, "output", tokens_only))
    if usage.cache_write_5m_tokens is not None:
        items.append(
            _line("Cache write 5m", usage.cache_write_5m_tokens, model_pricing, "cache_write_5m", tokens_only)
        )
    if usage.cache_write_1h_tokens is not None:
        items.append(
            _line("Cache write 1h", usage.cache_write_1h_tokens, model_pricing, "cache_write_1h", tokens_only)
        )
    line_items = tuple(items)

    total_cost: Decimal | None = Decimal("0")
    for item in line_items:
        if item.cost is None:
            if item.label in ("Input", "Output") or item.tokens > 0:
                total_cost = None
                break
            continue
        total_cost += item.cost

    return PricedUsage(
        usage=usage,
        model_key=model_key,
        pricing=model_pricing,
        line_items=line_items,
        total_tokens=sum(item.tokens for item in line_items),
        total_cost=money(total_cost) if total_cost is not None else None,
        tokens_only=tokens_only,
    )


def _line(
    label: str,
    tokens: int,
    model_pricing: dict[str, Any] | None,
    price_field: str,
    tokens_only: bool,
) -> LineItem:
    price = None if model_pricing is None or tokens_only else _decimal(model_pricing.get(price_field))
    cost = None if price is None else (Decimal(tokens) / MILLION) * price
    return LineItem(label=label, tokens=tokens, cost=cost, price=price)


def _optional_line(
    label: str,
    tokens: int | None,
    model_pricing: dict[str, Any] | None,
    price_field: str,
    tokens_only: bool,
) -> LineItem:
    if tokens is None:
        return LineItem(label=label, tokens=0, cost=None, price=None)
    return _line(label, tokens, model_pricing, price_field, tokens_only)


def money(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def format_cost(value: Decimal | None) -> str:
    if value is None:
        return "n/a"
    rounded = money(value)
    return f"${rounded:.4f}"


def format_tokens(value: int) -> str:
    return f"{value:,}"


def short_path(path: str) -> str:
    if not path:
        return ""
    home = str(Path.home())
    if path == home:
        return "~"
    if path.startswith(home + os.sep):
        return "~" + path[len(home):]
    return path


def render_receipt(priced: PricedUsage, ascii_only: bool = False, verbose: bool = False) -> str:
    usage = priced.usage
    width = RECEIPT_WIDTH
    sep = "-" * width
    strong_sep = "=" * width
    model_label = usage.model_display or usage.model_id or "unknown"
    if model_label == usage.model_id and priced.model_key:
        model_label = priced.model_key

    lines = [
        "LLM TOKEN MART".center(width),
        ("TOKENS ONLY RECEIPT" if priced.tokens_only else "SESSION COST RECEIPT").center(width),
        strong_sep,
        *_metadata_lines("PROVIDER", provider_label(usage), width),
        *_metadata_lines("SESSION", usage.session_id or "-", width),
        *_metadata_lines("MODEL", model_label, width),
        *_metadata_lines("DIR", short_path(usage.cwd), width),
        *_metadata_lines("TIME", usage.timestamp, width),
    ]

    if verbose:
        lines.extend(_metadata_lines("SOURCE", usage.source or "-", width))
        if usage.current_input_tokens is not None or usage.current_output_tokens is not None:
            lines.extend(
                _metadata_lines(
                    "CURR",
                    f"{format_tokens(usage.current_input_tokens or 0)} in / "
                    f"{format_tokens(usage.current_output_tokens or 0)} out",
                    width,
                )
            )
        if usage.context_window_size is not None:
            pct = "" if usage.context_used_percentage is None else f" ({usage.context_used_percentage}%)"
            lines.extend(_metadata_lines("CTX", f"{format_tokens(usage.context_window_size)}{pct}", width))
        if priced.pricing is not None:
            lines.extend(_metadata_lines("SRC", str(priced.pricing.get("source", "")), width))

    lines.extend(
        [
            sep,
            _items_header(priced.tokens_only, width),
            sep,
        ]
    )
    lines.extend(_item_line(item, priced.tokens_only, width) for item in priced.line_items)
    label_w, tok_w, rate_w, amt_w = _session_col_widths(priced.tokens_only, width)
    lines.extend([sep, f"{'TOTAL TOKENS':<{label_w}}{format_tokens(priced.total_tokens):>{tok_w}}"])
    if not priced.tokens_only:
        lines.append(f"{'SUBTOTAL':<{label_w}}{' ' * (tok_w + rate_w)}{format_cost(priced.total_cost):>{amt_w}}")
    lines.extend([sep, *_detail_rows(priced, width), strong_sep])
    if priced.tokens_only:
        lines.append("Token counts only. Pricing disabled.".center(width))
    else:
        lines.append("API price estimate, not subscription billing.".center(width))
    return "\n".join(lines)


def render_usage_collection(
    usages: list[Usage],
    pricing: dict[str, Any],
    label: str,
    label_name: str,
    source: str,
    tokens_only: bool,
    ascii_only: bool,
    verbose: bool,
    force_aggregate: bool = False,
) -> str:
    if not usages:
        raise SystemExit("usage-receipt: no usage records found")
    if len(usages) == 1 and not force_aggregate:
        return render_receipt(price_usage(usages[0], pricing, tokens_only=tokens_only), ascii_only, verbose)
    aggregate = build_aggregate_receipt(usages, pricing, label_name, label, source, tokens_only)
    return render_aggregate_receipt(aggregate, ascii_only=ascii_only, verbose=verbose)


def build_aggregate_receipt(
    usages: list[Usage],
    pricing: dict[str, Any],
    label_name: str,
    label: str,
    source: str,
    tokens_only: bool,
) -> AggregateReceipt:
    grouped: dict[str, list[Usage]] = {}
    labels: dict[str, str] = {}
    for usage in usages:
        model_key = resolve_model_key(usage.model_id, pricing) or resolve_model_key(usage.model_display, pricing)
        label_value = model_key or usage.model_display or usage.model_id or "unknown"
        group_key = model_key or f"unknown:{normalize_model_name(label_value)}"
        grouped.setdefault(group_key, []).append(usage)
        labels[group_key] = label_value

    groups = []
    for group_key in sorted(grouped):
        combined = combine_usages(grouped[group_key], model_label=labels[group_key])
        priced = price_usage(combined, pricing, tokens_only=tokens_only)
        groups.append(
            AggregateGroup(
                model_label=labels[group_key],
                session_count=len({usage.session_id for usage in grouped[group_key]}),
                priced=priced,
            )
        )

    total_cost: Decimal | None = Decimal("0")
    for group in groups:
        if group.priced.total_cost is None:
            continue
        total_cost += group.priced.total_cost

    first = usages[0]
    return AggregateReceipt(
        provider=first.provider,
        client="aggregate",
        label_name=label_name,
        label=label,
        source=source,
        session_count=len({usage.session_id for usage in usages}),
        groups=tuple(groups),
        total_tokens=sum(group.priced.total_tokens for group in groups),
        total_cost=money(total_cost) if total_cost is not None else None,
        tokens_only=tokens_only,
    )


def combine_usages(usages: list[Usage], model_label: str) -> Usage:
    first = usages[0]
    session_ids = {usage.session_id for usage in usages}
    cwd_values = {usage.cwd for usage in usages if usage.cwd}
    return Usage(
        provider=first.provider,
        client=first.client,
        session_id=f"{len(session_ids)} sessions",
        source="mixed",
        model_id=model_label,
        model_display=model_label,
        cwd=next(iter(cwd_values)) if len(cwd_values) == 1 else "mixed",
        project_dir="",
        timestamp=max((usage.timestamp for usage in usages if usage.timestamp), default=""),
        input_tokens=sum(usage.input_tokens for usage in usages),
        output_tokens=sum(usage.output_tokens for usage in usages),
        cache_read_tokens=sum_optional(usages, "cache_read_tokens"),
        cache_write_5m_tokens=sum_optional(usages, "cache_write_5m_tokens"),
        cache_write_1h_tokens=sum_optional(usages, "cache_write_1h_tokens"),
        reasoning_output_tokens=sum_optional(usages, "reasoning_output_tokens"),
    )


def sum_optional(usages: list[Usage], field_name: str) -> int | None:
    values = [getattr(usage, field_name) for usage in usages]
    if all(value is None for value in values):
        return None
    return sum(int(value or 0) for value in values)


def render_aggregate_receipt(
    aggregate: AggregateReceipt,
    ascii_only: bool = False,
    verbose: bool = False,
) -> str:
    width = RECEIPT_WIDTH
    sep = "-" * width
    strong_sep = "=" * width
    title = "SESSION COST RECEIPT" if aggregate.label_name == "SESSION" else "USAGE RANGE RECEIPT"
    if aggregate.tokens_only:
        title = f"TOKENS ONLY {aggregate.label_name} RECEIPT"
    lines = [
        "LLM TOKEN MART".center(width),
        title.center(width),
        strong_sep,
        *_metadata_lines("PROVIDER", f"{_PROVIDER_BRAND.get((aggregate.provider or '').lower(), aggregate.provider or '-')} / {aggregate.client or '-'}", width),
        *_metadata_lines(aggregate.label_name, aggregate.label, width),
        *_metadata_lines("SESSIONS", str(aggregate.session_count), width),
        sep,
        "MODEL GROUPS",
        _model_group_header(aggregate.tokens_only, width),
        sep,
    ]
    lines.extend(_model_group_line(group, aggregate.tokens_only, width) for group in aggregate.groups)
    lines.extend([sep, "ITEM TOTALS", _aggregate_item_header(aggregate.tokens_only, width), sep])
    lines.extend(_aggregate_item_line(item, aggregate.tokens_only, width) for item in aggregate_line_items(aggregate.groups))
    label_w, tok_w, amt_w = _aggregate_col_widths(aggregate.tokens_only, width)
    lines.extend([sep, f"{'TOTAL TOKENS':<{label_w}}{format_tokens(aggregate.total_tokens):>{tok_w}}"])
    if not aggregate.tokens_only:
        lines.append(f"{'SUBTOTAL':<{label_w}}{' ' * tok_w}{format_cost(aggregate.total_cost):>{amt_w}}")
    if verbose:
        lines.append(sep)
        lines.extend(_metadata_lines("SOURCE", aggregate.source, width))
        for group in aggregate.groups:
            source = group.priced.usage.source
            lines.extend(_metadata_lines(_trim_text(group.model_label, 6).upper(), source, width))
    lines.append(strong_sep)
    if aggregate.tokens_only:
        lines.append("Token counts only. Pricing disabled.".center(width))
    else:
        lines.append("API price estimate, not subscription billing.".center(width))
    return "\n".join(lines)


def _aggregate_col_widths(tokens_only: bool, width: int) -> tuple[int, int, int]:
    """Return (label_w, tok_w, amt_w) shared by all aggregate receipt sections."""
    label_w = width // 2
    if tokens_only:
        return label_w, width - label_w, 0
    tok_w = (width - label_w) // 2
    amt_w = width - label_w - tok_w
    return label_w, tok_w, amt_w


def _model_group_col_widths(tokens_only: bool, width: int) -> tuple[int, int, int, int]:
    label_w, tok_w, amt_w = _aggregate_col_widths(tokens_only, width)
    sess_w = 6
    model_w = label_w - sess_w
    return model_w, sess_w, tok_w, amt_w


def _model_group_header(tokens_only: bool, width: int) -> str:
    label_w, sess_w, tok_w, amt_w = _model_group_col_widths(tokens_only, width)
    if tokens_only:
        return f"{'MODEL':<{label_w}}{'SESS':>{sess_w}}{'TOKENS':>{tok_w}}"
    return f"{'MODEL':<{label_w}}{'SESS':>{sess_w}}{'TOKENS':>{tok_w}}{'AMOUNT':>{amt_w}}"


def _model_group_line(group: AggregateGroup, tokens_only: bool, width: int) -> str:
    label_w, sess_w, tok_w, amt_w = _model_group_col_widths(tokens_only, width)
    label = _trim_text(group.model_label, label_w)
    if tokens_only:
        return f"{label:<{label_w}}{group.session_count:>{sess_w}}{format_tokens(group.priced.total_tokens):>{tok_w}}"
    return (
        f"{label:<{label_w}}{group.session_count:>{sess_w}}"
        f"{format_tokens(group.priced.total_tokens):>{tok_w}}{format_cost(group.priced.total_cost):>{amt_w}}"
    )


def _aggregate_item_header(tokens_only: bool, width: int) -> str:
    label_w, tok_w, amt_w = _aggregate_col_widths(tokens_only, width)
    if tokens_only:
        return f"{'ITEM':<{label_w}}{'TOKENS':>{tok_w}}"
    return f"{'ITEM':<{label_w}}{'TOKENS':>{tok_w}}{'AMOUNT':>{amt_w}}"


def _aggregate_item_line(item: LineItem, tokens_only: bool, width: int) -> str:
    label_w, tok_w, amt_w = _aggregate_col_widths(tokens_only, width)
    if tokens_only:
        return f"{item.label:<{label_w}}{format_tokens(item.tokens):>{tok_w}}"
    return f"{item.label:<{label_w}}{format_tokens(item.tokens):>{tok_w}}{format_cost(item.cost):>{amt_w}}"


def aggregate_line_items(groups: tuple[AggregateGroup, ...]) -> list[LineItem]:
    order = ["Input", "Output", "Cache read", "Reasoning out", "Cache write 5m", "Cache write 1h"]
    items = []
    for label in order:
        matching = [item for group in groups for item in group.priced.line_items if item.label == label]
        if not matching:
            continue
        tokens = sum(item.tokens for item in matching)
        if tokens == 0 and label not in ("Input", "Output"):
            continue
        cost: Decimal | None = Decimal("0")
        for item in matching:
            if item.cost is None and item.tokens > 0:
                continue
            cost += item.cost or Decimal("0")
        items.append(LineItem(label=label, tokens=tokens, cost=money(cost), price=None))
    return items


def _trim_text(value: str, width: int) -> str:
    if len(value) <= width:
        return value
    return value[: max(0, width - 1)] + "~"


def _session_col_widths(tokens_only: bool, width: int) -> tuple[int, int, int, int]:
    if tokens_only:
        label_w = width // 2
        return label_w, width - label_w, 0, 0
    label_w = 16
    tok_w = 10
    rate_w = 12
    amt_w = width - label_w - tok_w - rate_w
    return label_w, tok_w, rate_w, amt_w


def _items_header(tokens_only: bool, width: int) -> str:
    label_w, tok_w, rate_w, amt_w = _session_col_widths(tokens_only, width)
    if tokens_only:
        return f"{'ITEM':<{label_w}}{'TOKENS':>{tok_w}}"
    return f"{'ITEM':<{label_w}}{'TOKENS':>{tok_w}}{'RATE/MTOK':>{rate_w}}{'AMOUNT':>{amt_w}}"


def _detail_rows(priced: PricedUsage, width: int) -> list[str]:
    usage = priced.usage
    rows = [
        _detail_line("CACHE HIT", format_percent(cache_hit_ratio(usage)), width),
    ]
    if not priced.tokens_only:
        rows.append(_detail_line("CACHE SAVED", format_cost(cache_savings(priced)), width))
        rows.append(_detail_line("EFFECTIVE RATE", effective_rate(priced), width))

    context = context_summary(usage)
    if context:
        rows.append(_detail_line("CONTEXT", context, width))

    current_turn = current_turn_summary(usage)
    if current_turn:
        rows.append(_detail_line("CURRENT TURN", current_turn, width))
    if usage.current_cached_input_tokens is not None:
        rows.append(_detail_line("LAST CACHED", format_tokens(usage.current_cached_input_tokens), width))
    if usage.current_reasoning_output_tokens is not None:
        rows.append(_detail_line("LAST REASONING", format_tokens(usage.current_reasoning_output_tokens), width))
    if usage.five_hour_limit_percentage is not None:
        rows.append(_detail_line("5H LIMIT", format_percent(usage.five_hour_limit_percentage), width))
    if usage.weekly_limit_percentage is not None:
        rows.append(_detail_line("WEEKLY LIMIT", format_percent(usage.weekly_limit_percentage), width))

    return rows


_PROVIDER_BRAND: dict[str, str] = {
    "claude": "Anthropic",
    "anthropic": "Anthropic",
    "openai": "OpenAI",
    "gpt": "OpenAI",
    "codex": "OpenAI",
    "gemini": "Google",
    "google": "Google",
    "deepseek": "DeepSeek",
    "mistral": "Mistral",
}

RECEIPT_WIDTH = 48
_LABEL_WIDTH = 8


def provider_label(usage: Usage) -> str:
    provider = usage.provider or "-"
    brand = _PROVIDER_BRAND.get(provider.lower(), provider)
    client = usage.client or "-"
    return f"{brand} / {client}"


def _detail_line(label: str, value: str, width: int) -> str:
    label_w = width // 2
    if len(value) <= width - label_w:
        return f"{label:<{label_w}}{value:>{width - label_w}}"
    gap = 1
    max_value = width - len(label) - gap
    return f"{label}{' ' * gap}{value:>{max_value}}"


def cache_hit_ratio(usage: Usage) -> Decimal | None:
    cache_read = usage.cache_read_tokens or 0
    prompt_tokens = (
        usage.input_tokens
        + cache_read
        + (usage.cache_write_5m_tokens or 0)
        + (usage.cache_write_1h_tokens or 0)
    )
    if prompt_tokens <= 0:
        return None
    return (Decimal(cache_read) / Decimal(prompt_tokens)) * Decimal("100")


def cache_savings(priced: PricedUsage) -> Decimal | None:
    usage = priced.usage
    if usage.cache_read_tokens is None or priced.pricing is None:
        return None
    input_price = _decimal(priced.pricing.get("input"))
    cached_price = _decimal(priced.pricing.get("cached_input"))
    if input_price is None or cached_price is None:
        return None
    per_token_savings = input_price - cached_price
    if per_token_savings <= 0:
        return Decimal("0")
    return money((Decimal(usage.cache_read_tokens) / MILLION) * per_token_savings)


def effective_rate(priced: PricedUsage) -> str:
    if priced.total_cost is None or priced.total_tokens <= 0:
        return "n/a"
    rate = money((priced.total_cost / Decimal(priced.total_tokens)) * MILLION)
    return f"{format_cost(rate)}/MTok"


def context_summary(usage: Usage) -> str:
    parts = []
    if usage.context_used_percentage is not None:
        parts.append(f"{format_percent(usage.context_used_percentage)} used")
    if usage.context_remaining_percentage is not None:
        parts.append(f"{format_percent(usage.context_remaining_percentage)} left")
    if usage.context_window_size is not None:
        parts.append(f"{format_tokens(usage.context_window_size)} window")
    return " / ".join(parts)


def current_turn_summary(usage: Usage) -> str:
    if usage.current_input_tokens is None and usage.current_output_tokens is None:
        return ""
    return f"{format_tokens(usage.current_input_tokens or 0)} in / {format_tokens(usage.current_output_tokens or 0)} out"


def format_percent(value: Decimal | None) -> str:
    if value is None:
        return "n/a"
    rounded = value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return f"{rounded}%"


def _metadata_lines(label: str, value: str, width: int) -> list[str]:
    if not value:
        value = "-"
    prefix = f"{label:>{_LABEL_WIDTH}} : "
    available = width - len(prefix)
    chunks = _wrap_text(value, available)
    lines = [prefix + chunks[0]]
    continuation = " " * len(prefix)
    lines.extend(continuation + chunk for chunk in chunks[1:])
    return lines


def _wrap_text(value: str, width: int) -> list[str]:
    if len(value) <= width:
        return [value]
    chunks = []
    remaining = value
    while len(remaining) > width:
        split_at = remaining.rfind("/", 0, width + 1)
        if split_at < max(10, width // 3):
            split_at = width
        chunk = remaining[:split_at]
        chunks.append(chunk)
        remaining = remaining[split_at:]
    if remaining:
        chunks.append(remaining)
    return chunks or [""]


def _item_line(item: LineItem, tokens_only: bool, width: int) -> str:
    label_w, tok_w, rate_w, amt_w = _session_col_widths(tokens_only, width)
    if tokens_only:
        return f"{item.label:<{label_w}}{format_tokens(item.tokens):>{tok_w}}"
    rate = "n/a" if item.price is None else f"${item.price:.2f}"
    return f"{item.label:<{label_w}}{format_tokens(item.tokens):>{tok_w}}{rate:>{rate_w}}{format_cost(item.cost):>{amt_w}}"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print an invoice-style receipt for an LLM session.")
    parser.add_argument("client_arg", nargs="?", choices=("claude", "codex"), help="Usage source to read.")
    parser.add_argument("--client", choices=("claude", "codex"), help="Usage source to read.")
    parser.add_argument("--file", help="Read usage JSON from this file.")
    parser.add_argument("--session", help="Read a specific local session id or id prefix.")
    parser.add_argument("--list", action="store_true", help="List available sessions.")
    parser.add_argument("--date", help="Aggregate sessions for today, yesterday, or YYYY-MM-DD.")
    parser.add_argument("--since", help="Aggregate sessions at or after this date/time.")
    parser.add_argument("--until", help="Aggregate sessions before this date/time; YYYY-MM-DD includes the whole day.")
    parser.add_argument("--last", help="Aggregate recent sessions, for example 30d, 4w, or 1m.")
    parser.add_argument("--pricing", help=argparse.SUPPRESS)
    parser.add_argument("--verbose", action="store_true", help="Show context and pricing source details.")
    parser.add_argument("--ascii", dest="ascii_only", action="store_true", help="Use ASCII borders.")
    parser.add_argument("--tokens-only", action="store_true", help="Print token totals without requiring pricing.")
    parser.add_argument("--setup", action="store_true", help="Write bundled pricing.json to config dir for customization.")
    parser.add_argument("--update-pricing", action="store_true", help="Fetch latest pricing.json from remote update_url.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing pricing.json when using --setup.")
    return parser.parse_args(argv)


def selected_client(args: argparse.Namespace) -> str:
    return args.client or args.client_arg or "claude"


def read_payload(args: argparse.Namespace, input_text: str | None = None) -> dict[str, Any]:
    if input_text is not None:
        try:
            payload = json.loads(input_text)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"usage-receipt: invalid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise SystemExit("usage-receipt: input JSON must be an object")
        return payload

    client = selected_client(args)
    if args.file:
        if client == "codex" and str(args.file).endswith(".jsonl"):
            return load_codex_session(args.file)
        return _load_json_file(Path(args.file))
    if not sys.stdin.isatty():
        data = sys.stdin.read()
        if data.strip():
            try:
                payload = json.loads(data)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"usage-receipt: invalid JSON: {exc}") from exc
            if not isinstance(payload, dict):
                raise SystemExit("usage-receipt: input JSON must be an object")
            return payload
    if client == "codex":
        return load_codex_session(latest_codex_session())
    state_path = default_state_path()
    payload = _load_json_file(state_path)
    payload.setdefault("provider", "claude")
    payload.setdefault("source", str(state_path))
    payload.setdefault("session_id", state_path.stem)
    return payload


def is_range_query(args: argparse.Namespace) -> bool:
    return bool(args.date or args.since or args.until or args.last)


def validate_query_args(args: argparse.Namespace) -> None:
    if args.list and (args.session or args.file or is_range_query(args)):
        raise SystemExit("usage-receipt: --list cannot be combined with other query options")
    if args.session and is_range_query(args):
        raise SystemExit("usage-receipt: --session cannot be combined with range filters")
    if args.file and (args.session or is_range_query(args)):
        raise SystemExit("usage-receipt: --file cannot be combined with --session or range filters")


def run_session_query(args: argparse.Namespace, pricing: dict[str, Any]) -> str:
    client = selected_client(args)
    session_path = resolve_session_path(client, args.session)
    if client == "codex":
        payload = load_codex_session(session_path)
        usage = parse_usage(payload)
        priced = price_usage(usage, pricing, tokens_only=args.tokens_only)
        return render_receipt(priced, ascii_only=args.ascii_only, verbose=args.verbose)

    usages = load_claude_session(session_path)
    return render_usage_collection(
        usages,
        pricing,
        label=f"session {args.session}",
        label_name="SESSION",
        source=str(session_path),
        tokens_only=args.tokens_only,
        ascii_only=args.ascii_only,
        verbose=args.verbose,
    )


def run_range_query(args: argparse.Namespace, pricing: dict[str, Any]) -> str:
    client = selected_client(args)
    start, end, label = range_bounds(args)
    usages = collect_range_usages(client, start, end)
    source = default_codex_sessions_glob() if client == "codex" else default_claude_sessions_glob()
    return render_usage_collection(
        usages,
        pricing,
        label=label,
        label_name="RANGE",
        source=source,
        tokens_only=args.tokens_only,
        ascii_only=args.ascii_only,
        verbose=args.verbose,
        force_aggregate=True,
    )


def collect_range_usages(client: str, start: datetime, end: datetime) -> list[Usage]:
    usages: list[Usage] = []
    for session_path in iter_session_paths(client):
        if client == "codex":
            try:
                usage = parse_usage(load_codex_session(session_path))
            except SystemExit as exc:
                if "no Codex token_count event found" in str(exc):
                    continue
                raise
            usage_time = parse_datetime(usage.timestamp)
            if usage_time is not None and start <= usage_time < end:
                usages.append(usage)
            continue
        usages.extend(load_claude_session(session_path, start=start, end=end))
    if not usages:
        raise SystemExit(f"usage-receipt: no {client} usage found in requested range")
    return usages


def _load_json_file(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"usage-receipt: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("usage-receipt: input JSON must be an object")
    payload.setdefault("source", str(path))
    payload.setdefault("session_id", path.stem)
    return payload


def run_setup(force: bool = False) -> str:
    config_dir = user_config_dir()
    pricing_path = config_dir / "pricing.json"
    if pricing_path.exists() and not force:
        return f"usage-receipt: {pricing_path} already exists. Use --force to overwrite."
    config_dir.mkdir(parents=True, exist_ok=True)
    pricing_path.write_text(json.dumps(_BUNDLED_PRICING, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return f"usage-receipt: pricing written to {pricing_path}\nEdit this file to customize model pricing."


def run_update_pricing() -> str:
    current = load_pricing()
    url = current.get("update_url") or _BUNDLED_PRICING.get("update_url")
    if not url:
        raise SystemExit("usage-receipt: no update_url found in pricing config")

    try:
        with urlopen(url, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
    except Exception as exc:
        raise SystemExit(f"usage-receipt: failed to fetch {url}: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"usage-receipt: invalid JSON from remote: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("models"), list):
        raise SystemExit("usage-receipt: remote pricing format invalid")

    config_dir = user_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    pricing_path = config_dir / "pricing.json"
    old_date = current.get("updated_at", "unknown")
    new_date = data.get("updated_at", "unknown")
    old_count = len(current.get("models", []))
    new_count = len(data["models"])
    pricing_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return (
        f"usage-receipt: pricing updated ({old_date} -> {new_date}, {old_count} -> {new_count} models)\n"
        f"Saved to {pricing_path}"
    )


def run(argv: list[str] | None = None, input_text: str | None = None) -> str:
    args = parse_args(argv)
    validate_query_args(args)

    if args.setup:
        return run_setup(force=args.force)

    if args.update_pricing:
        return run_update_pricing()

    if args.list:
        return run_list_sessions(args)

    pricing_path = Path(args.pricing) if args.pricing else None
    tokens_only = getattr(args, "tokens_only", False)
    if tokens_only and pricing_path and not pricing_path.exists():
        pricing_path = None
    pricing = load_pricing(pricing_path)

    if args.session:
        return run_session_query(args, pricing)
    if is_range_query(args):
        return run_range_query(args, pricing)
    if args.file and selected_client(args) == "claude" and str(args.file).endswith(".jsonl"):
        usages = load_claude_session(args.file)
        return render_usage_collection(
            usages,
            pricing,
            label=f"file {args.file}",
            label_name="FILE",
            source=str(args.file),
            tokens_only=args.tokens_only,
            ascii_only=args.ascii_only,
            verbose=args.verbose,
        )

    payload = read_payload(args, input_text)
    usage = parse_usage(payload)
    priced = price_usage(usage, pricing, tokens_only=args.tokens_only)
    return render_receipt(priced, ascii_only=args.ascii_only, verbose=args.verbose)


def main() -> int:
    try:
        print(f"\n{run()}\n")
    except (FileNotFoundError, OSError) as exc:
        print(f"usage-receipt: {exc}", file=sys.stderr)
        return 1
    except SystemExit as exc:
        if exc.code:
            print(exc.code, file=sys.stderr)
            return 1
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
