"""Six more hand-sequenced listening sets; preview first, --create to publish."""
import argparse
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('signature_builder',ROOT/'create-signature-playlists.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
builder.MARKER='Arieth signature sets volume three v1.'
builder.PLAN_NAME='signature-volume-three-plan.json'
builder.RESULT_NAME='signature-volume-three-result.json'
builder.BACKUP_PREFIX='signature-volume-three-'
builder.EXCLUDED_RECORDINGS=builder.recording_keys(builder.SETS)
prior_spec=importlib.util.spec_from_file_location('signature_volume_two',ROOT/'create-more-signature-playlists.py')
prior=importlib.util.module_from_spec(prior_spec);prior_spec.loader.exec_module(prior)
builder.EXCLUDED_RECORDINGS.update(builder.recording_keys(prior.builder.SETS))
builder.SETS=[
('Feedback Season',
 'Grunge, fuzz and riffs with a pulse. Fast opening run, a heavier middle, then Everlong into Black Hole Sun. Play in order.',
 '''Foo Fighters | The Pretender
Queens Of The Stone Age | No One Knows
Nirvana | Breed
Soundgarden | Rusty Cage
Alice In Chains | Them Bones
Rage Against The Machine | Bulls On Parade
Audioslave | Cochise
Stone Temple Pilots | Plush
Live | I Alone
The Smashing Pumpkins | Bullet With Butterfly Wings
Nirvana | Lithium
Queens Of The Stone Age | Go With The Flow
Foo Fighters | Monkey Wrench
Soundgarden | Outshined
Alice In Chains | Would?
Rage Against The Machine | Killing In The Name
Audioslave | Shadow On The Sun
Live | Lightning Crashes
Foo Fighters | Everlong
Soundgarden | Black Hole Sun'''),
('Letters You Never Sent',
 'The other side of the scene: side projects, deeper favorites and unfinished conversations. Opens with a pulse, gets tangled, then settles into a last few quieter songs. Play in order.',
 '''+44 | When Your Heart Stops Beating
Box Car Racer | I Feel So
Armor For Sleep | Car Underwater
Bayside | Duality
Matchbook Romance | The Greatest Fall (Of All Time)
Anberlin | Paperthin Hymn
Emarosa | The Past Should Stay Dead
Dance Gavin Dance | Lemon Meringue Tie
Chiodos | Baby, You Wouldn't Last A Minute On The Creek
Scary Kids Scaring Kids | My Darkest Hour
Hawthorne Heights | Niki FM
Senses Fail | Rum Is For Drinking, Not For Burning
Thursday | War All The Time
The Used | Blue And Yellow
Taking Back Sunday | This Photograph Is Proof (I Know You Know)
Dashboard Confessional | Vindicated
Box Car Racer | There Is
+44 | No, It Isn't
Dashboard Confessional | Stolen
Brand New | Soco Amaretto Lime'''),
('Nightfall on the Long Way Home',
 'Classic-rock slow burns, warm guitars and long horizons. Plenty of space for the songs to unfold; the final stretch is the destination. Play in order.',
 '''Journey | Who's Crying Now
The Eagles | One Of These Nights
Steely Dan | Deacon Blues
Led Zeppelin | No Quarter
Santana | Samba Pa Ti
Eric Clapton | Old Love
Lenny Kravitz | It Ain't Over 'Til It's Over
The Who | Behind Blue Eyes
Lynyrd Skynyrd | Simple Man
Ozzy Osbourne | Mama, I'm Coming Home
Bon Jovi | Wanted Dead Or Alive
Guns N' Roses | November Rain
Boston | A Man I'll Never Be
Pink Floyd | Time
Led Zeppelin | The Rain Song
The Eagles | The Last Resort
Pink Floyd | Comfortably Numb'''),
('Beautiful Machines',
 'Industrial pulse, intricate rhythms and wide-open guitars. Tense at first, then bigger and more spacious, with a quieter final descent. Headphones suggested; play in order.',
 '''Nine Inch Nails | The Hand That Feeds
Tool | Stinkfist
A Perfect Circle | The Outsider
Deftones | My Own Summer (Shove It)
Muse | Hysteria
Rage Against The Machine | Calm Like A Bomb
Queens Of The Stone Age | Sick, Sick, Sick
Nine Inch Nails | Wish
Tool | Forty Six & 2
A Perfect Circle | Weak And Powerless
Deftones | Be Quiet And Drive (Far Away)
Nine Inch Nails | We're In This Together
Muse | Stockholm Syndrome
Tool | Schism
A Perfect Circle | The Noose
Deftones | Cherry Waves
Nine Inch Nails | The Great Below
Tool | Lateralus
A Perfect Circle | Gravity
Deftones | Riviere'''),
('Borrowed Voices',
 'Familiar songs in different hands: pop hooks become heavy, the middle gets darker, then the closing run brings the singalongs back. A covers set, sequenced to play in order.',
 '''A Day To Remember | Since U Been Gone
Tonight Alive | Little Lion Man
Go Radio | Rolling in the Deep
Mayday Parade | Somebody That I Used To Know
A Static Lullaby | Toxic
Framing Hanley | Lollipop
The Word Alive | Heartless
The Cab | Disturbia {Rihanna}
Woe, Is Me | Hot N Cold
Silverstein | Apologize {One Republic}
Thrice | Send Me An Angel
Placebo | Running Up That Hill
Deftones | No Ordinary Love
Nine Inch Nails | Dead Souls
Metallica | Whiskey In The Jar
Limp Bizkit | Faith
Yellowcard | Everywhere
Four Year Strong | Love Song {Sara Bareilles}
We Came As Romans | Glad You Came
Rufio | Like A Prayer'''),
('Sunburn & Bad Ideas',
 'A loose summer afternoon: reggae grooves, rap-rock mischief, a burst of ska-punk, then a slower ride home. Play in order.',
 '''311 | Down
Sublime | What I Got
Red Hot Chili Peppers | Can't Stop
Incubus | Are You In?
OutKast | Ms. Jackson
Cypress Hill | Hits From The Bong
311 | Beautiful Disaster
Limp Bizkit | Nookie
Rage Against The Machine | Guerrilla Radio
Cypress Hill | (Rock) Superstar
Goldfinger | Superman
Less Than Jake | Johnny Quest Thinks We're Sellouts
Goldfinger | Here In Your Bedroom
Millencolin | No Cigar
The Offspring | The Kids Aren't Alright
Sublime | Santeria
Red Hot Chili Peppers | Scar Tissue
311 | 8:16 A.M.
Incubus | Stellar
Sublime | Badfish'''),
]

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--create',action='store_true')
    args=parser.parse_args();plan=builder.build()
    if args.create:builder.publish(plan)
