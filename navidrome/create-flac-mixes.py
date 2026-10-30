"""Curate five FLAC-only server playlists; --create publishes the reviewed plan."""
import argparse
import collections
import json
import os
from pathlib import Path
import re
import runpy
import unicodedata

SOURCE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get('NAVIDROME_DATA_DIR', SOURCE / 'local')).expanduser().resolve()
MARKER = 'Arieth FLAC mix v1, 2026-10-30.'
MIXES = {
    'Rock - Classics & Anthems': '''
Led Zeppelin | Black Dog | Rock And Roll
Guns N' Roses | Welcome To The Jungle | Sweet Child O'Mine
The Rolling Stones | Gimme Shelter | Paint It Black
Lynyrd Skynyrd | Sweet Home Alabama | Free Bird
The Who | Baba O'Riley | Won't Get Fooled Again
Pink Floyd | Money | Comfortably Numb
Boston | More Than A Feeling | Peace Of Mind
Journey | Separate Ways (Worlds Apart) | Don't Stop Believin'
The Eagles | Hotel California | Life In The Fast Lane
Foreigner | Juke Box Hero | Cold As Ice
Bon Jovi | Livin' On A Prayer | You Give Love A Bad Name
Ozzy Osbourne | Crazy Train | Mr. Crowley
Black Sabbath | Paranoid | Iron Man
Iron Maiden | Run To The Hills | The Trooper
Metallica | Enter Sandman | Master Of Puppets
The Jimi Hendrix Experience | Purple Haze | Voodoo Child (Slight Return)
Eric Clapton | Cocaine | Layla
Santana | Black Magic Woman | Oye Como Va
Lenny Kravitz | Are You Gonna Go My Way | Fly Away
Steely Dan | Do It Again | Reelin' In The Years
''',
    'Rock - Alternative & Grunge': '''
Foo Fighters | Everlong | My Hero
Nirvana | Smells Like Teen Spirit | Come As You Are
Soundgarden | Black Hole Sun | Outshined
Alice In Chains | Would? | Man In The Box
Red Hot Chili Peppers | Under The Bridge | Californication
Queens Of The Stone Age | No One Knows | Go With The Flow
The White Stripes | Seven Nation Army | Fell In Love With A Girl
Weezer | Say It Ain't So | Buddy Holly
Radiohead | Creep | Paranoid Android
Muse | Hysteria | Knights Of Cydonia
The Killers | Mr. Brightside | Somebody Told Me
The Strokes | Last Nite | Reptilia
Arctic Monkeys | I Bet You Look Good On The Dancefloor | Fluorescent Adolescent
The Smashing Pumpkins | 1979 | Bullet With Butterfly Wings
Rage Against The Machine | Killing In The Name | Bulls On Parade
Audioslave | Cochise | Like A Stone
Incubus | Drive | Wish You Were Here
Deftones | Change (In The House Of Flies) | My Own Summer (Shove It)
Linkin Park | In The End | Faint
Placebo | Every You Every Me | The Bitter End
''',
    'Emo & Pop Punk - Sing It Loud': '''
My Chemical Romance | Helena | I'm Not Okay (I Promise)
Taking Back Sunday | Cute Without The 'E' (Cut From The Team) | A Decade Under The Influence
Brand New | The Quiet Things That No One Ever Knows | Sic Transit Gloria... Glory Fades
Jimmy Eat World | The Middle | Sweetness
The Used | The Taste Of Ink | Buried Myself Alive
Fall Out Boy | Sugar, We're Goin Down | Dance, Dance
Paramore | Misery Business | That's What You Get
Dashboard Confessional | Vindicated | Stolen
Motion City Soundtrack | Everything Is Alright | The Future Freaks Me Out
AFI | Miss Murder | Girl's Not Grey
Say Anything | Alive With The Glory Of Love | Woe
Alkaline Trio | Radio | Stupid Kid
Bayside | Devotion And Desire | Blame It On Bad Luck
Anberlin | Feel Good Drag | Paperthin Hymn
Death Cab For Cutie | Soul Meets Body | I Will Follow You Into The Dark
Blink-182 | Dammit | I Miss You
+44 | When Your Heart Stops Beating | Lycanthrope
Box Car Racer | I Feel So | There Is
Yellowcard | Ocean Avenue | Way Away
Sum 41 | Fat Lip | In Too Deep
''',
    'Emo - Post-Hardcore Nights': '''
Thursday | Understanding In A Car Crash | War All The Time
Thrice | The Artist In The Ambulance | Stare At The Sun
Silverstein | Smile In Your Sleep | My Heroine
Senses Fail | Bite To Break Skin | Can't Be Saved
Saosin | Seven Years | You're Not Alone
Underoath | A Boy Brushed Red Living In Black And White | Writing On The Walls
Funeral For A Friend | Juneau | Roses For The Dead
Hawthorne Heights | Ohio Is For Lovers | Niki FM
Finch | What It Is To Burn | Letters To You
Story Of The Year | Until The Day I Die | Anthem Of Our Dying Day
Chiodos | Baby, You Wouldn't Last A Minute On The Creek | All Nereids Beware
Scary Kids Scaring Kids | The City Sleeps In Flames | My Darkest Hour
Dance Gavin Dance | Lemon Meringue Tie | Uneasy Hearts Weigh The Most
Emarosa | The Past Should Stay Dead | Set It Off Like Napalm
From Autumn To Ashes | The After Dinner Payback | Milligram Smile
A Static Lullaby | Toxic | Rattlesnake!
The Receiving End Of Sirens | Planning A Prison Break | This Armistice
Escape The Fate | Situations | The Guillotine
A Day To Remember | The Downfall Of Us All | Have Faith In Me
At The Drive-In | One Armed Scissor | Napoleon Solo
''',
    'Dance - After Dark': '''
Daft Punk | One More Time | Around The World
The Chemical Brothers | Hey Boy Hey Girl | Star Guitar
Deadmau5 | I Remember | Ghosts 'n' Stuff
Calvin Harris | Acceptable In The 80s | The Girls
Kaskade | 4am | Stars Align
David Guetta | Love Don't Let Me Go | When Love Takes Over
Armin Van Buuren | Not Giving Up On Love | This Light Between Us
Tiesto | Carpe Noctum | In The Dark
ATB | Apollo Road | Heartbeat (Club Version)
Pendulum | Slam | Propane Nightmares
Nero | Promises | Me And You
Chase & Status | Pieces | Eastern Jam
Shapeshifter | Dutchies | The Touch
MSTRKRFT | Heartbreaker | Bounce
Royksopp | Eple | The Girl And The Robot
Bob Sinclar | I Feel For You | Save Our Soul
Alex Gaudino | Destination Calabria | Watch Out
Alice Deejay | Better Off Alone | Back In My Life
iiO | Rapture | Is It Love
Skream | Midnight Request Line | Rutten
''',
}


def normalize(value):
    text = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode().casefold()
    return re.sub('[^a-z0-9]', '', text.replace('&', 'and'))


def artist_names(song):
    names = {normalize(song.get('artist', '')), normalize(song.get('albumArtist', '')),
            *(normalize(artist['name']) for artist in song.get('artists', [])),
            *(normalize(artist['name']) for artist in song.get('albumArtists', []))}
    if names & {'rollingstones', 'therollingstones', 'rollingstonesthe'}:
        names.add('therollingstones')
    return names


def choose(songs, artist, title):
    artist, title = normalize(artist), normalize(title)
    candidates = [song for song in songs if artist in artist_names(song)
                  and song.get('duration', 0) >= 90
                  and normalize(song['title']).startswith(title)]
    if not candidates:
        return None
    # Prefer the original title/studio take over remixes, demos, or live extras.
    def rank(song):
        label = song['title'].casefold()
        return (normalize(song['title']) != title,
                bool(re.search(r'\b(remix|acoustic|live|demo)\b', label)),
                bool(re.search(r'\b(live|compilation)\b', song.get('album', '').casefold())),
                len(song['title']), -song.get('bitDepth', 0), song['id'])
    return min(candidates, key=rank)


def build():
    songs = json.loads((ROOT/'playlist-library-inventory.json').read_text(encoding='utf-8'))
    assert all(song.get('suffix') == 'flac' and song.get('contentType') == 'audio/flac' for song in songs)
    by_artist = collections.defaultdict(list)
    for song in songs:
        for artist in artist_names(song):
            by_artist[artist].append(song)
    plan, missing, used = [], [], set()
    for name, source in MIXES.items():
        rows = [list(map(str.strip, line.split('|'))) for line in source.strip().splitlines()]
        entries = []
        for column in (1, 2):
            for artist, *titles in rows:
                title = titles[column-1]
                song = choose(by_artist[normalize(artist)], artist, title)
                if not song:
                    missing.append(name+': '+artist+' - '+title)
                    continue
                key = (normalize(song['artist']), normalize(song['title']))
                assert key not in used, 'Duplicate track across mixes: '+song['title']
                used.add(key)
                entries.append(song)
        plan.append(dict(name=name, comment=MARKER+' Forty hand-picked FLAC tracks from your collection. '
                         'Studio versions preferred; artists interleaved for variety.', songs=entries))
    (ROOT/'flac-playlist-plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    print(json.dumps(dict(missing=missing, playlists=[dict(name=p['name'], tracks=len(p['songs']),
        minutes=round(sum(s['duration'] for s in p['songs'])/60)) for p in plan])),flush=True)
    return plan, missing


def publish(plan):
    api = runpy.run_path(str(SOURCE/'playlist-library-audit.py'))['api']
    existing = api('getPlaylists').get('playlists', {}).get('playlist', [])
    # Preserve the previous state and the selected IDs before any writes.
    backup = ROOT/'playlist-backups'/'flac-mixes-20261030'
    backup.mkdir(parents=True, exist_ok=True)
    snapshot = backup/'before.json'
    if not snapshot.exists():
        snapshot.write_text(json.dumps(existing,indent=2),encoding='utf-8')
    results = []
    for playlist in plan:
        ids = [song['id'] for song in playlist['songs']]
        same_name = [item for item in existing if item['name'] == playlist['name']]
        if same_name:
            assert len(same_name) == 1
            found = api('getPlaylist', id=same_name[0]['id'])['playlist']
            assert found.get('comment', '').startswith(MARKER), 'An unrelated playlist already uses this name'
            assert [song['id'] for song in found.get('entry', [])] == ids, 'Existing mix differs; refusing to overwrite'
        else:
            found = api('createPlaylist', name=playlist['name'], songId=ids).get('playlist')
            if not found:
                found = next(item for item in api('getPlaylists')['playlists']['playlist']
                             if item['name'] == playlist['name'])
            api('updatePlaylist', playlistId=found['id'], comment=playlist['comment'], public='false')
            found = api('getPlaylist', id=found['id'])['playlist']
        assert [song['id'] for song in found.get('entry', [])] == ids
        assert all(song.get('suffix') == 'flac' for song in found['entry'])
        results.append({key: found[key] for key in ('id', 'name', 'songCount', 'duration', 'owner')})
        print(json.dumps(results[-1]),flush=True)
        (ROOT/'flac-playlist-result.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    expected = {item['id'] for item in results}
    for client in ('Feishin', 'Symfonium'):
        listed = api('getPlaylists', client=client).get('playlists', {}).get('playlist', [])
        assert expected <= {item['id'] for item in listed}, client+' cannot list the new playlists'
        assert {item['id'] for item in existing} <= {item['id'] for item in listed}, 'An old playlist disappeared'
        for result in results:
            visible = api('getPlaylist', client=client, id=result['id'])['playlist']
            assert len(visible.get('entry', [])) == 40
    print('Verified all five server playlists and their tracks through Feishin and Symfonium API clients.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--create', action='store_true')
    args = parser.parse_args()
    plan, missing = build()
    if args.create:
        assert not missing and len(plan) == 5 and all(len(p['songs']) == 40 for p in plan)
        publish(plan)
