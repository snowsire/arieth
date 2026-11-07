"""Save server playlist snapshots, native rules and ordered local M3U8 exports."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import runpy
import sqlite3


SOURCE=Path(__file__).resolve().parent
ROOT=Path(os.environ.get('NAVIDROME_DATA_DIR',SOURCE/'local')).expanduser().resolve()
MUSIC=Path(os.environ.get('NAVIDROME_MUSIC_DIR',ROOT/'music')).expanduser().resolve()


def main():
    api=runpy.run_path(str(SOURCE/'playlist-library-audit.py'))['api']
    listed=api('getPlaylists').get('playlists',{}).get('playlist',[])
    backup=ROOT/'playlist-backups'/('saved-playlists-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    backup.mkdir(parents=True);exports=backup/'M3U8';exports.mkdir()
    db=sqlite3.connect((ROOT/'data/navidrome.db').as_uri()+'?mode=ro',uri=True)
    paths=dict(db.execute('SELECT id,path FROM media_file'));db.close()
    library=MUSIC
    snapshots=[];manifest=[]
    for item in listed:
        playlist=api('getPlaylist',id=item['id'])['playlist']
        entries=playlist.get('entry',[])
        filename=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',playlist['name']).rstrip(' .')+' - '+playlist['id']+'.m3u8'
        lines=['#EXTM3U','#PLAYLIST:'+playlist['name'].replace('\r',' ').replace('\n',' ')];songs=[]
        for song in entries:
            if song['id'] not in paths:raise RuntimeError('Missing file mapping: '+playlist['name'])
            path=(library/paths[song['id']]).resolve()
            if not path.is_relative_to(library) or not path.is_file():raise RuntimeError('Unavailable source file: '+playlist['name'])
            label=(song.get('artist','')+' - '+song['title']).replace('\r',' ').replace('\n',' ')
            lines+=['#EXTINF:'+str(song.get('duration',-1))+','+label,str(path)]
            songs.append({k:song.get(k) for k in ['id','title','artist','album','duration','suffix','albumId','artistId']}|{'local_path':str(path)})
        target=exports/filename;target.write_text('\n'.join(lines)+'\n',encoding='utf-8')
        assert sum(line.startswith('#EXTINF:') for line in target.read_text(encoding='utf-8').splitlines())==len(entries)
        safe={k:playlist.get(k) for k in ['id','name','comment','owner','public','songCount','duration','created','changed']}
        safe['songs']=songs;snapshots.append(safe)
        manifest.append({'id':playlist['id'],'name':playlist['name'],'tracks':len(entries),'m3u8':'M3U8/'+filename})
    (backup/'playlists.json').write_text(json.dumps(snapshots,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    helpers=runpy.run_path(str(SOURCE/'smart-playlists.py'))
    credentials=json.loads((ROOT/'credentials.json').read_text(encoding='utf-8-sig'))
    native=helpers['NativeAPI'](os.environ.get('NAVIDROME_URL','http://127.0.0.1:4533').rstrip('/'),credentials)
    rules=[]
    for playlist in listed:
        current=native('GET','playlist/'+playlist['id'])
        rules.append({key:current.get(key) for key in ['id','name','comment','ownerId','public','rules']})
    (backup/'native-rules.json').write_text(json.dumps(rules,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    signature_ids={p['id'] for p in snapshots if (p.get('comment') or '').startswith('Arieth signature sets')}
    receipt={'saved_at':datetime.now().astimezone().isoformat(),'server':'Navidrome','playlist_count':len(listed),
             'signature_playlists':len(signature_ids),'track_entries':sum(len(p['songs']) for p in snapshots),
             'playlists':manifest,'backup_directory':str(backup),'credentials_included':False}
    (backup/'manifest.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (backup/'README.txt').write_text('Saved Navidrome playlists\n\nPlaylists remain saved on the Navidrome server.\nM3U8 contains local-player copies with the exact saved track order and absolute paths into the configured music folder.\nplaylists.json records ordered tracks and metadata.\nnative-rules.json preserves smart-playlist rules.\nmanifest.json lists every export.\n\nThe backup contains playlists, not copies of audio or credentials.\nKeep these files private: they include local paths and listening selections.\n',encoding='utf-8')
    (ROOT/'saved-playlists-latest.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:receipt[k] for k in ['playlist_count','signature_playlists','track_entries','backup_directory','credentials_included']},ensure_ascii=True),flush=True)


if __name__=='__main__':main()
