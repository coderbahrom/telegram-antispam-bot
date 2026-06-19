"""Yordamchi funksiyalar — admin tekshiruvi (cache bilan) va logging."""
import logging
import time

from aiogram import Bot
from aiogram.enums import ChatType
from aiogram.types import Message

import config

logger = logging.getLogger("antispam.utils")

# chat_id -> (amal qilish muddati, admin user id'lar)
_admin_cache: dict[int, tuple[float, set[int]]] = {}
_ADMIN_TTL = 300  # 5 daqiqa


async def _get_admins(bot: Bot, chat_id: int) -> set[int]:
    now = time.monotonic()
    cached = _admin_cache.get(chat_id)
    if cached and cached[0] > now:
        return cached[1]
    ids: set[int] = set()
    try:
        for member in await bot.get_chat_administrators(chat_id):
            ids.add(member.user.id)
    except Exception as exc:  # noqa: BLE001 — har qanday API xatosida cache'siz davom etamiz
        logger.warning("get_chat_administrators xato: %s", exc)
    _admin_cache[chat_id] = (now + _ADMIN_TTL, ids)
    return ids


async def is_admin_user(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Foydalanuvchi guruh admini yoki .env'dagi ADMIN_IDS'da bormi."""
    if user_id in config.ADMIN_IDS:
        return True
    return user_id in await _get_admins(bot, chat_id)


async def can_control_bot(bot: Bot, message: Message) -> bool:
    """Buyruq yuborgan kishi botni boshqara oladimi (admin buyruqlari uchun)."""
    user = message.from_user
    if user is None:
        return False
    if message.chat.type == ChatType.PRIVATE:
        return user.id in config.ADMIN_IDS
    return await is_admin_user(bot, message.chat.id, user.id)


async def log_action(bot: Bot, text: str) -> None:
    """Harakatni LOG_CHAT_ID'ga (agar berilgan bo'lsa) va konsolga yozadi."""
    logger.info(text.replace("\n", " | "))
    if config.LOG_CHAT_ID:
        try:
            await bot.send_message(config.LOG_CHAT_ID, text)
        except Exception as exc:  # noqa: BLE001
            logger.warning("log chatga yuborish xato: %s", exc)
