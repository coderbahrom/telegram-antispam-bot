"""Xabar filtri: spam balini hisoblab, kerak bo'lsa xabarni o'chiradi/ban qiladi."""
import logging

from aiogram import Bot, Router
from aiogram.enums import ChatType
from aiogram.types import Message

import config
import metrics
import state
from filters.spam import score_message
from utils import is_admin_user, log_action

router = Router(name="antispam")
logger = logging.getLogger("antispam.filter")


@router.message()
async def moderate(message: Message, bot: Bot) -> None:
    if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return
    # bot allaqachon turgan guruhlarni ham statistikaga olamiz (faqat o'zgarsa yoziladi)
    metrics.add_group(message.chat.id, message.chat.title or str(message.chat.id))
    # anonim admin / kanal nomidan yuborilgan xabarlarga tegmaymiz
    if message.sender_chat is not None:
        return
    user = message.from_user
    if user is None or user.is_bot:
        return
    # adminlarni tekshirmaymiz
    if await is_admin_user(bot, message.chat.id, user.id):
        return

    score, reasons = score_message(message)
    # yangi qo'shilgan a'zo bo'lsa qattiqroq qaraymiz (+1)
    if state.joined_recently(message.chat.id, user.id, config.NEW_USER_WINDOW):
        score += 1
        reasons.append("yangi a'zo")

    if score < config.SPAM_THRESHOLD:
        return

    try:
        await message.delete()
        metrics.incr("spam_deleted")
    except Exception as exc:  # noqa: BLE001
        logger.warning("xabarni o'chirish xato: %s", exc)

    action = "xabar o'chirildi"
    if config.SPAM_ACTION == "ban":
        try:
            await bot.ban_chat_member(message.chat.id, user.id)
            metrics.incr("banned")
            action = "o'chirildi + ban"
        except Exception as exc:  # noqa: BLE001
            logger.warning("ban xato: %s", exc)

    await log_action(
        bot,
        f"🚫 Spam ({action}, ball={score})\n"
        f"Foydalanuvchi: {user.mention_html()} <code>{user.id}</code>\n"
        f"Sabab: {', '.join(reasons)}",
    )
