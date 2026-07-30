# meta developer: ziahka
# ©️ ziahka, 2026
# This file is a part of the Nimbus Userbot modules catalog
# 🌐 https://github.com/ziahka/Nimbus
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

import asyncio
import logging

from nimbustl.tl.types import Message

from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class BroadcastMod(loader.Module):
    """Sends a message to a saved list of chats"""

    strings = {
        "name": "Broadcast",
        "added": "📢 <b>This chat was added to the broadcast list.</b>",
        "already_added": "📢 <b>This chat is already in the broadcast list.</b>",
        "removed": "📢 <b>This chat was removed from the broadcast list.</b>",
        "not_in_list": "📢 <b>This chat isn't in the broadcast list.</b>",
        "empty_list": "📢 <b>Broadcast list is empty.</b> Add a chat with <code>{prefix}bcadd</code>",
        "list_header": "📢 <b>Broadcast list ({count}):</b>\n{items}",
        "usage": "📢 <b>Usage:</b> <code>{prefix}broadcast &lt;text&gt;</code>",
        "sending": "📢 <b>Sending to {count} chats...</b>",
        "done": "📢 <b>Sent to {ok} of {count} chats.</b>",
    }

    strings_ru = {
        "added": "📢 <b>Этот чат добавлен в список рассылки.</b>",
        "already_added": "📢 <b>Этот чат уже в списке рассылки.</b>",
        "removed": "📢 <b>Этот чат убран из списка рассылки.</b>",
        "not_in_list": "📢 <b>Этого чата нет в списке рассылки.</b>",
        "empty_list": "📢 <b>Список рассылки пуст.</b> Добавь чат через <code>{prefix}bcadd</code>",
        "list_header": "📢 <b>Список рассылки ({count}):</b>\n{items}",
        "usage": "📢 <b>Использование:</b> <code>{prefix}broadcast &lt;текст&gt;</code>",
        "sending": "📢 <b>Отправляю в {count} чатов...</b>",
        "done": "📢 <b>Отправлено в {ok} из {count} чатов.</b>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "delay",
                1.0,
                "Seconds to wait between sends, to avoid flood limits",
                validator=loader.validators.Float(minimum=0),
            ),
        )

    @loader.command(
        ru_doc="Добавить текущий чат в список рассылки",
        en_doc="Add the current chat to the broadcast list",
    )
    async def bcaddcmd(self, message: Message):
        chat_id = utils.get_chat_id(message)
        targets = self.pointer("targets", [])

        if chat_id in targets:
            await utils.answer(message, self.strings["already_added"])
            return

        targets.append(chat_id)
        await utils.answer(message, self.strings["added"])

    @loader.command(
        ru_doc="Убрать текущий чат из списка рассылки",
        en_doc="Remove the current chat from the broadcast list",
    )
    async def bcdelcmd(self, message: Message):
        chat_id = utils.get_chat_id(message)
        targets = self.pointer("targets", [])

        if chat_id not in targets:
            await utils.answer(message, self.strings["not_in_list"])
            return

        targets.remove(chat_id)
        await utils.answer(message, self.strings["removed"])

    @loader.command(
        ru_doc="Показать список рассылки",
        en_doc="Show the broadcast list",
    )
    async def bclistcmd(self, message: Message):
        prefix = self.get_prefix()
        targets = self.pointer("targets", [])

        if not targets:
            await utils.answer(message, self.strings["empty_list"].format(prefix=prefix))
            return

        items = "\n".join(f"• <code>{chat_id}</code>" for chat_id in targets)
        await utils.answer(
            message,
            self.strings["list_header"].format(count=len(targets), items=items),
        )

    @loader.command(
        ru_doc="<текст> - Отправить сообщение всем чатам из списка рассылки",
        en_doc="<text> - Send a message to every chat in the broadcast list",
    )
    async def broadcastcmd(self, message: Message):
        prefix = self.get_prefix()
        text = utils.get_args_raw(message)
        targets = self.pointer("targets", [])

        if not text:
            await utils.answer(message, self.strings["usage"].format(prefix=prefix))
            return

        if not targets:
            await utils.answer(message, self.strings["empty_list"].format(prefix=prefix))
            return

        message = await utils.answer(
            message, self.strings["sending"].format(count=len(targets))
        )

        ok = 0
        delay = self.config["delay"]
        for chat_id in list(targets):
            try:
                await self._client.send_message(chat_id, text)
                ok += 1
            except Exception:
                logger.exception("Failed to broadcast to %s", chat_id)

            await asyncio.sleep(delay)

        await utils.answer(
            message, self.strings["done"].format(ok=ok, count=len(targets))
        )
