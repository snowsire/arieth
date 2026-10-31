"""Build local web preferences and migrate the presentation once per revision."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent
theme_files = ['snow-music.css', 'crimson.css', 'polygon-atmosphere.css', 'live-lyrics.css', 'home-discovery.css']
settings = {
    'SERVER_NAME': 'Snow Music', 'SERVER_TYPE': 'navidrome', 'SERVER_LOCK': 'true',
    'REMOTE_URL': '', 'LEGACY_AUTHENTICATION': 'false', 'ANALYTICS_DISABLED': 'true',
    'FS_GENERAL_ACCENT': 'rgb(237, 48, 72)', 'FS_GENERAL_THEME': 'glassyDark',
    'FS_GENERAL_THEME_DARK': 'glassyDark', 'FS_GENERAL_USE_THEME_ACCENT_COLOR': 'false',
    'FS_GENERAL_ALBUM_BACKGROUND': 'true', 'FS_GENERAL_ALBUM_BACKGROUND_BLUR': '1.25',
    'FS_GENERAL_ARTIST_BACKGROUND': 'true', 'FS_GENERAL_ARTIST_BACKGROUND_BLUR': '0.25',
    'FS_GENERAL_FOLLOW_SYSTEM_THEME': 'false', 'FS_PLAYBACK_MEDIA_SESSION': 'true',
    'FS_PLAYBACK_TRANSCODE_ENABLED': 'true', 'FS_PLAYBACK_TRANSCODE_FORMAT': 'opus',
    'FS_PLAYBACK_TRANSCODE_BITRATE': '192', 'FS_LYRICS_FETCH': 'true',
    'FS_LYRICS_FOLLOW': 'true', 'FS_LYRICS_PREFER_LOCAL': 'true',
    'FS_LYRICS_LINE_LEAD_TIME_MS': '650', 'FS_LYRICS_DELAY_MS': '0',
    'FS_LYRICS_FOLLOW_SCROLL_ALIGNMENT': '-8', 'FS_LYRICS_ALIGNMENT': 'left',
    'FS_CSS_ENABLED': 'true',
    'FS_CSS_CONTENT': '\n\n'.join((root/name).read_text(encoding='utf-8') for name in theme_files),
}
lines = ['"use strict";', 'window.SERVER_URL = window.location.origin + "/navidrome";',
         'if (!localStorage.getItem("version")) localStorage.setItem("version", JSON.stringify("1.17.0"));']
lines += ['window.'+key+' = '+json.dumps(value)+';' for key,value in settings.items()]
lines.append(r'''
(() => {
  try {
    if (localStorage.getItem('snow_theme_revision') === 'crimson-5') return;
    const theme = JSON.parse(localStorage.getItem('store_settings') || '{"state":{},"version":34}');
    theme.state ??= {};
    theme.state.general = {...theme.state.general, theme:'glassyDark', themeDark:'glassyDark',
      followSystemTheme:false, accent:'rgb(237, 48, 72)', homeFeature:true, homeFeatureStyle:'single'};
    const order = ['recentlyPlayed','random','recentlyAdded','mostPlayed','playlists','genres','recentlyReleased'];
    theme.state.general.homeItems ??= order.map(id=>({id,disabled:false}));
    theme.state.general.homeItems.sort((a,b)=>(order.includes(a.id)?order.indexOf(a.id):order.length)-(order.includes(b.id)?order.indexOf(b.id):order.length));
    const items = theme.state.general.playerItems || [];
    for (const id of ['title','artist','album']) {
      if (!items.some(item=>item.id===id)) items.push({id,disabled:false});
    }
    theme.state.general.playerItems = items.map(item=>['title','artist','album'].includes(item.id)?{...item,disabled:false}:item);
    theme.state.lyrics = {...theme.state.lyrics,fetch:true,follow:true,preferLocalLyrics:true,
      alignment:'left',delayMs:0,lineLeadTimeMs:650,followScrollAlignment:-8};
    theme.state.lyricsDisplay = {...theme.state.lyricsDisplay,
      default:{...theme.state.lyricsDisplay?.default,fontSize:32,fontSizeUnsync:24,gap:28,gapUnsync:18,
        opacityNonActive:0.38,scaleNonActive:0.96,paddingLeft:0,paddingRight:2},
      sidebar:{...theme.state.lyricsDisplay?.sidebar,fontSize:22,fontSizeUnsync:20,gap:22,gapUnsync:16,
        opacityNonActive:0.42,scaleNonActive:0.98,paddingLeft:0,paddingRight:0}};
    theme.state.css = {...theme.state.css,enabled:true,content:window.FS_CSS_CONTENT};
    localStorage.setItem('store_settings',JSON.stringify(theme));
    const layout = JSON.parse(localStorage.getItem('store_app') || 'null');
    if(layout?.state?.sidebar) {
      layout.state.sidebar.leftWidth='280px';
      localStorage.setItem('store_app',JSON.stringify(layout));
    }
    const player = JSON.parse(localStorage.getItem('store_full_screen_player') || '{"state":{},"version":5}');
    player.state = {...player.state,playerItemAlignment:'left',titleDisplayType:'wrap',titleLineCount:2,
      dynamicBackground:true,dynamicIsImage:true,dynamicImageBlur:0.18,opacity:30};
    localStorage.setItem('store_full_screen_player',JSON.stringify(player));
    localStorage.setItem('snow_theme_revision','crimson-5');
  } catch (error) { console.warn('Snow Music theme preferences could not be saved.'); }
})();

// Home has its own revision so this update preserves playback and lyric choices.
(() => {
  try {
    if (localStorage.getItem('snow_home_revision') === 'discovery-1') return;
    const settings = JSON.parse(localStorage.getItem('store_settings') || '{"state":{},"version":34}');
    settings.state ??= {};
    settings.state.general ??= {};
    const order = ['playlists','genres','recentlyPlayed','random','mostPlayed','recentlyAdded','recentlyReleased'];
    const old = settings.state.general.homeItems || [];
    settings.state.general.homeItems = order.map(id => ({
      ...old.find(item => item.id === id), id,
      disabled: id === 'recentlyAdded' || id === 'recentlyReleased',
    })).concat(old.filter(item => !order.includes(item.id)));
    settings.state.general.homeFeature = true;
    settings.state.general.homeFeatureStyle = 'single';
    settings.state.css = {...settings.state.css, enabled:true, content:window.FS_CSS_CONTENT};
    localStorage.setItem('store_settings', JSON.stringify(settings));
    const app = JSON.parse(localStorage.getItem('store_app') || 'null');
    if (app?.state?.sidebar) {
      app.state.sidebar.leftWidth = '280px';
      localStorage.setItem('store_app', JSON.stringify(app));
    }
    localStorage.setItem('snow_home_revision', 'discovery-1');
  } catch { console.warn('Snow Music Home preferences could not be saved.'); }
})();

(() => {
  try {
    if (localStorage.getItem('snow_lyrics_revision') === 'responsive-1') return;
    const settings = JSON.parse(localStorage.getItem('store_settings') || '{"state":{},"version":34}');
    settings.state ??= {};
    settings.state.lyrics = {...settings.state.lyrics, lineLeadTimeMs:650};
    settings.state.css = {...settings.state.css, enabled:true, content:window.FS_CSS_CONTENT};
    localStorage.setItem('store_settings', JSON.stringify(settings));
    localStorage.setItem('snow_lyrics_revision', 'responsive-1');
  } catch { console.warn('Snow Music lyric responsiveness could not be saved.'); }
})();

(() => {
  try {
    if (localStorage.getItem('snow_lyrics_layout_revision') === 'compact-1') return;
    const settings = JSON.parse(localStorage.getItem('store_settings') || '{"state":{},"version":34}');
    settings.state ??= {};
    const display = settings.state.lyricsDisplay || {};
    settings.state.lyricsDisplay = {...display,
      default:{...display.default,fontSize:28,fontSizeUnsync:22,gap:12,gapUnsync:10},
      sidebar:{...display.sidebar,fontSize:20,fontSizeUnsync:18,gap:8,gapUnsync:8},
    };
    settings.state.css = {...settings.state.css,enabled:true,content:window.FS_CSS_CONTENT};
    localStorage.setItem('store_settings',JSON.stringify(settings));
    localStorage.setItem('snow_lyrics_layout_revision','compact-1');
  } catch { console.warn('Snow Music compact lyrics could not be saved.'); }
})();
''')
target = root/'web'/'settings.js'
temporary = target.with_suffix('.js.tmp')
temporary.write_text('\n'.join(lines)+'\n',encoding='utf-8')
temporary.replace(target)
print('Phone web preferences written; no credentials embedded')
