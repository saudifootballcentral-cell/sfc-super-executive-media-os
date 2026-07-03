# سراج — Capabilities (v1)

| المكوّن | الأداة | الأمر |
|---------|--------|-------|
| توليد 3D من نص | Meshy text-to-3D | `siraj-build.sh --prompt "..." Name Category [--rig]` |
| توليد 3D من صورة | Meshy image-to-3D | `meshy_client.py image concept.png --name X` ثم `siraj-build.sh --meshy` |
| خامات جديدة لنفس الميش | Meshy retexture | `meshy_client.py retexture --task-id <id> --prompt "..."` |
| تنقيح + تسقيف polycount + rig | `meshy_refine.py` | ضمن `siraj-build.sh --meshy ... [--rig]` |
| حلبات/شخصيات/أسلحة إجرائية | مصانع Dhai في Blender | `siraj-build.sh tasks/x.py Name Category` |
| Prefab + وضع في المشهد + معاينة | `SirajBridge.cs` عبر MCP | `MakePrefab / PlaceInActiveScene / PreviewAsset` |
| استيراد تلقائي | `SirajAssetPostprocessor.cs` | Characters ⇒ Humanoid، `_COL_` ⇒ MeshCollider، استخراج خامات Meshy |

## حدود الصدق المهني

- Meshy يرفع السقف البصري فوق الإجرائي، لكنه ليس مثالياً: توقّع إعادة
  prompt للشخصيات المعقدة، وافحص كل أصل بصرياً قبل إدخاله المشهد.
- الـ rig التلقائي في `meshy_refine.py` هيكل Mecanim مبسّط بأوزان تلقائية —
  ممتاز للألعاب المنمّطة، غير كافٍ لـ facial animation أو أصابع دقيقة.
- طبقة الشبكة (multiplayer حقيقي) مكوّن منفصل يُبنى عند الحاجة.
