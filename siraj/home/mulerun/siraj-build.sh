#!/usr/bin/env bash
# siraj-build.sh — one command from asset (Meshy GLB or Blender task) to Unity.
#
#   Procedural (Blender factory task, same as dhai-build.sh):
#     siraj-build.sh tasks/my_arena.py MyArena Models/Arenas
#
#   Meshy AI asset (already downloaded GLB) -> refine -> Unity:
#     siraj-build.sh --meshy ~/meshy/downloads/Cannon.glb Cannon Models/Props
#     siraj-build.sh --meshy ~/meshy/downloads/Hero.glb Hero Characters --rig
#
#   Full text-to-Unity in one line:
#     siraj-build.sh --prompt "low poly pirate cannon" Cannon Models/Props
#
# Env: UNITY_PROJECT (default /home/mulerun/unity6/MyGame)
set -euo pipefail
BLENDER="${BLENDER:-/home/mulerun/blender/blender}"
SCRIPTS="$(cd "$(dirname "$0")/scripts" && pwd)"
EXPORTS="$HOME/blender/exports"
UNITY_PROJECT="${UNITY_PROJECT:-/home/mulerun/unity6/MyGame}"
MCP_PORT="${MCP_PORT:-8080}"

MODE="task"; RIG=""; POLYS=15000
if [[ "${1:-}" == "--meshy"  ]]; then MODE="meshy";  shift; fi
if [[ "${1:-}" == "--prompt" ]]; then MODE="prompt"; shift; fi

if [[ "$MODE" == "prompt" ]]; then
  PROMPT="$1"; NAME="$2"; CATEGORY="$3"; shift 3
  [[ "${1:-}" == "--rig" ]] && RIG="--rig"
  python3 "$HOME/meshy/meshy_client.py" text "$PROMPT" --name "$NAME" --polys $POLYS
  SRC="$HOME/meshy/downloads/$NAME.glb"
  MODE="meshy_run"
elif [[ "$MODE" == "meshy" ]]; then
  SRC="$1"; NAME="$2"; CATEGORY="$3"; shift 3
  [[ "${1:-}" == "--rig" ]] && RIG="--rig"
  MODE="meshy_run"
else
  TASK="$1"; NAME="$2"; CATEGORY="$3"; shift 3
fi

echo "== [Siraj] Blender stage =="
if [[ "$MODE" == "meshy_run" ]]; then
  timeout "${STAGE_TIMEOUT:-600}" "$BLENDER" --factory-startup -b -P "$SCRIPTS/meshy_refine.py" -- \
      "$SRC" "$NAME" "$POLYS" $RIG
else
  # Procedural task: reuse Dhai-style pipeline (task script builds + exports)
  timeout "${STAGE_TIMEOUT:-600}" "$BLENDER" --factory-startup -b -P "$TASK" -- "$NAME" "$@"
fi

FBX="$EXPORTS/$NAME.fbx"
[[ -f "$FBX" ]] || { echo "ERROR: $FBX not produced"; exit 1; }

echo "== [Siraj] Copy -> Unity =="
DEST="$UNITY_PROJECT/Assets/$CATEGORY"
mkdir -p "$DEST"
cp "$FBX" "$DEST/"
echo "   $DEST/$NAME.fbx"

echo "== [Siraj] Unity refresh (MCP) =="
curl -s -X POST "http://127.0.0.1:$MCP_PORT/tools/assets_refresh" \
     -H 'Content-Type: application/json' -d '{}' >/dev/null \
  && echo "   assets_refresh sent — watch logs/unity.log for '[Siraj] imported'" \
  || echo "   WARN: MCP not reachable — refresh Unity manually"
