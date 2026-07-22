"""Profil rasmini NSFW (18+) tekshirish — lokal NudeNet modeli.

Hammasi serverning o'zida ishlaydi: rasm vaqtinchalik faylga yuklanadi,
tekshiriladi va darhol o'chiriladi. Tashqi API yo'q, hech narsa chetga ketmaydi.
Model birinchi ishlatilганда yuklanadi (lazy) — bot start sekinlashmaydi.
"""
import asyncio
import logging
import os
import tempfile

from aiogram import Bot

import config

logger = logging.getLogger("antispam.nsfw")

_detector = None

# Faqat ANIQ 18+ klasslar — "bikini/ochiq kiyim" kabi chegaraviylar kirmaydi,
# real foydalanuvchilarni noto'g'ri ban qilmaslik uchun.
_NSFW_CLASSES = {
    "FEMALE_BREAST_EXPOSED",
    "FEMALE_GENITALIA_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
    "BUTTOCKS_EXPOSED",
    "ANUS_EXPOSED",
}


def _get_detector():
    global _detector
    if _detector is None:
        from nudenet import NudeDetector  # og'ir import — faqat kerak bo'lganda

        _detector = NudeDetector()
        logger.info("NudeNet modeli yuklandi")
    return _detector


def _detect_file(path: str) -> list[dict]:
    return _get_detector().detect(path)


async def is_nsfw_profile_photo(bot: Bot, user_id: int) -> tuple[bool, str]:
    """Foydalanuvchining profil rasmi 18+ bo'lsa (True, "rasm:...") qaytaradi."""
    if not config.NSFW_CHECK_ENABLED:
        return False, ""
    try:
        photos = await bot.get_user_profile_photos(user_id, limit=1)
    except Exception as exc:  # noqa: BLE001
        logger.debug("profil rasmini olish xato: %s", exc)
        return False, ""
    if not photos.photos:
        return False, ""  # rasm yo'q yoki maxfiylik yopiq

    # model kichik o'lchamda ishlaydi — ~640px atrofidagi versiyani olamiz (tez yuklanadi)
    sizes = photos.photos[0]
    photo = min(sizes, key=lambda p: abs(max(p.width, p.height) - 640))

    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    tmp.close()
    try:
        await bot.download(photo, destination=tmp.name)
        detections = await asyncio.get_running_loop().run_in_executor(None, _detect_file, tmp.name)
    except Exception as exc:  # noqa: BLE001
        logger.warning("NSFW tekshiruv xato: %s", exc)
        return False, ""
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    for d in detections or []:
        cls = d.get("class", "")
        score = float(d.get("score", 0))
        if cls in _NSFW_CLASSES and score >= config.NSFW_THRESHOLD:
            logger.info("NSFW rasm topildi: user=%s %s(%.2f)", user_id, cls, score)
            return True, f"rasm:{cls.lower()}({score:.2f})"
    return False, ""
