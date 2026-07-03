# SIRAJ_PLAYBOOK — من فكرة/GDD إلى لعبة 3D قابلة للعب

إجراء التشغيل القياسي لأي لعبة (party, platformer, shooter, sim…).
لا تتخطَّ مرحلة تحقق.

## المرحلة 0 — Spec

اقرأ الـ GDD (أو اسأل المالك 5 أسئلة: النوع، الكاميرا، عدد اللاعبين،
الإدخال، شرط الفوز) واستخرج `Assets/GameSpecs/<Game>.json`:

```json
{
  "gameName": "SkyDuel",
  "genre": "arena-shooter",
  "camera": { "mode": "Follow", "offset": [0, 5, -8] },
  "arena":  { "route": "procedural", "task": "tasks/sky_arena.py" },
  "characters": [
    { "name": "Falcon", "route": "meshy",
      "prompt": "stylized falcon warrior, low poly, game character, T-pose",
      "rig": true }
  ],
  "props": [
    { "name": "EnergyGate", "route": "meshy",
      "prompt": "sci-fi energy gate, stylized, low poly" }
  ],
  "roundSeconds": 90,
  "winCondition": "last player standing"
}
```

كل أصل يحمل `route` من SIRAJ_ASSET_ROUTER.md.

## المرحلة 1 — الأصول

نفّذ لكل أصل حسب مساره. **Meshy أولاً** (يستغرق دقائق سحابياً)،
وأثناء الـ polling ابنِ الأصول الإجرائية واكتب كود C#.

تحقق: `logs/unity.log` يظهر `[Siraj] imported ...` لكل ملف،
والشخصيات دخلت Humanoid (افحص الـ Avatar في الـ importer).

**فحص Meshy الإلزامي قبل الاستخدام:** بعد الاستيراد نفّذ
`SirajBridge.PreviewAsset(path)` وخذ لقطة عبر MCP. Meshy قد يخرج:
مقياس خاطئ، وجوه مقلوبة (normals)، أو تفاصيل مشوهة في الأصابع/الوجه.
إذا ظهر عيب: أعد الـ prompt بإضافة "clean topology, T-pose, symmetrical".

## المرحلة 2 — تجميع المشهد

إضاءة + كاميرا حسب الـ Spec + الحلبة بالـ Colliders + اللاعبون + UI.
استخدم `SirajBridge.MakePrefab` ثم `PlaceInActiveScene` عبر MCP.
(إن كان مشروع Moments: أعد استخدام `DhaiSceneBuilder/DhaiGameAssembler`.)

## المرحلة 3 — منطق اللعبة

اكتب الـ game loop حسب النوع. القاعدة: **State machine واحد يدير الجولة**
(Setup → Countdown → Playing → RoundEnd)، وكل ميكانيك في MonoBehaviour
مستقل. إدخال لوحة المفاتيح للاختبار دائماً، وطبقة إدخال حقيقية لاحقاً.

## المرحلة 4 — الجودة

- Play Mode عبر MCP، صفّر الـ Warnings، الهدف 60fps.
- Game feel: shake/hit-stop/particles عند كل حدث مهم.
- ألوان مواد متمايزة إذا كانت اللعبة متعددة اللاعبين.
- حدّث `SIRAJ_SYSTEMS.md` بما أُنجز بعد كل مرحلة.

## قواعد ثابتة

1. كل أصل يمر عبر `siraj-build.sh` — لا نسخ يدوي إلى Assets.
2. Meshy asset بدون فحص بصري = لا يدخل المشهد.
3. عظام بأسماء Mecanim فقط (Hips/Spine/Chest/Neck/Head/Left|Right …).
4. لا تولّد بـ Meshy ما يمكن بناؤه إجرائياً في دقيقة.
5. `MESHY_API_KEY` لا يُطبع في اللوقات ولا يُرسل لأي مكان.
