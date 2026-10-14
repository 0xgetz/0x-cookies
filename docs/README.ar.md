<div align="center" dir="rtl">

<img src="../assets/banner.png" alt="0x Cookies" width="100%"/>

# 0x Cookies

**فاحص كوكيز وجلسات جماعي على طريقة OpenBullet — مدعوم بـ Chromium حقيقي.**

افحص بشكل جماعي ما إذا كانت الكوكيز / تسجيلات الدخول المحفوظة لا تزال حيّة على
**189 منصة**. على عكس فاحصات HTTP العادية، يشغّل هذا الأداة **Chromium headless حقيقيًا**
(عبر Playwright)، لذا يبقى دقيقًا على المواقع التي تُرجع دائمًا `HTTP 200`
(مايكروسوفت، وسائل التواصل، خدمات SaaS، …).

[![Python](https://img.shields.io/badge/python-3.9%2B-34e5b0?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/playwright-Chromium-8b7cf6?style=flat-square&logo=playwright&logoColor=white)](https://playwright.dev/)
[![Platforms](https://img.shields.io/badge/platforms-189-f5b642?style=flat-square)](#-المنصات-المدمجة)
[![License](https://img.shields.io/badge/license-MIT-34e5b0?style=flat-square)](../LICENSE)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-8b7cf6?style=flat-square)](../CONTRIBUTING.md)
[![Made by 0xgetz](https://img.shields.io/badge/by-0xgetz-9aa4b2?style=flat-square&logo=github)](https://github.com/0xgetz)

[English](../README.md) · [Indonesia](README.id.md) · [Español](README.es.md) · [中文](README.zh.md) · [**العربية**](README.ar.md)

</div>

---

<div dir="rtl">

## لماذا وُجدت

معظم فاحصات الكوكيز ترسل طلب HTTP واحدًا ثم تنظر إلى رمز الحالة. يفشل هذا بمجرد أن
يُرجع موقع ما `200 OK` لكلٍّ من الجلسة **الحيّة** و**الميتة** — فتحصل على
«صالح 100%» على بيانات فارغة. **0x Cookies** يحمّل الصفحة في متصفح حقيقي، يتابع
إعادة التوجيه، ويقرر بناءً على **الرابط النهائي + DOM** هل أنت مسجَّل الدخول فعلًا.

- **أحكام متصفح حقيقي** — Chromium headless عبر Playwright.
- **سياقات معزولة** — كل مُدخَل يعمل في سياق متصفح خاص به، فلا تتسرب الكوكيز بين
  الحسابات، ولا يظهر ملف ميت كصالح أبدًا.
- **الفشل يتغلب على النجاح** — الهبوط على صفحة تسجيل دخول/خطأ يعني دائمًا `invalid`.
- **189 منصة جاهزة** — إضافةً إلى محرك إعدادات HTTP + متصفح عام.
- **لوحة تحكم ويب** — ارفع المُدخلات/الإعدادات/البروكسيات، start/pause/stop، وإحصاءات حيّة.
- **مشغّل CLI** — المحرك نفسه، مثالي لخادم VPS أو المهام المجدولة.
- **مجموعة بروكسي** — تدوير وحظر تلقائي عند الفشل (`http/https/socks4/socks5`).

> **للاستخدام المصرّح به فقط.** اختبر حساباتك الخاصة أو التي لديك إذن صريح باختبارها.
> انظر [إخلاء المسؤولية](#️-إخلاء-المسؤولية).

---

## البدء السريع

```bash
git clone https://github.com/0xgetz/0x-cookies.git
cd 0x-cookies
./start.sh                 # يفتح http://localhost:8080
```

يقوم `start.sh` بتثبيت Playwright وتنزيل Chromium وجلب مكتبات النظام المطلوبة
(apt / dnf / apk). تفضّل الطريقة اليدوية؟

```bash
pip install playwright
python -m playwright install chromium
python -m playwright install-deps chromium     # Debian/Ubuntu
python server.py --host 0.0.0.0 --port 8080
```

> افتح المنفذين **8080** (اللوحة) **و8081** (WebSocket للإحصاءات الحيّة) إذا وصلت إلى
> اللوحة من جهاز آخر. إذا كان 8081 محجوبًا، تتحول اللوحة تلقائيًا إلى الاستقصاء الدوري.

---

## استخدام لوحة التحكم

1. **Inputs** — الصق واحدًا في كل سطر، أو ارفع ملف `.txt`.
   وضع `userpass` → `user:pass`؛ وضع `cookie` → محتوى الكوكي (أو مسار ملف الكوكي).
2. **Config** — الصق JSON، اختر إعدادًا جاهزًا، أو حمّل أحد الإعدادات الـ189 من
   `configs/platforms/<الاسم>.json`.
3. **Proxies** *(اختياري)* — واحد في كل سطر:
   `host:port`، `user:pass@host:port`، `scheme://host:port`
   (`http` `https` `socks4` `socks5` `socks5h`). تدوير + حظر تلقائي.
4. **Options** — عدد العمال، المهلة، إعادة المحاولة، مدة حظر البروكسي، تشغيل/إيقاف headless.
5. **Start** — راقب tested / hits / invalid / errors / CPM / progress مباشرةً.
6. نزّل **hits** (`data/hits.txt`) و**كل النتائج** (`data/all.txt`).

---

## المنصات المدمجة

تأتي **189 إعدادًا** في [`configs/platforms/`](../configs/platforms)، وتغطي التواصل
والبريد والسحابة والمطوّرين والمالية والبث والتسوّق وغيرها — مثل
`google` `microsoft` `github` `discord` `instagram` `tiktok` `netflix` `spotify`
`openai` `claude` `notion` `sentry` `datadog` `supabase` `huggingface` `bybit` `revolut` `doordash` `strava` …

كل إعداد إما فحص `redirect` (الموقع يردّ المستخدم المجهول) أو فحص `marker`
(SPA: يُطابَق عبر محدّدات DOM صالحة/غير صالحة وعلامات في الـ body). أعد توليد المجموعة:

```bash
python gen_configs.py
```

---

## صيغة الإعداد (على طريقة OpenBullet)

```json
{
  "name": "Site login check",
  "author": "0x Cookies",
  "type": "http",
  "input_format": "userpass",
  "request": {
    "url": "https://site.com/api/login",
    "method": "POST",
    "headers": { "Cookie": "<COOKIE>", "User-Agent": "Mozilla/5.0" },
    "body": "user=<USER>&pass=<PASS>"
  },
  "captures": [ { "name": "token", "regex": "\"token\"\\s*:\\s*\"([^\"]+)\"" } ],
  "success": { "status": [200], "body_regex": "\"ok\":true", "url_regex": "/dashboard" },
  "fail":    { "body_regex": "invalid|incorrect", "url_regex": "(login|signin)" },
  "retry": 1
}
```

| الحقل | المعنى |
|-------|--------|
| `type` | `http` = طلب مباشر · `browser` = حمّل الصفحة في Chromium |
| `input_format` | `line` · `userpass` · `cookie` |
| `request` | url / method / headers / body (HTTP فقط) |
| `captures` | تعبيرات regex تُكتب في ملف **hits** |
| `success` / `fail` | `status` · `body_regex` · `url_regex` |
| متغيّرات القواعد | `<USER>` `<PASS>` `<LINE>` `<COOKIE>` تُستخدم في url والهيدرز والـ body **و** regex |

**`fail` يتغلب دائمًا على `success`** — إذا طابق الرابط النهائي صفحة تسجيل دخول/خطأ
فالنتيجة `invalid`، مهما تطابق غير ذلك.

---

## CLI

```bash
# إعداد HTTP
python cli.py --config configs/example_http.json --inputs users.txt \
  --proxies proxies.txt --workers 8 --timeout 30 \
  --hits hits.txt --all all.txt

# فحص كوكيز المتصفح عبر منصة مدمجة
python cli.py --config configs/platforms/github.json --inputs cookies/ \
  --workers 4 --headful
```

---

## واجهة REST API

| الطريقة | المسار | Body |
|--------|--------|------|
| `POST` | `/api/inputs` | `{"text":"a\nb"}` أو `{"lines":[...]}` |
| `POST` | `/api/config` | `{"raw":"<json>"}` أو كائن إعداد |
| `POST` | `/api/proxies` | `{"text":"host:port\n..."}` |
| `POST` | `/api/start` | `{"workers":4,"timeout":30,"retry":1,"headless":true}` |
| `POST` | `/api/stop` · `/api/pause` · `/api/resume` | — |
| `GET` | `/api/stats` | الإحصاءات + السجل |
| `GET` | `/api/hits` · `/api/all` | النتائج (نص) |
| `WS` | `ws://host:8081/` | يدفع الإحصاءات + السجل كل 0.5 ثانية |

اضبط `OXC_TOKEN` لفرض ترويسة `X-Auth-Token` على كل `POST`.

---

## بنية المشروع

انظر **[STRUCTURE.md](../STRUCTURE.md)** للمخطط الكامل المشروح.

```
0x-cookies/
├── server.py          لوحة التحكم (HTTP + WebSocket إحصاءات حيّة)
├── cli.py             مشغّل headless
├── start.sh           مشغّل بخطوة واحدة (يثبّت المتصفح والمكتبات)
├── gen_configs.py     يولّد إعدادات الـ189 منصة
├── core/              config · engine · proxies
├── web/               واجهة اللوحة
├── configs/           أمثلة + إعدادات لكل منصة
├── docs/              5 ملفات README مترجمة
└── assets/            الشعار + البانر
```

---

## VPS بدون root (مكتبات Chromium يدويًا)

إذا لم يتوفر `apt` وفشل Chromium بالخطأ
`error while loading shared libraries: libglib-2.0.so.0`:

```bash
mkdir -p third_party/lib
cp /path/to/*.so* third_party/lib/   # اجمع ملفات .so الناقصة
./start.sh                            # يضيف start.sh المجلد third_party/lib إلى LD_LIBRARY_PATH
```

---

## المساهمة

المشاكل (Issues) وطلبات الدمج (PRs) مرحّب بها — خصوصًا إعدادات منصات جديدة. انظر
[CONTRIBUTING.md](../CONTRIBUTING.md).

## الترخيص

[MIT](../LICENSE) © 0x Cookies

## ⚠️ إخلاء المسؤولية

تُقدَّم هذه الأداة **للبحوث الأمنية المشروعة واختبار الحسابات التي تملكها أو لديك إذن
صريح باختبارها**. أنت وحدك مسؤول عن كيفية استخدامها. لا تستخدمها أبدًا ضد أنظمة أو
حسابات دون إذن.

---

</div>

<div align="center" dir="rtl">

صنعها **0x Cookies** · [GitHub @0xgetz](https://github.com/0xgetz) · [Telegram @xiyyyyz](https://t.me/xiyyyyz)

</div>
