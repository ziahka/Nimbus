# ©️ ziahka, 2026
# This file is a part of Nimbus Userbot
# 🌐 https://github.com/ziahka/Nimbus
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

import logging

from nimbustl.tl.functions.channels import GetFullChannelRequest
from nimbustl.tl.functions.users import GetFullUserRequest
from nimbustl.tl.types import Channel, Chat, Message, User
from nimbustl.utils import get_display_name

from .. import loader, utils

logger = logging.getLogger(__name__)

E_USER = "<tg-emoji emoji-id=5424885441100782420>👀</tg-emoji>"
E_CHAT = "<tg-emoji emoji-id=5188377234380954537>🪐</tg-emoji>"
E_ID = "<tg-emoji emoji-id=5431736674147114227>📦</tg-emoji>"
E_LINK = "<tg-emoji emoji-id=4916086774649848789>🔗</tg-emoji>"
E_NOTE = "<tg-emoji emoji-id=5870450390679425417>🗒</tg-emoji>"
E_FLAG = "<tg-emoji emoji-id=5312383351217201533>⚠️</tg-emoji>"
E_ERROR = "<tg-emoji emoji-id=5210952531676504517>🚫</tg-emoji>"

# Attribute -> label, rendered as a badge row when the flag is set
USER_FLAGS = (
    ("premium", "premium"),
    ("verified", "verified"),
    ("scam", "scam"),
    ("fake", "fake"),
    ("bot", "bot"),
    ("restricted", "restricted"),
    ("deleted", "deleted"),
    ("support", "support"),
)

CHAT_FLAGS = (
    ("verified", "verified"),
    ("scam", "scam"),
    ("fake", "fake"),
    ("megagroup", "supergroup"),
    ("broadcast", "channel"),
    ("gigagroup", "gigagroup"),
    ("restricted", "restricted"),
    ("creator", "you own it"),
)


@loader.tds
class WhoisMod(loader.Module):
    """Detailed card for any user, chat or channel"""

    strings = {
        "name": "Whois",
        "not_found": f"{E_ERROR} <b>Could not resolve that.</b>",
        "user_card": (
            f"{E_USER} <b>{{name}}</b>{{flags}}\n"
            "<blockquote>"
            f"{E_ID} <b>ID:</b> <code>{{id}}</code>\n"
            f"{E_LINK} <b>Username:</b> {{username}}\n"
            "<b>Phone:</b> {phone} <b>·</b> <b>Language:</b> {lang}\n"
            "<b>Common chats:</b> {common} <b>·</b> <b>Status:</b> {status}"
            "</blockquote>{bio}"
        ),
        "chat_card": (
            f"{E_CHAT} <b>{{name}}</b>{{flags}}\n"
            "<blockquote>"
            f"{E_ID} <b>ID:</b> <code>{{id}}</code>\n"
            f"{E_LINK} <b>Username:</b> {{username}}\n"
            "<b>Members:</b> {members} <b>·</b> <b>Online:</b> {online}\n"
            "<b>Admins:</b> {admins} <b>·</b> <b>Banned:</b> {banned}"
            "</blockquote>{bio}"
        ),
        "bio": f"\n{E_NOTE} <blockquote expandable>{{}}</blockquote>",
        "none": "<i>none</i>",
        "unknown": "<i>unknown</i>",
    }

    strings_ru = {
        "not_found": f"{E_ERROR} <b>Не смог найти такого.</b>",
        "user_card": (
            f"{E_USER} <b>{{name}}</b>{{flags}}\n"
            "<blockquote>"
            f"{E_ID} <b>ID:</b> <code>{{id}}</code>\n"
            f"{E_LINK} <b>Юзернейм:</b> {{username}}\n"
            "<b>Телефон:</b> {phone} <b>·</b> <b>Язык:</b> {lang}\n"
            "<b>Общих чатов:</b> {common} <b>·</b> <b>Статус:</b> {status}"
            "</blockquote>{bio}"
        ),
        "chat_card": (
            f"{E_CHAT} <b>{{name}}</b>{{flags}}\n"
            "<blockquote>"
            f"{E_ID} <b>ID:</b> <code>{{id}}</code>\n"
            f"{E_LINK} <b>Юзернейм:</b> {{username}}\n"
            "<b>Участников:</b> {members} <b>·</b> <b>Онлайн:</b> {online}\n"
            "<b>Админов:</b> {admins} <b>·</b> <b>В бане:</b> {banned}"
            "</blockquote>{bio}"
        ),
        "none": "<i>нет</i>",
        "unknown": "<i>неизвестно</i>",
    }

    @staticmethod
    def _flags(entity, table) -> str:
        badges = [label for attr, label in table if getattr(entity, attr, False)]
        return f"  {E_FLAG} <i>{', '.join(badges)}</i>" if badges else ""

    def _username(self, entity) -> str:
        username = getattr(entity, "username", None)
        if not username:
            usernames = getattr(entity, "usernames", None) or []
            username = next((u.username for u in usernames if u.active), None)

        return f"@{username}" if username else self.strings["none"]

    def _bio(self, text: str | None) -> str:
        return self.strings["bio"].format(utils.escape_html(text)) if text else ""

    async def _resolve(self, message: Message):
        """Entity from the argument, the reply, or failing both the chat itself"""
        if args := utils.get_args_raw(message):
            return await self._client.get_entity(
                int(args) if args.lstrip("-").isdigit() else args
            )

        if reply := await message.get_reply_message():
            return await self._client.get_entity(reply.sender_id)

        return await message.get_chat()

    async def _user_card(self, user: User) -> str:
        try:
            full = (await self._client(GetFullUserRequest(user.id))).full_user
        except Exception:
            logger.debug("No full user for %s", user.id, exc_info=True)
            full = None

        return self.strings["user_card"].format(
            name=utils.escape_html(get_display_name(user) or str(user.id)),
            flags=self._flags(user, USER_FLAGS),
            id=user.id,
            username=self._username(user),
            phone=f"<code>+{user.phone}</code>" if user.phone else self.strings["none"],
            lang=utils.escape_html(user.lang_code or "") or self.strings["unknown"],
            common=getattr(full, "common_chats_count", None) or 0,
            status=utils.escape_html(type(user.status).__name__.replace("UserStatus", ""))
            or self.strings["unknown"],
            bio=self._bio(getattr(full, "about", None)),
        )

    async def _chat_card(self, chat: Channel | Chat) -> str:
        full = None
        if isinstance(chat, Channel):
            try:
                full = (await self._client(GetFullChannelRequest(chat))).full_chat
            except Exception:
                logger.debug("No full channel for %s", chat.id, exc_info=True)

        return self.strings["chat_card"].format(
            name=utils.escape_html(get_display_name(chat) or str(chat.id)),
            flags=self._flags(chat, CHAT_FLAGS),
            id=utils.get_entity_id(chat),
            username=self._username(chat),
            members=utils.humanize_number(
                getattr(full, "participants_count", None)
                or getattr(chat, "participants_count", None)
                or 0
            ),
            online=utils.humanize_number(getattr(full, "online_count", None) or 0),
            admins=getattr(full, "admins_count", None) or 0,
            banned=getattr(full, "kicked_count", None) or 0,
            bio=self._bio(getattr(full, "about", None)),
        )

    @loader.command(
        ru_doc="[@юзернейм|id] - Карточка юзера, чата или канала",
        en_doc="[@username|id] - Card for a user, chat or channel",
        alias="wi",
    )
    async def whois(self, message: Message):
        try:
            entity = await self._resolve(message)
        except Exception:
            logger.debug("Failed to resolve whois target", exc_info=True)
            await utils.answer(message, self.strings["not_found"])
            return

        await utils.answer(
            message,
            (
                await self._user_card(entity)
                if isinstance(entity, User)
                else await self._chat_card(entity)
            ),
        )
