import importlib.util
import hashlib
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('watch_export', ROOT / 'export-watch-playlist.py')
WATCH_EXPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WATCH_EXPORT)


class WatchExportTests(unittest.TestCase):
    def test_safe_filename_replaces_windows_path_characters(self):
        self.assertEqual(WATCH_EXPORT.safe_filename('Run/After: Dark?.mp3'), 'Run_After_ Dark_.mp3')
        self.assertEqual(WATCH_EXPORT.safe_filename(' . '), 'playlist')

    def test_playlist_files_preserve_order_and_repeated_entries(self):
        songs = [
            {'artist': 'Artist One', 'title': 'First', 'duration': 180},
            {'artist': 'Artist Two', 'title': 'Second', 'duration': 200},
            {'artist': 'Artist One', 'title': 'First', 'duration': 180},
        ]
        plain, extended = WATCH_EXPORT.playlist_files(
            'Run Tonight', songs, ['01 - First.mp3', '02 - Second.mp3', '01 - First.mp3'])
        self.assertEqual(plain.splitlines(), ['01 - First.mp3', '02 - Second.mp3', '01 - First.mp3'])
        self.assertEqual(extended.splitlines(), [
            '#EXTM3U', '#PLAYLIST:Run Tonight',
            '#EXTINF:180,Artist One - First', '01 - First.mp3',
            '#EXTINF:200,Artist Two - Second', '02 - Second.mp3',
            '#EXTINF:180,Artist One - First', '01 - First.mp3',
        ])

    def test_playlist_metadata_cannot_inject_extra_m3u_lines(self):
        songs = [{'artist': 'Artist\n#EXTINF:1,Injected', 'title': 'Song\rName', 'duration': 12}]
        _, extended = WATCH_EXPORT.playlist_files('Safe\nName', songs, ['01 - Song.mp3'])
        self.assertEqual(extended.splitlines(), [
            '#EXTM3U', '#PLAYLIST:Safe Name', '#EXTINF:12,Artist #EXTINF:1,Injected - Song Name',
            '01 - Song.mp3',
        ])

    def test_extend_copies_only_tracks_still_at_their_manifest_position(self):
        songs = [
            {'id': 'keep', 'artist': 'Artist', 'title': 'Keep'},
            {'id': 'moved', 'artist': 'Artist', 'title': 'Moved'},
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / 'old'
            staging = root / 'new'
            destination.mkdir()
            staging.mkdir()
            files = {
                '0001 - Artist - Keep.mp3': b'keep',
                '0003 - Artist - Moved.mp3': b'moved',
                '0002 - Artist - Removed.mp3': b'removed',
            }
            for name, content in files.items():
                (destination / name).write_bytes(content)
            existing = {'files': [
                {'id': 'keep', 'file': '0001 - Artist - Keep.mp3',
                 'sha256': hashlib.sha256(files['0001 - Artist - Keep.mp3']).hexdigest()},
                {'id': 'removed', 'file': '0002 - Artist - Removed.mp3',
                 'sha256': hashlib.sha256(files['0002 - Artist - Removed.mp3']).hexdigest()},
                {'id': 'moved', 'file': '0003 - Artist - Moved.mp3',
                 'sha256': hashlib.sha256(files['0003 - Artist - Moved.mp3']).hexdigest()},
            ]}
            WATCH_EXPORT.copy_reusable_export(existing, destination, staging, songs)
            self.assertEqual([path.name for path in staging.iterdir()],
                             ['0001 - Artist - Keep.mp3'])

    def test_extend_rejects_malformed_or_duplicate_manifest_records(self):
        songs = [{'id': 'one', 'artist': 'Artist', 'title': 'One'}]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root.joinpath('old').mkdir()
            root.joinpath('new').mkdir()
            with self.assertRaisesRegex(ValueError, 'valid file list'):
                WATCH_EXPORT.copy_reusable_export({}, root / 'old', root / 'new', songs)
            duplicate = {'files': [
                {'id': 'one', 'file': 'a.mp3', 'sha256': 'a'},
                {'id': 'one', 'file': 'b.mp3', 'sha256': 'b'},
            ]}
            with self.assertRaisesRegex(ValueError, 'duplicate track ID'):
                WATCH_EXPORT.copy_reusable_export(duplicate, root / 'old', root / 'new', songs)

    def test_resume_and_extend_modes_are_mutually_exclusive(self):
        with self.assertRaisesRegex(ValueError, 'cannot be used together'):
            WATCH_EXPORT.export_playlist('Playlist', '.', resume_dir='staging',
                                         extend_existing=True)


if __name__ == '__main__':
    unittest.main()

