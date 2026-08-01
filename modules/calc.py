# meta developer: ziahka
# ©️ ziahka, 2026
# This file is a part of the Nimbus Userbot modules catalog
# 🌐 https://github.com/ziahka/Nimbus
# You can redistribute it and/or modify it under the terms of the GNU AGPLv3
# 🔑 https://www.gnu.org/licenses/agpl-3.0.html

import ast
import math
import operator

from nimbustl.tl.types import Message

from .. import loader, utils

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}
_FUNCS = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log2": math.log2,
    "log10": math.log10,
    "exp": math.exp,
    "floor": math.floor,
    "ceil": math.ceil,
    "abs": abs,
    "round": round,
}
_NAMES = {"pi": math.pi, "e": math.e}
_MAX_POWER_EXPONENT = 1000
_MAX_EXPR_LEN = 200


class _CalcError(ValueError):
    """Raised on invalid or unsafe expressions."""


def _eval_node(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise _CalcError("Only numbers are allowed")

    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > _MAX_POWER_EXPONENT:
            raise _CalcError("Exponent too large")
        return _BIN_OPS[type(node.op)](left, right)

    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand))

    if isinstance(node, ast.Name) and node.id in _NAMES:
        return _NAMES[node.id]

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCS:
            raise _CalcError("Unknown function")
        if node.keywords:
            raise _CalcError("Keyword arguments are not allowed")
        args = [_eval_node(arg) for arg in node.args]
        return _FUNCS[node.func.id](*args)

    raise _CalcError("Invalid expression")


def calculate(expr: str) -> float:
    if len(expr) > _MAX_EXPR_LEN:
        raise _CalcError("Expression too long")

    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        raise _CalcError("Invalid expression") from None

    return _eval_node(tree.body)


@loader.tds
class CalcMod(loader.Module):
    """A safe pocket calculator"""

    strings = {
        "name": "Calc",
        "usage": "🧮 <b>Usage:</b> <code>{prefix}calc &lt;expression&gt;</code>",
        "result": "🧮 <code>{expr}</code> = <code>{result}</code>",
        "error": "🧮 <b>Couldn't evaluate that:</b> <code>{error}</code>",
    }

    strings_ru = {
        "usage": "🧮 <b>Использование:</b> <code>{prefix}calc &lt;выражение&gt;</code>",
        "result": "🧮 <code>{expr}</code> = <code>{result}</code>",
        "error": "🧮 <b>Не удалось вычислить:</b> <code>{error}</code>",
    }

    @loader.command(
        ru_doc="<выражение> - Вычислить арифметическое выражение",
        en_doc="<expression> - Evaluate an arithmetic expression",
    )
    async def calccmd(self, message: Message):
        prefix = self.get_prefix()
        expr = utils.get_args_raw(message)

        if not expr:
            await utils.answer(message, self.strings["usage"].format(prefix=prefix))
            return

        try:
            result = calculate(expr)
        except (_CalcError, ZeroDivisionError, OverflowError, ValueError, TypeError) as e:
            await utils.answer(
                message, self.strings["error"].format(error=utils.escape_html(str(e)))
            )
            return

        await utils.answer(
            message,
            self.strings["result"].format(
                expr=utils.escape_html(expr), result=result
            ),
        )
