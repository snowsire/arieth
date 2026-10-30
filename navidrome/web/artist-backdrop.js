/* Use the current artist's photo in front and behind the web player and lyrics. */
(() => {
  'use strict';
  const backgroundSelector = '.fs-full-screen-player-module-background-image, .fs-mobile-fullscreen-player-module-background-image';
  const foregroundSelector = 'img.full-screen-player-image, img.fs-mobile-fullscreen-player-module-album-image';
  const metadataSelector = '.fs-shared-full-screen-player-metadata-module-metadata-container';
  const cache = new Map();
  const pending = new Map();
  let activeKey = '';
  let generation = 0;
  let scheduled;

  function clearBackgrounds(nodes) {
    for (const node of nodes) {
      node.classList.remove('snow-artist-backdrop');
      node.classList.remove('snow-artist-foreground');
      node.style.removeProperty('--snow-artist-photo');
      delete node.dataset.snowArtist;
    }
  }

  function currentArtist() {
    const metadata = [...document.querySelectorAll(metadataSelector)]
      .find(node => node.getClientRects().length);
    const link = metadata?.querySelector('a[href^="#/library/album-artists/"]')
      || document.querySelector('.media-player .song-artist a[href^="#/library/album-artists/"]');
    if (!link) return null;
    const match = link.getAttribute('href')?.match(/^#\/library\/album-artists\/([^/]+)/);
    if (!match) return null;
    try {
      const server = JSON.parse(localStorage.getItem('store_authentication'))?.state?.currentServer;
      if (!server || server.type !== 'navidrome' || !server.credential) return null;
      const base = new URL(server.url, location.href);
      if (base.origin !== location.origin) return null;
      const artistId = decodeURIComponent(match[1]);
      const url = new URL(base.pathname.replace(/\/$/, '') + '/rest/getCoverArt.view', base.origin);
      const auth = new URLSearchParams(server.credential);
      for (const key of ['u', 's', 't', 'p']) {
        if (auth.has(key)) url.searchParams.set(key, auth.get(key));
      }
      url.searchParams.set('id', 'ar-' + artistId);
      url.searchParams.set('size', '1600');
      url.searchParams.set('v', '1.16.1');
      url.searchParams.set('c', 'SnowMusicBackdrop');
      return { key: server.id + ':' + artistId, artistId, url: url.href };
    } catch {
      return null;
    }
  }

  function loadPhoto(artist) {
    if (pending.has(artist.key)) return pending.get(artist.key);
    const request = fetchPhoto(artist).finally(() => pending.delete(artist.key));
    pending.set(artist.key, request);
    return request;
  }

  function remember(key, photo, ttl) {
    const old = cache.get(key);
    if (old?.photo) URL.revokeObjectURL(old.photo);
    cache.delete(key);
    cache.set(key, { photo, expires: Date.now() + ttl });
    if (cache.size > 20) {
      const [oldKey, entry] = cache.entries().next().value;
      if (entry.photo) URL.revokeObjectURL(entry.photo);
      cache.delete(oldKey);
    }
  }

  async function fetchPhoto(artist) {
    const known = cache.get(artist.key);
    if (known && known.expires > Date.now()) return known.photo;
    try {
      const infoUrl = new URL(artist.url);
      infoUrl.pathname = infoUrl.pathname.replace('getCoverArt.view', 'getArtistInfo2.view');
      infoUrl.searchParams.set('id', artist.artistId);
      infoUrl.searchParams.set('f', 'json');
      const infoResponse = await fetch(infoUrl, { credentials: 'same-origin' });
      const info = (await infoResponse.json())['subsonic-response'];
      if (info?.status !== 'ok' || !info.artistInfo2?.largeImageUrl) throw new Error('Artist photo unavailable');
      const response = await fetch(artist.url, { credentials: 'same-origin' });
      if (!response.ok) throw new Error('No artist photo');
      const blob = await response.blob();
      if (!blob.type.startsWith('image/') || blob.type.includes('svg')) throw new Error('No photograph');
      const photo = URL.createObjectURL(blob);
      const image = new Image();
      image.src = photo;
      try {
        await image.decode();
        if (image.naturalWidth < 96 || image.naturalHeight < 96) throw new Error('Image too small');
      } catch (error) {
        URL.revokeObjectURL(photo);
        throw error;
      }
      remember(artist.key, photo, 3600000);
      return photo;
    } catch {
      remember(artist.key, null, 300000);
      return null;
    }
  }

  async function update() {
    const nodes = [...document.querySelectorAll(backgroundSelector)];
    const foreground = [...document.querySelectorAll(foregroundSelector)];
    const artist = currentArtist();
    const nextKey = (nodes.length || foreground.length) && artist ? artist.key : '';
    if (nextKey !== activeKey) {
      activeKey = nextKey;
      generation++;
      clearBackgrounds([...nodes, ...foreground]);
    }
    if (!nextKey) return;
    const requestGeneration = generation;
    const photo = await loadPhoto(artist);
    if (requestGeneration !== generation || !photo) return;
    for (const node of document.querySelectorAll(backgroundSelector + ', ' + foregroundSelector)) {
      const value = 'url("' + photo + '")';
      if (node.dataset.snowArtist === artist.artistId && node.style.getPropertyValue('--snow-artist-photo') === value) continue;
      node.style.setProperty('--snow-artist-photo', value);
      node.dataset.snowArtist = artist.artistId;
      node.classList.add(node.matches(backgroundSelector) ? 'snow-artist-backdrop' : 'snow-artist-foreground');
    }
  }

  function schedule() {
    if (scheduled) return;
    scheduled = setTimeout(() => { scheduled = null; update(); }, 80);
  }

  new MutationObserver(schedule).observe(document.documentElement, {
    childList: true, subtree: true, attributes: true, attributeFilter: ['href', 'class']
  });
  window.addEventListener('hashchange', schedule);
  document.addEventListener('visibilitychange', schedule);
  schedule();
})();
