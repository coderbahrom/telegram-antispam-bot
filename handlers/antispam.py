"""Xabar filtri: spam balini hisoblab, kerak bo'lsa xabarni o'chiradi/ogohlantiradi/ban qiladi."""
import asyncio
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


async def _delete_later(bot: Bot, chat_id: int, message_id: int, delay: int) -> None:
    try:
        await asyncio.sleep(delay)
        await bot.delete_message(chat_id, message_id)
    except Exception:  # noqa: BLE001
        pass


async def _send_warning(bot: Bot, chat_id: int, user) -> None:
    """Ogohlantirish yuboradi va (sozlamaga ko'ra) bir necha soniyada o'zini o'chiradi."""
    text = config.WARN_TEXT.replace("{user}", user.mention_html())
    try:
        msg = await bot.send_message(chat_id, text)
    except Exception as exc:  # noqa: BLE001
        logger.warning("ogohlantirish yuborish xato: %s", exc)
        return
    if config.WARN_DELETE_AFTER > 0:
        asyncio.create_task(_delete_later(bot, chat_id, msg.message_id, config.WARN_DELETE_AFTER))


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
        metrics.incr(message.chat.id, "spam_deleted")
    except Exception as exc:  # noqa: BLE001
        logger.warning("xabarni o'chirish xato: %s", exc)

    action = "xabar o'chirildi"
    if config.SPAM_ACTION == "ban":
        try:
            await bot.ban_chat_member(message.chat.id, user.id)
            metrics.incr(message.chat.id, "banned")
            action = "o'chirildi + ban"
        except Exception as exc:  # noqa: BLE001
            logger.warning("ban xato: %s", exc)
    elif config.SPAM_ACTION == "warn":
        await _send_warning(bot, message.chat.id, user)
        metrics.incr(message.chat.id, "warned")
        action = "o'chirildi + ogohlantirildi"

    await log_action(
        bot,
        f"🚫 Spam ({action}, ball={score})\n"
        f"Foydalanuvchi: {user.mention_html()} <code>{user.id}</code>\n"
        f"Sabab: {', '.join(reasons)}",
    )
