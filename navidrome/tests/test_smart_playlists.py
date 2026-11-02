"""Rules, cooldown boundaries, and recovery without a live music server."""
import contextlib
import copy
from datetime import datetime, timezone, timedelta
import importlib.util
import io
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('smart_playlists', Path(__file__).resolve().parents[1] / 'smart-playlists.py')
smart = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smart)


class SmartPlaylistTests(unittest.TestCase):
    def test_rules_keep_daily_cache_and_feedback_without_smart_dependencies(self):
        genre = smart.make_rules(['Taking Back Sunday', 'Taking Back Sunday'])
        self.assertEqual(genre['limit'], 40)
        self.assertEqual(genre['refreshDelay'], '1d')
        self.assertEqual(genre['sort'], 'random')
        self.assertIn({'notInTheLast': {'lastplayed': 3}}, genre['all'])
        self.assertIn({'any': [{'is': {'rating': 0}}, {'gt': {'rating': 2}}]}, genre['all'])
        self.assertEqual(len(genre['all'][-1]['any']), 2)
        daily = smart.make_rules(['Taking Back Sunday'], 'manual-id')
        self.assertEqual(daily['sort'], '-loved,-rating,random')
        references = [r['inPlaylist']['id'] for r in daily['all'][-1]['any'] if 'inPlaylist' in r]
        self.assertEqual(references, ['manual-id'])
        with self.assertRaises(ValueError):
            smart.make_rules([])

    def test_cooldown_and_quality_keep_unplayed_tracks_and_handle_server_precision(self):
        now = datetime(2026, 11, 2, 12, tzinfo=timezone.utc)
        song = {'suffix': 'flac', 'duration': 200}
        self.assertTrue(smart.eligible(song, now))
        self.assertFalse(smart.eligible({**song, 'played': (now - timedelta(days=1)).isoformat()}, now))
        self.assertTrue(smart.eligible({**song, 'played': '2026-10-29T22:56:44.6359635+13:00'}, now))
        self.assertFalse(smart.eligible({**song, 'played': '2026-11-02T10:00:00Z'}, now))
        self.assertFalse(smart.eligible({**song, 'userRating': 1}, now))
        self.assertTrue(smart.eligible({**song, 'userRating': 0}, now))
        self.assertFalse(smart.eligible({**song, 'suffix': 'mp3'}, now))
        self.assertFalse(smart.eligible({**song, 'isMissing': True}, now))
        self.assertFalse(smart.eligible({**song, 'duration': 20}, now))

    def fixtures(self):
        entries = [{'id': str(i), 'artist': 'An artist', 'suffix': 'flac', 'duration': 200} for i in range(40)]
        native = {'id': 'genre', 'name': 'Rock', 'comment': 'original', 'rules': None, 'ownerId': 'me', 'public': False}
        plan = {'native': native, 'playlist': {'entry': entries},
                'rules': smart.make_rules(['An artist']), 'comment': 'upgraded'}
        return entries, plan

    def test_failed_verification_restores_rules_and_original_fixed_track_order(self):
        entries, plan = self.fixtures()
        stored = copy.deepcopy(plan['native'])
        writes, replacements = [], []
        def native(method, path, body=None):
            if method == 'PUT':
                writes.append(copy.deepcopy(body))
                stored.update(body)
            return copy.deepcopy(stored)
        def api(endpoint, **params):
            if endpoint == 'createPlaylist':
                replacements.append(params)
                return {}
            return {'playlist': {'entry': entries[:2]}}
        with self.assertRaisesRegex(RuntimeError, 'restored'):
            smart.apply_changes([plan], native, api)
        self.assertIsNone(stored['rules'])
        self.assertEqual(stored['comment'], 'original')
        self.assertEqual(replacements, [{'playlistId': 'genre', 'songId': [s['id'] for s in entries]}])

    def test_verified_update_preserves_identity_and_is_idempotent(self):
        entries, plan = self.fixtures()
        stored = copy.deepcopy(plan['native'])
        writes = []
        def native(method, path, body=None):
            if method == 'PUT':
                writes.append(body)
                stored.update(body)
            return copy.deepcopy(stored)
        def api(endpoint, **params):
            return {'playlist': {'entry': entries}}
        with contextlib.redirect_stdout(io.StringIO()):
            smart.apply_changes([plan], native, api)
            plan['native'] = copy.deepcopy(stored)
            smart.apply_changes([plan], native, api)
        self.assertEqual(len(writes), 1)
        self.assertEqual(stored['name'], 'Rock')
        self.assertFalse(stored['public'])

    def test_concurrent_playlist_edit_is_not_overwritten(self):
        _, plan = self.fixtures()
        writes = []
        def native(method, path, body=None):
            if method == 'PUT':
                writes.append(body)
            return {**plan['native'], 'comment': 'edited while previewing'}
        with self.assertRaises(RuntimeError):
            smart.apply_changes([plan], native, lambda *a, **k: None)
        self.assertEqual(writes, [])
