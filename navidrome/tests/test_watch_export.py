import importlib.util
from pathlib import Path
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


if __name__ == '__main__':
    unittest.main()
