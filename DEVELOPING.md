# Writing Nimbus modules

A module is a single `.py` file with one class that subclasses `loader.Module`.
Nimbus scans `nimbus/modules/` at startup and loads every file there; users can also
install modules at runtime with `.loadmod` (reply to a `.py` file) or `.dlmod` / `.dlm`
(fetch by name from a configured repo, or a raw URL / GitHub blob link).

## Minimal module

```python
from nimbustl.tl.types import Message

from .. import loader, utils


@loader.tds
class PingMod(loader.Module):
    """Replies with pong"""

    strings = {
        "name": "Ping",
        "pong": "🏓 Pong!",
    }

    strings_ru = {
        "pong": "🏓 Понг!",
    }

    @loader.command(
        ru_doc="Проверить, что бот жив",
        en_doc="Check that the bot is alive",
    )
    async def pingcmd(self, message: Message):
        await utils.answer(message, self.strings["pong"])
```

A few things that matter:

- **`@loader.tds`** — required on the class. It wires `ru_doc="..."` / `en_doc="..."`
  (or any `<lang>_doc=`) kwargs on `@loader.command(...)` into per-language docs, so
  `.help` shows the right language automatically.
- **The class docstring** is the module's own description, shown in `.help`.
- **`strings["name"]`** is the module's display name, used in `.help`, `.config <name>`,
  and log lines. Everything else in `strings`/`strings_ru` is looked up via
  `self.strings["key"]` — `strings` is the English/default fallback, `strings_ru` (or
  any other language code) only needs to override what differs.
- **Command methods** are named `<name>cmd` — `pingcmd` becomes `.ping`. Give a command
  an alias with `@loader.command(alias="p")`.

## Config

```python
def __init__(self):
    self.config = loader.ModuleConfig(
        loader.ConfigValue(
            "greeting",
            "Hello!",
            "Text to send",
            validator=loader.validators.String(),
        ),
        loader.ConfigValue(
            "enabled",
            True,
            "Whether the module is active",
            validator=loader.validators.Boolean(),
        ),
    )
```

Read with `self.config["greeting"]`, edit live with `.config <ModuleName> greeting`.
Useful validators from `loader.validators`: `String`, `Integer(minimum=, maximum=)`,
`Float(minimum=, maximum=)`, `Boolean`, `Link`, `RegExp(pattern)`, `Choice([...])`,
`Series(validator=...)` (a list of values), `Hidden(validator=...)` (masks the value in
the UI — use for API keys/tokens), `TelegramID`, `EntityLike`.

## Persistent state

Every module gets its own namespaced storage in the account's database:

```python
self.set("key", value)          # write
self.get("key", default)        # read
self.pointer("key", default)    # a live list/dict that auto-saves on mutation
```

`self.pointer(...)` is what you want for anything you'll append to or delete from —
`self.pointer("items", []).append(x)` and `self.pointer("items", {})[k] = v` both
persist immediately, no extra `self.set(...)` call needed.

## Watchers (reacting to messages)

```python
@loader.watcher("out", "no_commands")
async def watcher(self, message: Message):
    ...
```

Tags filter which messages reach the handler. Common ones: `out` / `in`, `only_pm` /
`no_pm`, `only_groups` / `no_groups`, `mention` / `no_mention`, `only_reply` /
`no_reply`, `only_media` / `no_media`, `no_commands` (skip messages that are commands —
almost always what you want, or you'll re-trigger on your own `.command` messages),
`regex=r"..."`, `contains="..."`, `from_id=...`, `chat_id=...`.

## Background loops

```python
@loader.loop(interval=15, autostart=True)
async def _checker(self):
    ...
```

`interval` is the delay in seconds, `wait_before=True` delays before the first run
instead of after, `stop_clause="db_key"` ties the loop's running state to a db flag.

## Inline UI

`self.inline.form(message=, text=, reply_markup=[...])` for confirm/cancel-style
cards, `self.inline.list(message, pages)` for paginated lists, `self.inline.gallery(...)`
for image carousels. Callback buttons take `{"text": ..., "callback": self.method, "args": (...)}`
or `{"text": ..., "action": "close"}`; callback methods are `async def method(self, call: InlineCall, *args)`.

## Untrusted text goes through `utils.escape_html`

Any command output is rendered as HTML. If you interpolate user-supplied text (a
command argument, a chat message, a note someone else wrote) into a larger templated
string, escape it first — `utils.escape_html(text)` — or a stray `<`/`&` breaks the
message. Text that *is* the entire response (nothing else around it) doesn't need this;
Nimbus renders it as-is, same as `.tr`'s output.

## Useful `# meta` / `# scope` pragmas

Put these as comments anywhere in the file:

```python
# meta developer: your_name
# scope: requires some-pip-package another-one
# scope: packages some-apt-package
# scope: ffmpeg
# scope: inline
# scope: nimbus_min 2.5.0
```

`requires`/`packages` are auto-installed before the module loads. `ffmpeg`/`inline`
refuse to load if that requirement isn't met. `nimbus_min` refuses to load on an older
Nimbus version and prompts the user to update instead of failing confusingly.

## Testing your module

- `.loadmod` replying to the `.py` file — loads it from a local file, no network needed.
- `.dlmod <raw file URL>` or a GitHub blob link (`.../blob/.../file.py`) — loads it
  straight from a URL.
- `.unloadmod <ModuleName>` to remove it and try again.

## Submitting to the built-in catalog

`.dlm <name>` (alias of `.dlmod`) pulls from `nimbus/modules/loader.py`'s
`MODULES_REPO` config, which defaults to this repo's own [`modules/`](modules/)
directory — a curated catalog, separate from the always-loaded core modules in
`nimbus/modules/`. To add yours:

1. Drop `modules/<name>.py` in this repo, written as above.
2. Add `<name>` (no `.py`) as a new line in [`modules/full.txt`](modules/full.txt).
3. Open a PR. Once merged to `master`, `.dlm <name>` finds it for everyone on the
   default config.

Keep catalog modules self-contained and reasonably scoped — no extra runtime services,
no hardcoded chats/servers to phone home to, and license header comments crediting
yourself are fine (see any file in `modules/` for the expected style).
