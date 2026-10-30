# Arieth

This repository maintains the overlays and local proxy for Feishin 1.17.0.
The `source/` directory, when present, is an ignored upstream reference archive.
Do not commit credentials, browser profiles, logs, library reports, screenshots,
installed executables, or generated web bundles/settings.

Run `python -m unittest discover -s tests -v` and `python setup-web.py` after changes.
Use Conventional Commits. Keep the proxy bound to loopback and preserve native
Feishin playback, authentication, and lyric timing.
