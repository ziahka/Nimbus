# ©️ ziahka, 2026
# This file is a part of Nimbus Userbot
# 🌐 https://github.com/ziahka/Nimbus
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

import inspect
import json
import logging
import re

import aiohttp
from nimbustl.tl.types import Message

from .. import loader, utils
from ..inline.types import InlineCall

logger = logging.getLogger(__name__)

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


class _NotJSON(ValueError):
    """Raised when the configured endpoint didn't return JSON at all."""


@loader.tds
class SmartCommandMod(loader.Module):
    """Turns a plain-language request into the right command, so you don't have to remember exact syntax"""

    strings = {
        "name": "SmartCommand",
        "no_key": (
            "🪄 <b>No API key configured.</b>\n"
            "Set one with <code>{prefix}config SmartCommand api_key</code> "
            "(any OpenAI-compatible provider works — set <code>base_url</code> too if it's not OpenAI itself)."
        ),
        "no_query": "🪄 <b>Tell me what you want to do</b>, e.g. <code>{prefix}ask mute this chat for an hour</code>",
        "thinking": "🪄 <b>Thinking...</b>",
        "no_match": "🪄 <b>Couldn't match that to a loaded command.</b>\n<i>{reasoning}</i>",
        "bad_response": "🪄 <b>The model didn't return something I could parse.</b> Try rephrasing.",
        "not_json": (
            "🪄 <b>That endpoint didn't return JSON</b> — got an HTML page back from "
            "<code>{url}</code> instead.\n"
            "Most OpenAI-compatible providers need a <code>/v1</code> suffix on "
            "<code>base_url</code>. Double check the value with "
            "<code>{prefix}config SmartCommand base_url</code>."
        ),
        "request_failed": "🪄 <b>Request to the model failed:</b> <code>{error}</code>",
        "confirm": (
            "🪄 <b>Best match:</b> <code>{prefix}{command} {args}</code>\n"
            "<i>{reasoning}</i>"
        ),
        "btn_run": "✅ Run",
        "btn_cancel": "❌ Cancel",
        "running": "🪄 Running <code>{prefix}{command} {args}</code>...",
    }

    strings_ru = {
        "no_key": (
            "🪄 <b>Не задан API-ключ.</b>\n"
            "Укажи его через <code>{prefix}config SmartCommand api_key</code> "
            "(подходит любой OpenAI-совместимый провайдер — если это не сам OpenAI, укажи ещё и <code>base_url</code>)."
        ),
        "no_query": "🪄 <b>Опиши, что нужно сделать</b>, например <code>{prefix}ask замьють этот чат на час</code>",
        "thinking": "🪄 <b>Думаю...</b>",
        "no_match": "🪄 <b>Не удалось подобрать команду среди загруженных.</b>\n<i>{reasoning}</i>",
        "bad_response": "🪄 <b>Модель ответила не тем, что я смог разобрать.</b> Попробуй переформулировать.",
        "not_json": (
            "🪄 <b>Этот адрес вернул не JSON</b> — вместо ответа API пришла HTML-страница "
            "с <code>{url}</code>.\n"
            "Большинству OpenAI-совместимых провайдеров нужен суффикс <code>/v1</code> "
            "в <code>base_url</code>. Проверь значение через "
            "<code>{prefix}config SmartCommand base_url</code>."
        ),
        "request_failed": "🪄 <b>Запрос к модели не удался:</b> <code>{error}</code>",
        "confirm": (
            "🪄 <b>Похоже, нужно:</b> <code>{prefix}{command} {args}</code>\n"
            "<i>{reasoning}</i>"
        ),
        "btn_run": "✅ Выполнить",
        "btn_cancel": "❌ Отмена",
        "running": "🪄 Выполняю <code>{prefix}{command} {args}</code>...",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_key",
                None,
                "OpenAI-compatible API key used to interpret .ask requests",
                validator=loader.validators.Hidden(),
            ),
            loader.ConfigValue(
                "base_url",
                "https://api.openai.com/v1",
                "Base URL of the OpenAI-compatible API (change this to use another provider)",
                validator=loader.validators.Link(),
            ),
            loader.ConfigValue(
                "model",
                "gpt-4o-mini",
                "Model name to use for interpreting requests",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "auto_run",
                False,
                "Run the matched command immediately, without asking for confirmation first",
                validator=loader.validators.Boolean(),
            ),
        )

    def _catalog(self) -> str:
        lines = []
        for name, func in sorted(self.allmodules.commands.items()):
            if name == "ask":
                continue
            doc = (inspect.getdoc(func) or "").strip().splitlines()
            doc = doc[0] if doc else "No description"
            lines.append(f"{name}: {doc}")
        return "\n".join(lines)

    async def _route(self, query: str) -> dict:
        system = (
            "You are a command router for a Telegram userbot. Given the user's "
            "plain-language request and a list of available commands (one per "
            "line, as `name: description`), pick the single command that best "
            "fulfills the request and the arguments to pass to it.\n\n"
            "Respond with strict JSON only, no other text, in this exact shape:\n"
            '{"command": "<name from the list, or null if nothing fits>", '
            '"args": "<arguments string, empty if none>", '
            '"reasoning": "<one short sentence, in the same language as the request>"}\n\n'
            f"Available commands:\n{self._catalog()}"
        )

        url = f"{str(self.config['base_url']).rstrip('/')}/chat/completions"

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers={"Authorization": f"Bearer {self.config['api_key']}"},
                json={
                    "model": self.config["model"],
                    "temperature": 0,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": query},
                    ],
                },
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                resp.raise_for_status()
                raw = await resp.text()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            raise _NotJSON(
                self.strings["not_json"].format(url=url, prefix=self.get_prefix())
            ) from None

        content = data["choices"][0]["message"]["content"]
        match = _JSON_BLOCK.search(content)
        if not match:
            raise ValueError(content)

        return json.loads(match.group(0))

    @loader.command(
        ru_doc="Выполнить команду по описанию на естественном языке",
        en_doc="Run a command described in plain language",
    )
    async def askcmd(self, message: Message):
        prefix = self.get_prefix()
        query = utils.get_args_raw(message)

        if not self.config["api_key"]:
            await utils.answer(message, self.strings["no_key"].format(prefix=prefix))
            return

        if not query:
            await utils.answer(message, self.strings["no_query"].format(prefix=prefix))
            return

        message = await utils.answer(message, self.strings["thinking"])

        try:
            decision = await self._route(query)
        except _NotJSON as e:
            await utils.answer(message, str(e))
            return
        except (aiohttp.ClientError, TimeoutError) as e:
            await utils.answer(
                message, self.strings["request_failed"].format(error=e)
            )
            return
        except (ValueError, KeyError, json.JSONDecodeError):
            await utils.answer(message, self.strings["bad_response"])
            return

        command = decision.get("command")
        args = decision.get("args") or ""
        reasoning = decision.get("reasoning") or ""

        if not command or command not in self.allmodules.commands:
            await utils.answer(
                message, self.strings["no_match"].format(reasoning=reasoning)
            )
            return

        if self.config["auto_run"]:
            await utils.answer(
                message,
                self.strings["running"].format(
                    prefix=prefix, command=command, args=args
                ),
            )
            await self.invoke(command, args, message=message, edit=True)
            return

        await self.inline.form(
            message=message,
            text=self.strings["confirm"].format(
                prefix=prefix, command=command, args=args, reasoning=reasoning
            ),
            reply_markup=[
                {
                    "text": self.strings["btn_run"],
                    "callback": self._run_picked,
                    "args": (utils.get_chat_id(message), command, args),
                },
                {"text": self.strings["btn_cancel"], "action": "close"},
            ],
        )

    async def _run_picked(
        self, call: InlineCall, chat_id: int, command: str, args: str
    ):
        prefix = self.get_prefix()
        await call.edit(
            self.strings["running"].format(prefix=prefix, command=command, args=args)
        )
        await self.invoke(command, args, peer=chat_id)
