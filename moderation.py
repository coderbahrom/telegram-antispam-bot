"""Profil bo'yicha moderatsiya — guruh/kanal join'ida VA birinchi xabarда ishlatiladi.

Uch bosqich:
  1. Matn (ism + bio + kanal nomi) — porn/phishing so'z/emoji → darrov ban
  2. Rasm (lokal NudeNet) — aniq 18+ (EXPOSED) → darrov ban
  3. Kombinatsiya — zaif signallar yig'indisi (emoji-kanal, gibberish username,
     faqat-mention bio, suggestive rasm) PROFILE_THRESHOLD'ga yetса → ban
"""
import logging

from aiogram import Bot

import config
import metrics
from filters.nsfw import check_profile_photo
from filters.profile import soft_profile_score
from filters.spam import profile_is_spam
from utils import log_action

logger = logging.getLogger("antispam.moderation")


async def ban_if_profile_spam(bot: Bot, chat_id: int, user) -> bool:
    """Foydalanuvchi profili spam bo'lsa ban qiladi. True = ban qilindi."""
    bio = ""
    channel_title = None
    try:
        info = await bot.get_chat(user.id)
        bio = getattr(info, "bio", "") or ""
        personal = getattr(info, "personal_chat", None)
        if personal is not None:
            channel_title = personal.title or ""
    except Exception as exc:  # noqa: BLE001 — o'qib bo'lmasa, boshqa qatlamlar ishlayveradi
        logger.debug("profil o'qish xato: %s", exc)

    # 1) qattiq matn signallari
    is_spam, reasons = profile_is_spam(user.full_name or "", bio, channel_title or "")

    # 2) rasm: nsfw → darrov ban; suggestive → 3-bosqichga signal
    photo_verdict = "clean"
    if not is_spam:
        photo_verdict, why = await check_profile_photo(bot, user.id)
        if photo_verdict == "nsfw":
            is_spam, reasons = True, [why]

    # 3) kombinatsiya (zaif signallar yig'indisi)
    if not is_spam:
        pscore, preasons = soft_profile_score(
            user.username, bio, channel_title, photo_verdict == "suggestive"
        )
        if pscore >= config.PROFILE_THRESHOLD:
            is_spam, reasons = True, [f"profil-ball={pscore}"] + preasons

    if not is_spam:
        return False

    try:
        await bot.ban_chat_member(chat_id, user.id)
        metrics.incr(chat_id, "banned")
    except Exception as exc:  # noqa: BLE001
        logger.warning("profil-spam ban xato: %s — bot admin emas?", exc)
        return False
    await log_action(
        bot,
        f"🚫 Profil-spam ban: {user.full_name} <code>{user.id}</code> — {', '.join(reasons)}",
    )
    logger.info("Profil-spam ban: %s (%s) — %s", user.full_name, user.id, reasons)
    return True
