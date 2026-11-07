"""Offline curation, publishing and backup checks with synthetic local music."""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch


SOURCE=Path(__file__).resolve().parents[1]


def load(filename,name):
    spec=importlib.util.spec_from_file_location(name,SOURCE/filename)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


signature=load('create-signature-playlists.py','signature_tests')
second=load('create-more-signature-playlists.py','second_signature_tests')
third=load('create-signature-volume-three.py','third_signature_tests')
backup=load('save-playlists.py','backup_tests')


class SignaturePlaylistTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.music=self.root/'music';self.music.mkdir()
        (self.root/'data').mkdir()
        (self.music/'alpha.flac').write_bytes(b'fLaC'+b'\0'*100001)
        # FLAC files may legitimately carry a leading ID3 tag.
        (self.music/'beta.flac').write_bytes(b'ID3\x03\0\0\0\0\0\x04testfLaC'+b'\0'*100001)
        (self.root/'outside.flac').write_bytes(b'fLaC'+b'\0'*100001)
        self.songs=[self.song('a','Artist','Alpha','Studio'),self.song('live','Artist','Alpha (Live)','Live'),
                    self.song('outside','Artist','Alpha','Studio',32),self.song('b','Other','Beta','Studio')]
        self.write_inventory()
        db=sqlite3.connect(self.root/'data/navidrome.db')
        db.execute('CREATE TABLE media_file (id TEXT,path TEXT,missing INTEGER)')
        db.executemany('INSERT INTO media_file VALUES (?,?,0)',[('a','alpha.flac'),('live','alpha.flac'),
                                                              ('outside','../outside.flac'),('b','beta.flac')])
        db.commit();db.close()
        self.plan_sets=[('A listening set','A fixed sequence.','Other | Beta\nArtist | Alpha')]
        for module in [signature,backup]:
            for name,value in [('ROOT',self.root),('MUSIC',self.music)]:
                p=patch.object(module,name,value);p.start();self.addCleanup(p.stop)
        for name,value in [('SETS',self.plan_sets),('EXCLUDED_RECORDINGS',set())]:
            p=patch.object(signature,name,value);p.start();self.addCleanup(p.stop)
        self.output=contextlib.redirect_stdout(io.StringIO());self.output.__enter__()
        self.addCleanup(self.output.__exit__,None,None,None)

    def song(self,identifier,artist,title,album,bits=16):
        return {'id':identifier,'artist':artist,'albumArtist':artist,'title':title,'album':album,
                'duration':200,'suffix':'flac','bitDepth':bits,'artists':[{'name':artist}]}

    def write_inventory(self):
        (self.root/'playlist-library-inventory.json').write_text(json.dumps(self.songs),encoding='utf-8')

    def test_all_sixteen_definitions_are_distinct_without_private_plan_files(self):
        first=load('create-signature-playlists.py','unpatched_signature_definitions')
        groups=[first.recording_keys(first.SETS),second.builder.recording_keys(second.builder.SETS),
                third.builder.recording_keys(third.builder.SETS)]
        names=[name for module in [first,second.builder,third.builder] for name,_,_ in module.SETS]
        self.assertEqual(len(names),len(set(names)))
        self.assertEqual(len(names),16)
        self.assertEqual(len(set.union(*groups)),315)
        self.assertEqual(sum(map(len,groups)),315)
        self.assertEqual(len(groups[0]),102)
        self.assertTrue(second.builder.EXCLUDED_RECORDINGS<=third.builder.EXCLUDED_RECORDINGS)
        self.assertFalse(groups[1]&second.builder.EXCLUDED_RECORDINGS)
        self.assertFalse(groups[2]&third.builder.EXCLUDED_RECORDINGS)
        self.assertEqual(len(groups[1]),96)
        self.assertEqual(len(groups[2]),117)

    def test_order_and_id3_flac_survive_while_live_and_outside_candidates_do_not(self):
        plan=signature.build()
        self.assertEqual([s['id'] for s in plan[0]['songs']],['b','a'])
        self.assertEqual(plan,json.loads((self.root/signature.PLAN_NAME).read_text(encoding='utf-8')))

    def test_corrupt_recording_fails_before_a_plan_is_written(self):
        (self.music/'beta.flac').write_bytes(b'broken')
        with self.assertRaises(SystemExit) as error:signature.build()
        self.assertEqual(error.exception.code,2)
        self.assertFalse((self.root/signature.PLAN_NAME).exists())

    def test_excluded_recording_cannot_reappear_as_a_new_edition(self):
        with patch.object(signature,'EXCLUDED_RECORDINGS',{('artist','alpha')}),self.assertRaisesRegex(ValueError,'Repeated recording'):
            signature.build()
        self.assertFalse((self.root/signature.PLAN_NAME).exists())

    def fake_api(self):
        stored={'old':{'id':'old','name':'Existing manual playlist','entry':[],'public':False,'comment':None}}
        calls=[]
        def api(endpoint,client=None,**params):
            calls.append((endpoint,client,copy.deepcopy(params)))
            if endpoint=='getPlaylists':return {'playlists':{'playlist':copy.deepcopy(list(stored.values()))}}
            if endpoint=='getPlaylist':return {'playlist':copy.deepcopy(stored[params['id']])}
            if endpoint=='createPlaylist':
                identifier=str(len(stored));p={'id':identifier,'name':params['name'],
                    'entry':[copy.deepcopy(next(s for s in self.songs if s['id']==i)) for i in params['songId']],
                    'public':False,'comment':'','songCount':len(params['songId'])}
                stored[identifier]=p;return {'playlist':copy.deepcopy(p)}
            if endpoint=='updatePlaylist':
                identifier=params.pop('playlistId')
                if 'public' in params:params['public']=params['public']=='true'
                stored[identifier].update(params);return {}
            self.fail('Unexpected mutation: '+endpoint)
        return api,stored,calls

    def test_publish_reuses_same_order_without_touching_existing_playlists(self):
        plan=signature.build();api,stored,calls=self.fake_api()
        with patch.object(signature.runpy,'run_path',return_value={'api':api}):
            signature.publish(plan);signature.publish(plan)
        self.assertEqual(len(stored),2)
        self.assertEqual([s['id'] for s in stored['1']['entry']],['b','a'])
        self.assertFalse(stored['1']['public'])
        self.assertEqual(stored['old']['entry'],[])
        self.assertEqual(sum(c[0]=='createPlaylist' for c in calls),1)
        self.assertEqual(sum(c[0]=='getPlaylist' and c[1]=='Symfonium' for c in calls),2)

    def test_all_name_collisions_are_checked_before_any_playlist_creation(self):
        plan=signature.build();plan.append({**plan[0],'name':'Existing manual playlist'})
        api,_,calls=self.fake_api()
        with patch.object(signature.runpy,'run_path',return_value={'api':api}),self.assertRaisesRegex(ValueError,'refusing to overwrite'):
            signature.publish(plan)
        self.assertFalse(any(c[0] in ['createPlaylist','updatePlaylist'] for c in calls))

    def test_failed_creation_retains_the_created_playlist_id_for_recovery(self):
        plan=signature.build();api,stored,_=self.fake_api()
        def fail_update(endpoint,**params):
            if endpoint=='updatePlaylist':raise TimeoutError('network unavailable')
            return api(endpoint,**params)
        with patch.object(signature.runpy,'run_path',return_value={'api':fail_update}),self.assertRaises(TimeoutError):
            signature.publish(plan)
        journal=json.loads((self.root/signature.RESULT_NAME).read_text(encoding='utf-8'))
        self.assertEqual(journal['playlists'][0]['id'],'1')
        self.assertIn('1',stored)

    def test_backup_exports_order_and_native_rules_without_credentials_or_audio(self):
        api,stored,calls=self.fake_api()
        stored['set']={'id':'set','name':'An example: set','comment':signature.MARKER,'public':False,'songCount':2,
                       'entry':[self.songs[-1],self.songs[0]]}
        (self.root/'credentials.json').write_text('{"username":"fixture","password":"never-export-this"}',encoding='utf-8')
        native_rules={'all':[{'is':{'filetype':'flac'}}],'refreshDelay':'1d'}
        def native(method,path):return {'id':path.split('/')[-1],'name':'Example','rules':native_rules,'public':False}
        def helpers(path):
            return {'api':api} if Path(path).name=='playlist-library-audit.py' else {'NativeAPI':lambda *_:native}
        with patch.object(backup.runpy,'run_path',side_effect=helpers):backup.main()
        receipt=json.loads((self.root/'saved-playlists-latest.json').read_text(encoding='utf-8'))
        self.assertEqual(receipt['signature_playlists'],1)
        self.assertEqual(receipt['playlist_count'],2)
        folder=Path(receipt['backup_directory'])
        entry=next(p for p in receipt['playlists'] if p['id']=='set')
        text=(folder/entry['m3u8']).read_text(encoding='utf-8')
        self.assertLess(text.index(str(self.music/'beta.flac')),text.index(str(self.music/'alpha.flac')))
        rules=json.loads((folder/'native-rules.json').read_text(encoding='utf-8'))
        self.assertTrue(all(p['rules']==native_rules for p in rules))
        for file in folder.rglob('*'):
            if file.is_file():self.assertNotIn('never-export-this',file.read_text(encoding='utf-8'))
        self.assertFalse(list(folder.rglob('*.flac')))
        self.assertTrue(all(c[0] in ['getPlaylist','getPlaylists'] for c in calls))

    def test_backup_refuses_outside_library_paths_without_claiming_success(self):
        api,stored,_=self.fake_api()
        stored['bad']={'id':'bad','name':'Bad mapping','entry':[self.songs[2]]}
        with patch.object(backup.runpy,'run_path',return_value={'api':api}),self.assertRaisesRegex(RuntimeError,'Unavailable source file'):
            backup.main()
        self.assertFalse((self.root/'saved-playlists-latest.json').exists())


if __name__=='__main__':unittest.main()
