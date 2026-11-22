// Clean Modern Monochrome SVG Icons (Zero Emoji / Zero AI-Slop)
const PLAYER_SVG = {
    folder: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>`,
    folderParent: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 14 12 11 9 14"></polyline><line x1="12" y1="11" x2="12" y2="21"></line><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>`,
    folderSmall: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block; vertical-align:-1.5px; margin-right:3px;"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>`,
    home: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="crumb-icon"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>`,
    video: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="crumb-icon"><rect x="2" y="4" width="20" height="16" rx="2"></rect><polygon points="10 9 15 12 10 15 10 9" fill="currentColor"></polygon></svg>`,
    play: `<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><polygon points="6 4 20 12 6 20 6 4"></polygon></svg>`,
    minimize: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="12" x2="20" y2="12"></line></svg>`,
    restore: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 3 21 3 21 9"></polyline><polyline points="9 21 3 21 3 15"></polyline><line x1="21" y1="3" x2="14" y2="10"></line><line x1="3" y1="21" x2="10" y2="14"></line></svg>`,
    fullscreen: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"></path></svg>`,
    exitFullscreen: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3"></path></svg>`,
    subBgOn: `<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><rect x="3" y="3" width="18" height="18" rx="2"></rect></svg>`,
    subBgOff: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"></rect></svg>`
};

// Safe LocalStorage helpers for private browsing & iframe security
function safeGetItem(key, fallback = null) {
    try {
        const val = localStorage.getItem(key);
        return val !== null ? val : fallback;
    } catch (e) {
        return fallback;
    }
}

function safeSetItem(key, val) {
    try {
        localStorage.setItem(key, String(val));
    } catch (e) {}
}

function safeRemoveItem(key) {
    try {
        localStorage.removeItem(key);
    } catch (e) {}
}

// MyCloud Web Media Player Client App

let currentMode = 'folder'; // 'folder' or 'all'
let currentSort = safeGetItem('mycloud_sort_mode', 'name_asc');
let currentLayout = safeGetItem('mycloud_layout_v2', 'list'); // 'list' or 'grid' (default: list)
let currentDir = '';
let currentParentDir = null;
let currentDirs = [];
let currentVideos = [];
let activeVideo = null;

let parsedSubtitles = []; // array of { start: seconds, end: seconds, text: string, isTop: boolean }
let subtitleOffset = 0; // in seconds
let subScale = parseFloat(safeGetItem('mycloud_sub_scale', '1.0')) || 1.0;
let subBgEnabled = safeGetItem('mycloud_sub_bg', 'true') !== 'false';
let currentAvailableTracks = [];
let userManuallySelectedSubtitle = false;
let currentCueIndex = -1;

// DOM Elements
const videoGrid = document.getElementById('video-grid');
const searchInput = document.getElementById('search-input');
const clearSearchBtn = document.getElementById('clear-search');
const refreshBtn = document.getElementById('refresh-btn');
const statsBadge = document.getElementById('stats-badge');
const breadcrumbsContainer = document.getElementById('breadcrumbs');
const modeFolderBtn = document.getElementById('mode-folder-btn');
const modeAllBtn = document.getElementById('mode-all-btn');
const layoutGridBtn = document.getElementById('layout-grid-btn');
const layoutListBtn = document.getElementById('layout-list-btn');
const metaHideBtn = document.getElementById('meta-hide-btn');
const metaShowBtn = document.getElementById('meta-show-btn');
const sortSelect = document.getElementById('sort-select');

const playerModal = document.getElementById('player-modal');
const closePlayerBtn = document.getElementById('close-player-btn');
const playerTitle = document.getElementById('player-title');
const videoWrapper = document.getElementById('video-wrapper');
const videoPlayer = document.getElementById('video-player');
const subtitleBox = document.getElementById('subtitle-box');
const subSelect = document.getElementById('sub-select');
const customSubBtn = document.getElementById('custom-sub-btn');
const customSubInput = document.getElementById('custom-sub-input');
const fullscreenBtn = document.getElementById('fullscreen-btn');
const minimizeBtn = document.getElementById('minimize-btn');

const syncDisplay = document.getElementById('sync-display');
const syncResetBtn = document.getElementById('sync-reset');
const subBgToggleBtn = document.getElementById('sub-bg-toggle');
const fontDecreaseBtn = document.getElementById('font-decrease');
const fontIncreaseBtn = document.getElementById('font-increase');
const directLinkBtn = document.getElementById('direct-link-btn');
const downloadLink = document.getElementById('download-link');

const modalDialog = document.querySelector('.modal-dialog');
const modalHeader = document.querySelector('.modal-header');
const playerTitleText = document.getElementById('player-title-text');
const resizeHandle = document.getElementById('modal-resize-handle');
const prevVideoBtn = document.getElementById('prev-video-btn');
const nextVideoBtn = document.getElementById('next-video-btn');
const toastEl = document.getElementById('toast'); // OPT-5: cache once

let isDragging = false;
let dragStartX = 0;
let dragStartY = 0;
let initialDialogLeft = 0;
let initialDialogTop = 0;
let hasCustomPosition = false;

let isMinimized = false;
let preMinimizeGeometry = null; // { left, top, width, height } to restore to

function getModalViewportMargin() {
    return window.innerWidth <= 640 ? 6 : 10;
}

function centerModalDialog() {
    if (!modalDialog) return;
    modalDialog.style.margin = '0';
    const margin = getModalViewportMargin();
    const dialogWidth = modalDialog.offsetWidth || Math.min(window.innerWidth - margin * 2, 1050);
    const dialogHeight = modalDialog.offsetHeight || Math.min(window.innerHeight - margin * 2, 620);
    const maxLeft = Math.max(margin, window.innerWidth - dialogWidth - margin);
    const maxTop = Math.max(margin, window.innerHeight - dialogHeight - margin);
    const left = Math.max(margin, Math.min(maxLeft, Math.round((window.innerWidth - dialogWidth) / 2)));
    const top = Math.max(margin, Math.min(maxTop, Math.round((window.innerHeight - dialogHeight) / 2)));
    
    modalDialog.style.left = `${left}px`;
    modalDialog.style.top = `${top}px`;
    hasCustomPosition = false;
}

if (videoPlayer) {
    videoPlayer.addEventListener('loadedmetadata', () => {
        if (!hasCustomPosition) {
            centerModalDialog();
        }
    });
}

// Setup Draggable Modal Window via Pointer Events
if (modalHeader && modalDialog) {
    modalHeader.addEventListener('pointerdown', (e) => {
        if (e.target.closest('button, a, input, select')) return;
        
        isDragging = true;
        try { modalHeader.setPointerCapture(e.pointerId); } catch (err) {}
        
        const rect = modalDialog.getBoundingClientRect();
        initialDialogLeft = rect.left;
        initialDialogTop = rect.top;
        dragStartX = e.clientX;
        dragStartY = e.clientY;
        
        modalHeader.classList.add('dragging');
        e.preventDefault();
    });
    
    modalHeader.addEventListener('pointermove', (e) => {
        if (!isDragging) return;
        
        const deltaX = e.clientX - dragStartX;
        const deltaY = e.clientY - dragStartY;
        
        let newLeft = initialDialogLeft + deltaX;
        let newTop = initialDialogTop + deltaY;
        
        const dialogWidth = modalDialog.offsetWidth;
        const dialogHeight = modalDialog.offsetHeight;
        const margin = getModalViewportMargin();
        const minLeft = margin;
        const maxLeft = Math.max(margin, window.innerWidth - dialogWidth - margin);
        const minTop = margin;
        const maxTop = Math.max(margin, window.innerHeight - dialogHeight - margin);
        
        newLeft = Math.max(minLeft, Math.min(maxLeft, newLeft));
        newTop = Math.max(minTop, Math.min(maxTop, newTop));
        
        modalDialog.style.left = `${newLeft}px`;
        modalDialog.style.top = `${newTop}px`;
        hasCustomPosition = true;
    });
    
    const endDrag = (e) => {
        if (!isDragging) return;
        isDragging = false;
        modalHeader.classList.remove('dragging');
        try { modalHeader.releasePointerCapture(e.pointerId); } catch (err) {}
    };
    
    modalHeader.addEventListener('pointerup', endDrag);
    modalHeader.addEventListener('pointercancel', endDrag);
    
    modalHeader.addEventListener('dblclick', (e) => {
        if (e.target.closest('button, a, input, select')) return;
        centerModalDialog();
    });
}

// -------------------------------------------------------------
// Floating Player Resizing Engine & Size Persistence
// -------------------------------------------------------------
let isResizing = false;
let resizeStartX = 0;
let resizeStartY = 0;
let startDialogWidth = 0;
let startDialogHeight = 0;

const savedPlayerWidth = safeGetItem('mycloud_player_width');
const savedPlayerHeight = safeGetItem('mycloud_player_height');
if (window.innerWidth > 640 && modalDialog) {
    if (savedPlayerWidth) {
        const parsedW = parseFloat(savedPlayerWidth);
        if (isFinite(parsedW) && parsedW >= 320) {
            modalDialog.style.width = `${Math.min(parsedW, window.innerWidth - 20)}px`;
        }
    }
    if (savedPlayerHeight) {
        const parsedH = parseFloat(savedPlayerHeight);
        if (isFinite(parsedH) && parsedH >= 220) {
            modalDialog.style.height = `${Math.min(parsedH, window.innerHeight - 20)}px`;
        }
    }
}

if (resizeHandle && modalDialog) {
    resizeHandle.addEventListener('pointerdown', (e) => {
        isResizing = true;
        resizeStartX = e.clientX;
        resizeStartY = e.clientY;
        const rect = modalDialog.getBoundingClientRect();
        startDialogWidth = rect.width;
        startDialogHeight = rect.height;
        resizeHandle.classList.add('resizing');
        try { resizeHandle.setPointerCapture(e.pointerId); } catch (err) {}
        e.preventDefault();
        e.stopPropagation();
    });

    resizeHandle.addEventListener('pointermove', (e) => {
        if (!isResizing) return;
        const dx = e.clientX - resizeStartX;
        const dy = e.clientY - resizeStartY;
        
        const margin = getModalViewportMargin();
        const minW = Math.min(window.innerWidth <= 640 ? 280 : 380, window.innerWidth - margin * 2);
        const maxW = window.innerWidth - margin * 2;
        const minH = Math.min(220, window.innerHeight - margin * 2);
        const maxH = window.innerHeight - margin * 2;
        
        const newW = Math.round(Math.max(minW, Math.min(maxW, startDialogWidth + dx)));
        const newH = Math.round(Math.max(minH, Math.min(maxH, startDialogHeight + dy)));
        
        modalDialog.style.width = `${newW}px`;
        modalDialog.style.height = `${newH}px`;
        // localStorage is saved in endResize (pointerup) to avoid a write on every mouse-move event
    });

    const endResize = (e) => {
        if (!isResizing) return;
        isResizing = false;
        resizeHandle.classList.remove('resizing');
        document.body.classList.remove('is-resizing');
        try { resizeHandle.releasePointerCapture(e.pointerId); } catch (err) {}
        // Persist final size once drag ends (not on every pointermove)
        const fw = modalDialog.style.width;
        const fh = modalDialog.style.height;
        if (fw) safeSetItem('mycloud_player_width', fw);
        if (fh) safeSetItem('mycloud_player_height', fh);
    };

    resizeHandle.addEventListener('pointerup', endResize);
    resizeHandle.addEventListener('pointercancel', endResize);

    // Double-click resize handle to reset to default size
    resizeHandle.addEventListener('dblclick', (e) => {
        e.stopPropagation();
        modalDialog.style.width = '';
        modalDialog.style.height = '';
        safeRemoveItem('mycloud_player_width');
        safeRemoveItem('mycloud_player_height');
        centerModalDialog();
        showToast('창 크기가 기본값으로 초기화되었습니다.');
    });
}

// -------------------------------------------------------------
// Auto Next Video & Playlist Navigation
// -------------------------------------------------------------
function getActivePlaylist() {
    const sorted = getSortedVideos(currentVideos, currentSort) || [];
    const query = searchInput ? searchInput.value.toLowerCase().trim() : '';
    if (query && activeVideo) {
        const filtered = sorted.filter(v => currentMode === 'all'
            ? (v._searchKey || v.name.toLowerCase()).includes(query)
            : ((v._searchKey || v.name.toLowerCase()).includes(query))
        );
        if (filtered.some(v => v.rel_path === activeVideo.rel_path)) {
            return filtered;
        }
    }
    return sorted;
}

function playNextVideo() {
    const playlist = getActivePlaylist();
    if (!playlist || playlist.length === 0 || !activeVideo) return;
    
    const currentIndex = playlist.findIndex(v => v.rel_path === activeVideo.rel_path);
    if (currentIndex === -1) return;
    
    const nextIndex = currentIndex + 1;
    if (nextIndex < playlist.length) {
        const nextVideo = playlist[nextIndex];
        showToast(`다음 영상 자동 재생: ${nextVideo.name}`);
        openPlayer(encodeURIComponent(nextVideo.rel_path));
    } else {
        showToast('마지막 영상입니다.');
    }
}

function playPrevVideo() {
    const playlist = getActivePlaylist();
    if (!playlist || playlist.length === 0 || !activeVideo) return;
    
    const currentIndex = playlist.findIndex(v => v.rel_path === activeVideo.rel_path);
    if (currentIndex === -1) return;
    
    const prevIndex = currentIndex - 1;
    if (prevIndex >= 0) {
        const prevVideo = playlist[prevIndex];
        showToast(`이전 영상 재생: ${prevVideo.name}`);
        openPlayer(encodeURIComponent(prevVideo.rel_path));
    } else {
        showToast('첫 번째 영상입니다.');
    }
}

// Auto-play next video when current video ends!
videoPlayer.addEventListener('ended', () => {
    playNextVideo();
});

if (prevVideoBtn) prevVideoBtn.addEventListener('click', playPrevVideo);
if (nextVideoBtn) nextVideoBtn.addEventListener('click', playNextVideo);

function isIOSDevice() {
    const ua = navigator.userAgent || '';
    return /iPad|iPhone|iPod/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
}

function isFullscreen() {
    return !!(
        document.fullscreenElement ||
        document.webkitFullscreenElement ||
        (videoPlayer && videoPlayer.webkitDisplayingFullscreen)
    );
}

function enterFullscreenSafe(elem = videoPlayer) {
    // Reverted to fullscreening <video> itself (not the wrapper div). The
    // wrapper approach was tried to fix an Android status-bar white-line
    // artifact, but that turned out to be an OS/Chrome-level bug outside
    // page control - it didn't go away, while fullscreening the wrapper
    // broke the subtitle-display fullscreen check (double subtitles) and
    // left the native video controls' fullscreen/PiP buttons in a confused
    // state (they don't know about div-level fullscreen). Native
    // <video>-element fullscreen is what the platform actually supports well.
    const target = elem || videoPlayer;
    if (!target) return;
    if (target.requestFullscreen) {
        target.requestFullscreen().catch(() => {});
    } else if (target.webkitRequestFullscreen) {
        target.webkitRequestFullscreen();
    } else if (typeof target.webkitEnterFullscreen === 'function') {
        // iPhone Safari only supports HTMLVideoElement.webkitEnterFullscreen().
        // Enable native WebVTT subtitle track BEFORE handing off to AVPlayerViewController.
        syncNativeFullscreenTracks(true);
        try {
            target.webkitEnterFullscreen();
        } catch (e) {
            showToast('영상이 로드된 후 전체화면을 눌러주세요.');
        }
    }
}

function exitFullscreenSafe() {
    if (document.exitFullscreen) {
        document.exitFullscreen().catch(() => {});
    } else if (document.webkitExitFullscreen) {
        document.webkitExitFullscreen();
    } else if (videoPlayer && typeof videoPlayer.webkitExitFullscreen === 'function') {
        try { videoPlayer.webkitExitFullscreen(); } catch (e) {}
    }
}

// Fullscreen toggle on videoPlayer
function toggleFullscreen() {
    if (isFullscreen()) {
        exitFullscreenSafe();
    } else {
        if (isMinimized) restoreFromMinimize();
        enterFullscreenSafe(videoPlayer);
    }
}

// -------------------------------------------------------------
// Minimize: shrink the floating player to a small corner window while the
// video keeps playing (drag/prev/next/subtitles all keep working) - separate
// from browser fullscreen, and separate from closePlayer() which unloads
// the video entirely.
// -------------------------------------------------------------
function updateMinimizeBtnUI() {
    if (!minimizeBtn) return;
    minimizeBtn.innerHTML = isMinimized 
        ? `${PLAYER_SVG.restore} <span>복원</span>` 
        : `${PLAYER_SVG.minimize} <span>최소화</span>`;
    minimizeBtn.title = isMinimized ? '원래 크기로 복원 (단축키: M)' : '최소화 (영상은 계속 재생됨, 단축키: M)';
}

function enterMinimize() {
    if (!modalDialog || isMinimized) return;
    const rect = modalDialog.getBoundingClientRect();
    preMinimizeGeometry = {
        left: rect.left,
        top: rect.top,
        styleWidth: modalDialog.style.width,
        styleHeight: modalDialog.style.height,
        hadCustomPosition: hasCustomPosition
    };

    const margin = getModalViewportMargin();
    const mw = Math.min(340, window.innerWidth - margin * 2);

    modalDialog.classList.add('minimized');
    modalDialog.style.width = `${mw}px`;
    modalDialog.style.height = '';
    hasCustomPosition = true;
    isMinimized = true;
    updateMinimizeBtnUI();

    const mh = modalDialog.offsetHeight || Math.round(mw * 9 / 16) + 36;
    const left = Math.max(margin, window.innerWidth - mw - (window.innerWidth <= 640 ? margin : 16));
    const top = Math.max(margin, window.innerHeight - mh - (window.innerWidth <= 640 ? margin : 16));
    modalDialog.style.left = `${left}px`;
    modalDialog.style.top = `${top}px`;
}

function restoreFromMinimize() {
    if (!modalDialog || !isMinimized) return;
    modalDialog.classList.remove('minimized');
    const geom = preMinimizeGeometry;
    preMinimizeGeometry = null;
    isMinimized = false;
    updateMinimizeBtnUI();

    if (geom) {
        if (window.innerWidth <= 640) {
            modalDialog.style.width = '';
            modalDialog.style.height = '';
        } else {
            modalDialog.style.width = geom.styleWidth || '';
            modalDialog.style.height = geom.styleHeight || '';
        }
        if (geom.hadCustomPosition) {
            const margin = getModalViewportMargin();
            const dw = modalDialog.offsetWidth;
            const dh = modalDialog.offsetHeight;
            const maxLeft = Math.max(margin, window.innerWidth - dw - margin);
            const maxTop = Math.max(margin, window.innerHeight - dh - margin);
            modalDialog.style.left = `${Math.max(margin, Math.min(Math.round(geom.left), maxLeft))}px`;
            modalDialog.style.top = `${Math.max(margin, Math.min(Math.round(geom.top), maxTop))}px`;
            hasCustomPosition = true;
        } else {
            centerModalDialog();
        }
    } else {
        modalDialog.style.width = '';
        modalDialog.style.height = '';
        centerModalDialog();
    }
}

function toggleMinimize() {
    if (isFullscreen()) exitFullscreenSafe();
    if (isMinimized) restoreFromMinimize();
    else enterMinimize();
}

// -------------------------------------------------------------
// Subtitle Display Engine (Dual: High-Fidelity Overlay + Native TextTrack)
// -------------------------------------------------------------
function formatVttTime(sec) {
    if (!isFinite(sec) || sec < 0) sec = 0;
    const totalMs = Math.round(sec * 1000);
    const ms = totalMs % 1000;
    const totalSec = Math.floor(totalMs / 1000);
    const s = totalSec % 60;
    const totalMin = Math.floor(totalSec / 60);
    const m = totalMin % 60;
    const h = Math.floor(totalMin / 60);
    const pad = (n, len = 2) => String(n).padStart(len, '0');
    return `${pad(h)}:${pad(m)}:${pad(s)}.${pad(ms, 3)}`;
}

function buildVttText(cues) {
    let vtt = 'WEBVTT\n\n';
    // A cue's `end` can be Infinity (parseSAMI leaves the last subtitle of a
    // file open so it stays up until the video ends - see parseSAMI). That's
    // fine for updateSubtitleDisplay()'s plain `curTime <= c.end` comparison,
    // but formatVttTime(Infinity) computes NaN for every field but the hours
    // ("Infinity:NaN:NaN.NaN"), which corrupts that cue's WebVTT block for
    // the native <track> used in fullscreen. Clamp to the actual video
    // duration (or a large-but-finite fallback before duration is known).
    const finiteEndCap = (videoPlayer && isFinite(videoPlayer.duration) && videoPlayer.duration > 0)
        ? videoPlayer.duration
        : 359999; // ~100 hours - safely past any real video, just needs to be finite
    let cueIndex = 1;
    cues.forEach((c) => {
        if (!c || !c.text || !c.text.trim()) return;
        const start = Math.max(0, c.start + subtitleOffset);
        const rawEnd = c.end + subtitleOffset;
        const end = Math.max(start + 0.1, isFinite(rawEnd) ? rawEnd : finiteEndCap);
        // '&'/'<'/'>' have markup meaning inside a WebVTT cue payload (e.g.
        // <b>, <c>) - escape them so literal characters in the dialogue text
        // can't be misread as cue markup.
        const text = c.text
            .trim()
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
        if (!text) return;
        const posLine = c.isTop
            ? 'line:8% position:50% align:center'
            : 'line:90% position:50% align:center';
        vtt += `${cueIndex}\n${formatVttTime(start)} --> ${formatVttTime(end)} ${posLine}\n${text}\n\n`;
        cueIndex++;
    });
    return vtt;
}

let currentVttBlobUrl = null;
let activeSubtitleTrackInfo = null;

function getNativeHlsSubtitleTracks() {
    const list = [];
    if (!videoPlayer || !videoPlayer.textTracks) return list;
    for (let i = 0; i < videoPlayer.textTracks.length; i++) {
        const t = videoPlayer.textTracks[i];
        if (t.label !== 'WebPlayerSub' && (t.kind === 'subtitles' || t.kind === 'captions')) {
            list.push(t);
        }
    }
    return list;
}

function getWebPlayerTrack() {
    if (!videoPlayer || !videoPlayer.textTracks) return null;
    for (let i = 0; i < videoPlayer.textTracks.length; i++) {
        if (videoPlayer.textTracks[i].label === 'WebPlayerSub') {
            return videoPlayer.textTracks[i];
        }
    }
    return null;
}

function syncNativeFullscreenTracks(forceFullscreen = false) {
    if (!videoPlayer || !videoPlayer.textTracks) return;
    const isFs = forceFullscreen || isFullscreen();
    const wpTrack = getWebPlayerTrack();
    const hlsTracks = getNativeHlsSubtitleTracks();

    if (!isFs) {
        // Windowed mode: suppress ALL native browser captions so our custom DOM
        // subtitle overlay renders cleanly with zero double subtitles.
        if (wpTrack) wpTrack.mode = 'hidden';
        for (let i = 0; i < hlsTracks.length; i++) {
            hlsTracks[i].mode = 'disabled';
        }
        return;
    }

    // Native fullscreen mode:
    const subTurnedOff = subSelect && subSelect.value === '' && parsedSubtitles.length === 0;
    if (subTurnedOff) {
        if (wpTrack) wpTrack.mode = 'hidden';
        for (let i = 0; i < hlsTracks.length; i++) {
            hlsTracks[i].mode = 'disabled';
        }
        return;
    }

    // When native HLS subtitle tracks exist (injected via #EXT-X-MEDIA:TYPE=SUBTITLES
    // for iOS AVPlayerViewController), activate the matching native HLS track!
    if (hlsTracks.length > 0) {
        if (wpTrack) wpTrack.mode = 'hidden';
        let targetIdx = 0;
        if (activeSubtitleTrackInfo) {
            const wantExt = activeSubtitleTrackInfo.type === 'external';
            const wantLabel = (activeSubtitleTrackInfo.label || '').toLowerCase();
            for (let i = 0; i < hlsTracks.length; i++) {
                const tl = (hlsTracks[i].label || '').toLowerCase();
                if (wantExt && tl.includes('외부')) {
                    targetIdx = i;
                    break;
                }
                if (!wantExt && wantLabel && (tl === wantLabel || tl.includes(wantLabel) || wantLabel.includes(tl))) {
                    targetIdx = i;
                    break;
                }
            }
        }
        for (let i = 0; i < hlsTracks.length; i++) {
            hlsTracks[i].mode = (i === targetIdx) ? 'showing' : 'disabled';
        }
    } else if (wpTrack) {
        wpTrack.mode = 'showing';
    }
}

// Uses a real <track> element (HTTP WebVTT on iOS direct MP4, WebVTT blob on
// desktop/Android) for native fullscreen captions; on iOS HLS, native
// #EXT-X-MEDIA:TYPE=SUBTITLES tracks inside hls_master take over seamlessly.
function syncCuesToTextTrack() {
    if (!videoPlayer) return;
    const trackEl = document.getElementById('webplayer-native-track');
    if (!trackEl) return;

    if (!trackEl._hasLoadSyncListener) {
        trackEl.addEventListener('load', () => {
            syncNativeFullscreenTracks(false);
        });
        trackEl._hasLoadSyncListener = true;
    }

    if (currentVttBlobUrl) {
        URL.revokeObjectURL(currentVttBlobUrl);
        currentVttBlobUrl = null;
    }

    if (parsedSubtitles.length === 0) {
        trackEl.removeAttribute('src');
        syncNativeFullscreenTracks(false);
        return;
    }

    // On iOS Safari playing native HLS, AVPlayerViewController uses the native
    // #EXT-X-MEDIA:TYPE=SUBTITLES tracks from hls_master (blob: tracks are ignored
    // by AVPlayer and can cause duplicate/empty track entries in iOS CC menu).
    const nativeHlsTracks = getNativeHlsSubtitleTracks();
    if (isIOSDevice() && isHlsRemuxActive && nativeHlsTracks.length > 0) {
        trackEl.removeAttribute('src');
        syncNativeFullscreenTracks(false);
        return;
    }

    // On iOS Safari playing direct MP4 (non-HLS), use our server-side HTTP WebVTT
    // endpoint instead of blob: because AVPlayerViewController cannot read blob: URLs!
    if (isIOSDevice() && activeSubtitleTrackInfo && activeSubtitleTrackInfo.type === 'external' && activeSubtitleTrackInfo.subRel) {
        const offParam = subtitleOffset !== 0 ? `&offset=${encodeURIComponent(subtitleOffset.toFixed(2))}` : '';
        trackEl.src = `api.php?action=hls_sub_vtt&src=ext&sub=${encodeURIComponent(activeSubtitleTrackInfo.subRel)}${offParam}&ext=.vtt`;
        syncNativeFullscreenTracks(false);
        return;
    }

    const blob = new Blob([buildVttText(parsedSubtitles)], { type: 'text/vtt' });
    currentVttBlobUrl = URL.createObjectURL(blob);
    trackEl.src = currentVttBlobUrl;
    syncNativeFullscreenTracks(false);
}

function handleFullscreenSubtitleSync() {
    const isFs = isFullscreen();
    syncNativeFullscreenTracks(isFs);
    if (isFs) {
        if (subtitleBox) subtitleBox.style.display = "none";
    } else {
        updateSubtitleDisplay();
    }
    applySubtitleStyle();
}

function handleFullscreenChange() {
    const isFs = isFullscreen();

    // See the .video-wrapper:fullscreen rule in style.css for why this class
    // exists - it's a defensive backstop against a stray white sliver some
    // Android tablets show at the top of the screen in fullscreen video.
    document.documentElement.classList.toggle('is-fullscreen', isFs);

    // Update Fullscreen button text in modal header
    if (fullscreenBtn) {
        fullscreenBtn.innerHTML = isFs 
            ? `${PLAYER_SVG.exitFullscreen} <span>창모드</span>` 
            : `${PLAYER_SVG.fullscreen} <span>전체화면</span>`;
        fullscreenBtn.title = isFs ? '전체화면 해제 (단축키: F 또는 Esc)' : '전체화면 (단축키: F 또는 더블클릭)';
    }

    handleFullscreenSubtitleSync();
}

document.addEventListener('fullscreenchange', handleFullscreenChange);
document.addEventListener('webkitfullscreenchange', handleFullscreenChange);

if (videoPlayer) {
    // iPhone Safari fires webkitbeginfullscreen / webkitendfullscreen on <video>
    // instead of document fullscreenchange!
    videoPlayer.addEventListener('webkitbeginfullscreen', () => {
        handleFullscreenChange();
        // Re-assert native subtitle track after AVPlayerViewController finishes opening
        setTimeout(() => {
            if (isFullscreen()) syncNativeFullscreenTracks(true);
        }, 180);
    });
    videoPlayer.addEventListener('webkitendfullscreen', () => {
        handleFullscreenChange();
        setTimeout(() => {
            if (!isFullscreen()) handleFullscreenSubtitleSync();
        }, 120);
    });
    if (videoPlayer.textTracks && typeof videoPlayer.textTracks.addEventListener === 'function') {
        videoPlayer.textTracks.addEventListener('addtrack', () => {
            handleFullscreenSubtitleSync();
        });
    }
}

let lastDisplayedText = null;
let lastDisplayedPosTop = null;

function updateSubtitleDisplay() {
    if (!subtitleBox) return;

    // In fullscreen we show the native WebVTT track instead (see
    // handleFullscreenSubtitleSync) - don't also render the custom overlay
    // on top of it.
    if (isFullscreen()) {
        if (subtitleBox.style.display !== 'none') subtitleBox.style.display = 'none';
        return;
    }
    
    if (parsedSubtitles.length === 0) {
        if (lastDisplayedText !== '') {
            subtitleBox.style.display = 'none';
            subtitleBox.innerHTML = '';
            lastDisplayedText = '';
            lastDisplayedPosTop = false;
        }
        currentCueIndex = -1;
        return;
    }
    
    const curTime = videoPlayer.currentTime + subtitleOffset;
    let textToDisplay = '';
    let isTop = false;

    // parsedSubtitles is sorted by start time. Binary-search for the first
    // cue that could still plausibly be active (started within the last 30s
    // - real subtitle cues essentially never run longer than that, matching
    // the 20s forward-gap bound used below) instead of always linear-scanning
    // from index 0 - on a long episode with hundreds of cues, a naive scan
    // from the start does needless work on every single timeupdate tick once
    // playback is well past the beginning.
    const SEARCH_WINDOW_SEC = Math.max(60, (parsedSubtitles._maxFiniteDur || 60) + 5);
    let searchFloor = curTime - SEARCH_WINDOW_SEC;
    // parseSAMI leaves the very last cue of a file open (end: Infinity) so it
    // stays visible until the video ends - it can legitimately still be
    // active long after "30s since it started". Never prune past it, or it
    // silently disappears ~30s after its start instead of staying up.
    const lastCue = parsedSubtitles[parsedSubtitles.length - 1];
    if (lastCue && lastCue.end === Infinity && searchFloor > lastCue.start) {
        searchFloor = lastCue.start;
    }
    let lo = 0, hi = parsedSubtitles.length;
    while (lo < hi) {
        const mid = (lo + hi) >>> 1;
        if (parsedSubtitles[mid].start < searchFloor) lo = mid + 1;
        else hi = mid;
    }
    currentCueIndex = lo;

    for (let i = lo; i < parsedSubtitles.length; i++) {
        const c = parsedSubtitles[i];
        if (curTime < c.start) {
            if (c.start - curTime > 20) break;
            continue;
        }
        if (curTime <= c.end) {
            if (c.isTop) {
                isTop = true;
            }
            textToDisplay = textToDisplay ? textToDisplay + '\n' + c.text : c.text;
        }
    }

    if (textToDisplay) {
        if (textToDisplay !== lastDisplayedText || isTop !== lastDisplayedPosTop) {
            if (isTop) subtitleBox.classList.add('pos-top');
            else subtitleBox.classList.remove('pos-top');
            // c.text comes straight from the video's subtitle track - untrusted
            // input. Escape it before it ever touches innerHTML, then turn our
            // own newline joins into <br> (never the other way around).
            const safeHtml = escapeHtml(textToDisplay).replace(/\n/g, '<br>');
            subtitleBox.innerHTML = `<span>${safeHtml}</span>`;
            subtitleBox.style.display = 'block';
            lastDisplayedText = textToDisplay;
            lastDisplayedPosTop = isTop;
        }
    } else {
        if (lastDisplayedText !== '') {
            subtitleBox.style.display = 'none';
            subtitleBox.innerHTML = '';
            lastDisplayedText = '';
            lastDisplayedPosTop = false;
        }
    }
}

if (videoPlayer) {
    videoPlayer.addEventListener('timeupdate', updateSubtitleDisplay);
    videoPlayer.addEventListener('seeked', updateSubtitleDisplay);
    videoPlayer.addEventListener('seeking', updateSubtitleDisplay);
    videoPlayer.addEventListener('pause', updateSubtitleDisplay);
    videoPlayer.addEventListener('play', updateSubtitleDisplay);
}

// -------------------------------------------------------------
// 1. Fetch and Load Directory Data
// -------------------------------------------------------------
let currentLoadDataAbortController = null;
let currentLoadDataSeq = 0;

async function loadData(dir = currentDir, mode = currentMode) {
    currentMode = mode;
    currentDir = dir;
    
    if (modeFolderBtn && modeAllBtn) {
        modeFolderBtn.classList.toggle('active', currentMode === 'folder');
        modeAllBtn.classList.toggle('active', currentMode === 'all');
    }
    
    if (currentLoadDataAbortController) {
        try { currentLoadDataAbortController.abort(); } catch (e) {}
    }
    currentLoadDataAbortController = new AbortController();
    const signal = currentLoadDataAbortController.signal;
    const reqSeq = ++currentLoadDataSeq;

    videoGrid.innerHTML = '<div class="loading-spinner">항목을 불러오는 중입니다...</div>';
    
    try {
        let apiUrl = 'api.php';
        if (currentMode === 'all') {
            apiUrl += '?all=1';
        } else if (dir) {
            apiUrl += '?dir=' + encodeURIComponent(dir);
        }
        
        const resp = await fetch(apiUrl, { signal });
        if (reqSeq !== currentLoadDataSeq) return;
        if (!resp.ok) {
            videoGrid.innerHTML = `<div class="loading-spinner">서버 응답 오류 (HTTP ${resp.status})</div>`;
            return;
        }
        let data;
        try {
            data = await resp.json();
        } catch (e) {
            if (reqSeq !== currentLoadDataSeq) return;
            videoGrid.innerHTML = '<div class="loading-spinner">데이터 파싱 실패 (잘못된 응답 형식)</div>';
            return;
        }
        if (reqSeq !== currentLoadDataSeq) return;
        
        if (!data.success) {
            // data.error is server-controlled and currently always a static
            // string, but escaping here costs nothing and means a future
            // change on the PHP side can never turn this into an XSS sink.
            videoGrid.innerHTML = `<div class="loading-spinner">오류: ${escapeHtml(data.error)}</div>`;
            return;
        }
        
        currentVideos = data.videos || [];
        for (let i = 0; i < currentVideos.length; i++) {
            const v = currentVideos[i];
            v._searchKey = ((v.name || '') + ' ' + (v.folder || '')).toLowerCase();
        }
        currentDirs = data.dirs || [];
        for (let i = 0; i < currentDirs.length; i++) {
            const d = currentDirs[i];
            d._searchKey = (d.name || '').toLowerCase();
        }
        currentParentDir = data.parent_dir !== undefined ? data.parent_dir : null;
        // OPT-2: Invalidate sort caches — data has changed
        _sortedVideosCache = null;
        _sortedDirsCache = null;
        
        updateBreadcrumbs();
        updateStats();
        applySortAndRender();
        
        if (searchInput.value) {
            searchInput.value = '';
            clearSearchBtn.style.display = 'none';
        }
    } catch (err) {
        if (err && err.name === 'AbortError') return;
        if (reqSeq !== currentLoadDataSeq) return;
        videoGrid.innerHTML = `<div class="loading-spinner">서버 연결 실패: ${escapeHtml(err.message)}</div>`;
    }
}

function updateBreadcrumbs() {
    if (!breadcrumbsContainer) return;
    
    if (currentMode === 'all') {
        breadcrumbsContainer.innerHTML = `
            <span class="crumb" onclick="switchMode('folder', '')">${PLAYER_SVG.home} <span>Public</span></span>
            <span class="crumb-sep">›</span>
            <span class="crumb active">${PLAYER_SVG.video} <span>전체 영상 모아보기</span></span>
        `;
        return;
    }
    
    if (!currentDir) {
        breadcrumbsContainer.innerHTML = `<span class="crumb active" data-path="">${PLAYER_SVG.home} <span>Public</span></span>`;
        return;
    }
    
    const parts = currentDir.split('/');
    let html = `<span class="crumb" onclick="openFolder('')">${PLAYER_SVG.home} <span>Public</span></span>`;
    let accumulated = '';
    
    parts.forEach((p, idx) => {
        accumulated = accumulated ? accumulated + '/' + p : p;
        html += `<span class="crumb-sep">›</span>`;
        if (idx === parts.length - 1) {
            html += `<span class="crumb active">${escapeHtml(p)}</span>`;
        } else {
            html += `<span class="crumb" onclick="openFolder('${pathEncode(accumulated)}')">${escapeHtml(p)}</span>`;
        }
    });
    
    breadcrumbsContainer.innerHTML = html;
}

function updateStats() {
    if (currentMode === 'all') {
        const subCount = currentVideos.filter(v => v.subtitles && v.subtitles.length > 0).length;
        statsBadge.textContent = `전체 영상 ${currentVideos.length}개 (외부자막: ${subCount}개)`;
    } else {
        const dCount = currentDirs.length;
        const vCount = currentVideos.length;
        statsBadge.textContent = `폴더 ${dCount}개 · 동영상 ${vCount}개`;
    }
}

// -------------------------------------------------------------
// 2. Sorting & Grid Rendering
// -------------------------------------------------------------
// OPT-2: High-speed Intl.Collator instance — up to 27x faster than repeated
// localeCompare() calls with option objects inside large sorting arrays.
const _naturalCollator = (typeof Intl !== 'undefined' && Intl.Collator)
    ? new Intl.Collator(undefined, { numeric: true, sensitivity: 'base' })
    : null;
const naturalCompare = (a, b) => _naturalCollator ? _naturalCollator.compare(a, b) : a.localeCompare(b);

// Sort result cache — avoid re-sorting on every keystroke / re-render
// Keyed on (array identity, sortMode); invalidated when loadData fetches new data.
let _sortedVideosCache = null, _sortedVideosCacheMode = null, _sortedVideosCacheSrc = null;
let _sortedDirsCache = null, _sortedDirsCacheMode = null, _sortedDirsCacheSrc = null;

function getSortedVideos(videos, sortMode) {
    if (_sortedVideosCacheSrc === videos && _sortedVideosCacheMode === sortMode && _sortedVideosCache) {
        return _sortedVideosCache;
    }
    const copy = [...videos];
    let result;
    switch (sortMode) {
        case 'name_asc':
            result = copy.sort((a, b) => naturalCompare(a.name, b.name)); break;
        case 'name_desc':
            result = copy.sort((a, b) => naturalCompare(b.name, a.name)); break;
        case 'date_desc':
            result = copy.sort((a, b) => (b.mtime || 0) - (a.mtime || 0)); break;
        case 'date_asc':
            result = copy.sort((a, b) => (a.mtime || 0) - (b.mtime || 0)); break;
        case 'size_desc':
            result = copy.sort((a, b) => (b.size || 0) - (a.size || 0)); break;
        default:
            result = copy.sort((a, b) => naturalCompare(a.name, b.name));
    }
    _sortedVideosCache = result;
    _sortedVideosCacheMode = sortMode;
    _sortedVideosCacheSrc = videos;
    return result;
}

function getSortedDirs(dirs, sortMode) {
    if (_sortedDirsCacheSrc === dirs && _sortedDirsCacheMode === sortMode && _sortedDirsCache) {
        return _sortedDirsCache;
    }
    const copy = [...dirs];
    const result = (sortMode === 'name_desc')
        ? copy.sort((a, b) => naturalCompare(b.name, a.name))
        : copy.sort((a, b) => naturalCompare(a.name, b.name));
    _sortedDirsCache = result;
    _sortedDirsCacheMode = sortMode;
    _sortedDirsCacheSrc = dirs;
    return result;
}

function applySortAndRender() {
    const query = searchInput ? searchInput.value.toLowerCase().trim() : '';
    
    let targetVideos = getSortedVideos(currentVideos, currentSort);
    let targetDirs = getSortedDirs(currentDirs, currentSort);
    
    if (query) {
        if (currentMode === 'all') {
            targetVideos = targetVideos.filter(v => (v._searchKey || v.name.toLowerCase()).includes(query));
            renderGrid([], targetVideos);
            return;
        } else {
            targetDirs = targetDirs.filter(d => (d._searchKey || d.name.toLowerCase()).includes(query));
            targetVideos = targetVideos.filter(v => (v._searchKey || v.name.toLowerCase()).includes(query));
            
            if (targetDirs.length === 0 && targetVideos.length === 0) {
                // Plain button + addEventListener (no inline onclick) - escapeHtml()
                // only neutralizes &/</>, not quotes, so interpolating `query`
                // straight into an onclick="...'...'" attribute would let a
                // search string containing a single quote break out of it.
                videoGrid.innerHTML = `
                    <div class="loading-spinner">
                        현재 폴더에 '<strong>${escapeHtml(query)}</strong>' 검색 결과가 없습니다.<br><br>
                        <button type="button" class="btn btn-secondary search-all-fallback-btn">
                            전체 영상 모아보기에서 검색하기
                        </button>
                    </div>
                `;
                const searchAllBtn = videoGrid.querySelector('.search-all-fallback-btn');
                if (searchAllBtn) {
                    searchAllBtn.addEventListener('click', async () => {
                        // loadData() (called by switchMode) clears searchInput
                        // itself once it resolves, so setting the query before
                        // it finishes just gets wiped out - wait for it first.
                        await switchMode('all');
                        searchInput.value = query;
                        applySortAndRender();
                    });
                }
                return;
            }
        }
    }
    
    renderGrid(targetDirs, targetVideos);
}

if (sortSelect) {
    sortSelect.value = currentSort;
    sortSelect.addEventListener('change', () => {
        currentSort = sortSelect.value;
        safeSetItem('mycloud_sort_mode', currentSort);
        applySortAndRender();
    });
}

function setLayoutMode(mode) {
    currentLayout = mode;
    safeSetItem('mycloud_layout_v2', mode);
    if (layoutGridBtn && layoutListBtn) {
        layoutGridBtn.classList.toggle('active', mode === 'grid');
        layoutListBtn.classList.toggle('active', mode === 'list');
    }
    if (videoGrid) {
        videoGrid.classList.toggle('list-view', mode === 'list');
    }
}

if (layoutGridBtn) {
    layoutGridBtn.addEventListener('click', () => setLayoutMode('grid'));
}
if (layoutListBtn) {
    layoutListBtn.addEventListener('click', () => setLayoutMode('list'));
}

// File Date and Size Visibility Toggle (Default: Hidden)
let showFileMeta = safeGetItem('mycloud_show_file_meta', 'false') === 'true'; // defaults to false (hidden)

function applyMetaVisibility() {
    if (showFileMeta) {
        videoGrid.classList.remove('hide-file-meta');
        if (metaHideBtn) metaHideBtn.classList.remove('active');
        if (metaShowBtn) metaShowBtn.classList.add('active');
    } else {
        videoGrid.classList.add('hide-file-meta');
        if (metaHideBtn) metaHideBtn.classList.add('active');
        if (metaShowBtn) metaShowBtn.classList.remove('active');
    }
}

// Initial apply
applyMetaVisibility();

if (metaHideBtn) {
    metaHideBtn.addEventListener('click', () => {
        showFileMeta = false;
        safeSetItem('mycloud_show_file_meta', 'false');
        applyMetaVisibility();
        showToast('파일 날짜 및 용량을 숨겼습니다.');
    });
}
if (metaShowBtn) {
    metaShowBtn.addEventListener('click', () => {
        showFileMeta = true;
        safeSetItem('mycloud_show_file_meta', 'true');
        applyMetaVisibility();
        showToast('파일 날짜 및 용량을 표시합니다.');
    });
}

function renderGrid(dirs, videos) {
    if ((!dirs || dirs.length === 0) && (!videos || videos.length === 0)) {
        let emptyHtml = '<div class="loading-spinner">표시할 항목이 없습니다.';
        if (currentMode === 'folder' && currentParentDir !== null) {
            emptyHtml += `<br><br><button onclick="openFolder('${pathEncode(currentParentDir)}')" class="btn btn-secondary">상위 폴더로 이동</button>`;
        }
        emptyHtml += '</div>';
        videoGrid.innerHTML = emptyHtml;
        return;
    }
    
    let html = '';
    
    if (currentMode === 'folder' && currentParentDir !== null) {
        html += `
            <div class="folder-card parent-card" onclick="openFolder('${pathEncode(currentParentDir)}')">
                <div class="folder-thumbnail">
                    <span class="card-folder-badge">상위</span>
                    <div class="folder-icon">${PLAYER_SVG.folderParent}</div>
                </div>
                <div class="card-content">
                    <div class="list-main-col">
                        <div class="card-title">.. (상위 폴더로 이동)</div>
                    </div>
                    <div class="list-sub-col">
                        <div class="card-meta">
                            <span>상위 폴더로 이동</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    if (dirs && dirs.length > 0) {
        dirs.forEach(d => {
            let metaDesc = '폴더';
            if (d.video_count > 0 && d.subdir_count > 0) {
                metaDesc = `영상 ${d.video_count}개 · 하위 폴더 ${d.subdir_count}개`;
            } else if (d.video_count > 0) {
                metaDesc = `영상 ${d.video_count}개`;
            } else if (d.subdir_count > 0) {
                metaDesc = `하위 폴더 ${d.subdir_count}개`;
            }
            
            html += `
                <div class="folder-card" onclick="openFolder('${pathEncode(d.rel_path)}')">
                    <div class="folder-thumbnail">
                        <span class="card-folder-badge">폴더</span>
                        <div class="folder-icon">${PLAYER_SVG.folder}</div>
                    </div>
                    <div class="card-content">
                        <div class="list-main-col">
                            <div class="card-title" title="${escapeHtml(d.name)}">${escapeHtml(d.name)}</div>
                        </div>
                        <div class="list-sub-col">
                            <div class="card-meta">
                                <span>${metaDesc}</span>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
    }
    
    if (videos && videos.length > 0) {
        videos.forEach(v => {
            let badgesHtml = '';
            if (v.subtitles && v.subtitles.length > 0) {
                badgesHtml = v.subtitles.map(s => `<span class="badge badge-${s.ext}">${s.ext.toUpperCase()}</span>`).join('');
            } else if (v.ext === 'mkv' || v.ext === 'mp4') {
                badgesHtml = '<span class="badge badge-srt">내장자막지원</span>';
            } else {
                badgesHtml = '<span class="badge badge-none">자막없음</span>';
            }
            
            const folderTag = (currentMode === 'all' && v.folder)
                ? `<div class="card-folder-path" title="${escapeHtml(v.folder)}">${PLAYER_SVG.folderSmall} <span>${escapeHtml(v.folder)}</span></div>`
                : '';
                
            html += `
                <div class="video-card" onclick="openPlayer('${pathEncode(v.rel_path)}')">
                    <div class="card-thumbnail">
                        <span class="card-format-badge">${v.ext}</span>
                        <div class="play-icon-overlay">${PLAYER_SVG.play}</div>
                    </div>
                    <div class="card-content">
                        <div class="list-main-col">
                            ${folderTag}
                            <div class="card-title" title="${escapeHtml(v.name)}">${escapeHtml(v.name)}</div>
                        </div>
                        <div class="list-sub-col">
                            <div class="card-meta">
                                <span class="meta-size">${v.size_formatted}</span>
                                <span class="meta-date">${(v.mtime_formatted || '').split(' ')[0]}</span>
                            </div>
                            <div class="card-badges">
                                ${badgesHtml}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
    }
    
    videoGrid.innerHTML = html;
    applyMetaVisibility();
}

window.openFolder = function(encodedPath) {
    const path = decodeURIComponent(encodedPath);
    loadData(path, 'folder');
};

window.switchMode = function(mode, dir = '') {
    return loadData(dir, mode);
};

if (modeFolderBtn) {
    modeFolderBtn.addEventListener('click', () => switchMode('folder', currentDir));
}
if (modeAllBtn) {
    modeAllBtn.addEventListener('click', () => switchMode('all', ''));
}

// -------------------------------------------------------------
// 3. Open Video Player, On-Demand HLS Remuxing & Subtitle Management
// -------------------------------------------------------------
const btnHlsRemux = document.getElementById('btn-hls-remux');
const hlsRemuxText = document.getElementById('hls-remux-text');
let activeHlsInstance = null;
let isHlsRemuxActive = false;
let hlsAutoFallbackAttempted = false;
let _hlsScriptPromise = null;
let activeNativeMetaHandler = null;

function browserNeedsMkvRemux() {
    const ua = navigator.userAgent || '';
    const isIOS = /iPad|iPhone|iPod/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    const isSafari = /^((?!chrome|android|crios|fxios|edg).)*safari/i.test(ua);
    const isFirefox = /firefox|fxios/i.test(ua);
    return isIOS || isSafari || isFirefox;
}

function destroyHlsInstance() {
    if (activeNativeMetaHandler && videoPlayer) {
        videoPlayer.removeEventListener('loadedmetadata', activeNativeMetaHandler);
        activeNativeMetaHandler = null;
    }
    if (activeHlsInstance) {
        try { activeHlsInstance.destroy(); } catch (e) {}
        activeHlsInstance = null;
    }
}

function loadHlsLibrary() {
    if (window.Hls) return Promise.resolve(window.Hls);
    if (_hlsScriptPromise) return _hlsScriptPromise;
    _hlsScriptPromise = new Promise((resolve, reject) => {
        const s = document.createElement('script');
        s.src = 'hls.light.min.js?v=20261122_1';
        s.onload = () => resolve(window.Hls);
        s.onerror = () => {
            _hlsScriptPromise = null;
            reject(new Error('HLS 라이브러리를 불러올 수 없습니다.'));
        };
        document.head.appendChild(s);
    });
    return _hlsScriptPromise;
}

function updateHlsButtonUI(video) {
    if (!btnHlsRemux) return;
    const isMkv = video && (video.ext || '').toLowerCase() === 'mkv';
    btnHlsRemux.style.display = isMkv ? 'inline-flex' : 'none';
    if (isHlsRemuxActive) {
        btnHlsRemux.style.borderColor = 'var(--accent)';
        btnHlsRemux.style.color = 'var(--accent)';
        if (hlsRemuxText) hlsRemuxText.textContent = 'HLS ON';
    } else {
        btnHlsRemux.style.borderColor = '';
        btnHlsRemux.style.color = '';
        if (hlsRemuxText) hlsRemuxText.textContent = 'HLS';
    }
}

async function attachVideoSource(video, useHls, resumeTime = 0) {
    if (!video || !videoPlayer) return;
    destroyHlsInstance();
    isHlsRemuxActive = Boolean(useHls);
    updateHlsButtonUI(video);

    if (!isHlsRemuxActive) {
        videoPlayer.src = video.url;
        if (resumeTime > 0) {
            const onMeta = () => {
                videoPlayer.removeEventListener('loadedmetadata', onMeta);
                try { videoPlayer.currentTime = resumeTime; } catch (e) {}
            };
            videoPlayer.addEventListener('loadedmetadata', onMeta);
        }
        videoPlayer.play().catch(() => {});
        return;
    }

    const hlsUrl = `api.php?action=hls_master&video=${encodeURIComponent(video.rel_path)}&ext=.m3u8`;
    const nativeHls = videoPlayer.canPlayType('application/vnd.apple.mpegurl');
    if (nativeHls === 'probably' || nativeHls === 'maybe') {
        videoPlayer.preload = 'auto';
        videoPlayer.src = hlsUrl;
        if (resumeTime > 0) {
            const onMeta = () => {
                videoPlayer.removeEventListener('loadedmetadata', onMeta);
                if (activeNativeMetaHandler === onMeta) activeNativeMetaHandler = null;
                if (activeVideo !== video) return;
                try { videoPlayer.currentTime = resumeTime; } catch (e) {}
                if (videoPlayer.paused) videoPlayer.play().catch(() => {});
            };
            activeNativeMetaHandler = onMeta;
            videoPlayer.addEventListener('loadedmetadata', onMeta);
        }
        videoPlayer.play().catch(() => {});
        return;
    }

    try {
        const HlsLib = await loadHlsLibrary();
        if (activeVideo !== video) return;
        if (HlsLib && HlsLib.isSupported()) {
            const hls = new HlsLib({
                maxBufferLength: 12,
                maxMaxBufferLength: 20,
                backBufferLength: 15,
                startPosition: resumeTime > 0 ? resumeTime : -1
            });
            activeHlsInstance = hls;
            hls.loadSource(hlsUrl);
            hls.attachMedia(videoPlayer);
            hls.on(HlsLib.Events.MANIFEST_PARSED, () => {
                if (activeVideo !== video) return;
                videoPlayer.play().catch(() => {});
            });
            hls.on(HlsLib.Events.ERROR, (evt, data) => {
                if (!data || !data.fatal) return;
                if (data.type === HlsLib.ErrorTypes.NETWORK_ERROR) {
                    hls.startLoad();
                } else if (data.type === HlsLib.ErrorTypes.MEDIA_ERROR) {
                    hls.recoverMediaError();
                } else {
                    destroyHlsInstance();
                    showToast('실시간 HLS 리먹싱 스트림 오류가 발생했습니다.', 4000);
                }
            });
        } else {
            showToast('이 브라우저는 HLS 스트리밍을 지원하지 않습니다.', 4000);
        }
    } catch (e) {
        showToast(e.message || 'HLS 리먹싱 초기화 실패', 4000);
    }
}

if (btnHlsRemux) {
    btnHlsRemux.addEventListener('click', () => {
        if (!activeVideo) return;
        const pos = (videoPlayer && isFinite(videoPlayer.currentTime)) ? videoPlayer.currentTime : 0;
        const nextMode = !isHlsRemuxActive;
        hlsAutoFallbackAttempted = true;
        showToast(nextMode ? '실시간 HLS 리먹싱 모드로 전환합니다...' : '원본 직접 재생 모드로 전환합니다...');
        attachVideoSource(activeVideo, nextMode, pos);
    });
}

window.openPlayer = async function(encodedRelPath) {
    const relPath = decodeURIComponent(encodedRelPath);
    const video = currentVideos.find(v => v.rel_path === relPath);
    if (!video) return;
    
    activeVideo = video;
    hlsAutoFallbackAttempted = false;
    userManuallySelectedSubtitle = false;
    document.title = `${video.name} - MyCloud Media Player`;
    if (playerTitleText) {
        playerTitleText.textContent = video.name;
    } else if (playerTitle) {
        playerTitle.textContent = video.name;
    }
    if (downloadLink) downloadLink.href = video.url;
    // Activate modal BEFORE attaching media & calling play() so <video> is visible
    // in the render tree during the user gesture (required by iOS Safari).
    playerModal.classList.add('active');
    applySubtitleStyle();

    const isMkv = (video.ext || '').toLowerCase() === 'mkv';
    const startWithHls = isMkv && browserNeedsMkvRemux();
    if (startWithHls) {
        showToast('실시간 HLS 리먹싱 모드로 재생합니다.');
    }
    attachVideoSource(video, startWithHls, 0);
    
    clearSubtitles();
    
    // 1. Add external subtitles to list
    currentAvailableTracks = [];
    if (video.subtitles && video.subtitles.length > 0) {
        video.subtitles.forEach(s => {
            const subRel = (video.folder ? `${video.folder}/` : '') + s.filename;
            currentAvailableTracks.push({
                type: 'external',
                label: `[외부-${s.ext.toUpperCase()}] ${s.filename}`,
                url: s.url,
                subRel: subRel,
                ext: s.ext,
                lang: s.ext
            });
        });
    }
    
    renderSubtitleDropdown(currentAvailableTracks, '내장 자막 확인 중...');
    
    if (!isMinimized && window.innerWidth <= 640 && modalDialog) {
        modalDialog.style.width = '';
        modalDialog.style.height = '';
    }
    if (!hasCustomPosition) {
        centerModalDialog();
        requestAnimationFrame(() => centerModalDialog());
    }
    
    setupMediaSession(video);
    
    // 2. Probe embedded subtitle tracks with AbortController, client cache, and race condition guard
    if (currentProbeAbortController) {
        currentProbeAbortController.abort();
    }
    if (currentSubAbortController) {
        currentSubAbortController.abort();
    }

    const probeCacheKey = `${video.rel_path}:${video.mtime || ''}`;
    let embeddedSubs = probeMemoryCache.get(probeCacheKey);

    if (!embeddedSubs) {
        currentProbeAbortController = new AbortController();
        const probeSignal = currentProbeAbortController.signal;
        
        try {
            const probeResp = await fetch(`api.php?action=probe_subs&video=${encodeURIComponent(video.rel_path)}`, { signal: probeSignal });
            if (!probeResp.ok) return;
            const probeData = await probeResp.json();
            
            // Guard against race condition: ensure this response matches active video
            if (!activeVideo || activeVideo.rel_path !== video.rel_path) return;
            
            if (probeData.success && Array.isArray(probeData.subtitles)) {
                embeddedSubs = probeData.subtitles;
                probeMemoryCache.set(probeCacheKey, embeddedSubs);
            }
        } catch (e) {
            if (e.name !== 'AbortError') {
                console.warn('Subtitle probe failed:', e);
            }
        }
    }

    if (!activeVideo || activeVideo.rel_path !== video.rel_path) return;
    if (embeddedSubs && embeddedSubs.length > 0) {
        embeddedSubs.forEach(emb => {
            currentAvailableTracks.push({
                type: 'embedded',
                label: emb.label,
                streamId: emb.stream_id,
                codec: emb.codec,
                lang: emb.lang,
                relPath: video.rel_path
            });
        });
    }
    
    if (!activeVideo || activeVideo.rel_path !== video.rel_path) return;
    const prevSelectedVal = subSelect.value;
    renderSubtitleDropdown(currentAvailableTracks, null);
    if (userManuallySelectedSubtitle && prevSelectedVal !== '__loading__') {
        subSelect.value = prevSelectedVal;
    }
    
    // 3. Auto-select Korean subtitle if available (unless user manually picked one)
    if (!userManuallySelectedSubtitle && currentAvailableTracks.length > 0) {
        // 우선순위 1: lang='kor' 또는 'ko' (내장 한국어)
        let bestTrack = currentAvailableTracks.find(t =>
            t.lang === 'kor' || t.lang === 'ko'
        );
        // 우선순위 2: label에 '한국어' 포함 (lang 코드가 다를 경우 대비)
        if (!bestTrack) {
            bestTrack = currentAvailableTracks.find(t => t.label.includes('한국어'));
        }
        // 우선순위 3: lang='korean'  (비표준 태그 대비)
        if (!bestTrack) {
            bestTrack = currentAvailableTracks.find(t => t.lang === 'korean');
        }
        // 폴백: 첫 번째 트랙 (한국어 없을 때만)
        if (!bestTrack) {
            bestTrack = currentAvailableTracks[0];
        }
        const bestIdx = currentAvailableTracks.indexOf(bestTrack);
        subSelect.value = String(bestIdx);
        loadSelectedTrack(bestTrack);
    }
};

function renderSubtitleDropdown(tracks, loadingNotice) {
    subSelect.innerHTML = '';
    
    const offOpt = document.createElement('option');
    offOpt.value = '';
    offOpt.textContent = '자막 없음 (끄기)';
    subSelect.appendChild(offOpt);
    
    if (loadingNotice) {
        const noticeOpt = document.createElement('option');
        noticeOpt.value = '__loading__';
        noticeOpt.disabled = true;
        noticeOpt.textContent = loadingNotice;
        subSelect.appendChild(noticeOpt);
    }
    
    tracks.forEach((t, idx) => {
        const opt = document.createElement('option');
        opt.value = String(idx);
        opt.textContent = t.label;
        subSelect.appendChild(opt);
    });
}

const subtitleMemoryCache = new Map();
const probeMemoryCache = new Map();
let currentProbeAbortController = null;
let currentSubAbortController = null;

async function loadSelectedTrack(track) {
    clearSubtitles();
    if (!track) return;
    activeSubtitleTrackInfo = track;
    // Snapshot which video this load was requested for. loadSelectedTrack is
    // async (and the cache branch below can still interleave with a fast
    // prev/next click via microtask ordering) - without this check, a track
    // load that started for the video the user just navigated away from can
    // land after a newer call and paint the wrong video's subtitles.
    const requestedVideo = activeVideo;

    const cacheKey = `${track.relPath || track.url}:${track.streamId !== undefined ? track.streamId : ''}`;
    if (subtitleMemoryCache.has(cacheKey)) {
        const cached = subtitleMemoryCache.get(cacheKey);
        if (activeVideo !== requestedVideo) return;
        parsedSubtitles = cached;
        syncCuesToTextTrack();
        updateSubtitleDisplay();
        showToast(`자막 즉시 로드 완료 (${parsedSubtitles.length}개 자막)`);
        return;
    }
    
    if (currentSubAbortController) {
        currentSubAbortController.abort();
    }
    currentSubAbortController = new AbortController();
    const currentSignal = currentSubAbortController.signal;
    
    try {
        const isEmbedded = (track.type === 'embedded');
        const isAss = (track.codec && track.codec.toLowerCase() === 'ass') || 
                      (track.ext && (track.ext.toLowerCase() === 'ass' || track.ext.toLowerCase() === 'ssa'));
        const isSami = track.ext && (track.ext.toLowerCase() === 'smi' || track.ext.toLowerCase() === 'sami');
        
        showToast(`[${track.label}] 실시간 읽는 중...`);
        
        const url = isEmbedded
            ? `api.php?action=stream_sub&video=${encodeURIComponent(track.relPath)}&stream=${track.streamId}&codec=${encodeURIComponent(track.codec)}`
            : track.url;
            
        const resp = await fetch(url, { signal: currentSignal });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        
        // All external subtitle files (!isEmbedded) must pass through decodeSubtitleBuffer()
        // so EUC-KR (CP949) and UTF-16LE/BE external .srt/.ass/.smi/.vtt files decode properly.
        if (!resp.body || !isEmbedded || isSami) {
            const buffer = await resp.arrayBuffer();
            if (activeVideo !== requestedVideo) return;
            const text = decodeSubtitleBuffer(buffer);
            if (isAss) parsedSubtitles = parseASS(text);
            else if (isSami) parsedSubtitles = parseSAMI(text);
            else parsedSubtitles = parseSRT(text);

            if (parsedSubtitles.length > 0) {
                subtitleMemoryCache.set(cacheKey, parsedSubtitles);
            }
            syncCuesToTextTrack();
            updateSubtitleDisplay();
            showToast(`자막 로드 완료 (${parsedSubtitles.length}개 자막)`);
            return;
        }
        
        const reader = resp.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let rawBuffer = '';
        let lastReportedCount = 0;
        let lastParseTime = 0;
        let updateTimer = null;
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            if (activeVideo !== requestedVideo) return;
            rawBuffer += decoder.decode(value, { stream: true });
            
            const now = Date.now();
            if (lastReportedCount === 0 || (now - lastParseTime) >= 220) {
                lastParseTime = now;
                if (isAss) {
                    parsedSubtitles = parseASS(rawBuffer);
                } else {
                    parsedSubtitles = parseSRT(rawBuffer);
                }
                
                if (parsedSubtitles.length !== lastReportedCount) {
                    lastReportedCount = parsedSubtitles.length;
                    if (isFullscreen()) {
                        syncCuesToTextTrack();
                    }
                    updateSubtitleDisplay();
                    
                    if (!updateTimer) {
                        updateTimer = setTimeout(() => {
                            updateTimer = null;
                            if (parsedSubtitles.length > 0 && !currentSignal.aborted) {
                                showToast(`자막 실시간 읽는 중... (${parsedSubtitles.length}개)`);
                            }
                        }, 800);
                    }
                }
            }
        }
        
        if (activeVideo !== requestedVideo) return;
        rawBuffer += decoder.decode();
        if (isAss) parsedSubtitles = parseASS(rawBuffer);
        else parsedSubtitles = parseSRT(rawBuffer);

        if (parsedSubtitles.length > 0) {
            subtitleMemoryCache.set(cacheKey, parsedSubtitles);
        }

        if (updateTimer) {
            clearTimeout(updateTimer);
            updateTimer = null;
        }

        syncCuesToTextTrack();
        updateSubtitleDisplay();
        showToast(`자막 로드 완료 (${parsedSubtitles.length}개 자막)`);
        
    } catch (err) {
        if (err.name === 'AbortError') return;
        console.error('Failed to load subtitle:', err);
        showToast(`자막 로드 실패: ${err.message}`);
    }
}

function clearSubtitles() {
    activeSubtitleTrackInfo = null;
    if (currentSubAbortController) {
        try { currentSubAbortController.abort(); } catch (e) {}
        currentSubAbortController = null;
    }
    parsedSubtitles = [];
    currentCueIndex = -1;
    // Without resetting these, updateSubtitleDisplay()'s change-detection can
    // compare the *new* track's first cue text against stale text left over
    // from the *previous* track and (on a coincidental match) skip
    // re-rendering - re-selecting the same subtitle track then does nothing
    // visible until the text actually changes.
    lastDisplayedText = '';
    lastDisplayedPosTop = false;
    if (subtitleBox) {
        subtitleBox.innerHTML = '';
        subtitleBox.style.display = 'none';
    }
    subtitleOffset = 0;
    if (syncDisplay) syncDisplay.textContent = '0.0s';
    
    if (currentVttBlobUrl) {
        URL.revokeObjectURL(currentVttBlobUrl);
        currentVttBlobUrl = null;
    }
    const nativeTrackEl = document.getElementById('webplayer-native-track');
    if (nativeTrackEl) {
        nativeTrackEl.removeAttribute('src');
    }
    if (videoPlayer && videoPlayer.textTracks) {
        for (let i = 0; i < videoPlayer.textTracks.length; i++) {
            const track = videoPlayer.textTracks[i];
            if (track.label === 'WebPlayerSub' && track.cues) {
                while (track.cues.length > 0) {
                    track.removeCue(track.cues[0]);
                }
            }
        }
    }
    syncNativeFullscreenTracks(false);
}

subSelect.addEventListener('change', () => {
    userManuallySelectedSubtitle = true;
    const val = subSelect.value;
    if (val === '' || val === '__loading__') {
        clearSubtitles();
    } else {
        const idx = parseInt(val, 10);
        if (currentAvailableTracks[idx]) {
            loadSelectedTrack(currentAvailableTracks[idx]);
        }
    }
});

// -------------------------------------------------------------
// 4. Subtitle Parsers (SRT, ASS, SAMI)
// -------------------------------------------------------------
function decodeSubtitleBuffer(buffer) {
    const bytes = new Uint8Array(buffer);
    // UTF-16 LE BOM: FF FE  (가장 흔한 Windows SMI 인코딩)
    if (bytes.length >= 2 && bytes[0] === 0xFF && bytes[1] === 0xFE) {
        try {
            return new TextDecoder('utf-16le').decode(buffer);
        } catch(e) {}
    }
    // UTF-16 BE BOM: FE FF
    if (bytes.length >= 2 && bytes[0] === 0xFE && bytes[1] === 0xFF) {
        try {
            return new TextDecoder('utf-16be').decode(buffer);
        } catch(e) {}
    }
    // UTF-8 BOM: EF BB BF
    if (bytes.length >= 3 && bytes[0] === 0xEF && bytes[1] === 0xBB && bytes[2] === 0xBF) {
        return new TextDecoder('utf-8').decode(buffer.slice(3));
    }
    // UTF-8 (strict)
    try {
        return new TextDecoder('utf-8', { fatal: true }).decode(buffer);
    } catch (e) {}
    // EUC-KR (한국어 레거시 SMI)
    try {
        return new TextDecoder('euc-kr').decode(buffer);
    } catch (e2) {}
    // 최후 수단
    return new TextDecoder('utf-8').decode(buffer);
}

function decodeHtmlEntities(str) {
    if (!str) return '';
    return str
        .replace(/&nbsp;/gi, ' ')
        .replace(/&amp;/gi, '&')
        .replace(/&lt;/gi, '<')
        .replace(/&gt;/gi, '>')
        .replace(/&quot;/gi, '"')
        .replace(/&#39;|&#x27;/gi, "'")
        .replace(/&#34;|&#x22;/gi, '"')
        .replace(/&#x([0-9a-fA-F]{1,6});/gi, (match, hex) => {
            try { return String.fromCodePoint ? String.fromCodePoint(parseInt(hex, 16)) : String.fromCharCode(parseInt(hex, 16)); } catch (e) { return match; }
        })
        .replace(/&#([0-9]{1,7});/g, (match, dec) => {
            try { return String.fromCodePoint ? String.fromCodePoint(parseInt(dec, 10)) : String.fromCharCode(parseInt(dec, 10)); } catch (e) { return match; }
        });
}

function parseTimestamp(str) {
    if (!str) return 0;
    // Strip trailing WebVTT cue settings (e.g. "00:01:13.500 line:90% align:center")
    let s = str.trim();
    const sp = s.indexOf(' ');
    if (sp !== -1) s = s.substring(0, sp);
    const tb = s.indexOf('\t');
    if (tb !== -1) s = s.substring(0, tb);
    if (s.indexOf(',') !== -1) s = s.replace(',', '.');
    
    const p1 = s.indexOf(':');
    let res = 0;
    if (p1 === -1) {
        res = parseFloat(s);
    } else {
        const p2 = s.indexOf(':', p1 + 1);
        if (p2 === -1) {
            res = parseFloat(s.substring(0, p1)) * 60 + parseFloat(s.substring(p1 + 1));
        } else {
            res = parseFloat(s.substring(0, p1)) * 3600 + parseFloat(s.substring(p1 + 1, p2)) * 60 + parseFloat(s.substring(p2 + 1));
        }
    }
    return (isFinite(res) && res >= 0) ? res : 0;
}

function finalizeCues(cues) {
    cues.sort((a, b) => a.start - b.start);
    let maxFiniteDur = 0;
    for (let i = 0; i < cues.length; i++) {
        const dur = cues[i].end - cues[i].start;
        if (isFinite(dur) && dur > maxFiniteDur) {
            maxFiniteDur = dur;
        }
    }
    cues._maxFiniteDur = maxFiniteDur;
    return cues;
}

function parseSRT(srtText) {
    const cues = [];
    const normalized = srtText.replace(/\r\n|\r/g, '\n');
    const blocks = normalized.split(/\n\s*\n/);
    
    for (const block of blocks) {
        const trimmedBlock = block.trim();
        if (!trimmedBlock || /^WEBVTT\b/i.test(trimmedBlock) || /^STYLE\b/i.test(trimmedBlock) || /^NOTE\b/i.test(trimmedBlock)) {
            continue;
        }
        const lines = trimmedBlock.split('\n');
        // BUG-1: Use findIndex instead of hardcoded lines[0]/[1] heuristic —
        // correctly handles SRT with or without sequence-number lines, and SRT
        // blocks where extra blank lines produce different array lengths.
        const timeLineIdx = lines.findIndex(l => l.includes('-->'));
        if (timeLineIdx !== -1) {
            const timeLine = lines[timeLineIdx];
            const textLines = lines.slice(timeLineIdx + 1);
            
            const times = timeLine.split('-->');
            if (times.length === 2) {
                const start = parseTimestamp(times[0].trim());
                const end = parseTimestamp(times[1].trim());
                
                let rawText = textLines.join('\n');
                const isTop = rawText.includes('{\\an8}') || rawText.includes('{\\an7}') || rawText.includes('{\\an9}') || /\bline:(?:[0-9]|1[0-5])%/i.test(times[1]);
                
                // Keep '\n' as a real newline here rather than an HTML '<br>' -
                // the text is untrusted (comes straight from the video file's
                // subtitle track) and still needs to pass through escapeHtml()
                // at render time before touching innerHTML. '<br>' insertion
                // happens after escaping, in updateSubtitleDisplay().
                let cleanText = decodeHtmlEntities(rawText
                    .replace(/\{[^}]+\}/g, '')
                    .replace(/<[^>]+>/g, '')).trim();

                if (cleanText && end > start) {
                    cues.push({ start, end, text: cleanText, isTop });
                }
            }
        }
    }
    return finalizeCues(cues);
}

function parseASS(assText) {
    const cues = [];
    const lines = assText.replace(/\r\n|\r/g, '\n').split('\n');
    for (const line of lines) {
        const trimmed = line.trim();
        if (/^Dialogue\s*:/i.test(trimmed)) {
            const commaIdx = trimmed.indexOf(':');
            const parts = trimmed.substring(commaIdx + 1).split(',');
            if (parts.length >= 10) {
                const start = parseTimestamp(parts[1].trim());
                const end = parseTimestamp(parts[2].trim());
                const rawText = parts.slice(9).join(',');
                
                const isTop = rawText.includes('{\\an8}') || rawText.includes('{\\an7}') || rawText.includes('{\\an9}');
                
                // '\n' / ' ' here are real newline/NBSP characters, not
                // HTML - see the note in parseSRT() about why this text still
                // has to go through escapeHtml() before touching innerHTML.
                let cleanText = decodeHtmlEntities(rawText
                    .replace(/\{[^}]+\}/g, '')
                    .replace(/\\N/gi, '\n')
                    .replace(/\\n/g, '\n')
                    .replace(/\\h/gi, ' ')).trim();

                if (cleanText && end > start) {
                    cues.push({ start, end, text: cleanText, isTop });
                }
            }
        }
    }
    return finalizeCues(cues);
}

function parseSAMI(smiText) {
    const cues = [];
    // SAMI BODY만 추출 (HEAD 스타일 등 제거)
    const bodyMatch = smiText.match(/<BODY[^>]*>([\s\S]*)/i);
    const bodyText = bodyMatch ? bodyMatch[1] : smiText;

    const syncRegex = /<SYNC\s+Start=([0-9]+)[^>]*>([\s\S]*?)(?=<SYNC|$)/gi;
    let match;

    while ((match = syncRegex.exec(bodyText)) !== null) {
        const startSec = parseInt(match[1], 10) / 1000;
        let content = match[2];

        // <br> 태그를 먼저 줄바꿈으로 변환 (내용 보존)
        content = content.replace(/<br\s*\/?>/gi, '\n');
        // <P ...> 태그 제거
        content = content.replace(/<P[^>]*>/gi, '');
        // 나머지 모든 HTML 태그 제거 (<font color=...> 등)
        content = content.replace(/<[^>]+>/g, '');
        // HTML 엔티티 디코딩
        content = decodeHtmlEntities(content);
        // 각 줄 앞뒤 공백 정리 후 빈 줄 제거, 실제 개행으로 조합
        // (HTML '<br>' 조합은 렌더링 시 escapeHtml() 이후로 미룸 - 자막 텍스트는
        // 신뢰할 수 없는 입력이라 innerHTML에 넣기 전에 반드시 이스케이프해야 함)
        content = content.split('\n')
            .map(l => l.trim())
            .filter(l => l.length > 0)
            .join('\n')
            .trim();

        if (content && content !== '\xa0') {
            // end defaults to Infinity, not start+4 - the overlap-prevention
            // pass below clamps every cue except the very last one down to
            // its actual close time anyway (either the next SYNC's start, or
            // an explicit empty SYNC below). Without a real "next" event, the
            // last subtitle of the file was disappearing after a fixed 4s
            // instead of staying up until the video ends.
            cues.push({
                start: startSec,
                end: Infinity,
                text: content,
                isTop: false
            });
        } else if (cues.length > 0) {
            // 빈 SYNC = 직전 열려있는 모든 자막들의 종료 시각
            for (let j = cues.length - 1; j >= 0; j--) {
                if (cues[j].end === Infinity) {
                    if (startSec > cues[j].start) {
                        cues[j].end = startSec;
                    }
                } else {
                    break;
                }
            }
        }
    }

    // 겹침 방지: 다음 자막 시작 전에 끝나도록 보정하되, 동일 시각 자막(동시 대사/다국어)의 조기 소멸 방지
    for (let i = 0; i < cues.length - 1; i++) {
        let nextStart = Infinity;
        for (let j = i + 1; j < cues.length; j++) {
            if (cues[j].start > cues[i].start) {
                nextStart = cues[j].start;
                break;
            }
        }
        if (nextStart !== Infinity && cues[i].end > nextStart) {
            cues[i].end = nextStart;
        }
    }

    return finalizeCues(cues);
}

// -------------------------------------------------------------
// 5. Controls & Styling
// -------------------------------------------------------------
function applySubtitleStyle() {
    // 1. Floating player DOM subtitle box
    if (subtitleBox) {
        if (subBgEnabled) {
            subtitleBox.classList.remove('no-bg');
        } else {
            subtitleBox.classList.add('no-bg');
        }
    }
    if (subBgToggleBtn) {
        subBgToggleBtn.innerHTML = subBgEnabled ? `${PLAYER_SVG.subBgOn} <span>배경: 있음</span>` : `${PLAYER_SVG.subBgOff} <span>배경: 없음</span>`;
    }
    
    // 2. Set root CSS variable for windowed subtitle box
    document.documentElement.style.setProperty('--sub-scale', subScale);
    
    // 3. Dynamic stylesheet for fullscreen video::cue to follow all subtitle settings identically!
    let cueStyleEl = document.getElementById('webplayer-cue-dynamic-style');
    if (!cueStyleEl) {
        cueStyleEl = document.createElement('style');
        cueStyleEl.id = 'webplayer-cue-dynamic-style';
        document.head.appendChild(cueStyleEl);
    }
    
    const cueFontSize = (2.8 * subScale).toFixed(2);
    const cueBg = subBgEnabled 
        ? 'rgba(0, 0, 0, 0.75)' 
        : 'transparent';
    const cueShadow = subBgEnabled
        ? '2px 2px 4px #000, -2px -2px 4px #000, 2px -2px 4px #000, -2px 2px 4px #000, 0 0 8px #000'
        : '2px 2px 3px #000, -2px -2px 3px #000, 2px -2px 3px #000, -2px 2px 3px #000, 0 0 10px #000, 0 2px 6px #000';
        
    cueStyleEl.textContent = `
        video::cue {
            background-color: ${cueBg} !important;
            color: #ffffff !important;
            font-size: ${cueFontSize}vw !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans KR", sans-serif !important;
            font-weight: 700 !important;
            line-height: 1.4 !important;
            text-shadow: ${cueShadow} !important;
            white-space: pre-line !important;
        }
    `;
}

function updateSubtitleScale(newScale) {
    subScale = Math.round(Math.max(0.6, Math.min(3.0, newScale)) * 100) / 100;
    safeSetItem('mycloud_sub_scale', subScale);
    applySubtitleStyle();
    showToast(`자막 크기: ${Math.round(subScale * 100)}%`);
}

if (subBgToggleBtn) {
    subBgToggleBtn.addEventListener('click', () => {
        subBgEnabled = !subBgEnabled;
        safeSetItem('mycloud_sub_bg', subBgEnabled ? 'true' : 'false');
        applySubtitleStyle();
    });
}

fontIncreaseBtn.addEventListener('click', () => {
    updateSubtitleScale(subScale + 0.15);
});

fontDecreaseBtn.addEventListener('click', () => {
    updateSubtitleScale(subScale - 0.15);
});

document.querySelectorAll('.sync-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const offset = parseFloat(btn.dataset.offset);
        subtitleOffset += offset;
        syncDisplay.textContent = (subtitleOffset >= 0 ? '+' : '') + subtitleOffset.toFixed(1) + 's';
        syncCuesToTextTrack();
        updateSubtitleDisplay();
    });
});

syncResetBtn.addEventListener('click', () => {
    subtitleOffset = 0;
    syncDisplay.textContent = '0.0s';
    syncCuesToTextTrack();
    updateSubtitleDisplay();
});

const customSubBlobUrls = [];
customSubBtn.addEventListener('click', () => customSubInput.click());
customSubInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    customSubInput.value = '';
    
    const ext = file.name.split('.').pop().toLowerCase();
    const blobUrl = URL.createObjectURL(file);
    customSubBlobUrls.push(blobUrl);
    const track = {
        type: 'external',
        label: `[로컬 파일] ${file.name}`,
        url: blobUrl,
        ext: ext,
        lang: ext
    };
    userManuallySelectedSubtitle = true;
    currentAvailableTracks.unshift(track);
    renderSubtitleDropdown(currentAvailableTracks, null);
    subSelect.value = '0';
    loadSelectedTrack(track);
});

if (fullscreenBtn) {
    fullscreenBtn.addEventListener('click', toggleFullscreen);
}
videoPlayer.addEventListener('dblclick', toggleFullscreen);

if (minimizeBtn) {
    minimizeBtn.addEventListener('click', toggleMinimize);
}

function closePlayer() {
    if (isFullscreen()) {
        exitFullscreenSafe();
    }
    if (isMinimized) restoreFromMinimize();
    destroyHlsInstance();
    isHlsRemuxActive = false;
    hlsAutoFallbackAttempted = false;
    videoPlayer.pause();
    videoPlayer.removeAttribute('src');
    videoPlayer.load();
    currentSpeedIndex = 1;
    if (videoPlayer) videoPlayer.playbackRate = 1.0;
    if (videoSpeedText) videoSpeedText.textContent = '1.0x';
    if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'none';
    if (currentProbeAbortController) {
        currentProbeAbortController.abort();
        currentProbeAbortController = null;
    }
    if (currentSubAbortController) {
        currentSubAbortController.abort();
        currentSubAbortController = null;
    }
    while (customSubBlobUrls.length > 0) {
        const u = customSubBlobUrls.pop();
        subtitleMemoryCache.delete(`${u}:`);
        try { URL.revokeObjectURL(u); } catch (e) {}
    }
    userManuallySelectedSubtitle = false;
    clearSubtitles();
    playerModal.classList.remove('active');
    hasCustomPosition = false;
    activeVideo = null;
    document.title = 'MyCloud Media Player';
}

closePlayerBtn.addEventListener('click', closePlayer);

document.addEventListener('keydown', (e) => {
    // Guard against firing shortcuts while typing in input fields
    if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable)) {
        if (e.key === 'Escape') {
            e.target.blur();
        }
        return;
    }
    // Suppress player hotkeys when typing in search input or dropdowns (Item 20)
    if (e.target && typeof e.target.matches === 'function' && e.target.matches('input, select, textarea') || (e.target && e.target.isContentEditable)) {
        if (e.key === 'Escape') e.target.blur();
        return;
    }
    if (e.key === 'Escape' && playerModal.classList.contains('active')) {
        if (isFullscreen()) {
            exitFullscreenSafe();
            e.preventDefault();
            e.stopPropagation();
            return;
        }
        closePlayer();
    }
    if (playerModal.classList.contains('active')) {
        // Space: Toggle Play/Pause
        if (e.code === 'Space' || e.key === ' ') {
            e.preventDefault();
            if (videoPlayer.paused) {
                videoPlayer.play();
            } else {
                videoPlayer.pause();
            }
            return;
        }
        // ArrowLeft: Seek -5s (Shift+ArrowLeft: -30s)
        if (e.key === 'ArrowLeft') {
            e.preventDefault();
            const step = e.shiftKey ? 30 : 5;
            videoPlayer.currentTime = Math.max(0, videoPlayer.currentTime - step);
            showToast(`탐색: -${step}초`);
            return;
        }
        // ArrowRight: Seek +5s (Shift+ArrowRight: +30s)
        if (e.key === 'ArrowRight') {
            e.preventDefault();
            const step = e.shiftKey ? 30 : 5;
            const maxTime = (videoPlayer.duration && isFinite(videoPlayer.duration) && videoPlayer.duration > 0)
                ? videoPlayer.duration
                : Infinity;
            videoPlayer.currentTime = Math.min(maxTime, Math.max(0, videoPlayer.currentTime + step));
            showToast(`탐색: +${step}초`);
            return;
        }
        // ArrowUp: Volume +10%
        if (e.key === 'ArrowUp') {
            e.preventDefault();
            videoPlayer.volume = Math.min(1, Math.round((videoPlayer.volume + 0.1) * 10) / 10);
            showToast(`볼륨: ${Math.round(videoPlayer.volume * 100)}%`);
            return;
        }
        // ArrowDown: Volume -10%
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            videoPlayer.volume = Math.max(0, Math.round((videoPlayer.volume - 0.1) * 10) / 10);
            showToast(`볼륨: ${Math.round(videoPlayer.volume * 100)}%`);
            return;
        }
        // > or Shift+. : Increase speed
        if (e.key === '>' || (e.shiftKey && e.key === '.')) {
            e.preventDefault();
            currentSpeedIndex = Math.min(SPEED_STEPS.length - 1, currentSpeedIndex + 1);
            setVideoSpeed(SPEED_STEPS[currentSpeedIndex]);
            return;
        }
        // < or Shift+, : Decrease speed
        if (e.key === '<' || (e.shiftKey && e.key === ',')) {
            e.preventDefault();
            currentSpeedIndex = Math.max(0, currentSpeedIndex - 1);
            setVideoSpeed(SPEED_STEPS[currentSpeedIndex]);
            return;
        }
        if (e.key === 'f' || e.key === 'F') {
            toggleFullscreen();
        } else if (e.key === 'm' || e.key === 'M') {
            toggleMinimize();
        } else if (e.key === 'b' || e.key === 'B') {
            subBgEnabled = !subBgEnabled;
            safeSetItem('mycloud_sub_bg', subBgEnabled ? 'true' : 'false');
            applySubtitleStyle();
        } else if (e.key === '+' || e.key === '=') {
            updateSubtitleScale(subScale + 0.15);
        } else if (e.key === '-' || e.key === '_') {
            updateSubtitleScale(subScale - 0.15);
        } else if (e.key === '[') {
            subtitleOffset -= 0.5;
            syncDisplay.textContent = (subtitleOffset >= 0 ? '+' : '') + subtitleOffset.toFixed(1) + 's';
            syncCuesToTextTrack();
            updateSubtitleDisplay();
        } else if (e.key === ']') {
            subtitleOffset += 0.5;
            syncDisplay.textContent = (subtitleOffset >= 0 ? '+' : '') + subtitleOffset.toFixed(1) + 's';
            syncCuesToTextTrack();
            updateSubtitleDisplay();
        } else if (e.shiftKey && (e.key === 'N' || e.key === 'n')) {
            playNextVideo();
        } else if (e.shiftKey && (e.key === 'P' || e.key === 'p')) {
            playPrevVideo();
        }
    }
});

if (directLinkBtn) {
    directLinkBtn.addEventListener('click', () => {
        if (!activeVideo) return;
        const fullUrl = window.location.origin + activeVideo.url;
        navigator.clipboard.writeText(fullUrl).then(() => {
            showToast('동영상 주소가 클립보드에 복사되었습니다!');
        });
    });
}

let searchDebounceTimer = null;
searchInput.addEventListener('input', () => {
    const query = searchInput.value.toLowerCase().trim();
    clearSearchBtn.style.display = query ? 'block' : 'none';
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
        applySortAndRender();
    }, 150); // 150ms debounce for smooth typing (Item 21)
});

clearSearchBtn.addEventListener('click', () => {
    searchInput.value = '';
    clearSearchBtn.style.display = 'none';
    applySortAndRender();
});

refreshBtn.addEventListener('click', () => loadData(currentDir, currentMode));

let toastTimer = null;
function showToast(msg, duration = 2500) {
    if (!toastEl) return;
    toastEl.textContent = msg;
    toastEl.classList.add('show');
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
        toastEl.classList.remove('show');
        toastTimer = null;
    }, duration);
}

const _HTML_CHARS = /[&<>"']/;
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const str = String(text);
    if (!_HTML_CHARS.test(str)) return str;
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// BUG-6: encodeURIComponent deliberately does not encode ' (apostrophe), which
// would break onclick="openFolder('value')" when the path contains one.
// pathEncode adds that missing step so all filesystem paths are safe in onclick attrs.
function pathEncode(path) {
    return encodeURIComponent(path || '').replace(/'/g, '%27');
}

window.addEventListener('resize', () => {
    if (!playerModal.classList.contains('active')) return;
    const margin = getModalViewportMargin();
    if (modalDialog) {
        if (isMinimized) {
            const mw = Math.min(340, window.innerWidth - margin * 2);
            modalDialog.style.width = `${mw}px`;
            modalDialog.style.height = '';
        } else if (window.innerWidth <= 640) {
            modalDialog.style.width = '';
            modalDialog.style.height = '';
        } else {
            const maxW = window.innerWidth - margin * 2;
            const maxH = window.innerHeight - margin * 2;
            if (modalDialog.style.width && modalDialog.offsetWidth > maxW) {
                modalDialog.style.width = `${maxW}px`;
            }
            if (modalDialog.style.height && modalDialog.offsetHeight > maxH) {
                modalDialog.style.height = `${maxH}px`;
            }
        }
    }
    // Clamp dialog position to keep it on screen
    if (hasCustomPosition && modalDialog) {
        const rect = modalDialog.getBoundingClientRect();
        const maxLeft = Math.max(margin, window.innerWidth - modalDialog.offsetWidth - margin);
        const maxTop = Math.max(margin, window.innerHeight - modalDialog.offsetHeight - margin);
        modalDialog.style.left = `${Math.max(margin, Math.min(Math.round(rect.left), maxLeft))}px`;
        modalDialog.style.top = `${Math.max(margin, Math.min(Math.round(rect.top), maxTop))}px`;
    } else {
        centerModalDialog();
    }
});

document.addEventListener('DOMContentLoaded', async () => {
    applySubtitleStyle();
    setLayoutMode(currentLayout);

    // Check for auto-open video param from WebExplorer or direct link (e.g. ?open=Path/To/Video.mkv)
    const urlParams = new URLSearchParams(window.location.search);
    const targetVideoRel = urlParams.get('open') || urlParams.get('video');

    if (targetVideoRel) {
        // Find parent folder of the video to load context
        let cleanPath = decodeURIComponent(targetVideoRel).replace(/\\/g, '/').replace(/^\/+/, '');
        if (cleanPath.startsWith('Public/')) {
            cleanPath = cleanPath.substring(7);
        }
        const lastSlash = cleanPath.lastIndexOf('/');
        const parentDir = lastSlash !== -1 ? cleanPath.substring(0, lastSlash) : '';

        await loadData(parentDir, 'folder');

        // Locate and open the requested video immediately
        const found = currentVideos.find(v => v.rel_path === cleanPath || v.rel_path.endsWith('/' + cleanPath) || cleanPath.endsWith('/' + v.rel_path) || v.name === cleanPath);
        if (found) {
            openPlayer(encodeURIComponent(found.rel_path));
        } else {
            // If not found in parent folder, try searching in all mode
            await loadData('', 'all');
            const foundAll = currentVideos.find(v => v.rel_path === cleanPath || v.rel_path.endsWith('/' + cleanPath) || cleanPath.endsWith('/' + v.rel_path) || v.name === cleanPath);
            if (foundAll) {
                openPlayer(encodeURIComponent(foundAll.rel_path));
            }
        }
    } else {
        loadData('', 'folder');
    }
});


// -------------------------------------------------------------
// Playback Speed Controller
// -------------------------------------------------------------
const btnVideoSpeed = document.getElementById('btn-video-speed');
const videoSpeedText = document.getElementById('video-speed-text');
const SPEED_STEPS = [0.75, 1.0, 1.25, 1.5, 2.0];
let currentSpeedIndex = 1; // Default 1.0x

function setVideoSpeed(speed) {
    if (!videoPlayer) return;
    videoPlayer.playbackRate = speed;
    if (videoSpeedText) videoSpeedText.textContent = `${speed.toFixed(speed % 1 === 0 ? 1 : 2)}x`;
    showToast(`재생 배속: ${speed}x`);
}

function cycleVideoSpeed() {
    currentSpeedIndex = (currentSpeedIndex + 1) % SPEED_STEPS.length;
    setVideoSpeed(SPEED_STEPS[currentSpeedIndex]);
}

if (btnVideoSpeed) {
    btnVideoSpeed.addEventListener('click', cycleVideoSpeed);
}

// -------------------------------------------------------------
// MediaSession API Integration (Lockscreen & Bluetooth Headset Control)
// -------------------------------------------------------------
function updateMediaSessionPosition() {
    if (!('mediaSession' in navigator) || !navigator.mediaSession.setPositionState || !videoPlayer) return;
    try {
        if (videoPlayer.duration && isFinite(videoPlayer.duration) && videoPlayer.duration > 0) {
            navigator.mediaSession.setPositionState({
                duration: videoPlayer.duration,
                playbackRate: videoPlayer.playbackRate || 1.0,
                position: Math.min(Math.max(videoPlayer.currentTime || 0, 0), videoPlayer.duration)
            });
        }
    } catch (e) {}
}

function setupMediaSession(video) {
    if (!('mediaSession' in navigator)) return;
    try {
        navigator.mediaSession.metadata = new MediaMetadata({
            title: video.name,
            artist: 'MyCloud Media Player',
            album: video.folder || 'Public'
        });
        navigator.mediaSession.playbackState = 'playing';

        navigator.mediaSession.setActionHandler('play', () => { if (videoPlayer) videoPlayer.play(); });
        navigator.mediaSession.setActionHandler('pause', () => { if (videoPlayer) videoPlayer.pause(); });
        navigator.mediaSession.setActionHandler('previoustrack', () => playPrevVideo());
        navigator.mediaSession.setActionHandler('nexttrack', () => playNextVideo());
        navigator.mediaSession.setActionHandler('seekbackward', (details) => {
            if (!videoPlayer) return;
            const skipTime = details.seekOffset || 10;
            videoPlayer.currentTime = Math.max(videoPlayer.currentTime - skipTime, 0);
            updateMediaSessionPosition();
        });
        navigator.mediaSession.setActionHandler('seekforward', (details) => {
            if (!videoPlayer) return;
            const skipTime = details.seekOffset || 10;
            const maxTime = (videoPlayer.duration && isFinite(videoPlayer.duration) && videoPlayer.duration > 0)
                ? videoPlayer.duration
                : Infinity;
            videoPlayer.currentTime = Math.min(videoPlayer.currentTime + skipTime, maxTime);
            updateMediaSessionPosition();
        });
        try {
            navigator.mediaSession.setActionHandler('seekto', (details) => {
                if (!videoPlayer || details.seekTime == null) return;
                videoPlayer.currentTime = details.seekTime;
                updateMediaSessionPosition();
            });
        } catch (e) {}
        updateMediaSessionPosition();
    } catch (e) {}
}

if (videoPlayer) {
    videoPlayer.addEventListener('error', () => {
        if (!videoPlayer.getAttribute('src') || videoPlayer.src === window.location.href) return;
        const err = videoPlayer.error;
        // Automatic fallback to On-Demand Real-Time HLS Remuxing when direct MKV playback fails
        if (activeVideo && (activeVideo.ext || '').toLowerCase() === 'mkv' && !isHlsRemuxActive && !hlsAutoFallbackAttempted) {
            hlsAutoFallbackAttempted = true;
            showToast('MKV 직접 재생 미지원 — 실시간 HLS 리먹싱으로 자동 전환합니다...', 3500);
            attachVideoSource(activeVideo, true, videoPlayer.currentTime || 0);
            return;
        }
        let msg = '동영상 재생 중 오류가 발생했습니다.';
        if (err) {
            if (err.code === 4) {
                msg = '브라우저에서 지원하지 않는 비디오 코덱(HEVC/H.265 등)이거나 파일을 찾을 수 없습니다.';
            } else if (err.code === 3) {
                msg = '비디오 디코딩 중 오류가 발생했습니다.';
            } else if (err.code === 2) {
                msg = '네트워크 전송 오류로 비디오를 불러올 수 없습니다.';
            }
        }
        showToast(msg, 5000);
    });

    let lastMsPosUpdate = 0;
    videoPlayer.addEventListener('play', () => {
        if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'playing';
        updateMediaSessionPosition();
    });
    videoPlayer.addEventListener('pause', () => {
        if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'paused';
        updateMediaSessionPosition();
    });
    videoPlayer.addEventListener('timeupdate', () => {
        const now = Date.now();
        if (now - lastMsPosUpdate > 1000) {
            lastMsPosUpdate = now;
            updateMediaSessionPosition();
        }
    });
    videoPlayer.addEventListener('seeked', updateMediaSessionPosition);
    videoPlayer.addEventListener('ratechange', updateMediaSessionPosition);
    videoPlayer.addEventListener('loadedmetadata', updateMediaSessionPosition);
    
    // Toggle play/pause by clicking directly on video element (desktop only;
    // on iOS/touch devices native <video controls> already handles taps).
    videoPlayer.addEventListener('click', (e) => {
        if (e.target !== videoPlayer) return;
        if ('ontouchstart' in window || navigator.maxTouchPoints > 0) return;
        if (videoPlayer.paused) {
            videoPlayer.play().catch(() => {});
        } else {
            videoPlayer.pause();
        }
    });
}
