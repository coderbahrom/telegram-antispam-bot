"""Spam aniqlash — ball (score) tizimi.

Har bir signal ball qo'shadi; yig'indi SPAM_THRESHOLD'ga yetса harakat qilinadi.
Bu yolg'on-pozitivni kamaytiradi: bitta shubhali so'z yetarli emas, bir nechta
signal birga kelishi kerak.
"""
import re

from aiogram.types import Message

from data.keywords import get_ban_keywords, get_keywords

# Apostrof variantlarini bitta belgiga keltirish (o'ting / oʻting / o`ting ...)
_APOST = str.maketrans({"`": "'", "ʻ": "'", "‘": "'", "’": "'", "´": "'", "ʼ": "'"})

# Ko'rinmas / zero-width / yo'nalish belgilari — spammerlar so'z ichiga
# (masalan "pro<zwnj><bom>filimga") qo'yib filtrni chalg'itadi. Olib tashlaymiz.
#   00ad soft hyphen | 180e | 200b-200f zwsp/zwnj/zwj/lrm/rlm
#   202a-202e yo'nalish | 2060-2064 word-joiner va h.k. | feff BOM
_INVISIBLE_RE = re.compile("[\u00ad\u180e\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff]")

# Aniq 18+ emojilar — porn signal (is_hard = ban). Oddiy/reklama xabarlarda uchramaydi.
_HARD_EMOJI = ["🔞", "🍑", "🍆", "💦", "👅"]
# Jozibali, lekin ko'p ma'noli emojilar (faqat +1, ban emas)
_SOFT_EMOJI = ["😘", "😍", "🥵", "🔥", "💋", "😏", "😉", "🌶", "🥰", "😈"]

# Link / mention / kanal havolasi
_URL_RE = re.compile(r"(https?://|www\.|t\.me/|telegram\.me/|telegra\.ph/|@[A-Za-z]\w{3,})", re.IGNORECASE)

# Maxfiy "invite" havolalari (t.me/+... , joinchat) — oddiy a'zolar kam ishlatadi,
# deyarli doim reklama/scam (tilдан qat'i nazar). Kuchli signal (+3, o'zi yetadi).
_INVITE_RE = re.compile(r"(t\.me/\+|t\.me/joinchat/|telegram\.me/\+|telegram\.me/joinchat/)", re.IGNORECASE)

# Pul-summa va'dasi: "14.000р", "5000₽", "$500", "от 5000 в день" — "yengil daromad"
# scamlarining asosiy belgisi (tilдан qat'i nazar). Link bilan birga kuchli signal.
_MONEY_RE = re.compile(
    r"\d[\d\s.,]{2,}\s*(?:₽|руб|р\b|сум|so['ʻ`]?m|\$|€|usd|долл)"
    r"|\bв\s+(?:день|неделю|месяц)\b",
    re.IGNORECASE,
)


def normalize(text: str) -> str:
    text = _INVISIBLE_RE.sub("", text)  # ko'rinmas belgilarni olib tashlash (filtr aldovi)
    # apostrof variantlarini olib tashlaymiz: "o'ting" va "oting" bir xil hisoblanadi
    text = text.translate(_APOST).lower().replace("'", "")
    return re.sub(r"\s+", " ", text).strip()


def score_text(text: str) -> tuple[int, list[str], bool]:
    """Matn (xabar/bio/ism) bo'yicha so'z + emoji bali. Link/forward bu yerga kirmaydi."""
    norm = normalize(text)
    score = 0
    reasons: list[str] = []
    is_hard = False
    ban_set = {normalize(k) for k in get_ban_keywords()}

    # bloklangan so'z/iboralar (har biri +2)
    for kw in get_keywords():
        nk = normalize(kw)
        if nk in norm:
            score += 2
            reasons.append(f"so'z:'{kw}'")
            if nk in ban_set:
                is_hard = True  # qattiq spam — hybrid rejimda ban

    # emoji: aniq 18+ → qattiq, jozibali → yumshoq
    if any(e in text for e in _HARD_EMOJI):
        score += 1
        reasons.append("emoji-18+")
        is_hard = True
    elif any(e in text for e in _SOFT_EMOJI):
        score += 1
        reasons.append("emoji")

    return score, reasons, is_hard


def profile_is_spam(*parts: str) -> tuple[bool, list[str]]:
    """Profil (ism + bio + shaxsiy kanal nomi) qattiq spam-mi? Faqat QATTIQ (porn/phishing)
    signalда True — oddiy/biznes bio (link, reklama) tufayli ban qilib qo'ymaslik uchun."""
    text = " ".join(p for p in parts if p).strip()
    if not text:
        return False, []
    _, reasons, is_hard = score_text(text)
    return is_hard, reasons


def score_message(message: Message) -> tuple[int, list[str], bool]:
    """Xabarning spam balini, sabablar ro'yxatini va `is_hard` (porn/phishing → ban) ni qaytaradi."""
    text = message.text or message.caption or ""
    score, reasons, is_hard = score_text(text)

    # 3) link / invite-link. Yashirin (text_link) havolalarni ham tekshiramiz.
    invite = bool(_INVITE_RE.search(text))
    has_link = bool(_URL_RE.search(text))
    for ent in (message.entities or []) + (message.caption_entities or []):
        if ent.type == "text_link" and ent.url and _INVITE_RE.search(ent.url):
            invite = True
        if ent.type in ("url", "text_link", "mention"):
            has_link = True
    if invite:
        score += 3
        reasons.append("invite-link")
    elif has_link:
        score += 2
        reasons.append("link")

    # pul-summa va'dasi (+2) — "yengil daromad" scam belgisi
    if _MONEY_RE.search(text):
        score += 2
        reasons.append("pul-summa")

    # 4) kanal/guruhdan forward qilingan post (+2) — reklama uchun klassik
    origin = getattr(message, "forward_origin", None)
    if origin is not None and origin.__class__.__name__ in ("MessageOriginChannel", "MessageOriginChat"):
        score += 2
        reasons.append("forward-kanal")
    elif getattr(message, "forward_from_chat", None) is not None:  # eski API bilan moslik
        score += 2
        reasons.append("forward-kanal")

    # 5) Forward qilingan STORY — bot uning ichini o'qiy olmaydi, guruhда deyarli
    #    doim spam/reklama (kripto, kanal reklamasi...). O'zi yetarli ball beramiz.
    if getattr(message, "story", None) is not None:
        score += 3
        reasons.append("forward-story")

    return score, reasons, is_hard
