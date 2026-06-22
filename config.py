"""Sozlamalar — .env faylidan o'qiladi."""
import os

from dotenv import load_dotenv

load_dotenv()


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on", "ha")


def _int(value: str | None, default: int) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _ids(value: str | None) -> set[int]:
    if not value:
        return set()
    out: set[int] = set()
    for part in value.replace(" ", "").split(","):
        if part:
            try:
                out.add(int(part))
            except ValueError:
                pass
    return out


BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS: set[int] = _ids(os.getenv("ADMIN_IDS"))

CAPTCHA_ENABLED: bool = _bool(os.getenv("CAPTCHA_ENABLED"), True)
CAPTCHA_TIMEOUT: int = _int(os.getenv("CAPTCHA_TIMEOUT"), 60)

SPAM_ACTION: str = os.getenv("SPAM_ACTION", "warn").strip().lower()
SPAM_THRESHOLD: int = _int(os.getenv("SPAM_THRESHOLD"), 3)
NEW_USER_WINDOW: int = _int(os.getenv("NEW_USER_WINDOW"), 3600)

# "warn" rejimida yuboriladigan ogohlantirish. {user} -> foydalanuvchi nomi.
WARN_TEXT: str = os.getenv(
    "WARN_TEXT",
    "⚠️ {user}, bu guruhда reklama/spam taqiqlangan. Iltimos, reklama tarqatmang.",
)
# Ogohlantirish necha soniyadan keyin o'zi o'chsin (0 = o'chmaydi)
WARN_DELETE_AFTER: int = _int(os.getenv("WARN_DELETE_AFTER"), 15)

DELETE_SERVICE_MESSAGES: bool = _bool(os.getenv("DELETE_SERVICE_MESSAGES"), True)

_log = os.getenv("LOG_CHAT_ID", "").strip()
LOG_CHAT_ID: int | None = int(_log) if _log.lstrip("-").isdigit() else None
