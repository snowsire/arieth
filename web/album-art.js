/* Full-resolution album-cover viewer alongside the artist-photo player. */
(() => {
  'use strict';
  const selector = 'img.full-screen-player-image, img.fs-mobile-fullscreen-player-module-album-image';
  let scheduled;
  let dialog;
  let image;
  let status;
  let title;

  function ensureViewer() {
    if (dialog) return;
    dialog = document.createElement('dialog');
    dialog.id = 'snow-album-art-viewer';
    dialog.className = 'snow-album-art-viewer';
    dialog.setAttribute('aria-label', 'Full album cover');
    const panel = document.createElement('div');
    panel.className = 'snow-album-art-panel';
    const header = document.createElement('div');
    header.className = 'snow-album-art-header';
    title = document.createElement('strong');
    const close = document.createElement('button');
    close.type = 'button';
    close.textContent = 'Close';
    close.setAttribute('aria-label', 'Close full album cover');
    close.addEventListener('click', () => dialog.close());
    header.append(title, close);
    status = document.createElement('p');
    status.setAttribute('role', 'status');
    image = document.createElement('img');
    image.className = 'snow-full-album-cover';
    image.addEventListener('load', () => { status.hidden = true; image.hidden = false; });
    image.addEventListener('error', () => { status.hidden = false; status.textContent = 'No album artwork available.'; image.hidden = true; });
    panel.append(header, status, image);
    dialog.append(panel);
    dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
    dialog.addEventListener('cancel', event => { event.preventDefault(); dialog.close(); });
    dialog.addEventListener('close', () => image.removeAttribute('src'));
    document.body.append(dialog);
  }

  function fullCoverUrl(node) {
    if (!node?.src) return null;
    const url = new URL(node.src, location.href);
    if (url.origin !== location.origin) return null;
    const albumLink = document.querySelector('.media-player .song-album a[href^="#/library/albums/"]')
      || document.querySelector('.fs-shared-full-screen-player-metadata-module-metadata-container a[href^="#/library/albums/"]');
    const albumId = albumLink?.getAttribute('href')?.match(/^#\/library\/albums\/([^/]+)/)?.[1];
    if (url.pathname.includes('/getCoverArt')) {
      if (albumId) url.searchParams.set('id', 'al-' + decodeURIComponent(albumId));
      url.searchParams.set('size', '0');
    }
    return { url: url.href, album: albumLink?.textContent.trim() || 'Album art' };
  }

  function openCover(node) {
    const cover = fullCoverUrl(node);
    if (!cover) return;
    ensureViewer();
    title.textContent = cover.album;
    image.alt = cover.album + ' - full album cover';
    image.hidden = true;
    status.hidden = false;
    status.textContent = 'Loading cover…';
    image.src = cover.url;
    if (!dialog.open) dialog.showModal();
  }

  function liveImage(parent) {
    return [...parent.querySelectorAll(selector)]
      .filter(node => node.isConnected && node.src)
      .sort((a, b) => Number(getComputedStyle(b).opacity) - Number(getComputedStyle(a).opacity))[0];
  }

  function update() {
    for (const node of document.querySelectorAll(selector)) {
      const parent = node.parentElement;
      if (!parent || parent.querySelector(':scope > .snow-album-art-button')) continue;
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'snow-album-art-button';
      button.textContent = 'Album art';
      button.title = 'View full album cover';
      button.setAttribute('aria-label', 'View full album cover');
      button.setAttribute('aria-haspopup', 'dialog');
      button.addEventListener('click', event => {
        event.stopPropagation();
        openCover(liveImage(parent));
      });
      parent.append(button);
    }
  }

  document.addEventListener('click', event => {
    if (event.button === 0 && event.target.matches?.(selector)) openCover(event.target);
  });
  window.addEventListener('keydown', event => {
    if (dialog?.open && event.key === 'Escape') {
      event.preventDefault();
      event.stopImmediatePropagation();
      dialog.close();
    }
  }, true);
  function schedule() {
    if (scheduled) return;
    scheduled = setTimeout(() => { scheduled = null; update(); }, 80);
  }
  new MutationObserver(schedule).observe(document.documentElement, {
    childList: true, subtree: true, attributes: true, attributeFilter: ['src', 'class']
  });
  schedule();
})();
