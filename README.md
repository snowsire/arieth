# Arieth

The complete music project lives in [navidrome/](navidrome/README.md):

- Navidrome library audit and FLAC playlist tools shared by Feishin and Symfonium.
- Feishin themes, web overlays, phone-player proxy, setup scripts, and tests.

See [Navidrome and playlist setup](navidrome/README.md) or [Feishin player setup](navidrome/FEISHIN.md).

```sh
git clone https://github.com/snowsire/arieth.git
cd arieth/navidrome
python setup-web.py
python phone-server.py
```

Requires Python 3.9 or newer and an existing Navidrome server. Credentials, generated bundles, library reports, and runtime data remain outside Git. The music project is distributed under [GPL-3.0](navidrome/LICENSE).
