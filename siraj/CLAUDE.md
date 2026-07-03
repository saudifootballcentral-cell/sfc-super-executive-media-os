# SIRAJ — Enterprise Game Development OS (Claude Code project)

سراج يعمل هنا كمنصة إنتاج ألعاب مستقلة: العقل (هذه الجلسة) + 27 وكيلاً فرعياً
متخصصاً (`.claude/agents/`) + محرك تنسيق حقيقي (`os/engine/`) + خط أنابيب
Meshy→Blender→Unity فعلي (`home/mulerun/`). كل شيء هنا ينفَّذ فعلياً على هذا
الجهاز، لا محاكاة.

## أول شيء في كل جلسة
شغّل `/siraj-boot` قبل أي عمل آخر. لا تفترض حالة المشروع من الذاكرة — اقرأها
من `os/engine/memory.py boot` دائماً، فهي المصدر الوحيد للحقيقة.

## القانون الثلاثي (غير قابل للتفاوض)
```
تصميم اللعبة → Meshy (توليد) → Blender (إصلاح/تسقيف/تهيكل) → Unity (إنتاج)
```
لا أصل من Meshy يدخل Unity مباشرة. لا مرحلة من الـ21 مرحلة تُتخطى — انظر
`os/engine/orchestrator.py` (STAGES) و`os/ARCHITECTURE.md`.

## الأوامر (slash commands)
| أمر | الاستخدام |
|---|---|
| `/siraj-boot` | حالة المشروع + الطابور — أول كل جلسة |
| `/siraj-new` | فتح مشروع لعبة جديد |
| `/siraj-dispatch` | توزيع دورة واحدة على الوكيل الصحيح عبر Task |
| `/siraj-run` | تشغيل عدة دورات تلقائياً دون توقف بعد كل مهمة |
| `/siraj-route` | قرار مسار أصل (reuse/retexture/procedural/meshy) |
| `/siraj-gate` | اجتياز/إسقاط بوابة مرحلة |
| `/siraj-status` | تقرير كامل للقراءة فقط |

## كيف يعمل التوزيع
`orchestrator.py next` يُرجع المهمة والوكيل المسؤول (`act_as`، kebab-case).
استدعِ ذلك الوكيل عبر **أداة Task** (`subagent_type: <act_as>`) — لا تنفّذ
عمله بنفسك في الجلسة الرئيسية. كل وكيل في `.claude/agents/<id>.md` له
صلاحية وأدوات محددة تطابق دوره الحقيقي في الاستوديو (راجع الملف قبل أي شك).

## البنية
```
CLAUDE.md              ← هذا الملف (يُحمَّل تلقائياً كل جلسة)
.claude/agents/         27 وكيلاً فرعياً (مولَّدة من os/agents/*.yaml)
.claude/skills/         أوامر / (siraj-boot, dispatch, run, route, gate, status)
.claude/hooks/          حارس أمني: يمنع طباعة MESHY_API_KEY أو محتوى .env
.mcp.json               اتصال MCP بجسر يونيتي المحلي (127.0.0.1:8080)
os/engine/               orchestrator.py · asset_router.py · memory.py (المصدر الحقيقي للحقيقة)
os/agents/*.yaml         مصدر تعريف الوكلاء — عدّل هنا ثم أعد توليد .claude/agents عبر:
                         python3 .claude/generate_claude_agents.py
os/pipelines/            توثيق كل مرحلة (meshy/blender/unity/qa/self_repair/build/publishing)
os/ARCHITECTURE.md       القرارات المعمارية (ADR-001: وكلاء كأدوار لا عمليات، إلخ)
os/OPS_LESSONS.md        دروس تشغيلية من جلسات ضي الفعلية — اقرأه قبل أي تشخيص Unity/MCP
home/mulerun/            التنفيذ الفعلي: meshy_client.py · meshy_refine.py (بديل بليندر بـtrimesh
                         إن لم يتوفر bpy) · siraj-build.sh · SirajBridge.cs · SirajAssetPostprocessor.cs
memory/*.json            سجلات دائمة: assets, credits, bugs, decisions, gates, versions...
```

## ربط حساب يونيتي (الترخيص) — طريقة ضي المثبتة
تمييز حاسم تعلمناه من مشروع ضي: **ربط الحساب ≠ خدمات السحابة.**
ضي اتصل بحساب يونيتي عبر **التفعيل اليدوي للترخيص فقط** (.alf → متصفح المالك
على license.unity3d.com/manual → .ulf)، بلا أي خدمة سحابية. الأداة:
`home/mulerun/unity_cloud/unity_license.sh {check|request|apply}`.
الترخيص **مربوط بالجهاز** — إعادة بناء الـVM تتطلب إعادة الدورة، و`siraj-activate.sh`
يفحص حالته تلقائياً. خطوة المتصفح يقوم بها المالك مرة واحدة، لا يمكن أتمتتها.

## Unity Cloud (اختياري — إن كان مفعّلاً)
ثلاث نقاط تكامل حقيقية، لا محاكاة:
- **Asset Manager** (`home/mulerun/unity_cloud/unity_cloud_bridge.py`) — يفحص
  مدير الأصول قبل أي قرار reuse إن كانت `UNITY_CLOUD_ORG_ID`/`UNITY_CLOUD_PROJECT_ID`
  مضبوطتين؛ السجل السحابي يتفوّق على `memory/assets.json` المحلي.
- **UGS CLI** (`home/mulerun/unity_cloud/ugs_deploy.sh`) — لنشر إعدادات
  الخدمات الحية (Remote Config/Economy/Leaderboards) فقط عندما يتطلبها GDD
  صراحة — القانون المحلي أولاً ما زال سارياً.
- **Unity VCS / Plastic SCM** (`home/mulerun/unity_cloud/unity_vcs.sh`) —
  **الطريق المثبت فعلياً في جلسات ضي** لمزامنة المشروع الحقيقي من Unity Cloud:
  `cm` CLI ضد `<ORG_ID>@unity`، مصادقة متصفح لمرة واحدة (VNC على headless)
  ثم كل شيء آلي. راجع os/OPS_LESSONS.md §4 لما نجح وفشل بالضبط.
- **Cloud Build** — يُضبط من Dashboard، ويسجّل نتيجته في ذاكرة سراج عبر
  `home/mulerun/unity_cloud/cloud_build_hooks/post-build.sh` كـpost-build hook.

بيانات الاعتماد في `home/mulerun/.env` فقط (`UNITY_CLOUD_ORG_ID`,
`UNITY_CLOUD_PROJECT_ID`, `UGS_CLI_SERVICE_KEY_ID`, `UGS_CLI_SERVICE_SECRET_KEY`)
— الحارس الأمني يحجب طباعة المفتاحين الأخيرين. **ثغرة معروفة وموثّقة:**
دالة رفع أصل جديد (`upload_new_asset`) لم تُؤكَّد بعد من توثيق Unity الحالي
وهي عمداً `NotImplementedError` — لا تخمّنها، تحقق من التوثيق أولاً.

## قواعد أمان صارمة
- `MESHY_API_KEY` يعيش في `home/mulerun/.env` فقط (`chmod 600`) — لا يُطبع،
  لا يُلصق في رسالة، لا يدخل أي ملف مُتتبَّع بـgit. حارس `.claude/hooks/`
  يمنع أوامر Bash التي قد تكشفه.
- أي بوابة `orchestrator.py gate <stage> pass` ترفض المرور إن وُجدت مهام
  مفتوحة في تلك المرحلة — لا تحاول تمريرها يدوياً بتحرير JSON مباشرة.
- Meshy يكلّف اعتمادات حقيقية من حساب المستخدم — استخدم `/siraj-route`
  قبل أي توليد؛ لا توليد بلا قرار موجَّه مسجَّل.

## عندما تحتاج تفاصيل أعمق
اقرأ `os/ARCHITECTURE.md` (المعمارية) أو `os/pipelines/<name>.md` (تفاصيل
مرحلة محددة) أو ملف الوكيل نفسه في `.claude/agents/` — لا تخمّن قواعد لم
تُكتب هنا.
