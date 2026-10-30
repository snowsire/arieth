"""Install Arieth's overlays on the checksum-verified Feishin 1.17.0 web build."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import runpy

ROOT = Path(__file__).resolve().parent


def customize(web):
    entry = web / 'index.html'
    html = entry.read_text(encoding='utf-8')
    html = re.sub(r'<title>.*?</title>', '<title>Arieth - Snow Music</title>', html)
    html = html.replace('width=device-width, initial-scale=1"',
                        'width=device-width, initial-scale=1, viewport-fit=cover"')
    # Remove prior overlay tags so rerunning setup cannot duplicate observers.
    html = re.sub(r'\s*<(?:link|script)\b[^>]*(?:artist-backdrop|album-art|mobile-polish)\.(?:css|js)[^>]*>(?:</script>)?', '', html)
    tags = ''.join('\n        <link rel="stylesheet" href="{0}.css?v=5" />'
                   '\n        <script defer src="{0}.js?v=5"></script>'.format(name)
                   for name in ('artist-backdrop', 'album-art', 'mobile-polish'))
    if '</head>' not in html:
        raise ValueError('Feishin entry point has no head element')
    html = re.sub(r'\s*</head>', tags + '\n    </head>', html)
    html = html.replace('./assets/manifest.webmanifest', 'manifest.webmanifest')
    manifest_path = web / 'assets' / 'manifest.webmanifest'
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        manifest.update(name='Arieth - Snow Music', short_name='Arieth', scope='/',
                        start_url='/', background_color='#09080b', theme_color='#ed3048')
        for item in manifest.get('icons', []) + manifest.get('screenshots', []):
            item['src'] = './assets/' + item['src'].removeprefix('./')
        (web / 'manifest.webmanifest').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    entry.write_text(html, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true', help='reinstall the pinned official web assets')
    args = parser.parse_args()
    web = ROOT / 'web'
    if args.download or not (web / 'index.html').is_file():
        spec = importlib.util.spec_from_file_location('extract_web', ROOT / 'extract-web.py')
        extractor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(extractor)
        extractor.main()
    customize(web)
    runpy.run_path(str(ROOT / 'prepare-phone-settings.py'), run_name='__main__')
    print('Arieth web player ready. Run python phone-server.py to serve it.')


if __name__ == '__main__':
    main()
