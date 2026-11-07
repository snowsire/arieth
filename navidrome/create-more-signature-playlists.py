"""A second collection of hand-sequenced playlists using available local music."""
import argparse
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('signature_sets',ROOT/'create-signature-playlists.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
builder.MARKER='Arieth signature sets volume two v1.'
builder.PLAN_NAME='signature-volume-two-plan.json'
builder.RESULT_NAME='signature-volume-two-result.json'
builder.BACKUP_PREFIX='signature-volume-two-'
builder.EXCLUDED_RECORDINGS=builder.recording_keys(builder.SETS)
builder.SETS=[
('No Brakes',
 'A heavier second set: short fuses, fast turns, then a final stomp. More bite than Teeth & Heart, with a different track list. Play in order.',
 '''Linkin Park | Given Up
I Prevail | Bow Down
Bring Me The Horizon | The House of Wolves
A Day To Remember | Mr. Highway's Thinking About The End
Silverstein | Your Sword Versus My Dagger
Senses Fail | Bite To Break Skin
Underoath | A Boy Brushed Red Living in Black and White
Escape The Fate | The Guillotine
Thrice | Deadbolt
Thursday | Understanding In A Car Crash
Finch | Bitemarks And Bloodstains
Saosin | Sleepers
Bad Omens | Artificial Suicide
Electric Callboy | Tekkno Train
I Prevail | Body Bag
Bring Me The Horizon | Antivist
A Day To Remember | The Plot To Bomb The Panhandle
Rise Against | Give It All
Linkin Park | Bleed It Out
Thrice | The Earth Will Shake'''),
('Back Seat Choir',
 'Big pop-punk hooks for a car full of people who know every word. Starts rowdy, stays bright, then gives the last chorus room to land. Play in order.',
 '''Good Charlotte | The Anthem
Sum 41 | Fat Lip
New Found Glory | My Friend Over You
blink-182 | What's My Age Again?
The All-American Rejects | Move Along
Simple Plan | I'd Do Anything
Relient K | Be My Escape
Motion City Soundtrack | Everything Is Alright
Yellowcard | Way Away
Alkaline Trio | Private Eye
Fall Out Boy | Saturday
Taking Back Sunday | You're So Last Summer
My Chemical Romance | I'm Not Okay (I Promise)
Paramore | crushcrushcrush
Good Charlotte | Lifestyles of the Rich and Famous
Sum 41 | In Too Deep
New Found Glory | Head On Collision
blink-182 | Reckless Abandon
Simple Plan | Welcome To My Life
The All-American Rejects | It Ends Tonight'''),
('First Light, Last Dance',
 'Progressive house, vocal trance and a few early-hours favorites. Long builds, big melodies and a quiet final landing. Full songs in a fixed order, not a beatmatched mix.',
 '''Tiesto | Ten Seconds Before Sunrise
Kaskade | Stars Align
iiO | Rapture
ATB | Heartbeat (Club Version)
Armin van Buuren | This Light Between Us
Kaskade | Angel On My Shoulder
Armin van Buuren | Not Giving Up On Love
Alice Deejay | Back in My Life
Tiesto | Carpe Noctum
Armin van Buuren | Communication Part 3
ATB | Apollo Road (Club Version) (Dash Berlin)
Alice Deejay | Better Off Alone
Armin van Buuren | Burned With Desire (Rising Star Mix)
deadmau5 | Not Exactly
Kaskade | Move For Me
Tiesto | In The Dark
iiO | At The End
ATB | Moments In Peace'''),
('Concrete & Conscience',
 'Hip-hop with weight: current favorites, older heavy hitters, then more reflective storytelling. Built around the Hilltop Hoods and Kendrick side of your listening. Play in order.',
 '''Hilltop Hoods | Fall From The Light
Kendrick Lamar | Not Like Us
Jay-Z | 99 Problems
OutKast | Rosa Parks
Eminem | 'Till I Collapse
Cypress Hill | Insane In The Brain
Public Enemy | Fight The Power
G-Eazy | The Beautiful & Damned
Atmosphere | Trying To Find A Balance
Linkin Park | Nobody's Listening
Kendrick Lamar | heart pt. 6
OutKast | Da Art of Storytellin', Part 1
Jay-Z | Heart of the City (Ain't No Love)
Hilltop Hoods | Something Bigger Than This
Eminem | The Way I Am
Atmosphere | Yesterday
G-Eazy | Eazy
Kendrick Lamar | luther
Hilltop Hoods | Never Coming Home
Eminem | Sing For The Moment'''),
('Smoke & Signals',
 'Late-night beats, trip-hop and spacious electronic music. A slow burn through DJ Shadow, Massive Attack and Royksopp, with an instrumental finish. Play in order.',
 '''DJ Shadow | Building Steam With a Grain of Salt
Massive Attack | Teardrop
Royksopp | Sparks
Radiohead | Everything In Its Right Place
Flume | Take a Chance
Massive Attack | Paradise Circus
DJ Shadow | Midnight In a Perfect World
Royksopp | Remind Me
Kaskade | Be Still
Flume | Like Water
Radiohead | Subterranean Homesick Alien
Massive Attack | Protection
Royksopp | Eple
deadmau5 | Alone With You
Kaskade | In This Life
DJ Shadow | Blood On the Motorway
Nine Inch Nails | A Warm Place
Nine Inch Nails | Leaving Hope'''),
]

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--create',action='store_true')
    args=parser.parse_args();plan=builder.build()
    if args.create:builder.publish(plan)
