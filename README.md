# Arieth

Arieth customizes [Feishin 1.17.0](https://github.com/jeffvli/feishin/tree/v1.17.0) for a personal Navidrome music library. It adds a crimson glass theme, geometric backgrounds, phone navigation with an exposed search field, artist-photo player backgrounds, a full-resolution album-cover viewer, and lyric styling that preserves Feishin's native timing and tap-to-seek behavior.

This repository contains the maintained customization sources and local web proxy. Official Feishin bundles are downloaded during setup, verified against the pinned OCI manifest and layer SHA-256 digests, and kept out of Git. The upstream reference archive, music library, credentials, browser profiles, screenshots, reports, and executables are also excluded.

## Run the web player

Requires Python 3.9 or newer and Navidrome listening on `127.0.0.1:4533`.

```sh
git clone https://github.com/snowsire/arieth.git
cd arieth
python setup-web.py
python phone-server.py
```

Open `http://127.0.0.1:9180/` and sign in using your Navidrome account. Setup downloads the pinned official build on the first run. Rerunning setup regenerates the theme settings and reapplies the overlays without duplicating scripts. Use `python setup-web.py --download` to reinstall the official assets and then reapply the customization.

The proxy listens only on loopback, disables directory listings, preserves range requests for streaming, and omits API query strings from logs. It does not embed a username or password. Logs are written to `phone-server.log`. Keep the PC running while listening from another device.

For access from a phone, configure an existing private tunnel such as Tailscale Serve to forward to `http://127.0.0.1:9180`. The repository does not configure a public endpoint. Home-screen installation and browser capabilities depend on your browser and whether your tunnel provides HTTPS; offline playback is not supplied by this customization.

On Windows, an elevated PowerShell can optionally run `./install-phone-task.ps1` to register the startup task. The script resolves Python and the checkout path on the target PC; it does not contain a machine-specific installation path.

## Customize

- `snow-music.css`, `crimson.css`, `polygon-atmosphere.css`, and `live-lyrics.css` form the current web theme, in that order.
- `polygon-atmosphere.py` regenerates the geometric SVG backgrounds without external assets.
- `prepare-phone-settings.py` defines web defaults and a versioned, one-time presentation migration. Existing authentication and unrelated preferences are preserved.
- `web/mobile-polish.*`, `web/artist-backdrop.*`, and `web/album-art.*` extend the official web UI without editing its compiled bundles. Album art remains the fallback when no artist photo is available.
- `dark-glass.css` retains the alternative glass theme. Desktop Feishin can use the CSS through its supported custom stylesheet setting; this repository does not replace the desktop executable.

Run `python setup-web.py` after changes to theme files. The current settings migration is `crimson-5`; increase the revision when changing migration behavior so existing browsers receive it once. Keep native Feishin lyric timestamps and word cues intact. Line-only lyrics remain line-synchronized.

## Verify

```sh
python -m unittest discover -s tests -v
node --test tests/*.test.cjs
```

The checks use a fake local music server and isolated browser storage. They cover proxy framing, methods, range headers, failures, log privacy, setup idempotence, checksum rejection, fresh-browser defaults, and preservation of saved preferences. No live library credentials are needed. GitHub Actions runs these checks and JavaScript syntax validation.

Feishin is by jeffvli and contributors. The customization is distributed under [GPL-3.0](LICENSE), with upstream attribution retained. Original sources and build instructions are available in the linked Feishin release tree.
