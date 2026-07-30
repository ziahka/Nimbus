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
