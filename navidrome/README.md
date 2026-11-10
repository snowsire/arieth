# Navidrome

This directory contains the complete music project: Navidrome playlist tools, Feishin themes and web overlays, the phone-player proxy, setup scripts, and tests. Navidrome owns the music library and server playlists; Feishin and Symfonium are clients.

See [FEISHIN.md](FEISHIN.md) for the player setup, theme customization, and verification commands. All paths in that guide are relative to this directory after `cd navidrome`.

## Tools

- `playlist-library-audit.py` reads the library through the OpenSubsonic API and writes a FLAC inventory and a summary. It does not change the server.
- `create-flac-mixes.py` builds a local preview of five curated mixes from that inventory. `--create` creates the server playlists and verifies their track lists. A repeat run reuses matching playlists and refuses to overwrite an unrelated or changed playlist.
- `smart-playlists.py` previews an upgrade of the five existing genre mixes and Your Daily Mix. `--apply` backs them up, updates their native Navidrome rules in place, and verifies the same track selection through Feishin and Symfonium API clients. It creates no additional playlists and leaves **shot yourself in the foot again** editable.

The mixes are Rock - Classics & Anthems, Rock - Alternative & Grunge, Emo & Pop Punk - Sing It Loud, Emo - Post-Hardcore Nights, and Dance - After Dark. Each contains 40 FLAC tracks, interleaving artists, with no duplicate tracks across the five mixes. The scripts require the selected tracks to exist in your collection before publishing.

That describes the initial hand-picked seed lists. The current server uses the smarter rules below; once upgraded, the original `create-flac-mixes.py --create` command intentionally refuses to overwrite these changed lists.

## Smarter playlists

The five genre mixes now choose 40 FLAC tracks from the wider catalogs of their original artist rosters. They exclude missing files, tracks shorter than 90 seconds or longer than 15 minutes, songs played in the last three days, and tracks/artists you rated 1–2 stars. Unrated music remains eligible. Selection is random within each pool, so deeper cuts can join the original anthems.

Native rules select unique library entries; different editions of the same recording can still appear, and random selection does not enforce a fixed per-artist quota.

Your Daily Mix uses those artist rosters directly, your editable playlist, loved tracks/albums/artists, highly rated songs, and artists you have played. It prefers loved tracks first, then higher track ratings, with random ties. Its tracks remain 2–10 minutes long and have the same three-day cooldown and low-rating exclusions. No favorites are required to get a full mix.

Each mix stays stable for 24 hours after evaluation, then refreshes the next time a client accesses it. This is a rolling interval, not a midnight job. Navidrome evaluates the rules; the laptop does not need a scheduled task. Play counts and ratings belong to the playlist owner's account, so use that same account in all clients. Favorite a song to promote it in Daily Mix; rate unwanted tracks or artists 1–2 stars to exclude them at the next refresh. The current selection can remain cached until the daily interval expires. [Navidrome documents the refresh behavior and supported rules](https://www.navidrome.org/docs/usage/features/smart-playlists/).

Smart playlists are edited through their rules in Feishin, rather than adding/reordering individual tracks. **shot yourself in the foot again** remains a regular playlist for manual additions. Playlist IDs, names, ownership, and visibility are preserved, and M3U auto-import stays disabled.

From `arieth/navidrome`, using the same data-folder configuration as the other playlist tools:

```powershell
$env:NAVIDROME_DATA_DIR = 'C:\path\to\your\navidrome-data'
python smart-playlists.py
# Writes smart-playlist-plan.json locally; inspect before applying.
python smart-playlists.py --apply
```

The tool requires the existing seven playlists and recognizes only the Arieth-managed mix comments. It reads the current library and stores native rule and track snapshots in `playlist-backups/smart-upgrade-<timestamp>/before.json` before writing. If an update or verification fails, it restores the attempted playlists' old rules and fixed track lists; any restore failure names the affected playlist. Unchanged rules are not reapplied, so repeating the command does not force a new shuffle. The local report is `smart-playlist-result.json`. Keep these files and credentials outside Git. This setup uses Navidrome's native playlist API and never writes directly to its database or music files.

## Personal listening playlists

`build-taste-playlists.py` creates six fixed, editable playlists from your
available FLAC tracks and local Spotify listening exports:

- **On Repeat - Your Favorites**: listening favorites, with recent favorites weighted higher.
- **Heavy Hearts, Loud Guitars**: melodic heavy music and post-hardcore.
- **Windows Down**: pop punk and emo.
- **After Hours - Bass & Trance**: electronic music, bass and trance.
- **Bars for the Drive**: hip-hop.
- **The Other Tracks**: underplayed album tracks from familiar artists.

Each list contains 35 tracks. Selections share no repeated artist/title pair
across the six lists, allow at most three tracks per artist and two per album
within a list, and leave two other artists between repeat appearances. The
builder checks local FLAC headers before selecting files. It excludes live,
acoustic and demo recordings; electronic remixes remain eligible. Listening
counts describe the supplied export, rather than a promise of complete history.

Run this on the music-server machine using Python 3.9+. The data folder must
contain `credentials.json`, the local Navidrome database at
`data/navidrome.db`, and the inventory written by `playlist-library-audit.py`.
The export folder needs `top_tracks.csv`, `heavy_rotation.csv`,
`recent_favourites.csv`, `saved_tracks.csv` and `top_artists.csv` from the local
Spotify analysis. Artist/track columns are `Artist` and `Track`; listening
counts use `Plays_30s_plus`. These inputs remain private and outside Git.

From `arieth/navidrome` in PowerShell:

```powershell
$env:NAVIDROME_DATA_DIR = 'C:\path\to\your\navidrome-data'
$env:SPOTIFY_EXPORT_DIR = 'C:\path\to\your\spotify-analysis'
$env:NAVIDROME_MUSIC_DIR = 'D:\path\to\your\music'
python playlist-library-audit.py
python build-taste-playlists.py
# Inspect personal-playlist-plan.json in the data folder, then create:
python build-taste-playlists.py --create
```

The default folders are `local/`, `local/spotify/` and `local/music/` beside the
script. Preview writes a local plan only. Creation makes private server
playlists and verifies the selected tracks using Feishin and Symfonium API
client identifiers. Actual app playback is a separate device check. Existing
matching lists are reused; different content or an unrelated list with the
same name causes a refusal instead of an overwrite. The operation snapshots
existing playlist metadata under `playlist-backups/personal-<timestamp>/` and
writes a result journal, including any partial creation, to
`personal-playlist-result.json`. The music files and existing playlists are
unchanged. Refresh Feishin's Playlists view or sync Symfonium to see the lists.

## Signature listening collections and backups

The signature scripts contain 16 hand-sequenced playlists across three
collections. Their 315 artist/title selections do not repeat across the
collections. These are fixed running orders with chosen opening and closing
tracks, separate from the daily smart mixes and listening-history selections.

| Script | Playlists |
| --- | --- |
| `create-signature-playlists.py` | Teeth & Heart; Velvet & Venom; 2005 Never Ended; Neon Pressure; When the Noise Stops |
| `create-more-signature-playlists.py` | No Brakes; Back Seat Choir; First Light, Last Dance; Concrete & Conscience; Smoke & Signals |
| `create-signature-volume-three.py` | Feedback Season; Letters You Never Sent; Nightfall on the Long Way Home; Beautiful Machines; Borrowed Voices; Sunburn & Bad Ideas |

Use the same `NAVIDROME_DATA_DIR` and `NAVIDROME_MUSIC_DIR` as the personal
playlist builder. The scripts need the current local library inventory and
Navidrome database at `NAVIDROME_DATA_DIR/data/navidrome.db`. They do not require
Spotify exports or previous generated plans. The default data folder is
`local/` beside the scripts, and the default music folder is `local/music/`.
`NAVIDROME_URL` selects the existing music server, defaulting to loopback port
4533. Run on the machine that can read that database and music folder.

From `arieth/navidrome`, after setting those environment variables:

```powershell
python playlist-library-audit.py
python create-signature-playlists.py
python create-more-signature-playlists.py
python create-signature-volume-three.py
# After reviewing the plans in the data folder:
python create-signature-playlists.py --create
python create-more-signature-playlists.py --create
python create-signature-volume-three.py --create
python save-playlists.py
```

Preview checks the selected local files, including FLAC with a leading ID3
tag, and writes the ordered plan. Missing or invalid selections stop creation;
the scripts do not silently substitute recordings. Live, demo, acoustic and
remix versions are excluded. Each volume checks the earlier collections'
source definitions to prevent repeats without reading private plan files.

Creation makes private server playlists, checks every name before writing,
and verifies track order through the Feishin and Symfonium API client
identifiers. An unchanged existing set is reused. A playlist with different
content or comment is refused instead of overwritten. Existing playlist
snapshots and a creation journal are saved locally. If creation stops partway,
the journal retains the IDs already created so they can be inspected before
retrying. Server verification does not operate the phone app; import the
server playlists in Symfonium or refresh Feishin's playlist view.

`save-playlists.py` reads all server playlists and their native smart rules.
It writes a dated directory under `playlist-backups/` containing
`playlists.json`, `native-rules.json`, `manifest.json` and ordered UTF-8 M3U8
exports. `saved-playlists-latest.json` points to the most recent completed
backup. It does not change the server playlists or copy audio. Exports contain
local file paths and server IDs, so retain the music at those paths and keep
the backup private. Credentials, generated inventories, plans, journals,
databases and exports remain outside Git.

## Local configuration
## Garmin watch playlists

`export-watch-playlist.py` exports one existing Navidrome playlist as a folder
of numbered MP3 tracks plus ordered `.m3u` and `.m3u8` files. It reads the live
playlist through the Navidrome API and streams the tracks from the server, so
it does not depend on database paths matching the current music-folder layout.
Repeated playlist entries reuse one MP3 while their positions remain repeated
in the playlist. Each MP3 is written as 320 kbps, 44.1 kHz stereo with ID3v2.3
tags, then checked for codec, duration, artist/title tags and a complete decode.
An `export.json` manifest records the file hashes and playlist order. A
progress JSON sits beside the bundle while it is being built.

Requirements are a reachable Navidrome server, `credentials.json` in
`NAVIDROME_DATA_DIR`, and `ffmpeg` plus `ffprobe` on `PATH` (or paths supplied
with `--ffmpeg` and `--ffprobe`). `NAVIDROME_URL` selects the server and
defaults to `http://127.0.0.1:4533`. Keep credentials and output outside Git.

From `arieth/navidrome` in PowerShell, with the same data-folder configuration
used by the playlist tools:

```powershell
$env:NAVIDROME_DATA_DIR = 'C:\path\to\your\navidrome-data'
$env:NAVIDROME_WATCH_EXPORT_DIR = 'D:\NativeAI\watch-exports'
python export-watch-playlist.py "2005 Never Ended"
```

The named bundle contains the MP3 files, both playlist formats and manifest.
The default output is ignored `navidrome/local/watch-exports`; set
`NAVIDROME_WATCH_EXPORT_DIR` or pass `--output-dir` to place it elsewhere. The
exporter refuses to overwrite an existing bundle. An interrupted export keeps
its hidden staging folder and progress report for inspection; it does not
publish a partial bundle as complete.

`transfer-watch-playlist.ps1` copies one completed bundle to a Garmin's
`Primary/Music/<playlist>` folder over USB/MTP. It checks the source hashes,
available watch storage, playlist order, and refuses to overwrite an existing
same-named watch folder. It reads the copied folder back and verifies every
MP3 SHA-256 plus the `.m3u` ordering before writing a transfer receipt beside
the bundle. Keep the watch connected and awake until the receipt is reported.
Run it with:

```powershell
.\transfer-watch-playlist.ps1 -BundlePath 'D:\NativeAI\watch-exports\2005 Never Ended' -WatchName 'fenix 6X Sapphire'
```

The transfer script never deletes or replaces watch files. Generated MP3s,
M3U files, manifests, progress reports and transfer receipts are local user
data and must not be committed.

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
