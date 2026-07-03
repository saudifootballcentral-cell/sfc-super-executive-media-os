#!/usr/bin/env bash
# unity_license.sh — ربط يونيتي بحساب المستخدم على سيرفر بلا واجهة،
# بنفس الطريقة المثبتة عملياً في مشروع ضي (Dhai): تدفق .alf/.ulf اليدوي.
#
# لماذا هذه الطريقة؟ الدخول التفاعلي (Unity Hub / متصفح) مستحيل على سيرفر
# headless. التفعيل اليدوي يحتاج المتصفح مرة واحدة فقط — من جهاز المستخدم،
# لا من السيرفر — والترخيص الناتج مربوط بالجهاز (MachineID).
#
#   ./unity_license.sh check              # حالة الترخيص الحالية
#   ./unity_license.sh request            # توليد ملف .alf (طلب تفعيل)
#   ./unity_license.sh apply <file.ulf>   # تطبيق ملف الترخيص المُنزَّل
#
# الدورة الكاملة (خطوة المتصفح يقوم بها المالك، مرة واحدة لكل VM):
#   1. على السيرفر:  ./unity_license.sh request   → ينتج Unity_vX.alf
#   2. على جهازك:    ادخل https://license.unity3d.com/manual بحساب يونيتي
#                    الخاص بك، ارفع الـ.alf، نزّل ملف الـ.ulf
#   3. على السيرفر:  ./unity_license.sh apply Unity_vX.ulf
#
# تحذير موروث من تجربة ضي: الترخيص مربوط بالجهاز — إعادة بناء الـVM
# (تغيّر MachineID) تُبطل الترخيص وتتطلب إعادة الدورة من الخطوة 1.
set -euo pipefail
UNITY="${UNITY_BIN:-/home/mulerun/unity6/Editor/Unity}"
LOG="/tmp/unity_license.log"

[ -x "$UNITY" ] || { echo "❌ Unity غير موجود في $UNITY (عدّل UNITY_BIN)"; exit 1; }

case "${1:-}" in
  check)
    # مواضع ملف الترخيص المعتادة على لينكس
    FOUND=""
    for p in "$HOME/.local/share/unity3d/Unity/Unity_lic.ulf" \
             "/usr/share/unity3d/Unity/Unity_lic.ulf"; do
      [ -f "$p" ] && FOUND="$p" && break
    done
    if [ -n "$FOUND" ]; then
      echo "✅ ملف ترخيص موجود: $FOUND"
      grep -o 'SerialMasked[^/]*' "$FOUND" | head -1 || true
      grep -o '<MachineID Value="[^"]*"' "$FOUND" | head -1 || true
    else
      echo "❌ لا ملف ترخيص — شغّل: $0 request"
      exit 1
    fi
    ;;
  request)
    echo "توليد طلب التفعيل (.alf)..."
    "$UNITY" -batchmode -nographics -quit -createManualActivationFile -logfile "$LOG" || true
    ALF=$(ls -t Unity_v*.alf 2>/dev/null | head -1)
    if [ -n "${ALF:-}" ]; then
      echo "✅ تولّد: $(pwd)/$ALF"
      echo
      echo "الخطوة التالية (من جهازك، مرة واحدة):"
      echo "  1. انقل $ALF إلى جهازك"
      echo "  2. افتح https://license.unity3d.com/manual ودخّل بحساب يونيتي"
      echo "  3. ارفع الـ.alf، اختر Unity Personal (أو رخصتك)، نزّل الـ.ulf"
      echo "  4. أعد الـ.ulf للسيرفر ثم: $0 apply <file.ulf>"
    else
      echo "❌ لم يتولّد ملف .alf — راجع $LOG"
      tail -5 "$LOG" 2>/dev/null || true
      exit 1
    fi
    ;;
  apply)
    ULF="${2:?usage: $0 apply <file.ulf>}"
    [ -f "$ULF" ] || { echo "❌ $ULF غير موجود"; exit 1; }
    echo "تطبيق الترخيص..."
    "$UNITY" -batchmode -nographics -quit -manualLicenseFile "$ULF" -logfile "$LOG" || true
    if grep -qi "Licensing::Module.*success\|License activated\|Next license update" "$LOG" 2>/dev/null \
       || "$0" check >/dev/null 2>&1; then
      echo "✅ الترخيص فُعِّل — تحقق: $0 check"
      # سجّل الحدث في ذاكرة سراج إن كانت متوفرة
      MEM="$(dirname "$0")/../../../os/engine/memory.py"
      [ -f "$MEM" ] && python3 "$MEM" log versions '{"event":"unity_license_activated","note":"machine-bound: re-activate if VM rebuilt"}' >/dev/null 2>&1 || true
    else
      echo "⚠️ لم أستطع تأكيد التفعيل من السجل — افحص: tail -30 $LOG"
    fi
    ;;
  *)
    echo "usage: $0 {check|request|apply <file.ulf>}"; exit 1 ;;
esac
