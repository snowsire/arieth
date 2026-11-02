# Install Arieth on the work laptop

Use the existing home Navidrome server and the same music account. The seven server playlists, favorites, and Daily Mix follow that account; the laptop only needs a player and the theme. There is no music import or database migration on the laptop.

## Connect to the home server

Connect through your existing private VPN/tunnel, then open the home Navidrome address in a browser and sign in. Use an address reachable from the laptop, such as your home PC's private VPN hostname and Navidrome port `4533`. `127.0.0.1:4533` on the laptop refers to the laptop itself.

Keep the home PC and Navidrome running. Use the Navidrome server address for the native Feishin app, and the separate Arieth web-player address for the browser player. If a VPN is needed on a managed laptop, use your workplace's approved connection method. These instructions do not expose a public server or change the work network.

## Install the Windows desktop player

1. Install [Feishin 1.17.0 from the official release](https://github.com/jeffvli/feishin/releases/tag/v1.17.0), choosing the Windows build matching the laptop's architecture. This is the version Arieth targets. Start it once.
2. Add a server of type **Navidrome**, enter the reachable home server URL, and sign in with your existing account. Check that an album plays before adding the theme. Refresh Playlists: you should see the five Rock/Emo/Dance mixes, **shot yourself in the foot again**, and **Your Daily Mix**.
3. Install [Python 3.9 or newer](https://www.python.org/downloads/windows/) and [Git for Windows](https://git-scm.com/downloads/win) if needed. In PowerShell:

   ```powershell
   git clone https://github.com/snowsire/arieth.git
   cd arieth\navidrome
   py -3 setup-desktop.py --install-css
   ```

   If you already cloned it, run `git pull --ff-only` inside that checkout, then run the setup command. The helper uses this laptop's `%APPDATA%\feishin` profile. It backs up a different existing stylesheet before installing `custom.css`, and writes the three importable presets under `local\desktop`. No credentials or saved server settings are copied.

4. In Feishin **Settings > Advanced > Styles**, enable **Custom CSS**. The crimson glass theme, patterned genre pills, compact lyrics, and visualizer stage should appear. If necessary, exit Feishin fully and reopen it.
5. In **Settings > General > Home configuration**, turn off **Newly added releases** and **Recently released**. Put Playlists and Genres first, followed by Recently played, Random, and Most played. Desktop preferences are per device.
6. In lyric settings, use a line lead of **650 ms** and enable following. The stylesheet supplies the tighter fullscreen lyric layout; keep any personal synchronization offset you need.

## Add the three visualizer presets

Start a song and open the expanded player, then its **Visualizer** panel. Open the visualizer's gear button and select **AudioMotion Analyzer**. The player must have visualizer/Web Audio support enabled in Playback settings. For native MPV playback, Feishin may ask for system-audio capture permission; its normal consent flow is required. Selecting the web playback backend is another supported route, with different playback capabilities from MPV.

Import each configuration through the existing UI:

| Configuration file in `local\desktop` | Save as preset | Appearance |
| --- | --- | --- |
| `arieth-neon-orbit.json` | Neon Orbit | Rotating radial spectrum, glowing aurora colors and trailing peaks |
| `arieth-afterglow.json` | Crimson Afterglow | Layered stereo waves with a soft reflection |
| `arieth-night-drive.json` | Night Drive | Mirrored stereo bars with crimson/cyan color |

From the `navidrome` directory, copy a configuration in PowerShell:

```powershell
Get-Content -Raw .\local\desktop\arieth-neon-orbit.json | Set-Clipboard
```

Click **Paste Configuration**, paste the JSON into its text area, and click **Apply Configuration**. Then choose **Save as Preset** and enter its name. Repeat for the other two files, and select **Neon Orbit** as your starting preset. Import each once: Feishin's paste action can append gradients again if repeated. Avoid pasting `visualizer-presets.json` itself; it is the source recipe, not an individual configuration.

Use the expand button for the full visualizer stage. The three presets analyze the playing audio and cap drawing at 60 FPS; actual frame rate depends on hardware. Music volume and output remain controlled by Feishin's playback settings.

## Use the browser player instead

If the home PC already serves Arieth through a private HTTPS tunnel, open that Arieth address from the laptop and sign in. No local Python server is needed. The web player installs the three presets and theme automatically the first time the updated settings load. Browser installation as an app depends on the browser.

To host Arieth on a PC that also runs Navidrome locally:

```powershell
cd arieth\navidrome
py -3 setup-web.py
py -3 phone-server.py
```

Open `http://127.0.0.1:9180/`. Setup downloads and verifies the pinned official web build. The proxy is bound to loopback and its backend is fixed to `127.0.0.1:4533`, so starting it on the work laptop alone will not connect it to your home server. Host it at home and access that existing player through your private tunnel. See [the web setup guide](FEISHIN.md#run-the-web-player).

## Update, troubleshoot, or undo

- Update the desktop theme with `git pull --ff-only`, then `py -3 setup-desktop.py --install-css`. Reimport a preset only when you want to replace its saved configuration. For the web host, run `py -3 setup-web.py` after pulling, then reload the browser.
- If login works only at home, verify the VPN/tunnel and the server URL. A laptop cannot reach the home PC using the laptop's loopback address.
- If the visualizer is empty, start playback, confirm Web Audio/visualizer support is enabled, and check Feishin's system-audio capture consent when using MPV. Check the gear menu is set to AudioMotion Analyzer. No microphone is needed for the web playback backend.
- If old imported playlists still appear, refresh Feishin's playlist view. Navidrome already has M3U automatic import disabled and only the seven curated playlists remain; do not run playlist creation scripts just to set up a second player.
- To undo the theme, disable Custom CSS. To restore a previous stylesheet, exit Feishin and copy the timestamped `custom.css.*.bak` over `%APPDATA%\feishin\custom.css`. Delete Arieth presets through the visualizer settings if desired. Keep account credentials on each device; do not commit or copy browser profiles into this repository.
