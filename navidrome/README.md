# Navidrome

Navidrome owns the music library and server playlists. Feishin and Symfonium connect to the same server account to access them. Feishin's theme and phone-player sources remain at the repository root.

## Tools

- `playlist-library-audit.py` reads the library through the OpenSubsonic API and writes a FLAC inventory and a summary. It does not change the server.
- `create-flac-mixes.py` builds a local preview of five curated mixes from that inventory. `--create` creates the server playlists and verifies their track lists. A repeat run reuses matching playlists and refuses to overwrite an unrelated or changed playlist.

The mixes are Rock - Classics & Anthems, Rock - Alternative & Grunge, Emo & Pop Punk - Sing It Loud, Emo - Post-Hardcore Nights, and Dance - After Dark. Each contains 40 FLAC tracks, interleaving artists, with no duplicate tracks across the five mixes. The scripts require the selected tracks to exist in your collection before publishing.

## Local configuration

Requires Python 3.9 or newer. Set `NAVIDROME_DATA_DIR` to a local folder containing `credentials.json`, with `username` and `password` fields. The same folder receives the inventory, preview, creation report, and playlist snapshots. You can point this variable at an existing installation folder; no live files need to move.

The default data folder is `navidrome/local/`, which is ignored by Git. Create it before adding credentials if using that default. Keep credentials, reports, databases, logs, and music outside version control. `NAVIDROME_URL` defaults to `http://127.0.0.1:4533`; set it explicitly if your server has a different address or base path.

Run from the Arieth repository root in PowerShell:

```powershell
$env:NAVIDROME_DATA_DIR = 'C:\path\to\your\navidrome-data'
python navidrome/playlist-library-audit.py
python navidrome/create-flac-mixes.py
# Review flac-playlist-plan.json in the data folder, then publish:
python navidrome/create-flac-mixes.py --create
```

The playlists are private to the configured account and stored on the server, rather than in one player's local library. Use that same account in Feishin and Symfonium. Refresh Feishin's Playlists view and sync the Navidrome provider in Symfonium if their lists are cached. The scripts check the shared API using both client identifiers; this does not operate or verify the actual phone app.

Automatic M3U imports are disabled in the current local setup. These tools create playlists directly through the server API and do not modify that setting, the database, or music files. The existing installation, credentials, and already-created playlists stay in place.
