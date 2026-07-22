"""Runtime holat — yangi qo'shilgan a'zolarni kuzatish (RAM ichida)."""
import time

# (chat_id, user_id) -> qo'shilgan vaqt (monotonic soniya)
_recent_joins: dict[tuple[int, int], float] = {}


def mark_join(chat_id: int, user_id: int) -> None:
    _recent_joins[(chat_id, user_id)] = time.monotonic()


def joined_recently(chat_id: int, user_id: int, window: int) -> bool:
    ts = _recent_joins.get((chat_id, user_id))
    return ts is not None and (time.monotonic() - ts) <= window


# Profili tekshirilgan userlar — har xabarда qayta API chaqirmaslik uchun (RAM)
_profile_checked: set[int] = set()


def profile_checked(user_id: int) -> bool:
    return user_id in _profile_checked


def mark_profile_checked(user_id: int) -> None:
    _profile_checked.add(user_id)
