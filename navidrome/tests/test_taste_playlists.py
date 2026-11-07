"""Personal playlist checks use synthetic music and an in-memory server."""
import collections
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch


SOURCE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('taste_playlists',SOURCE/'build-taste-playlists.py')
taste=importlib.util.module_from_spec(spec)
spec.loader.exec_module(taste)


class TastePlaylistTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/'data').mkdir()
        (self.root/'song.flac').write_bytes(b'fLaC'+b'\0'*100001)
        roster=sorted({artist for values in taste.ROSTERS.values() for artist in values.split('|')})
        songs=[];plays=collections.defaultdict(int);affinity=collections.defaultdict(int)
        for artist in roster:
            affinity[taste.norm(artist)]=100
            for i in range(12):
                song={'id':taste.norm(artist)+'-'+str(i),'artist':artist,'albumArtist':artist,
                      'title':'Song '+str(i),'album':'Album '+str(i//3),'albumId':taste.norm(artist)+'-album-'+str(i//3),
                      'suffix':'flac','duration':200,'bitDepth':16,'artists':[{'name':artist}]}
                songs.append(song)
                if i<3:plays[(taste.norm(artist),taste.title_key(song['title']))]=50-i
        self.songs=songs
        (self.root/'playlist-library-inventory.json').write_text(json.dumps(songs),encoding='utf-8')
        db=sqlite3.connect(self.root/'data/navidrome.db')
        db.execute('CREATE TABLE media_file (id TEXT,path TEXT,missing INTEGER)')
        db.executemany('INSERT INTO media_file VALUES (?,?,0)',[(s['id'],'song.flac') for s in songs])
        db.commit();db.close()
        for name in ['ROOT','MUSIC']:
            p=patch.object(taste,name,self.root);p.start();self.addCleanup(p.stop)
        p=patch.object(taste,'history',return_value=(plays,collections.defaultdict(int),set(),affinity))
        p.start();self.addCleanup(p.stop)

    def test_variety_and_unique_tracks_across_all_six_playlists(self):
        plan=taste.build();inventory={s['id']:s for s in self.songs};keys=[]
        self.assertEqual(len(plan),6)
        for playlist in plan:
            self.assertEqual(len(playlist['songs']),35)
            songs=[inventory[s['id']] for s in playlist['songs']]
            artists=[taste.primary(s) for s in songs]
            self.assertLessEqual(max(collections.Counter(artists).values()),3)
            self.assertLessEqual(max(collections.Counter((taste.primary(s),s['albumId']) for s in songs).values()),2)
            for i,artist in enumerate(artists):self.assertNotIn(artist,artists[max(0,i-2):i])
            keys.extend((taste.primary(s),taste.title_key(s['title'])) for s in songs)
        self.assertEqual(len(set(keys)),210)
        self.assertEqual(plan,taste.build(),'The same inputs must produce the same selections')

    def test_corrupt_audio_never_enters_a_plan(self):
        (self.root/'song.flac').write_bytes(b'broken')
        with self.assertRaisesRegex(ValueError,'Not enough varied, playable tracks'):
            taste.build()
        self.assertFalse((self.root/'personal-playlist-plan.json').exists())

    def test_library_path_cannot_escape_music_folder(self):
        db=sqlite3.connect(self.root/'data/navidrome.db')
        db.execute("UPDATE media_file SET path='../outside.flac'");db.commit();db.close()
        with self.assertRaisesRegex(ValueError,'Not enough varied, playable tracks'):
            taste.build()

    def test_title_matching_preserves_recording_versions(self):
        self.assertEqual(taste.title_key('Song (feat. Guest)'),taste.title_key('Song'))
        self.assertEqual(taste.title_key('Song (2011 Remastered)'),taste.title_key('Song'))
        self.assertNotEqual(taste.title_key('Song (Live)'),taste.title_key('Song'))
        self.assertNotEqual(taste.title_key('Song (Club Remix)'),taste.title_key('Song'))

    def fake_server(self):
        stored={'original':{'id':'original','name':'My editable playlist','entry':[{'id':'keep'}],'public':False}}
        calls=[]
        def api(endpoint,client=None,**params):
            calls.append((endpoint,client,params))
            if endpoint=='getPlaylists':return {'playlists':{'playlist':list(stored.values())}}
            if endpoint=='getPlaylist':return {'playlist':stored[params['id']]}
            if endpoint=='createPlaylist':
                identifier=str(len(stored));value={'id':identifier,'name':params['name'],'entry':[{'id':i} for i in params['songId']],'public':False}
                stored[identifier]=value;return {'playlist':value}
            if endpoint=='updatePlaylist':
                if 'public' in params:params['public']=params['public']=='true'
                stored[params.pop('playlistId')].update(params);return {}
            self.fail('Unexpected API endpoint: '+endpoint)
        return api,stored,calls

    def test_creation_is_private_verified_and_repeatable_without_overwrites(self):
        plan=taste.build();api,stored,calls=self.fake_server()
        with patch.object(taste.runpy,'run_path',return_value={'api':api}),contextlib.redirect_stdout(io.StringIO()):
            taste.publish(plan);taste.publish(plan)
        self.assertEqual(len(stored),7)
        self.assertEqual(stored['original']['entry'],[{'id':'keep'}])
        self.assertTrue(all(not p['public'] for p in stored.values()))
        self.assertEqual(sum(endpoint=='createPlaylist' for endpoint,_,_ in calls),6)
        for client in ['Feishin','Symfonium']:
            self.assertEqual(sum(endpoint=='getPlaylist' and value==client for endpoint,value,_ in calls),12)

    def test_existing_unrelated_playlist_is_never_overwritten(self):
        plan=taste.build();api,stored,calls=self.fake_server()
        stored['collision']={'id':'collision','name':plan[0]['name'],'comment':'Mine','entry':[{'id':'keep'}],'public':False}
        with patch.object(taste.runpy,'run_path',return_value={'api':api}),self.assertRaisesRegex(ValueError,'refusing to overwrite'):
            taste.publish(plan)
        self.assertFalse(any(endpoint in ['createPlaylist','updatePlaylist'] for endpoint,_,_ in calls))


if __name__=='__main__':unittest.main()
