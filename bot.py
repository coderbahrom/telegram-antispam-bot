"""Telegram Anti-Spam Bot — ishga tushiruvchi."""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import config
from handlers import admin, antispam, captcha, stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("antispam")


async def main() -> None:
    if not config.BOT_TOKEN:
        raise SystemExit("❌ BOT_TOKEN topilmadi. .env faylga BOT_TOKEN qo'ying (.env.example'dan nusxa oling).")

    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    # tartib muhim: buyruqlar avval, keyin captcha, oxirida umumiy filtr
    dp.include_router(admin.router)
    dp.include_router(stats.router)
    dp.include_router(captcha.router)
    dp.include_router(antispam.router)

    me = await bot.get_me()
    logger.info("✅ Bot ishga tushdi: @%s (id=%s)", me.username, me.id)
    logger.info(
        "Sozlamalar: CAPTCHA=%s (%ss), SPAM_ACTION=%s, THRESHOLD=%s",
        config.CAPTCHA_ENABLED, config.CAPTCHA_TIMEOUT, config.SPAM_ACTION, config.SPAM_THRESHOLD,
    )

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
