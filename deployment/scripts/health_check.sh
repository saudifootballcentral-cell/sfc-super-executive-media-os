#!/usr/bin/env bash
# SFC Super Executive Media OS — health check
set -euo pipefail

python - <<'EOF'
import sys
sys.path.insert(0, "src")
from sfc.graph.graph import build_graph
from sfc.core.constitution import load_constitution
from sfc.memory import GlobalMemory, EpisodicMemory

graph = build_graph()
_ = load_constitution()
_ = GlobalMemory()
_ = EpisodicMemory()
print("SFC Media OS health check: OK")
EOF
