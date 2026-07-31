# Nimbus Changelog

## ☁️ Nimbus 2.5.0

 - Added `.afk` / `.unafk` — auto-replies while you're away, with per-chat cooldown and
   automatic turn-off on your next outgoing message
 - Added `.save` / `.note` (`.n`) / `.notes` / `.delnote` — saved text snippets you can
   recall by name
 - Added `.remind` / `.reminders` / `.delremind` — self-reminders on a delay
   (`10m`, `2h`, `1d2h30m`, ...), restart-safe
 - Removed the `.ask` smart command router and the `.tldr` AI summary command —
   dropped the built-in dependency on an external AI provider
 - `.dlmod` / `.dlm <name>` now installs from this repo's own [`modules/`](modules/)
   catalog by default, instead of the original Heroku maintainer's module repo
 - Added a first batch of catalog modules: `.broadcast` (+ `.bcadd`/`.bcdel`/`.bclist`),
   `.purge`, `.calc`
 - Added [`DEVELOPING.md`](DEVELOPING.md), a guide for writing and submitting modules
 - Rebuilt `.nimbus`'s output template (all 9 langpacks): dropped a leftover
   "Developers: @ur_jump" credit line pointing at the original Hikka project's contact
   that had survived the entire rebrand, fixed a nonsensical 📁 icon on the library
   version line, and restyled it into one boxed card with ping/uptime
 - Restyled `.info` with the same closing tagline treatment
 - Both cards' tagline is configurable (`.config Settings status_line`,
   `.config NimbusInfo status_line`)
 - Redrawn all 12 banner images (`assets/*.png`) with a glowing dusk-sky cloud scene —
   soft rim lighting, stars, a moon, sparkle accents — generated procedurally via
   [`tools/generate_banners.py`](tools/generate_banners.py) (Pillow + numpy, run through
   `uv run --with pillow --with numpy`)
 - Upgraded several plain emoji to premium/custom Telegram emoji across `.notes`,
   `.remind`, `.broadcast`, and the `.nimbus` card, reusing emoji IDs already verified
   elsewhere in this codebase

## ☁️ Nimbus 2.4.0

 - Replaced every remaining external asset reference with locally-stored, self-branded
   images (banners, avatar, install/update graphics) and a redrawn startup banner
 - Removed a background poller that fetched and displayed an "announcement" message
   from a third-party-controlled remote endpoint — not something an independent fork
   should keep listening to
 - Set the sole owner credit in the version command's output

## ☁️ Nimbus 2.3.0

 - Vendored the MTProto client library locally under `vendor/nimbustl` instead of an
   external PyPI dependency
 - Fixed a real bug this uncovered: the vendored library expects a `self.nimbus_me`
   attribute for premium-status checks (e.g. reaction limits), which an earlier rename
   had silently dropped when setting client attributes in `main.py`
 - Renamed matching internal identifiers (imports, class names, error types) to suit

## ☁️ Nimbus 2.2.0

 - Initial release under the new name and branding
 - Renamed internal package, modules, classes and the version command to match
 - Bumped `certifi` and `rsa` to their latest patch releases
