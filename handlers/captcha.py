"""Qo'shilishda CAPTCHA: yangi a'zo cheklanadi, tugmani bosсa ochiladi,
vaqtida bosmasa chetlatiladi. Bu avtomatik spam-akkauntlarni to'xtatadi."""
import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.filters import JOIN_TRANSITION, ChatMemberUpdatedFilter
from aiogram.types import (
    CallbackQuery,
    ChatMemberUpdated,
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import config
import state
from utils import log_action

router = Router(name="captcha")
logger = logging.getLogger("antispam.captcha")

# (chat_id, user_id) -> kick taymeri (asyncio.Task)
_pending: dict[tuple[int, int], asyncio.Task] = {}

_MUTED = ChatPermissions(can_send_messages=False)
_UNMUTED = ChatPermissions(
    can_send_messages=True,
    can_send_audios=True,
    can_send_documents=True,
    can_send_photos=True,
    can_send_videos=True,
    can_send_video_notes=True,
    can_send_voice_notes=True,
    can_send_polls=True,
    can_send_other_messages=True,
    can_add_web_page_previews=True,
)


@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def on_join(event: ChatMemberUpdated, bot: Bot) -> None:
    user = event.new_chat_member.user
    chat = event.chat
    if user.is_bot:
        return

    state.mark_join(chat.id, user.id)
    if not config.CAPTCHA_ENABLED:
        return

    try:
        await bot.restrict_chat_member(chat.id, user.id, permissions=_MUTED)
    except Exception as exc:  # noqa: BLE001
        logger.warning("cheklash (mute) xato: %s — bot admin emas yoki huquqi yo'q?", exc)
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="✅ Men robot emasman", callback_data=f"captcha:{user.id}")]]
    )
    text = (
        f"👋 Xush kelibsiz, {user.mention_html()}!\n\n"
        f"Guruhda yozish uchun quyidagi tugmani <b>{config.CAPTCHA_TIMEOUT} soniya</b> ichida bosing."
    )
    try:
        msg = await bot.send_message(chat.id, text, reply_markup=keyboard)
    except Exception as exc:  # noqa: BLE001
        logger.warning("captcha xabarini yuborish xato: %s", exc)
        return

    _pending[(chat.id, user.id)] = asyncio.create_task(
        _kick_timer(bot, chat.id, user.id, msg.message_id, user.full_name)
    )


async def _kick_timer(bot: Bot, chat_id: int, user_id: int, msg_id: int, name: str) -> None:
    try:
        await asyncio.sleep(config.CAPTCHA_TIMEOUT)
        try:
            # ban + unban = kick (qayta kira oladi, lekin avto-spam to'xtaydi)
            await bot.ban_chat_member(chat_id, user_id)
            await bot.unban_chat_member(chat_id, user_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("kick xato: %s", exc)
        try:
            await bot.delete_message(chat_id, msg_id)
        except Exception:  # noqa: BLE001
            pass
        await log_action(bot, f"⏱ CAPTCHA o'tilmadi → chetlatildi: {name} <code>{user_id}</code>")
    except asyncio.CancelledError:
        pass
    finally:
        _pending.pop((chat_id, user_id), None)


@router.callback_query(F.data.startswith("captcha:"))
async def on_captcha_click(call: CallbackQuery, bot: Bot) -> None:
    try:
        target_id = int(call.data.split(":", 1)[1])
    except (ValueError, IndexError):
        return
    if call.from_user.id != target_id:
        await call.answer("Bu tugma sizga mo'ljallanmagan.", show_alert=True)
        return
    if call.message is None:
        await call.answer()
        return

    chat_id = call.message.chat.id
    try:
        await bot.restrict_chat_member(chat_id, target_id, permissions=_UNMUTED)
    except Exception as exc:  # noqa: BLE001
        logger.warning("ochish (unmute) xato: %s", exc)

    task = _pending.pop((chat_id, target_id), None)
    if task:
        task.cancel()
    try:
        await call.message.delete()
    except Exception:  # noqa: BLE001
        pass
    await call.answer("✅ Tasdiqlandi! Endi yozishingiz mumkin.")


@router.message(F.new_chat_members | F.left_chat_member)
async def clean_service_messages(message: Message) -> None:
    """Kirish/chiqish xizmat xabarlarini o'chirib, guruhni toza tutadi."""
    if not config.DELETE_SERVICE_MESSAGES:
        return
    try:
        await message.delete()
    except Exception:  # noqa: BLE001
        pass
