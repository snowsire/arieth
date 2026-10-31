/* Discovery chrome reuses Feishin's authenticated playlist links and controls. */
(() => {
  'use strict';
  if (window.__snowDiscovery) return;
  window.__snowDiscovery = true;
  const names = {
    'Playlists': 'Mixes for your day',
    'Recently played': 'Back in rotation',
    'Explore from your library': 'Find your next favorite',
    'Most Played': 'On repeat',
    'Genres': 'Find your frequency',
  };
  const palette = [
    [/emo|screamo|post.hardcore/i, '#b46cff', 'orbits'],
    [/punk/i, '#ff639b', 'checker'],
    [/rock|grunge|metal/i, '#ff795b', 'rays'],
    [/dubstep/i, '#31cecb', 'wave'],
    [/drum|bass/i, '#31cecb', 'equalizer'],
    [/dance|house|trance|electro/i, '#688bff', 'grooves'],
    [/indie|alternative/i, '#c279f4', 'orbits'],
    [/jazz|soul|blues/i, '#e9ad53', 'grooves'],
    [/hip.hop|rap|funk/i, '#61c897', 'equalizer'],
    [/pop/i, '#f277be', 'checker'],
    [/ambient|classical|instrumental/i, '#70b6c4', 'orbits'],
  ];
  let timer;
  let genreState = {key:'', items:null};

  function loadGenres() {
    let server;
    try { server = JSON.parse(localStorage.getItem('store_authentication'))?.state?.currentServer; }
    catch { return; }
    if (!server?.ndCredential || server.type !== 'navidrome') return;
    const key = server.id + ':' + server.ndCredential;
    if (genreState.key === key) return;
    let base;
    try { base = new URL(server.url, location.href); } catch { return; }
    if (base.origin !== location.origin) return;
    const requestState = genreState = {key, items:null};
    const url = new URL(base.pathname.replace(/\/$/, '') + '/api/genre', base.origin);
    url.search = '_start=0&_end=500&_sort=name&_order=ASC';
    fetch(url, {headers:{'x-nd-authorization':'Bearer ' + server.ndCredential}, credentials:'same-origin'})
      .then(response => { if (!response.ok) throw new Error('Genres unavailable'); return response.json(); })
      .then(items => {
        if (genreState !== requestState || !Array.isArray(items)) return;
        requestState.items = items;
        schedule();
      })
      .catch(() => {}); // Original Feishin genre links remain available on failure.
  }

  function curateGenres() {
    if (!genreState.items) return;
    const container = document.querySelector('.fs-featured-genres-module-container');
    if (!container || container.querySelector('.snow-genre-picks')) return;
    const choices = [
      [['rock'], 'LOUD & CLEAR', '#ff795b'],
      [['emo','emocore','post-hardcore'], 'ALL THE FEELINGS', '#b46cff'],
      [['pop-punk','pop punk','punk','punk rock'], 'GOOD TROUBLE', '#ff639b'],
      [['dance','house','electronic'], 'AFTER HOURS', '#688bff'],
      [['dubstep'], 'HEAVY LOWS', '#31cecb'],
      [['drum & bass','drum and bass',"drum 'n bass"], 'HIGHER TEMPO', '#e9ad53'],
    ];
    const grid = document.createElement('div');
    grid.className = 'snow-genre-picks';
    for (const [aliases, subtitle, color] of choices) {
      const genre = aliases.map(name => genreState.items.find(item => item.name?.toLowerCase() === name)).find(Boolean);
      if (!genre?.id) continue;
      const tile = document.createElement('a');
      tile.href = '#/library/genres/' + encodeURIComponent(genre.id);
      tile.className = 'snow-genre-tile';
      tile.dataset.snowGenreArt = palette.find(([pattern]) => pattern.test(genre.name))?.[2] || 'orbits';
      tile.style.setProperty('--snow-genre-color', color);
      tile.style.setProperty('--snow-genre-rgb', color.slice(1).match(/../g).map(part => parseInt(part,16)).join(','));
      const kicker = document.createElement('span');
      kicker.className = 'snow-genre-kicker';
      kicker.textContent = subtitle;
      const name = document.createElement('strong');
      name.textContent = genre.name;
      const arrow = document.createElement('span');
      arrow.className = 'snow-genre-arrow';
      arrow.setAttribute('aria-hidden', 'true');
      arrow.textContent = '↗';
      tile.append(kicker, name, arrow);
      grid.append(tile);
    }
    if (!grid.children.length) return;
    container.append(grid);
    container.classList.add('snow-curated-genres');
  }

  function makeHero(container) {
    const hero = document.createElement('section');
    hero.id = 'snow-discovery-hero';
    hero.setAttribute('aria-label', 'Your daily listening');
    hero.innerHTML = '<div class="snow-discovery-copy">'
      + '<span class="snow-eyebrow">YOUR COLLECTION. A NEW PERSPECTIVE.</span>'
      + '<h2>Your Daily Mix<span>A little familiar.<br>A little unexpected.</span></h2>'
      + '<p>Your favorites, your discoveries, your next obsession. All from your own collection.</p>'
      + '<div class="snow-discovery-actions"><a class="snow-mix-open" href="#/playlists">Explore your mixes <span aria-hidden="true">↗</span></a>'
      + '<a class="snow-mix-browse" href="#/playlists">All playlists <span aria-hidden="true">→</span></a></div></div>'
      + '<div class="snow-mix-art" aria-hidden="true"><span class="snow-mix-art-label">MADE FOR YOU</span>'
      + '<strong>DAILY<br>MIX<span>01 / YOUR SOUND</span></strong><i></i><b></b></div>';
    container.append(hero);
    return hero;
  }

  function update() {
    timer = null;
    for (const node of document.querySelectorAll('.fs-featured-genres-module-genre-container, .fs-item-card-module-genre-placeholder')) {
      const name = node.querySelector('.fs-featured-genres-module-genre-name, .fs-item-card-module-genre-placeholder-text')?.textContent.trim();
      if (!name || node.dataset.snowGenre === name) continue;
      const [, color, artwork] = palette.find(([pattern]) => pattern.test(name)) || [null, '#8b95e8', 'orbits'];
      node.dataset.snowGenreArt = artwork;
      node.style.setProperty('--snow-genre-color', color);
      node.style.setProperty('--snow-genre-rgb', color.slice(1).match(/../g).map(part => parseInt(part,16)).join(','));
      if (node.matches('.fs-item-card-module-genre-placeholder')) {
        node.style.setProperty('background', 'radial-gradient(ellipse at 100% 0%, ' + color + '99, transparent 75%), linear-gradient(135deg, ' + color + '66, #17131f)', 'important');
      }
      node.dataset.snowGenre = name;
    }
    const isHome = !location.hash || /^#\/?(?:\?.*)?$/.test(location.hash);
    document.body.classList.toggle('snow-discovery-home', isHome);
    if (!isHome) return;
    loadGenres();
    curateGenres();
    const container = document.querySelector('.fs-feature-carousel-module-single-carousel-container');
    if (container) {
      const hero = container.querySelector('#snow-discovery-hero') || makeHero(container);
      const daily = [...document.querySelectorAll('a[href^="#/playlists/"]')]
        .find(link => !hero.contains(link) && link.textContent.trim() === 'Your Daily Mix');
      const open = hero.querySelector('.snow-mix-open');
      const href = daily?.getAttribute('href');
      if (href && /^#\/playlists\/[^/]+\/songs$/.test(href) && open.getAttribute('href') !== href) {
        open.setAttribute('href', href);
        open.innerHTML = 'Open today’s mix <span aria-hidden="true">↗</span>';
      }
    }
    for (const title of document.querySelectorAll('h3')) {
      const replacement = names[title.textContent.trim()];
      if (replacement) title.textContent = replacement;
    }
  }

  function schedule() {
    if (!timer) timer = setTimeout(update, 160);
  }
  const observer = new MutationObserver(schedule);
  observer.observe(document.body, {childList:true, subtree:true});
  window.addEventListener('hashchange', schedule);
  window.addEventListener('pageshow', schedule);
  window.addEventListener('pagehide', event => {
    clearTimeout(timer);
    timer = null;
    if (!event.persisted) observer.disconnect();
  });
  update();
})();
