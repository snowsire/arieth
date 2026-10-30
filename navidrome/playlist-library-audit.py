"""Read-only audit of the music server, with credentials kept out of reports."""
import collections
import hashlib
import json
import os
from pathlib import Path
import secrets
import urllib.parse
import urllib.request

ROOT = Path(os.environ.get('NAVIDROME_DATA_DIR', Path(__file__).resolve().parent / 'local')).expanduser().resolve()
SERVER = os.environ.get('NAVIDROME_URL', 'http://127.0.0.1:4533').rstrip('/')

def api(endpoint, client='AriethPlaylistSetup', **params):
    credentials = json.loads((ROOT/'credentials.json').read_text(encoding='utf-8-sig'))
    salt = secrets.token_hex(12)
    auth = dict(u=credentials['username'], s=salt,
                t=hashlib.md5((credentials['password']+salt).encode()).hexdigest(),
                v='1.16.1', c=client, f='json')
    request = urllib.request.Request(SERVER+'/rest/'+endpoint+'.view',
        data=urllib.parse.urlencode(dict(auth, **params), doseq=True).encode(),
        headers={'Content-Type':'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)['subsonic-response']
    if result.get('status') != 'ok':
        raise RuntimeError(endpoint+': '+result.get('error',{}).get('message','API failed'))
    return result

if __name__ == '__main__':
    songs = []
    offset = 0
    while True:
        page = api('search3', query='', songCount=500, songOffset=offset,
                   artistCount=0, albumCount=0).get('searchResult3',{}).get('song',[])
        songs.extend(page)
        if len(page) < 500:
            break
        offset += len(page)
    assert len({song['id'] for song in songs}) == len(songs), 'Duplicate inventory IDs'
    flac = [song for song in songs if song.get('suffix','').lower() == 'flac']
    (ROOT/'playlist-library-inventory.json').write_text(json.dumps(flac,indent=2),encoding='utf-8')
    artists = collections.Counter(song.get('albumArtist') or song.get('artist') for song in flac)
    genres = collections.Counter(song.get('genre','(untagged)') for song in flac)
    report = dict(totalSongs=len(songs), flacSongs=len(flac), artists=artists.most_common(),
                  genres=genres.most_common(), currentPlaylists=api('getPlaylists').get('playlists',{}).get('playlist',[]))
    (ROOT/'playlist-library-audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
