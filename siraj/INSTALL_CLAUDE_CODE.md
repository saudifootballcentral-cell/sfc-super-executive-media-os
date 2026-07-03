# تشغيل سراج عبر Claude Code — دليل التثبيت

هذا يجعل سراج **يعمل فعلياً**: يشغّل bash، يكتب ملفات، يشغّل Blender ويونيتي،
يستدعي 27 وكيلاً فرعياً حقيقياً — على نفس الجهاز الذي فيه Unity وBlender
وحساباتك، لا داخل متصفح.

## 0) المتطلبات
نفس متطلبات حزمة سراج السابقة (Python 3، Blender، مشروع Unity 6، MCP على
127.0.0.1:8080) + **Node.js** لتثبيت Claude Code.

## 1) تثبيت Claude Code
```bash
npm install -g @anthropic-ai/claude-code
claude --version   # تأكيد التثبيت
```
(المصدر الرسمي: https://www.npmjs.com/package/@anthropic-ai/claude-code)

## 2) وضع المشروع
فك ضغط هذه الحزمة على نفس الخادم، مثلاً في `~/siraj`، بحيث تحصل على:
```
~/siraj/CLAUDE.md
~/siraj/.claude/...
~/siraj/.mcp.json
~/siraj/os/...
~/siraj/home/mulerun/...
```
إن كان لديك من قبل تثبيت سابق لسراج (siraj-package-v4)، انسخ فقط المجلدات
الجديدة (`CLAUDE.md`, `.claude/`, `.mcp.json`) فوق تثبيتك الحالي — لا شيء
آخر تغيّر.

## 3) مفتاح Meshy
```bash
echo 'MESHY_API_KEY=msy_xxxxxxxx' >> home/mulerun/.env
chmod 600 home/mulerun/.env
```
**لا تلصق المفتاح في محادثة Claude Code أبداً** — اتركه في هذا الملف فقط.
حارس `.claude/hooks/guard-secrets.sh` يمنع أي أمر Bash قد يطبعه، لكنه خط
دفاع ثانٍ لا بديل عن عدم كتابته في الشات من الأساس.

## 4) اتصال يونيتي (MCP)
`.mcp.json` يفترض أن جسر يونيتي الموجود لديك (`127.0.0.1:8080`) يتحدث بروتوكول
MCP الحقيقي (JSON-RPC عبر HTTP). **تحقق أولاً:**
```bash
claude mcp list        # هل يظهر siraj-unity متصلاً؟
```
- **إن ظهر متصلاً** — ممتاز، الوكلاء يستطيعون استدعاء أدوات يونيتي مباشرة.
- **إن فشل الاتصال** — على الأغلب جسرك REST بسيط (نفس `/tools/assets_refresh`
  الذي بنيناه في `siraj-build.sh`) وليس MCP حقيقياً بعد. **لا مشكلة عملياً:**
  كل وكيل فرعي لديه صلاحية Bash، وسيستخدم `siraj-build.sh` و`curl` تماماً
  كما كنا نفعل — يعمل بلا أي بروتوكول MCP فعلي. احذف `.mcp.json` أو تجاهل
  رسالة الفشل إن أردت تفادي الضجيج في `/mcp`.

## 4.4) ترخيص يونيتي على السيرفر (طريقة ضي — إلزامي لأي VM جديدة)
على سيرفر بلا واجهة، ربط يونيتي بحسابك يتم عبر التفعيل اليدوي، مرة واحدة:
```bash
cd home/mulerun/unity_cloud
./unity_license.sh check      # هل الترخيص مفعَّل أصلاً؟
./unity_license.sh request    # يولّد Unity_vX.alf
# من جهازك: افتح license.unity3d.com/manual بحسابك، ارفع الـ.alf، نزّل الـ.ulf
./unity_license.sh apply Unity_vX.ulf
```
تنبيه من تجربة ضي: الترخيص مربوط بالجهاز — أي إعادة بناء للـVM تبطله
وتتطلب إعادة الدورة كاملة.

## 4.5) يونيتي كلاود (اختياري)
إن كنت تستخدم Unity Cloud (Asset Manager / UGS / Cloud Build):

```bash
pip install --index-url https://unity3ddist.jfrog.io/artifactory/api/pypi/am-pypi-prod-local/simple unity-cloud --break-system-packages

cat >> home/mulerun/.env << 'ENV'
UNITY_CLOUD_ORG_ID=رقم_مؤسستك
UNITY_CLOUD_PROJECT_ID=معرف_مشروعك
UGS_CLI_SERVICE_KEY_ID=من_Dashboard_Service_Accounts
UGS_CLI_SERVICE_SECRET_KEY=من_Dashboard_Service_Accounts
ENV
chmod 600 home/mulerun/.env
```
الـService Account يُنشأ من Unity Cloud Dashboard → Administration → Service
Accounts. **لا تلصقه في الشات أبداً** — نفس قاعدة مفتاح Meshy تماماً.

أول مرة فقط، وبشكل تفاعلي (وليس عبر سكربت آلي):
```bash
python3 -c "from home.mulerun.unity_cloud.unity_cloud_bridge import auth; auth()"
```
سيفتح تسجيل دخول بالمتصفح (توثيق Unity الرسمي الحالي لا يذكر مساراً غير
تفاعلي لهذا الـSDK تحديداً — إن وجدت واحداً في حسابك حدّث `auth()` باستخدامه).

لخدمات UGS الحية (Remote Config/Economy) استخدم `ugs_deploy.sh` بدل ذلك —
مصمَّم من الأساس لعمل بلا واجهة عبر Service Account.

## 4.6) Unity VCS — مزامنة مشروعك الحقيقي من Unity Cloud (طريق ضي المثبت)
إن كان مشروعك على Unity Version Control (كما عند ضي — مستودع Moments):
```bash
cd home/mulerun/unity_cloud
./unity_vcs.sh setup <ORG_ID>            # مثال ضي: 18968407097579
./unity_vcs.sh repos                      # أول مرة: يطلب دخول متصفح بـUnity ID
./unity_vcs.sh clone "اسم_المستودع@<ORG_ID>@unity" /home/mulerun/unity6/MyGame
./unity_vcs.sh update /home/mulerun/unity6/MyGame   # بالخلفية، راقب /tmp/cm_update.log
```
على سيرفر headless: خطوة المتصفح تتم عبر VNC مرة واحدة والجلسة تُحفظ.
التفاصيل الكاملة وما نجح/فشل فعلياً: `os/OPS_LESSONS.md` §4.

## 5) أول تشغيل
```bash
cd ~/siraj
claude
```
داخل الجلسة:
```
/siraj-boot
```
يجب أن يعرض حالة الذاكرة (فارغة أول مرة) وتأكيد أن كل شيء جاهز. تحقق أيضاً:
```
/agents      ← يجب أن تظهر 27 وكيلاً فرعياً
/mcp         ← حالة اتصال siraj-unity (راجع البند 4)
```

## 6) ابدأ أول لعبة
```
/siraj-new لعبة سباق فضائي بسيطة، لاعب واحد، كاميرا خلفية، 3 لفات للفوز
```
سيستدعي `game-director` تلقائياً عبر أداة Task لتحليل الفكرة. بعد اعتمادك،
استمر يدوياً بـ`/siraj-dispatch` دورة بدورة (لمراقبة كل خطوة)، أو
`/siraj-run 10` لتشغيل عشر دورات تلقائياً دون توقف.

## استكشاف الأخطاء
| المشكلة | الحل |
|---|---|
| `/agents` لا يظهر الوكلاء | تأكد أنك شغّلت `claude` من جذر المشروع (حيث `CLAUDE.md`) لا من مجلد فرعي |
| الحارس يحجب أمراً مشروعاً | راجع `.claude/hooks/guard-secrets.sh` — عدّل النمط إن كان مبالغاً في الحجب |
| عدّلت `os/agents/*.yaml` ولا يظهر التغيير | أعد التوليد: `python3 .claude/generate_claude_agents.py` ثم أعد تشغيل `claude` |
| Meshy يرفض الطلبات | تحقق من صلاحية المفتاح ومن اعتمادك المتبقي على meshy.ai مباشرة |
