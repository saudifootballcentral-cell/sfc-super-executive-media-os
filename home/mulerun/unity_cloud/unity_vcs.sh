#!/usr/bin/env bash
# unity_vcs.sh — ربط Unity Version Control (Plastic SCM) — الطريقة المثبتة
# فعلياً في جلسات ضي لمزامنة المشروع الحقيقي من Unity Cloud.
#
# ما ثبت عملياً من جلسات ضي (يوليو 2026):
#   - السيرفر: <ORG_ID>@unity  (مثال ضي: 18968407097579@unity)
#   - الأداة: cm (Plastic SCM CLI) — كانت مثبتة مسبقاً مع أدوات يونيتي
#   - المصادقة: تسجيل دخول متصفح لمرة واحدة (عبر VNC على سيرفر headless)،
#     وبعدها الجلسة تبقى محفوظة في Chrome/إعدادات cm — «الاتصال يكتمل تلقائياً»
#   - REST API بالـ Service Account عمل جزئياً فقط (token exchange نجح لكن
#     أغلب الـ endpoints لم تكفِ) — cm هو العمود الفقري الفعلي للمزامنة
#   - الأداء المقاس: ~170-200MB/دقيقة، رأس مستودع 234GB نزل فعلياً 6.2GB في ~25 دقيقة
#     (حجم الـ head أصغر بكثير من حجم التاريخ الكامل — لا تنخدع بالرقم الكبير)
#
# usage:
#   ./unity_vcs.sh setup <ORG_ID>          # ضبط السيرفر
#   ./unity_vcs.sh repos                   # قائمة المستودعات (يفشل إن لم تكتمل المصادقة)
#   ./unity_vcs.sh clone "<repo_spec>" <dir>   # إنشاء workspace ومزامنة
#   ./unity_vcs.sh update <dir>            # سحب آخر التغييرات (في الخلفية للأحجام الكبيرة)
#   ./unity_vcs.sh status <dir>            # حالة الـ workspace
set -euo pipefail
command -v cm >/dev/null || { echo "❌ cm (Plastic SCM CLI) غير مثبت — على سيرفر ضي كان موجوداً مع أدوات يونيتي؛ ثبّته من Unity DevOps docs"; exit 1; }

case "${1:-}" in
  setup)
    ORG="${2:?usage: $0 setup <ORG_ID>}"
    cm configure --language=en --workingmode=SSOWorkingMode --server="${ORG}@unity" 2>/dev/null \
      || cm configure --server="${ORG}@unity" || true
    echo "السيرفر مضبوط: ${ORG}@unity"
    echo "⚠️  المصادقة تتطلب تسجيل دخول متصفح لمرة واحدة (Unity ID):"
    echo "   - على جهاز بواجهة: أي أمر cm سيفتح المتصفح تلقائياً"
    echo "   - على سيرفر headless: افتح متصفحاً عبر VNC وسجّل دخول Unity ID،"
    echo "     ثم أعد الأمر — الجلسة تُحفظ ويكتمل الربط تلقائياً (مثبت في جلسات ضي)"
    ;;
  repos)
    cm repository list 2>&1 || {
      echo; echo "إن ظهر خطأ مصادقة/انتظار: أكمل تسجيل دخول المتصفح أولاً (انظر setup)"; exit 1; }
    ;;
  clone)
    SPEC="${2:?usage: $0 clone \"<repo>@<org>@unity\" <dir>}"; DIR="${3:?target dir}"
    mkdir -p "$DIR"
    cm workspace create "$(basename "$DIR")_wk" "$DIR" --repository="$SPEC"
    echo "workspace أُنشئ — المزامنة (قد تطول للمستودعات الكبيرة):"
    echo "  $0 update $DIR"
    ;;
  update)
    DIR="${2:?usage: $0 update <dir>}"
    cd "$DIR"
    # درس ضي: للمستودعات الكبيرة شغّلها بالخلفية وراقب، ولا تتركها تحت مهلة قصيرة
    nohup cm update > /tmp/cm_update.log 2>&1 &
    echo "cm update انطلق بالخلفية (PID $!) — راقب: tail -f /tmp/cm_update.log"
    ;;
  status)
    DIR="${2:?usage: $0 status <dir>}"
    cd "$DIR" && cm status 2>&1 | head -20
    ;;
  *)
    echo "usage: $0 {setup <ORG_ID>|repos|clone <spec> <dir>|update <dir>|status <dir>}"; exit 1 ;;
esac
