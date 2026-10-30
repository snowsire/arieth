/* Snow Music mobile navigation. All playback and search stay in Feishin. */
(() => {
  'use strict';
  if (window.__snowMobileNavigation) return;
  window.__snowMobileNavigation = true;

  const mobile = window.matchMedia('(max-width: 768px)');
  const drawerSelector = '.fs-mobile-layout-module-drawer-button';
  const overlaySelector = '.fs-mobile-layout-module-full-screen-player-overlay, .mantine-Modal-content, .mantine-Drawer-content, dialog[open]';
  const icons = {
    home: '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z"/>',
    search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
    library: '<rect x="3" y="4" width="4" height="16" rx="1"/><rect x="10" y="4" width="4" height="16" rx="1"/><path d="m18 4 3 16"/>',
    menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  };
  const icon = name => '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + icons[name] + '</svg>';
  const nav = document.createElement('nav');
  nav.id = 'snow-mobile-nav';
  nav.setAttribute('aria-label', 'Music navigation');
  nav.hidden = true;
  nav.innerHTML = [
    '<a href="#/" data-snow-page="home">' + icon('home') + '<span>Home</span></a>',
    '<a href="#/search/song" data-snow-page="search">' + icon('search') + '<span>Search</span></a>',
    '<a href="#/library/albums" data-snow-page="library">' + icon('library') + '<span>Library</span></a>',
    '<button type="button" data-snow-page="menu" aria-label="Open library menu" aria-controls="mobile-sidebar" aria-expanded="false">' + icon('menu') + '<span>Menu</span></button>',
  ].join('');
  document.body.appendChild(nav);

  const menu = nav.querySelector('button');
  menu.addEventListener('click', () => document.querySelector(drawerSelector)?.click());

  let timer = 0;
  let stopped = false;
  let lastReady = null;
  let lastSearch = null;
  let lastActive = '';
  function update() {
    timer = 0;
    if (stopped) return;
    const path = location.hash.slice(1).split('?')[0] || '/';
    const layout = document.getElementById('mobile-layout');
    let signedIn = false;
    try { signedIn = Boolean(JSON.parse(localStorage.getItem('store_authentication') || '{}').state?.currentServer); } catch {}
    const ready = mobile.matches && Boolean(layout && layout.querySelector('#player-bar') && document.querySelector(drawerSelector)) && signedIn && !/^\/(?:login|servers|action-required|no-network)(?:\/|$)/.test(path);
    if (ready !== lastReady) {
      document.body.classList.toggle('snow-mobile-ready', ready);
      lastReady = ready;
    }
    const isSearch = ready && path.startsWith('/search/');
    if (isSearch !== lastSearch) {
      document.body.classList.toggle('snow-mobile-search', isSearch);
      lastSearch = isSearch;
    }
    if (isSearch) {
      document.querySelectorAll('.fs-page-header-module-container input').forEach(input => {
        const header = input.closest('.fs-page-header-module-container');
        // SearchInput's Box owns only TextInput + its collapsed search button.
        let wrapper = input.parentElement;
        while (wrapper && wrapper !== header && !(wrapper.style.display === 'inline-flex' && /^(36px|200px|100%)$/.test(wrapper.style.width))) wrapper = wrapper.parentElement;
        if (!wrapper || wrapper === header) return;
        wrapper.classList.add('snow-native-search');
        wrapper.parentElement.classList.add('snow-search-field-slot');
        header.classList.add('snow-search-header');
        const heading = header.querySelector('.fs-page-header-module-title-wrapper > div');
        heading?.classList.add('snow-search-heading');
        if (!input.getAttribute('placeholder')) input.setAttribute('placeholder', 'Search your music');
        if (!input.getAttribute('aria-label')) input.setAttribute('aria-label', 'Search your music');
      });
    }
    if (ready) {
      for (const [headerClass, closeLabel] of [['lyrics', 'Close lyrics'], ['queue', 'Close queue']]) {
        const buttons = document.querySelectorAll('.fs-mobile-fullscreen-player-module-' + headerClass + '-header button');
        if (buttons.length === 2) {
          buttons[0].setAttribute('aria-label', 'Minimize player');
          buttons[1].setAttribute('aria-label', closeLabel);
        }
      }
      // Feishin 1.17.0's MobileFullscreenPlayerBottomControls source order.
      const labels = ['Shuffle', 'Repeat', 'Queue', 'Lyrics', 'More'];
      document.querySelectorAll('.fs-mobile-fullscreen-player-module-bottom-controls-group').forEach(group => {
        const buttons = [...group.querySelectorAll('button.fs-mobile-fullscreen-player-module-bottom-control-icon')];
        if (buttons.length !== labels.length) return;
        buttons.forEach((button, index) => {
          if (button.dataset.snowControlLabel === labels[index]) return;
          button.dataset.snowControlLabel = labels[index];
          button.setAttribute('aria-label', labels[index]);
          button.title = labels[index];
        });
      });
    }
    const overlayOpen = Boolean(document.querySelector(overlaySelector));
    nav.hidden = !ready || overlayOpen;
    const drawerOpen = Boolean(document.getElementById('mobile-sidebar'));
    const active = path === '/' ? 'home' : path.startsWith('/search/') ? 'search' : /^\/(?:library|favorites|playlists)(?:\/|$)/.test(path) ? 'library' : '';
    if (active !== lastActive) {
      nav.querySelectorAll('a').forEach(link => {
        if (link.dataset.snowPage === active) link.setAttribute('aria-current', 'page');
        else link.removeAttribute('aria-current');
      });
      lastActive = active;
    }
    if (menu.getAttribute('aria-expanded') !== String(drawerOpen)) menu.setAttribute('aria-expanded', String(drawerOpen));
  }

  // A bounded throttle avoids work on each lyric tick or artwork mutation.
  function schedule() {
    if (!timer && !stopped) timer = window.setTimeout(update, 120);
  }
  const observer = new MutationObserver(records => {
    if (records.some(record => record.target !== nav && !nav.contains(record.target))) schedule();
  });
  observer.observe(document.body, { childList: true, subtree: true });
  window.addEventListener('hashchange', schedule);
  mobile.addEventListener('change', schedule);
  function handlePageShow(event) {
    if (event.persisted) schedule();
  }
  function handlePageHide(event) {
    clearTimeout(timer);
    timer = 0;
    // Keep listeners for a page restored from the browser's back/forward cache.
    if (event.persisted) return;
    stopped = true;
    observer.disconnect();
    window.removeEventListener('hashchange', schedule);
    mobile.removeEventListener('change', schedule);
    window.removeEventListener('pagehide', handlePageHide);
    window.removeEventListener('pageshow', handlePageShow);
  }
  window.addEventListener('pagehide', handlePageHide);
  window.addEventListener('pageshow', handlePageShow);
  update();
})();
