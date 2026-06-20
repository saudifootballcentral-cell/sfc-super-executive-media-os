#!/usr/bin/env bash
# SFC Super Executive Media OS — start script
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "========================================"
echo "SFC Super Executive Media OS v1.0.0"
echo "========================================"

# Validate environment
if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
    echo "⚠  ANTHROPIC_API_KEY not set — Claude fallback will be used"
fi

# Install deps if not in a container
if [[ "${SFC_ENVIRONMENT:-development}" == "development" ]]; then
    pip install -q -e "$ROOT[dev]"
fi

# Run demo or custom scenario
SCENARIO="${1:-transfer}"
echo "Running scenario: $SCENARIO"
echo ""

cd "$ROOT"
python scripts/run_demo.py --scenario "$SCENARIO"
