const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../web/artist-backdrop.js'), 'utf8');

test('artist changes discard stale responses, bound failures, and retain album-art fallback', async () => {
  let artist = 'first';
  let observer;
  let scheduled;
  let release;
  let fetchCount = 0;
  const revoked = [];
  const classes = new Set();
  const styles = new Map();
  const node = {
    dataset: {},
    classList: { add: name => classes.add(name), remove: name => classes.delete(name) },
    style: { setProperty: (key, value) => styles.set(key, value),
      getPropertyValue: key => styles.get(key), removeProperty: key => styles.delete(key) },
    matches: () => true,
  };
  class BrowserURL extends URL {
    static createObjectURL() { return 'blob:photo'; }
    static revokeObjectURL(value) { revoked.push(value); }
  }
  const context = {
    URL: BrowserURL, URLSearchParams, Map, Date,
    Image: class { naturalWidth = 200; naturalHeight = 200; async decode() {} },
    location: { href: 'http://localhost:9180/', origin: 'http://localhost:9180' },
    localStorage: { getItem: () => JSON.stringify({ state: { currentServer: {
      id: 'server', type: 'navidrome', credential: 'u=test&t=unused', url: '/navidrome',
    } } }) },
    document: {
      documentElement: {}, addEventListener() {},
      querySelectorAll(selector) {
        if (selector.includes('metadata-container')) return [{
          getClientRects: () => [1], querySelector: () => ({
            getAttribute: () => '#/library/album-artists/' + artist,
          }),
        }];
        return selector.startsWith('img.') ? [] : [node];
      },
    },
    window: { addEventListener() {} },
    setTimeout(callback) { scheduled = callback; return 1; },
    MutationObserver: class { constructor(callback) { observer = callback; } observe() {} },
    async fetch(url) {
      fetchCount++;
      url = new URL(url);
      if (url.pathname.includes('getArtistInfo2')) {
        if (artist === 'first') await new Promise(resolve => { release = resolve; });
        return { json: async () => ({ 'subsonic-response': {
          status: 'ok', artistInfo2: { largeImageUrl: 'available' },
        } }) };
      }
      // The original artwork must remain visible when a photo request fails.
      return { ok: artist === 'second', blob: async () => ({ type: 'image/jpeg' }) };
    },
  };
  const flush = async () => {
    if (scheduled) { const callback = scheduled; scheduled = null; callback(); }
    await new Promise(resolve => setImmediate(resolve));
  };
  vm.runInNewContext(source, context);
  await flush(); // First request remains in flight.
  artist = 'second';
  observer();
  await flush();
  assert.ok(classes.has('snow-artist-backdrop'));
  assert.equal(node.dataset.snowArtist, 'second');
  release();
  await flush();
  assert.equal(node.dataset.snowArtist, 'second');

  for (let index = 0; index < 22; index++) {
    artist = 'missing-' + index;
    observer();
    await flush();
    assert.equal(classes.size, 0);
    assert.equal(styles.size, 0);
  }
  assert.ok(revoked.includes('blob:photo'), 'evicting a photo must release its object URL');
  const before = fetchCount;
  artist = 'missing-0';
  observer();
  await flush();
  assert.ok(fetchCount > before, 'negative cache entries must also respect the cache limit');
});
