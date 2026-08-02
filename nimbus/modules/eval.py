# ©️ Dan Gazizullin, 2021-2023
# This file is a part of Hikka Userbot
# 🌐 https://github.com/hikariatama/Hikka
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

# ©️ Codrago, 2024-2030
# This file is a part of Heroku Userbot
# 🌐 https://github.com/coddrago/Heroku
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

# ©️ ziahka, 2026
# This file is a part of Nimbus Userbot
# 🌐 https://github.com/ziahka/Nimbus
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

import asyncio
import contextlib
import dataclasses
import datetime
import itertools
import json
import logging
import os
import random
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import typing
from io import StringIO
from types import ModuleType

import nimbustl
from nimbustl.errors.rpcerrorlist import MessageIdInvalidError
from nimbustl.sessions import StringSession
from nimbustl.tl.types import Message
from meval import meval

from .. import loader, main, utils
from ..log import NimbusException

logger = logging.getLogger(__name__)

# Premium emoji ids that exist for a given language's logo. The rest share the
# generic code badge — inventing ids just renders as a broken sticker.
E_CODE = "4985626654563894116"
E_PYTHON = "4985626654563894116"
E_C = "4986046904228905931"
E_CPP = "4985844035743646190"
E_RUST = "5424780918776671920"
E_GO = "4994652309293105740"
E_JS = "4985643941807260310"

# Compilation may legitimately take a while; running must not, or a stray
# `while(1)` would pin a core until the process is killed.
BUILD_TIMEOUT = 30
RUN_TIMEOUT = 10

# Brainf*ck has no runtime to shell out to, so it gets an interpreter here. The
# step cap is what stops `+[]` from hanging the executor thread forever.
BF_STEP_LIMIT = 5_000_000
BF_TAPE_SIZE = 30_000


def _split_sql(script: str) -> list[str]:
    """
    Split a script into statements

    Naively splitting on `;` cuts strings like `'a;b'` in half, so let SQLite
    itself say when what we've accumulated is a complete statement.
    """
    statements: list[str] = []
    buffer = ""

    for chunk in re.split(r"(;)", script):
        buffer += chunk
        if chunk == ";" and sqlite3.complete_statement(buffer):
            statements.append(buffer)
            buffer = ""

    statements.append(buffer)

    return [statement for statement in statements if statement.strip()]


@dataclasses.dataclass(frozen=True)
class Language:
    """One external toolchain `.e*` can hand code to"""

    name: str
    emoji: str
    highlight: str
    filename: str
    probe: tuple[str, ...]
    run: tuple[str, ...]
    build: tuple[str, ...] | None = None

    @property
    def executable(self) -> str:
        return self.probe[0]


LANGUAGES: dict[str, Language] = {
    "ec": Language(
        name="C (gcc)",
        emoji=E_C,
        highlight="c",
        # Used to be written as `code.cpp` and handed to gcc, which infers the
        # language from the extension — so `.ec` was quietly compiling C++.
        filename="code.c",
        probe=("gcc", "--version"),
        build=("gcc", "-o", "code", "code.c"),
        run=("./code",),
    ),
    "ecpp": Language(
        name="C++ (g++)",
        emoji=E_CPP,
        highlight="cpp",
        filename="code.cpp",
        probe=("g++", "--version"),
        build=("g++", "-o", "code", "code.cpp"),
        run=("./code",),
    ),
    "ers": Language(
        name="Rust (rustc)",
        emoji=E_RUST,
        highlight="rust",
        filename="code.rs",
        probe=("rustc", "--version"),
        build=("rustc", "code.rs", "-o", "code"),
        run=("./code",),
    ),
    "eg": Language(
        name="Go",
        emoji=E_GO,
        highlight="go",
        filename="code.go",
        probe=("go", "version"),
        run=("go", "run", "code.go"),
    ),
    "enode": Language(
        name="Node.js",
        emoji=E_JS,
        highlight="javascript",
        filename="code.js",
        probe=("node", "--version"),
        run=("node", "code.js"),
    ),
    "ets": Language(
        name="TypeScript (deno)",
        emoji=E_JS,
        highlight="typescript",
        filename="code.ts",
        probe=("deno", "--version"),
        # `--no-prompt` matters: without it deno blocks on an interactive
        # permission question that nobody is there to answer.
        run=("deno", "run", "--quiet", "--no-prompt", "code.ts"),
    ),
    "ephp": Language(
        name="PHP",
        emoji=E_CODE,
        highlight="php",
        filename="code.php",
        probe=("php", "--version"),
        run=("php", "code.php"),
    ),
    "eruby": Language(
        name="Ruby",
        emoji=E_CODE,
        highlight="ruby",
        filename="code.rb",
        probe=("ruby", "--version"),
        run=("ruby", "code.rb"),
    ),
    "elua": Language(
        name="Lua",
        emoji=E_CODE,
        highlight="lua",
        filename="code.lua",
        probe=("lua", "-v"),
        run=("lua", "code.lua"),
    ),
    "eperl": Language(
        name="Perl",
        emoji=E_CODE,
        highlight="perl",
        filename="code.pl",
        probe=("perl", "--version"),
        run=("perl", "code.pl"),
    ),
    "ejava": Language(
        name="Java",
        emoji=E_CODE,
        highlight="java",
        filename="Main.java",
        probe=("java", "--version"),
        # Single-file source mode (JEP 330, Java 11+) — compiles in memory
        run=("java", "Main.java"),
    ),
    "ehs": Language(
        name="Haskell (runghc)",
        emoji=E_CODE,
        highlight="haskell",
        filename="code.hs",
        probe=("runghc", "--version"),
        run=("runghc", "code.hs"),
    ),
    "esh": Language(
        name="Bash",
        emoji=E_CODE,
        highlight="bash",
        filename="code.sh",
        probe=("bash", "--version"),
        run=("bash", "code.sh"),
    ),
}


@loader.tds
class Evaluator(loader.Module):
    """Evaluates code in various languages"""

    strings = {
        "name": "Evaluator",
        "no_code": (
            "<tg-emoji emoji-id=5210952531676504517>🚫</tg-emoji> <b>Give me some"
            " code</b> — as an argument, or reply to a message."
        ),
        "timeout": "Timed out after {}s",
        "langs_header": (
            "<tg-emoji emoji-id=4985626654563894116>💻</tg-emoji> <b>Toolchains on"
            " this machine</b>"
        ),
        "langs_hint": (
            "<i>Everything below is a</i> <code>{prefix}e…</code> <i>command."
            " Missing ones just need the compiler installed.</i>"
        ),
    }

    strings_ru = {
        "no_code": (
            "<tg-emoji emoji-id=5210952531676504517>🚫</tg-emoji> <b>Дай код</b> —"
            " аргументом или ответом на сообщение."
        ),
        "timeout": "Превышено время ожидания ({}с)",
        "langs_header": (
            "<tg-emoji emoji-id=4985626654563894116>💻</tg-emoji> <b>Тулчейны на этой"
            " машине</b>"
        ),
        "langs_hint": (
            "<i>Всё ниже — команды</i> <code>{prefix}e…</code><i>. Отсутствующим"
            " нужен всего лишь установленный компилятор.</i>"
        ),
    }

    class _SecureDB:
        """
        Proxy class to protect sensitive DB fields from eval
        """

        def __init__(self, original_db):
            self._db = original_db

        def __getattr__(self, name):
            return getattr(self._db, name)

        def __getitem__(self, item):
            return self._db[item]

        def set(self, *args, **kwargs):
            if len(args) >= 2 and args[0] == "nimbus.security" and args[1] == "owner":
                raise ValueError(
                    "⚠️ Security Protection: You cannot change the bot owner via evaluator."
                )

            return self._db.set(*args, **kwargs)

    @loader.command(alias="eval")
    async def e(self, message: Message):
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()

        if not args and reply and reply.text:
            args = reply.message

        skip_output = args.startswith(("-so ", "--skip-output "))
        if skip_output:
            args = args.split(" ", 1)[1]

        args = args.replace("\xa0", "\x20")

        real_db = self.db
        self.db = self._SecureDB(real_db)

        output_print = StringIO()

        try:
            start_time = time.time()
            with contextlib.redirect_stdout(output_print):
                result = await meval(
                    args,
                    globals(),
                    **await self.getattrs(message),
                )
            print_output = output_print.getvalue()

        except Exception:
            item = NimbusException.from_exc_info(*sys.exc_info())
            print_output = output_print.getvalue()

            await utils.answer(
                message,
                self.strings["err"].format(
                    E_PYTHON,
                    "python",
                    utils.escape_html(args),
                    "error",
                    self.censor(
                        "\n".join(item.full_stack.splitlines()[:-1])
                        + "\n\n"
                        + "🚫 "
                        + item.full_stack.splitlines()[-1]
                    ),
                )
                + (
                    self.strings["print_outp"].format(
                        "python",
                        utils.escape_html(self.censor(print_output)),
                    )
                    if print_output
                    else ""
                ),
            )

            return
        finally:
            self.db = real_db

        if skip_output:
            return

        if callable(getattr(result, "stringify", None)):
            with contextlib.suppress(Exception):
                result = str(result.stringify())

        exec_time = time.time() - start_time

        with contextlib.suppress(MessageIdInvalidError):
            await utils.answer(
                message,
                self.strings["eval_py"].format(
                    E_PYTHON,
                    "python",
                    utils.escape_html(args),
                )
                + (
                    self.strings["eval_result"].format(
                        "python", utils.escape_html(self.censor(str(result)))
                    )
                    if result or not print_output
                    else ""
                )
                + (
                    self.strings["print_outp"].format(
                        "python",
                        utils.escape_html(self.censor(print_output)),
                    )
                    if print_output
                    else ""
                )
                + (self.strings["time_exec"].format(round(exec_time, 2))),
            )

    async def _code_of(self, message: Message) -> str | None:
        """Code from the argument, falling back to the replied-to message"""
        if code := utils.get_args_raw(message):
            return code

        reply = await message.get_reply_message()
        return reply.message if reply and reply.text else None

    async def _report(
        self,
        message: Message,
        lang: Language | tuple[str, str, str],
        code: str,
        output: str,
        error: bool,
    ) -> None:
        emoji, highlight = (
            (lang.emoji, lang.highlight)
            if isinstance(lang, Language)
            else (lang[1], lang[2])
        )

        with contextlib.suppress(MessageIdInvalidError):
            await utils.answer(
                message,
                self.strings["err" if error else "eval"].format(
                    emoji,
                    highlight,
                    utils.escape_html(code),
                    "error" if error else "output",
                    # Anything the program printed can contain whatever it read
                    # out of the environment, so it goes through the same
                    # redaction the Python evaluator uses.
                    utils.escape_html(self.censor(output)),
                ),
            )

    @staticmethod
    def _shell(argv: typing.Sequence[str], cwd: str, timeout: int) -> tuple[str, bool]:
        """Run `argv`, returning its combined output and whether it failed"""
        try:
            return (
                subprocess.check_output(
                    list(argv),
                    cwd=cwd,
                    stderr=subprocess.STDOUT,
                    timeout=timeout,
                ).decode(errors="replace"),
                False,
            )
        except subprocess.CalledProcessError as e:
            return e.output.decode(errors="replace"), True
        except subprocess.TimeoutExpired:
            return "", True

    async def _run_language(self, message: Message, lang: Language) -> None:
        if not shutil.which(lang.executable):
            await utils.answer(
                message,
                self.strings["no_compiler"].format(lang.emoji, lang.name),
            )
            return

        code = await self._code_of(message)
        if not code:
            await utils.answer(message, self.strings["no_code"])
            return

        if lang.build:
            message = await utils.answer(message, self.strings["compiling"])

        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, lang.filename), "w") as f:
                f.write(code)

            if lang.build:
                # Blocking calls are pushed off the event loop — a 30s compile
                # used to freeze every other command and watcher along with it.
                output, error = await utils.run_sync(
                    self._shell, lang.build, tmpdir, BUILD_TIMEOUT
                )
                if error:
                    await self._report(
                        message,
                        lang,
                        code,
                        output or self.strings["timeout"].format(BUILD_TIMEOUT),
                        True,
                    )
                    return

            output, error = await utils.run_sync(
                self._shell, lang.run, tmpdir, RUN_TIMEOUT
            )

        await self._report(
            message,
            lang,
            code,
            output or (self.strings["timeout"].format(RUN_TIMEOUT) if error else ""),
            error,
        )

    @loader.command(
        ru_doc="<код> - Выполняет код на C++",
        en_doc="<code> - Evaluates C++ code",
    )
    async def ecpp(self, message: Message):
        await self._run_language(message, LANGUAGES["ecpp"])

    @loader.command(
        ru_doc="<код> - Выполняет код на C",
        en_doc="<code> - Evaluates C code",
    )
    async def ec(self, message: Message):
        await self._run_language(message, LANGUAGES["ec"])

    @loader.command(
        ru_doc="<код> - Выполняет код на Rust",
        en_doc="<code> - Evaluates Rust code",
    )
    async def ers(self, message: Message):
        await self._run_language(message, LANGUAGES["ers"])

    @loader.command(
        ru_doc="<код> - Выполняет код на Go",
        en_doc="<code> - Evaluates Go code",
    )
    async def eg(self, message: Message):
        await self._run_language(message, LANGUAGES["eg"])

    @loader.command(
        ru_doc="<код> - Выполняет код на Node.js",
        en_doc="<code> - Evaluates Node.js code",
    )
    async def enode(self, message: Message):
        await self._run_language(message, LANGUAGES["enode"])

    @loader.command(
        ru_doc="<код> - Выполняет код на TypeScript (deno)",
        en_doc="<code> - Evaluates TypeScript code (deno)",
    )
    async def ets(self, message: Message):
        await self._run_language(message, LANGUAGES["ets"])

    @loader.command(
        ru_doc="<код> - Выполняет код на PHP",
        en_doc="<code> - Evaluates PHP code",
    )
    async def ephp(self, message: Message):
        await self._run_language(message, LANGUAGES["ephp"])

    @loader.command(
        ru_doc="<код> - Выполняет код на Ruby",
        en_doc="<code> - Evaluates Ruby code",
        alias="erb",
    )
    async def eruby(self, message: Message):
        await self._run_language(message, LANGUAGES["eruby"])

    @loader.command(
        ru_doc="<код> - Выполняет код на Lua",
        en_doc="<code> - Evaluates Lua code",
    )
    async def elua(self, message: Message):
        await self._run_language(message, LANGUAGES["elua"])

    @loader.command(
        ru_doc="<код> - Выполняет код на Perl",
        en_doc="<code> - Evaluates Perl code",
        alias="epl",
    )
    async def eperl(self, message: Message):
        await self._run_language(message, LANGUAGES["eperl"])

    @loader.command(
        ru_doc="<код> - Выполняет код на Java",
        en_doc="<code> - Evaluates Java code",
    )
    async def ejava(self, message: Message):
        await self._run_language(message, LANGUAGES["ejava"])

    @loader.command(
        ru_doc="<код> - Выполняет код на Haskell",
        en_doc="<code> - Evaluates Haskell code",
    )
    async def ehs(self, message: Message):
        await self._run_language(message, LANGUAGES["ehs"])

    @loader.command(
        ru_doc="<код> - Выполняет Bash-скрипт",
        en_doc="<code> - Evaluates a Bash script",
        alias="ebash",
    )
    async def esh(self, message: Message):
        await self._run_language(message, LANGUAGES["esh"])

    @staticmethod
    def _brainfuck(code: str, stdin: str = "") -> str:
        """Interpret Brainf*ck, giving up once the step budget is spent"""
        program = [char for char in code if char in "><+-.,[]"]

        jumps: dict[int, int] = {}
        stack: list[int] = []
        for index, char in enumerate(program):
            if char == "[":
                stack.append(index)
            elif char == "]":
                if not stack:
                    raise ValueError(f"Unmatched ']' at instruction {index}")

                start = stack.pop()
                jumps[start], jumps[index] = index, start

        if stack:
            raise ValueError(f"Unmatched '[' at instruction {stack[-1]}")

        tape = bytearray(BF_TAPE_SIZE)
        out = bytearray()
        pointer = pc = reads = steps = 0

        while pc < len(program):
            steps += 1
            if steps > BF_STEP_LIMIT:
                raise ValueError(f"Gave up after {BF_STEP_LIMIT} instructions")

            match program[pc]:
                case ">":
                    pointer = (pointer + 1) % BF_TAPE_SIZE
                case "<":
                    pointer = (pointer - 1) % BF_TAPE_SIZE
                case "+":
                    tape[pointer] = (tape[pointer] + 1) & 0xFF
                case "-":
                    tape[pointer] = (tape[pointer] - 1) & 0xFF
                case ".":
                    out.append(tape[pointer])
                case ",":
                    tape[pointer] = ord(stdin[reads]) & 0xFF if reads < len(stdin) else 0
                    reads += 1
                case "[" if not tape[pointer]:
                    pc = jumps[pc]
                case "]" if tape[pointer]:
                    pc = jumps[pc]

            pc += 1

        return out.decode(errors="replace")

    @loader.command(
        ru_doc="<код> - Выполняет код на Brainf*ck",
        en_doc="<code> - Evaluates Brainf*ck code",
    )
    async def ebf(self, message: Message):
        code = await self._code_of(message)
        if not code:
            await utils.answer(message, self.strings["no_code"])
            return

        # `,` reads from anything after a `|` separator
        code, _, stdin = code.partition("|")

        try:
            output = await utils.run_sync(self._brainfuck, code, stdin)
            error = False
        except ValueError as e:
            output, error = str(e), True

        await self._report(
            message, ("bf", E_CODE, "brainfuck"), code.strip(), output, error
        )

    @staticmethod
    def _sqlite(script: str) -> str:
        """Run a script against a throwaway in-memory database"""
        rendered: list[str] = []

        with contextlib.closing(sqlite3.connect(":memory:")) as connection:
            cursor = connection.cursor()

            for statement in _split_sql(script):
                cursor.execute(statement)
                if cursor.description is None:
                    # DDL reports -1 rather than a row count
                    rendered.append(
                        "-- ok"
                        if cursor.rowcount < 0
                        else f"-- {cursor.rowcount} row(s) affected"
                    )
                    continue

                headers = [column[0] for column in cursor.description]
                rows = cursor.fetchall()
                widths = [
                    max(
                        len(str(header)),
                        *(len(str(row[index])) for row in rows or [headers]),
                    )
                    for index, header in enumerate(headers)
                ]

                rendered.append(
                    " | ".join(h.ljust(w) for h, w in zip(headers, widths)).rstrip()
                )
                rendered.append("-+-".join("-" * w for w in widths))
                rendered.extend(
                    " | ".join(str(v).ljust(w) for v, w in zip(row, widths)).rstrip()
                    for row in rows
                )

        return "\n".join(rendered)

    @loader.command(
        ru_doc="<sql> - Выполняет SQL во временной in-memory базе SQLite",
        en_doc="<sql> - Runs SQL against a throwaway in-memory SQLite database",
    )
    async def esql(self, message: Message):
        code = await self._code_of(message)
        if not code:
            await utils.answer(message, self.strings["no_code"])
            return

        try:
            output, error = await utils.run_sync(self._sqlite, code), False
        except sqlite3.Error as e:
            output, error = f"{type(e).__name__}: {e}", True

        await self._report(message, ("sql", E_CODE, "sql"), code, output, error)

    @loader.command(
        ru_doc="Показать, какие тулчейны установлены",
        en_doc="Show which language toolchains are installed",
    )
    async def elangs(self, message: Message):
        prefix = self.get_prefix()
        rows = [
            "{} <code>{}{}</code> <b>·</b> {}".format(
                "✅" if shutil.which(lang.executable) else "❌",
                prefix,
                command,
                utils.escape_html(lang.name),
            )
            for command, lang in LANGUAGES.items()
        ]

        # These two need no toolchain at all — they run inside Nimbus
        rows.extend(
            [
                f"✅ <code>{prefix}ebf</code> <b>·</b> Brainf*ck <i>(built in)</i>",
                f"✅ <code>{prefix}esql</code> <b>·</b> SQLite <i>(built in)</i>",
                f"✅ <code>{prefix}e</code> <b>·</b> Python <i>(built in)</i>",
            ]
        )

        await utils.answer(
            message,
            "{}\n<blockquote>{}</blockquote>\n{}".format(
                self.strings["langs_header"],
                "\n".join(rows),
                self.strings["langs_hint"].format(prefix=prefix),
            ),
        )

    def censor(self, ret: str) -> str:
        ret = ret.replace(str(self._client.nimbus_me.phone), "&lt;phone&gt;")

        if redis := os.environ.get("REDIS_URL") or main.get_config_key("redis_uri"):
            ret = ret.replace(redis, f'redis://{"*" * 26}')

        if db := os.environ.get("DATABASE_URL") or main.get_config_key("db_uri"):
            ret = ret.replace(db, f'postgresql://{"*" * 26}')

        if btoken := self._db.get("nimbus.inline", "bot_token", False):
            ret = ret.replace(
                btoken,
                f'{btoken.split(":")[0]}:{"*" * 26}',
            )

        if htoken := self.lookup("LoaderMod").get("token", False):
            ret = ret.replace(htoken, f'eugeo_{"*" * 26}')

        ret = ret.replace(
            StringSession.save(self._client.session),
            "StringSession(**************************)",
        )

        return ret

    async def getattrs(self, message: Message) -> dict:
        reply = await message.get_reply_message()
        return {
            "message": message,
            "client": self._client,
            "reply": reply,
            "r": reply,
            "event": message,
            "chat": message.to_id,
            "chat_id": utils.get_chat_id(message),
            "me": self._client.nimbus_me,
            "nimbustl": nimbustl,
            "telethon": nimbustl,
            "hikkatl": nimbustl,
            "utils": utils,
            "main": main,
            "loader": loader,
            "c": self._client,
            "m": message,
            "lookup": self.lookup,
            "self": self,
            "db": self.db,
            # Batteries the one-liners in a chat always end up needing
            "asyncio": asyncio,
            "datetime": datetime,
            "json": json,
            "os": os,
            "random": random,
            "re": re,
            "sys": sys,
            "time": time,
            "typing": typing,
            **self.get_sub(nimbustl.tl.functions),
            **self.get_sub(nimbustl.tl.types),
        }

    def get_sub(self, obj: typing.Any, _depth: int = 1) -> dict:
        """Get all callable capitalised objects in an object recursively, ignoring _*"""
        return {
            **dict(
                filter(
                    lambda x: x[0][0] != "_"
                    and x[0][0].upper() == x[0][0]
                    and callable(x[1]),
                    obj.__dict__.items(),
                )
            ),
            **dict(
                itertools.chain.from_iterable(
                    [
                        self.get_sub(y[1], _depth + 1).items()
                        for y in filter(
                            lambda x: x[0][0] != "_"
                            and isinstance(x[1], ModuleType)
                            and x[1] != obj
                            and x[1].__package__.rsplit(".", _depth)[0]
                            == "nimbustl.tl",
                            obj.__dict__.items(),
                        )
                    ]
                )
            ),
        }
