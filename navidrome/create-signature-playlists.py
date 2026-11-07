"""Hand-sequenced local listening sets. Preview by default; --create publishes."""
import argparse
import collections
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
MARKER='Arieth signature sets v1.'
PLAN_NAME='signature-playlist-plan.json'
RESULT_NAME='signature-playlist-result.json'
BACKUP_PREFIX='signature-'
EXCLUDED_RECORDINGS=set()
SETS=[
('Teeth & Heart',
 'Start fierce, open up the choruses, then earn the release. Modern melodic heavy music with a post-hardcore spine. Play in order.',
 '''Linkin Park | Heavy Is the Crown
I Prevail | Self-Destruction
Bring Me The Horizon | Shadow Moses
Future Palace | The Echoes of Disparity
Electric Callboy | We Got the Moves
A Day To Remember | The Downfall Of Us All
As Everything Unfolds | Slow Down
Breaking Benjamin | The Diary of Jane
Silverstein | Smile in Your Sleep
Thrice | The Artist in the Ambulance
Saosin | You're Not Alone
I Prevail | Hurricane
Bad Omens | Like A Villain
Funeral For A Friend | Roses for the Dead
Finch | What it is to Burn
Linkin Park | The Emptiness Machine
Electric Callboy | Pump It
Underoath | Writing On The Walls
A Day To Remember | Have Faith In Me
Bad Omens | Just Pretend
Bring Me The Horizon | Hospital for Souls'''),
('Velvet & Venom',
 'Bright hooks with teeth: modern melodic rock, pop-punk urgency and a darker middle. The last three tracks are the emotional landing. Play in order.',
 '''Against The Current | weapon
Tonight Alive | Lonely Girl
Paramore | Ignorance
Maggie Lindemann | she knows it
The Veronicas | Untouched
Flyleaf | I'm So Sick
Future Palace | Uncontrolled
As Everything Unfolds | Felt Like Home
Evanescence | Going Under
Lacuna Coil | Our Truth
Against The Current | that won't save us
Tonight Alive | The Ocean
Paramore | Let The Flames Begin
Maggie Lindemann | self sabotage
The Veronicas | Revenge Is Sweeter (Than You Ever Were)
Flyleaf | All Around Me
Future Palace | Dreamstate
Against The Current | lullaby
Evanescence | Lithium
Paramore | All I Wanted'''),
('2005 Never Ended',
 'The scene-night set: instant recognition up front, sharper edges in the middle, then the songs you stay for. A few years either side of 2005. Play in order.',
 '''My Chemical Romance | Thank You For The Venom
Taking Back Sunday | A Decade Under The Influence
Fall Out Boy | Grand Theft Autumn/Where is Your Boy
The Used | The Taste Of Ink
Jimmy Eat World | Sweetness
Yellowcard | Ocean Avenue
blink-182 | Feeling This
Brand New | Sic Transit Gloria... Glory Fades
Senses Fail | Can't Be Saved
Silverstein | My Heroine
Thrice | Stare at the Sun
Anberlin | The Feel Good Drag
Funeral For A Friend | Juneau
Saosin | Seven Years
Taking Back Sunday | MakeDamnSure
Fall Out Boy | Sugar, We're Goin' Down
My Chemical Romance | Helena
The Used | I Caught Fire
Jimmy Eat World | A Praise Chorus
Brand New | The Quiet Things That No One Ever Knows
Yellowcard | Only One
My Chemical Romance | Famous Last Words'''),
('Neon Pressure',
 'A night out in four movements: melodic glow, bass pressure, a drum-and-bass run, then a long way home. Full tracks, not a beatmatched DJ mix. Play in order.',
 '''Flume | Never Be Like You
NERO | Innocence
Skrillex | Summit
Flume | Say It
NERO | Guilt
Chase & Status | Eastern Jam
Skrillex | Bangarang
Pendulum | Propane Nightmares
Chase & Status | Pieces
Shapeshifter | Dutchies
Pendulum | Witchcraft
Shapeshifter | The Touch
The Chemical Brothers | Hey Boy Hey Girl
Pendulum | Watercolour
NERO | Doomsday
The Chemical Brothers | Star Guitar
deadmau5 | Ghosts 'n' Stuff
Kaskade | 4am
deadmau5 | I Remember
Flume | Tiny Cities
deadmau5 | Strobe'''),
('When the Noise Stops',
 'Low light, tension and room to breathe. Dreamlike guitars turn inward, the middle opens out, and Transatlanticism closes the door slowly. Play in order.',
 '''Deftones | Digital Bath
Placebo | Sleeping With Ghosts
Incubus | Echo
Deftones | Sextape
Nine Inch Nails | Right Where It Belongs
Radiohead | Let Down
Brand New | The Boy Who Blocked His Own Shot
Audioslave | I Am The Highway
The Smashing Pumpkins | 1979
Linkin Park | Leave Out All the Rest
Breaking Benjamin | Rain
Jimmy Eat World | 23
Thrice | The Whaler
Death Cab For Cutie | What Sarah Said
Brand New | Play Crack The Sky
Nine Inch Nails | Hurt
Radiohead | How To Disappear Completely
Death Cab For Cutie | Transatlanticism'''),
]


def recording_keys(sets):
    helper=runpy.run_path(str(SOURCE/'build-taste-playlists.py'))
    keys=set()
    for _,_,listing in sets:
        for line in listing.splitlines():
            artist,title=(part.strip() for part in line.split('|',1))
            keys.add((helper['norm'](artist),helper['title_key'](title)))
    return keys


def build():
    helper=runpy.run_path(str(SOURCE/'build-taste-playlists.py'))
    songs=json.loads((ROOT/'playlist-library-inventory.json').read_text(encoding='utf-8'))
    index=collections.defaultdict(list)
    for song in songs:
        for artist in helper['artists'](song):index[artist].append(song)
    db=sqlite3.connect((ROOT/'data/navidrome.db').as_uri()+'?mode=ro',uri=True)
    paths=dict(db.execute('SELECT id,path FROM media_file WHERE coalesce(missing,0)=0'));db.close()
    missing=[];plan=[];used=set(EXCLUDED_RECORDINGS)
    for name,description,listing in SETS:
        selected=[]
        for line in listing.splitlines():
            artist,title=(part.strip() for part in line.split('|',1))
            wanted=helper['title_key'](title)
            choices=[s for s in index[helper['norm'](artist)] if helper['title_key'](s['title'])==wanted
                     and s.get('suffix','').lower()=='flac' and s.get('userRating',0) not in [1,2]
                     and s['id'] in paths and 90<=s.get('duration',0)<=900
                     and not re.search(r'\b(live|demo|radio session|acoustic|remix)\b',s['title']+' '+s.get('album',''),re.I)]
            def rank(s):
                return (helper['norm'](s['title'])!=helper['norm'](title),
                        bool(re.search(r'compilation|greatest|best of',s.get('album',''),re.I)),
                        -s.get('bitDepth',0),len(s['title']),s['id'])
            valid=[]
            for song in sorted(choices,key=rank):
                path=(MUSIC/paths[song['id']]).resolve()
                if not path.is_relative_to(MUSIC):continue
                try:
                    with path.open('rb') as f:
                        header=f.read(10)
                        if header[:3]==b'ID3' and len(header)==10 and all(b<128 for b in header[6:10]):
                            size=sum(value << shift for value,shift in zip(header[6:10],[21,14,7,0]))
                            f.seek(10+size+(10 if header[3]==4 and header[5]&16 else 0))
                            header=f.read(4)
                        if path.stat().st_size>100000 and header[:4]==b'fLaC':valid.append(song)
                except OSError:pass
            if not valid:
                missing.append({'playlist':name,'artist':artist,'title':title});continue
            song=valid[0];key=(helper['norm'](artist),wanted)
            if key in used:raise ValueError('Repeated recording across signature sets: '+artist+' - '+title)
            used.add(key)
            selected.append({key:song.get(key) for key in ['id','artist','title','album','duration','bitDepth']})
        plan.append({'name':name,'comment':MARKER+' '+description,'songs':selected,
                     'minutes':round(sum(s['duration'] for s in selected)/60),
                     'artists':len({helper['norm'](s['artist']) for s in selected})})
    if missing:
        print(json.dumps({'missing':missing},ensure_ascii=True,indent=2),flush=True)
        raise SystemExit(2)
    (ROOT/PLAN_NAME).write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([{'name':p['name'],'tracks':len(p['songs']),'minutes':p['minutes'],
                       'running_order':[s['artist']+' - '+s['title'] for s in p['songs']]} for p in plan],ensure_ascii=True,indent=2),flush=True)
    return plan


def publish(plan):
    api=runpy.run_path(str(SOURCE/'playlist-library-audit.py'))['api']
    listed=api('getPlaylists').get('playlists',{}).get('playlist',[])
    backup=ROOT/'playlist-backups'/(BACKUP_PREFIX+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    backup.mkdir(parents=True)
    snapshots=[api('getPlaylist',id=p['id'])['playlist'] for p in listed]
    (backup/'before.json').write_text(json.dumps(snapshots,ensure_ascii=False,indent=2),encoding='utf-8')
    # Check every name before creating anything.
    for p in plan:
        matches=[old for old in snapshots if old['name'].casefold()==p['name'].casefold()]
        if len(matches)>1:raise ValueError('Ambiguous playlist name: '+p['name'])
        if matches and (matches[0].get('comment')!=p['comment'] or
                        [s['id'] for s in matches[0].get('entry',[])]!=[s['id'] for s in p['songs']]):
            raise ValueError('An existing playlist differs; refusing to overwrite: '+p['name'])
    results=[]
    for p in plan:
        ids=[s['id'] for s in p['songs']]
        current=next((old for old in snapshots if old['name'].casefold()==p['name'].casefold()),None)
        if current is None:
            current=api('createPlaylist',name=p['name'],songId=ids)['playlist']
            results.append({'id':current['id'],'name':p['name'],'status':'created'})
            (ROOT/RESULT_NAME).write_text(json.dumps({'playlists':results,'backup':str(backup)},indent=2),encoding='utf-8')
            api('updatePlaylist',playlistId=current['id'],comment=p['comment'],public='false')
        for client in ['Feishin','Symfonium']:
            verified=api('getPlaylist',client=client,id=current['id'])['playlist']
            assert [s['id'] for s in verified.get('entry',[])]==ids,p['name']+' track order changed'
            assert not verified.get('public',False)
        result={'id':current['id'],'name':p['name'],'tracks':len(ids),'minutes':p['minutes'],'order_verified':True}
        if results and results[-1]['id']==current['id']:results[-1]=result
        else:results.append(result)
        (ROOT/RESULT_NAME).write_text(json.dumps({'playlists':results,'backup':str(backup)},indent=2)+'\n',encoding='utf-8')
        print(json.dumps(result,ensure_ascii=True),flush=True)
    after=api('getPlaylists').get('playlists',{}).get('playlist',[])
    assert {(p['id'],p['name']) for p in listed}<={(p['id'],p['name']) for p in after}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--create',action='store_true')
    args=parser.parse_args();plan=build()
    if args.create:publish(plan)
