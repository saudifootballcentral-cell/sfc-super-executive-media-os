#!/usr/bin/env bash
# siraj-activate.sh — تفعيل سراج بأمر واحد على السيرفر.
# ينسخ الملفات، يفحص المثلث كاملاً (Meshy/Blender/Unity/MCP)،
# يشغّل self-test للمحركات، ويسجّل الجاهزية في الذاكرة.
#
#   ./siraj-activate.sh              # تفعيل كامل
#   ./siraj-activate.sh check        # فحص الجاهزية فقط (بدون نسخ)
set -uo pipefail
PKG="$(cd "$(dirname "$0")" && pwd)"
HOME_DIR="${SIRAJ_HOME:-/home/mulerun}"
OS_DIR="$HOME_DIR/siraj-os"
PASS=0; FAIL=0; WARN=0
ok()   { echo "  ✅ $1"; PASS=$((PASS+1)); }
bad()  { echo "  ❌ $1"; FAIL=$((FAIL+1)); }
warn() { echo "  ⚠️  $1"; WARN=$((WARN+1)); }

install() {
  echo "== [1/3] تثبيت الملفات =="
  mkdir -p "$HOME_DIR"
  cp -r "$PKG/home/mulerun/." "$HOME_DIR/" 2>/dev/null || true
  mkdir -p "$OS_DIR"
  cp -r "$PKG/os/." "$OS_DIR/"
  cp -r "$PKG/workspace" "$OS_DIR/"
  chmod +x "$HOME_DIR/siraj-build.sh" "$HOME_DIR/meshy/meshy_client.py" 2>/dev/null
  mkdir -p "$HOME_DIR/meshy/downloads" "$HOME_DIR/blender/exports"
  ok "الملفات في $HOME_DIR و $OS_DIR"
}

check() {
  echo "== [2/3] فحص المثلث =="
  # Python
  command -v python3 >/dev/null && ok "python3 $(python3 -V 2>&1 | cut -d' ' -f2)" || bad "python3 غير موجود"
  # Meshy
  KEY="${MESHY_API_KEY:-$(grep -s '^MESHY_API_KEY=' "$HOME_DIR/.env" | cut -d= -f2)}"
  if [ -n "${KEY:-}" ]; then
    ok "MESHY_API_KEY موجود"
    CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 \
        -H "Authorization: Bearer $KEY" https://api.meshy.ai/openapi/v2/text-to-3d 2>/dev/null || echo 000)
    case "$CODE" in
      200|400|405) ok "Meshy API يستجيب (HTTP $CODE)" ;;
      401)         bad "Meshy: المفتاح مرفوض (401)" ;;
      000)         warn "Meshy: لا يوجد اتصال شبكة من هنا — أعد الفحص على السيرفر" ;;
      *)           warn "Meshy: استجابة غير متوقعة HTTP $CODE — راجع docs.meshy.ai" ;;
    esac
  else
    bad "MESHY_API_KEY غير موجود — أضفه: echo 'MESHY_API_KEY=msy_xxx' >> $HOME_DIR/.env && chmod 600 $HOME_DIR/.env"
  fi
  # Blender
  BL="${BLENDER:-$HOME_DIR/blender/blender}"
  if [ -x "$BL" ]; then
    ok "Blender: $("$BL" --version 2>/dev/null | head -1)"
  else
    bad "Blender غير موجود في $BL"
  fi
  # Unity + مشروع
  # درس ضي: lockfiles صفرية من انهيار سابق تمنع إقلاع Unity بصمت
  ZLOCKS=$(find "$HOME_DIR/unity6" -name "*.lock" -o -name "UnityLockfile" 2>/dev/null | xargs -r ls -la 2>/dev/null | awk '$5==0{print $NF}')
  if [ -n "${ZLOCKS:-}" ]; then
    echo "$ZLOCKS" | xargs -r rm -f && ok "حُذفت lockfiles صفرية كانت ستمنع إقلاع Unity"
  fi
  [ -x "$HOME_DIR/unity6/Editor/Unity" ] && ok "Unity Editor موجود" || bad "Unity Editor غير موجود في $HOME_DIR/unity6/Editor/Unity"
  # فحص الترخيص (طريقة ضي المثبتة: .alf/.ulf مربوط بالجهاز)
  if [ -f "$HOME/.local/share/unity3d/Unity/Unity_lic.ulf" ] || [ -f "/usr/share/unity3d/Unity/Unity_lic.ulf" ]; then
    ok "ترخيص يونيتي مفعَّل (ملف .ulf موجود)"
  else
    warn "لا ترخيص يونيتي — شغّل: home/mulerun/unity_cloud/unity_license.sh request (دورة .alf/.ulf، مرة لكل VM)"
  fi
  [ -d "$HOME_DIR/unity6/MyGame/Assets" ] && ok "مشروع Unity موجود" || bad "مشروع Unity غير موجود"
  [ -f "$HOME_DIR/unity6/MyGame/Assets/Editor/SirajBridge.cs" ] && ok "SirajBridge.cs في المشروع" || warn "SirajBridge.cs لم يُنسخ بعد للمشروع"
  # MCP + Xvfb
  if curl -s --max-time 3 "http://127.0.0.1:${MCP_PORT:-8080}/" >/dev/null 2>&1; then
    ok "MCP يستجيب على :${MCP_PORT:-8080}"
  else
    warn "MCP لا يستجيب — شغّل: $HOME_DIR/start-dhai.sh"
  fi
  pgrep -f "Xvfb.*:99" >/dev/null 2>&1 && ok "Xvfb :99 يعمل" || warn "Xvfb :99 متوقف — سيشغّله start-dhai.sh"

  echo "== [3/3] Self-test لمحركات النظام =="
  cd "$OS_DIR" 2>/dev/null || cd "$PKG/os"
  python3 -m py_compile engine/*.py 2>/dev/null && ok "المحركات تُجمَّع بدون أخطاء" || bad "خطأ تجميع في المحركات"
  R=$(python3 engine/asset_router.py route '{"name":"__selftest","type":"prop","exact_dims":true}' 2>/dev/null | python3 -c 'import sys,json;print(json.load(sys.stdin)["route"])' 2>/dev/null)
  [ "$R" = "procedural" ] && ok "Asset Router يقرر بشكل صحيح" || bad "Asset Router فشل"
  python3 engine/memory.py boot >/dev/null 2>&1 && ok "نظام الذاكرة يعمل" || bad "نظام الذاكرة فشل"
  python3 engine/orchestrator.py status >/dev/null 2>&1 && ok "المنسّق (Orchestrator) يعمل" || bad "المنسّق فشل"
}

report() {
  echo
  echo "================ تقرير الجاهزية ================"
  echo "  نجح: $PASS  |  تحذير: $WARN  |  فشل: $FAIL"
  if [ "$FAIL" -eq 0 ]; then
    STATUS="READY"
    echo "  🟢 سراج جاهز. ابدأ مشروعاً:"
    echo "     cd $OS_DIR && python3 engine/orchestrator.py new \"<اسم اللعبة>\""
    echo "     python3 engine/orchestrator.py task '{\"stage\":\"game_idea\",\"title\":\"تحليل الفكرة\",\"priority\":9}'"
    echo "     python3 engine/orchestrator.py next"
  else
    STATUS="BLOCKED"
    echo "  🔴 أصلح عناصر ❌ أعلاه ثم أعد: ./siraj-activate.sh check"
  fi
  cd "$OS_DIR" 2>/dev/null || cd "$PKG/os"
  python3 engine/memory.py log versions \
    "{\"event\":\"activation\",\"status\":\"$STATUS\",\"pass\":$PASS,\"warn\":$WARN,\"fail\":$FAIL}" >/dev/null 2>&1
}

if [ "${1:-}" = "check" ]; then check; else install; check; fi
report
