"""Admin buyruqlari: so'zlarni boshqarish va qo'lda ban."""
import logging

from aiogram import Bot, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from data.keywords import add_keyword, get_keywords, remove_keyword
from utils import can_control_bot, log_action

router = Router(name="admin")
logger = logging.getLogger("antispam.admin")

_HELP = (
    "🛡 <b>Anti-Spam Bot</b>\n\n"
    "Meni guruhga <b>admin</b> qiling — quyidagi huquqlar bilan:\n"
    "• Delete messages\n• Ban users\n• Restrict members\n\n"
    "<b>Buyruqlar (faqat guruh adminlari):</b>\n"
    "/stats — bot statistikasi (guruhlar, qamrov, ish hisobi)\n"
    "/words — bloklangan so'zlar ro'yxati\n"
    "/addword &lt;so'z&gt; — yangi so'z/ibora qo'shish\n"
    "/delword &lt;so'z&gt; — qo'shilgan so'zni o'chirish\n"
    "/ban — (xabarga <b>reply</b> qilib) foydalanuvchini ban qilish\n"
)


@router.message(Command("start", "help"))
async def cmd_start(message: Message) -> None:
    await message.answer(_HELP)


@router.message(Command("words"))
async def cmd_words(message: Message, bot: Bot) -> None:
    if not await can_control_bot(bot, message):
        return
    words = get_keywords()
    chunk = "\n".join(f"• {w}" for w in words)
    await message.answer(f"🔒 Bloklangan so'zlar ({len(words)} ta):\n{chunk}")


@router.message(Command("addword"))
async def cmd_addword(message: Message, command: CommandObject, bot: Bot) -> None:
    if not await can_control_bot(bot, message):
        return
    if not command.args:
        await message.answer("Foydalanish: <code>/addword so'z yoki ibora</code>")
        return
    if add_keyword(command.args):
        await message.answer(f"✅ Qo'shildi: <code>{command.args}</code>")
    else:
        await message.answer("Bu so'z allaqachon ro'yxatda.")


@router.message(Command("delword"))
async def cmd_delword(message: Message, command: CommandObject, bot: Bot) -> None:
    if not await can_control_bot(bot, message):
        return
    if not command.args:
        await message.answer("Foydalanish: <code>/delword so'z yoki ibora</code>")
        return
    if remove_keyword(command.args):
        await message.answer(f"🗑 O'chirildi: <code>{command.args}</code>")
    else:
        await message.answer("Bu so'z qo'shilganlar ro'yxatida yo'q (asosiy ro'yxatni o'chirib bo'lmaydi).")


@router.message(Command("ban"))
async def cmd_ban(message: Message, bot: Bot) -> None:
    if not await can_control_bot(bot, message):
        return
    if message.reply_to_message is None or message.reply_to_message.from_user is None:
        await message.answer("Ban qilish uchun foydalanuvchining xabariga <b>reply</b> qiling.")
        return
    target = message.reply_to_message.from_user
    try:
        await bot.ban_chat_member(message.chat.id, target.id)
        try:
            await message.reply_to_message.delete()
        except Exception:  # noqa: BLE001
            pass
        await message.answer(f"🚫 Ban qilindi: {target.mention_html()}")
        await log_action(bot, f"👮 Qo'lda ban: {target.full_name} <code>{target.id}</code>")
    except Exception as exc:  # noqa: BLE001
        await message.answer(f"Xatolik: <code>{exc}</code>")
