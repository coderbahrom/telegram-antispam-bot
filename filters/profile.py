"""Profil "kombinatsiya" bali — yakka holда kuchsiz, birga kelganда spamга xos signallar.

"Salom" deb yozib, profilida 💞-kanal (ichida porn/invite-link) ko'tarib yuruvchi
akkauntlar uchun: matnда porn so'z yo'q, rasm texnik "yopiq" — lekin signallar
YIG'INDISI ularni oddiy foydalanuvchidan aniq ajratadi.
"""
import re

# Harf/raqam bormi (lotin, kirill) — bo'lmasa "faqat emoji" hisoblanadi
_HAS_TEXT_RE = re.compile(r"[A-Za-z0-9Ѐ-ӿ]")
_MENTION_RE = re.compile(r"@([A-Za-z0-9_]{4,})")


def is_gibberish(username: str | None) -> bool:
    """Username tasodifiy belgilar to'plamiga o'xshaydimi (@nn02xfa, @svkc9ymuoy).

    Oxiridagi raqamlar odatiy (dilnoza93) — faqat O'RTADAGI raqam, juda kam unli
    yoki 5+ undosh ketma-ketligi gibberish deb baholanadi.
    """
    if not username:
        return False
    name = username.strip().lstrip("@").lower()
    if len(name) < 5:
        return False
    core = name.rstrip("0123456789_")  # oxiridagi raqamlar normal
    if re.search(r"\d", core):  # o'rtada raqam: nn02xfa, w4zutttp
        return True
    letters = re.sub(r"[^a-z]", "", core)
    if len(letters) >= 5:
        vowels = sum(c in "aeiou" for c in letters)
        if vowels / len(letters) < 0.2:  # unlilar deyarli yo'q: svkcymt
            return True
    if re.search(r"[bcdfghjklmnpqrstvwxyz]{5,}", core):  # 5+ undosh qator
        return True
    return False


def is_emoji_only(title: str | None) -> bool:
    """Kanal nomi faqat emoji/belgilardan iboratmi ("💞💞") — matn umuman yo'q."""
    if not title:
        return False
    t = title.strip()
    return bool(t) and not _HAS_TEXT_RE.search(t)


def soft_profile_score(
    username: str | None,
    bio: str,
    channel_title: str | None,
    photo_suggestive: bool,
) -> tuple[int, list[str]]:
    """Zaif signallar yig'indisi. PROFILE_THRESHOLD'ga yetса — spam-profil."""
    score = 0
    reasons: list[str] = []

    if is_emoji_only(channel_title):
        score += 2
        reasons.append("kanal:faqat-emoji")

    bio = (bio or "").strip()
    mentions = _MENTION_RE.findall(bio)
    if bio and mentions and _MENTION_RE.sub("", bio).strip() == "":
        score += 1
        reasons.append("bio:faqat-mention")
    if any(is_gibberish(m) for m in mentions):
        score += 1
        reasons.append("bio:gibberish-mention")

    if is_gibberish(username):
        score += 1
        reasons.append("username:gibberish")

    if photo_suggestive:
        score += 1
        reasons.append("rasm:suggestive")

    return score, reasons
