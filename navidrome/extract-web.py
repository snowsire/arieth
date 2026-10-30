"""Extract the official Feishin web files from its public OCI image.

Only regular files under usr/share/nginx/html are copied; archive paths are
validated before writing. No container runtime or third-party modules needed.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent
DEST = (ROOT / 'web').resolve()
REPOSITORY = 'jeffvli/feishin'
REGISTRY = 'https://ghcr.io/v2/' + REPOSITORY
PREFIX = PurePosixPath('usr/share/nginx/html')


def request(url, token=None):
    headers = {'User-Agent': 'FeishinLocalSetup/1.0'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    headers['Accept'] = 'application/vnd.oci.image.manifest.v1+json,application/vnd.docker.distribution.manifest.v2+json'
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60)


def verified_bytes(url, digest, token):
    with request(url, token) as response:
        content = response.read()
    if digest != 'sha256:' + hashlib.sha256(content).hexdigest():
        raise ValueError('OCI object digest mismatch')
    return content


def extract_layer(layer, token):
    # The temporary archive is closed and deleted before this function returns.
    with tempfile.TemporaryFile(dir=DEST) as archive:
        hasher = hashlib.sha256()
        with request(REGISTRY + '/blobs/' + layer['digest'], token) as response:
            while True:
                data = response.read(1024 * 1024)
                if not data:
                    break
                hasher.update(data)
                archive.write(data)
        if layer['digest'] != 'sha256:' + hasher.hexdigest():
            raise ValueError('Application layer SHA-256 mismatch')
        archive.seek(0)
        count = 0
        with tarfile.open(fileobj=archive, mode='r:*') as container:
            for member in container:
                if not member.isfile():
                    continue
                name = PurePosixPath(member.name)
                if name.is_absolute() or '..' in name.parts or '\\' in member.name:
                    continue
                try:
                    relative = name.relative_to(PREFIX)
                except ValueError:
                    continue
                if not relative.parts or any(part in ('', '.', '..') or ':' in part for part in relative.parts):
                    continue
                target = (DEST / Path(*relative.parts)).resolve()
                if DEST not in target.parents:
                    raise ValueError('Archive target escaped web directory')
                if target.is_symlink():
                    raise ValueError('Refusing to overwrite a symbolic link')
                target.parent.mkdir(parents=True, exist_ok=True)
                source = container.extractfile(member)
                if source is None:
                    continue
                with source, target.open('wb') as output:
                    while True:
                        data = source.read(1024 * 1024)
                        if not data:
                            break
                        output.write(data)
                count += 1
        return count


def main():
    if DEST.parent != ROOT.resolve():
        raise ValueError('Web destination must remain directly inside the Feishin workspace')
    index = json.loads((ROOT / 'web-manifest.json').read_text(encoding='utf-8-sig'))
    descriptor = next(m for m in index['manifests'] if m.get('platform') == {'architecture': 'amd64', 'os': 'linux'})
    token_url = 'https://ghcr.io/token?' + urllib.parse.urlencode({'service': 'ghcr.io', 'scope': 'repository:' + REPOSITORY + ':pull'})
    with request(token_url) as response:
        token = json.load(response)['token']
    manifest = json.loads(verified_bytes(REGISTRY + '/manifests/' + descriptor['digest'], descriptor['digest'], token))
    config = json.loads(verified_bytes(REGISTRY + '/blobs/' + manifest['config']['digest'], manifest['config']['digest'], token))
    history = [h for h in config.get('history', []) if not h.get('empty_layer')]
    layers = manifest['layers']
    if '--inspect' in sys.argv:
        for i, layer in enumerate(layers):
            print(json.dumps({'index': i, 'bytes': layer['size'], 'digest': layer['digest'], 'command': history[i].get('created_by', '') if i < len(history) else ''}))
        return
    DEST.mkdir(parents=True, exist_ok=True)
    selected = [layer for i, layer in enumerate(layers) if i < len(history) and '/usr/share/nginx/html' in history[i].get('created_by', '')]
    if not selected:
        raise ValueError('No application layer found in OCI image history')
    total = 0
    for layer in selected:
        total += extract_layer(layer, token)
    index_html = DEST / 'index.html'
    if not index_html.is_file():
        raise ValueError('The extracted application has no index.html')
    print(json.dumps({'extractedFiles': total, 'entryHtml': str(index_html), 'manifestDigest': descriptor['digest'], 'applicationLayers': [l['digest'] for l in selected]}))


if __name__ == '__main__':
    main()
