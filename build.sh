#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
DIST_DIR="${SCRIPT_DIR}/dist"
SRC="${SCRIPT_DIR}/usage_receipt.py"
OUT="${DIST_DIR}/usage-receipt"

mkdir -p "$DIST_DIR"
cp "$SRC" "$OUT"
chmod +x "$OUT"

SIZE=$(wc -c < "$OUT" | tr -d ' ')
echo "Built: ${OUT} (${SIZE} bytes)"
