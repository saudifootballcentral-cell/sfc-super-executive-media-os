#!/usr/bin/env bash
# guard-secrets.sh — PreToolUse hook on Bash: blocks commands likely to print
# or exfiltrate MESHY_API_KEY / Unity service credentials / .env contents.
#
# Second line of defense — the first is never pasting a key into chat.
# Exit 2 = block the tool call and surface the message to Claude.
# If this over-blocks a legitimate command, tune BLOCK_PATTERNS below
# (see INSTALL_CLAUDE_CODE.md troubleshooting).
set -uo pipefail

INPUT="$(cat)"
CMD="$(printf '%s' "$INPUT" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
print(d.get("tool_input", {}).get("command", ""))
' 2>/dev/null)"

[ -z "$CMD" ] && exit 0

BLOCK_PATTERNS=(
  # printing the secrets by name
  'echo[^|;&]*MESHY_API_KEY'
  'printf[^|;&]*MESHY_API_KEY'
  'echo[^|;&]*UGS_CLI_SERVICE'
  'printf[^|;&]*UGS_CLI_SERVICE'
  # dumping env files or the whole environment
  '\b(cat|less|more|head|tail|bat|strings|vi|vim|nano)\b[^|;&]*\.env\b'
  '^\s*(env|printenv)\s*($|\|)'
  'printenv[^|;&]*(MESHY|UGS)'
  # copying .env into tracked/shared locations
  '\b(cp|mv|scp|rsync)\b[^|;&]*\.env\b'
  'git\s+add[^|;&]*\.env\b'
  # grep that would print the value
  'grep[^|;&]*(MESHY_API_KEY|UGS_CLI_SERVICE)[^|;&]*\.env(?!.*cut)'
)

# shipping a key anywhere but its own API is exfiltration
if printf '%s' "$CMD" | grep -qPi '\b(curl|wget)\b[^;&]*(MESHY_API_KEY|UGS_CLI_SERVICE)' 2>/dev/null \
   && ! printf '%s' "$CMD" | grep -qi 'api\.meshy\.ai'; then
  echo "BLOCKED by guard-secrets.sh: curl/wget carrying a secret to a non-Meshy host." >&2
  exit 2
fi

for pat in "${BLOCK_PATTERNS[@]}"; do
  if printf '%s' "$CMD" | grep -qPi -- "$pat" 2>/dev/null; then
    echo "BLOCKED by guard-secrets.sh: command matches secret-exposure pattern ($pat)." >&2
    echo "MESHY_API_KEY and Unity service credentials live in home/mulerun/.env only —" >&2
    echo "never printed, never transmitted, never copied into tracked files." >&2
    echo "Legitimate need? Adjust BLOCK_PATTERNS in .claude/hooks/guard-secrets.sh." >&2
    exit 2
  fi
done
exit 0
