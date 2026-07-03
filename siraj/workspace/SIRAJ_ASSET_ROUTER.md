# SIRAJ_ASSET_ROUTER — أي أداة لأي أصل؟

القرار الأول لكل أصل في اللعبة: **من يصنعه؟** هذا الجدول هو الحكم.

| نوع الأصل | الطريق | لماذا |
|-----------|--------|-------|
| حلبات، أرضيات، منصات، عوائق هندسية | **Blender procedural** (`arena_factory` / task script) | مجاني، فوري، تحكم كامل بالمقاسات والـ Colliders |
| Props بسيطة (صناديق، أعمدة، لافتات) | **Blender procedural** | أسرع من انتظار Meshy، وأخف على الميزانية |
| شخصيات، مخلوقات، أصول عضوية مفصلة | **Meshy text-to-3D** → Blender refine → Unity | Meshy يتجاوز سقف النحت الإجرائي؛ Blender يضبط الـ polycount والـ rig |
| أصل من رسم/كونسبت آرت | **Meshy image-to-3D** → Blender refine | أدق تطابق بصري مع رؤية المالك |
| نفس الشكل بخامة مختلفة (skins) | **Meshy retexture** | لا تعيد توليد الميش — أرخص وأسرع |
| أسلحة منمّطة | Blender `weapon_factory`، وMeshy فقط للأسلحة البطلة (hero weapons) | القواعد الثابتة (GripPoint/MuzzlePoint) أسهل إجرائياً |
| حركات (Idle/Run/Jump/Win/Lose) | Blender `animation_library` على rig بأسماء Mecanim | تُعاد توجيهها لأي Humanoid في Unity |

## الأوامر (واحد لكل طريق)

```bash
# 1) إجرائي (نفس نمط Dhai)
siraj-build.sh tasks/my_arena.py MyArena Models/Arenas

# 2) Meshy نص → Unity في سطر واحد (توليد + تنقيح + استيراد)
siraj-build.sh --prompt "stylized desert watchtower, low poly" Watchtower Models/Props

# 3) Meshy من صورة كونسبت
python3 ~/meshy/meshy_client.py image concept.png --name Hero
siraj-build.sh --meshy ~/meshy/downloads/Hero.glb Hero Characters --rig

# 4) Retexture (skin جديد لنفس الميش)
python3 ~/meshy/meshy_client.py retexture --task-id <id> \
    --prompt "obsidian black with red glow" --name Hero_Dark
siraj-build.sh --meshy ~/meshy/downloads/Hero_Dark.glb Hero_Dark Characters
```

## قواعد الميزانية والذاكرة

1. Meshy يكلّف credits — **لا تولّد أصلاً موجوداً**. افحص `~/meshy/downloads/`
   و`Assets/` أولاً. الـ retexture أرخص من إعادة التوليد.
2. Preview قبل Refine: مرحلة الـ preview في Meshy أرخص — إذا كان الشكل خاطئاً
   أعد الـ prompt قبل دفع تكلفة الـ refine.
3. سقف الـ polycount: 15k للشخصيات، 8k للـ props، 30k للحلبات الكبيرة.
   `meshy_refine.py` يفرض decimation تلقائياً.
4. نفس قاعدة Dhai للذاكرة (3.5GB): لا Blender ثقيل أثناء استيراد Unity.
   Meshy يعمل سحابياً — الـ polling رخيص، استغل وقته لكتابة كود C#.
