# meta developer: ziahka
# ©️ ziahka, 2026
# This file is a part of the Nimbus Userbot modules catalog
# 🌐 https://github.com/ziahka/Nimbus
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

from nimbustl.tl.types import Message

from .. import loader, utils

_MAX_COUNT = 200
_SCAN_LIMIT = 2000


@loader.tds
class PurgeMod(loader.Module):
    """Deletes your own recent messages in a chat"""

    strings = {
        "name": "Purge",
        "done": "🧹 <b>Deleted {count} messages.</b>",
        "nothing": "🧹 <b>Nothing to delete.</b>",
    }

    strings_ru = {
        "done": "🧹 <b>Удалено сообщений: {count}.</b>",
        "nothing": "🧹 <b>Нечего удалять.</b>",
    }

    @loader.command(
        ru_doc="[кол-во] - Удалить последние свои сообщения в чате (по умолчанию 10)",
        en_doc="[count] - Delete your own recent messages in this chat (default 10)",
    )
    async def purgecmd(self, message: Message):
        args = utils.get_args_raw(message)
        count = 10
        if args and args.isdigit():
            count = min(int(args), _MAX_COUNT)

        chat_id = utils.get_chat_id(message)
        ids = [message.id]

        async for msg in self._client.iter_messages(
            chat_id, from_user="me", limit=_SCAN_LIMIT
        ):
            if msg.id == message.id:
                continue
            ids.append(msg.id)
            if len(ids) - 1 >= count:
                break

        if len(ids) <= 1:
            await utils.answer(message, self.strings["nothing"])
            return

        await self._client.delete_messages(chat_id, ids)
        await self._client.send_message(
            chat_id, self.strings["done"].format(count=len(ids) - 1)
        )
