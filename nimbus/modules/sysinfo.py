# ©️ ziahka, 2026
# This file is a part of Nimbus Userbot
# 🌐 https://github.com/ziahka/Nimbus
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

import logging
import platform
import sys
import time

from nimbustl.tl.types import Message

from .. import loader, utils
from ..version import __version__

logger = logging.getLogger(__name__)

E_HOST = "<tg-emoji emoji-id=5188377234380954537>🪐</tg-emoji>"
E_OS = "<tg-emoji emoji-id=5409117246062625941>⚙️</tg-emoji>"
E_KERNEL = "<tg-emoji emoji-id=5411341373402025345>⏩</tg-emoji>"
E_PACKAGE = "<tg-emoji emoji-id=5404521025465518254>📦</tg-emoji>"
E_UPTIME = "<tg-emoji emoji-id=5409373221818496084>💘</tg-emoji>"
E_CPU = "<tg-emoji emoji-id=5411252368794746740>📈</tg-emoji>"
E_RAM = "<tg-emoji emoji-id=5134202243486057363>💫</tg-emoji>"
E_DISK = "<tg-emoji emoji-id=5256113064821926998>📁</tg-emoji>"
E_CORES = "<tg-emoji emoji-id=5341715473882955310>⚙️</tg-emoji>"


@loader.tds
class SysInfoMod(loader.Module):
    """A neofetch-style card for the machine Nimbus runs on"""

    strings = {
        "name": "SysInfo",
        "card": (
            f"{E_HOST} <b>{{host}}</b>  <i>·</i>  <code>{{platform}}</code>\n"
            "<blockquote>"
            f"{E_OS} <b>OS:</b> {{os}}\n"
            f"{E_KERNEL} <b>Kernel:</b> <code>{{kernel}}</code>\n"
            f"{E_PACKAGE} <b>Python:</b> {{python}} <b>·</b> <b>Nimbus:</b> {{version}}\n"
            f"{E_UPTIME} <b>Uptime:</b> {{uptime}}"
            "</blockquote>\n"
            "<blockquote>"
            f"{E_CPU} <b>CPU</b>  <code>{{cpu_bar}}</code>  {{cpu_percent}}%\n"
            f"{E_RAM} <b>RAM</b>  <code>{{ram_bar}}</code>  {{ram_percent}}%"
            "  <i>{ram_used} / {ram_total}</i>\n"
            f"{E_DISK} <b>Disk</b> <code>{{disk_bar}}</code>  {{disk_percent}}%"
            "  <i>{disk_used} / {disk_total}</i>"
            "</blockquote>\n"
            "<blockquote>"
            f"{E_CORES} <b>Cores:</b> {{cores}}  <b>·</b>  <b>Nimbus RSS:</b>"
            " {proc_ram} MB"
            "</blockquote>"
        ),
        "bad_template": (
            "🚫 <b>Your custom template references an unknown placeholder:</b>"
            " <code>{}</code>"
        ),
    }

    strings_ru = {
        "card": (
            f"{E_HOST} <b>{{host}}</b>  <i>·</i>  <code>{{platform}}</code>\n"
            "<blockquote>"
            f"{E_OS} <b>Система:</b> {{os}}\n"
            f"{E_KERNEL} <b>Ядро:</b> <code>{{kernel}}</code>\n"
            f"{E_PACKAGE} <b>Python:</b> {{python}} <b>·</b> <b>Nimbus:</b> {{version}}\n"
            f"{E_UPTIME} <b>Аптайм:</b> {{uptime}}"
            "</blockquote>\n"
            "<blockquote>"
            f"{E_CPU} <b>ЦП</b>   <code>{{cpu_bar}}</code>  {{cpu_percent}}%\n"
            f"{E_RAM} <b>ОЗУ</b>  <code>{{ram_bar}}</code>  {{ram_percent}}%"
            "  <i>{ram_used} / {ram_total}</i>\n"
            f"{E_DISK} <b>Диск</b> <code>{{disk_bar}}</code>  {{disk_percent}}%"
            "  <i>{disk_used} / {disk_total}</i>"
            "</blockquote>\n"
            "<blockquote>"
            f"{E_CORES} <b>Ядер:</b> {{cores}}  <b>·</b>  <b>Nimbus в памяти:</b>"
            " {proc_ram} МБ"
            "</blockquote>"
        ),
        "bad_template": (
            "🚫 <b>В твоём шаблоне есть неизвестный плейсхолдер:</b> <code>{}</code>"
        ),
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "custom_template",
                None,
                (
                    "Full custom template for the card. Placeholders: {host},"
                    " {platform}, {os}, {kernel}, {python}, {version}, {uptime},"
                    " {cpu_bar}, {cpu_percent}, {cores}, {ram_bar}, {ram_percent},"
                    " {ram_used}, {ram_total}, {disk_bar}, {disk_percent},"
                    " {disk_used}, {disk_total}, {proc_ram}, {boot}. Leave empty for"
                    " the built-in card"
                ),
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "bar_width",
                12,
                "Width of the CPU/RAM/disk bars, in characters",
                validator=loader.validators.Integer(minimum=4, maximum=30),
            ),
        )

    def _collect(self) -> dict:
        """Gather every placeholder value, degrading gracefully without psutil"""
        width = self.config["bar_width"]
        disk = utils.get_disk_usage()

        ram_total = ram_used = 0
        ram_percent = 0.0
        cores = "?"
        boot = "unknown"

        try:
            import psutil

            memory = psutil.virtual_memory()
            ram_total, ram_used, ram_percent = (
                memory.total,
                memory.used,
                memory.percent,
            )
            physical = psutil.cpu_count(logical=False)
            logical = psutil.cpu_count(logical=True)
            cores = f"{physical or '?'} / {logical or '?'} logical"
            boot = time.strftime("%Y-%m-%d %H:%M", time.localtime(psutil.boot_time()))
        except Exception:
            logger.debug("psutil unavailable, sysinfo card degraded", exc_info=True)

        try:
            cpu_percent = float(utils.get_cpu_usage())
        except (TypeError, ValueError):
            cpu_percent = 0.0

        return {
            "host": utils.escape_html(utils.get_hostname()),
            "platform": utils.escape_html(utils.get_named_platform()),
            "os": utils.escape_html(f"{platform.system()} {platform.machine()}"),
            "kernel": utils.escape_html(platform.release()),
            "python": ".".join(map(str, sys.version_info[:3])),
            "version": ".".join(map(str, __version__)),
            "uptime": utils.formatted_uptime(),
            "cpu_bar": utils.progress_bar(cpu_percent, width),
            "cpu_percent": f"{cpu_percent:.1f}",
            "cores": cores,
            "ram_bar": utils.progress_bar(ram_percent, width),
            "ram_percent": f"{ram_percent:.1f}",
            "ram_used": utils.humanize_bytes(ram_used),
            "ram_total": utils.humanize_bytes(ram_total),
            "disk_bar": utils.progress_bar(disk["percent"], width),
            "disk_percent": f"{disk['percent']:.1f}",
            "disk_used": f"{disk['used']} GB",
            "disk_total": f"{disk['total']} GB",
            "proc_ram": utils.get_ram_usage(),
            "boot": boot,
        }

    @loader.command(
        ru_doc="Показать карточку системы",
        en_doc="Show a card describing this machine",
        alias="sys",
    )
    async def neofetch(self, message: Message):
        # psutil's cpu_percent samples for 0.1s, so keep it off the event loop
        data = await utils.run_sync(self._collect)
        template = self.config["custom_template"]
        data = await utils.get_placeholders(data, template)

        try:
            text = (template or self.strings["card"]).format(**data)
        except KeyError as e:
            await utils.answer(
                message,
                self.strings["bad_template"].format(utils.escape_html(str(e))),
            )
            return

        await utils.answer(message, text)
