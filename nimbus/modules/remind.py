# ©️ ziahka, 2026
# This file is a part of Nimbus Userbot
# 🌐 https://github.com/ziahka/Nimbus
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

import logging
import re
import time

from nimbustl.tl.types import Message

from .. import loader, utils

logger = logging.getLogger(__name__)

_DURATION = re.compile(r"(\d+)\s*([smhdw])", re.IGNORECASE)
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}


def _parse_duration(raw: str) -> int:
    total = sum(
        int(amount) * _UNIT_SECONDS[unit.lower()]
        for amount, unit in _DURATION.findall(raw)
    )
    return total


@loader.tds
class RemindMod(loader.Module):
    """Reminds you about something after a delay"""

    strings = {
        "name": "Remind",
        "usage": (
            "<tg-emoji emoji-id=5877458226823302157>🕒</tg-emoji> <b>Usage:</b> <code>{prefix}remind &lt;time&gt; &lt;text&gt;</code>\n"
            "<i>Time examples: 10m, 2h, 1d, 1d2h30m</i>"
        ),
        "set": "<tg-emoji emoji-id=5877458226823302157>🕒</tg-emoji> <b>Reminder #{id} set for {duration} from now.</b>",
        "fired": "<tg-emoji emoji-id=5877458226823302157>🕒</tg-emoji> <b>Reminder!</b>\n{text}",
        "no_reminders": "<tg-emoji emoji-id=5877458226823302157>🕒</tg-emoji> <b>No pending reminders.</b>",
        "list_header": "<tg-emoji emoji-id=5877458226823302157>🕒</tg-emoji> <b>Pending reminders ({count}):</b>\n{items}",
        "usage_del": "<tg-emoji emoji-id=5877458226823302157>🕒</tg-emoji> <b>Usage:</b> <code>{prefix}delremind &lt;id&gt;</code>",
        "not_found": "<tg-emoji emoji-id=5877458226823302157>🕒</tg-emoji> <b>No pending reminder with id</b> <code>{id}</code>",
        "deleted": "<tg-emoji emoji-id=5877458226823302157>🕒</tg-emoji> <b>Reminder #{id} cancelled.</b>",
    }

    strings_ru = {
        "usage": (
            "<tg-emoji emoji-id=5877458226823302157>🕒</tg-emoji> <b>Использование:</b> <code>{prefix}remind &lt;время&gt; &lt;текст&gt;</code>\n"
            "<i>Примеры времени: 10m, 2h, 1d, 1d2h30m</i>"
        ),
        "set": "<tg-emoji emoji-id=5877458226823302157>🕒</tg-emoji> <b>Напоминание #{id} установлено через {duration}.</b>",
        "fired": "<tg-emoji emoji-id=5877458226823302157>🕒</tg-emoji> <b>Напоминание!</b>\n{text}",
        "no_reminders": "<tg-emoji emoji-id=5877458226823302157>🕒</tg-emoji> <b>Нет активных напоминаний.</b>",
        "list_header": "<tg-emoji emoji-id=5877458226823302157>🕒</tg-emoji> <b>Активные напоминания ({count}):</b>\n{items}",
        "usage_del": "<tg-emoji emoji-id=5877458226823302157>🕒</tg-emoji> <b>Использование:</b> <code>{prefix}delremind &lt;id&gt;</code>",
        "not_found": "<tg-emoji emoji-id=5877458226823302157>🕒</tg-emoji> <b>Нет напоминания с id</b> <code>{id}</code>",
        "deleted": "<tg-emoji emoji-id=5877458226823302157>🕒</tg-emoji> <b>Напоминание #{id} отменено.</b>",
    }

    @loader.command(
        ru_doc="<время> <текст> - Напомнить о чём-либо через заданное время",
        en_doc="<time> <text> - Remind yourself about something after a delay",
    )
    async def remindcmd(self, message: Message):
        prefix = self.get_prefix()
        args = utils.get_args_raw(message)

        parts = args.split(maxsplit=1) if args else []
        duration = _parse_duration(parts[0]) if parts else 0
        text = parts[1] if len(parts) > 1 else ""

        if not duration or not text:
            await utils.answer(message, self.strings["usage"].format(prefix=prefix))
            return

        reminder_id = self.get("next_id", 1)
        self.set("next_id", reminder_id + 1)

        self.pointer("reminders", []).append(
            {
                "id": reminder_id,
                "chat_id": utils.get_chat_id(message),
                "text": text,
                "due": time.time() + duration,
            }
        )

        await utils.answer(
            message,
            self.strings["set"].format(
                id=reminder_id, duration=utils.format_duration(duration)
            ),
        )

    @loader.command(
        ru_doc="Показать список активных напоминаний",
        en_doc="Show pending reminders",
    )
    async def reminderscmd(self, message: Message):
        reminders = self.pointer("reminders", [])

        if not reminders:
            await utils.answer(message, self.strings["no_reminders"])
            return

        now = time.time()
        items = "\n".join(
            f"• <code>#{r['id']}</code> in {utils.format_duration(max(r['due'] - now, 0))}"
            f" — {utils.escape_html(r['text'])}"
            for r in sorted(reminders, key=lambda r: r["due"])
        )

        await utils.answer(
            message,
            self.strings["list_header"].format(count=len(reminders), items=items),
        )

    @loader.command(
        ru_doc="<id> - Отменить напоминание",
        en_doc="<id> - Cancel a pending reminder",
    )
    async def delremindcmd(self, message: Message):
        prefix = self.get_prefix()
        args = utils.get_args_raw(message)

        if not args or not args.isdigit():
            await utils.answer(message, self.strings["usage_del"].format(prefix=prefix))
            return

        reminder_id = int(args)
        reminders = self.pointer("reminders", [])
        match = next((r for r in reminders if r["id"] == reminder_id), None)

        if not match:
            await utils.answer(message, self.strings["not_found"].format(id=reminder_id))
            return

        reminders.remove(match)
        await utils.answer(message, self.strings["deleted"].format(id=reminder_id))

    @loader.loop(interval=15, autostart=True)
    async def _checker(self):
        reminders = self.pointer("reminders", [])
        now = time.time()
        due = [r for r in reminders if r["due"] <= now]

        for r in due:
            try:
                await self._client.send_message(
                    r["chat_id"],
                    self.strings["fired"].format(text=utils.escape_html(r["text"])),
                )
            except Exception:
                logger.exception("Failed to deliver reminder #%s", r["id"])
            finally:
                if r in reminders:
                    reminders.remove(r)
