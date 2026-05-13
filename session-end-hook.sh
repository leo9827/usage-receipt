#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
CLIENT="${1:-claude}"
RECEIPT="${SCRIPT_DIR}/usage-receipt"

INPUT=$(cat 2>/dev/null || true)
[ -z "$INPUT" ] && exit 0

SESSION_ID=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('session_id') or d.get('sessionId') or d.get('id') or '')
except Exception:
    pass
" 2>/dev/null || true)

TRANSCRIPT_PATH=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('transcript_path') or d.get('transcriptPath') or '')
except Exception:
    pass
" 2>/dev/null || true)

if [ -n "$TRANSCRIPT_PATH" ] && [ -f "$TRANSCRIPT_PATH" ]; then
    OUTPUT=$("$RECEIPT" "$CLIENT" --ascii --file "$TRANSCRIPT_PATH" 2>/dev/null) || true
elif [ -n "$SESSION_ID" ]; then
    OUTPUT=$("$RECEIPT" "$CLIENT" --ascii --session "$SESSION_ID" 2>/dev/null) || true
else
    exit 0
fi

if [ -n "$OUTPUT" ]; then
    if ! { printf '\n%s\n\n' "$OUTPUT" > /dev/tty; } 2>/dev/null; then
        printf '\n%s\n\n' "$OUTPUT"
    fi
fi
