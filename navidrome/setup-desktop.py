"""Build the desktop stylesheet and configurations for Feishin 1.17.0's import UI."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
THEME_FILES = (
    'snow-music.css', 'crimson.css', 'polygon-atmosphere.css',
    'live-lyrics.css', 'home-discovery.css', 'visualizer-stage.css',
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-css', action='store_true',
                        help='back up and install custom.css in the Windows Feishin profile')
    args = parser.parse_args()
    destination = ROOT / 'local' / 'desktop'
    destination.mkdir(parents=True, exist_ok=True)
    css = '\n\n'.join((ROOT / name).read_text(encoding='utf-8') for name in THEME_FILES)
    stylesheet = destination / 'custom.css'
    stylesheet.write_text(css, encoding='utf-8')
    recipe = json.loads((ROOT / 'visualizer-presets.json').read_text(encoding='utf-8'))
    for preset in recipe['presets']:
        value = {**recipe['base'], **preset['value'], 'customGradients': recipe['gradients']}
        (destination / (preset['id'] + '.json')).write_text(
            json.dumps(value, indent=2) + '\n', encoding='utf-8')
    print('Desktop stylesheet and three importable presets: ' + str(destination))
    if args.install_css:
        if os.name != 'nt' or not os.environ.get('APPDATA'):
            parser.error('--install-css requires Windows and APPDATA')
        profile = Path(os.environ['APPDATA']) / 'feishin'
        if not profile.is_dir():
            parser.error('Open Feishin once to create its profile, then run this command again')
        target = profile / 'custom.css'
        if target.exists() and target.read_bytes() != stylesheet.read_bytes():
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            backup = profile / ('custom.css.' + stamp + '.bak')
            shutil.copy2(target, backup)
            print('Previous stylesheet backed up: ' + str(backup))
        shutil.copyfile(stylesheet, target)
        print('Installed: ' + str(target))
        print('Enable Custom CSS in Feishin Settings > Advanced > Styles.')
    print('Import each JSON using visualizer Settings > Paste Configuration, then Save as Preset.')


if __name__ == '__main__':
    main()
