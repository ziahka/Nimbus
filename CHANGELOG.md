# Nimbus Changelog

## ☁️ Nimbus 2.3.0

 - Vendored the MTProto client library as `vendor/nimbustl` (renamed from the external
   `herokutl` package, MIT-licensed) instead of depending on it from PyPI — no more
   "Heroku" in the dependency chain. `requirements.txt` now installs it from a local path
 - Fixed a real bug this uncovered: the library expects a `self.nimbus_me` (formerly
   `self.heroku_me`) attribute for premium-status checks (e.g. reaction limits), which
   the earlier rename had silently dropped when setting client attributes in `main.py`
 - Everything else (imports, class names, error types) renamed to match: `nimbustl`

## ☁️ Nimbus 2.2.0

 - Initial release under the new name and branding
 - Renamed internal package, modules, classes and the version command to match
 - Bumped `certifi` and `rsa` to their latest patch releases
 - Full history prior to this fork is archived in [UPSTREAM_CHANGELOG.md](UPSTREAM_CHANGELOG.md)
