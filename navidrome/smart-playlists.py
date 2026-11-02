"""Preview or apply daily, history-aware rules to the six existing Arieth mixes."""
import argparse
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import re
import runpy
import urllib.request

SOURCE = Path(__file__).resolve().parent
MARKER = 'Arieth smart mix v2.'
DAILY = 'Your Daily Mix'
MANUAL = 'shot yourself in the foot again'


def quality_rules(minimum=90, maximum=900):
    return [
        {'is': {'filetype': 'flac'}}, {'is': {'missing': False}},
        {'inTheRange': {'duration': [minimum, maximum]}},
        {'notInTheLast': {'lastplayed': 3}},
        {'any': [{'is': {'rating': 0}}, {'gt': {'rating': 2}}]},
        {'any': [{'is': {'artistrating': 0}}, {'gt': {'artistrating': 2}}]},
    ]


def artist_rules(names):
    return [{'is': {field: name}} for name in sorted(set(names), key=str.casefold)
            for field in ('artist', 'albumartist')]


def make_rules(names, manual_id=None):
    sources = artist_rules(names)
    if not sources:
        raise ValueError('An artist roster is required')
    if manual_id:
        sources += [
            {'inPlaylist': {'id': manual_id}}, {'is': {'loved': True}},
            {'is': {'albumloved': True}}, {'is': {'artistloved': True}},
            {'gt': {'rating': 3}}, {'gt': {'artistplaycount': 0}},
        ]
    return {
        'all': quality_rules(120, 600) + [{'any': sources}] if manual_id
               else quality_rules() + [{'any': sources}],
        'sort': '-loved,-rating,random' if manual_id else 'random',
        'limit': 40, 'refreshDelay': '1d',
    }


def eligible(song, now):
    if song.get('suffix', '').lower() != 'flac' or song.get('isMissing', False):
        return False
    if not 90 <= song.get('duration', 0) <= 900:
        return False
    if song.get('userRating', 0) in (1, 2):
        return False
    played = song.get('played')
    if played:
        # OpenSubsonic dates are ISO 8601; accept both UTC and explicit offsets.
        stamp = datetime.fromisoformat(re.sub(r'(\.\d{6})\d+', r'\1', played).replace('Z', '+00:00'))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        if stamp >= now - timedelta(days=3):
            return False
    return True


class NativeAPI:
    def __init__(self, server, credentials):
        self.server = server
        request = urllib.request.Request(server + '/auth/login',
            data=json.dumps({key: credentials[key] for key in ('username', 'password')}).encode(),
            headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(request, timeout=20) as response:
            self.token = json.load(response)['token']

    def __call__(self, method, path, body=None):
        request = urllib.request.Request(self.server + '/api/' + path, method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={'Content-Type': 'application/json',
                     'x-nd-authorization': 'Bearer ' + self.token})
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)


def apply_changes(plans, native, api):
    attempted = []
    try:
        for plan in plans:
            old = plan['native']
            if old.get('rules') == plan['rules'] and old.get('comment') == plan['comment']:
                continue
            current = native('GET', 'playlist/' + old['id'])
            if any(current.get(key) != old.get(key) for key in ('name', 'comment', 'rules', 'ownerId', 'public')):
                raise ValueError('Playlist changed since preview: ' + old['name'])
            attempted.append(plan)
            native('PUT', 'playlist/' + old['id'],
                   {'rules': plan['rules'], 'comment': plan['comment']})
            first = api('getPlaylist', client='Feishin', id=old['id'])['playlist']
            second = api('getPlaylist', client='Symfonium', id=old['id'])['playlist']
            ids = [song['id'] for song in first.get('entry', [])]
            if len(ids) != 40 or len(set(ids)) != 40:
                raise ValueError('Expected forty unique tracks: ' + old['name'])
            if ids != [song['id'] for song in second.get('entry', [])]:
                raise ValueError('Selection differs between clients')
            now = datetime.now(timezone.utc)
            if not all(eligible(song, now) for song in first['entry']):
                raise ValueError('A selected track failed quality/cooldown checks')
            stored = native('GET', 'playlist/' + old['id'])
            if stored.get('rules') != plan['rules']:
                raise ValueError('Server did not retain the rules')
            for key in ('name', 'ownerId', 'public'):
                if stored.get(key) != old.get(key):
                    raise ValueError('Playlist identity or visibility changed')
            print(json.dumps({'verified': old['name'], 'tracks': len(ids),
                              'artists': len({s['artist'] for s in first['entry']})}), flush=True)
    except Exception:
        failures = []
        for plan in reversed(attempted):
            old = plan['native']
            try:
                native('PUT', 'playlist/' + old['id'],
                       {'rules': old.get('rules'), 'comment': old.get('comment', '')})
                if not old.get('rules'):
                    api('createPlaylist', playlistId=old['id'],
                        songId=[s['id'] for s in plan['playlist'].get('entry', [])])
            except Exception:
                failures.append(old['name'])
        if failures:
            raise RuntimeError('Upgrade failed; restore required from backup for: ' + ', '.join(failures)) from None
        raise RuntimeError('Upgrade failed; previous rules and fixed track lists restored. See the backup.') from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='back up and update the existing server playlists')
    args = parser.parse_args()
    data = Path(os.environ.get('NAVIDROME_DATA_DIR', SOURCE / 'local')).expanduser().resolve()
    data.mkdir(parents=True, exist_ok=True)
    helpers = runpy.run_path(str(SOURCE / 'playlist-library-audit.py'))
    api = helpers['api']
    mixes = runpy.run_path(str(SOURCE / 'create-flac-mixes.py'))
    listed = api('getPlaylists').get('playlists', {}).get('playlist', [])
    expected_names = list(mixes['MIXES']) + [DAILY, MANUAL]
    targets = {}
    for name in expected_names:
        matches = [p for p in listed if p['name'].casefold() == name.casefold()]
        if len(matches) != 1:
            raise ValueError('Expected exactly one existing playlist named ' + name)
        targets[name] = api('getPlaylist', id=matches[0]['id'])['playlist']
    songs, offset = [], 0
    while True:
        page = api('search3', query='', songCount=500, songOffset=offset,
                   artistCount=0, albumCount=0).get('searchResult3', {}).get('song', [])
        songs.extend(page)
        if len(page) < 500:
            break
        offset += len(page)
    if len({s['id'] for s in songs}) != len(songs):
        raise ValueError('Inventory contains duplicate IDs')
    credentials = json.loads((data / 'credentials.json').read_text(encoding='utf-8-sig'))
    native = NativeAPI(helpers['SERVER'], credentials)
    plans, all_artists = [], set()
    now = datetime.now(timezone.utc)
    for name, source in mixes['MIXES'].items():
        wanted = {mixes['normalize'](line.split('|')[0].strip()) for line in source.strip().splitlines()}
        def match(song):
            return bool(wanted & mixes['artist_names'](song))
        matched = [song for song in songs if match(song) and song.get('suffix', '').lower() == 'flac']
        pool = [song for song in matched if eligible(song, now)]
        if len(pool) < 40:
            raise ValueError('Fewer than forty eligible tracks for ' + name)
        roster = set()
        for song in matched:
            names = [song.get('artist', ''), song.get('albumArtist', '')]
            names += [a['name'] for a in song.get('artists', []) + song.get('albumArtists', [])]
            roster.update(raw for raw in names if raw and wanted & mixes['artist_names']({'artist': raw}))
        all_artists.update(roster)
        old = native('GET', 'playlist/' + targets[name]['id'])
        if not old.get('comment', '').startswith(('Arieth FLAC mix v1,', MARKER)):
            raise ValueError('Refusing to replace an unrelated playlist: ' + name)
        plans.append({'native': old, 'playlist': targets[name], 'rules': make_rules(roster),
            'comment': MARKER + ' Forty FLAC deep cuts from the original artist roster. '
                       'Avoids tracks played in the last three days and 1-2 star tracks/artists. '
                       'Random selection stays stable for 24 hours, then refreshes on access.',
            'eligiblePool': len(pool), 'artists': sorted(roster, key=str.casefold)})
    old = native('GET', 'playlist/' + targets[DAILY]['id'])
    if not old.get('comment', '').startswith(('Arieth daily mix v1.', MARKER)):
        raise ValueError('Refusing to replace an unrelated Daily Mix')
    plans.append({'native': old, 'playlist': targets[DAILY],
        'rules': make_rules(all_artists, targets[MANUAL]['id']),
        'comment': MARKER + ' Forty FLAC tracks from the original mix artists, your editable '
                   'playlist, favorites, and artists you play. Loved and highly rated tracks first; '
                   'random ties, three-day track cooldown, 1-2 star tracks/artists excluded. '
                   'Stable for 24 hours, then refreshes on access.'})
    preview = [{'id': p['native']['id'], 'name': p['native']['name'],
                'rules': p['rules'], 'eligiblePool': p.get('eligiblePool')} for p in plans]
    (data / 'smart-playlist-plan.json').write_text(json.dumps(preview, indent=2), encoding='utf-8')
    print(json.dumps({'mode': 'apply' if args.apply else 'preview', 'playlists': [
        {'name': p['native']['name'], 'eligiblePool': p.get('eligiblePool'),
         'rosterSize': len(p.get('artists', []))} for p in plans]}), flush=True)
    if not args.apply:
        return
    stamp = now.strftime('%Y%m%dT%H%M%S%fZ')
    backup = data / 'playlist-backups' / ('smart-upgrade-' + stamp)
    backup.mkdir(parents=True)
    (backup / 'before.json').write_text(json.dumps({'plans': plans,
        'manual': targets[MANUAL], 'listed': listed}, indent=2), encoding='utf-8')
    print('Backup: ' + str(backup), flush=True)
    apply_changes(plans, native, api)
    after = api('getPlaylists').get('playlists', {}).get('playlist', [])
    if {p['id']: p['name'] for p in listed} != {p['id']: p['name'] for p in after}:
        raise RuntimeError('Playlist identities changed during the upgrade')
    manual_after = api('getPlaylist', id=targets[MANUAL]['id'])['playlist']
    if [s['id'] for s in manual_after.get('entry', [])] != [s['id'] for s in targets[MANUAL].get('entry', [])]:
        raise RuntimeError('The editable playlist changed during the upgrade')
    results = []
    for plan in plans:
        playlist = api('getPlaylist', id=plan['native']['id'])['playlist']
        results.append({'name': playlist['name'], 'id': playlist['id'],
            'tracks': len(playlist.get('entry', [])),
            'artists': len({s['artist'] for s in playlist.get('entry', [])}),
            'refreshDelay': '1d'})
    report = {'upgraded': results, 'manualPlaylistPreserved': True, 'backup': str(backup)}
    (data / 'smart-playlist-result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
