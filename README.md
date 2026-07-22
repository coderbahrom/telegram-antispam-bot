# Telegram Anti-Spam Bot 🛡

Telegram guruhlarini "profilimga o'ting va zavqlaning 😘" turidagi spam/phishing
akkauntlardan himoya qiluvchi bot. Python + [aiogram](https://docs.aiogram.dev) 3.x.

## Nima qiladi

1. **Profil tekshiruvi** — a'zo qo'shilganda ism + bio + shaxsiy kanal nomi
   spam filtridan o'tkaziladi; porn/phishing bo'lsa darrov ban (guruh va kanalда).
2. **NSFW rasm AI** — profil rasmi lokal NudeNet modeli bilan tekshiriladi;
   18+ rasm topilsa darrov ban. Tashqi API yo'q, hammasi serverda.
3. **CAPTCHA** — yangi a'zo cheklanadi (yoza olmaydi), tugmani bosсагина
   ochiladi. Vaqtida bosmasa chetlatiladi.
4. **Spam filtri** — har bir xabar ball (score) tizimi bilan tekshiriladi:
   so'z/ibora (uz/ru/en, o'zaklar), 18+ emoji, link/invite-link, pul-summa
   va'dasi, forward/story, yangi a'zo. `hybrid` rejimда porn/phishing → ban,
   oddiy reklama → o'chirish + ogohlantirish.
5. **Admin buyruqlari** — `/stats`, so'z boshqaruvi, qo'lda ban.

## 1-qadam: Bot yaratish (@BotFather)

1. Telegramda [@BotFather](https://t.me/BotFather) ga `/newbot` yozing.
2. Nom va username bering → u sizga **token** beradi (`123456:ABC-...`).
3. `/setprivacy` → botingizni tanlang → **Disable** (guruhdagi barcha xabarlarni
   ko'rishi uchun MAJBURIY, aks holda filtr ishlamaydi).

## 2-qadam: Sozlash

```bash
cp .env.example .env
```

`.env` faylida kamida `BOT_TOKEN` ni to'ldiring. O'z Telegram ID'ingizni
[@userinfobot](https://t.me/userinfobot) dan olib, `ADMIN_IDS` ga qo'ying.

## 3-qadam: Ishga tushirish

### Variant A — Docker (server uchun tavsiya)

```bash
docker compose up -d --build      # ishga tushirish
docker compose logs -f            # loglarni ko'rish
docker compose down               # to'xtatish
```

### Variant B — to'g'ridan-to'g'ri Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python bot.py
```

### Variant C — systemd (Docker'siz, 24/7 server)

`/etc/systemd/system/antispam-bot.service`:

```ini
[Unit]
Description=Telegram Anti-Spam Bot
After=network.target

[Service]
WorkingDirectory=/opt/telegram-antispam-bot
ExecStart=/opt/telegram-antispam-bot/.venv/bin/python bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now antispam-bot
sudo journalctl -u antispam-bot -f
```

## 4-qadam: Guruhga qo'shish

1. Botni guruhga qo'shing.
2. Uni **admin** qiling, quyidagi huquqlar bilan:
   - ✅ Delete messages
   - ✅ Ban users
   - ✅ Restrict members (CAPTCHA uchun)

Tayyor! Yangi a'zolar CAPTCHA orqali o'tadi, spam xabarlar avto-o'chiriladi.

## Buyruqlar (guruh adminlari)

| Buyruq | Vazifa |
|--------|--------|
| `/stats` | Bot statistikasi. **Egasi** (`ADMIN_IDS`) — **barcha** guruhlar bo'yicha umumiy (shaxsiy chatда ham). **Oddiy guruh admini** — faqat **o'z guruhi** statistikasi. Har guruh: a'zolar soni + spam / ban / CAPTCHA hisobi. |
| `/words` | Bloklangan so'zlar ro'yxati |
| `/addword <so'z>` | Yangi so'z/ibora qo'shish |
| `/delword <so'z>` | Qo'shilgan so'zni o'chirish |
| `/ban` | Xabarga **reply** qilib foydalanuvchini ban qilish |

## Sozlamalar (.env)

| O'zgaruvchi | Tavsif | Default |
|-------------|--------|---------|
| `BOT_TOKEN` | @BotFather tokeni | — |
| `ADMIN_IDS` | Bot adminlari (vergul bilan ID) | bo'sh |
| `CAPTCHA_ENABLED` | CAPTCHA yoqilganmi | `true` |
| `CAPTCHA_TIMEOUT` | Tugma bosish vaqti (soniya) | `60` |
| `SPAM_ACTION` | `hybrid` (porn/phishing → ban, reklama → ogohlantirish) / `warn` (hammasi: o'chir + ogohlantir) / `ban` (hammasi: o'chir + ban) / `delete` (jim o'chir) | `hybrid` |
| `WARN_TEXT` | `warn` rejimi ogohlantirish matni (`{user}` → foydalanuvchi) | ⚠️ ...reklama tarqatmang |
| `WARN_DELETE_AFTER` | Ogohlantirish necha soniyada o'zi o'chsin (`0` = o'chmaydi) | `15` |
| `SPAM_THRESHOLD` | Harakat uchun kerakli ball | `3` |
| `NEW_USER_WINDOW` | "Yangi a'zo" oynasi (soniya) | `3600` |
| `DELETE_SERVICE_MESSAGES` | Kirish/chiqish xabarlarini o'chir | `true` |
| `NSFW_CHECK_ENABLED` | Profil rasmini lokal AI bilan tekshirish | `true` |
| `NSFW_THRESHOLD` | NSFW ishonch bo'sag'asi (0..1, kattaroq = ehtiyotkorroq) | `0.6` |
| `LOG_CHAT_ID` | Loglar uchun chat ID (ixtiyoriy) | bo'sh |

## Ball (score) tizimi qanday ishlaydi

| Signal | Ball |
|--------|------|
| Bloklangan so'z/ibora (har biri) | +2 |
| Intim emoji (😘🍑🔥💋…) | +1 |
| Link / @mention / kanal havolasi | +2 |
| Kanal/guruhdan forward | +2 |
| Yangi qo'shilgan a'zo | +1 |

Yig'indi `SPAM_THRESHOLD` (default 3) ga yetса harakat qilinadi. Misol:
`"Salom, profilimga o'ting va zavqlaning😘"` → 2+2+1 = **5** → o'chiriladi + ban.
