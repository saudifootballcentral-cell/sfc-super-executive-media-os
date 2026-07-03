#!/usr/bin/env bash
# ugs_deploy.sh — wraps the Unity Gaming Services CLI for Siraj.
# Used by networking_engineer ONLY when the GDD needs live-service features
# (Remote Config, Economy, Leaderboards, Cloud Code) — local-first law still
# applies: the game must run offline with bots/defaults without this.
#
# Install the CLI first (see https://services.docs.unity.com/guides/ugs-cli/
# -> Get Started -> Install the CLI for the current command for your OS).
#
# Auth — set in home/mulerun/.env (never print these):
#   UGS_CLI_PROJECT_ID=<your-project-id>
#   UGS_CLI_SERVICE_KEY_ID=<your-service-key-id>
#   UGS_CLI_SERVICE_SECRET_KEY=<your-service-secret-key>
# These three env vars are the CONFIRMED auth mechanism (Unity's own CI/CD
# docs use exactly this pattern for Cloud Build script hooks).
#
# Usage:
#   ./ugs_deploy.sh status
#   ./ugs_deploy.sh deploy ./unity-services/   # deploy service configs in a dir
set -euo pipefail
ENV_FILE="${SIRAJ_ENV:-$HOME/.env}"
[ -f "$ENV_FILE" ] && export $(grep -E '^UGS_CLI_' "$ENV_FILE" | xargs) 2>/dev/null || true

: "${UGS_CLI_PROJECT_ID:?Set UGS_CLI_PROJECT_ID in $ENV_FILE}"
: "${UGS_CLI_SERVICE_KEY_ID:?Set UGS_CLI_SERVICE_KEY_ID in $ENV_FILE}"
: "${UGS_CLI_SERVICE_SECRET_KEY:?Set UGS_CLI_SERVICE_SECRET_KEY in $ENV_FILE}"

command -v ugs >/dev/null || { echo "ugs CLI not found — install it first (see script header)."; exit 1; }

case "${1:-}" in
  status)  ugs status ;;
  env)     ugs env list ;;
  deploy)  [ -n "${2:-}" ] || { echo "usage: $0 deploy <config-dir>"; exit 1; }
           ugs deploy "$2" -j ;;
  version) ugs --version ;;
  *) echo "usage: $0 {status|env|deploy <dir>|version}"; exit 1 ;;
esac
