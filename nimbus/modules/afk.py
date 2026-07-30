# ©️ ziahka, 2026
# This file is a part of Nimbus Userbot
# 🌐 https://github.com/ziahka/Nimbus
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

import time

from nimbustl.tl.types import Message

from .. import loader, utils


@loader.tds
class AFKMod(loader.Module):
    """Auto-replies to messages while you're away"""

    strings = {
        "name": "AFK",
        "now_afk": "🌙 <b>AFK mode enabled.</b>\n<i>{reason}</i>",
        "now_afk_no_reason": "🌙 <b>AFK mode enabled.</b>",
        "no_longer_afk": "☀️ <b>AFK mode disabled.</b> You were away for {duration}.",
        "not_afk": "☀️ <b>You're not AFK.</b>",
        "reply_reason": (
            "🌙 <b>I'm AFK right now</b> (away for {duration}).\n<i>{reason}</i>"
        ),
        "reply_no_reason": "🌙 <b>I'm AFK right now</b> (away for {duration}).",
    }

    strings_ru = {
        "now_afk": "🌙 <b>Режим АФК включён.</b>\n<i>{reason}</i>",
        "now_afk_no_reason": "🌙 <b>Режим АФК включён.</b>",
        "no_longer_afk": "☀️ <b>Режим АФК выключен.</b> Отсутствие длилось {duration}.",
        "not_afk": "☀️ <b>Ты не в АФК.</b>",
        "reply_reason": (
            "🌙 <b>Сейчас меня нет на месте</b> (отсутствую уже {duration}).\n<i>{reason}</i>"
        ),
        "reply_no_reason": (
            "🌙 <b>Сейчас меня нет на месте</b> (отсутствую уже {duration})."
        ),
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "cooldown",
                600,
                "Seconds to wait before replying again in the same chat",
                validator=loader.validators.Integer(minimum=0),
            ),
            loader.ConfigValue(
                "reply_in_groups",
                False,
                "Reply to every message in groups, not just PMs and mentions",
                validator=loader.validators.Boolean(),
            ),
        )

    def _eligible(self, message: Message) -> bool:
        if getattr(message, "is_private", False):
            return True

        if getattr(message, "mentioned", False):
            return True

        return bool(self.config["reply_in_groups"])

    @loader.command(
        ru_doc="[причина] - Включить режим АФК",
        en_doc="[reason] - Enable AFK mode",
    )
    async def afkcmd(self, message: Message):
        reason = utils.get_args_raw(message)

        self.set("enabled", True)
        self.set("reason", reason)
        self.set("since", time.time())
        self.pointer("replied", {}).clear()

        await utils.answer(
            message,
            self.strings["now_afk"].format(reason=utils.escape_html(reason))
            if reason
            else self.strings["now_afk_no_reason"],
        )

    @loader.command(
        ru_doc="Выключить режим АФК",
        en_doc="Disable AFK mode",
    )
    async def unafkcmd(self, message: Message):
        if not self.get("enabled", False):
            await utils.answer(message, self.strings["not_afk"])
            return

        duration = utils.format_duration(time.time() - self.get("since", time.time()))
        self.set("enabled", False)

        await utils.answer(
            message, self.strings["no_longer_afk"].format(duration=duration)
        )

    @loader.watcher("out", "no_commands")
    async def _turn_off_watcher(self, message: Message):
        if self.get("enabled", False):
            self.set("enabled", False)

    @loader.watcher("in", "no_commands")
    async def _reply_watcher(self, message: Message):
        if not self.get("enabled", False):
            return

        if getattr(message, "via_bot_id", False):
            return

        if not self._eligible(message):
            return

        chat_id = str(utils.get_chat_id(message))
        replied = self.pointer("replied", {})
        cooldown = self.config["cooldown"]
        now = time.time()

        if now - replied.get(chat_id, 0) < cooldown:
            return

        replied[chat_id] = now

        reason = self.get("reason", "")
        duration = utils.format_duration(now - self.get("since", now))

        await message.reply(
            self.strings["reply_reason"].format(
                duration=duration, reason=utils.escape_html(reason)
            )
            if reason
            else self.strings["reply_no_reason"].format(duration=duration)
        )
