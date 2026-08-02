# ©️ ziahka, 2026
# This file is a part of Nimbus Userbot
# 🌐 https://github.com/ziahka/Nimbus
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

import collections
import logging
import time

from nimbustl.tl.types import Message
from nimbustl.utils import get_display_name

from .. import loader, utils

logger = logging.getLogger(__name__)

E_CHART = "<tg-emoji emoji-id=5411252368794746740>📈</tg-emoji>"
E_LOOK = "<tg-emoji emoji-id=5424885441100782420>👀</tg-emoji>"
E_CLOCK = "<tg-emoji emoji-id=5208622108191506906>🕗</tg-emoji>"
E_FOLDER = "<tg-emoji emoji-id=5256113064821926998>📁</tg-emoji>"
E_ERROR = "<tg-emoji emoji-id=5210952531676504517>🚫</tg-emoji>"

# Keyed in the order they're tested — the first match wins, since a voice note
# is also a document and a gif is also a video.
MEDIA_KINDS = (
    ("sticker", "🖼"),
    ("voice", "🎤"),
    ("video_note", "⭕️"),
    ("gif", "🎬"),
    ("photo", "📷"),
    ("video", "📹"),
    ("audio", "🎵"),
    ("document", "📄"),
)

MEDALS = ("🥇", "🥈", "🥉")


@loader.tds
class StatsMod(loader.Module):
    """Message statistics for the current chat"""

    strings = {
        "name": "Stats",
        "scanning": f"{E_LOOK} <b>Reading {{}} messages…</b> <code>{{}}</code>",
        "no_messages": f"{E_ERROR} <b>Nothing to count here.</b>",
        "header": (
            f"{E_CHART} <b>{{title}}</b>\n"
            "<blockquote><b>{total}</b> messages <b>·</b> <b>{people}</b> people"
            " <b>·</b> scanned in {elapsed}s</blockquote>"
        ),
        "top_header": "<b>Top posters</b>",
        "media_header": "<b>Media</b>",
        "hours_header": "<b>By hour</b> <i>(local time)</i>",
        "busiest": "Busiest hour: <b>{}:00</b>",
        "text_only": "<i>text only</i>",
    }

    strings_ru = {
        "scanning": f"{E_LOOK} <b>Читаю {{}} сообщений…</b> <code>{{}}</code>",
        "no_messages": f"{E_ERROR} <b>Тут нечего считать.</b>",
        "header": (
            f"{E_CHART} <b>{{title}}</b>\n"
            "<blockquote><b>{total}</b> сообщений <b>·</b> <b>{people}</b> человек"
            " <b>·</b> просканировано за {elapsed}с</blockquote>"
        ),
        "top_header": "<b>Самые активные</b>",
        "media_header": "<b>Медиа</b>",
        "hours_header": "<b>По часам</b> <i>(местное время)</i>",
        "busiest": "Пик активности: <b>{}:00</b>",
        "text_only": "<i>только текст</i>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "default_limit",
                1000,
                "How many messages to scan when no count is given",
                validator=loader.validators.Integer(minimum=10, maximum=50000),
            ),
            loader.ConfigValue(
                "top_size",
                10,
                "How many people to show in the leaderboard",
                validator=loader.validators.Integer(minimum=3, maximum=25),
            ),
            loader.ConfigValue(
                "bar_width",
                14,
                "Width of the leaderboard bars, in characters",
                validator=loader.validators.Integer(minimum=4, maximum=30),
            ),
        )

    @staticmethod
    def _classify(message: Message) -> str | None:
        for kind, _ in MEDIA_KINDS:
            if getattr(message, kind, None):
                return kind

        return None

    async def _name_for(self, uid: int) -> str:
        try:
            return utils.escape_html(
                get_display_name(await self._client.get_entity(uid)) or str(uid)
            )
        except Exception:
            logger.debug("Could not resolve sender %s", uid, exc_info=True)
            return f"<code>{uid}</code>"

    @loader.command(
        ru_doc="[кол-во] - Статистика сообщений в этом чате",
        en_doc="[count] - Message statistics for this chat",
        alias="cstat",
    )
    async def chatstat(self, message: Message):
        args = utils.get_args_raw(message)
        limit = self.config["default_limit"]

        if args.isdigit():
            limit = max(10, min(int(args), 50000))

        status = await utils.answer(
            message,
            self.strings["scanning"].format(limit, utils.progress_bar(0, 14)),
        )

        started = time.perf_counter()
        senders = collections.Counter()
        media = collections.Counter()
        hours = collections.Counter()
        total = 0

        async for msg in self._client.iter_messages(message.peer_id, limit=limit):
            total += 1
            if msg.sender_id:
                senders[msg.sender_id] += 1

            if kind := self._classify(msg):
                media[kind] += 1

            if msg.date:
                hours[msg.date.astimezone().hour] += 1

            # Editing on every message would hit the rate limiter instantly
            if total % 500 == 0:
                await utils.answer(
                    status,
                    self.strings["scanning"].format(
                        limit,
                        utils.progress_bar(total / limit * 100, 14),
                    ),
                )

        if not total:
            await utils.answer(status, self.strings["no_messages"])
            return

        elapsed = f"{time.perf_counter() - started:.1f}"
        top = senders.most_common(self.config["top_size"])
        leader = top[0][1] if top else 1
        width = self.config["bar_width"]

        rows = []
        for place, (uid, count) in enumerate(top):
            marker = MEDALS[place] if place < len(MEDALS) else f"<code>{place + 1:>2}</code>"
            rows.append(
                "{} <code>{}</code> <b>{}</b> <i>({:.1f}%)</i>\n     {}".format(
                    marker,
                    utils.progress_bar(count / leader * 100, width),
                    utils.humanize_number(count),
                    count / total * 100,
                    await self._name_for(uid),
                )
            )

        media_line = (
            " <b>·</b> ".join(
                f"{icon} {utils.humanize_number(media[kind])}"
                for kind, icon in MEDIA_KINDS
                if media[kind]
            )
            or self.strings["text_only"]
        )

        by_hour = [hours.get(hour, 0) for hour in range(24)]
        busiest = max(range(24), key=lambda hour: by_hour[hour])

        await utils.answer(
            status,
            "\n\n".join(
                [
                    self.strings["header"].format(
                        title=utils.escape_html(
                            get_display_name(await message.get_chat()) or "this chat"
                        ),
                        total=utils.humanize_number(total),
                        people=len(senders),
                        elapsed=elapsed,
                    ),
                    self.strings["top_header"] + "\n" + "\n".join(rows),
                    "{} {}\n<blockquote>{}</blockquote>".format(
                        E_FOLDER, self.strings["media_header"], media_line
                    ),
                    "{} {}\n<blockquote><code>{}</code>\n{}</blockquote>".format(
                        E_CLOCK,
                        self.strings["hours_header"],
                        utils.sparkline(by_hour),
                        self.strings["busiest"].format(f"{busiest:02d}"),
                    ),
                ]
            ),
        )
