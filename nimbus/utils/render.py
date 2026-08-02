# ©️ ziahka, 2026
# This file is a part of Nimbus Userbot
# 🌐 https://github.com/ziahka/Nimbus
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

"""Small text-rendering helpers shared by Nimbus' info cards"""

import logging

logger = logging.getLogger(__name__)

BAR_FULL = "█"
BAR_EMPTY = "░"

SIZE_UNITS = ("B", "KB", "MB", "GB", "TB", "PB")


def progress_bar(
    percent: float,
    /,
    width: int = 10,
    *,
    full: str = BAR_FULL,
    empty: str = BAR_EMPTY,
) -> str:
    """
    Render a percentage as a fixed-width block bar
    :param percent: Value in 0..100 (clamped)
    :param width: Bar width in characters
    :param full: Character for the filled part
    :param empty: Character for the empty part
    :return: Bar string, exactly `width` characters long
    """
    percent = min(100.0, max(0.0, float(percent)))
    filled = round(percent / 100 * width)
    return full * filled + empty * (width - filled)


def humanize_bytes(size: float, /, precision: int = 1) -> str:
    """
    Format a byte count with a human-readable unit
    :param size: Size in bytes
    :param precision: Digits after the decimal point
    :return: e.g. "1.4 GB"
    """
    size = float(size)
    for unit in SIZE_UNITS:
        if abs(size) < 1024 or unit == SIZE_UNITS[-1]:
            return f"{size:.{precision}f} {unit}"

        size /= 1024

    return f"{size:.{precision}f} {SIZE_UNITS[-1]}"


def humanize_number(number: float, /) -> str:
    """
    Format a count compactly: 1234 -> "1.2K", 1500000 -> "1.5M"
    :param number: Number to format
    :return: Compact representation
    """
    number = float(number)
    for threshold, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")):
        if abs(number) >= threshold:
            return f"{number / threshold:.1f}{suffix}".replace(".0", "")

    return str(int(number))


def sparkline(values: list[float], /) -> str:
    """
    Render a series as a one-line unicode sparkline
    :param values: Series to render
    :return: One character per value, empty string for an empty series
    """
    if not values:
        return ""

    blocks = "▁▂▃▄▅▆▇█"
    lowest, highest = min(values), max(values)
    span = highest - lowest

    if not span:
        # A flat series would otherwise render as a solid block wall
        return blocks[0] * len(values)

    return "".join(
        blocks[min(len(blocks) - 1, int((value - lowest) / span * len(blocks)))]
        for value in values
    )
