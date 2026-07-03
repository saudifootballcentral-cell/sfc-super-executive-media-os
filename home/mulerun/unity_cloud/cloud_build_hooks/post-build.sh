#!/usr/bin/env bash
# post-build.sh — Unity Cloud Build post-build script hook.
#
# CONFIRMED mechanism (Unity's own docs): Dashboard -> DevOps -> Cloud Build
# -> Configurations -> your config -> Advanced Settings -> set this file's
# path as the "post-build" script hook. Cloud Build runs it after every
# build with the same UGS_CLI_* env vars available (set them in the same
# Advanced Settings panel).
#
# This logs the build result back into Siraj's local memory so
# build_release_director's next /siraj-boot sees it, even though the build
# itself ran on Unity's infrastructure, not the local VM.
#
# Cloud Build exposes standard env vars during the hook (exact names depend
# on your Cloud Build version — check your config's env var reference in
# the Dashboard). Common ones historically include $UNITY_CLOUD_BUILD_TARGET_ID
# and a build-number var; adjust the two lines below to match what your
# Dashboard actually exposes before relying on this.
set -uo pipefail
STATUS="${BUILD_STATUS:-unknown}"
TARGET="${UNITY_CLOUD_BUILD_TARGET_ID:-unknown-target}"
BUILD_NO="${BUILD_NUMBER:-unknown}"

python3 "$(dirname "$0")/../../../../os/engine/memory.py" log versions \
  "{\"event\":\"cloud_build\",\"status\":\"$STATUS\",\"target\":\"$TARGET\",\"build_number\":\"$BUILD_NO\"}" \
  || echo "[siraj] warning: could not log cloud build result to memory.py"
