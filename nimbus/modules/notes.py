# ©️ ziahka, 2026
# This file is a part of Nimbus Userbot
# 🌐 https://github.com/ziahka/Nimbus
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

from nimbustl.tl.types import Message

from .. import loader, utils


@loader.tds
class NotesMod(loader.Module):
    """Saves and recalls text snippets by name"""

    strings = {
        "name": "Notes",
        "usage_save": (
            "<tg-emoji emoji-id=5870450390679425417>🗒</tg-emoji> <b>Usage:</b> <code>{prefix}save &lt;name&gt; &lt;text&gt;</code> "
            "or reply to a message with <code>{prefix}save &lt;name&gt;</code>"
        ),
        "nothing_to_save": "<tg-emoji emoji-id=5870450390679425417>🗒</tg-emoji> <b>Nothing to save</b> — give text or reply to a message",
        "saved": "<tg-emoji emoji-id=5870450390679425417>🗒</tg-emoji> <b>Note</b> <code>{name}</code> <b>saved.</b>",
        "usage_note": "<tg-emoji emoji-id=5870450390679425417>🗒</tg-emoji> <b>Usage:</b> <code>{prefix}note &lt;name&gt;</code>",
        "not_found": "<tg-emoji emoji-id=5870450390679425417>🗒</tg-emoji> <b>No note named</b> <code>{name}</code>",
        "no_notes": "<tg-emoji emoji-id=5870450390679425417>🗒</tg-emoji> <b>No saved notes yet.</b> Save one with <code>{prefix}save &lt;name&gt; &lt;text&gt;</code>",
        "notes_list": "<tg-emoji emoji-id=5870450390679425417>🗒</tg-emoji> <b>Saved notes ({count}):</b>\n{names}",
        "deleted": "<tg-emoji emoji-id=5870450390679425417>🗒</tg-emoji> <b>Note</b> <code>{name}</code> <b>deleted.</b>",
    }

    strings_ru = {
        "usage_save": (
            "<tg-emoji emoji-id=5870450390679425417>🗒</tg-emoji> <b>Использование:</b> <code>{prefix}save &lt;имя&gt; &lt;текст&gt;</code> "
            "или ответом на сообщение <code>{prefix}save &lt;имя&gt;</code>"
        ),
        "nothing_to_save": "<tg-emoji emoji-id=5870450390679425417>🗒</tg-emoji> <b>Нечего сохранять</b> — укажи текст или ответь на сообщение",
        "saved": "<tg-emoji emoji-id=5870450390679425417>🗒</tg-emoji> <b>Заметка</b> <code>{name}</code> <b>сохранена.</b>",
        "usage_note": "<tg-emoji emoji-id=5870450390679425417>🗒</tg-emoji> <b>Использование:</b> <code>{prefix}note &lt;имя&gt;</code>",
        "not_found": "<tg-emoji emoji-id=5870450390679425417>🗒</tg-emoji> <b>Нет заметки с именем</b> <code>{name}</code>",
        "no_notes": (
            "<tg-emoji emoji-id=5870450390679425417>🗒</tg-emoji> <b>Пока нет сохранённых заметок.</b> Сохрани через "
            "<code>{prefix}save &lt;имя&gt; &lt;текст&gt;</code>"
        ),
        "notes_list": "<tg-emoji emoji-id=5870450390679425417>🗒</tg-emoji> <b>Сохранённые заметки ({count}):</b>\n{names}",
        "deleted": "<tg-emoji emoji-id=5870450390679425417>🗒</tg-emoji> <b>Заметка</b> <code>{name}</code> <b>удалена.</b>",
    }

    @loader.command(
        ru_doc="<имя> [текст] - Сохранить заметку (текстом или ответом на сообщение)",
        en_doc="<name> [text] - Save a note (from text or a replied message)",
    )
    async def savecmd(self, message: Message):
        prefix = self.get_prefix()
        args = utils.get_args_raw(message)

        if not args:
            await utils.answer(message, self.strings["usage_save"].format(prefix=prefix))
            return

        parts = args.split(maxsplit=1)
        name = parts[0].lower()
        text = parts[1] if len(parts) > 1 else None

        if not text:
            reply = await message.get_reply_message()
            if not reply or not reply.raw_text:
                await utils.answer(message, self.strings["nothing_to_save"])
                return
            text = reply.raw_text

        self.pointer("notes", {})[name] = text
        await utils.answer(
            message, self.strings["saved"].format(name=utils.escape_html(name))
        )

    @loader.command(alias="n", ru_doc="<имя> - Отправить сохранённую заметку", en_doc="<name> - Send a saved note")
    async def notecmd(self, message: Message):
        prefix = self.get_prefix()
        name = utils.get_args_raw(message).lower()

        if not name:
            await utils.answer(message, self.strings["usage_note"].format(prefix=prefix))
            return

        notes = self.pointer("notes", {})
        if name not in notes:
            await utils.answer(
                message, self.strings["not_found"].format(name=utils.escape_html(name))
            )
            return

        await utils.answer(message, notes[name])

    @loader.command(ru_doc="Показать список сохранённых заметок", en_doc="Show the list of saved notes")
    async def notescmd(self, message: Message):
        prefix = self.get_prefix()
        notes = self.pointer("notes", {})

        if not notes:
            await utils.answer(message, self.strings["no_notes"].format(prefix=prefix))
            return

        names = "\n".join(
            f"• <code>{utils.escape_html(name)}</code>" for name in sorted(notes)
        )
        await utils.answer(
            message,
            self.strings["notes_list"].format(count=len(notes), names=names),
        )

    @loader.command(
        ru_doc="<имя> - Удалить сохранённую заметку",
        en_doc="<name> - Delete a saved note",
    )
    async def delnotecmd(self, message: Message):
        prefix = self.get_prefix()
        name = utils.get_args_raw(message).lower()
        notes = self.pointer("notes", {})

        if not name or name not in notes:
            await utils.answer(
                message,
                self.strings["not_found"].format(name=utils.escape_html(name))
                if name
                else self.strings["usage_note"].format(prefix=prefix),
            )
            return

        del notes[name]
        await utils.answer(
            message, self.strings["deleted"].format(name=utils.escape_html(name))
        )
