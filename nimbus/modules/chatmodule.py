# meta developer: @codrago_m
#
# Original module author: codrago (@codrago_m, https://t.me/codrago_m)
# 🌐 Original source: https://github.com/coddrago/modules (chatmodule.py + libs/xdlib.py)
#
# Ported into Nimbus as a genuine local, self-contained built-in module:
# imports rewritten for nimbustl, and the original module's runtime dependency
# on a remotely-fetched library (xdlib.py, pulled live from coddrago/modules on
# every startup via `import_lib`) has been inlined below instead, so this
# module no longer phones home to any third-party server.
#
# ©️ ziahka, 2026
# This file is a part of Nimbus Userbot
# 🌐 https://github.com/ziahka/Nimbus
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

import logging
import re
import typing
from datetime import datetime, timedelta, timezone

from nimbustl.errors.rpcerrorlist import (
    HideRequesterMissingError,
    UserNotParticipantError,
)
from nimbustl.tl import types
from nimbustl.tl.functions import channels, messages

from .. import loader, utils

logger = logging.getLogger("ChatModule")


class _Rights:
    RIGHTS_LIST: list = []

    def __init__(self, mask: int = 0):
        self.mask = mask & self.MAX_MASK

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.RIGHTS = {name: 1 << i for i, name in enumerate(cls.RIGHTS_LIST)}
        cls.MAX_MASK = (1 << len(cls.RIGHTS_LIST)) - 1

    def add(self, *right_names: str):
        for name in right_names:
            if name not in self.RIGHTS:
                return None
            self.mask |= self.RIGHTS[name]
        return self

    def remove(self, *right_names: str):
        for name in right_names:
            if name not in self.RIGHTS:
                return None
            self.mask &= ~self.RIGHTS[name]
        return self

    def has(self, right_name: str) -> bool:
        return bool(self.mask & self.RIGHTS.get(right_name, 0))

    def has_index(self, idx: int) -> bool:
        if 0 <= idx < len(self.RIGHTS_LIST):
            return bool(self.mask & (1 << idx))
        return False

    def to_dict(self) -> dict:
        return {name: self.has(name) for name in self.RIGHTS_LIST}

    def to_int(self) -> int:
        return self.mask

    def to_chat_rights(self):
        return (
            types.ChatBannedRights(**self.to_dict())
            if isinstance(self, _BannedRights)
            else types.ChatAdminRights(**self.to_dict())
        )

    @classmethod
    def to_mask(cls, chat_rights) -> int:
        mask = 0
        for right, rmask in cls.RIGHTS.items():
            if (
                getattr(chat_rights, right)
                and isinstance(chat_rights, types.ChatAdminRights)
            ) or (
                not getattr(chat_rights, right)
                and isinstance(chat_rights, types.ChatBannedRights)
            ):
                mask |= rmask
        return mask

    @classmethod
    def all(cls):
        return cls(cls.MAX_MASK)


class _BannedRights(_Rights):
    RIGHTS_LIST = [
        x for x in types.ChatBannedRights(until_date=None).to_dict().keys() if x != "_"
    ]


class _AdminRights(_Rights):
    RIGHTS_LIST = [x for x in types.ChatAdminRights().to_dict().keys() if x != "_"]


class _ParseUtils:
    def minutes_to_hhmm(self, m: int) -> str:
        h = (m // 60) % 24
        mm = m % 60
        return f"{h:02d}:{mm:02d}"

    def opts(self, args: list) -> typing.Dict[str, typing.Any]:
        """Parses command-line style options from a list of arguments."""
        options = {}
        i = 0

        def auto_cast(value: str):
            if not value:
                return True
            low = value.lower()
            if low in {"true", "yes", "on"}:
                return True
            if low in {"false", "no", "off"}:
                return False
            if re.fullmatch(r"-?\d+", value):
                return int(value)
            if re.fullmatch(r"-?\d+\.\d+", value):
                return float(value)
            return value

        def apply_operations(base, ops: list):
            val = base
            for op_str in ops:
                m = re.fullmatch(r"([+*/])(\d+(\.\d+)?)", op_str)
                if not m:
                    val = auto_cast(op_str)
                    continue
                op, number, _ = m.groups()
                number = float(number) if "." in number else int(number)
                if op == "+":
                    val += number
                elif op == "*":
                    val *= number
                elif op == "/":
                    val /= number
            return val

        while i < len(args):
            arg = args[i]

            if "=" in arg:
                key, value = arg.split("=", 1)
                key = key.lstrip("-")
                options[key] = auto_cast(value.strip("\"'"))
            elif arg.startswith("-"):
                key = arg.lstrip("-")
                values = []
                i += 1
                while i < len(args) and not args[i].startswith("-"):
                    values.append(args[i].strip("\"'"))
                    i += 1
                i -= 1

                if key in options and isinstance(options[key], (int, float)):
                    options[key] = apply_operations(options[key], values)
                elif values:
                    base = auto_cast(values[0])
                    options[key] = apply_operations(base, values[1:])
                else:
                    options[key] = True

            i += 1

        return options

    def time(self, time_str: str) -> int:
        time_units = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800, "y": 31536000}
        total_seconds = 0
        for value, unit in re.findall(r"(\d+)([smhdwy])", time_str):
            total_seconds += int(value) * time_units[unit]
        return total_seconds


class _FormatUtils:
    def time(self, seconds: int) -> str:
        intervals = (
            ("years", 31536000),
            ("months", 2592000),
            ("weeks", 604800),
            ("days", 86400),
            ("hours", 3600),
            ("minutes", 60),
            ("seconds", 1),
        )
        result = []
        for name, count in intervals:
            value = seconds // count
            if value:
                seconds -= value * count
                if value == 1:
                    name = name.rstrip("s")
                result.append(f"{value} {name}")
        return ", ".join(result) if result else "0 seconds"


class _MessageUtils:
    def __init__(self, client):
        self._client = client

    async def delete_messages(self, msg):
        """Deletes multiple messages based on a specific pattern."""
        reply = await msg.get_reply_message()
        pattern = r"([ab])(\d+)"
        matches = re.findall(pattern, utils.get_args_raw(msg))

        ids_to_delete = [msg.id]
        if reply:
            ids_to_delete.append(reply.id)

        for direction, count_str in matches:
            count = int(count_str)
            if direction == "a" and reply:
                async for m in self._client.iter_messages(
                    msg.chat_id, min_id=reply.id, limit=count, reverse=True
                ):
                    ids_to_delete.append(m.id)
            elif direction == "b":
                async for m in self._client.iter_messages(
                    msg.chat_id, max_id=(reply if reply else msg).id, limit=count
                ):
                    ids_to_delete.append(m.id)

        await self._client.delete_messages(msg.chat_id, message_ids=ids_to_delete)


class _DialogUtils:
    def __init__(self, client) -> None:
        self._client = client

    async def get_all(self, client):
        return [dialog async for dialog in client.iter_dialogs()]

    async def get_owns(self, client):
        return [
            ent
            for ent in await self.get_all(client)
            if hasattr(ent.entity, "creator") and ent.entity.creator
        ]


class _UserUtils:
    def __init__(self, client, db):
        self._client = client
        self._db = db

    async def get_info(self, user_id) -> dict:
        userfull = await self._client.get_fulluser(user_id)
        full_user = userfull.full_user
        user = userfull.users[0]
        usernames = user.usernames or [user] or None
        unames = [username.username for username in usernames] if usernames else []
        personal_channel = (
            await self._client.get_entity(full_user.personal_channel_id)
            if full_user.personal_channel_id
            else None
        )
        common = await self._client(
            messages.GetCommonChatsRequest(user_id=user_id, max_id=0, limit=100)
        )

        return {
            "common_chats_count": full_user.common_chats_count,
            "common_chats": common.chats,
            "id": user.id,
            "profile_photo": full_user.personal_photo or user.photo,
            "business_work_hours": full_user.business_work_hours,
            "birthday": full_user.birthday,
            "personal_channel": personal_channel or None,
            "stargifts_count": full_user.stargifts_count,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "usernames": unames,
            "emoji_status": getattr(user.emoji_status, "document_id", None),
            "about": full_user.about,
            "phone": user.phone,
        }


class _AdminUtils:
    def __init__(self, client) -> None:
        self._client = client

    async def set_rights(self, chat, user, mask: int, rank: str = "Admin") -> bool:
        try:
            rights = _AdminRights(mask)
            await self._client(
                channels.EditAdminRequest(
                    chat,
                    user,
                    rights.to_chat_rights(),
                    rank=rank,
                )
            )
            return True
        except Exception:
            logger.error(
                "Failed to set rights with mask %s for user %s in chat %s",
                mask,
                getattr(user, "id", user),
                chat,
                exc_info=True,
            )
            return False


class _ChatUtils:
    def __init__(self, client, db) -> None:
        self._client = client
        self._db = db

    async def set_restrictions(self, chat, user, mask: int, duration: int = None) -> bool:
        try:
            rights = _BannedRights(mask)
            rights_dict = rights.to_dict()
            rights_dict["until_date"] = (
                None if duration is None else int(datetime.now().timestamp()) + duration
            )
            new_banned_rights = types.ChatBannedRights(**rights_dict)

            await self._client(
                channels.EditBannedRequest(
                    channel=chat,
                    participant=user,
                    banned_rights=new_banned_rights,
                )
            )
            return True
        except Exception:
            logger.error(
                "Failed to set restrictions with mask %s for user %s in chat %s",
                mask,
                getattr(user, "id", user),
                chat,
                exc_info=True,
            )
            return False

    async def join_request(self, chat, user_id, approved):
        try:
            await self._client(
                messages.HideChatJoinRequestRequest(
                    peer=chat, user_id=user_id, approved=approved
                )
            )
        except HideRequesterMissingError:
            logger.error("Request not found")

    async def get_members(self, chat):
        try:
            return await self._client.get_participants(chat) or None
        except Exception:
            logger.error("Couldn't get members of the chat %s", chat)
            return None

    async def get_deleted(self, chat):
        try:
            members = await self._client.get_participants(chat)
            deleted = [member for member in members if getattr(member, "deleted", False)]
            return deleted or None
        except Exception:
            logger.error("Couldn't get members of the chat %s", chat)
            return None

    async def get_bots(self, chat):
        try:
            return (
                await self._client.get_participants(
                    chat, filter=types.ChannelParticipantsBots()
                )
                or None
            )
        except Exception:
            logger.error("Couldn't get bots from the chat %s", chat)
            return None

    async def get_admins(self, chat, only_users: bool = False):
        try:
            admins = await self._client.get_participants(
                chat, filter=types.ChannelParticipantsAdmins()
            )
            users = [
                user
                for user in admins
                if user
                and not getattr(user, "bot", False)
                and not isinstance(
                    getattr(user, "participant", None), types.ChannelParticipantCreator
                )
            ]
            return users if only_users else admins
        except Exception:
            logger.error("Couldn't get admins from the chat %s", chat)
            return None

    async def get_creator(self, chat):
        try:
            admins = await self._client.get_participants(
                chat, filter=types.ChannelParticipantsAdmins()
            )
            if not admins:
                return None
            for admin in admins:
                if hasattr(admin, "participant") and isinstance(
                    admin.participant, types.ChannelParticipantCreator
                ):
                    return admin
            return None
        except Exception:
            logger.error("Couldn't get the creator from the chat %s", chat)
            return None

    async def get_rights(self, chat, user):
        try:
            return await self._client.get_perms_cached(chat, user)
        except UserNotParticipantError:
            return None
        except Exception:
            logger.error(
                "Failed to check membership for user %s in chat %s",
                user,
                getattr(chat, "title", chat),
                exc_info=True,
            )
            return None

    async def invite_user(self, chat, user) -> bool:
        try:
            await self._client(channels.InviteToChannelRequest(channel=chat, users=[user]))
            return True
        except Exception:
            logger.error(
                "Failed to invite user %s to chat %s",
                user,
                getattr(chat, "title", chat),
                exc_info=True,
            )
            return False

    async def get_info(self, chat) -> dict:
        try:
            chat_full = await self._client.get_fullchannel(chat)
            full_chat = chat_full.full_chat
            chat = chat_full.chats[0]
            return {
                "id": full_chat.id or 0,
                "about": full_chat.about or "",
                "chat_photo": full_chat.chat_photo,
                "admins_count": full_chat.admins_count or 0,
                "online_count": full_chat.online_count or 0,
                "participants_count": full_chat.participants_count or 0,
                "kicked_count": full_chat.kicked_count,
                "slowmode_seconds": full_chat.slowmode_seconds or 0,
                "call": full_chat.call or None,
                "title": chat.title or "",
                "ttl_period": full_chat.ttl_period or 0,
                "requests_pending": full_chat.requests_pending or 0,
                "recent_requesters": full_chat.recent_requesters or [],
                "is_forum": getattr(chat, "forum", False),
                "linked_chat_id": full_chat.linked_chat_id or 0,
                "antispam": full_chat.antispam or False,
                "participants_hidden": full_chat.participants_hidden or False,
                "link": (
                    f"https://t.me/{chat.username}"
                    if chat.username
                    else (
                        full_chat.exported_invite.link
                        if full_chat.exported_invite
                        else ""
                    )
                ),
                "is_channel": chat.broadcast or False,
                "is_group": chat.megagroup or False,
            }
        except Exception:
            logger.error("Failed to get the chat info", exc_info=True)
            return {}

    async def invite_bot(self, client, chat) -> bool:
        try:
            await self._client(
                channels.InviteToChannelRequest(
                    chat,
                    [client.inline.bot_username or client.inline.bot_id],
                )
            )
        except Exception:
            logger.error("Failed to invite inline bot to chat", exc_info=True)
            return False

        rights = _AdminRights.all()
        rights.remove("anonymous")
        admin = _AdminUtils(self._client)
        await admin.set_rights(
            chat,
            client.inline.bot_username or client.inline.bot_id,
            rights.to_int(),
            rank="Bot",
        )
        return True


@loader.tds
class ChatModuleMod(loader.Module):
    """A collection of chat/group moderation commands"""

    strings = {
        "name": "ChatModule",
        "my_id": "<tg-emoji emoji-id=5361912768045792571>👑</tg-emoji><b> My ID: </b><code>{id}</code>",
        "chat_id": "<tg-emoji emoji-id=5886436057091673541>💬</tg-emoji> <b>Chat ID:</b> <code>{id}</code>",
        "user_id": "<tg-emoji emoji-id=6035084557378654059>👤</tg-emoji> <b>User's ID:</b> <code>{id}</code>",
        "user_not_participant": "<tg-emoji emoji-id=5019523782004441717>❌</tg-emoji> <b>User is not in this group.</b>",
        "admin_rights": "<blockquote expandable><tg-emoji emoji-id=6023985764885338464>📜</tg-emoji> {name} <b>Rights in this chat:\n\n{rights}</b>\n\n<tg-emoji emoji-id=5287734473775918473>🔼</tg-emoji><b> Promoted by: {promoter_name}</b> [{promoter_id}]</blockquote>",
        "not_an_admin": "<tg-emoji emoji-id=5019523782004441717>❌</tg-emoji><b> {user} is not an admin.</b>",
        "no_rights": "<tg-emoji emoji-id=5019523782004441717>❌</tg-emoji> <b>I don't have enough rights :(</b>",
        "no_user": "<tg-emoji emoji-id=5019523782004441717>❌</tg-emoji> <b>User not found.</b>",
        "change_info": "Change Info",
        "delete_messages": "Delete messages",
        "other": "Other",
        "ban_users": "Ban users",
        "invite_users": "Invite Users",
        "pin_messages": "Pin Messages",
        "add_admins": "Add Admins",
        "manage_call": "Manage Call",
        "post_stories": "Post Stories",
        "edit_stories": "Edit Stories",
        "delete_stories": "Delete Stories",
        "anonymous": "Anonymous",
        "manage_topics": "Manage Topics",
        "post_messages": "Post messages",
        "edit_messages": "Edit messages",
        "until_date": "Until: {until_date}",
        "view_messages": "View messages",
        "send_messages": "Send messages",
        "send_media": "Send media",
        "send_stickers": "Send stickers",
        "send_gifs": "Send GIFs",
        "send_games": "Send games",
        "send_inline": "Use inline bots",
        "embed_links": "Embed links",
        "send_polls": "Send polls",
        "send_photos": "Send photos",
        "send_videos": "Send videos",
        "send_roundvideos": "Send round videos",
        "send_audios": "Send audio",
        "send_voices": "Send voice messages",
        "send_docs": "Send documents",
        "send_plain": "Send plain text",
        "invalid_args": "<tg-emoji emoji-id=5219776129669276751>❌</tg-emoji> <b>Invalid args.</b>",
        "error": "<tg-emoji emoji-id=5458497936763676259>😖</tg-emoji><b> Something went wrong. Check the logs.</b>",
        "successful_delete": "<tg-emoji emoji-id=5409029658794537988>✅</tg-emoji> <b>Entity successfully deleted</b>",
        "no_deleted_accounts": "<tg-emoji emoji-id=5238020759900668600>😶‍🌫️</tg-emoji> <b>No deleted accounts found here</b>",
        "kicked_deleted_accounts": "<tg-emoji emoji-id=5408832111773757273>🗑</tg-emoji> <b>Removed deleted accounts from the chat</b>",
        "no_admins_in_chat": "<tg-emoji emoji-id=5458610095539645297>✖️</tg-emoji> <b>No admins in this chat.</b>",
        "bot_list": "<blockquote expandable><tg-emoji emoji-id=5355051922862653659>🤖</tg-emoji><b> Bots ({count}):</b>\n{bots}</blockquote>",
        "no_bots_in_chat": "<tg-emoji emoji-id=5458610095539645297>✖️</tg-emoji> <b>No bots in this chat.</b>",
        "user_list": "<blockquote expandable><tg-emoji emoji-id=5408846628763217930>👤</tg-emoji><b> Users ({count}):</b>\n{users}</blockquote>",
        "no_user_in_chat": "<tg-emoji emoji-id=5458610095539645297>✖️</tg-emoji> <b>No users in this chat.</b>",
        "user_is_banned": "<tg-emoji emoji-id=5348402067947929537>🚫</tg-emoji> <b>{name} [<code>{id}</code>] has been banned for{time_info}.</b>",
        "user_is_unbanned": "<tg-emoji emoji-id=5355277430120523169>👋</tg-emoji> <b>{name} [<code>{id}</code>] has been unbanned.</b>",
        "user_is_kicked": "<tg-emoji emoji-id=5983033346207256798>🚪</tg-emoji> <b><code>{name}</code> [<code>{id}</code>] has been kicked.</b>",
        "user_is_muted": "<tg-emoji emoji-id=5409380965644514142>🔕</tg-emoji> <b>{name} [<code>{id}</code>] has been muted for{time_info}.</b>",
        "reason": "<i>Reason: {reason}</i>",
        "forever": "ever",
        "user_is_unmuted": "<tg-emoji emoji-id=5409331062419502443>🔉</tg-emoji> <b>{name} [<code>{id}</code>] has been unmuted.</b>",
        "channel_created": "<tg-emoji emoji-id=6296367896398399651>✅</tg-emoji> <b>The channel <code>{title}</code> is created.\n</b><tg-emoji emoji-id=5237918475254526196>🔗</tg-emoji><b> Invite link: {link}</b>",
        "group_created": "<tg-emoji emoji-id=6296367896398399651>✅</tg-emoji> <b>The group <code>{title}</code> is created.\n</b><tg-emoji emoji-id=5237918475254526196>🔗</tg-emoji><b> Invite link: {link}</b>",
        "user_invited": "<tg-emoji emoji-id=5409029658794537988>✅</tg-emoji> <b>User <a href='tg://user?id={id}'>{user}</a> is invited to the chat.</b>",
        "user_not_invited": "<tg-emoji emoji-id=5019523782004441717>❌</tg-emoji> <b>User could not be invited to the chat.</b>",
        "admin_list": "<blockquote expandable><tg-emoji emoji-id=5361912768045792571>👑</tg-emoji> <b>The creator is <a href='tg://user?id={id}'>{name}</a>\n\nAdmins ({admins_count}):</b>\n{admins}</blockquote>",
        "dnd": "<tg-emoji emoji-id=5384262794306669858>🔕</tg-emoji> <b>Chat muted and archived</b>",
        "dnd_failed": "<tg-emoji emoji-id=5312383351217201533>⚠️</tg-emoji> <b>Failed to mute and archive chat</b>",
        "pinned": "<tg-emoji emoji-id=6296367896398399651>✅</tg-emoji> <b>Pinned the message</b>",
        "pin_failed": "<tg-emoji emoji-id=5458610095539645297>✖️</tg-emoji><b> Failed to pin the message</b>",
        "unpinned": "<tg-emoji emoji-id=6296367896398399651>✅</tg-emoji> <b>Unpinned the message</b>",
        "unpin_failed": "<tg-emoji emoji-id=5458610095539645297>✖️</tg-emoji><b> Failed to unpin the message</b>",
        "type_group": "Group",
        "type_channel": "Channel",
        "type_unknown": "Unknown",
        "yes": "<tg-emoji emoji-id=5408909562919007848>✅</tg-emoji> Yes",
        "no": "<tg-emoji emoji-id=5361566877149578396>✖️</tg-emoji> No",
        "chatinfo": "<blockquote><tg-emoji emoji-id=5983036958274752500>🔒</tg-emoji><b> Type: {type_of}\n</b><tg-emoji emoji-id=5985457743576698865>#️⃣</tg-emoji><b> Chat ID: </b><code>{id}</code><b>\n</b><tg-emoji emoji-id=5408849420491962048>🔥</tg-emoji><b> Title: {title}\n<tg-emoji emoji-id=5258328383183396223>📖</tg-emoji><b> Forum:</b> {is_forum}</blockquote>\n</b><blockquote><tg-emoji emoji-id=5870676941614354370>🖋</tg-emoji><b> About: {about}</blockquote>\n</b><blockquote><tg-emoji emoji-id=5805553606635559688>👑</tg-emoji><b> Admin count: {admins_count}\n</b><tg-emoji emoji-id=5433648711982921307>✅</tg-emoji><b> Online count: {online_count}\n</b><tg-emoji emoji-id=6024039683904772353>👤</tg-emoji><b> Participants count: {participants_count}\n</b><tg-emoji emoji-id=5816617137447376501>🚫</tg-emoji><b> Kicked сount: {kicked_count}\n</b><tg-emoji emoji-id=5431560533243346887>🔀</tg-emoji><b> Requests pending: {requests_pending}</blockquote>\n</b><blockquote><tg-emoji emoji-id=5408910404732595664>🕐</tg-emoji><b> Slowmode period: {slowmode_seconds}\n</b><tg-emoji emoji-id=6019279794988915337>📞</tg-emoji><b> Call: {call}\n</b><tg-emoji emoji-id=5408832111773757273>🗑</tg-emoji><b> TTL period: {ttl_period}\n</b><tg-emoji emoji-id=5408846628763217930>👤</tg-emoji><b> Recent requesters: {recent_requesters}</blockquote>\n</b><blockquote><tg-emoji emoji-id=6021690418398239007>👥</tg-emoji><b> Linked Chat ID: {linked_chat_id}\n</b><tg-emoji emoji-id=6019328362479097179>🛡</tg-emoji><b> Antispam: {antispam}\n</b><tg-emoji emoji-id=6024008227564296298>👁</tg-emoji><b> Participants hidden: {participants_hidden}</blockquote>\n</b><tg-emoji emoji-id=6028171274939797252>🔗</tg-emoji><b> Link: {link}</b>",
        "requests_checked": "<tg-emoji emoji-id=5409029658794537988>✅</tg-emoji> <b>Checked requests from {entities}</b>",
        "promoted": "<tg-emoji emoji-id=5458614983212427372>👑</tg-emoji> <b><a href='tg://user?id={id}'>{name}</a> is promoted!\n<tg-emoji emoji-id=5409029658794537988>✅</tg-emoji> Rights: {rights}</b>",
        "full_rights": "Full rights",
        "promote": "<b>Select rights for <a href='tg://user?id={id}'>{name}</a>!\nRank: {rank}</b>",
        "restrict": "<b>Restricting <a href='tg://user?id={id}'>{name}</a> for{time}\n\n<i>Select which actions to restrict. Options marked in green will be applied.</i></b>",
        "restricted": "<tg-emoji emoji-id=5208491751639106607>🚫</tg-emoji> <b><a href='tg://user?id={id}'>{name}</a> has been restricted for{time}</b>",
        "demoted": "<tg-emoji emoji-id=5447183459602669338>🔽</tg-emoji> <b><a href='tg://user?id={id}'>{name}</a> is demoted</b>",
        "userinfo": "<blockquote><tg-emoji emoji-id=5985457743576698865>#️⃣</tg-emoji><b> ID: {user_id}\n</b><tg-emoji emoji-id=5408849420491962048>🔥</tg-emoji><b> First name: {first_name}\n</b><tg-emoji emoji-id=5408849420491962048>🔥</tg-emoji><b> Last name: {last_name}\n</b><tg-emoji emoji-id=5208889774848361126>📞</tg-emoji><b> Phone number: {phone}\n</b><tg-emoji emoji-id=5364052602357044385>🐶</tg-emoji><b>  Usernames: {usernames}</b></blockquote><b>\n</b><blockquote><tg-emoji emoji-id=5985616786215669454>ℹ️</tg-emoji><b> About: {about}</b></blockquote><b>\n</b><blockquote><tg-emoji emoji-id=5408910404732595664>🕐</tg-emoji><b> Work hours: </b>{business_work_hours}\n<tg-emoji emoji-id=5408892365869952851>❤️</tg-emoji><b> Emoji status: {emoji_status}</b></blockquote><b>\n</b><blockquote><tg-emoji emoji-id=5409331062419502443>🔉</tg-emoji><b> Personal channel: {personal_channel}\n</b><tg-emoji emoji-id=6024041612345088787>🎂</tg-emoji><b> Birthday: {birthday}\n</b><tg-emoji emoji-id=6037175527846975726>🎁</tg-emoji><b> Gifts count: {stargifts_count}</b></blockquote><b>\n</b><blockquote><tg-emoji emoji-id=5208842667647061916>🚨</tg-emoji><b> Common chats count: {common_chats_count}\n</b><tg-emoji emoji-id=5985401861757210746>👥</tg-emoji><b> Common chats: {common_chats}</b></blockquote>",
        "monday": "Monday",
        "tuesday": "Tuesday",
        "wednesday": "Wednesday",
        "thursday": "Thursday",
        "friday": "Friday",
        "saturday": "Saturday",
        "sunday": "Sunday",
        "owns": "<tg-emoji emoji-id=5458614983212427372>👑</tg-emoji><b> My kingdoms [{num}]:</b>\n<blockquote expandable>{owns}</blockquote>",
        "close": "❌ Close",
        "apply": "✅ Apply",
    }

    strings_ru = {
        "my_id": "<tg-emoji emoji-id=5361912768045792571>👑</tg-emoji><b> Мой ID: </b><code>{id}</code>",
        "chat_id": "<tg-emoji emoji-id=5886436057091673541>💬</tg-emoji> <b>ID чата:</b> <code>{id}</code>",
        "user_id": "<tg-emoji emoji-id=6035084557378654059>👤</tg-emoji> <b>ID пользователя:</b> <code>{id}</code>",
        "not_an_admin": "<tg-emoji emoji-id=5019523782004441717>❌</tg-emoji><b> {user} не является админом.</b>",
        "no_rights": "<tg-emoji emoji-id=5019523782004441717>❌</tg-emoji> <b>У меня недостаточно прав :(</b>",
        "no_user": "<tg-emoji emoji-id=5019523782004441717>❌</tg-emoji> <b>Пользователь не найден.</b>",
        "invalid_args": "<tg-emoji emoji-id=5219776129669276751>❌</tg-emoji> <b>Неверные аргументы.</b>",
        "error": "<tg-emoji emoji-id=5458497936763676259>😖</tg-emoji><b> Что-то пошло не так. Проверьте логи.</b>",
        "successful_delete": "<tg-emoji emoji-id=5409029658794537988>✅</tg-emoji> <b>Сущность успешно удалена</b>",
        "no_deleted_accounts": "<tg-emoji emoji-id=5238020759900668600>😶‍🌫️</tg-emoji> <b>Удалённых аккаунтов здесь нет</b>",
        "kicked_deleted_accounts": "<tg-emoji emoji-id=5408832111773757273>🗑</tg-emoji> <b>Удалённые аккаунты очищены из чата</b>",
        "no_admins_in_chat": "<tg-emoji emoji-id=5458610095539645297>✖️</tg-emoji> <b>В этом чате нет админов.</b>",
        "bot_list": "<blockquote expandable><tg-emoji emoji-id=5355051922862653659>🤖</tg-emoji><b> Боты ({count}):</b>\n{bots}</blockquote>",
        "no_bots_in_chat": "<tg-emoji emoji-id=5458610095539645297>✖️</tg-emoji> <b>В этом чате нет ботов.</b>",
        "user_list": "<blockquote expandable><tg-emoji emoji-id=5408846628763217930>👤</tg-emoji><b> Пользователи ({count}):</b>\n{users}</blockquote>",
        "no_user_in_chat": "<tg-emoji emoji-id=5458610095539645297>✖️</tg-emoji> <b>В этом чате нет пользователей.</b>",
        "user_is_banned": "<tg-emoji emoji-id=5348402067947929537>🚫</tg-emoji> <b>{name} [<code>{id}</code>] забанен на{time_info}.</b>",
        "user_is_unbanned": "<tg-emoji emoji-id=5355277430120523169>👋</tg-emoji> <b>{name} [<code>{id}</code>] разбанен.</b>",
        "user_is_kicked": "<tg-emoji emoji-id=5983033346207256798>🚪</tg-emoji> <b><code>{name}</code> [<code>{id}</code>] кикнут.</b>",
        "user_is_muted": "<tg-emoji emoji-id=5409380965644514142>🔕</tg-emoji> <b>{name} [<code>{id}</code>] замьючен на{time_info}.</b>",
        "reason": "<i>Причина: {reason}</i>",
        "forever": "всегда",
        "user_is_unmuted": "<tg-emoji emoji-id=5409331062419502443>🔉</tg-emoji> <b>{name} [<code>{id}</code>] размьючен.</b>",
        "channel_created": "<tg-emoji emoji-id=6296367896398399651>✅</tg-emoji> <b>Канал <code>{title}</code> создан.\n</b><tg-emoji emoji-id=5237918475254526196>🔗</tg-emoji><b> Пригласительная ссылка: {link}</b>",
        "group_created": "<tg-emoji emoji-id=6296367896398399651>✅</tg-emoji> <b>Группа <code>{title}</code> создана.\n</b><tg-emoji emoji-id=5237918475254526196>🔗</tg-emoji><b> Пригласительная ссылка: {link}</b>",
        "user_invited": "<tg-emoji emoji-id=5409029658794537988>✅</tg-emoji> <b>Пользователь <a href='tg://user?id={id}'>{user}</a> приглашён в чат.</b>",
        "user_not_invited": "<tg-emoji emoji-id=5019523782004441717>❌</tg-emoji> <b>Не удалось пригласить пользователя.</b>",
        "admin_list": "<blockquote expandable><tg-emoji emoji-id=5361912768045792571>👑</tg-emoji> <b>Создатель: <a href='tg://user?id={id}'>{name}</a>\n\nАдмины ({admins_count}):</b>\n{admins}</blockquote>",
        "dnd": "<tg-emoji emoji-id=5384262794306669858>🔕</tg-emoji> <b>Чат заглушён и архивирован</b>",
        "dnd_failed": "<tg-emoji emoji-id=5312383351217201533>⚠️</tg-emoji> <b>Не удалось заглушить и архивировать чат</b>",
        "pinned": "<tg-emoji emoji-id=6296367896398399651>✅</tg-emoji> <b>Сообщение закреплено</b>",
        "pin_failed": "<tg-emoji emoji-id=5458610095539645297>✖️</tg-emoji><b> Не удалось закрепить сообщение</b>",
        "unpinned": "<tg-emoji emoji-id=6296367896398399651>✅</tg-emoji> <b>Сообщение откреплено</b>",
        "unpin_failed": "<tg-emoji emoji-id=5458610095539645297>✖️</tg-emoji><b> Не удалось открепить сообщение</b>",
        "type_group": "Группа",
        "type_channel": "Канал",
        "type_unknown": "Неизвестно",
        "yes": "<tg-emoji emoji-id=5408909562919007848>✅</tg-emoji> Да",
        "no": "<tg-emoji emoji-id=5361566877149578396>✖️</tg-emoji> Нет",
        "requests_checked": "<tg-emoji emoji-id=5409029658794537988>✅</tg-emoji> <b>Рассмотрены заявки от {entities}</b>",
        "promoted": "<tg-emoji emoji-id=5458614983212427372>👑</tg-emoji> <b><a href='tg://user?id={id}'>{name}</a> назначен администратором!\n<tg-emoji emoji-id=5409029658794537988>✅</tg-emoji> Права: {rights}</b>",
        "full_rights": "Полные права",
        "promote": "<b>Выберите права для <a href='tg://user?id={id}'>{name}</a>!\nРанг: {rank}</b>",
        "restrict": "<b>Ограничение <a href='tg://user?id={id}'>{name}</a> на{time}\n\n<i>Выберите, что нужно запретить. Опции, отмеченные зелёным, будут применены.</i></b>",
        "restricted": "<tg-emoji emoji-id=5208491751639106607>🚫</tg-emoji> <b><a href='tg://user?id={id}'>{name}</a> был(а) ограничен(а) на{time}</b>",
        "demoted": "<tg-emoji emoji-id=5447183459602669338>🔽</tg-emoji> <b><a href='tg://user?id={id}'>{name}</a> понижен</b>",
        "monday": "Понедельник",
        "tuesday": "Вторник",
        "wednesday": "Среда",
        "thursday": "Четверг",
        "friday": "Пятница",
        "saturday": "Суббота",
        "sunday": "Воскресенье",
        "owns": "<tg-emoji emoji-id=5458614983212427372>👑</tg-emoji><b> Мои королевства [{num}]:</b>\n<blockquote expandable>{owns}</blockquote>",
        "close": "❌ Закрыть",
        "apply": "✅ Применить",
    }

    async def client_ready(self):
        self._parse = _ParseUtils()
        self._format = _FormatUtils()
        self._messages = _MessageUtils(self._client)
        self._admin = _AdminUtils(self._client)
        self._chat = _ChatUtils(self._client, self.db)
        self._dialog = _DialogUtils(self._client)
        self._user = _UserUtils(self._client, self.db)

    @loader.command(ru_doc="[reply] - Узнать ID")
    async def id(self, message):
        """[reply] - Get the ID"""
        ids = [self.strings["my_id"].format(id=self.tg_id)]
        if message.is_private:
            ids.append(self.strings["user_id"].format(id=message.to_id.user_id))
            return await utils.answer(message, "\n".join(ids))
        ids.append(self.strings["chat_id"].format(id=message.chat_id))
        reply = await message.get_reply_message()
        if reply and not reply.is_private and reply.sender_id != self.tg_id:
            user_id = (await reply.get_sender()).id
            ids.append(self.strings["user_id"].format(id=user_id))
        return await utils.answer(message, "\n".join(ids))

    @loader.command(
        ru_doc="[reply/-u username/id] - Посмотреть права администратора пользователя",
    )
    @loader.tag("no_pm")
    async def rights(self, message):
        """[reply/-u username/id] - Check user's admin rights"""
        opts = self._parse.opts(utils.get_args(message))
        reply = await message.get_reply_message()
        user = opts.get("u") or opts.get("user") or (reply.sender_id if reply else None)
        if not user:
            return await utils.answer(message, self.strings["no_user"])
        perms = await self._chat.get_rights(message.chat, user)
        user = await self._client.get_entity(user)
        if not perms or not hasattr(perms, "participant"):
            return await utils.answer(
                message, self.strings["not_an_admin"].format(user=user.first_name)
            )
        participant = perms.participant
        if not hasattr(participant, "admin_rights") or not participant.admin_rights:
            return await utils.answer(
                message, self.strings["not_an_admin"].format(user=user.first_name)
            )
        can_do = [
            right
            for right, is_permitted in participant.admin_rights.to_dict().items()
            if right != "_" and is_permitted
        ]
        promoter = (
            await self._client.get_entity(participant.promoted_by)
            if hasattr(participant, "promoted_by")
            else None
        )
        return await utils.answer(
            message,
            self.strings["admin_rights"].format(
                rights="\n".join(
                    f"<tg-emoji emoji-id=5409029658794537988>✅</tg-emoji> {self.strings[right]}"
                    for right in can_do
                ),
                promoter_id=promoter.id if promoter else 0,
                promoter_name=promoter.first_name if promoter else self.strings["no"],
                name=user.first_name,
            ),
        )

    @loader.command(ru_doc="Покинуть чат")
    @loader.tag("no_pm")
    async def leave(self, message):
        """Leave chat"""
        await message.delete()
        await self._client(channels.LeaveChannelRequest((await message.get_chat()).id))

    @loader.command(ru_doc="[a[1-100] b[1-100]] | [reply] Удалить сообщения")
    async def d(self, message):
        """[a[1-100] b[1-100]] | [reply] - Delete messages"""
        await self._messages.delete_messages(message)

    @loader.command(ru_doc="[reply] - Закрепить сообщение")
    @loader.tag("only_reply")
    async def pin(self, message):
        """[reply] - Pin a message"""
        reply = await message.get_reply_message()
        try:
            await reply.pin(notify=True, pm_oneside=False)
        except Exception as e:
            logger.error(str(e))
            return await utils.answer(message, self.strings["pin_failed"])
        await utils.answer(message, self.strings["pinned"])

    @loader.command(ru_doc="Открепить сообщение")
    @loader.tag("only_reply")
    async def unpin(self, message):
        """Unpin a message"""
        reply = await message.get_reply_message()
        try:
            await reply.unpin()
        except Exception as e:
            logger.error(str(e))
            return await utils.answer(message, self.strings["unpin_failed"])
        await utils.answer(message, self.strings["unpinned"])

    @loader.command(ru_doc="[-c id] Удаляет группу/канал")
    async def dgc(self, message):
        """[-c id] Delete chat/channel"""
        args = utils.get_args(message)
        opts = self._parse.opts(args)
        chat_id = opts.get("c") or opts.get("chat")
        if chat_id:
            chat = await self._client.get_entity(chat_id)
        else:
            chat = message.chat
        if isinstance(chat, types.Channel):
            await self._client(channels.DeleteChannelRequest(chat.id))
        elif isinstance(chat, types.Chat):
            await self._client(messages.DeleteChatRequest(chat.id))
        else:
            return await utils.answer(message, self.strings["error"])
        return await utils.answer(message, self.strings["successful_delete"])

    @loader.command(ru_doc="Очищает группу/канал от удаленных аккаунтов")
    @loader.tag("no_pm")
    async def flush(self, message):
        """Removes deleted accounts from the chat/channel"""
        chat = await message.get_chat()

        if not getattr(chat, "admin_rights", None) or not getattr(
            chat.admin_rights, "ban_users", False
        ):
            return await utils.answer(message, self.strings["no_rights"])

        deleted = await self._chat.get_deleted(chat)
        if not deleted:
            return await utils.answer(message, self.strings["no_deleted_accounts"])
        for to_delete in deleted:
            try:
                await self._client.kick_participant(chat, to_delete)
            except Exception as e:
                logger.error(str(e))
                return await utils.answer(message, self.strings["error"])
        return await utils.answer(message, self.strings["kicked_deleted_accounts"])

    @loader.command(ru_doc="Показывает админов в группе/канале")
    @loader.tag("no_pm")
    async def admins(self, message):
        """Shows the admins in the chat/channel"""
        admins = await self._chat.get_admins(message.chat, True)
        creator = await self._chat.get_creator(message.chat)
        return await utils.answer(
            message,
            self.strings["admin_list"].format(
                id=creator.id if creator else 0,
                name=creator.first_name if creator else self.strings["no"],
                admins_count=len(admins) or 0,
                admins=(
                    "\n".join(
                        f"<tg-emoji emoji-id=5774022692642492953>✅</tg-emoji> <a href='tg://user?id={admin.id}'>{admin.first_name}</a> [<code>{admin.id}</code>]"
                        for admin in admins
                    )
                    if admins
                    else f"\n{self.strings['no_admins_in_chat']}"
                ),
            ),
        )

    @loader.command(ru_doc="Показывает ботов в группе/канале")
    @loader.tag("no_pm")
    async def bots(self, message):
        """Shows the bots in the chat/channel"""
        bots = await self._chat.get_bots(message.chat)
        if not bots:
            return await utils.answer(message, self.strings["no_bots_in_chat"])
        await utils.answer(
            message,
            self.strings["bot_list"].format(
                count=len(bots),
                bots="\n".join(
                    f"<tg-emoji emoji-id=5774022692642492953>✅</tg-emoji> <a href='tg://user?id={bot.id}'>{bot.first_name}</a> [<code>{bot.id}</code>]"
                    for bot in bots
                ),
            ),
        )

    @loader.command(ru_doc="Показывает простых участников чата/канала")
    @loader.tag("no_pm")
    async def users(self, message):
        """Shows the users in the chat/channel"""
        users = await self._chat.get_members(message.chat)
        if not users:
            return await utils.answer(message, self.strings["no_user_in_chat"])
        await utils.answer(
            message,
            self.strings["user_list"].format(
                count=len(users),
                users="\n".join(
                    f"<tg-emoji emoji-id=5774022692642492953>✅</tg-emoji> <a href='tg://user?id={user.id}'>{user.first_name}</a> [<code>{user.id}</code>]"
                    for user in users
                ),
            ),
        )

    @loader.command(ru_doc="[-u] [-t] [-r] Забанить участника")
    @loader.tag("no_pm")
    async def ban(self, message):
        """[-u] [-t] [-r] Ban a participant temporarily or permanently"""
        opts = self._parse.opts(utils.get_args(message))
        reason = opts.get("r")
        reply = await message.get_reply_message()
        user = opts.get("u") or (reply.sender_id if reply else None)
        user = await self._client.get_entity(user) if user else None
        if not user:
            return await utils.answer(message, self.strings["no_user"])

        seconds = self._parse.time(opts.get("t")) if opts.get("t") else None
        until_date = (
            (datetime.now(timezone.utc) + timedelta(seconds=seconds)) if seconds else None
        )
        time_info = f" {self._format.time(seconds)}" if seconds else None
        try:
            await self._client.edit_permissions(
                message.chat, user, until_date=until_date, view_messages=False
            )
        except Exception as e:
            logger.error(str(e))
            return await utils.answer(message, self.strings["error"])

        strings = [
            self.strings["user_is_banned"].format(
                id=user.id,
                name=getattr(user, "first_name", None) or getattr(user, "title", ""),
                time_info=time_info or self.strings["forever"],
            )
        ]
        if reason:
            strings.append(self.strings["reason"].format(reason=reason))
        return await utils.answer(message, "\n".join(strings))

    @loader.command(ru_doc="Разбанить пользователя")
    @loader.tag("no_pm")
    async def unban(self, message):
        """[-u] Unban a user"""
        opts = self._parse.opts(utils.get_args(message))
        reply = await message.get_reply_message()
        user = opts.get("u") or (reply.sender_id if reply else None)
        user = await self._client.get_entity(user) if user else None
        if not user:
            return await utils.answer(message, self.strings["no_user"])
        try:
            await self._client.edit_permissions(message.chat, user, view_messages=True)
        except Exception as e:
            logger.error(str(e))
            return await utils.answer(message, self.strings["error"])
        return await utils.answer(
            message,
            self.strings["user_is_unbanned"].format(
                id=user.id,
                name=getattr(user, "first_name", None) or getattr(user, "title", ""),
            ),
        )

    @loader.command(ru_doc="[-u] [-r] Кикнуть участника")
    @loader.tag("no_pm")
    async def kick(self, message):
        """[-u] [-r] Kick a participant"""
        opts = self._parse.opts(utils.get_args(message))
        reason = opts.get("r")
        reply = await message.get_reply_message()
        user = opts.get("u") or (reply.sender_id if reply else None)
        user = await self._client.get_entity(user) if user else None
        if not user:
            return await utils.answer(message, self.strings["no_user"])
        try:
            await self._client.kick_participant(message.chat, user)
        except Exception as e:
            logger.error(str(e))
            return await utils.answer(message, self.strings["error"])
        strings = [
            self.strings["user_is_kicked"].format(
                id=user.id,
                name=getattr(user, "first_name", None) or getattr(user, "title", ""),
            )
        ]
        if reason:
            strings.append(self.strings["reason"].format(reason=reason))
        return await utils.answer(message, "\n".join(strings))

    @loader.command(ru_doc="[-u] [-t] [-r] Замутить участника")
    @loader.tag("no_pm")
    async def mute(self, message):
        """[-u] [-t] [-r] Mute a participant temporarily or permanently"""
        opts = self._parse.opts(utils.get_args(message))
        reason = opts.get("r")
        reply = await message.get_reply_message()
        user = opts.get("u") or (reply.sender_id if reply else None)
        user = await self._client.get_entity(user) if user else None
        if not user:
            return await utils.answer(message, self.strings["no_user"])

        seconds = self._parse.time(opts.get("t")) if opts.get("t") else None
        until_date = (
            (datetime.now(timezone.utc) + timedelta(seconds=seconds)) if seconds else None
        )
        time_info = f" {self._format.time(seconds)}" if seconds else None
        try:
            await self._client.edit_permissions(
                message.chat, user, until_date=until_date, send_messages=False
            )
        except Exception as e:
            logger.error(str(e))
            return await utils.answer(message, self.strings["error"])

        strings = [
            self.strings["user_is_muted"].format(
                id=user.id,
                name=getattr(user, "first_name", None) or getattr(user, "title", ""),
                time_info=time_info or self.strings["forever"],
            )
        ]
        if reason:
            strings.append(self.strings["reason"].format(reason=reason))
        return await utils.answer(message, "\n".join(strings))

    @loader.command(ru_doc="Размутить участника")
    @loader.tag("no_pm")
    async def unmute(self, message):
        """Unmute a participant"""
        opts = self._parse.opts(utils.get_args(message))
        reply = await message.get_reply_message()
        user = opts.get("u") or (reply.sender_id if reply else None)
        user = await self._client.get_entity(user) if user else None
        if not user:
            return await utils.answer(message, self.strings["no_user"])
        try:
            await self._client.edit_permissions(message.chat, user, send_messages=True)
        except Exception as e:
            logger.error(str(e))
            return await utils.answer(message, self.strings["error"])
        return await utils.answer(
            message,
            self.strings["user_is_unmuted"].format(
                id=user.id,
                name=getattr(user, "first_name", None) or getattr(user, "title", ""),
            ),
        )

    @loader.command(ru_doc="[-g|--group name] [-c|--channel name] - Создать группу/канал")
    async def create(self, message):
        """[-g|--group name] [-c|--channel name] - Create group/channel"""
        opts = self._parse.opts(utils.get_args(message))
        group_name = opts.get("g") or opts.get("group")
        channel_name = opts.get("c") or opts.get("channel")
        if channel_name:
            result = await self._client(
                channels.CreateChannelRequest(title=channel_name, broadcast=True, about="")
            )
            chat = await self._chat.get_info(result.chats[0])
            return await utils.answer(
                message,
                self.strings["channel_created"].format(
                    link=chat.get("link"), title=channel_name
                ),
            )
        if group_name:
            result = await self._client(
                channels.CreateChannelRequest(title=group_name, megagroup=True, about="")
            )
            chat = await self._chat.get_info(result.chats[0])
            return await utils.answer(
                message,
                self.strings["group_created"].format(
                    link=chat.get("link"), title=group_name
                ),
            )
        return await utils.answer(message, self.strings["invalid_args"])

    @loader.command(ru_doc="Отключает звук и архивирует чат")
    async def dnd(self, message):
        """Mutes and archives the current chat"""
        dnd_ok = await utils.dnd(self._client, await message.get_chat())
        if dnd_ok:
            return await utils.answer(message, self.strings["dnd"])
        return await utils.answer(message, self.strings["dnd_failed"])

    @loader.command(
        ru_doc="-u username/id - Пригласить пользователя в чат (-b пригласить инлайн бота)"
    )
    async def invite(self, message):
        """-u username/id - Invite a user to the chat (use -b to invite the inline bot)"""
        args = utils.get_args(message)
        opts = self._parse.opts(args)
        if opts.get("b") or opts.get("bot"):
            invited = await self._chat.invite_bot(self, message.chat)
            entity = await self._client.get_entity(self.inline.bot_id)
            if invited:
                return await utils.answer(
                    message,
                    self.strings["user_invited"].format(
                        user=entity.first_name, id=entity.id
                    ),
                )
            return await utils.answer(message, self.strings["user_not_invited"])
        reply = await message.get_reply_message()
        user = opts.get("u") or opts.get("user") or (reply.sender_id if reply else None)
        if not user:
            return await utils.answer(message, self.strings["no_user"])
        entity = await self._client.get_entity(user)
        invited = await self._chat.invite_user(message.chat, user)
        if invited:
            return await utils.answer(
                message,
                self.strings["user_invited"].format(user=entity.first_name, id=entity.id),
            )
        return await utils.answer(message, self.strings["user_not_invited"])

    @loader.command(ru_doc="[-i] Получить информацию о сущности")
    async def inspect(self, message):
        """[-i] Get the info about the entity"""
        opts = self._parse.opts(utils.get_args(message))
        reply = await message.get_reply_message()
        target = opts.get("i") or (reply.sender if reply else await message.get_chat())
        if not target:
            return await utils.answer(message, self.strings["no_user"])
        ent = await self._client.get_entity(target)

        if isinstance(ent, types.Channel):
            try:
                chatinfo = await self._chat.get_info(ent)
                photo = chatinfo.get("chat_photo")
                photo = photo if not isinstance(photo, types.PhotoEmpty) else None
                return await utils.answer(
                    message,
                    self.strings["chatinfo"].format(
                        id=chatinfo.get("id"),
                        title=chatinfo.get("title"),
                        about=chatinfo.get("about") or self.strings["no"],
                        admins_count=chatinfo.get("admins_count"),
                        online_count=chatinfo.get("online_count"),
                        participants_count=chatinfo.get("participants_count"),
                        kicked_count=chatinfo.get("kicked_count"),
                        slowmode_seconds=(
                            self._format.time(chatinfo.get("slowmode_seconds"))
                            if chatinfo.get("slowmode_seconds")
                            else self.strings["no"]
                        ),
                        call=(
                            self.strings["yes"] if chatinfo.get("call") else self.strings["no"]
                        ),
                        ttl_period=(
                            self._format.time(chatinfo.get("ttl_period"))
                            if chatinfo.get("ttl_period")
                            else self.strings["no"]
                        ),
                        requests_pending=chatinfo.get("requests_pending"),
                        recent_requesters=(
                            ", ".join(
                                f"<code>{user}</code>"
                                for user in chatinfo.get("recent_requesters")
                            )
                            or self.strings["no"]
                        ),
                        linked_chat_id=chatinfo.get("linked_chat_id")
                        or self.strings["no"],
                        antispam=(
                            self.strings["yes"]
                            if chatinfo.get("antispam")
                            else self.strings["no"]
                        ),
                        participants_hidden=(
                            self.strings["yes"]
                            if chatinfo.get("participants_hidden")
                            else self.strings["no"]
                        ),
                        link=chatinfo.get("link") or self.strings["no"],
                        is_forum=(
                            self.strings["yes"]
                            if chatinfo.get("is_forum")
                            else self.strings["no"]
                        ),
                        type_of=(
                            self.strings["type_group"]
                            if chatinfo.get("is_group")
                            else (
                                self.strings["type_channel"]
                                if chatinfo.get("is_channel")
                                else self.strings["type_unknown"]
                            )
                        ),
                    ),
                    file=(
                        types.InputMediaPhoto(
                            types.InputPhoto(
                                photo.id, photo.access_hash, photo.file_reference
                            )
                        )
                        if photo
                        else None
                    ),
                )
            except Exception as e:
                logger.error(str(e))
                return await utils.answer(message, self.strings["error"])

        if isinstance(ent, types.User):
            try:
                userinfo = await self._user.get_info(ent)
                photo = userinfo.get("profile_photo")
                working_hours = (
                    userinfo.get("business_work_hours").weekly_open
                    if userinfo.get("business_work_hours")
                    else 0
                )
                weekdays = [
                    self.strings["monday"],
                    self.strings["tuesday"],
                    self.strings["wednesday"],
                    self.strings["thursday"],
                    self.strings["friday"],
                    self.strings["saturday"],
                    self.strings["sunday"],
                ]
                personal_channel = userinfo.get("personal_channel")
                working_hours_output = []
                if working_hours:
                    for item in working_hours:
                        day_index = item.start_minute // (24 * 60)
                        day = weekdays[day_index]
                        start = self._parse.minutes_to_hhmm(item.start_minute)
                        end = self._parse.minutes_to_hhmm(item.end_minute)
                        working_hours_output.append(f"<b>{day}: {start} - {end}</b>")
                return await utils.answer(
                    message,
                    self.strings["userinfo"].format(
                        common_chats_count=userinfo.get("common_chats_count") or 0,
                        phone=userinfo.get("phone") or self.strings["no"],
                        common_chats=(
                            ", ".join(
                                f"<a href='{(await self._chat.get_info(channel)).get('link')}'>{channel.title}</a>"
                                for channel in userinfo.get("common_chats")
                            )
                            if userinfo.get("common_chats")
                            else self.strings["no"]
                        ),
                        user_id=userinfo.get("id", 0),
                        first_name=userinfo.get("first_name") or self.strings["no"],
                        last_name=userinfo.get("last_name") or self.strings["no"],
                        about=userinfo.get("about") or self.strings["no"],
                        emoji_status=(
                            f"<tg-emoji emoji-id={userinfo.get('emoji_status')}>🌙</tg-emoji>"
                            if userinfo.get("emoji_status")
                            else self.strings["no"]
                        ),
                        business_work_hours=", ".join(working_hours_output)
                        or self.strings["no"],
                        birthday=(
                            f"{userinfo.get('birthday').day or ''}."
                            f"{userinfo.get('birthday').month or ''}."
                            f"{userinfo.get('birthday').year or ''}"
                            if userinfo.get("birthday")
                            else self.strings["no"]
                        ),
                        stargifts_count=userinfo.get("stargifts_count")
                        or self.strings["no"],
                        usernames=(
                            ", ".join(f"@{username}" for username in userinfo.get("usernames"))
                            if userinfo.get("usernames")
                            else self.strings["no"]
                        ),
                        personal_channel=(
                            f"<a href='{(await self._chat.get_info(personal_channel)).get('link')}'>"
                            f"{personal_channel.title}</a>"
                            if personal_channel
                            else self.strings["no"]
                        ),
                    ),
                    file=(
                        types.InputMediaPhoto(
                            types.InputPhoto(
                                photo.id, photo.access_hash, photo.file_reference
                            )
                        )
                        if photo
                        else None
                    ),
                )
            except Exception as e:
                logger.error(str(e))
                return await utils.answer(message, self.strings["error"])

        return await utils.answer(message, self.strings["error"])

    @loader.command(ru_doc="[-a] [-d] Управлять заявками на вступление")
    @loader.tag("no_pm")
    async def requests(self, message):
        """[-a] [-d] Manage join requests"""
        opts = self._parse.opts(utils.get_args(message))
        approve_list = [x for x in str(opts.get("a", "")).split(",") if x]
        dismiss_list = [x for x in str(opts.get("d", "")).split(",") if x]
        all_list = approve_list + dismiss_list
        all_targets = [
            await self._client.get_entity(int(ent) if ent.isdigit() else ent)
            for ent in all_list
        ]
        for approve in approve_list:
            target = int(approve) if approve.isdigit() else approve
            await self._chat.join_request(message.chat, target, True)
        for dismiss in dismiss_list:
            target = int(dismiss) if dismiss.isdigit() else dismiss
            await self._chat.join_request(message.chat, target, False)
        return await utils.answer(
            message,
            self.strings["requests_checked"].format(
                entities=", ".join(
                    ent.first_name
                    or getattr(ent, "username", None)
                    or str(getattr(ent, "id", "unknown"))
                    for ent in all_targets
                )
            ),
        )

    @loader.command(ru_doc="Получить все свои чаты/каналы")
    async def owns(self, message):
        """Get all your chats/channels"""
        owns = await self._dialog.get_owns(self._client)
        return await utils.answer(
            message,
            self.strings["owns"].format(
                num=len(owns),
                owns="\n".join(
                    f"<tg-emoji emoji-id=5458833171846029357>✅</tg-emoji> {own.title} [<code>{str(own.id).replace('-100', '')}</code>]"
                    for own in owns
                ),
            ),
        )

    @loader.command(ru_doc="[-r] [-u] [-f] - Выдать админку участнику")
    @loader.tag("no_pm")
    async def promote(self, message):
        """[-r] [-u] [-f] - Promote a participant"""
        reply = await message.get_reply_message()
        opts = self._parse.opts(utils.get_args(message))
        user = opts.get("u") or getattr(reply, "sender_id", None)
        if not user:
            return await utils.answer(message, self.strings["no_user"])
        user = await self._client.get_entity(user)
        rank = opts.get("r") or "Admin"
        chat = await message.get_chat()
        perms = await self._chat.get_rights(message.chat, user)
        if not chat.admin_rights or not getattr(chat.admin_rights, "add_admins", False):
            return await utils.answer(message, self.strings["no_rights"])

        full = opts.get("f")
        if full:
            my_rights = [
                r for r, y in chat.admin_rights.to_dict().items() if y and r != "_"
            ]
            new_rights = _AdminRights(0).add(*my_rights)
            await self._admin.set_rights(chat, user, new_rights.to_int(), rank)
            return await utils.answer(
                message,
                self.strings["promoted"].format(
                    id=user.id,
                    name=getattr(user, "first_name", None)
                    or getattr(user, "title", "None"),
                    rights=self.strings["full_rights"],
                ),
            )

        mask = (
            _AdminRights.to_mask(perms.participant.admin_rights)
            if perms and hasattr(perms.participant, "admin_rights")
            else 0
        )

        await utils.answer(
            message,
            self.strings["promote"].format(
                id=user.id,
                name=getattr(user, "first_name", None) or getattr(user, "title", "None"),
                rank=rank,
            ),
            reply_markup=await self.build_markup(user.id, chat.id, mask, rank),
        )

    @loader.command(ru_doc="[-t] [-u] - Ограничить участника")
    @loader.tag("no_pm")
    async def restrict(self, message):
        """[-t] [-u] - Restrict a participant"""
        reply = await message.get_reply_message()
        opts = self._parse.opts(utils.get_args(message))

        user = opts.get("u") or getattr(reply, "sender_id", None)
        if not user:
            return await utils.answer(message, self.strings["no_user"])

        user = await self._client.get_entity(user)
        chat = await message.get_chat()

        if not chat.admin_rights or not getattr(chat.admin_rights, "ban_users", False):
            return await utils.answer(message, self.strings["no_rights"])

        duration = opts.get("t", None)
        duration_str = (
            self._format.time(self._parse.time(duration)) if duration else None
        )

        perms = await self._chat.get_rights(chat, user)
        mask = (
            _BannedRights.MAX_MASK
            - _BannedRights.to_mask(perms.participant.banned_rights)
            if perms and hasattr(perms.participant, "banned_rights")
            else 0
        )

        await utils.answer(
            message,
            self.strings["restrict"].format(
                id=user.id,
                name=getattr(user, "first_name", None) or getattr(user, "title", "None"),
                time=f" {duration_str}" if duration_str else self.strings["forever"],
            ),
            reply_markup=await self.build_markup(
                user.id,
                chat.id,
                mask,
                "-",
                mode="restrict",
                duration=f" {duration_str}" if duration_str else None,
            ),
        )

    async def build_markup(
        self,
        user_id: int,
        chat_id: int,
        mask: int,
        rank: str,
        duration: typing.Optional[str] = None,
        mode: str = "admin",
    ):
        rights_cls = _AdminRights if mode == "admin" else _BannedRights
        rights_names = rights_cls.RIGHTS_LIST
        rights = rights_cls(mask)
        chat = await self._client.get_entity(chat_id)

        markup = utils.chunks(
            [
                {
                    "text": f"{'🟢' if rights.has_index(idx) else '🔴'} {self.strings[name]}",
                    "callback": self._toggle_right,
                    "args": (user_id, chat_id, mask, idx, rank, mode, duration),
                }
                for idx, name in enumerate(rights_names)
                if name != "until_date"
                and not (
                    getattr(chat.default_banned_rights, name, True)
                    if mode != "admin"
                    else False
                )
            ],
            2,
        )

        markup.append(
            [
                {
                    "text": self.strings["apply"],
                    "callback": self._apply_rights,
                    "args": (user_id, chat_id, mask, rank, mode, duration),
                }
            ]
        )
        markup.append([{"text": self.strings["close"], "action": "close"}])
        return markup

    async def _toggle_right(
        self, call, user_id: int, chat_id: int, mask: int, idx: int, rank: str,
        mode: str, duration: str,
    ):
        new_mask = mask ^ (1 << idx)
        new_markup = await self.build_markup(
            user_id, chat_id, new_mask, rank, mode=mode, duration=duration
        )
        user = await self._client.get_entity(user_id)
        title = self.strings["promote"] if mode == "admin" else self.strings["restrict"]
        await utils.answer(
            call,
            title.format(
                id=user_id,
                name=getattr(user, "first_name", None) or getattr(user, "title", "None"),
                rank=rank,
                time=f" {duration}" if duration else self.strings["forever"],
            ),
            reply_markup=new_markup,
        )

    async def _apply_rights(
        self, call, user_id: int, chat_id: int, mask: int, rank: str, mode: str,
        duration: typing.Optional[str] = None,
    ):
        user = await self._client.get_entity(user_id)
        chat = await self._client.get_entity(chat_id)

        if mode == "admin":
            ok = await self._admin.set_rights(chat, user, mask, rank)
            rights_items = _AdminRights(mask).to_dict()
        else:
            ok = await self._chat.set_restrictions(chat, user, mask, duration=duration)
            rights_items = _BannedRights(mask).to_dict()

        rights_list = [r for r, v in rights_items.items() if v]

        if not ok:
            await utils.answer(
                call,
                self.strings["error"],
                reply_markup=[[{"text": self.strings["close"], "action": "close"}]],
            )
            return

        text = (
            self.strings["promoted"]
            if mode == "admin" and mask
            else self.strings["demoted"]
            if mode == "admin" and not mask
            else self.strings["restricted"]
        )

        await utils.answer(
            call,
            text.format(
                id=user_id,
                name=getattr(user, "first_name", None) or getattr(user, "title", "None"),
                rights=", ".join(self.strings[r] for r in rights_list)
                if rights_list
                else self.strings["no"],
                duration=f" {duration}" if duration else self.strings["forever"],
                time=f" {duration}" if duration else self.strings["forever"],
            ),
            reply_markup=[[{"text": self.strings["close"], "action": "close"}]],
        )
