const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
execFileSync(process.env.PYTHON || 'python', ['prepare-phone-settings.py'], { cwd: root });
const settings = fs.readFileSync(path.join(root, 'web/settings.js'), 'utf8');

function browser(initial = {}) {
  const values = new Map(Object.entries(initial));
  const context = {
    window: { location: { origin: 'http://localhost:9180' } },
    localStorage: { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value) },
    console: { warn() {} },
  };
  const run = () => vm.runInNewContext(settings, context);
  const read = key => JSON.parse(values.get(key));
  return { run, read, values, context };
}

test('fresh browser gets a complete home order and visible song metadata', () => {
  const app = browser();
  app.run();
  const state = app.read('store_settings').state;
  assert.equal(state.general.homeItems[0].id, 'playlists');
  assert.equal(state.general.homeItems.length, 7);
  assert.deepEqual(state.general.homeItems.filter(item => item.disabled).map(item => item.id), ['recentlyAdded', 'recentlyReleased']);
  assert.deepEqual(state.general.playerItems.map(item => item.id), ['title', 'artist', 'album']);
  assert.ok(state.general.playerItems.every(item => !item.disabled));
  assert.equal(state.lyrics.lineLeadTimeMs, 650);
  assert.equal(state.lyrics.delayMs, 0);
  assert.equal(app.context.window.SERVER_URL, 'http://localhost:9180/navidrome');
  assert.equal(app.context.window.ANALYTICS_DISABLED, 'true');
});

test('migration preserves unrelated preferences and orders unknown sections last', () => {
  const app = browser({
    store_settings: JSON.stringify({ version: 34, state: {
      playback: { volume: 23 }, general: {
        homeItems: [{ id: 'future' }, { id: 'genres' }, { id: 'recentlyPlayed' }],
        playerItems: [{ id: 'title', disabled: true }, { id: 'codec', disabled: true }],
      }, lyrics: { translation: 'existing' },
    } }),
    store_authentication: 'do not modify authentication',
  });
  app.run();
  const state = app.read('store_settings').state;
  assert.equal(state.playback.volume, 23);
  assert.equal(state.lyrics.translation, 'existing');
  assert.deepEqual(state.general.homeItems.map(item => item.id), ['playlists', 'genres', 'recentlyPlayed', 'random', 'mostPlayed', 'recentlyAdded', 'recentlyReleased', 'future']);
  assert.equal(state.general.playerItems.find(item => item.id === 'codec').disabled, true);
  assert.equal(state.general.playerItems.find(item => item.id === 'title').disabled, false);
  assert.equal(app.values.get('store_authentication'), 'do not modify authentication');
  state.general.accent = 'my preference';
  app.values.set('store_settings', JSON.stringify({ state, version: 34 }));
  app.run();
  assert.equal(app.read('store_settings').state.general.accent, 'my preference');
});

test('missing state is repaired and corrupt storage is left intact', () => {
  const partial = browser({ store_settings: '{}' });
  partial.run();
  assert.equal(partial.read('store_settings').state.lyrics.follow, true);
  const corrupt = browser({ store_settings: '{broken' });
  assert.doesNotThrow(corrupt.run);
  assert.equal(corrupt.values.get('store_settings'), '{broken');
  assert.equal(corrupt.values.has('snow_theme_revision'), false);
});

test('existing theme gets discovery Home without resetting playback or lyric choices', () => {
  const app = browser({
    snow_theme_revision: 'crimson-5',
    store_settings: JSON.stringify({version:34,state:{
      general:{accent:'my color',homeItems:[{id:'recentlyAdded',disabled:false},{id:'recentlyReleased',disabled:false}]},
      playback:{volume:17}, lyrics:{follow:false,delayMs:300},
    }}),
  });
  app.run();
  const state = app.read('store_settings').state;
  assert.equal(state.general.accent, 'my color');
  assert.equal(state.playback.volume, 17);
  assert.equal(state.lyrics.follow, false);
  assert.equal(state.lyrics.delayMs, 300);
  assert.ok(state.general.homeItems.filter(item => ['recentlyAdded','recentlyReleased'].includes(item.id)).every(item => item.disabled));
  assert.equal(app.values.get('snow_home_revision'), 'discovery-1');
  assert.ok(state.css.content.includes('snow-discovery-hero'));
});

test('responsive lyrics migrate once and preserve custom offsets and Home settings', () => {
  const app = browser({
    snow_theme_revision:'crimson-5', snow_home_revision:'discovery-1',
    store_settings:JSON.stringify({version:34,state:{
      general:{homeItems:[{id:'recentlyAdded',disabled:true}]},
      lyrics:{lineLeadTimeMs:250,delayMs:320,follow:false,preferLocalLyrics:false},
      playback:{volume:19},
    }}),
  });
  app.run();
  let state=app.read('store_settings').state;
  assert.equal(state.lyrics.lineLeadTimeMs,650);
  assert.equal(state.lyrics.delayMs,320);
  assert.equal(state.lyrics.follow,false);
  assert.equal(state.lyrics.preferLocalLyrics,false);
  assert.equal(state.playback.volume,19);
  assert.equal(state.general.homeItems[0].disabled,true);
  assert.ok(state.css.content.includes('transition-duration: 180ms, 180ms'));
  state.lyrics.lineLeadTimeMs=450;
  app.values.set('store_settings',JSON.stringify({version:34,state}));
  app.run();
  assert.equal(app.read('store_settings').state.lyrics.lineLeadTimeMs,450);
});

test('compact lyrics fit more lines while preserving timing and unrelated display choices', () => {
  const app=browser({
    snow_theme_revision:'crimson-5', snow_home_revision:'discovery-1', snow_lyrics_revision:'responsive-1',
    store_settings:JSON.stringify({version:34,state:{
      lyrics:{lineLeadTimeMs:650,delayMs:280,follow:true},
      lyricsDisplay:{default:{fontSize:32,gap:28,opacityNonActive:0.4},sidebar:{gap:22,paddingLeft:3}},
      general:{homeItems:[{id:'recentlyAdded',disabled:true}]},
    }}),
  });
  app.run();
  const state=app.read('store_settings').state;
  assert.equal(state.lyricsDisplay.default.gap,12);
  assert.equal(state.lyricsDisplay.default.fontSize,28);
  assert.equal(state.lyricsDisplay.default.opacityNonActive,0.4);
  assert.equal(state.lyricsDisplay.sidebar.gap,8);
  assert.equal(state.lyricsDisplay.sidebar.paddingLeft,3);
  assert.equal(state.lyrics.lineLeadTimeMs,650);
  assert.equal(state.lyrics.delayMs,280);
  assert.equal(state.general.homeItems[0].disabled,true);
  state.lyricsDisplay.default.gap=16;
  app.values.set('store_settings',JSON.stringify({version:34,state}));
  app.run();
  assert.equal(app.read('store_settings').state.lyricsDisplay.default.gap,16);
});
