"""/stats — bot qaysi guruhlarda, qancha a'zoni qamragan va nima ish qilgan."""
import logging

from aiogram import Bot, Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import ChatMemberUpdated, Message

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


@router.message(Command("stats"))
async def cmd_stats(message: Message, bot: Bot) -> None:
    if not await can_control_bot(bot, message):
        return
    groups = metrics.get_groups()
    lines: list[str] = []
    total = 0
    for cid, title in groups.items():
        try:
            count = await bot.get_chat_member_count(int(cid))
        except Exception:  # noqa: BLE001 — botni chiqarib yuborgan bo'lishi mumkin
            count = 0
        total += count
        lines.append(f"• {title}: <b>{count}</b> a'zo")

    c = metrics.get_counters()
    text = (
        "📊 <b>Bot statistikasi</b>\n\n"
        f"Guruhlar soni: <b>{len(groups)}</b>\n"
        f"Jami a'zolar (qamrov): <b>{total}</b>\n\n"
        + ("\n".join(lines) if lines else "<i>Hali guruh qo'shilmagan</i>")
        + "\n\n🛡 <b>Bajarilgan ishlar:</b>\n"
        f"• Spam o'chirildi: {c['spam_deleted']}\n"
        f"• Ban qilindi: {c['banned']}\n"
        f"• CAPTCHA o'tdi: {c['captcha_passed']}\n"
        f"• CAPTCHA chetlatildi: {c['captcha_kicked']}"
    )
    await message.answer(text)
