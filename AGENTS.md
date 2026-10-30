# Arieth

All music-project code lives under `navidrome/`: Navidrome playlist tools,
Feishin 1.17.0 overlays, themes, local proxy, setup scripts, and tests.
Only repository metadata and the GitHub Actions workflow stay at the root.
The `source/` directory, when present, is an ignored upstream reference archive.
Do not commit credentials, browser profiles, logs, library reports, screenshots,
installed executables, or generated web bundles/settings.

From `navidrome/`, run `python -m unittest discover -s tests -v`,
`node --test tests/*.test.cjs`, and `python setup-web.py` after changes.
Use Conventional Commits. Keep the proxy bound to loopback and preserve native
Feishin playback, authentication, and lyric timing.
