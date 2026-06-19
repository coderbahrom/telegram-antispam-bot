"""Statistika — bot qaysi guruhlarda ekani va harakat hisoblagichlari.

Ma'lumotlar data/ ichida JSON sifatida saqlanadi (volume orqali konteyner
qayta ishga tushganda ham yo'qolmaydi). RAM'da kesh — har xabarda diskka
yozilmaydi, faqat o'zgarganда yoziladi.
"""
import json
import os

_DIR = os.path.join(os.path.dirname(__file__), "data")
_GROUPS_PATH = os.path.join(_DIR, "groups.json")
_COUNTERS_PATH = os.path.join(_DIR, "counters.json")

_DEFAULT_COUNTERS = {
    "spam_deleted": 0,
    "banned": 0,
    "captcha_passed": 0,
    "captcha_kicked": 0,
}

_groups: dict[str, str] | None = None
_counters: dict[str, int] | None = None


def _load(path: str, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _save(path: str, data) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


# ---- Guruhlar ----
def get_groups() -> dict[str, str]:
    global _groups
    if _groups is None:
        loaded = _load(_GROUPS_PATH, {})
        _groups = loaded if isinstance(loaded, dict) else {}
    return _groups


def add_group(chat_id: int, title: str) -> None:
    groups = get_groups()
    key = str(chat_id)
    if groups.get(key) == title:
        return  # o'zgarmagan — yozmaymiz
    groups[key] = title
    _save(_GROUPS_PATH, groups)


def remove_group(chat_id: int) -> None:
    groups = get_groups()
    if groups.pop(str(chat_id), None) is not None:
        _save(_GROUPS_PATH, groups)


# ---- Hisoblagichlar ----
def get_counters() -> dict[str, int]:
    global _counters
    if _counters is None:
        _counters = dict(_DEFAULT_COUNTERS)
        loaded = _load(_COUNTERS_PATH, {})
        if isinstance(loaded, dict):
            _counters.update({k: int(v) for k, v in loaded.items() if k in _DEFAULT_COUNTERS})
    return _counters


def incr(key: str, n: int = 1) -> None:
    counters = get_counters()
    counters[key] = counters.get(key, 0) + n
    _save(_COUNTERS_PATH, counters)
