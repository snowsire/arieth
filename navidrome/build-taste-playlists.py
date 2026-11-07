"""Build and optionally create personal playlists from local listening exports."""
import argparse
import collections
import csv
import json
import math
import os
from pathlib import Path
import re
import runpy
import sqlite3
from datetime import datetime, timezone
import unicodedata

SOURCE=Path(__file__).resolve().parent
ROOT=Path(os.environ.get('NAVIDROME_DATA_DIR',SOURCE/'local')).expanduser().resolve()
EXPORTS=Path(os.environ.get('SPOTIFY_EXPORT_DIR',ROOT/'spotify')).expanduser().resolve()
MUSIC=Path(os.environ.get('NAVIDROME_MUSIC_DIR',ROOT/'music')).expanduser().resolve()
MARKER='Arieth personal selections v1.'
ROSTERS={
    'Heavy Hearts, Loud Guitars': '''Linkin Park|I Prevail|A Day To Remember|As Everything Unfolds|Future Palace|Breaking Benjamin|Silverstein|Senses Fail|Saosin|Thrice|Underoath|Funeral For A Friend|Finch|The Used|Story Of The Year|Emarosa|Deftones|Bring Me The Horizon|Bad Omens|Electric Callboy|Escape The Fate|Thursday|Chiodos''',
    'Windows Down': '''Against The Current|Tonight Alive|blink-182|Fall Out Boy|Paramore|Sum 41|Rise Against|Yellowcard|All Time Low|New Found Glory|The Red Jumpsuit Apparatus|Anberlin|Taking Back Sunday|My Chemical Romance|Jimmy Eat World|Motion City Soundtrack|The Starting Line|Relient K|The Offspring|Good Charlotte|Panic! At The Disco|Alkaline Trio|Bayside''',
    'After Hours - Bass & Trance': '''NERO|Skrillex|Pendulum|Chase & Status|Shapeshifter|ODESZA|Flume|Armin van Buuren|Above & Beyond|ATB|Tiesto|deadmau5|Kaskade|Calvin Harris|David Guetta|Daft Punk|The Chemical Brothers|Royksopp|Robin Schulz|The Prodigy|Seven Lions|MSTRKRFT|The Crystal Method|The Chainsmokers''',
    'Bars for the Drive': '''Hilltop Hoods|Kendrick Lamar|G-Eazy|Eminem|Jay-Z|Atmosphere|OutKast|2Pac|Public Enemy|Cypress Hill|Nas|Kanye West|Kid Cudi|Lupe Fiasco|Aesop Rock|Beastie Boys|Ludacris|T.I.|Nelly|Macklemore & Ryan Lewis|NF|Fort Minor|Dr. Dre|Snoop Dogg''',
}
DESCRIPTIONS={
    'On Repeat - Your Favorites':'Favorites matched to your Spotify listening history, with recent favorites weighted higher. A little heavy, a little melodic, a little electronic.',
    'Heavy Hearts, Loud Guitars':'Melodic metalcore and post-hardcore: big choruses, heavier guitars, and a few older favorites between the newer bands.',
    'Windows Down':'Pop punk and emo for a loud drive. Familiar hooks and melodic album tracks, with artists spaced out.',
    'After Hours - Bass & Trance':'Bass, melodic electronic music and trance from your own collection. Remixes are welcome here.',
    'Bars for the Drive':'Hip-hop for a long drive, built around your Hilltop Hoods, Kendrick and G-Eazy listening and nearby favorites.',
    'The Other Tracks':'Album tracks from artists you already listen to, with at most two Spotify plays in the supplied export. These are underplayed in that export, not necessarily new to you.',
}


def norm(value):
    value=unicodedata.normalize('NFKD',value).encode('ascii','ignore').decode().casefold()
    return re.sub('[^a-z0-9]','',value.replace('&','and'))


def title_key(value):
    value=re.sub(r'[\[(](?:feat\.?|ft\.?|featuring|with)\s+[^\])]*[\])]','',value,flags=re.I)
    value=re.sub(r'\s+(?:feat\.?|ft\.?|featuring)\s+.*$','',value,flags=re.I)
    value=re.sub(r'[\[(][^\])]*remaster[^\])]*[\])]|\s*-\s*(?:\d{4}\s+)?remaster(?:ed)?(?:\s+\d{4})?','',value,flags=re.I)
    return norm(value)


def primary(song):return norm(song.get('albumArtist') or next(iter(song.get('albumArtists',[])),{}).get('name') or song['artist'])


def artists(song):
    return {primary(song),norm(song['artist']),*(norm(a['name']) for a in song.get('artists',[])),
            *(norm(a['name']) for a in song.get('albumArtists',[]))}-{''}


def history():
    plays=collections.defaultdict(int);recent=collections.defaultdict(int);saved=set();artist_plays=collections.defaultdict(int)
    for filename in ['top_tracks.csv','heavy_rotation.csv','recent_favourites.csv','saved_tracks.csv','top_artists.csv']:
        with (EXPORTS/filename).open(encoding='utf-8-sig',newline='') as f:
            for row in csv.DictReader(f):
                artist=norm(row['Artist']);count=int(row.get('Plays_30s_plus') or 0)
                if filename=='top_artists.csv':artist_plays[artist]=max(artist_plays[artist],count);continue
                key=(artist,title_key(row['Track']))
                if filename=='recent_favourites.csv':recent[key]=count
                elif filename=='saved_tracks.csv':saved.add(key)
                else:plays[key]=max(plays[key],count)
    return plays,recent,saved,artist_plays


def build():
    songs=json.loads((ROOT/'playlist-library-inventory.json').read_text(encoding='utf-8'))
    plays,recent,saved,artist_plays=history()
    db=sqlite3.connect((ROOT/'data/navidrome.db').as_uri()+'?mode=ro',uri=True)
    paths=dict(db.execute('SELECT id,path FROM media_file WHERE coalesce(missing,0)=0'));db.close()
    tracks=[]
    for song in songs:
        if song.get('suffix','').lower()!='flac' or not 110<=song.get('duration',0)<=540 or song.get('userRating',0) in [1,2] or song['id'] not in paths:continue
        if re.search(r'\b(live|acoustic|demo|instrumental|karaoke|interlude|skit)\b',song['title']+' '+song.get('album',''),re.I):continue
        keys={(a,title_key(song['title'])) for a in artists(song)}
        tracks.append({'song':song,'artist':primary(song),'artists':artists(song),'key':(primary(song),title_key(song['title'])),
                       'plays':max((plays[k] for k in keys),default=0),'recent':max((recent[k] for k in keys),default=0),
                       'saved':bool(keys & saved),'affinity':max((artist_plays[a] for a in artists(song)),default=0)})
    def score(item):
        return 6*math.log1p(item['plays'])+4*math.log1p(item['recent'])+4*item['saved']+math.log1p(item['affinity'])
    def ranking(item):
        s=item['song']
        return (-score(item),bool(re.search(r'\b(remix|edit|version)\b',s['title'],re.I)),-s.get('bitDepth',0),s['id'])
    used=set();plan=[];checked={}
    def playable(item):
        identifier=item['song']['id']
        if identifier not in checked:
            p=(MUSIC/paths[identifier]).resolve()
            try:
                if not p.is_relative_to(MUSIC):
                    checked[identifier]=False
                    return False
                with p.open('rb') as f:checked[identifier]=p.stat().st_size>100000 and f.read(4)==b'fLaC'
            except OSError:checked[identifier]=False
        return checked[identifier]
    def select(name,pool,count=35):
        pool=sorted(pool,key=ranking);chosen=[];artist_counts=collections.Counter();album_counts=collections.Counter()
        while len(chosen)<count:
            item=next((t for t in pool if t['key'] not in used and artist_counts[t['artist']]<3
                       and album_counts[(t['artist'],t['song'].get('albumId',t['song']['album']))]<2
                       and all(t['artist']!=c['artist'] for c in chosen[-2:]) and playable(t)),None)
            if item is None:raise ValueError('Not enough varied, playable tracks for '+name)
            chosen.append(item);used.add(item['key']);artist_counts[item['artist']]+=1
            album_counts[(item['artist'],item['song'].get('albumId',item['song']['album']))]+=1
        entries=[{k:t['song'].get(k) for k in ['id','artist','title','album','duration','bitDepth']} for t in chosen]
        plan.append({'name':name,'comment':MARKER+' '+DESCRIPTIONS[name],
                     'songs':entries,'artist_count':len(artist_counts),'minutes':round(sum(s['duration'] for s in entries)/60)})
    select('On Repeat - Your Favorites',[t for t in tracks if t['plays']>0])
    for name,roster in ROSTERS.items():
        wanted={norm(a) for a in roster.split('|')}
        select(name,[t for t in tracks if t['artists'] & wanted and (name.startswith('After Hours') or not re.search(r'\b(remix|acoustic)\b',t['song']['title'],re.I))])
    familiar={norm(a) for name in ['Heavy Hearts, Loud Guitars','Windows Down'] for a in ROSTERS[name].split('|')}
    select('The Other Tracks',[t for t in tracks if t['artists'] & familiar and t['plays']<=2 and t['recent']==0
                              and t['affinity']>=90 and not re.search(r'\b(remix|acoustic)\b',t['song']['title'],re.I)])
    (ROOT/'personal-playlist-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return plan


def publish(plan):
    api=runpy.run_path(str(SOURCE/'playlist-library-audit.py'))['api']
    before=api('getPlaylists').get('playlists',{}).get('playlist',[])
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup=ROOT/'playlist-backups'/('personal-'+stamp);backup.mkdir(parents=True)
    (backup/'before.json').write_text(json.dumps(before,indent=2)+'\n',encoding='utf-8')
    results=[]
    journal=ROOT/'personal-playlist-result.json'
    for playlist in plan:
        ids=[s['id'] for s in playlist['songs']]
        matches=[p for p in before if p['name'].casefold()==playlist['name'].casefold()]
        if len(matches)>1:raise ValueError('Ambiguous existing playlist: '+playlist['name'])
        if matches:
            current=api('getPlaylist',id=matches[0]['id'])['playlist']
            if not current.get('comment','').startswith(MARKER) or [s['id'] for s in current.get('entry',[])]!=ids:
                raise ValueError('Existing playlist differs; refusing to overwrite: '+playlist['name'])
        else:
            current=api('createPlaylist',name=playlist['name'],songId=ids)['playlist']
            results.append({'id':current['id'],'name':playlist['name'],'status':'created'})
            journal.write_text(json.dumps({'playlists':results,'backup':str(backup)},indent=2),encoding='utf-8')
            api('updatePlaylist',playlistId=current['id'],comment=playlist['comment'],public='false')
        for client in ['Feishin','Symfonium']:
            verified=api('getPlaylist',client=client,id=current['id'])['playlist']
            if [s['id'] for s in verified.get('entry',[])]!=ids or verified.get('public',False):
                raise ValueError('Playlist verification failed: '+playlist['name'])
        result={'id':current['id'],'name':playlist['name'],'tracks':len(ids),'minutes':playlist['minutes'],
                'artists':playlist['artist_count'],'verified':True}
        if results and results[-1]['id']==current['id']:results[-1]=result
        else:results.append(result)
        journal.write_text(json.dumps({'playlists':results,'backup':str(backup)},indent=2)+'\n',encoding='utf-8')
        print(json.dumps(result,ensure_ascii=True),flush=True)
    after=api('getPlaylists').get('playlists',{}).get('playlist',[])
    if not {(p['id'],p['name']) for p in before}<={(p['id'],p['name']) for p in after}:
        raise ValueError('An existing playlist disappeared')
    print('Verified all six playlists through Feishin and Symfonium APIs.',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--create',action='store_true')
    args=parser.parse_args();plan=build()
    if args.create:publish(plan)
    else:
        print(json.dumps([{k:v for k,v in p.items() if k!='songs'}|{'opening_tracks':p['songs'][:6]} for p in plan],ensure_ascii=True,indent=2))
