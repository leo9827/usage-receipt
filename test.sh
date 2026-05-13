#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT_DIR="${SCRIPT_DIR}"
CLI="${ROOT_DIR}/usage-receipt"
TEST_ROOT="$(mktemp -d /tmp/usage-receipt-test.XXXXXX)"
FAILURES=0

cleanup() {
  rm -rf "${TEST_ROOT}"
}

trap cleanup EXIT

fail() {
  echo "FAIL: $1"
  FAILURES=$((FAILURES + 1))
}

pass() {
  echo "PASS: $1"
}

write_sonnet_payload() {
  local path="$1"
  cat >"${path}" <<EOF
{
  "model": {
    "display_name": "Claude Sonnet 4.6",
    "id": "claude-sonnet-4-6-20260217"
  },
  "workspace": {
    "current_dir": "${ROOT_DIR}"
  },
  "context_window": {
    "current_usage": {
      "input_tokens": 1234,
      "output_tokens": 56
    },
    "total_input_tokens": 2000000,
    "total_output_tokens": 100000,
    "context_window_size": 1000000,
    "used_percentage": 21.5
  }
}
EOF
}

write_codex_session_jsonl() {
  local path="$1"
  mkdir -p "$(dirname "${path}")"
  cat >"${path}" <<'EOF'
{"timestamp":"2026-05-13T03:00:00Z","type":"session_meta","payload":{"id":"019ehook","timestamp":"2026-05-13T03:00:00Z","cwd":"/Users/lihong98/dotfiles"}}
{"timestamp":"2026-05-13T03:00:01Z","type":"turn_context","payload":{"turn_id":"turn-1","cwd":"/Users/lihong98/dotfiles","model":"gpt-5.5"}}
{"timestamp":"2026-05-13T03:01:00Z","type":"event_msg","payload":{"type":"token_count","info":{"total_token_usage":{"input_tokens":1000,"cached_input_tokens":800,"output_tokens":200,"reasoning_output_tokens":50,"total_tokens":1200},"last_token_usage":{"input_tokens":100,"cached_input_tokens":80,"output_tokens":20,"reasoning_output_tokens":5,"total_tokens":120},"model_context_window":258400},"rate_limits":null}}
EOF
}

run_python_unit_tests() {
  local test_file="${TEST_ROOT}/test_usage_receipt_unit.py"
  cat >"${test_file}" <<'PY'
import json
import os
import pathlib
import tempfile
import unittest

import usage_receipt


class UsageReceiptUnitTests(unittest.TestCase):
    def setUp(self):
        self.repo = pathlib.Path(__import__("os").environ["USAGE_RECEIPT_REPO"])
        self.pricing = usage_receipt.load_pricing(self.repo / "pricing.json")
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def write_codex_session(self, session_file, session_id="019eaaaa-bbbb-7ccc-8ddd-eeeeeeeeeeee", rate_limits="default"):
        if rate_limits == "default":
            rate_limits = {
                "primary": {"used_percent": 25.0, "window_minutes": 300},
                "secondary": {"used_percent": 40.0, "window_minutes": 10080},
            }
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "timestamp": "2026-05-13T03:00:00Z",
                            "type": "session_meta",
                            "payload": {
                                "id": session_id,
                                "timestamp": "2026-05-13T03:00:00Z",
                                "cwd": "/Users/lihong98/dotfiles",
                            },
                        }
                    ),
                    json.dumps(
                        {
                            "timestamp": "2026-05-13T03:00:01Z",
                            "type": "turn_context",
                            "payload": {
                                "turn_id": "turn-1",
                                "cwd": "/Users/lihong98/dotfiles",
                                "model": "gpt-5.5",
                            },
                        }
                    ),
                    json.dumps(
                        {
                            "timestamp": "2026-05-13T03:01:00Z",
                            "type": "event_msg",
                            "payload": {
                                "type": "token_count",
                                "info": {
                                    "total_token_usage": {
                                        "input_tokens": 1000,
                                        "cached_input_tokens": 800,
                                        "output_tokens": 200,
                                        "reasoning_output_tokens": 50,
                                        "total_tokens": 1200,
                                    },
                                    "last_token_usage": {
                                        "input_tokens": 100,
                                        "cached_input_tokens": 80,
                                        "output_tokens": 20,
                                        "reasoning_output_tokens": 5,
                                        "total_tokens": 120,
                                    },
                                    "model_context_window": 258400,
                                },
                                "rate_limits": rate_limits,
                            },
                        }
                    ),
                ]
            ),
            encoding="utf-8",
        )

    def write_claude_session(self, session_file, session_id, model_id, timestamp, output_tokens=100):
        session_file.parent.mkdir(parents=True, exist_ok=True)
        rows = [
            {
                "type": "user",
                "sessionId": session_id,
                "timestamp": timestamp,
                "cwd": "/Users/lihong98/dotfiles",
                "message": {"role": "user", "content": "hello"},
            },
            {
                "type": "assistant",
                "sessionId": session_id,
                "timestamp": timestamp,
                "cwd": "/Users/lihong98/dotfiles",
                "message": {
                    "id": f"msg-{session_id}-1",
                    "role": "assistant",
                    "model": model_id,
                    "usage": {
                        "input_tokens": 1000,
                        "cache_read_input_tokens": 500,
                        "cache_creation_input_tokens": 200,
                        "cache_creation": {
                            "ephemeral_5m_input_tokens": 200,
                            "ephemeral_1h_input_tokens": 0,
                        },
                        "output_tokens": output_tokens,
                    },
                },
            },
            {
                "type": "assistant",
                "sessionId": session_id,
                "timestamp": timestamp,
                "cwd": "/Users/lihong98/dotfiles",
                "message": {
                    "id": f"msg-{session_id}-1",
                    "role": "assistant",
                    "model": model_id,
                    "usage": {
                        "input_tokens": 1000,
                        "cache_read_input_tokens": 500,
                        "cache_creation_input_tokens": 200,
                        "cache_creation": {
                            "ephemeral_5m_input_tokens": 200,
                            "ephemeral_1h_input_tokens": 0,
                        },
                        "output_tokens": output_tokens,
                    },
                },
            },
        ]
        session_file.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    def test_prefers_claude_total_tokens_over_current_usage(self):
        payload = {
            "model": {
                "display_name": "Claude Sonnet 4.6",
                "id": "claude-sonnet-4-6-20260217",
            },
            "workspace": {"current_dir": str(self.repo)},
            "context_window": {
                "current_usage": {"input_tokens": 1234, "output_tokens": 56},
                "total_input_tokens": 2_000_000,
                "total_output_tokens": 100_000,
                "context_window_size": 1_000_000,
                "used_percentage": 21.5,
            },
        }

        usage = usage_receipt.parse_usage(payload)
        priced = usage_receipt.price_usage(usage, self.pricing, tokens_only=False)

        self.assertEqual(usage.input_tokens, 2_000_000)
        self.assertEqual(usage.output_tokens, 100_000)
        self.assertEqual(priced.model_key, "claude-sonnet-4-6")
        self.assertEqual(str(priced.total_cost), "7.5000")

    def test_model_aliases_strip_snapshot_suffixes(self):
        self.assertEqual(
            usage_receipt.resolve_model_key("claude-opus-4-5-20251101", self.pricing),
            "claude-opus-4-5",
        )
        self.assertEqual(
            usage_receipt.resolve_model_key("mco-4", self.pricing),
            "claude-opus-4",
        )
        self.assertEqual(
            usage_receipt.resolve_model_key("mcs-5", self.pricing),
            "claude-sonnet-4",
        )
        self.assertEqual(
            usage_receipt.resolve_model_key("gpt-5.5-2026-04-23", self.pricing),
            "gpt-5.5",
        )

    def test_unknown_model_keeps_tokens_without_guessing_cost(self):
        payload = {
            "client": "codex",
            "model_id": "unknown-frontier-1",
            "model_display": "Unknown Frontier",
            "cwd": str(self.repo),
            "input_tokens": 10_000,
            "output_tokens": 1_000,
        }

        priced = usage_receipt.price_usage(
            usage_receipt.parse_usage(payload),
            self.pricing,
            tokens_only=False,
        )

        self.assertIsNone(priced.total_cost)
        self.assertEqual(priced.total_tokens, 11_000)

    def test_cache_write_tokens_are_charged_when_present(self):
        payload = {
            "model_id": "claude-sonnet-4-6",
            "model_display": "Claude Sonnet 4.6",
            "input_tokens": 1_000_000,
            "output_tokens": 0,
            "cache_read_tokens": 1_000_000,
            "cache_write_5m_tokens": 1_000_000,
        }

        priced = usage_receipt.price_usage(
            usage_receipt.parse_usage(payload),
            self.pricing,
            tokens_only=False,
        )

        self.assertEqual(str(priced.total_cost), "7.0500")
        self.assertEqual(priced.total_tokens, 3_000_000)

    def test_opus_4_display_name_resolves_to_legacy_pricing(self):
        payload = {
            "client": "claude-code",
            "model_display": "Opus 4",
            "input_tokens": 145_152,
            "output_tokens": 100_014,
            "cache_read_tokens": 144_915,
            "cache_write_5m_tokens": 88,
        }

        priced = usage_receipt.price_usage(
            usage_receipt.parse_usage(payload),
            self.pricing,
            tokens_only=False,
        )

        self.assertEqual(priced.model_key, "claude-opus-4")
        self.assertEqual(str(priced.total_cost), "9.8974")

    def test_receipt_uses_thermal_paper_sections(self):
        payload = {
            "client": "claude-code",
            "model_display": "Opus 4",
            "cwd": "/Users/lihong98/Workspace/jdcloud/src/jd.com/lb/jstack-lb-server",
            "timestamp": "2026-05-13T03:02:00Z",
            "input_tokens": 145_152,
            "output_tokens": 100_014,
            "cache_read_tokens": 144_915,
            "cache_write_5m_tokens": 88,
            "current_input_tokens": 878,
            "current_output_tokens": 14_626,
            "context_window": {
                "context_window_size": 200_000,
                "used_percentage": 42.2,
                "remaining_percentage": 57.8,
            },
        }

        priced = usage_receipt.price_usage(
            usage_receipt.parse_usage(payload),
            self.pricing,
            tokens_only=False,
        )
        output = usage_receipt.render_receipt(priced)

        self.assertIn("LLM TOKEN MART", output)
        self.assertIn("ITEM", output)
        self.assertIn("RATE/MTOK", output)
        self.assertIn("SUBTOTAL", output)
        self.assertIn("CACHE HIT", output)
        self.assertIn("CACHE SAVED", output)
        self.assertIn("EFFECTIVE RATE", output)
        self.assertIn("CONTEXT", output)
        self.assertIn("CURRENT TURN", output)
        self.assertIn("$9.8974", output)
        self.assertLessEqual(max(len(line) for line in output.splitlines()), 48)

    def test_missing_pricing_file_fails_unless_tokens_only(self):
        payload = {
            "model_id": "claude-sonnet-4-6",
            "input_tokens": 1,
            "output_tokens": 1,
        }
        missing = pathlib.Path(tempfile.gettempdir()) / "usage-receipt-missing-pricing.json"

        with self.assertRaises(SystemExit):
            usage_receipt.run(["--pricing", str(missing)], input_text=json.dumps(payload))

        output = usage_receipt.run(
            ["--pricing", str(missing), "--tokens-only", "--ascii"],
            input_text=json.dumps(payload),
        )
        self.assertIn("TOTAL", output)
        self.assertNotIn("n/a", output)
        self.assertNotIn("RATE/MTOK", output)
        self.assertNotIn("SUBTOTAL", output)

    def test_tokens_only_receipt_hides_price_columns(self):
        payload = {
            "client": "claude-code",
            "model_display": "Opus 4",
            "input_tokens": 886,
            "output_tokens": 18_409,
            "cache_read_tokens": 91_666,
            "cache_write_5m_tokens": 787,
            "current_input_tokens": 1,
            "current_output_tokens": 461,
            "context_window": {
                "context_window_size": 200_000,
                "used_percentage": 48.0,
                "remaining_percentage": 52.0,
            },
        }

        output = usage_receipt.run(
            ["--tokens-only", "--ascii"],
            input_text=json.dumps(payload),
        )

        self.assertIn("TOKENS ONLY", output)
        self.assertIn("TOTAL TOKENS", output)
        self.assertIn("CONTEXT", output)
        self.assertIn("CURRENT TURN", output)
        self.assertNotIn("n/a", output)
        self.assertNotIn("RATE/MTOK", output)
        self.assertNotIn("AMOUNT", output)
        self.assertNotIn("SUBTOTAL", output)

    def test_receipt_header_identifies_provider_and_source(self):
        payload = {
            "provider": "claude",
            "client": "claude-code",
            "session_id": "claude-latest",
            "source": "/tmp/claude-latest.json",
            "model_display": "Opus 4",
            "input_tokens": 1,
            "output_tokens": 1,
        }

        output = usage_receipt.run(["--ascii", "--verbose"], input_text=json.dumps(payload))

        self.assertIn("PROVIDER : Anthropic / claude-code", output)
        self.assertIn("SESSION : claude-latest", output)
        self.assertIn("SOURCE : /tmp/claude-latest.json", output)

    def test_codex_session_jsonl_maps_latest_token_count(self):
        session_file = self.tmp / "codex" / "rollout-2026-05-13T03-00-00-019eaaaa.jsonl"
        self.write_codex_session(session_file)

        payload = usage_receipt.load_codex_session(session_file)
        usage = usage_receipt.parse_usage(payload)

        self.assertEqual(usage.provider, "codex")
        self.assertEqual(usage.client, "codex")
        self.assertEqual(usage.model_id, "gpt-5.5")
        self.assertEqual(usage.input_tokens, 200)
        self.assertEqual(usage.cache_read_tokens, 800)
        self.assertEqual(usage.output_tokens, 200)
        self.assertEqual(usage.reasoning_output_tokens, 50)
        self.assertEqual(usage.current_input_tokens, 20)
        self.assertEqual(usage.current_output_tokens, 20)
        self.assertEqual(usage.context_window_size, 258400)
        self.assertEqual(usage.session_id, "019eaaaa-bbbb-7ccc-8ddd-eeeeeeeeeeee")

        output = usage_receipt.run(["codex", "--file", str(session_file), "--ascii"])
        self.assertIn("PROVIDER : OpenAI / codex", output)
        self.assertIn("Reasoning out", output)
        self.assertIn("5H LIMIT", output)
        self.assertIn("WEEKLY LIMIT", output)

    def test_codex_session_allows_null_rate_limits(self):
        session_file = self.tmp / "codex" / "rollout-null-rate-limits.jsonl"
        self.write_codex_session(session_file, rate_limits=None)

        output = usage_receipt.run(["codex", "--file", str(session_file), "--ascii"])

        self.assertIn("PROVIDER : OpenAI / codex", output)
        self.assertIn("Reasoning out", output)
        self.assertNotIn("5H LIMIT", output)
        self.assertNotIn("WEEKLY LIMIT", output)

    def test_codex_session_can_be_selected_by_session_id_prefix(self):
        session_file = self.tmp / "codex" / "2026" / "05" / "13" / "rollout-session.jsonl"
        self.write_codex_session(session_file)
        os.environ["USAGE_RECEIPT_CODEX_SESSIONS_GLOB"] = str(self.tmp / "codex" / "**" / "*.jsonl")
        try:
            output = usage_receipt.run(["codex", "--session", "019eaaaa", "--ascii"])
        finally:
            os.environ.pop("USAGE_RECEIPT_CODEX_SESSIONS_GLOB", None)

        self.assertIn("SESSION : 019eaaaa-bbbb-7ccc-8ddd-eeeeeeeeeeee", output)

    def test_codex_range_skips_sessions_without_token_counts(self):
        root = self.tmp / "codex" / "2026" / "05" / "13"
        self.write_codex_session(root / "rollout-good.jsonl")
        (root / "rollout-empty.jsonl").write_text(
            json.dumps(
                {
                    "timestamp": "2026-05-13T02:00:00Z",
                    "type": "session_meta",
                    "payload": {
                        "id": "019eempty",
                        "timestamp": "2026-05-13T02:00:00Z",
                        "cwd": "/Users/lihong98/dotfiles",
                    },
                }
            ),
            encoding="utf-8",
        )
        os.environ["USAGE_RECEIPT_CODEX_SESSIONS_GLOB"] = str(self.tmp / "codex" / "**" / "*.jsonl")
        try:
            output = usage_receipt.run(["codex", "--date", "2026-05-13", "--ascii"])
        finally:
            os.environ.pop("USAGE_RECEIPT_CODEX_SESSIONS_GLOB", None)

        self.assertIn("USAGE RANGE RECEIPT", output)
        self.assertIn("SESSIONS : 1", output)
        self.assertIn("gpt-5.5", output)

    def test_claude_session_jsonl_dedupes_repeated_message_usage(self):
        session_file = self.tmp / "claude" / "projects" / "dotfiles" / "claude-session-1.jsonl"
        self.write_claude_session(
            session_file,
            "claude-session-1",
            "claude-sonnet-4-6",
            "2026-05-13T03:00:00Z",
        )

        usages = usage_receipt.load_claude_session(session_file)

        self.assertEqual(len(usages), 1)
        self.assertEqual(usages[0].session_id, "claude-session-1")
        self.assertEqual(usages[0].input_tokens, 1000)
        self.assertEqual(usages[0].cache_read_tokens, 500)
        self.assertEqual(usages[0].cache_write_5m_tokens, 200)
        self.assertEqual(usages[0].output_tokens, 100)

    def test_claude_range_receipt_groups_by_model(self):
        root = self.tmp / "claude" / "projects" / "dotfiles"
        self.write_claude_session(
            root / "claude-session-1.jsonl",
            "claude-session-1",
            "claude-sonnet-4-6",
            "2026-05-13T03:00:00Z",
            output_tokens=100,
        )
        self.write_claude_session(
            root / "claude-session-2.jsonl",
            "claude-session-2",
            "claude-opus-4",
            "2026-05-13T04:00:00Z",
            output_tokens=200,
        )
        os.environ["USAGE_RECEIPT_CLAUDE_SESSIONS_GLOB"] = str(root / "*.jsonl")
        try:
            output = usage_receipt.run(["claude", "--date", "2026-05-13", "--ascii"])
        finally:
            os.environ.pop("USAGE_RECEIPT_CLAUDE_SESSIONS_GLOB", None)

        self.assertIn("USAGE RANGE RECEIPT", output)
        self.assertIn("PROVIDER : Anthropic / aggregate", output)
        self.assertIn("MODEL GROUPS", output)
        self.assertIn("claude-sonnet-4-6", output)
        self.assertIn("claude-opus-4", output)
        self.assertIn("SESSIONS : 2", output)
        self.assertIn("SUBTOTAL", output)

    def test_list_claude_sessions(self):
        root = self.tmp / "claude" / "projects" / "dotfiles"
        self.write_claude_session(
            root / "session-aaa.jsonl",
            "session-aaa",
            "claude-sonnet-4-6",
            "2026-05-13T03:00:00Z",
        )
        self.write_claude_session(
            root / "session-bbb.jsonl",
            "session-bbb",
            "claude-opus-4",
            "2026-05-13T04:00:00Z",
        )
        os.environ["USAGE_RECEIPT_CLAUDE_SESSIONS_GLOB"] = str(root / "*.jsonl")
        try:
            output = usage_receipt.run(["claude", "--list"])
        finally:
            os.environ.pop("USAGE_RECEIPT_CLAUDE_SESSIONS_GLOB", None)

        self.assertIn("CLAUDE SESSIONS", output)
        self.assertIn("session-aaa", output)
        self.assertIn("session-bbb", output)
        self.assertIn("TOTAL: 2 sessions", output)

    def test_list_codex_sessions(self):
        root = self.tmp / "codex" / "2026" / "05" / "13"
        self.write_codex_session(
            root / "rollout-a.jsonl",
            session_id="019eaaaa-aaaa-7ccc-8ddd-eeeeeeeeeeee",
        )
        self.write_codex_session(
            root / "rollout-b.jsonl",
            session_id="019ebbbb-bbbb-7ccc-8ddd-eeeeeeeeeeee",
        )
        os.environ["USAGE_RECEIPT_CODEX_SESSIONS_GLOB"] = str(self.tmp / "codex" / "**" / "*.jsonl")
        try:
            output = usage_receipt.run(["codex", "--list"])
        finally:
            os.environ.pop("USAGE_RECEIPT_CODEX_SESSIONS_GLOB", None)

        self.assertIn("CODEX SESSIONS", output)
        self.assertIn("019eaaaa", output)
        self.assertIn("019ebbbb", output)
        self.assertIn("TOTAL: 2 sessions", output)

    def test_list_cannot_combine_with_session(self):
        with self.assertRaises(SystemExit):
            usage_receipt.run(["--list", "--session", "abc"])


if __name__ == "__main__":
    unittest.main()
PY

  USAGE_RECEIPT_REPO="${ROOT_DIR}" \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${ROOT_DIR}" \
    python3 -m unittest discover -s "${TEST_ROOT}" -p "$(basename "${test_file}")" -v
}

test_setup_installs_into_temp_home() {
  local home="${TEST_ROOT}/home"
  local bin_dir="${home}/.local/bin"
  mkdir -p "${home}"

  HOME="${home}" \
  SHELL="/bin/zsh" \
  PYTHON_BIN="/usr/bin/python3" \
  PATH="${bin_dir}:${PATH}" \
    "${ROOT_DIR}/setup.sh" --bin-dir "${bin_dir}" --no-path-update

  [[ -L "${bin_dir}/usage-receipt" ]] || fail "setup should create usage-receipt symlink"
  [[ "$(readlink "${bin_dir}/usage-receipt")" == "${CLI}" ]] ||
    fail "usage-receipt symlink should point at repo wrapper"
  [[ -x "${CLI}" ]] || fail "repo wrapper should be executable"
  [[ -x "${ROOT_DIR}/session-end-hook.sh" ]] || fail "hook script should be executable"
  PYTHONDONTWRITEBYTECODE=1 "${bin_dir}/usage-receipt" --help >/dev/null ||
    fail "installed usage-receipt command should run through symlink"

  HOME_FOR_CHECK="${home}" REPO_FOR_CHECK="${ROOT_DIR}" python3 - <<'PY'
import json
import os
import pathlib
import sys

home = pathlib.Path(os.environ["HOME_FOR_CHECK"])
repo = pathlib.Path(os.environ["REPO_FOR_CHECK"])
hook = repo / "session-end-hook.sh"

claude_settings = json.loads((home / ".claude" / "settings.json").read_text())
claude_stop = claude_settings["hooks"]["SessionEnd"]
claude_commands = [
    hook_entry["command"]
    for group in claude_stop
    for hook_entry in group.get("hooks", [])
]
if f"'{hook}' claude" not in claude_commands:
    sys.exit("Claude SessionEnd hook was not installed")
PY
  if [[ $? -eq 0 ]]; then
    pass "setup installs command and Claude hook into temp home"
  else
    fail "setup should install command and Claude hook into temp home"
  fi
}

test_ascii_receipt_renders_costs() {
  local payload="${TEST_ROOT}/sonnet.json"
  local output
  write_sonnet_payload "${payload}"

  output="$("${CLI}" --file "${payload}" --ascii)"

  [[ "${output}" == *"LLM TOKEN MART"* ]] || fail "receipt should include title"
  [[ "${output}" == *"Input"* && "${output}" == *"\$6.0000"* ]] ||
    fail "receipt should include input line cost"
  [[ "${output}" == *"Output"* && "${output}" == *"\$1.5000"* ]] ||
    fail "receipt should include output line cost"
  [[ "${output}" == *"Cache read"* && "${output}" == *"n/a"* ]] ||
    fail "missing cache fields should render cache cost as n/a"
  [[ "${output}" == *"SUBTOTAL"* && "${output}" == *"\$7.5000"* ]] ||
    fail "receipt should include total cost"
  if RECEIPT_OUTPUT="${output}" python3 - <<'PY'
import os
text = os.environ["RECEIPT_OUTPUT"]
raise SystemExit(0 if "┌" not in text and "│" not in text else 1)
PY
  then
    pass "ascii receipt renders costs"
  else
    fail "ascii receipt should not include unicode borders"
  fi
}

test_no_input_reads_latest_claude_state() {
  local payload="${TEST_ROOT}/state/llm-usage-receipt/claude-latest.json"
  local output
  mkdir -p "$(dirname "${payload}")"
  write_sonnet_payload "${payload}"

  output="$(
    USAGE_RECEIPT_STATE="${payload}" "${CLI}" --ascii
  )"

  [[ "${output}" == *"Claude Sonnet 4.6"* && "${output}" == *"\$7.5000"* ]] ||
    fail "command without stdin/file should read latest Claude state"
  pass "command without stdin/file reads latest Claude state"
}

test_codex_wrapper_prints_receipt_after_exit() {
  local fake_bin="${TEST_ROOT}/fake-bin"
  local codex_log="${TEST_ROOT}/codex.log"
  local output
  local status

  mkdir -p "${fake_bin}"
  cat >"${fake_bin}/codex" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "${CODEX_LOG}"
printf 'FAKE-CODEX:%s\n' "$*"
exit 23
EOF
  chmod +x "${fake_bin}/codex"

  set +e
  output="$(
    CODEX_LOG="${codex_log}" PATH="${fake_bin}:${PATH}" zsh -f -c '
      codex_should_skip_receipt() {
        local first_arg="${1:-}"

        case "$first_arg" in
          -h|--help|--version|help|completion|login|logout|features|update|mcp|mcp-server|app-server|remote-control|app)
            return 0
            ;;
        esac

        return 1
      }

      codex() {
        if codex_should_skip_receipt "${1:-}"; then
          command codex "$@"
          return $?
        fi

        local exit_status=0
        command codex "$@"
        exit_status=$?

        usage-receipt codex --ascii || true

        return $exit_status
      }

      usage-receipt() { printf "RECEIPT:%s\n" "$*"; }
      codex
    '
  )"
  status=$?
  set -e

  if [[ "${status}" -ne 23 ]]; then
    fail "codex wrapper should preserve the command exit status"
    return
  fi

  if [[ "${output}" == *"FAKE-CODEX:"*"RECEIPT:codex --ascii"* ]]; then
    pass "codex wrapper prints receipt after the command exits"
  else
    fail "codex wrapper should print receipt after command output"
  fi
}

test_hook_outputs_to_stdout_without_tty() {
  local session="${TEST_ROOT}/codex-session.jsonl"
  local output
  write_codex_session_jsonl "${session}"

  output="$(printf '{"transcript_path":"%s"}' "${session}" | "${ROOT_DIR}/session-end-hook.sh" codex)"

  if [[ "${output}" == *"LLM TOKEN MART"* && "${output}" == *"OpenAI / codex"* ]]; then
    pass "hook prints receipt without tty"
  else
    fail "hook should print receipt to stdout when tty output is unavailable"
  fi
}

echo "=== usage receipt tests ==="

run_python_unit_tests
test_setup_installs_into_temp_home
test_ascii_receipt_renders_costs
test_no_input_reads_latest_claude_state
test_codex_wrapper_prints_receipt_after_exit
test_hook_outputs_to_stdout_without_tty

if (( FAILURES > 0 )); then
  echo "Tests failed: ${FAILURES}"
  exit 1
fi

echo "All usage receipt tests passed."
