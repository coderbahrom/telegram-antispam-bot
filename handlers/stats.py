"""/stats — bot qaysi guruhlarda, qancha a'zoni qamragan va nima ish qilgan."""
import logging

from aiogram import Bot, Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import ChatMemberUpdated, Message

import config
import metrics
from utils import can_control_bot

router = Router(name="stats")
logger = logging.getLogger("antispam.stats")

_ACTIVE = {"member", "administrator"}


@router.my_chat_member()
async def on_bot_status_change(event: ChatMemberUpdated) -> None:
    """Bot guruhga qo'shilganda/chiqarilganda guruhlar ro'yxatini yangilaydi."""
    if event.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return
    if event.new_chat_member.status in _ACTIVE:
        metrics.add_group(event.chat.id, event.chat.title or str(event.chat.id))
        logger.info("Guruhga qo'shildi: %s (%s)", event.chat.title, event.chat.id)
    else:  # left / kicked
        metrics.remove_group(event.chat.id)
        logger.info("Guruhdan chiqdi: %s (%s)", event.chat.title, event.chat.id)


def _counters_block(c: dict[str, int]) -> str:
    return (
        "🛡 <b>Bajarilgan ishlar:</b>\n"
        f"• Spam o'chirildi: {c['spam_deleted']}\n"
        f"• Ban qilindi: {c['banned']}\n"
        f"• CAPTCHA o'tdi: {c['captcha_passed']}\n"
        f"• CAPTCHA chetlatildi: {c['captcha_kicked']}"
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message, bot: Bot) -> None:
    if not await can_control_bot(bot, message):
        return

    is_owner = message.from_user is not None and message.from_user.id in config.ADMIN_IDS

    if is_owner:
        # EGASI — barcha guruhlar bo'yicha umumiy ko'rinish
        groups = metrics.get_groups()
        lines: list[str] = []
        total_members = 0
        for cid, title in groups.items():
            try:
                count = await bot.get_chat_member_count(int(cid))
            except Exception:  # noqa: BLE001 — botni chiqarib yuborgan bo'lishi mumkin
                count = 0
            total_members += count
            gc = metrics.get_counters(int(cid))
            lines.append(f"• {title}: <b>{count}</b> a'zo — {gc['spam_deleted']} spam")
        text = (
            "📊 <b>Bot statistikasi — umumiy (egasi)</b>\n\n"
            f"Guruhlar soni: <b>{len(groups)}</b>\n"
            f"Jami a'zolar (qamrov): <b>{total_members}</b>\n\n"
            + ("\n".join(lines) if lines else "<i>Hali guruh qo'shilmagan</i>")
            + "\n\n"
            + _counters_block(metrics.get_total_counters())
        )
        await message.answer(text)
        return

    # ODDIY GURUH ADMINI — faqat shu guruh statistikasi
    if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.answer("Bu buyruq guruh ichida ishlaydi.")
        return
    try:
        count = await bot.get_chat_member_count(message.chat.id)
    except Exception:  # noqa: BLE001
        count = 0
    text = (
        f"📊 <b>{message.chat.title} — statistika</b>\n\n"
        f"A'zolar: <b>{count}</b>\n\n"
        + _counters_block(metrics.get_counters(message.chat.id))
    )
    await message.answer(text)
