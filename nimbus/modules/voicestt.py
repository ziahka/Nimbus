# ©️ ziahka, 2026
# This file is a part of Nimbus Userbot
# 🌐 https://github.com/ziahka/Nimbus
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

import logging

import requests
from nimbustl.tl.types import Message

from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class VoiceSTTMod(loader.Module):
    """Auto-transcribes voice messages to text, toggleable on demand"""

    strings = {
        "name": "VoiceSTT",
        "enabled": "🎙 <b>Voice auto-transcription enabled.</b>",
        "disabled": "🔇 <b>Voice auto-transcription disabled.</b>",
        "status_on": "🎙 <b>Voice auto-transcription is on.</b>",
        "status_off": "🔇 <b>Voice auto-transcription is off.</b>",
        "no_key": (
            "🚫 <b>No API key set.</b> Set one with"
            " <code>.config VoiceSTT api_key <your key></code>"
            " (get one at https://platform.openai.com/api-keys)"
        ),
        "result": "🎙 <b>Transcript:</b>\n{text}",
        "empty": "🎙 <i>Couldn't make out any speech in this voice message.</i>",
        "error": "🚫 <b>Transcription failed:</b> <code>{error}</code>",
    }

    strings_ru = {
        "enabled": "🎙 <b>Авто-распознавание голосовых включено.</b>",
        "disabled": "🔇 <b>Авто-распознавание голосовых выключено.</b>",
        "status_on": "🎙 <b>Авто-распознавание голосовых сейчас включено.</b>",
        "status_off": "🔇 <b>Авто-распознавание голосовых сейчас выключено.</b>",
        "no_key": (
            "🚫 <b>Не задан API-ключ.</b> Укажи его командой"
            " <code>.config VoiceSTT api_key <твой ключ></code>"
            " (получить можно на https://platform.openai.com/api-keys)"
        ),
        "result": "🎙 <b>Расшифровка:</b>\n{text}",
        "empty": "🎙 <i>Не удалось разобрать речь в этом голосовом сообщении.</i>",
        "error": "🚫 <b>Распознавание не удалось:</b> <code>{error}</code>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_key",
                None,
                "OpenAI API key used for transcription (platform.openai.com/api-keys)",
                validator=loader.validators.Hidden(),
            ),
            loader.ConfigValue(
                "model",
                "whisper-1",
                "Transcription model to use",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "language",
                None,
                (
                    "Optional ISO-639-1 language hint (e.g. 'en', 'ru')."
                    " Leave empty for auto-detection"
                ),
                validator=loader.validators.String(length=2),
            ),
            loader.ConfigValue(
                "groups",
                False,
                "Also transcribe voice messages in group chats, not just PMs",
                validator=loader.validators.Boolean(),
            ),
        )

    def _eligible(self, message: Message) -> bool:
        if getattr(message, "is_private", False):
            return True

        return bool(self.config["groups"])

    @loader.command(
        ru_doc="[on|off] - Переключить авто-распознавание голосовых сообщений",
        en_doc="[on|off] - Toggle voice message auto-transcription",
    )
    async def sttcmd(self, message: Message):
        args = utils.get_args_raw(message).strip().lower()

        if args in ("on", "1", "вкл", "включить"):
            enabled = True
        elif args in ("off", "0", "выкл", "выключить"):
            enabled = False
        elif not args:
            enabled = not self.get("enabled", False)
        else:
            enabled = self.get("enabled", False)
            await utils.answer(
                message,
                self.strings["status_on"] if enabled else self.strings["status_off"],
            )
            return

        self.set("enabled", enabled)
        await utils.answer(
            message, self.strings["enabled"] if enabled else self.strings["disabled"]
        )

    async def _transcribe(self, audio: bytes) -> str:
        def _do() -> str:
            data = {"model": self.config["model"] or "whisper-1"}
            if self.config["language"]:
                data["language"] = self.config["language"]

            response = requests.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {self.config['api_key']}"},
                files={"file": ("voice.ogg", audio, "audio/ogg")},
                data=data,
                timeout=60,
            )
            response.raise_for_status()
            return response.json().get("text", "").strip()

        return await utils.run_sync(_do)

    @loader.watcher("in", "no_commands")
    async def _watcher(self, message: Message):
        if not self.get("enabled", False):
            return

        if not message.voice:
            return

        if not self._eligible(message):
            return

        if not self.config["api_key"]:
            self.set("enabled", False)
            await message.reply(self.strings["no_key"])
            return

        try:
            audio = await message.download_media(bytes)
        except Exception:
            logger.exception("Failed to download voice message for transcription")
            return

        try:
            text = await self._transcribe(audio)
        except Exception as e:
            logger.exception("Voice transcription request failed")
            await message.reply(
                self.strings["error"].format(error=utils.escape_html(str(e)))
            )
            return

        await message.reply(
            self.strings["result"].format(text=utils.escape_html(text))
            if text
            else self.strings["empty"]
        )
