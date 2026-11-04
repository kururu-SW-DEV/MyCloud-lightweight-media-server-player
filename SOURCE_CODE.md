# MyCloud Media Player 전체 소스 코드 (Full Source Code)

- **배포 타겟**: WD My Cloud Gen 1 (ARMv7 650MHz, 226MB RAM, Apache 2.4, PHP 5.6.7-1, Python 2.7)
- **웹 서버 배포 경로**: `/shares/webplayer/`
- **미디어 루트 경로**: `/shares/Public/`
- **최신 버전**: `v20261104_v4`

---

## index.html

```html
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <meta name="theme-color" content="#090d16">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <title>MyCloud Media Player</title>
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2338bdf8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect x='2' y='4' width='20' height='16' rx='2.5'%3E%3C/rect%3E%3Cpolygon points='10 9 15 12 10 15 10 9' fill='%2338bdf8'%3E%3C/polygon%3E%3C/svg%3E">
    <link rel="stylesheet" href="style.css?v=20261104_1">
</head>
<body>
    <div class="app-container">
        <!-- Header -->
        <header class="navbar">
            <div class="brand" onclick="switchMode('folder', '')" style="cursor: pointer;" title="홈으로 이동 (Public)">
                <span class="brand-logo" aria-hidden="true">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2.5"></rect><polygon points="10 9 15 12 10 15 10 9" fill="currentColor"></polygon></svg>
                </span>
                <h1>MyCloud <span>Media Player</span></h1>
            </div>
            <div class="search-bar">
                <input type="text" id="search-input" placeholder="영상 또는 폴더 검색..." autocomplete="off">
                <button id="clear-search" class="clear-btn" title="검색어 지우기">&times;</button>
            </div>
            <div class="nav-actions">
                <button id="refresh-btn" class="btn btn-secondary" title="새로고침">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
                    <span>새로고침</span>
                </button>
                <a href="/explorer/" class="btn btn-secondary btn-nav-switch" id="btn-explorer-nav" title="MyCloud Explorer로 이동">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
                    <span>Explorer ↗</span>
                </a>
            </div>
        </header>

        <!-- Main Content -->
        <main class="main-content">
            <!-- Directory Path, Mode Toggle & Status -->
            <div class="breadcrumb-container">
                <div class="breadcrumbs" id="breadcrumbs">
                    <span class="crumb active" data-path="">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="crumb-icon"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>
                        <span>Public</span>
                    </span>
                </div>
                <div class="toolbar-right">
                    <div class="view-mode-toggle" title="탐색 모드 선택">
                        <button id="mode-folder-btn" class="btn-mode active" title="폴더별 탐색">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
                            <span>폴더별</span>
                        </button>
                        <button id="mode-all-btn" class="btn-mode" title="모든 폴더의 영상을 한 번에 보기">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"></rect><polygon points="10 9 15 12 10 15 10 9" fill="currentColor"></polygon></svg>
                            <span>전체 영상</span>
                        </button>
                    </div>
                    <div class="layout-toggle" title="목록 표시 형태">
                        <button id="layout-grid-btn" class="btn-layout" title="타일 형식으로 보기">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
                            <span>타일</span>
                        </button>
                        <button id="layout-list-btn" class="btn-layout active" title="목록(리스트) 형식으로 보기">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line></svg>
                            <span>목록</span>
                        </button>
                    </div>
                    <div class="meta-toggle" title="파일 날짜 및 용량 표시 설정 (기본: 숨김)">
                        <button id="meta-hide-btn" class="btn-layout active" title="파일 날짜 및 용량 숨김 (기본값)">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>
                            <span class="toggle-text-full">날짜·용량 숨김</span>
                            <span class="toggle-text-short">숨김</span>
                        </button>
                        <button id="meta-show-btn" class="btn-layout" title="파일 날짜 및 용량 표시">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                            <span class="toggle-text-full">날짜·용량 표시</span>
                            <span class="toggle-text-short">표시</span>
                        </button>
                    </div>
                    <select id="sort-select" class="sort-select" title="정렬 기준">
                        <option value="name_asc" selected>이름순 (오름차순)</option>
                        <option value="name_desc">이름순 (내림차순)</option>
                        <option value="date_desc">최신 등록순</option>
                        <option value="date_asc">오래된 등록순</option>
                        <option value="size_desc">파일 크기순</option>
                    </select>
                    <div class="stats" id="stats-badge">불러오는 중...</div>
                </div>
            </div>

            <!-- Media Grid (Folders & Videos) -->
            <div class="video-grid list-view" id="video-grid">
                <div class="loading-spinner">항목을 불러오는 중입니다...</div>
            </div>
        </main>
    </div>

    <!-- Video Player Modal -->
    <div id="player-modal" class="modal">
        <div class="modal-dialog">
            <div class="modal-header" title="마우스로 드래그하여 창 이동 (더블클릭: 중앙 정렬)">
                <h2 id="player-title" class="video-title-display">
                    <span class="drag-handle-icon" title="마우스로 드래그하여 창 이동">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="5 9 2 12 5 15"></polyline><polyline points="9 5 12 2 15 5"></polyline><polyline points="15 19 12 22 9 19"></polyline><polyline points="19 9 22 12 19 15"></polyline><line x1="2" y1="12" x2="22" y2="12"></line><line x1="12" y1="2" x2="12" y2="22"></line></svg>
                    </span>
                    <span id="player-title-text">제목</span>
                </h2>
                <div class="modal-header-actions">
                    <button id="prev-video-btn" class="btn btn-small" title="이전 영상 재생 (단축키: Shift + P)">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><polygon points="19 20 9 12 19 4 19 20"></polygon><line x1="5" y1="19" x2="5" y2="5" stroke="currentColor" stroke-width="2"></line></svg>
                        <span>이전</span>
                    </button>
                    <button id="next-video-btn" class="btn btn-small" title="다음 영상 재생 (단축키: Shift + N)">
                        <span>다음</span>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 4 15 12 5 20 5 4"></polygon><line x1="19" y1="5" x2="19" y2="19" stroke="currentColor" stroke-width="2"></line></svg>
                    </button>
                                        <button id="btn-video-speed" class="btn btn-small" title="재생 배속 변경 (단축키: > 또는 <)">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                        <span id="video-speed-text">1.0x</span>
                    </button>
                    <button id="minimize-btn" class="btn btn-small" title="최소화 (영상은 계속 재생됨, 단축키: M)">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="12" x2="20" y2="12"></line></svg>
                        <span>최소화</span>
                    </button>
                    <button id="fullscreen-btn" class="btn btn-small" title="전체화면 (단축키: F 또는 더블클릭)">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"></path></svg>
                        <span>전체화면</span>
                    </button>
                    <button id="close-player-btn" class="btn-close" title="닫기 (Esc)">&times;</button>
                </div>
            </div>
            <div class="modal-body">
                <div class="video-wrapper" id="video-wrapper">
                    <video id="video-player" playsinline controls preload="metadata">
                        <track id="webplayer-native-track" kind="subtitles" srclang="ko" label="WebPlayerSub">
                    </video>
                    <!-- Custom High-Fidelity Subtitle Overlay -->
                    <div id="subtitle-box" class="subtitle-box" style="display:none;"></div>
                </div>
            </div>
            <!-- Player Toolbar -->
            <div class="modal-footer">
                <div class="control-group">
                    <label for="sub-select">자막 선택:</label>
                    <select id="sub-select" class="select-input">
                        <option value="">자막 없음</option>
                    </select>
                    <button id="custom-sub-btn" class="btn btn-small" title="외부 자막 파일 선택 (.smi, .srt, .ass, .vtt)">
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
                        <span>외부 자막</span>
                    </button>
                    <input type="file" id="custom-sub-input" accept=".smi,.sami,.srt,.ass,.ssa,.vtt" style="display:none">
                </div>
                <div class="control-group">
                    <span>자막 스타일:</span>
                    <button id="sub-bg-toggle" class="btn btn-small" title="자막 배경 박스 전환 (단축키: B)">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><rect x="3" y="3" width="18" height="18" rx="2"></rect></svg>
                        <span>배경: 있음</span>
                    </button>
                    <button id="font-decrease" class="btn btn-small" title="자막 축소 (단축키: -)">A-</button>
                    <button id="font-increase" class="btn btn-small" title="자막 확대 (단축키: +)">A+</button>
                </div>
                <div class="control-group">
                    <span>싱크 조절:</span>
                    <button class="btn btn-small sync-btn" data-offset="-0.5">-0.5s</button>
                    <span id="sync-display" class="sync-value">0.0s</span>
                    <button class="btn btn-small sync-btn" data-offset="0.5">+0.5s</button>
                    <button id="sync-reset" class="btn btn-small">초기화</button>
                </div>

            </div>
            <!-- Floating Player Resize Handle -->
            <div id="modal-resize-handle" class="modal-resize-handle" title="창 크기 조절 (마우스 드래그 / 더블클릭: 기본 크기 복원)">
                <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor"><circle cx="2" cy="8" r="1"></circle><circle cx="5" cy="5" r="1"></circle><circle cx="8" cy="2" r="1"></circle><circle cx="5" cy="8" r="1"></circle><circle cx="8" cy="5" r="1"></circle><circle cx="8" cy="8" r="1"></circle></svg>
            </div>
        </div>
    </div>

    <!-- Toast Notification -->
    <div id="toast" class="toast"></div>

    <script src="app.js?v=20261104_1"></script>
</body>
</html>

```

---

## style.css

```css
* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

:root {
    --bg-dark: #0f172a;
    --bg-card: #182235;
    --bg-hover: #26334d;
    --accent: #38bdf8;
    --accent-hover: #0ea5e9;
    --text-main: #f1f5f9;
    --text-muted: #94a3b8;
    --danger: #ef4444;
    --danger-hover: #dc2626;
    --border-card: rgba(255, 255, 255, 0.08);
    --radius: 8px;
    --shadow: 0 2px 8px rgba(0, 0, 0, 0.28);
    --font-stack: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans KR", sans-serif;
    --badge-ass: #a855f7;
    --badge-smi: #22c55e;
    --badge-srt: #3b82f6;
    --badge-none: #64748b;
    --sub-scale: 1;
}

body {
    font-family: var(--font-stack);
    background-color: var(--bg-dark);
    color: var(--text-main);
    min-height: 100vh;
    min-height: 100dvh;
    touch-action: manipulation;
    -webkit-text-size-adjust: 100%;
    padding-bottom: env(safe-area-inset-bottom);
}

.app-container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 20px;
}

/* Navbar */
.navbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 15px;
    padding: 12px 20px;
    background-color: var(--bg-card);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    border: 1px solid var(--border-card);
    margin-bottom: 16px;
    flex-wrap: wrap;
}

.brand {
    display: flex;
    align-items: center;
    gap: 10px;
    user-select: none;
}

.brand-logo {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    border-radius: 8px;
    background: rgba(56, 189, 248, 0.12);
    color: var(--accent);
    border: 1px solid rgba(56, 189, 248, 0.25);
    flex-shrink: 0;
}

.brand h1 {
    font-size: 1.3rem;
    font-weight: 700;
}

.brand h1 span {
    color: var(--accent);
}

.search-bar {
    flex: 1;
    max-width: 450px;
    position: relative;
    display: flex;
    align-items: center;
}

.search-bar input {
    width: 100%;
    padding: 8px 32px 8px 13px;
    background-color: var(--bg-dark);
    border: 1px solid var(--border-card);
    border-radius: 7px;
    color: var(--text-main);
    font-size: 0.86rem;
    outline: none;
    transition: border-color 0.15s, box-shadow 0.15s;
}

.search-bar input:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.15);
}

.clear-btn {
    position: absolute;
    right: 12px;
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: 1.2rem;
    cursor: pointer;
    display: none;
}


.btn-explorer-nav {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    text-decoration: none;
    color: var(--text-main);
    background: var(--bg-hover);
    border: 1px solid rgba(255, 255, 255, 0.08);
    padding: 7px 12px;
    border-radius: 7px;
    font-size: 0.84rem;
    font-weight: 600;
    transition: background-color 0.15s, border-color 0.15s, color 0.15s;
    white-space: nowrap;
}
.btn-explorer-nav:hover {
    background: rgba(56, 189, 248, 0.15);
    border-color: rgba(56, 189, 248, 0.4);
    color: var(--accent);
}
.btn-explorer-nav:hover {
    background: rgba(56, 189, 248, 0.15);
    border-color: rgba(56, 189, 248, 0.4);
    color: var(--accent);
}
.btn-explorer-nav svg {
    flex-shrink: 0;
}

.nav-actions {
    display: flex;
    gap: 10px;
}

/* Buttons */
.btn {
    padding: 7px 12px;
    border: 1px solid transparent;
    border-radius: 7px;
    font-size: 0.84rem;
    font-weight: 600;
    cursor: pointer;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 5px;
    transition: background-color 0.15s, border-color 0.15s, color 0.15s;
    user-select: none;
    white-space: nowrap;
    flex-shrink: 0;
}

.btn:active {
    transform: scale(0.97);
}

.btn-secondary {
    background-color: var(--bg-hover);
    color: var(--text-main);
    border-color: rgba(255, 255, 255, 0.07);
}

.btn-secondary:hover {
    background-color: #334155;
    border-color: rgba(255, 255, 255, 0.15);
}

.btn-small {
    padding: 5px 10px;
    font-size: 0.8rem;
    background-color: var(--bg-hover);
    color: var(--text-main);
    border-radius: 5px;
    border: none;
    cursor: pointer;
}

.btn-small:hover {
    background-color: #475569;
}

/* Breadcrumb & Mode Toolbar */
.breadcrumb-container {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    padding: 4px 6px;
    flex-wrap: wrap;
    gap: 12px;
}

.breadcrumbs {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.95rem;
    flex-wrap: wrap;
}

.crumb {
    color: var(--accent);
    cursor: pointer;
    font-weight: 500;
    transition: color 0.15s;
}

.crumb:hover {
    text-decoration: underline;
    color: var(--accent-hover);
}

.crumb.active {
    color: var(--text-main);
    cursor: default;
    text-decoration: none;
    font-weight: 700;
}

.crumb-sep {
    color: var(--text-muted);
    user-select: none;
    font-size: 0.85rem;
}

.toolbar-right {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
}

.view-mode-toggle {
    display: flex;
    background-color: var(--bg-card);
    border: 1px solid var(--border-card);
    border-radius: 8px;
    padding: 3px;
    gap: 3px;
    box-shadow: var(--shadow);
}

.btn-mode {
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: 0.82rem;
    font-weight: 600;
    padding: 5px 11px;
    border-radius: 6px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    transition: background-color 0.15s, color 0.15s;
}

.btn-mode:hover {
    color: var(--text-main);
}

.btn-mode.active {
    background-color: var(--accent);
    color: #0f172a;
    font-weight: 700;
}

.sort-select {
    background-color: var(--bg-card);
    color: var(--text-main);
    border: 1px solid var(--border-card);
    padding: 6px 12px;
    border-radius: 8px;
    font-size: 0.82rem;
    font-weight: 600;
    outline: none;
    cursor: pointer;
    transition: border-color 0.15s;
    box-shadow: var(--shadow);
}

.sort-select:hover, .sort-select:focus {
    border-color: var(--accent);
}

.layout-toggle {
    display: flex;
    background-color: var(--bg-card);
    border: 1px solid var(--border-card);
    border-radius: 8px;
    padding: 3px;
    gap: 3px;
    box-shadow: var(--shadow);
}

.btn-layout {
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: 0.82rem;
    font-weight: 600;
    padding: 5px 9px;
    border-radius: 6px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    transition: background-color 0.15s, color 0.15s;
}

.btn-layout:hover {
    color: var(--text-main);
}

.btn-layout.active {
    background-color: var(--accent);
    color: #0f172a;
    font-weight: 700;
}

.meta-toggle {
    display: flex;
    background-color: var(--bg-card);
    border: 1px solid var(--border-card);
    border-radius: 8px;
    padding: 3px;
    gap: 3px;
    box-shadow: var(--shadow);
}

.toggle-text-short {
    display: none;
}

@media (max-width: 900px) {
    .toggle-text-full {
        display: none;
    }
    .toggle-text-short {
        display: inline;
    }
}

/* Hide file date & size when meta toggle is set to hidden (default) */
.video-grid.hide-file-meta .video-card .card-meta {
    display: none !important;
}

.stats {
    font-size: 0.82rem;
    font-weight: 500;
    color: var(--text-muted);
    background: var(--bg-card);
    border: 1px solid var(--border-card);
    padding: 6px 12px;
    border-radius: 8px;
    white-space: nowrap;
    box-shadow: var(--shadow);
}

/* Video & Folder Grid */
.video-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 20px;
}

/* List View Styles */
.video-grid.list-view {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.video-grid.list-view .folder-card,
.video-grid.list-view .video-card {
    flex-direction: row;
    height: 60px;
    min-height: 60px;
    padding: 6px 16px;
    border-radius: 8px;
    align-items: center;
    gap: 15px;
    box-shadow: none;
    border: 1px solid rgba(255, 255, 255, 0.05);
}

.video-grid.list-view .folder-thumbnail,
.video-grid.list-view .card-thumbnail {
    width: 44px;
    height: 44px;
    min-width: 44px;
    border-radius: 6px;
}

.video-grid.list-view .folder-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--accent);
}

.video-grid.list-view .folder-icon svg {
    width: 24px;
    height: 24px;
}

.video-grid.list-view .card-folder-badge,
.video-grid.list-view .card-format-badge {
    display: none;
}

.video-grid.list-view .play-icon-overlay {
    width: 32px;
    height: 32px;
    background: rgba(56, 189, 248, 0.12);
    border: 1px solid rgba(56, 189, 248, 0.3);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--accent);
    box-shadow: none;
    transform: none;
    flex-shrink: 0;
}

.video-grid.list-view .video-card:hover .play-icon-overlay {
    transform: scale(1.06);
    background: var(--accent);
    color: #0f172a;
}

.video-grid.list-view .card-content {
    flex: 1;
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    padding: 0;
    gap: 15px;
    overflow: hidden;
}

.video-grid.list-view .list-main-col {
    display: flex;
    flex-direction: column;
    overflow: hidden;
    flex: 1;
}

.video-grid.list-view .card-title {
    font-size: 0.95rem;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-bottom: 2px;
}

.video-grid.list-view .card-folder-path {
    font-size: 0.75rem;
    color: var(--accent);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.video-grid.list-view .list-sub-col {
    display: flex;
    align-items: center;
    gap: 20px;
    flex-shrink: 0;
}

.video-grid.list-view .card-meta {
    font-size: 0.8rem;
    display: flex;
    gap: 12px;
    color: var(--text-muted);
    white-space: nowrap;
}

.video-grid.list-view .card-badges {
    display: flex;
    gap: 4px;
    min-width: 60px;
    justify-content: flex-end;
}

/* Cards (Default Grid) */
.folder-card, .video-card {
    background-color: var(--bg-card);
    border-radius: var(--radius);
    overflow: hidden;
    box-shadow: var(--shadow);
    border: 1px solid var(--border-card);
    transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s, background-color 0.2s;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    position: relative;
    user-select: none;
}

.folder-card:hover, .video-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 16px -2px rgba(0, 0, 0, 0.4);
    border-color: rgba(56, 189, 248, 0.4);
    background-color: var(--bg-card);
}

.folder-thumbnail {
    height: 120px;
    background: linear-gradient(135deg, #182235, #0f172a);
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
}

.parent-card .folder-thumbnail {
    background: linear-gradient(135deg, #26334d, #182235);
}

.folder-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--accent);
    opacity: 0.85;
    transition: transform 0.2s, color 0.2s;
}

.folder-icon svg {
    width: 48px;
    height: 48px;
}

.folder-card:hover .folder-icon {
    transform: scale(1.1);
    color: #7dd3fc;
}

.card-thumbnail {
    height: 150px;
    background: linear-gradient(135deg, #0f172a 0%, #182235 100%);
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
}

.play-icon-overlay {
    width: 44px;
    height: 44px;
    background-color: rgba(56, 189, 248, 0.85);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #0f172a;
    font-size: 1.2rem;
    padding-left: 3px;
    transition: transform 0.2s, background-color 0.2s;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.5);
}

.video-card:hover .play-icon-overlay {
    transform: scale(1.15);
    background-color: var(--accent);
}

.card-format-badge {
    position: absolute;
    top: 8px;
    left: 8px;
    background-color: rgba(15, 23, 42, 0.85);
    color: var(--text-main);
    font-size: 0.72rem;
    font-weight: 700;
    padding: 3px 6px;
    border-radius: 4px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.card-folder-badge {
    position: absolute;
    top: 8px;
    left: 8px;
    background-color: rgba(56, 189, 248, 0.2);
    color: var(--accent);
    font-size: 0.72rem;
    font-weight: 700;
    padding: 3px 6px;
    border-radius: 4px;
    text-transform: uppercase;
}

.card-content {
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    flex: 1;
}

.card-title {
    font-size: 0.92rem;
    font-weight: 600;
    line-height: 1.35;
    word-break: break-all;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.card-meta {
    font-size: 0.78rem;
    color: var(--text-muted);
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: auto;
}

.card-badges {
    display: flex;
    gap: 5px;
    flex-wrap: wrap;
    margin-top: 4px;
}

.badge {
    font-size: 0.7rem;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 4px;
    text-transform: uppercase;
}

.badge-smi, .badge-sami {
    background-color: rgba(34, 197, 94, 0.2);
    color: var(--badge-smi);
    border: 1px solid rgba(34, 197, 94, 0.3);
}

.badge-srt, .badge-vtt {
    background-color: rgba(59, 130, 246, 0.2);
    color: var(--badge-srt);
    border: 1px solid rgba(59, 130, 246, 0.3);
}

.badge-ass, .badge-ssa {
    background-color: rgba(168, 85, 247, 0.2);
    color: var(--badge-ass);
    border: 1px solid rgba(168, 85, 247, 0.3);
}

.badge-none {
    background-color: rgba(100, 116, 139, 0.2);
    color: var(--badge-none);
}

/* Modal Video Player */
.modal {
    display: none;
    position: fixed;
    inset: 0;
    z-index: 9999;
    pointer-events: none;
}

.modal.active {
    display: block;
}

.modal-dialog {
    position: fixed;
    width: min(94vw, 1050px);
    min-width: 380px;
    min-height: 250px;
    max-width: 98vw;
    max-height: 96vh;
    background-color: #111827;
    border-radius: 10px;
    border: 1px solid rgba(255, 255, 255, 0.12);
    overflow: hidden;
    box-shadow: 0 25px 65px -10px rgba(0, 0, 0, 0.88), 0 0 0 1px rgba(255, 255, 255, 0.08), 0 10px 30px rgba(0, 0, 0, 0.6);
    display: flex;
    flex-direction: column;
    z-index: 10000;
    pointer-events: auto;
    resize: both;
    contain: layout;
    will-change: width, height;
}

body.is-resizing,
body.is-dragging {
    user-select: none !important;
    -webkit-user-select: none !important;
}

:focus-visible {
    outline: 2px solid #38bdf8 !important;
    outline-offset: 2px !important;
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 14px;
    background: #182235;
    border-bottom: 1px solid var(--border-card);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
    cursor: grab;
    user-select: none;
    touch-action: none;
    gap: 12px;
    min-width: 0;
    flex-shrink: 0;
}

.modal-dialog .btn-small {
    background-color: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.13);
    color: #e2e8f0;
    border-radius: 6px;
    padding: 5px 11px;
    font-size: 0.8rem;
    font-weight: 500;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.modal-dialog .btn-small:hover {
    background-color: rgba(255, 255, 255, 0.16);
    border-color: rgba(255, 255, 255, 0.28);
    color: #ffffff;
    transform: translateY(-1px);
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.35);
}

.modal-dialog .btn-small:active {
    transform: translateY(0);
    background-color: rgba(255, 255, 255, 0.1);
}

.modal-header.dragging {
    cursor: grabbing;
}

.video-title-display {
    font-size: 0.93rem;
    font-weight: 600;
    color: #f8fafc;
    display: flex;
    align-items: center;
    gap: 7px;
    flex: 1;
    min-width: 0;
    overflow: hidden;
    margin-right: 0;
    letter-spacing: -0.01em;
}

#player-title-text {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
    flex: 1;
    display: inline-block;
}

.drag-handle-icon {
    font-size: 1.1rem;
    color: #38bdf8;
    cursor: grab;
    flex-shrink: 0;
    opacity: 0.85;
}

.modal-header-actions {
    display: flex;
    align-items: center;
    gap: 7px;
    flex-shrink: 0;
    white-space: nowrap;
}

.modal-header-actions button,
.modal-header-actions a {
    cursor: pointer;
    user-select: none;
    white-space: nowrap;
}

.btn-close {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #94a3b8;
    font-size: 1.15rem;
    line-height: 1;
    cursor: pointer;
    padding: 0;
    margin-left: 3px;
    transition: all 0.15s ease;
}

.btn-close:hover {
    background: rgba(239, 68, 68, 0.25);
    border-color: rgba(239, 68, 68, 0.45);
    color: #f87171;
    transform: scale(1.08);
}

/* Video Player Area */
.modal-body {
    background-color: black;
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 1;
    min-height: 0;
    overflow: hidden;
}

.video-wrapper {
    position: relative;
    width: 100%;
    height: 100%;
    flex: 1;
    min-height: 180px;
    aspect-ratio: 16 / 9;
    max-height: calc(96vh - 110px);
    display: flex;
    align-items: center;
    justify-content: center;
    background: black;
}

/* Fullscreen support on video-wrapper */
/* 100vh alone is a well-known source of a stray white sliver on Android
   Chrome fullscreen video - it's computed from a viewport size that can
   briefly mismatch the real one during/after the fullscreen transition.
   100dvh (dynamic viewport height) tracks the actual visible viewport;
   declaring vh first keeps a working fallback on browsers that don't know
   dvh, since the later, supported declaration simply wins. */
.video-wrapper:fullscreen,
.video-wrapper:-webkit-full-screen {
    width: 100vw !important;
    height: 100vh !important;
    height: 100dvh !important;
    max-height: 100vh !important;
    max-height: 100dvh !important;
    background: black !important;
}

.video-wrapper:fullscreen video,
.video-wrapper:-webkit-full-screen video {
    width: 100vw !important;
    height: 100vh !important;
    height: 100dvh !important;
    max-height: 100vh !important;
    max-height: 100dvh !important;
    object-fit: contain;
}

/* Belt-and-suspenders: force the whole document black while any element is
   fullscreen (class toggled in app.js), so nothing can ever show through as
   a stray white edge regardless of the exact viewport-height quirk at play. */
html.is-fullscreen,
html.is-fullscreen body {
    background: black !important;
}

video {
    width: 100%;
    height: 100%;
    max-height: 100%;
    object-fit: contain;
    background: black;
}

/* Subtitle Overlay Box */
.subtitle-box {
    display: none;
    position: absolute;
    bottom: 55px;
    left: 4%;
    right: 4%;
    text-align: center;
    color: #ffffff;
    font-size: calc(clamp(1.05rem, 1.25rem + 0.3vw, 1.45rem) * var(--sub-scale, 1));
    font-weight: 700;
    line-height: 1.4;
    text-shadow: 2px 2px 4px #000, -2px -2px 4px #000, 2px -2px 4px #000, -2px 2px 4px #000, 0 0 8px #000;
    pointer-events: none;
    user-select: none;
    z-index: 2147483647;
    white-space: pre-wrap;
    transition: font-size 0.1s;
    transform: translateZ(0);
    will-change: transform, opacity;
}

.subtitle-box.pos-top {
    top: 50px !important;
    bottom: auto !important;
}

.subtitle-box span {
    display: inline-block;
    background-color: rgba(0, 0, 0, 0.75);
    padding: 6px 16px;
    border-radius: 6px;
    max-width: 92%;
    word-break: break-word;
}

.subtitle-box.no-bg span {
    background-color: transparent !important;
    text-shadow: 2px 2px 3px #000, -2px -2px 3px #000, 2px -2px 3px #000, -2px 2px 3px #000, 0 0 10px #000, 0 2px 6px #000 !important;
}

.video-wrapper:fullscreen .subtitle-box,
.video-wrapper:-webkit-full-screen .subtitle-box {
    bottom: 95px !important;
    font-size: calc(clamp(2.0rem, 3.0vw, 3.6rem) * var(--sub-scale, 1)) !important;
    z-index: 2147483647 !important;
}

.video-wrapper:fullscreen .subtitle-box.pos-top,
.video-wrapper:-webkit-full-screen .subtitle-box.pos-top {
    top: 60px !important;
    bottom: auto !important;
}

/* Native WebVTT / HTML5 TextTrack Subtitle Styling */
video::cue {
    background-color: rgba(0, 0, 0, 0.75);
    color: #ffffff;
    font-size: 2.8vw;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans KR", sans-serif;
    font-weight: 700;
    line-height: 1.4;
    text-shadow: 2px 2px 4px #000, -2px -2px 4px #000;
    white-space: pre-line;
}

/* Modal Footer Toolbar */
.modal-footer {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 8px 14px;
    padding: 9px 16px;
    background: #141c2b;
    border-top: 1px solid var(--border-card);
    font-size: 0.83rem;
    flex-shrink: 0;
    position: relative;
}

.modal-dialog .select-input {
    background-color: #0d1017;
    color: #f1f5f9;
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 0.8rem;
    font-weight: 500;
    transition: border-color 0.15s, box-shadow 0.15s;
}

.modal-dialog .select-input:hover,
.modal-dialog .select-input:focus {
    border-color: #38bdf8;
    box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2);
    outline: none;
}

.modal-dialog .control-group label,
.modal-dialog .control-group span {
    color: #94a3b8;
    font-size: 0.81rem;
    font-weight: 500;
}

.sync-value {
    min-width: 44px;
    text-align: center;
    font-weight: 700;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    color: #38bdf8;
    background: rgba(56, 189, 248, 0.1);
    border: 1px solid rgba(56, 189, 248, 0.25);
    border-radius: 4px;
    padding: 2px 7px;
    font-size: 0.78rem;
    letter-spacing: 0.02em;
}

.modal-resize-handle {
    position: absolute;
    right: 3px;
    bottom: 3px;
    width: 20px;
    height: 20px;
    cursor: nwse-resize;
    display: flex;
    align-items: center;
    justify-content: center;
    color: rgba(255, 255, 255, 0.35);
    font-size: 1.05rem;
    line-height: 1;
    user-select: none;
    touch-action: none;
    z-index: 10001;
    transition: color 0.15s, transform 0.15s;
}

.modal-resize-handle:hover,
.modal-resize-handle.resizing {
    color: #38bdf8;
    transform: scale(1.25);
}

/* Minimized (mini-player) mode - small corner window, video keeps playing */
.modal-dialog.minimized {
    resize: none;
    min-width: 260px;
    min-height: 0;
    box-shadow: 0 15px 40px -8px rgba(0, 0, 0, 0.85), 0 0 0 1px rgba(255, 255, 255, 0.08);
}

.modal-dialog.minimized .modal-header {
    padding: 6px 10px;
}

.modal-dialog.minimized .video-title-display {
    font-size: 0.8rem;
}

.modal-dialog.minimized .modal-footer,
.modal-dialog.minimized .modal-resize-handle {
    display: none;
}

.modal-dialog.minimized .video-wrapper {
    min-height: 0;
    max-height: none;
}

.control-group {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
}

.control-group label,
.control-group span {
    white-space: nowrap;
    font-size: 0.82rem;
    color: var(--text-muted);
}

.select-input {
    background: var(--bg-dark);
    color: var(--text-main);
    border: 1px solid var(--bg-hover);
    padding: 4px 8px;
    border-radius: 4px;
    outline: none;
    max-width: 220px;
    min-width: 120px;
    font-size: 0.82rem;
}

.sync-value {
    min-width: 42px;
    text-align: center;
    font-weight: bold;
    color: var(--accent);
}

/* Toast */
.toast {
    position: fixed;
    top: 25px;
    left: 50%;
    transform: translateX(-50%) translateY(-100px);
    background-color: rgba(30, 41, 59, 0.95);
    color: var(--text-main);
    border: 1px solid var(--accent);
    font-weight: 600;
    padding: 9px 20px;
    border-radius: 20px;
    box-shadow: var(--shadow);
    transition: transform 0.3s cubic-bezier(0.18, 0.89, 0.32, 1.28);
    z-index: 99999;
    pointer-events: none;
}

.toast.show {
    transform: translateX(-50%) translateY(0);
}

.loading-spinner {
    grid-column: 1 / -1;
    text-align: center;
    padding: 60px 0;
    color: var(--text-muted);
    font-size: 1.1rem;
}

/* Responsive Breakpoints & Distorted Window Fixes */
@media (max-width: 960px) {
    .modal-footer {
        justify-content: flex-start;
        gap: 8px 14px;
    }
}

@media (max-width: 768px) {
    .navbar {
        padding: 10px 14px;
        gap: 10px;
    }
    .search-bar {
        order: 3;
        max-width: 100%;
        flex-basis: 100%;
    }
    .brand h1 {
        font-size: 1.15rem;
    }
    .toolbar-right {
        gap: 6px;
    }
    .btn-mode, .btn-layout, .sort-select {
        padding: 4px 8px;
        font-size: 0.78rem;
    }
    .video-grid.list-view .card-meta {
        font-size: 0.72rem;
        gap: 6px;
    }
    .video-grid.list-view .list-sub-col {
        gap: 8px;
    }
}

@media (max-width: 640px) {
    .navbar {
        padding: 10px 12px;
        gap: 8px;
    }
    .breadcrumb-container {
        flex-direction: column;
        align-items: stretch;
        gap: 8px;
    }
    .toolbar-right {
        width: 100%;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
        scrollbar-width: none;
        flex-wrap: nowrap;
        padding-bottom: 3px;
        gap: 6px;
    }
    .toolbar-right::-webkit-scrollbar {
        display: none;
    }
    .view-mode-toggle, .layout-toggle, .meta-toggle, .sort-select {
        flex-shrink: 0;
    }
    .modal-dialog {
        width: 98vw;
        max-height: 96vh;
        border-radius: 10px;
    }
    .modal-header-actions {
        display: flex;
        align-items: center;
        gap: 4px;
        overflow-x: auto;
        scrollbar-width: none;
        flex-wrap: nowrap;
    }
    .modal-header-actions .btn-small {
        flex-shrink: 0;
        padding: 5px 8px;
        font-size: 0.74rem;
    }
    .modal-footer {
        overflow-x: auto;
        scrollbar-width: none;
        flex-wrap: nowrap;
        gap: 8px;
        padding: 8px 10px;
    }
    .modal-footer::-webkit-scrollbar {
        display: none;
    }
    .control-group {
        flex-shrink: 0;
        gap: 4px;
    }
    .control-group .btn-small {
        padding: 4px 7px;
        font-size: 0.76rem;
    }
    .select-input {
        max-width: 130px;
        font-size: 0.78rem;
    }
    .subtitle-box {
        font-size: 1.05rem;
        bottom: 40px;
    }
}

/* Modal Drag & Action Buttons SVG alignment */
.drag-handle-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: var(--text-muted);
    cursor: grab;
    flex-shrink: 0;
    margin-right: 4px;
}
.drag-handle-icon svg {
    pointer-events: none;
}
.modal-header-actions .btn-small {
    display: inline-flex;
    align-items: center;
    gap: 4px;
}
.modal-footer .btn-small {
    display: inline-flex;
    align-items: center;
    gap: 4px;
}
.modal-resize-handle {
    display: flex;
    align-items: flex-end;
    justify-content: flex-end;
    padding: 3px;
    color: rgba(255, 255, 255, 0.3);
}
.modal-resize-handle svg {
    pointer-events: none;
}


/* Unified Navigation Switch Button between Explorer & Player */
.btn-nav-switch {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    text-decoration: none;
    color: var(--text-main);
    background: var(--bg-hover);
    border: 1px solid rgba(255, 255, 255, 0.08);
    padding: 7px 12px;
    border-radius: 7px;
    font-size: 0.84rem;
    font-weight: 600;
    transition: background-color 0.15s, border-color 0.15s, color 0.15s, box-shadow 0.15s;
    white-space: nowrap;
    flex-shrink: 0;
}

.btn-nav-switch:hover {
    background: rgba(56, 189, 248, 0.15);
    border-color: rgba(56, 189, 248, 0.45);
    color: var(--accent);
    box-shadow: 0 0 8px rgba(56, 189, 248, 0.2);
}

.btn-nav-switch svg {
    flex-shrink: 0;
}

```

---

## app.js

```javascript
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

// MyCloud Web Media Player Client App

let currentMode = 'folder'; // 'folder' or 'all'
let currentSort = localStorage.getItem('mycloud_sort_mode') || 'name_asc';
let currentLayout = localStorage.getItem('mycloud_layout_v2') || 'list'; // 'list' or 'grid' (default: list)
let currentDir = '';
let currentParentDir = null;
let currentDirs = [];
let currentVideos = [];
let activeVideo = null;

let parsedSubtitles = []; // array of { start: seconds, end: seconds, text: string, isTop: boolean }
let subtitleOffset = 0; // in seconds
let subScale = 1.0;
let subBgEnabled = localStorage.getItem('mycloud_sub_bg') !== 'false';
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

function centerModalDialog() {
    if (!modalDialog) return;
    modalDialog.style.margin = '0';
    const dialogWidth = modalDialog.offsetWidth || Math.min(window.innerWidth * 0.94, 1050);
    const dialogHeight = modalDialog.offsetHeight || Math.min(window.innerHeight * 0.88, 620);
    const left = Math.max(10, Math.round((window.innerWidth - dialogWidth) / 2));
    const top = Math.max(10, Math.round((window.innerHeight - dialogHeight) / 2));
    
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
        const minLeft = 10;
        const maxLeft = Math.max(10, window.innerWidth - dialogWidth - 10);
        const minTop = 10;
        const maxTop = Math.max(10, window.innerHeight - dialogHeight - 10);
        
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

const savedPlayerWidth = localStorage.getItem('mycloud_player_width');
const savedPlayerHeight = localStorage.getItem('mycloud_player_height');
if (savedPlayerWidth && modalDialog) modalDialog.style.width = savedPlayerWidth;
if (savedPlayerHeight && modalDialog) modalDialog.style.height = savedPlayerHeight;

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
        
        const minW = Math.min(380, window.innerWidth - 20);
        const maxW = window.innerWidth - 20;
        const minH = 240;
        const maxH = window.innerHeight - 20;
        
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
        if (fw) localStorage.setItem('mycloud_player_width', fw);
        if (fh) localStorage.setItem('mycloud_player_height', fh);
    };

    resizeHandle.addEventListener('pointerup', endResize);
    resizeHandle.addEventListener('pointercancel', endResize);

    // Double-click resize handle to reset to default size
    resizeHandle.addEventListener('dblclick', (e) => {
        e.stopPropagation();
        modalDialog.style.width = '';
        modalDialog.style.height = '';
        localStorage.removeItem('mycloud_player_width');
        localStorage.removeItem('mycloud_player_height');
        centerModalDialog();
        showToast('창 크기가 기본값으로 초기화되었습니다.');
    });
}

// -------------------------------------------------------------
// Auto Next Video & Playlist Navigation
// -------------------------------------------------------------
function playNextVideo() {
    const sortedVideos = getSortedVideos(currentVideos, currentSort);
    if (!sortedVideos || sortedVideos.length === 0 || !activeVideo) return;
    
    const currentIndex = sortedVideos.findIndex(v => v.rel_path === activeVideo.rel_path);
    if (currentIndex === -1) return;
    
    const nextIndex = currentIndex + 1;
    if (nextIndex < sortedVideos.length) {
        const nextVideo = sortedVideos[nextIndex];
        showToast(`다음 영상 자동 재생: ${nextVideo.name}`);
        openPlayer(encodeURIComponent(nextVideo.rel_path));
    } else {
        showToast('마지막 영상입니다.');
    }
}

function playPrevVideo() {
    const sortedVideos = getSortedVideos(currentVideos, currentSort);
    if (!sortedVideos || sortedVideos.length === 0 || !activeVideo) return;
    
    const currentIndex = sortedVideos.findIndex(v => v.rel_path === activeVideo.rel_path);
    if (currentIndex === -1) return;
    
    const prevIndex = currentIndex - 1;
    if (prevIndex >= 0) {
        const prevVideo = sortedVideos[prevIndex];
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

function isFullscreen() {
    return !!(document.fullscreenElement || document.webkitFullscreenElement);
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
    if (target.requestFullscreen) {
        target.requestFullscreen().catch(() => {});
    } else if (target.webkitRequestFullscreen) {
        target.webkitRequestFullscreen();
    }
}

function exitFullscreenSafe() {
    if (document.exitFullscreen) {
        document.exitFullscreen().catch(() => {});
    } else if (document.webkitExitFullscreen) {
        document.webkitExitFullscreen();
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
        width: modalDialog.style.width || `${rect.width}px`,
        height: modalDialog.style.height || `${rect.height}px`
    };

    const mw = 340;
    const left = Math.max(10, window.innerWidth - mw - 20);
    const top = Math.max(10, window.innerHeight - 250);

    modalDialog.classList.add('minimized');
    modalDialog.style.width = `${mw}px`;
    modalDialog.style.height = '';
    modalDialog.style.left = `${left}px`;
    modalDialog.style.top = `${top}px`;
    hasCustomPosition = true;
    isMinimized = true;
    updateMinimizeBtnUI();
}

function restoreFromMinimize() {
    if (!modalDialog || !isMinimized) return;
    modalDialog.classList.remove('minimized');
    if (preMinimizeGeometry) {
        modalDialog.style.left = `${preMinimizeGeometry.left}px`;
        modalDialog.style.top = `${preMinimizeGeometry.top}px`;
        modalDialog.style.width = preMinimizeGeometry.width;
        modalDialog.style.height = preMinimizeGeometry.height;
    }
    preMinimizeGeometry = null;
    isMinimized = false;
    updateMinimizeBtnUI();
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
    sec = Math.max(0, sec);
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = Math.floor(sec % 60);
    const ms = Math.round((sec - Math.floor(sec)) * 1000);
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
    cues.forEach((c, i) => {
        const start = Math.max(0, c.start + subtitleOffset);
        const rawEnd = c.end + subtitleOffset;
        const end = Math.max(start + 0.1, isFinite(rawEnd) ? rawEnd : finiteEndCap);
        // '&'/'<'/'>' have markup meaning inside a WebVTT cue payload (e.g.
        // <b>, <c>) - escape them so literal characters in the dialogue text
        // can't be misread as cue markup.
        const text = c.text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
        const posLine = c.isTop
            ? 'line:8% position:50% align:center'
            : 'line:90% position:50% align:center';
        vtt += `${i + 1}\n${formatVttTime(start)} --> ${formatVttTime(end)} ${posLine}\n${text}\n\n`;
    });
    return vtt;
}

let currentVttBlobUrl = null;

// Uses a real <track> element fed a WebVTT blob (rather than a bare
// addTextTrack()/addCue() track) - this is the standards-compliant way to
// supply native captions for fullscreen.
//
// NOTE: an earlier version of this player also had a Picture-in-Picture
// button that switched to this same native track. It was removed - Chrome's
// PiP window doesn't render captions at all, regardless of how the track is
// supplied (see https://issues.chromium.org/issues/40581723, still open).
// Document Picture-in-Picture (which *can* show arbitrary DOM, including our
// custom subtitle overlay) would work around this, but requires HTTPS, which
// this NAS doesn't serve. Don't re-add a PiP button without addressing that.
function syncCuesToTextTrack() {
    if (!videoPlayer) return;
    const trackEl = document.getElementById('webplayer-native-track');
    if (!trackEl) return;

    if (currentVttBlobUrl) {
        URL.revokeObjectURL(currentVttBlobUrl);
        currentVttBlobUrl = null;
    }

    if (parsedSubtitles.length === 0) {
        trackEl.removeAttribute('src');
        return;
    }

    const blob = new Blob([buildVttText(parsedSubtitles)], { type: 'text/vtt' });
    currentVttBlobUrl = URL.createObjectURL(blob);
    trackEl.src = currentVttBlobUrl;

    // Reassigning `src` resets the track's mode to "disabled" - reapply
    // whatever visibility state we're currently in (fullscreen uses the
    // native track; the windowed player uses the custom DOM overlay instead).
    if (trackEl.track) {
        trackEl.track.mode = isFullscreen() ? 'showing' : 'hidden';
    }
}

function handleFullscreenSubtitleSync() {
    let track = null;
    if (videoPlayer && videoPlayer.textTracks) {
        for (let i = 0; i < videoPlayer.textTracks.length; i++) {
            if (videoPlayer.textTracks[i].label === 'WebPlayerSub') {
                track = videoPlayer.textTracks[i];
                break;
            }
        }
    }
    
    const isFs = isFullscreen();
    if (isFs) {
        // Native video element fullscreen: show native WebVTT cues mirroring custom settings
        if (track) track.mode = "showing";
        if (subtitleBox) subtitleBox.style.display = "none";
    } else {
        // Windowed floating player: hide native cues, show rich DOM overlay
        if (track) track.mode = "hidden";
        updateSubtitleDisplay();
    }
    applySubtitleStyle();
}

function handleFullscreenChange() {
    const fsElem = document.fullscreenElement || document.webkitFullscreenElement;
    const isFs = !!fsElem;

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
    const SEARCH_WINDOW_SEC = 60; // widened from 30s as a safety margin for long-running cues (e.g. opening-theme lyric blocks) that aren't the special-cased open-ended last cue
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
async function loadData(dir = currentDir, mode = currentMode) {
    currentMode = mode;
    currentDir = dir;
    
    if (modeFolderBtn && modeAllBtn) {
        modeFolderBtn.classList.toggle('active', currentMode === 'folder');
        modeAllBtn.classList.toggle('active', currentMode === 'all');
    }
    
    videoGrid.innerHTML = '<div class="loading-spinner">항목을 불러오는 중입니다...</div>';
    
    try {
        let apiUrl = 'api.php';
        if (currentMode === 'all') {
            apiUrl += '?all=1';
        } else if (dir) {
            apiUrl += '?dir=' + encodeURIComponent(dir);
        }
        
        const resp = await fetch(apiUrl);
        const data = await resp.json();
        
        if (!data.success) {
            // data.error is server-controlled and currently always a static
            // string, but escaping here costs nothing and means a future
            // change on the PHP side can never turn this into an XSS sink.
            videoGrid.innerHTML = `<div class="loading-spinner">오류: ${escapeHtml(data.error)}</div>`;
            return;
        }
        
        currentVideos = data.videos || [];
        currentDirs = data.dirs || [];
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
// OPT-2: Sort result cache — avoid re-sorting on every keystroke / re-render
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
            result = copy.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' })); break;
        case 'name_desc':
            result = copy.sort((a, b) => b.name.localeCompare(a.name, undefined, { numeric: true, sensitivity: 'base' })); break;
        case 'date_desc':
            result = copy.sort((a, b) => (b.mtime || 0) - (a.mtime || 0)); break;
        case 'date_asc':
            result = copy.sort((a, b) => (a.mtime || 0) - (b.mtime || 0)); break;
        case 'size_desc':
            result = copy.sort((a, b) => (b.size || 0) - (a.size || 0)); break;
        default:
            result = copy.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' }));
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
        ? copy.sort((a, b) => b.name.localeCompare(a.name, undefined, { numeric: true, sensitivity: 'base' }))
        : copy.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' }));
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
            targetVideos = targetVideos.filter(v => 
                v.name.toLowerCase().includes(query) || (v.folder && v.folder.toLowerCase().includes(query))
            );
            renderGrid([], targetVideos);
            return;
        } else {
            targetDirs = targetDirs.filter(d => d.name.toLowerCase().includes(query));
            targetVideos = targetVideos.filter(v => v.name.toLowerCase().includes(query));
            
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
        localStorage.setItem('mycloud_sort_mode', currentSort);
        applySortAndRender();
    });
}

function setLayoutMode(mode) {
    currentLayout = mode;
    localStorage.setItem('mycloud_layout_v2', mode);
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
let showFileMeta = localStorage.getItem('mycloud_show_file_meta') === 'true'; // defaults to false (hidden)

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
        localStorage.setItem('mycloud_show_file_meta', 'false');
        applyMetaVisibility();
        showToast('파일 날짜 및 용량을 숨겼습니다.');
    });
}
if (metaShowBtn) {
    metaShowBtn.addEventListener('click', () => {
        showFileMeta = true;
        localStorage.setItem('mycloud_show_file_meta', 'true');
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
// 3. Open Video Player & Subtitle Management
// -------------------------------------------------------------
window.openPlayer = async function(encodedRelPath) {
    const relPath = decodeURIComponent(encodedRelPath);
    const video = currentVideos.find(v => v.rel_path === relPath);
    if (!video) return;
    
    activeVideo = video;
    document.title = `${video.name} - MyCloud Media Player`;
    if (playerTitleText) {
        playerTitleText.textContent = video.name;
    } else if (playerTitle) {
        playerTitle.textContent = video.name;
    }
    if (downloadLink) downloadLink.href = video.url;
    videoPlayer.src = video.url;
    
    clearSubtitles();
    
    // 1. Add external subtitles to list
    currentAvailableTracks = [];
    if (video.subtitles && video.subtitles.length > 0) {
        video.subtitles.forEach(s => {
            currentAvailableTracks.push({
                type: 'external',
                label: `[외부-${s.ext.toUpperCase()}] ${s.filename}`,
                url: s.url,
                ext: s.ext,
                lang: s.ext
            });
        });
    }
    
    renderSubtitleDropdown(currentAvailableTracks, '내장 자막 확인 중...');
    
    playerModal.classList.add('active');
    applySubtitleStyle();
    
    if (!hasCustomPosition) {
        centerModalDialog();
        requestAnimationFrame(() => centerModalDialog());
    }
    
    setupMediaSession(video);
    videoPlayer.play().catch(() => {});
    
    // 2. Probe embedded subtitle tracks with AbortController and race condition guard
    if (currentProbeAbortController) {
        currentProbeAbortController.abort();
    }
    if (currentSubAbortController) {
        currentSubAbortController.abort();
    }
    currentProbeAbortController = new AbortController();
    const probeSignal = currentProbeAbortController.signal;
    
    try {
        const probeResp = await fetch(`api.php?action=probe_subs&video=${encodeURIComponent(video.rel_path)}`, { signal: probeSignal });
        const probeData = await probeResp.json();
        
        // Guard against race condition: ensure this response matches active video
        if (!activeVideo || activeVideo.rel_path !== video.rel_path) return;
        
        if (probeData.success && probeData.subtitles && probeData.subtitles.length > 0) {
            probeData.subtitles.forEach(emb => {
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
    } catch (e) {
        if (e.name !== 'AbortError') {
            console.warn('Subtitle probe failed:', e);
        }
    }
    
    if (!activeVideo || activeVideo.rel_path !== video.rel_path) return;
    renderSubtitleDropdown(currentAvailableTracks, null);
    
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
let currentProbeAbortController = null;
let currentSubAbortController = null;

async function loadSelectedTrack(track) {
    clearSubtitles();
    if (!track) return;
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
        
        if (!resp.body || isSami) {
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
        let updateTimer = null;
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            if (activeVideo !== requestedVideo) return;
            rawBuffer += decoder.decode(value, { stream: true });
            
            if (isAss) {
                parsedSubtitles = parseASS(rawBuffer);
            } else {
                parsedSubtitles = parseSRT(rawBuffer);
            }
            
            if (parsedSubtitles.length !== lastReportedCount) {
                lastReportedCount = parsedSubtitles.length;
                syncCuesToTextTrack();
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
        
        if (activeVideo !== requestedVideo) return;
        rawBuffer += decoder.decode();
        if (isAss) parsedSubtitles = parseASS(rawBuffer);
        else parsedSubtitles = parseSRT(rawBuffer);

        if (parsedSubtitles.length > 0) {
            subtitleMemoryCache.set(cacheKey, parsedSubtitles);
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

function parseTimestamp(str) {
    if (!str) return 0;
    const parts = str.trim().replace(',', '.').split(':');
    if (parts.length === 3) {
        return parseFloat(parts[0]) * 3600 + parseFloat(parts[1]) * 60 + parseFloat(parts[2]);
    } else if (parts.length === 2) {
        return parseFloat(parts[0]) * 60 + parseFloat(parts[1]);
    }
    return parseFloat(parts[0]) || 0;
}

function parseSRT(srtText) {
    const cues = [];
    const normalized = srtText.replace(/\r\n|\r/g, '\n');
    const blocks = normalized.split('\n\n');
    
    for (const block of blocks) {
        const lines = block.trim().split('\n');
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
                const isTop = rawText.includes('{\\an8}') || rawText.includes('{\\an7}') || rawText.includes('{\\an9}');
                
                // Keep '\n' as a real newline here rather than an HTML '<br>' -
                // the text is untrusted (comes straight from the video file's
                // subtitle track) and still needs to pass through escapeHtml()
                // at render time before touching innerHTML. '<br>' insertion
                // happens after escaping, in updateSubtitleDisplay().
                let cleanText = rawText
                    .replace(/\{[^}]+\}/g, '')
                    .replace(/<[^>]+>/g, '')
                    .trim();

                if (cleanText && end > start) {
                    cues.push({ start, end, text: cleanText, isTop });
                }
            }
        }
    }
    cues.sort((a, b) => a.start - b.start);
    return cues;
}

function parseASS(assText) {
    const cues = [];
    const lines = assText.replace(/\r\n|\r/g, '\n').split('\n');
    for (const line of lines) {
        if (line.startsWith('Dialogue:')) {
            const commaIdx = line.indexOf(':');
            const parts = line.substring(commaIdx + 1).split(',');
            if (parts.length >= 10) {
                const start = parseTimestamp(parts[1].trim());
                const end = parseTimestamp(parts[2].trim());
                const rawText = parts.slice(9).join(',');
                
                const isTop = rawText.includes('{\\an8}') || rawText.includes('{\\an7}') || rawText.includes('{\\an9}');
                
                // '\n' / ' ' here are real newline/NBSP characters, not
                // HTML - see the note in parseSRT() about why this text still
                // has to go through escapeHtml() before touching innerHTML.
                let cleanText = rawText
                    .replace(/\{[^}]+\}/g, '')
                    .replace(/\\N/g, '\n')
                    .replace(/\\n/g, '\n')
                    .replace(/\\h/g, ' ')
                    .trim();

                if (cleanText && end > start) {
                    cues.push({ start, end, text: cleanText, isTop });
                }
            }
        }
    }
    cues.sort((a, b) => a.start - b.start);
    return cues;
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
        content = content
            .replace(/&nbsp;/gi, ' ')
            .replace(/&amp;/gi, '&')
            .replace(/&lt;/gi, '<')
            .replace(/&gt;/gi, '>')
            .replace(/&quot;/gi, '"')
            .replace(/&#39;/gi, "'");
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
            // 빈 SYNC = 이전 자막의 종료 시각
            const prev = cues[cues.length - 1];
            if (startSec > prev.start) {
                prev.end = startSec;
            }
        }
    }

    // 겹침 방지: 다음 자막 시작 전에 끝나도록 보정
    for (let i = 0; i < cues.length - 1; i++) {
        if (cues[i].end > cues[i + 1].start) {
            cues[i].end = cues[i + 1].start;
        }
    }

    cues.sort((a, b) => a.start - b.start);
    return cues;
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
    subScale = Math.max(0.6, Math.min(3.0, newScale));
    localStorage.setItem('mycloud_sub_scale', subScale);
    applySubtitleStyle();
}

if (subBgToggleBtn) {
    subBgToggleBtn.addEventListener('click', () => {
        subBgEnabled = !subBgEnabled;
        localStorage.setItem('mycloud_sub_bg', subBgEnabled ? 'true' : 'false');
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

customSubBtn.addEventListener('click', () => customSubInput.click());
customSubInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const ext = file.name.split('.').pop().toLowerCase();
    const track = {
        type: 'external',
        label: `[로컬 파일] ${file.name}`,
        url: URL.createObjectURL(file),
        ext: ext,
        lang: ext
    };
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
    videoPlayer.pause();
    videoPlayer.src = '';
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
    if (e.target.matches('input, select, textarea') || e.target.isContentEditable) {
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
            videoPlayer.currentTime = Math.min(videoPlayer.duration || 0, videoPlayer.currentTime + step);
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
            localStorage.setItem('mycloud_sub_bg', subBgEnabled ? 'true' : 'false');
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

function showToast(msg) {
    if (!toastEl) return;
    toastEl.textContent = msg;
    toastEl.classList.add('show');
    setTimeout(() => toastEl.classList.remove('show'), 2500);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// BUG-6: encodeURIComponent deliberately does not encode ' (apostrophe), which
// would break onclick="openFolder('value')" when the path contains one.
// pathEncode adds that missing step so all filesystem paths are safe in onclick attrs.
function pathEncode(path) {
    return encodeURIComponent(path || '').replace(/'/g, '%27');
}

window.addEventListener('resize', () => {
    if (!playerModal.classList.contains('active')) return;
    // Clamp dialog size to fit new window dimensions (BUG-3: merged from removed inner handler)
    if (modalDialog) {
        const maxW = window.innerWidth - 20;
        const maxH = window.innerHeight - 20;
        if (modalDialog.offsetWidth > maxW) modalDialog.style.width = `${maxW}px`;
        if (modalDialog.offsetHeight > maxH) modalDialog.style.height = `${maxH}px`;
    }
    // Clamp dialog position to keep it on screen
    if (hasCustomPosition) {
        const rect = modalDialog.getBoundingClientRect();
        const maxLeft = Math.max(10, window.innerWidth - modalDialog.offsetWidth - 10);
        const maxTop = Math.max(10, window.innerHeight - modalDialog.offsetHeight - 10);
        if (rect.left > maxLeft || rect.top > maxTop || rect.left < 10 || rect.top < 10) {
            modalDialog.style.left = `${Math.max(10, Math.min(rect.left, maxLeft))}px`;
            modalDialog.style.top = `${Math.max(10, Math.min(rect.top, maxTop))}px`;
        }
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
        const found = currentVideos.find(v => v.rel_path === cleanPath || v.rel_path.endsWith('/' + cleanPath) || cleanPath.endsWith(v.rel_path));
        if (found) {
            openPlayer(encodeURIComponent(found.rel_path));
        } else {
            // If not found in parent folder, try searching in all mode
            await loadData('', 'all');
            const foundAll = currentVideos.find(v => v.rel_path === cleanPath || v.rel_path.endsWith('/' + cleanPath) || cleanPath.endsWith(v.rel_path));
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
            videoPlayer.currentTime = Math.min(videoPlayer.currentTime + skipTime, videoPlayer.duration || 0);
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
    
    // Toggle play/pause by clicking directly on video element
    videoPlayer.addEventListener('click', (e) => {
        if (e.target !== videoPlayer) return;
        if (videoPlayer.paused) {
            videoPlayer.play().catch(() => {});
        } else {
            videoPlayer.pause();
        }
    });
}

```

---

## api.php

```php
<?php
header('Access-Control-Allow-Origin: *');
@setlocale(LC_ALL, 'C.UTF-8');

function safeShellArg($arg) {
    return "'" . str_replace("'", "'\\''", $arg) . "'";
}

// realpath()-resolved $path is only really "inside" $base when it equals $base
// or starts with "$base/" - a bare strpos($path, $base) === 0 check also lets
// a sibling directory through, e.g. resolved "/shares/Public-evil/x" would
// pass a check against base "/shares/Public" since the string itself matches
// as a prefix even though the directory is not a descendant.

// Security: Prevent path traversal and double URL encoding (%252e%252e, %00, null bytes)
function validateRelativePath($path) {
    if (!is_string($path)) return false;
    $decoded = rawurldecode($path);
    if (strpos($path, '..') !== false || strpos($path, "\0") !== false) return false;
    if (strpos($decoded, '..') !== false || strpos($decoded, "\0") !== false) return false;
    return true;
}

// 32-bit PHP integer overflow protection for large video files (> 2GB)
function getSafeFileSize($fullPath) {
    $size = @filesize($fullPath);
    if ($size !== false && $size > 0 && $size <= 1073741824) {
        return (string)$size;
    }
    $cmd = 'timeout 3 stat -c "%s" -- ' . safeShellArg($fullPath) . ' 2>/dev/null';
    $out = trim(@shell_exec($cmd));
    if ($out !== '' && ctype_digit($out)) {
        return $out;
    }
    if ($size !== false && $size > 0) {
        return sprintf("%.0f", (float)$size);
    }
    return '0';
}

function isWithinBaseDir($resolved, $base) {
    return $resolved === $base || strpos($resolved, $base . '/') === 0;
}

// WD My Cloud /shares/Public is a symlink to /DataVolume/shares/Public
$baseDir = realpath('/shares/Public');
if ($baseDir === false) {
    $baseDir = '/shares/Public';
}

$videoExts = array('mp4', 'mkv', 'webm', 'mov', 'avi', 'm4v', 'flv');
$subExts = array('smi', 'sami', 'srt', 'ass', 'ssa', 'vtt');
$ignoreList = array('.', '..', 'webplayer', 'incomplete', 'lost+found', '.DS_Store', 'Thumbs.db', 'desktop.ini', '.thumb');

// Helper: Make Apache Web URL from relative path
function makeWebUrl($relPath) {
    $parts = explode('/', trim(str_replace('\\', '/', $relPath), '/'));
    $encoded = array_map('rawurlencode', $parts);
    return '/media/' . implode('/', $encoded);
}

// Helper: Format bytes - pure integer branch without log() / pow() (Item 9)
function formatBytes($bytes, $precision = 2) {
    $bytes = (float)$bytes;
    if ($bytes <= 0) return '0 B';
    if ($bytes < 1024) return $bytes . ' B';
    if ($bytes < 1048576) return round($bytes / 1024, $precision) . ' KB';
    if ($bytes < 1073741824) return round($bytes / 1048576, $precision) . ' MB';
    if ($bytes < 1099511627776) return round($bytes / 1073741824, $precision) . ' GB';
    return round($bytes / 1099511627776, $precision) . ' TB';
}

// -------------------------------------------------------------
// Action 1: Probe embedded subtitle streams in video (~0.5s)
// -------------------------------------------------------------
if (isset($_GET['action']) && $_GET['action'] === 'probe_subs') {
    header('Content-Type: application/json; charset=utf-8');
    $videoRel = isset($_GET['video']) ? trim($_GET['video'], " /\\") : '';
    if (empty($videoRel) || !validateRelativePath($videoRel)) {
        echo json_encode(array('success' => false, 'error' => 'Invalid video path'));
        exit;
    }
    $fullVideoPath = realpath($baseDir . '/' . $videoRel);
    if ($fullVideoPath === false || !isWithinBaseDir($fullVideoPath, $baseDir) || !file_exists($fullVideoPath) || is_link($fullVideoPath)) {
        echo json_encode(array('success' => false, 'error' => 'File not found'));
        exit;
    }
    
    // 1. High-speed zero-disk pure Python MKV probe (< 0.05s vs 2.5s avconv)
    $fastCmd = 'python /shares/webplayer/stream_sub.py probe ' . safeShellArg($fullVideoPath) . ' 2>/dev/null';
    $fastOut = @shell_exec($fastCmd);
    if (!empty($fastOut)) {
        $fastJson = @json_decode($fastOut, true);
        if ($fastJson && isset($fastJson['success']) && $fastJson['success'] && !empty($fastJson['subtitles'])) {
            echo $fastOut;
            exit;
        }
    }

    // 2. Fallback to avconv probe for non-MKV or unusual streams
    $cmd = 'export LANG=C.UTF-8 && export LC_ALL=C.UTF-8 && export LD_LIBRARY_PATH=/usr/local/wdmcserver/lib && /usr/local/wdmcserver/bin/avconv -probesize 65536 -analyzeduration 1000000 -i ' . safeShellArg($fullVideoPath) . ' 2>&1';
    $output = @shell_exec($cmd);
    
    $subs = array();
    $lines = explode("\n", $output);
    foreach ($lines as $line) {
        if (preg_match('/Stream #0[.:](\d+)(?:\(([^)]+)\))?: Subtitle: ([^,\n\r]+)/i', $line, $m)) {
            $s_id = $m[1];
            $lang = strtolower(trim($m[2]));
            if (empty($lang)) $lang = 'und';
            $codec = strtolower(trim($m[3]));
            
            $langLabel = strtoupper($lang);
            if ($lang === 'kor' || $lang === 'ko' || $lang === 'korean') $langLabel = '한국어';
            else if ($lang === 'eng' || $lang === 'en' || $lang === 'english') $langLabel = '영어';
            else if ($lang === 'jpn' || $lang === 'ja' || $lang === 'japanese') $langLabel = '일본어';
            else if ($lang === 'chi' || $lang === 'zh' || $lang === 'chinese') $langLabel = '중국어';
            else if ($lang === 'fre' || $lang === 'fra' || $lang === 'fr') $langLabel = '프랑스어';
            else if ($lang === 'ger' || $lang === 'deu' || $lang === 'de') $langLabel = '독일어';
            else if ($lang === 'spa' || $lang === 'es') $langLabel = '스페인어';
            else if ($lang === 'rus' || $lang === 'ru') $langLabel = '러시아어';
            
            $isDef = stripos($line, '(default)') !== false;
            $isForced = stripos($line, '(forced)') !== false;
            
            $codecLabel = 'SRT';
            if (stripos($codec, 'ass') !== false || stripos($codec, 'ssa') !== false) {
                $codecLabel = 'ASS';
            }
            
            $label = '[내장-' . $langLabel . '] ' . $langLabel . ' 자막 (' . $codecLabel . ')';
            if ($isForced) $label .= ' [강제/일부]';
            else if ($isDef) $label .= ' [기본]';
            
            $subs[] = array(
                'stream_id' => $s_id,
                'lang' => $lang,
                'lang_label' => $langLabel,
                'label' => $label,
                'codec' => $codecLabel,
                'is_default' => $isDef,
                'is_forced' => $isForced,
                'embedded' => true
            );
        }
    }
    
    // Sort: Korean first, then English, then others; non-forced first
    usort($subs, function($a, $b) {
        $aKor = ($a['lang'] === 'kor' || $a['lang'] === 'ko') ? 0 : 1;
        $bKor = ($b['lang'] === 'kor' || $b['lang'] === 'ko') ? 0 : 1;
        if ($aKor !== $bKor) return $aKor - $bKor;
        
        $aForced = $a['is_forced'] ? 1 : 0;
        $bForced = $b['is_forced'] ? 1 : 0;
        if ($aForced !== $bForced) return $aForced - $bForced;
        
        return 0;
    });
    
    echo json_encode(array('success' => true, 'subtitles' => $subs), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

// -------------------------------------------------------------
// Action 2: On-demand Zero-Disk Stream Subtitle directly to client
// -------------------------------------------------------------
if (isset($_GET['action']) && $_GET['action'] === 'stream_sub') {
    $videoRel = isset($_GET['video']) ? trim($_GET['video'], " /\\") : '';
    $streamId = isset($_GET['stream']) ? intval($_GET['stream']) : 0;
    $codec = isset($_GET['codec']) ? strtolower(trim($_GET['codec'])) : 'srt';
    if (!in_array($codec, array('srt', 'vtt', 'ass', 'ssa'), true)) {
        $codec = 'srt';
    }

    if (empty($videoRel) || !validateRelativePath($videoRel)) {
        header('HTTP/1.1 400 Bad Request');
        echo "Invalid video path";
        exit;
    }
    $fullVideoPath = realpath($baseDir . '/' . $videoRel);
    if ($fullVideoPath === false || !isWithinBaseDir($fullVideoPath, $baseDir) || !file_exists($fullVideoPath) || is_link($fullVideoPath)) {
        header('HTTP/1.1 404 Not Found');
        echo "File not found";
        exit;
    }
    
    // Disable any output buffering for immediate progressive streaming
    if (function_exists('apache_setenv')) {
        @apache_setenv('no-gzip', '1');
    }
    @ini_set('zlib.output_compression', '0');
    @ini_set('implicit_flush', '1');
    while (ob_get_level()) {
        @ob_end_flush();
    }
    
    header('Content-Type: text/plain; charset=utf-8');
    header('Cache-Control: no-cache, no-store, must-revalidate');
    header('Pragma: no-cache');
    header('Expires: 0');
    header('X-Accel-Buffering: no');
    
    // Volatile RAM cache in /tmp (tmpfs in RAM: 0 disk space on HDD, instant 2ms delivery)
    $tmpDir = '/tmp/webplayer_sub_ram';
    if (is_link($tmpDir)) {
        @unlink($tmpDir);
    }
    if (!is_dir($tmpDir)) {
        @mkdir($tmpDir, 0777, true);
    }
    $cacheFile = $tmpDir . '/' . md5($fullVideoPath . ':' . $streamId . ':' . filemtime($fullVideoPath)) . '.' . $codec;
    if (file_exists($cacheFile) && filesize($cacheFile) > 0) {
        readfile($cacheFile);
        exit;
    }
    
    // Unified zero-disk high-speed stream with process supervision & orphan prevention
    $cmd = 'exec python /shares/webplayer/stream_sub.py ' . safeShellArg($fullVideoPath) . ' ' . $streamId;
    $descriptors = array(
        0 => array('pipe', 'r'),
        1 => array('pipe', 'w'),
        2 => array('file', '/dev/null', 'w')
    );
    $procEnv = array('LANG' => 'C.UTF-8', 'LC_ALL' => 'C.UTF-8');
    $proc = @proc_open($cmd, $descriptors, $pipes, null, $procEnv);
    $cacheFp = @fopen($cacheFile . '.tmp', 'wb');
    
    if (is_resource($proc)) {
        fclose($pipes[0]);
        stream_set_blocking($pipes[1], 1);
        stream_set_timeout($pipes[1], 15);
        
        while (!feof($pipes[1])) {
            if (connection_aborted()) {
                @proc_terminate($proc, 9);
                break;
            }
            $buffer = fread($pipes[1], 8192);
            $meta = stream_get_meta_data($pipes[1]);
            if ($meta['timed_out']) {
                @proc_terminate($proc, 9);
                break;
            }
            if ($buffer !== false && strlen($buffer) > 0) {
                echo $buffer;
                flush();
                if ($cacheFp) {
                    fwrite($cacheFp, $buffer);
                }
            }
        }
        fclose($pipes[1]);
        
        if (connection_aborted()) {
            @proc_terminate($proc, 9);
            @proc_close($proc);
            if ($cacheFp) {
                fclose($cacheFp);
                @unlink($cacheFile . '.tmp');
            }
            exit;
        }
        
        @proc_close($proc);
        if ($cacheFp) {
            fclose($cacheFp);
            @rename($cacheFile . '.tmp', $cacheFile);
        }
    }
    
    // Strict volatile RAM cache auto-prune (protect 226MB RAM)
    $now = time();
    $tmpFiles = @glob($tmpDir . '/*.tmp');
    if ($tmpFiles) {
        foreach ($tmpFiles as $tf) {
            if ($now - @filemtime($tf) > 120) {
                @unlink($tf);
            }
        }
    }
    $ramFiles = @glob($tmpDir . '/*');
    if ($ramFiles && count($ramFiles) > 15) {
        usort($ramFiles, function($a, $b) { return filemtime($a) - filemtime($b); });
        while (count($ramFiles) > 10) {
            $old = array_shift($ramFiles);
            @unlink($old);
        }
    }
    exit;
}

header('Content-Type: application/json; charset=utf-8');
$mode = isset($_GET['all']) && $_GET['all'] == '1' ? 'all' : 'folder';

if ($mode === 'all') {
    $allVideos = array();
    $allSubs = array();
    
    $scanRecursive = function($dir, $depth = 0) use (&$scanRecursive, &$allVideos, &$allSubs, $baseDir, $videoExts, $subExts, $ignoreList) {
        if ($depth > 8 || count($allVideos) >= 2500) return;
        $items = @scandir($dir);
        if ($items === false) return;
        
        foreach ($items as $item) {
            if (in_array($item, $ignoreList) || $item[0] === '.') continue;
            $fullPath = $dir . '/' . $item;
            
            if (is_link($fullPath)) continue;
            if (is_dir($fullPath)) {
                $scanRecursive($fullPath, $depth + 1);
            } else if (is_file($fullPath)) {
                $ext = strtolower(pathinfo($item, PATHINFO_EXTENSION));
                $relPath = ltrim(substr($fullPath, strlen($baseDir)), '/\\');
                $folderRel = ltrim(substr($dir, strlen($baseDir)), '/\\');
                $baseName = pathinfo($item, PATHINFO_FILENAME);
                
                if (in_array($ext, $videoExts)) {
                    $sizeStr = getSafeFileSize($fullPath);
                    $size = (float)$sizeStr;
                    if ($size <= 0) continue;
                    $mtime = @filemtime($fullPath);
                    $allVideos[] = array(
                        'name' => $item,
                        'basename' => $baseName,
                        'ext' => $ext,
                        'folder' => $folderRel,
                        'rel_path' => $relPath,
                        'url' => makeWebUrl($relPath),
                        'size' => $size,
                        'size_formatted' => formatBytes($size),
                        'mtime' => $mtime,
                        'mtime_formatted' => date('Y-m-d', $mtime),
                        'subtitles' => array()
                    );
                } else if (in_array($ext, $subExts)) {
                    $allSubs[] = array(
                        'filename' => $item,
                        'basename' => $baseName,
                        'ext' => $ext,
                        'folder' => $folderRel,
                        'rel_path' => $relPath,
                        'url' => makeWebUrl($relPath)
                    );
                }
            }
        }
    };
    
    $scanRecursive($baseDir);

    // Group subs by folder first so each video only scans its own folder's
    // subs instead of every sub in the whole library (was O(videos * subs) -
    // on a big flat collection that's millions of comparisons on a 650MHz CPU).
    $subsByFolder = array();
    foreach ($allSubs as $sub) {
        $subsByFolder[$sub['folder']][] = $sub;
    }

    foreach ($allVideos as &$video) {
        if (!isset($subsByFolder[$video['folder']])) continue;
        $vidBase = $video['basename'];
        foreach ($subsByFolder[$video['folder']] as $sub) {
            $subBase = $sub['basename'];
            if ($subBase === $vidBase || strpos($subBase, $vidBase) === 0) {
                $video['subtitles'][] = $sub;
            }
        }
    }
    unset($video);
    
    usort($allVideos, function($a, $b) {
        return strnatcasecmp($a['name'], $b['name']);
    });
    
    $etag = '"' . md5($baseDir . ':' . @filemtime($baseDir) . ':' . count($allVideos)) . '"';
    header('ETag: ' . $etag);
    if (isset($_SERVER['HTTP_IF_NONE_MATCH']) && trim($_SERVER['HTTP_IF_NONE_MATCH']) === $etag) {
        header('HTTP/1.1 304 Not Modified');
        exit;
    }

    echo json_encode(array(
        'success' => true,
        'mode' => 'all',
        'current_dir' => '',
        'parent_dir' => null,
        'dirs' => array(),
        'videos' => $allVideos,
        'count' => count($allVideos)
    ), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PARTIAL_OUTPUT_ON_ERROR);
    exit;
}

// Mode: Folder navigation
$requestDir = isset($_GET['dir']) ? trim($_GET['dir'], " /\\") : '';
$targetDir = $baseDir;

if ($requestDir !== '') {
    if (!validateRelativePath($requestDir)) {
        echo json_encode(array('success' => false, 'error' => 'Path traversal prohibited'));
        exit;
    }
    $resolved = realpath($baseDir . '/' . $requestDir);
    if ($resolved !== false && isWithinBaseDir($resolved, $baseDir) && is_dir($resolved) && !is_link($resolved)) {
        $targetDir = $resolved;
    } else {
        echo json_encode(array('success' => false, 'error' => 'Invalid directory path'));
        exit;
    }
}

// Compute parent dir
$parentDir = null;
if ($requestDir !== '') {
    $parent = dirname($requestDir);
    $parentDir = ($parent === '.' || $parent === '/' || $parent === '') ? '' : $parent;
}

$items = @scandir($targetDir);
if ($items === false) {
    echo json_encode(array('success' => false, 'error' => 'Cannot read directory'));
    exit;
}

$subtitlesMap = array();
$allFiles = array();
$rawDirs = array();

foreach ($items as $item) {
    if (in_array($item, $ignoreList) || $item[0] === '.') continue;
    $fullPath = $targetDir . '/' . $item;
    if (is_link($fullPath)) continue;
    
    if (is_dir($fullPath)) {
        $rawDirs[] = $item;
    } else if (is_file($fullPath)) {
        $ext = strtolower(pathinfo($item, PATHINFO_EXTENSION));
        $allFiles[] = $item;
        if (in_array($ext, $subExts)) {
            $baseName = pathinfo($item, PATHINFO_FILENAME);
            $subRel = ($requestDir ? $requestDir . '/' : '') . $item;
            $subtitlesMap[$item] = array(
                'filename' => $item,
                'basename' => $baseName,
                'ext' => $ext,
                'path' => $subRel,
                'url' => makeWebUrl($subRel)
            );
        }
    }
}

$dirs = array();
// OPT-4: Cap per-folder scandir calls. If there are many subdirs, skipping the
// count is cheaper than doing N extra scandir() calls on a slow HDD NAS.
$scanSubdirCounts = count($rawDirs) <= 30;
foreach ($rawDirs as $d) {
    $dRel = ($requestDir ? $requestDir . '/' : '') . $d;
    $dFull = $targetDir . '/' . $d;
    
    $vidCount = 0;
    $subDirCount = 0;
    if ($scanSubdirCounts) {
        $subItems = @scandir($dFull);
        if ($subItems !== false) {
            foreach ($subItems as $si) {
                if ($si[0] === '.' || in_array($si, $ignoreList)) continue;
                $dotPos = strrpos($si, '.');
                if ($dotPos !== false) {
                    $siExt = strtolower(substr($si, $dotPos + 1));
                    if (in_array($siExt, $videoExts)) {
                        $vidCount++;
                        continue;
                    }
                }
                if (is_dir($dFull . '/' . $si)) {
                    $subDirCount++;
                }
            }
        }
    }
    
    $dirs[] = array(
        'name' => $d,
        'rel_path' => $dRel,
        'video_count' => $vidCount,
        'subdir_count' => $subDirCount
    );
}

$videos = array();
foreach ($allFiles as $item) {
    $ext = strtolower(pathinfo($item, PATHINFO_EXTENSION));
    if (!in_array($ext, $videoExts)) continue;
    
    $baseName = pathinfo($item, PATHINFO_FILENAME);
    $fullPath = $targetDir . '/' . $item;
    if (is_link($fullPath)) continue;
    $sizeStr = getSafeFileSize($fullPath);
    $size = (float)$sizeStr;
    if ($size <= 0) continue;
    $mtime = @filemtime($fullPath);
    
    $matchedSubs = array();
    foreach ($subtitlesMap as $subItem => $subInfo) {
        $subBase = $subInfo['basename'];
        if ($subBase === $baseName || strpos($subBase, $baseName) === 0) {
            $matchedSubs[] = $subInfo;
        }
    }
    
    $relPath = ($requestDir ? $requestDir . '/' : '') . $item;
    $webUrl = makeWebUrl($relPath);
    
    $videos[] = array(
        'name' => $item,
        'basename' => $baseName,
        'ext' => $ext,
        'rel_path' => $relPath,
        'folder' => $requestDir,
        'url' => $webUrl,
        'size' => $size,
        'size_formatted' => formatBytes($size),
        'mtime' => $mtime,
        'mtime_formatted' => date('Y-m-d', $mtime),
        'subtitles' => $matchedSubs
    );
}

usort($dirs, function($a, $b) {
    return strnatcasecmp($a['name'], $b['name']);
});

usort($videos, function($a, $b) {
    return strnatcasecmp($a['name'], $b['name']);
});

$etag = '"' . md5($targetDir . ':' . @filemtime($targetDir) . ':' . count($items)) . '"';
header('ETag: ' . $etag);
if (isset($_SERVER['HTTP_IF_NONE_MATCH']) && trim($_SERVER['HTTP_IF_NONE_MATCH']) === $etag) {
    header('HTTP/1.1 304 Not Modified');
    exit;
}

echo json_encode(array(
    'success' => true,
    'mode' => 'folder',
    'current_dir' => $requestDir,
    'parent_dir' => $parentDir,
    'dirs' => $dirs,
    'videos' => $videos,
    'count' => count($videos)
), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PARTIAL_OUTPUT_ON_ERROR);

```

---

## stream_sub.py (Zero-Disk High-Speed MKV Cues Demuxer)

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
stream_sub.py - Zero-disk high-speed on-demand MKV subtitle engine for WD My Cloud Gen 1
Provides:
  1. Ultra-fast MKV subtitle track probing (< 10ms vs 2500ms avconv)
  2. Sub-second direct-seek Cues streaming (< 0.1s to first subtitle dialogue)
  3. Automatic fallback to sequential stream for non-indexed MKV tracks
"""
import os
import sys
import json
import struct
import subprocess
import signal

try:
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except Exception:
    pass

def read_vint(data, pos):
    if pos >= len(data): return None, 0
    b0 = ord(data[pos])
    for length in range(1, 9):
        if b0 & (0x80 >> (length - 1)):
            mask = (1 << (8 - length)) - 1
            val = b0 & mask
            for i in range(1, length):
                if pos + i >= len(data): return None, 0
                val = (val << 8) | ord(data[pos + i])
            return val, length
    return None, 0

def read_id(data, pos):
    if pos >= len(data): return None, 0
    b0 = ord(data[pos])
    for length in range(1, 5):
        if b0 & (0x80 >> (length - 1)):
            val = b0
            for i in range(1, length):
                if pos + i >= len(data): return None, 0
                val = (val << 8) | ord(data[pos + i])
            return val, length
    return None, 0

def ms_to_srt(ms):
    if ms < 0: ms = 0
    h = ms // 3600000
    m = (ms % 3600000) // 60000
    s = (ms % 60000) // 1000
    millis = ms % 1000
    return "%02d:%02d:%02d,%03d" % (h, m, s, millis)

def get_language_label(lang):
    lang = lang.lower().strip()
    if lang in ('kor', 'ko', 'korean'): return u'한국어'
    if lang in ('eng', 'en', 'english'): return u'영어'
    if lang in ('jpn', 'ja', 'japanese'): return u'일본어'
    if lang in ('chi', 'zh', 'chinese'): return u'중국어'
    if lang in ('fre', 'fra', 'fr'): return u'프랑스어'
    if lang in ('ger', 'deu', 'de'): return u'독일어'
    if lang in ('spa', 'es'): return u'스페인어'
    if lang in ('rus', 'ru'): return u'러시아어'
    if lang in ('ita', 'it'): return u'이탈리아어'
    if lang in ('pol', 'pl'): return u'폴란드어'
    if lang in ('por', 'pt'): return u'포르투갈어'
    if lang in ('tha', 'th'): return u'태국어'
    if lang in ('vie', 'vi'): return u'베트남어'
    if lang in ('ara', 'ar'): return u'아랍어'
    if lang in ('hin', 'hi'): return u'힌디어'
    if lang in ('ind', 'id'): return u'인도네시아어'
    if not lang or lang == 'und': return u'기타'
    return lang.upper()

def parse_mkv_seekhead(f):
    f.seek(0)
    hdr = f.read(65536)
    seg_idx = hdr.find(b'\x18\x53\x80\x67')
    if seg_idx == -1: return None, None, None
    
    b0 = ord(hdr[seg_idx + 4])
    sl = 1
    for length in range(1, 9):
        if b0 & (0x80 >> (length - 1)):
            sl = length
            break
    seg_data_start = seg_idx + 4 + sl
    
    sh_idx = hdr.find(b'\x11\x4d\x9b\x74')
    if sh_idx == -1: return seg_data_start, None, None
    
    sh_sz, sh_len = read_vint(hdr, sh_idx + 4)
    if sh_sz is None: return seg_data_start, None, None
    sh_end = sh_idx + 4 + sh_len + sh_sz
    sh_data = hdr[sh_idx + 4 + sh_len : sh_end]
    
    tracks_offset = None
    cues_offset = None
    
    p = 0
    while p < len(sh_data) - 4:
        if ord(sh_data[p]) == 0x4D and ord(sh_data[p+1]) == 0xBB:
            sp = p + 2
            ssz, sl = read_vint(sh_data, sp)
            sp += sl
            send = sp + ssz
            sid = None
            spos = None
            while sp < send:
                tag = ord(sh_data[sp])
                if tag == 0x53 and ord(sh_data[sp+1]) == 0xAB:
                    tsz = ord(sh_data[sp+2]) & 0x7F
                    sid = sh_data[sp+3:sp+3+tsz]
                    sp += 3 + tsz
                elif tag == 0x53 and ord(sh_data[sp+1]) == 0xAC:
                    tsz = ord(sh_data[sp+2]) & 0x7F
                    pval = 0
                    for i in range(tsz): pval = (pval << 8) | ord(sh_data[sp+3+i])
                    spos = pval
                    sp += 3 + tsz
                else:
                    sp += 1
            if sid == b'\x16\x54\xae\x6b':
                tracks_offset = spos
            elif sid == b'\x1c\x53\xbb\x6b':
                cues_offset = spos
        p += 1
        
    return seg_data_start, tracks_offset, cues_offset

def probe_subtitles(video_path):
    try:
        f = open(video_path, 'rb')
    except Exception as e:
        print json.dumps({'success': False, 'error': str(e)})
        return
        
    seg_data_start, tracks_offset, cues_offset = parse_mkv_seekhead(f)
    if seg_data_start is None or tracks_offset is None:
        f.close()
        # Fallback to avconv probe
        return fallback_avconv_probe(video_path)
        
    f.seek(seg_data_start + tracks_offset)
    tid_b = f.read(12)
    tid, tl = read_id(tid_b, 0)
    tsz, tsl = read_vint(tid_b, tl)
    f.seek(seg_data_start + tracks_offset + tl + tsl)
    tracks_data = f.read(tsz)
    f.close()
    
    p = 0
    cur_stream = 0
    subs = []
    
    while p < len(tracks_data):
        eid, el = read_id(tracks_data, p)
        if eid is None: break
        esz, esl = read_vint(tracks_data, p + el)
        if esz is None: break
        entry_end = p + el + esl + esz
        
        if eid == 0xAE: # TrackEntry
            ep = p + el + esl
            tnum = None
            ttype = None
            tcodec = None
            tlang = 'und'
            tname = ''
            tdef = 1
            tforced = 0
            
            while ep < entry_end:
                ieid, iel = read_id(tracks_data, ep)
                if ieid is None: break
                isz, isl = read_vint(tracks_data, ep + iel)
                if isz is None: break
                vpos = ep + iel + isl
                
                if ieid == 0xD7: # TrackNumber
                    v = 0
                    for i in range(isz): v = (v << 8) | ord(tracks_data[vpos + i])
                    tnum = v
                elif ieid == 0x83: # TrackType
                    ttype = ord(tracks_data[vpos])
                elif ieid == 0x86: # CodecID
                    tcodec = tracks_data[vpos : vpos + isz]
                elif ieid == 0x22B59C: # Language
                    tlang = tracks_data[vpos : vpos + isz]
                elif ieid == 0x536E: # Name
                    tname = tracks_data[vpos : vpos + isz]
                elif ieid == 0x88: # FlagDefault
                    tdef = ord(tracks_data[vpos])
                elif ieid == 0x55AA: # FlagForced
                    tforced = ord(tracks_data[vpos])
                ep = vpos + isz
                
            if ttype == 17: # Subtitle
                codec_label = 'SRT'
                if tcodec and ('ASS' in tcodec or 'SSA' in tcodec):
                    codec_label = 'ASS'
                lang_label = get_language_label(tlang)
                label = u"[내장-%s] %s 자막 (%s)" % (lang_label, lang_label, codec_label)
                if tforced: label += u" [강제/일부]"
                elif tdef: label += u" [기본]"
                if tname:
                    try:
                        uname = tname.decode('utf-8', errors='replace')
                        label += u" - " + uname
                    except: pass
                    
                subs.append({
                    'stream_id': cur_stream,
                    'track_number': tnum,
                    'lang': tlang,
                    'lang_label': lang_label,
                    'label': label,
                    'codec': codec_label,
                    'is_default': bool(tdef),
                    'is_forced': bool(tforced),
                    'embedded': True
                })
            cur_stream += 1
        p = entry_end
        
    # Sort: Korean first, then English, then others; non-forced first
    def sub_sort_key(s):
        lang = s['lang'].lower()
        is_kor = 0 if (lang in ('kor', 'ko', 'korean')) else 1
        is_forced = 1 if s['is_forced'] else 0
        return (is_kor, is_forced, s['stream_id'])
        
    subs.sort(key=sub_sort_key)
    print json.dumps({'success': True, 'subtitles': subs})

def fallback_avconv_probe(video_path):
    env = os.environ.copy()
    env['LD_LIBRARY_PATH'] = '/usr/local/wdmcserver/lib'
    cmd = ['/usr/local/wdmcserver/bin/avconv', '-probesize', '32768', '-analyzeduration', '0', '-i', video_path]
    try:
        p = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _, stderr_data = p.communicate()
    except Exception as e:
        print json.dumps({'success': False, 'error': str(e)})
        return
        
    subs = []
    for line in stderr_data.splitlines():
        if 'Subtitle:' in line:
            import re
            m = re.search(r'Stream #0[.:](\d+)(?:\(([^)]+)\))?: Subtitle: ([^,\n\r]+)', line)
            if m:
                s_id = int(m.group(1))
                lang = (m.group(2) or 'und').strip().lower()
                codec = m.group(3).strip()
                lang_label = get_language_label(lang)
                is_def = '(default)' in line
                is_forced = '(forced)' in line
                codec_label = 'ASS' if ('ass' in codec.lower() or 'ssa' in codec.lower()) else 'SRT'
                label = u"[내장-%s] %s 자막 (%s)" % (lang_label, lang_label, codec_label)
                if is_forced: label += u" [강제/일부]"
                elif is_def: label += u" [기본]"
                subs.append({
                    'stream_id': s_id,
                    'lang': lang,
                    'lang_label': lang_label,
                    'label': label,
                    'codec': codec_label,
                    'is_default': is_def,
                    'is_forced': is_forced,
                    'embedded': True
                })
    print json.dumps({'success': True, 'subtitles': subs})

def stream_subtitles_cues(video_path, stream_id):
    try:
        f = open(video_path, 'rb')
    except Exception as e:
        sys.stderr.write("Failed to open file: %s\n" % e)
        fallback_avconv_stream(video_path, stream_id)
        return
        
    target_stream_idx = int(stream_id)
    seg_data_start, tracks_offset, cues_offset = parse_mkv_seekhead(f)
    if seg_data_start is None or tracks_offset is None or cues_offset is None:
        f.close()
        fallback_avconv_stream(video_path, stream_id)
        return
        
    # Read tracks data
    f.seek(seg_data_start + tracks_offset)
    tid_b = f.read(12)
    tid, tl = read_id(tid_b, 0)
    tsz, tsl = read_vint(tid_b, tl)
    f.seek(seg_data_start + tracks_offset + tl + tsl)
    tracks_data = f.read(tsz)
    
    p = 0
    cur_stream = 0
    target_track_num = None
    target_codec = None
    codec_private = b''
    
    while p < len(tracks_data):
        eid, el = read_id(tracks_data, p)
        if eid is None: break
        esz, esl = read_vint(tracks_data, p + el)
        if esz is None: break
        entry_end = p + el + esl + esz
        if eid == 0xAE:
            ep = p + el + esl
            tnum = None
            ttype = None
            tcodec = None
            tpriv = b''
            while ep < entry_end:
                ieid, iel = read_id(tracks_data, ep)
                if ieid is None: break
                isz, isl = read_vint(tracks_data, ep + iel)
                if isz is None: break
                vpos = ep + iel + isl
                if ieid == 0xD7:
                    v = 0
                    for i in range(isz): v = (v << 8) | ord(tracks_data[vpos + i])
                    tnum = v
                elif ieid == 0x83:
                    ttype = ord(tracks_data[vpos])
                elif ieid == 0x86:
                    tcodec = tracks_data[vpos : vpos + isz]
                elif ieid == 0x63A2:
                    tpriv = tracks_data[vpos : vpos + isz]
                ep = vpos + isz
            is_sub = (ttype == 17) or (tcodec and 'S_' in tcodec)
            if is_sub and (cur_stream == target_stream_idx or tnum == target_stream_idx):
                target_track_num = tnum
                target_codec = tcodec
                codec_private = tpriv
                break
            cur_stream += 1
        p = entry_end
        
    if target_track_num is None:
        f.close()
        fallback_avconv_stream(video_path, stream_id)
        return
        
    # Read Cues
    f.seek(seg_data_start + cues_offset)
    cid_b = f.read(12)
    cid, cl = read_id(cid_b, 0)
    csz, csl = read_vint(cid_b, cl)
    f.seek(seg_data_start + cues_offset + cl + csl)
    cues_data = f.read(csz)
    
    # Fast search for target track
    # In EBML, TrackNumber in CueTrack (0xF7) is a vint
    if target_track_num < 128:
        track_sig = b'\xf7\x81' + chr(target_track_num)
    else:
        track_sig = b'\xf7\x82' + chr(target_track_num >> 8) + chr(target_track_num & 0xFF)
        
    cues = []
    pos = 0
    while True:
        idx = cues_data.find(track_sig, pos)
        if idx == -1: break
        pos = idx + len(track_sig)
        
        b7_idx = cues_data.rfind(b'\xb7', max(0, idx - 10), idx)
        if b7_idx == -1: continue
        
        b0 = ord(cues_data[b7_idx+1])
        b7_len = 1
        for l in range(1, 9):
            if b0 & (0x80 >> (l - 1)):
                b7_len = l
                break
        b7_sz = b0 & ((1 << (8 - b7_len)) - 1)
        for i in range(1, b7_len): b7_sz = (b7_sz << 8) | ord(cues_data[b7_idx+1+i])
        
        _, el = read_id(cues_data, b7_idx)
        esz, esl = read_vint(cues_data, b7_idx + el)
        if esz is None: continue
        
        tp = b7_idx + el + esl
        tp_end = tp + esz
        cpos = None
        rpos = 0
        dur = 0
        
        while tp < tp_end:
            tag_id, id_len = read_id(cues_data, tp)
            if tag_id is None: break
            tag_sz, sz_len = read_vint(cues_data, tp + id_len)
            if tag_sz is None: break
            vpos = tp + id_len + sz_len
            if tag_id == 0xF1: # CueClusterPosition
                v = 0
                for i in range(tag_sz): v = (v << 8) | ord(cues_data[vpos + i])
                cpos = v
            elif tag_id == 0xF0: # CueRelativePosition
                v = 0
                for i in range(tag_sz): v = (v << 8) | ord(cues_data[vpos + i])
                rpos = v
            elif tag_id == 0xB2: # CueDuration
                v = 0
                for i in range(tag_sz): v = (v << 8) | ord(cues_data[vpos + i])
                dur = v
            tp = vpos + tag_sz
                
        if cpos is not None:
            t_idx = cues_data.rfind(b'\xb3', max(0, b7_idx - 30), b7_idx)
            ctime = 0
            if t_idx != -1:
                _, tl = read_id(cues_data, t_idx)
                tsz, tsl = read_vint(cues_data, t_idx + tl)
                if tsz is not None:
                    v = 0
                    for i in range(tsz): v = (v << 8) | ord(cues_data[t_idx + tl + tsl + i])
                    ctime = v
            cues.append((ctime, dur, cpos, rpos))
            
    if not cues:
        f.close()
        fallback_avconv_stream(video_path, stream_id)
        return
        
    is_ass = bool(target_codec and ('ASS' in target_codec or 'SSA' in target_codec))
    if is_ass and codec_private:
        try:
            sys.stdout.write(codec_private)
            if not codec_private.endswith('\n'):
                sys.stdout.write('\n')
            sys.stdout.write("[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
            sys.stdout.flush()
        except IOError:
            sys.exit(0)
            
    cue_idx = 1
    cluster_cache = {}
    for ctime, dur, cpos, rpos in cues:
        abs_cluster = seg_data_start + cpos
        if cpos in cluster_cache:
            cluster_data_start = cluster_cache[cpos]
        else:
            f.seek(abs_cluster + 4)
            b0 = ord(f.read(1))
            vlen = 1
            for l in range(1, 9):
                if b0 & (0x80 >> (l - 1)):
                    vlen = l
                    break
            cluster_data_start = abs_cluster + 4 + vlen
            cluster_cache[cpos] = cluster_data_start
            
        if rpos > 0:
            f.seek(cluster_data_start + rpos)
        else:
            f.seek(cluster_data_start)
            
        block_hdr = f.read(4096)
        txt = None
        b_dur = dur
        
        eid, el = read_id(block_hdr, 0)
        if eid == 0xA0: # BlockGroup
            esz, esl = read_vint(block_hdr, el)
            if esz is not None:
                bg_data = block_hdr[el + esl : el + esl + esz]
                bp = 0
                while bp < len(bg_data):
                    bid, bl = read_id(bg_data, bp)
                    if bid is None: break
                    bsz, bsl = read_vint(bg_data, bp + bl)
                    if bsz is None: break
                    if bid == 0xA1: # Block
                        block_payload = bg_data[bp + bl + bsl : bp + bl + bsl + bsz]
                        tnum, tlen = read_vint(block_payload, 0)
                        if tnum == target_track_num:
                            txt = block_payload[tlen + 3:]
                            break
                    elif bid == 0x9B: # BlockDuration
                        dv = 0
                        for i in range(bsz): dv = (dv << 8) | ord(bg_data[bp + bl + bsl + i])
                        b_dur = dv
                    bp += bl + bsl + bsz
        elif eid == 0xA1 or eid == 0xA3: # Block or SimpleBlock
            esz, esl = read_vint(block_hdr, el)
            if esz is not None:
                block_payload = block_hdr[el + esl : el + esl + esz]
                tnum, tlen = read_vint(block_payload, 0)
                if tnum == target_track_num:
                    txt = block_payload[tlen + 3:]
                    
        # Fallback linear scan inside block_hdr if not matched at offset
        if not txt:
            p = 0
            while p < len(block_hdr) - 4:
                tag = ord(block_hdr[p])
                if tag == 0xA0:
                    _, vlen = read_vint(block_hdr, p + 1)
                    p += 1 + (vlen if vlen else 1)
                elif tag == 0xA1 or tag == 0xA3:
                    bsz, bsl = read_vint(block_hdr, p + 1)
                    if bsz is None: break
                    block_payload = block_hdr[p + 1 + bsl : p + 1 + bsl + bsz]
                    tnum, tlen = read_vint(block_payload, 0)
                    if tnum == target_track_num:
                        txt = block_payload[tlen + 3:]
                        break
                    p += 1 + bsl + bsz
                elif tag == 0x9B:
                    dsz, dsl = read_vint(block_hdr, p + 1)
                    if dsz is None: break
                    dv = 0
                    for i in range(dsz): dv = (dv << 8) | ord(block_hdr[p + 1 + dsl + i])
                    b_dur = dv
                    p += 1 + dsl + dsz
                else:
                    p += 1
                    
        if txt:
            start_ms = ctime
            end_ms = ctime + (b_dur if b_dur > 0 else 3000)
            try:
                if is_ass:
                    parts = txt.split(',', 8)
                    if len(parts) >= 9:
                        layer = parts[1]
                        style = parts[2]
                        name = parts[3]
                        ml = parts[4]
                        mr = parts[5]
                        mv = parts[6]
                        effect = parts[7]
                        text = parts[8]
                        def ms_to_ass(ms):
                            h, rem = divmod(ms, 3600000)
                            m, rem = divmod(rem, 60000)
                            s, ms_part = divmod(rem, 1000)
                            cs = ms_part // 10
                            return "%d:%02d:%02d.%02d" % (h, m, s, cs)
                        line = "Dialogue: %s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n" % (
                            layer, ms_to_ass(start_ms), ms_to_ass(end_ms), style, name, ml, mr, mv, effect, text.strip()
                        )
                        sys.stdout.write(line)
                    else:
                        out = "%d\n%s --> %s\n%s\n\n" % (cue_idx, ms_to_srt(start_ms), ms_to_srt(end_ms), txt.strip())
                        sys.stdout.write(out)
                else:
                    out = "%d\n%s --> %s\n%s\n\n" % (cue_idx, ms_to_srt(start_ms), ms_to_srt(end_ms), txt.strip())
                    sys.stdout.write(out)
                sys.stdout.flush()
                cue_idx += 1
            except IOError:
                break
                
    f.close()

def fallback_avconv_stream(video_path, stream_id):
    env = os.environ.copy()
    env['LD_LIBRARY_PATH'] = '/usr/local/wdmcserver/lib'
    env['LANG'] = 'C.UTF-8'
    env['LC_ALL'] = 'C.UTF-8'
    cmd = [
        '/usr/local/wdmcserver/bin/avconv',
        '-y',
        '-threads', '2',
        '-vn', '-an',
        '-i', video_path,
        '-map', '0:' + str(stream_id),
        '-c:s', 'copy',
        '-f', 'matroska',
        '-'
    ]
    try:
        devnull = open('/dev/null', 'w')
        p = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=devnull, bufsize=65536)
    except Exception:
        return
        
    buf = b''
    cluster_tag = b'\x1f\x43\xb6\x75'
    cue_idx = 1
    pending_cue = None

    def emit_cue(cue_tuple):
        try:
            idx, s_ms, e_ms, txt, _ = cue_tuple
            out = "%d\n%s --> %s\n%s\n\n" % (idx, ms_to_srt(s_ms), ms_to_srt(e_ms), txt)
            sys.stdout.write(out)
            sys.stdout.flush()
        except IOError:
            try: p.kill()
            except: pass
            sys.exit(0)

    while True:
        try:
            chunk = p.stdout.read(16384)
        except Exception:
            break
        if not chunk:
            if p.poll() is not None: break
            continue
        buf += chunk
        while True:
            c1 = buf.find(cluster_tag)
            if c1 == -1:
                buf = buf[-3:]
                break
            c_size, c_len = read_vint(buf, c1 + 4)
            if c_size is None: break
            cluster_end = c1 + 4 + c_len + c_size
            if len(buf) < cluster_end: break
            cluster_data = buf[c1 : cluster_end]
            buf = buf[cluster_end:]
            p_pos = 4 + c_len
            tc = 0
            while p_pos < len(cluster_data):
                tag = ord(cluster_data[p_pos])
                if tag == 0xE7:
                    s, l = read_vint(cluster_data, p_pos + 1)
                    p_pos += 1 + l
                    tc = 0
                    for i in range(s): tc = (tc << 8) | ord(cluster_data[p_pos + i])
                    p_pos += s
                elif tag == 0xA0 or tag == 0xA3:
                    tag_size, tag_len = read_vint(cluster_data, p_pos + 1)
                    inner_end = p_pos + 1 + tag_len + tag_size
                    bp = p_pos + 1 + tag_len
                    duration = 0
                    block_data = None
                    rel_tc = 0
                    if tag == 0xA0:
                        while bp < inner_end and bp < len(cluster_data):
                            btag = ord(cluster_data[bp])
                            if btag == 0xA1:
                                bs, bl = read_vint(cluster_data, bp + 1)
                                doff = bp + 1 + bl
                                tnum, tlen = read_vint(cluster_data, doff)
                                rel_tc = struct.unpack('>h', cluster_data[doff + tlen : doff + tlen + 2])[0]
                                block_data = cluster_data[doff + tlen + 3 : doff + bs]
                                bp = doff + bs
                            elif btag == 0x9B:
                                ds, dl = read_vint(cluster_data, bp + 1)
                                doff = bp + 1 + dl
                                dur = 0
                                for i in range(ds): dur = (dur << 8) | ord(cluster_data[doff + i])
                                duration = dur
                                bp = doff + ds
                            else:
                                sub_s, sub_l = read_vint(cluster_data, bp + 1)
                                if sub_s is None: break
                                bp = bp + 1 + sub_l + sub_s
                    else:
                        doff = bp
                        tnum, tlen = read_vint(cluster_data, doff)
                        rel_tc = struct.unpack('>h', cluster_data[doff + tlen : doff + tlen + 2])[0]
                        block_data = cluster_data[doff + tlen + 3 : doff + tag_size]
                    if block_data:
                        start_ms = tc + rel_tc
                        is_fallback = (duration <= 0)
                        end_ms = start_ms + (duration if duration > 0 else 4000)
                        txt = block_data.strip().replace('\r\n', '\n').replace('\r', '\n')
                        if pending_cue is not None:
                            p_idx, p_start, p_end, p_txt, p_is_fallback = pending_cue
                            if p_is_fallback and p_end > start_ms:
                                p_end = max(p_start + 500, start_ms)
                            emit_cue((p_idx, p_start, p_end, p_txt, p_is_fallback))
                        pending_cue = (cue_idx, start_ms, end_ms, txt, is_fallback)
                        cue_idx += 1
                    p_pos = inner_end
                else:
                    p_pos += 1
    if pending_cue is not None:
        emit_cue(pending_cue)
    try:
        p.stdout.close()
        devnull.close()
    except Exception:
        pass

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: stream_sub.py probe <video_path> OR stream_sub.py <video_path> <stream_id>\n")
        sys.exit(1)
    if sys.argv[1] == 'probe':
        if len(sys.argv) < 3:
            sys.exit(1)
        probe_subtitles(sys.argv[2])
    else:
        if len(sys.argv) < 3:
            sys.exit(1)
        stream_subtitles_cues(sys.argv[1], sys.argv[2])

```
