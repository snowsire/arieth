"""Export one Navidrome playlist as deduplicated Garmin-ready MP3 files."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import secrets
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent
BITRATE = '320k'
SAMPLE_RATE = '44100'
CHANNELS = 2


def safe_filename(value, limit=120):
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', value).strip(' .')
    return value[:limit] or 'playlist'


def playlist_files(name, songs, filenames):
    plain = []
    extended = ['#EXTM3U', '#PLAYLIST:' + name.replace('\r', ' ').replace('\n', ' ')]
    for song, filename in zip(songs, filenames):
        plain.append(filename)
        artist = song['artist'].replace('\r', ' ').replace('\n', ' ')
        title = song['title'].replace('\r', ' ').replace('\n', ' ')
        extended.extend([f"#EXTINF:{int(song.get('duration') or 0)},{artist} - {title}", filename])
    return '\n'.join(plain) + '\n', '\n'.join(extended) + '\n'


def file_hash(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_executable(value, label):
    path = Path(value).expanduser()
    if path.is_file():
        return path.resolve()
    located = shutil.which(value)
    if located:
        return Path(located).resolve()
    raise FileNotFoundError(f'{label} executable was not found: {value}')


def verify_mp3(path, song, ffprobe, ffmpeg):
    result = subprocess.run([
        str(ffprobe), '-v', 'error', '-show_format', '-show_streams',
        '-of', 'json', str(path),
    ], check=True, capture_output=True, text=True, encoding='utf-8')
    probe = json.loads(result.stdout)
    audio = [stream for stream in probe['streams'] if stream['codec_type'] == 'audio']
    tags = {key.lower(): value for key, value in probe['format'].get('tags', {}).items()}
    if (len(audio) != 1 or audio[0].get('codec_name') != 'mp3'
            or audio[0].get('sample_rate') != SAMPLE_RATE
            or audio[0].get('channels') != CHANNELS
            or abs(float(probe['format']['duration']) - int(song.get('duration') or 0)) > 2
            or tags.get('title') != song['title'] or tags.get('artist') != song['artist']):
        raise RuntimeError(f"MP3 verification failed for {song['artist']} - {song['title']}.")
    subprocess.run([
        str(ffmpeg), '-hide_banner', '-loglevel', 'error', '-xerror', '-nostdin',
        '-i', str(path), '-f', 'null', '-',
    ], check=True, capture_output=True)
    return {'bytes': path.stat().st_size, 'sha256': file_hash(path)}


def export_playlist(playlist_name, output_dir, ffmpeg_name='ffmpeg', ffprobe_name='ffprobe'):
    data_dir = Path(os.environ.get('NAVIDROME_DATA_DIR', ROOT / 'local')).expanduser().resolve()
    helper = runpy.run_path(str(ROOT / 'playlist-library-audit.py'))
    api = helper['api']
    server = os.environ.get('NAVIDROME_URL', 'http://127.0.0.1:4533').rstrip('/')
    playlists = [item for item in api('getPlaylists').get('playlists', {}).get('playlist', [])
                 if item.get('name', '').casefold() == playlist_name.casefold()]
    if len(playlists) != 1:
        raise ValueError(f'Expected exactly one playlist named {playlist_name!r}; found {len(playlists)}.')
    playlist = api('getPlaylist', id=playlists[0]['id'])['playlist']
    songs = playlist.get('entry', [])
    if not songs or any(not song.get('id') or not song.get('artist') or not song.get('title') for song in songs):
        raise ValueError('The playlist is empty or has an entry without an ID, artist, or title.')

    unique_songs = {}
    for song in songs:
        unique_songs.setdefault(song['id'], song)
    safe_name = safe_filename(playlist['name'])
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / safe_name
    if destination.exists():
        raise FileExistsError(f'Export already exists; refusing to overwrite: {destination}')

    ffmpeg = resolve_executable(ffmpeg_name, 'FFmpeg')
    ffprobe = resolve_executable(ffprobe_name, 'FFprobe')
    unique_seconds = sum(int(song.get('duration') or 0) for song in unique_songs.values())
    minimum_free = unique_seconds * 40000 + 100 * 1024 * 1024
    if shutil.disk_usage(output_dir).free < minimum_free:
        raise RuntimeError('Not enough free space for the estimated MP3 export and staging files.')

    staging = Path(tempfile.mkdtemp(prefix=f'.{safe_name}-', dir=output_dir))
    progress_path = output_dir / f'{safe_name}-progress.json'
    credentials = json.loads((data_dir / 'credentials.json').read_text(encoding='utf-8-sig'))
    records = []
    progress = {'status': 'exporting', 'playlist': playlist['name'],
                'playlists': 1, 'entries': len(songs), 'unique_tracks': len(unique_songs),
                'completed_tracks': 0, 'format': 'MP3 320 kbps'}

    def write_progress():
        temporary = progress_path.with_suffix(progress_path.suffix + '.tmp')
        temporary.write_text(json.dumps(progress, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        temporary.replace(progress_path)

    write_progress()
    source_tmp = staging / '.source.audio'
    try:
        for number, song in enumerate(unique_songs.values(), 1):
            label = song['artist'] + ' - ' + song['title']
            stem = safe_filename(label, 150)
            filename = f'{number:04d} - {stem}.mp3'
            target = staging / filename
            salt = secrets.token_hex(12)
            signature = hashlib.md5((credentials['password'] + salt).encode()).hexdigest()
            params = dict(u=credentials['username'], s=salt, t=signature, v='1.16.1',
                          c='AriethWatchExport', f='json', id=song['id'])
            url = server + '/rest/stream.view?' + urllib.parse.urlencode(params)
            request = urllib.request.Request(url, headers={'User-Agent': 'AriethWatchExport/1.0'})
            try:
                with urllib.request.urlopen(request, timeout=120) as response, source_tmp.open('wb') as output:
                    if not response.headers.get('Content-Type', '').lower().startswith('audio/'):
                        raise ValueError('Navidrome did not return an audio stream.')
                    shutil.copyfileobj(response, output, length=1024 * 1024)
            except Exception as error:
                raise RuntimeError(f'Could not stream {label} ({type(error).__name__}).') from None
            if source_tmp.stat().st_size < 4096:
                raise ValueError(f'Audio stream was unexpectedly small for {label}.')
            subprocess.run([
                str(ffmpeg), '-hide_banner', '-loglevel', 'error', '-nostdin', '-n',
                '-i', str(source_tmp), '-map', '0:a:0', '-map_metadata', '-1',
                '-c:a', 'libmp3lame', '-b:a', BITRATE, '-ar', SAMPLE_RATE,
                '-ac', str(CHANNELS), '-threads', '2', '-id3v2_version', '3',
                '-metadata', 'title=' + song['title'], '-metadata', 'artist=' + song['artist'],
                '-metadata', 'album=' + playlist['name'],
                '-metadata', 'album_artist=' + song.get('albumArtist', song['artist']),
                '-metadata', f'track={number}/{len(unique_songs)}', '-metadata', 'disc=1/1',
                str(target),
            ], check=True, capture_output=True)
            source_tmp.unlink()
            verified = verify_mp3(target, song, ffprobe, ffmpeg)
            records.append({
                'id': song['id'], 'artist': song['artist'], 'title': song['title'],
                'duration': int(song.get('duration') or 0), 'file': filename,
                'bytes': verified['bytes'], 'sha256': verified['sha256'],
            })
            progress.update({'completed_tracks': number, 'last_completed': label})
            write_progress()
            print(json.dumps({'track': number, 'total': len(unique_songs), 'name': label}), flush=True)

        record_by_id = {record['id']: record for record in records}
        filenames = [record_by_id[song['id']]['file'] for song in songs]
        plain, extended = playlist_files(playlist['name'], songs, filenames)
        (staging / (safe_name + '.m3u')).write_text(plain, encoding='utf-8')
        (staging / (safe_name + '.m3u8')).write_text(extended, encoding='utf-8')
        manifest = {
            'playlist': playlist['name'], 'folder_name': safe_name,
            'playlist_id': playlist['id'],
            'tracks': len(records), 'entries': len(songs),
            'seconds': sum(int(song.get('duration') or 0) for song in songs),
            'bytes': sum(record['bytes'] for record in records),
            'format': 'MP3 320 kbps, 44.1 kHz stereo, ID3v2.3',
            'files': records,
        }
        (staging / 'export.json').write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        staging.rename(destination)
        progress.update({'status': 'complete', 'output': str(destination), 'bytes': manifest['bytes']})
        write_progress()
        print(json.dumps({'status': 'complete', 'output': str(destination),
                          'tracks': len(records), 'entries': len(songs),
                          'seconds': manifest['seconds'], 'bytes': manifest['bytes']}), flush=True)
        return destination
    finally:
        source_tmp.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('playlist', help='Exact Navidrome playlist name')
    parser.add_argument('--output-dir', default=os.environ.get(
        'NAVIDROME_WATCH_EXPORT_DIR', ROOT / 'local' / 'watch-exports'),
        help='Directory that will hold the named export folder')
    parser.add_argument('--ffmpeg', default=os.environ.get('FFMPEG', 'ffmpeg'))
    parser.add_argument('--ffprobe', default=os.environ.get('FFPROBE', 'ffprobe'))
    args = parser.parse_args()
    export_playlist(args.playlist, args.output_dir, args.ffmpeg, args.ffprobe)


if __name__ == '__main__':
    main()
