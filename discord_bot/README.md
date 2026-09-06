# Alythia Discord Bot

بوت Discord عربي ومنظم لسيرفر **Alythia**. يعمل من داخل Discord فقط، ويحفظ الإعدادات والتحذيرات والاقتراحات في SQLite.

## التشغيل على Replit

1. افتح تبويب **Secrets** في Replit.
2. أضف Secret بالاسم:

   `DISCORD_BOT_TOKEN`

3. ضع قيمة Bot Token التي نسختها من Discord Developer Portal.
4. شغّل Workflow باسم **Alythia Discord Bot**.

لا تضع التوكن داخل أي ملف أو رسالة. إذا ظهر لك التوكن في مكان عام، أعد توليده فورًا من Developer Portal.

## إنشاء البوت ودعوته للسيرفر

من الهاتف:

1. افتح `discord.com/developers/applications`.
2. اختر **New Application**، ثم سمّه `Alythia`.
3. من **Bot** اختر **Add Bot** ثم **Reset Token** وانسخ التوكن إلى Secret في Replit.
4. من **Bot > Privileged Gateway Intents** فعّل:
   - **Server Members Intent**
   - **Message Content Intent**
5. من **OAuth2 > URL Generator** فعّل:
   - Scopes: `bot` و `applications.commands`
   - Bot Permissions: `View Channels`, `Send Messages`, `Embed Links`, `Read Message History`,
     `Manage Channels`, `Manage Messages`, `Manage Roles`, `Kick Members`, `Ban Members`,
      `Moderate Members`, `Connect`
6. افتح رابط الدعوة الذي تم توليده، واختر سيرفر Alythia، ثم وافق.

لا تمنح Administrator إذا لم تكن تحتاجه؛ الصلاحيات المحددة أعلاه تكفي للأنظمة الموجودة.

## الأوامر الأساسية

- `/help` — عرض المساعدة.
- `/ping` — اختبار سرعة الاستجابة.
- `/server` — معلومات السيرفر.
- `/user` و `/avatar` — معلومات وصورة عضو.
- `/welcome setup #channel` و `/welcome disable` — إعداد الترحيب.
- `/autorole setup @role` و `/autorole disable` — إعداد الرتبة التلقائية.
- `/logs setup #channel` — تحديد قناة اللوقز.
- `/setup line` — تحديد صورة أمر `!خط`، للإدارة فقط.
- `/un setup line` — إزالة صورة أمر `!خط`، للإدارة فقط.
- `/ticket setup [category]` — نشر لوحة فتح التذاكر.
- `/suggest setup #channel` — إعداد قناة الاقتراحات.
- `/suggest send content` — إرسال اقتراح.
- `/balance` `/daily` `/work` `/pay` `/rich` — نظام العملات.
- `/profile` `/rank` `/leaderboard` — نظام الملف الشخصي والمستويات والخبرة.
- `/achievements` — عرض الإنجازات المكتملة والمقفلة.
- `/quests` — عرض المهام اليومية والأسبوعية والتقدم الحالي.
- `/reputation` `/give-rep` `/rep-leaderboard` — نظام Reputation.
- `/title list` `/title set` — عرض الألقاب المفتوحة واختيار اللقب الحالي.
- `/event status` — عرض الحدث العالمي النشط.
- `/event start` `/event end` — إدارة الأحداث العالمية.
- `/setlevel` `/addxp` `/removexp` — أوامر إدارة XP للمشرفين.
- `/coinflip` `/roll` `/eightball` `/choose` — أوامر ترفيهية.
- `/giveaway start` `/giveaway end` — السحوبات.
- `/reactionrole setup` — إنشاء رتبة تفاعلية بالإيموجي.
- `/automod setup` `/automod disable` — الحماية من السبام والروابط.
- `/custom add` `/custom remove` `/custom list` — أوامر مخصصة بصيغة `!اسم_الأمر`.
- `/embed message` أو `!embed message` — إرسال رسالة على شكل Embed، للإدارة فقط.
- `/call @member message` — إرسال نداء خاص لعضو، للإدارة فقط.
- `/voice join` — دخول البوت إلى رومك الصوتي والبقاء فيه حتى إخراجه يدويًا.
- `/voice leave` — إخراج البوت من الروم الصوتي.
- `/ban`, `/kick`, `/timeout`, `/untimeout` — إدارة الأعضاء.
- `/warn`, `/warnings`, `/clearwarnings` — نظام التحذيرات مع SQLite.
- `/clear`, `/lock`, `/unlock` — إدارة القنوات والرسائل.

كل رسائل البوت باللغة العربية، والأوامر الحساسة محمية بصلاحيات Discord.

## استخدام البريفكس `!`

يمكنك استخدام الأوامر الأساسية بطريقتين: Slash Commands أو بريفكس `!`.

أمثلة:

```text
!help
!ping
!balance
!daily
!rank
!roll 20
!clear 10
!call @member تفضل راجع الإدارة
!خط
!join
!leave
```

إعدادات الأنظمة المتقدمة مثل التذاكر والسحوبات والرتب التفاعلية تبقى متاحة من أوامر Slash لأنها تعتمد على خيارات وأزرار Discord.

## تعديل الإعدادات

الإعدادات لا تحتاج تعديل الكود. استخدم أوامر `setup` داخل السيرفر، وسيحفظها البوت تلقائيًا في:

`discord_bot/alythia.sqlite3`

لا تحذف هذا الملف إذا كنت تريد الاحتفاظ بالإعدادات والتحذيرات.