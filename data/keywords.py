"""Bloklangan so'zlar/iboralar.

DEFAULT_KEYWORDS — kodga yozilgan asosiy ro'yxat (git'ga tushadi).
Runtime'da /addword orqali qo'shilganlari custom_keywords.json ga yoziladi
(u .gitignore'da — har bir guruh o'ziniki qo'shadi).

Eslatma: bittalik shubhali so'z (masalan "seks") tahdid solib qolishi mumkin,
shuning uchun u yolg'iz harakatga sabab bo'lmaydi — score tizimi uni boshqa
signal (emoji/link) bilan birga hisoblaydi (qarang: filters/spam.py).
"""
import json
import os

_DIR = os.path.dirname(__file__)
_CUSTOM_PATH = os.path.join(_DIR, "custom_keywords.json")

# "Qattiq" so'zlar — porn / phishing / profil-spam. hybrid rejimda BAN qilinadi.
BAN_KEYWORDS: list[str] = [
    # "profilim..." turidagi klassik phishing. O'zak shakl barcha ko'rinishlarni tutadi:
    # profilimga / profilimda / profilimni / profilim sizni ... (apostrof + ko'rinmas
    # belgilar normalize'da olib tashlanadi). Yolg'iz +2 — harakatga 2-signal kerak.
    "profilim",
    "akkauntim",
    # zavq / intim
    "zavqlaning",
    "zavq olasiz",
    "rohatlaning",
    # intim video
    "eng sokin video",
    "sokin videom",
    "eng issiq video",
    "issiq videom",
    "videolarimni kor",
    "videomni kor",
    # ochiq mazmun
    "seks",
    "porno",
    "porn",
    "intim",
    "18+",
    "kattalar uchun",
    "erotik",
    # profil/bio porn-spam (masalan "joylar cheklangan 🔞", "HotVideolarim24")
    "joylar cheklangan",
    "videolarim",
    "hotvideo",
    "hot video",
]

# "Yumshoq" so'zlar — oddiy reklama. hybrid rejimda faqat OGOHLANTIRILADI.
AD_KEYWORDS: list[str] = [
    "kanalimga o'ting",
    "kanalimga obuna",
    "kanalimga kir",
    "obuna bol",
    "tezkor pul",
    "pul ishlash",
    "investitsiya",
    "investment",
    "daromad qiling",
    # kripto firibgarlik (ko'pincha inglizcha)
    "crypto",
    "kripto",
    "bitcoin",
    "pump",
    "signal",
    "trading",
    "binance",
    "usdt",
    "sarmoya",
    # ruscha "yengil daromad / yozgi ish" scam (o'zak shakl barcha ko'rinishni tutadi)
    "зараб",            # заработок / заработай / зарабатывай / заработать
    "подработ",         # подработка / подработать
    "доход",
    "вакансия",
    "вложен",           # вложений / вложения (investitsiya)
    "удалённая работа",
    "удаленная работа",
    "места ограничен",  # "Места ограничены" — sun'iy shoshilinch
    "пиши в личку",
]

# Ballash uchun barcha asosiy so'zlar
DEFAULT_KEYWORDS: list[str] = BAN_KEYWORDS + AD_KEYWORDS


def _load_custom() -> list[str]:
    if not os.path.exists(_CUSTOM_PATH):
        return []
    try:
        with open(_CUSTOM_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return [str(x) for x in data] if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _save_custom(words: list[str]) -> None:
    with open(_CUSTOM_PATH, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=2)


def get_keywords() -> list[str]:
    """Ballash uchun barcha so'zlar: asosiy + custom (takrorlanmasdan)."""
    seen: list[str] = []
    for w in DEFAULT_KEYWORDS + _load_custom():
        if w not in seen:
            seen.append(w)
    return seen


def get_ban_keywords() -> list[str]:
    """hybrid rejimda BAN qiladigan "qattiq" so'zlar: porn/phishing + qo'lda qo'shilganlar."""
    seen: list[str] = []
    for w in BAN_KEYWORDS + _load_custom():
        if w not in seen:
            seen.append(w)
    return seen


def add_keyword(word: str) -> bool:
    word = word.strip().lower()
    if not word:
        return False
    custom = _load_custom()
    if word in custom or word in DEFAULT_KEYWORDS:
        return False
    custom.append(word)
    _save_custom(custom)
    return True


def remove_keyword(word: str) -> bool:
    """Faqat custom (qo'lda qo'shilgan) so'zni o'chiradi."""
    word = word.strip().lower()
    custom = _load_custom()
    if word not in custom:
        return False
    custom.remove(word)
    _save_custom(custom)
    return True
