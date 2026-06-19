"""Spam aniqlash — ball (score) tizimi.

Har bir signal ball qo'shadi; yig'indi SPAM_THRESHOLD'ga yetса harakat qilinadi.
Bu yolg'on-pozitivni kamaytiradi: bitta shubhali so'z yetarli emas, bir nechta
signal birga kelishi kerak.
"""
import re

from aiogram.types import Message

from data.keywords import get_keywords

# Apostrof variantlarini bitta belgiga keltirish (o'ting / oʻting / o`ting ...)
_APOST = str.maketrans({"`": "'", "ʻ": "'", "‘": "'", "’": "'", "´": "'", "ʼ": "'"})

# Ko'rinmas / zero-width / yo'nalish belgilari — spammerlar so'z ichiga
# (masalan "pro<zwnj><bom>filimga") qo'yib filtrni chalg'itadi. Olib tashlaymiz.
#   00ad soft hyphen | 180e | 200b-200f zwsp/zwnj/zwj/lrm/rlm
#   202a-202e yo'nalish | 2060-2064 word-joiner va h.k. | feff BOM
_INVISIBLE_RE = re.compile("[\u00ad\u180e\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff]")

# Intim/jozibali emojilar (bittasi bo'lsa +1)
_SUGGESTIVE_EMOJI = ["😘", "😍", "🥵", "🍑", "🔥", "💋", "😏", "😉", "👅", "🍆", "💦", "🌶", "🥰", "😈"]

# Link / mention / kanal havolasi
_URL_RE = re.compile(r"(https?://|www\.|t\.me/|telegram\.me/|telegra\.ph/|@[A-Za-z]\w{3,})", re.IGNORECASE)


def normalize(text: str) -> str:
    text = _INVISIBLE_RE.sub("", text)  # ko'rinmas belgilarni olib tashlash (filtr aldovi)
    # apostrof variantlarini olib tashlaymiz: "o'ting" va "oting" bir xil hisoblanadi
    text = text.translate(_APOST).lower().replace("'", "")
    return re.sub(r"\s+", " ", text).strip()


def score_message(message: Message) -> tuple[int, list[str]]:
    """Xabarning spam balini va sabablar ro'yxatini qaytaradi."""
    text = message.text or message.caption or ""
    norm = normalize(text)
    score = 0
    reasons: list[str] = []

    # 1) bloklangan so'z/iboralar (har biri +2)
    for kw in get_keywords():
        if normalize(kw) in norm:
            score += 2
            reasons.append(f"so'z:'{kw}'")

    # 2) jozibali emoji (+1)
    if any(emoji in text for emoji in _SUGGESTIVE_EMOJI):
        score += 1
        reasons.append("emoji")

    # 3) link / @mention / kanal havolasi (+2)
    has_link = bool(_URL_RE.search(text))
    if not has_link:
        for ent in (message.entities or []) + (message.caption_entities or []):
            if ent.type in ("url", "text_link", "mention"):
                has_link = True
                break
    if has_link:
        score += 2
        reasons.append("link")

    # 4) kanal/guruhdan forward qilingan post (+2) — reklama uchun klassik
    origin = getattr(message, "forward_origin", None)
    if origin is not None and origin.__class__.__name__ in ("MessageOriginChannel", "MessageOriginChat"):
        score += 2
        reasons.append("forward-kanal")
    elif getattr(message, "forward_from_chat", None) is not None:  # eski API bilan moslik
        score += 2
        reasons.append("forward-kanal")

    return score, reasons
