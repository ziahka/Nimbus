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

# Rotating each character 180° — the classic upside-down text trick
_FLIP = str.maketrans(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789,.?!'\"()[]{}<>&_",
    "ɐqɔpǝɟƃɥıɾʞlɯuodbɹsʇnʌʍxʎz∀qƆpƎℲƃHIſʞ˥WNOԀQɹS┴∩ΛMX⅄Z0ƖᄅƐㄣϛ9ㄥ86',¿¡,„)(][}{><⅋‾",
)

# Fullwidth forms live at a fixed offset from printable ASCII
_WIDE_OFFSET = 0xFEE0

_BUBBLE_UPPER = "ⒶⒷⒸⒹⒺⒻⒼⒽⒾⒿⓀⓁⓂⓃⓄⓅⓆⓇⓈⓉⓊⓋⓌⓍⓎⓏ"
_BUBBLE_LOWER = "ⓐⓑⓒⓓⓔⓕⓖⓗⓘⓙⓚⓛⓜⓝⓞⓟⓠⓡⓢⓣⓤⓥⓦⓧⓨⓩ"
_BUBBLE_DIGIT = "⓪①②③④⑤⑥⑦⑧⑨"


@loader.tds
class TextFXMod(loader.Module):
    """Text effects: typewriter, mocking case, upside-down, bubbles and more"""

    strings = {
        "name": "TextFX",
        "no_text": (
            "🚫 <b>Give me some text</b> — as an argument, or reply to a message."
        ),
        "too_long": "🚫 <b>Too long for a typewriter</b> (limit is {} characters).",
    }

    strings_ru = {
        "no_text": (
            "🚫 <b>Дай текст</b> — аргументом или ответом на сообщение."
        ),
        "too_long": "🚫 <b>Слишком длинно для печатной машинки</b> (лимит {} символов).",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "type_delay",
                0.3,
                "Seconds between typewriter frames. Below ~0.25 Telegram throttles",
                validator=loader.validators.Float(minimum=0.15, maximum=3.0),
            ),
            loader.ConfigValue(
                "type_limit",
                120,
                "Longest string .type will animate",
                validator=loader.validators.Integer(minimum=10, maximum=400),
            ),
            loader.ConfigValue(
                "type_cursor",
                "▮",
                "Cursor drawn at the end of each typewriter frame",
                validator=loader.validators.String(max_len=4),
            ),
        )

    async def _text_of(self, message: Message) -> str | None:
        if args := utils.get_args_raw(message):
            return args

        reply = await message.get_reply_message()
        return reply.raw_text if reply and reply.raw_text else None

    async def _transform(self, message: Message, func) -> None:
        text = await self._text_of(message)
        if not text:
            await utils.answer(message, self.strings["no_text"])
            return

        await utils.answer(message, utils.escape_html(func(text)))

    @loader.command(
        ru_doc="<текст> - Печатать текст по буквам",
        en_doc="<text> - Type the text out one character at a time",
    )
    async def type(self, message: Message):
        text = await self._text_of(message)
        if not text:
            await utils.answer(message, self.strings["no_text"])
            return

        limit = self.config["type_limit"]
        if len(text) > limit:
            await utils.answer(message, self.strings["too_long"].format(limit))
            return

        cursor = self.config["type_cursor"]
        delay = self.config["type_delay"]
        current = message

        for length in range(1, len(text) + 1):
            current = await utils.answer(
                current,
                utils.escape_html(text[:length] + cursor),
            )
            await asyncio.sleep(delay)

        await utils.answer(current, utils.escape_html(text))

    @loader.command(
        ru_doc="<текст> - тЕкСт ВоТ ТаКоЙ",
        en_doc="<text> - tExT lIkE tHiS",
    )
    async def mock(self, message: Message):
        await self._transform(
            message,
            lambda text: "".join(
                char.upper() if index % 2 else char.lower()
                for index, char in enumerate(text)
            ),
        )

    @loader.command(
        ru_doc="<текст> - Перевернуть текст вверх ногами",
        en_doc="<text> - Turn the text upside down",
    )
    async def flip(self, message: Message):
        await self._transform(
            message,
            lambda text: text.translate(_FLIP)[::-1],
        )

    @loader.command(
        ru_doc="<текст> - Ш и р о к и й  т е к с т",
        en_doc="<text> - Ｗｉｄｅ ｔｅｘｔ",
    )
    async def wide(self, message: Message):
        await self._transform(
            message,
            lambda text: "".join(
                chr(ord(char) + _WIDE_OFFSET) if "!" <= char <= "~" else char
                for char in text
            ),
        )

    @loader.command(
        ru_doc="<текст> - Ⓣⓔⓚⓢⓣ ⓥ ⓟⓤⓩⓨⓡⓨⓐⓗ",
        en_doc="<text> - Ⓣⓔⓧⓣ ⓘⓝ ⓑⓤⓑⓑⓛⓔⓢ",
    )
    async def bubble(self, message: Message):
        def bubbled(text: str) -> str:
            out = []
            for char in text:
                if "a" <= char <= "z":
                    out.append(_BUBBLE_LOWER[ord(char) - ord("a")])
                elif "A" <= char <= "Z":
                    out.append(_BUBBLE_UPPER[ord(char) - ord("A")])
                elif char.isdigit():
                    out.append(_BUBBLE_DIGIT[int(char)])
                else:
                    out.append(char)

            return "".join(out)

        await self._transform(message, bubbled)

    @loader.command(
        ru_doc="<текст> - Р а з р е ж е н н ы й   т е к с т",
        en_doc="<text> - S p a c e d   o u t   t e x t",
    )
    async def spaced(self, message: Message):
        await self._transform(message, lambda text: " ".join(text))
