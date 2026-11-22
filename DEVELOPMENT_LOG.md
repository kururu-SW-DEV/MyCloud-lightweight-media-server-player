# MyCloud Media Player 개발 및 보안 감사 로그 (Development & Security Audit Log)

- **프로젝트 명**: MyCloud Media Player (초경량 NAS 웹 미디어 플레이어)
- **배포 타겟 환경**: WD My Cloud Gen 1 (ARMv7 650MHz 싱글코어, 226MB RAM, Debian Wheezy 32비트, Apache 2.4, PHP 5.6.7-1)
- **웹 서버 배포 경로**: `/shares/webplayer/`
- **미디어 루트 경로**: `/shares/Public/`
- **로컬 작업 경로**: `C:\Users\nzlhu\Desktop\AI 작업\3. 경량 서버용 미디어 플레이어\`
- **최신 안정 배포 버전**: `v20261104_v4`

---

## 1. 아키텍처 및 핵심 설계 원칙

1. **Strict Zero-Disk Cache (디스크 쓰기 0바이트 원칙)**:
   - 5400RPM HDD의 물리적 I/O 병목 및 헤드 파킹 방해를 방지하기 위해 디스크에 어떠한 임시 파일도 생성하지 않음.
   - 자막 추출 및 스트리밍은 RAM 디스크(`/tmp/webplayer_sub_ram` tmpfs) 또는 표준 출력 파이프(`php://stdout`)를 통해 100% 인메모리로 처리.
2. **Matroska Cues Direct Seek (< 10ms)**:
   - 10GB 이상의 대용량 MKV 동영상도 avconv/ffmpeg을 통한 전체 스캔 없이, EBML 구조 파싱 및 Cues 인덱스 오프셋(`rpos`) 다이렉트 seek을 통해 0.005초 만에 자막 트랙을 감지하고 스트리밍 시작.
3. **고아 프로세스 완전 박멸 (Zombie Process Elimination)**:
   - 사용자가 창을 닫거나 영상을 넘길 때 `connection_aborted()` 감지 및 `stream_set_timeout(15)`를 통해 백그라운드 디먹서 프로세스를 즉각 `SIGKILL(9)`로 정리.
4. **ETag 304 Not Modified & SWR 캐싱**:
   - 변경 없는 폴더 재진입 시 0ms 즉시 응답으로 네트워크 트래픽 100% 절감.
5. **WebExplorer와의 완벽한 시각적/기능적 일체화**:
   - 동일한 다크 슬레이트 블루 테마, Linear SVG 벡터 아이콘, 상호 전환 버튼(`.btn-nav-switch`), 현재 탭 교차 탐색 지원.

---

## 2. 상세 개발 및 개선 이력 (Chronological Changelog)

### Phase 1: 고속 MKV 자막 엔진 및 Zero-Disk 파이프라인 구축
- **초기 구현**:
  - `stream_sub.py`: Python 2.7(Debian Wheezy 기본) 기반의 Matroska EBML 파서 구현.
  - Cues 엘리먼트(`0x1C53BB6B`) 인덱스를 역추적하여 원하는 자막 블록만 클러스터에서 직접 추출.
  - WebVTT / SRT 실시간 포맷 변환 및 `api.php` 스트리밍 파이프 연결.

### Phase 2: 다국어(MULTi) MKV 한국어 콘텐츠 자동 감지 최적화 (2026-09-11)
1. **한국어 트랙 자동 감지 속도 개선 (`has_hangul_content`)**:
   - 여러 개의 `kor` 태그 트랙 중 실제로 한글이 들어있는 트랙을 고르는 로직이 서브프로세스를 띄우던 구조에서, **스트리밍 로직과 동일하게 단일 seek+read**로 인메모리 파싱하도록 개선 (76개 트랙 기준 `probe` 응답 2.04초 → 0.39초).
2. **엉뚱한 언어 트랙이 매칭되던 버그 수정**:
   - `cur_stream == target_stream_idx` 또는 `tnum == target_stream_idx` 이중 매칭 조건에서 `tnum` 조건을 제거하여 순번(`stream_id`) 기반 매칭으로 일원화.
3. **배포 시 RAM 자막 캐시 미정리 문제 해결**:
   - `deploy_webplayer.py` 정리 단계에 `/tmp/webplayer_sub_ram/*` 경로를 추가하여 수정 전 잘못 캐시된 자막이 서빙되지 않도록 개선.
4. **타임코드 역방향 스캔 IndexError 크래시 방지**:
   - Cue 타임코드(`0xB3`) 역방향 바이트 스캔 시 경계값 검사를 추가하여 오매칭 예외 처리.

### Phase 3: 보안 취약점 전면 감사 및 방어 강화 (2026-11-04)
1. **이중 URL 인코딩 및 경로 탐색(Path Traversal) 방어 (`api.php`)**:
   - `validateRelativePath()` 함수를 도입하여 `%252e%252e`, `..`, `\0`, `%00`을 검사하고 조작된 상대 경로를 HTTP 400으로 차단.
   - `probe_subs`, `stream_sub`, 폴더 탐색 파라미터 전수 검증 적용.
2. **심볼릭 링크(Symlink) 악용 및 무한 재귀 탈출 방어 (`api.php`)**:
   - `is_link()` 검사를 통해 `/shares/Public` 외부를 가리키거나 디렉터리 루프를 형성하는 심볼릭 링크 파일을 라이브러리 목록에서 원천 배제.
   - 자막 RAM 캐시 디렉터리(`/tmp/webplayer_sub_ram`)가 심볼릭 링크로 교체된 경우 자동 감지 및 삭제.
3. **아파치 디렉터리 인덱싱 노출 차단 (`apache_webplayer.conf`)**:
   - `/shares/webplayer`에 `Options -Indexes +FollowSymLinks` 적용하여 파일 목록 노출 차단 및 `Require ip 127.0.0.1` 추가.
4. **자막 스트림 소켓 타임아웃 (`api.php`)**:
   - `stream_set_timeout($pipes[1], 15)` 및 `timed_out` 감지 시 백그라운드 자식 프로세스를 즉각 `SIGKILL(9)`로 정리하여 프로세스 누수 방지.

### Phase 4: 32-bit PHP 대용량 파일 (> 2.14GB) 정수 오버플로 버그 해결 (2026-11-04)
1. **원인 분석**:
   - 32비트 ARMv7 Linux 상의 PHP 5.6은 정수형이 32비트(`PHP_INT_MAX = 2,147,483,647`)이므로 2.14GB를 초과하는 고화질 영화 파일(예: 3GB)의 `filesize()` 호출 결과가 음수(예: `-1073741824`)로 반환됨.
   - 이로 인해 `if ($size <= 0) continue;` 필터링에서 대용량 동영상들이 목록에서 조용히 사라지던 버그 발생.
2. **해결 방안**:
   - `getSafeFileSize()`를 구현하여 파일 크기가 1GB를 초과하거나 음수/비정상일 경우 `stat -c "%s"`를 호출해 64비트 정밀도 문자열을 확보하고 float 및 formatBytes로 안전 변환.
3. **실서버 3GB 스파스 파일 검증**:
   - `truncate -s 3221225472 /shares/Public/test_sparse_3g.mp4` 테스트 결과, 기존 `filesize()`는 `-1073741824`를 반환했으나 `getSafeFileSize()`는 `3221225472` (3 GB)로 정상 인식하여 API 목록에 완벽 노출됨을 확인.

### Phase 5: 모던 UI 개편 및 이모지 100% 박멸 (2026-11-04)
1. **Zero AI Slop / 선형 모노크롬 SVG 전면 교체**:
   - HTML, JS, CSS 내의 모든 컬러 이모지를 제거하고 WebExplorer와 동일한 다크 슬레이트 테마의 정제된 Linear SVG 벡터 아이콘 적용 (0개 검증 완료).
2. **반응형 툴바 & 모바일 최적화**:
   - `touch-action: manipulation` 적용 (iOS Safari 300ms 탭 딜레이 방지), Safe-Area 인셋 지원, 좁은 화면 가로 스크롤 툴바.

### Phase 6: WebExplorer 디자인 토큰 및 색상 팔레트 1:1 완벽 일체화 (2026-11-04)
1. **CSS `:root` 변수 통일**:
   - `--bg-card`: `#1e293b` -> `#182235` (WebExplorer와 동일한 다크 슬레이트 블루)
   - `--bg-hover`: `#334155` -> `#26334d`
   - `--text-main`: `#f8fafc` -> `#f1f5f9` (슬레이트 100)
   - `--border-card: rgba(255, 255, 255, 0.08);` 추가 및 카드/네비바/검색창 테두리 적용
   - `--radius`: `10px` -> `8px` 일치화
   - `--shadow`: `0 2px 8px rgba(0, 0, 0, 0.28);`
2. **컴포넌트 스타일 정밀 일치**:
   - 검색창: 라운드 알약형(`20px`) -> 모던 라운드 사각(`7px`, `border-card`, 포커스 시 시안 글로우 `0 0 0 2px rgba(56, 189, 248, 0.15)`).
   - 카드 테두리: 기본 `border: 1px solid var(--border-card);`, 호버 시 `border-color: rgba(56, 189, 248, 0.4);`.
   - 썸네일 그라디언트: `#182235` 베이스로 일치화.
   - 모달 다이얼로그: `#111827` 베이스, 10px 곡률, 미세 보더 적용.

### Phase 7: 익스플로러 <-> 미디어 플레이어 상호 전환 버튼 완전 통일화 (2026-11-04)
1. **버튼 위치 대칭성 확보**:
   - 미디어 플레이어 상단 네비바 우측(`.nav-actions`)과 익스플로러 상단 네비바 우측(`.nav-actions`)의 동일 위치에 상호 전환 버튼 배치.
2. **버튼 스타일 및 네이밍 통일 (`.btn-nav-switch`)**:
   - 공통 클래스 `.btn.btn-secondary.btn-nav-switch` 정의 (패딩 `7px 12px`, 모서리 `7px`, 배경 `var(--bg-hover)`, 테두리 `rgba(255, 255, 255, 0.08)`, 호버 시 시안 글로우).
   - 표기 규격: `Explorer ->` (플레이어 측) <-> `Player ->` (익스플로러 측).
   - 아이콘: 플레이어 측은 Folder 아이콘, 익스플로러 측은 Play 아이콘 적용.
3. **현재 탭 전환 (`window.location.href`)**:
   - 새 창(`target="_blank"`) 팝업을 전면 배제하고 현재 탭에서 즉시 부드럽게 전환.

### Phase 8: 미디어 재생 편의성 및 추가 버그 개선 (2026-11-04)
1. **`?open=` 파라미터 `Public/` 접두사 자동 정규화**:
   - 익스플로러에서 `Public/경로` 형태로 전달되어도 플레이어에서 누락 없이 동영상을 즉각 찾아 자동 재생.
2. **텍스트 입력창 핫키 가드**:
   - 검색창 등 input/textarea 입력 중에는 Space(재생/일시정지), 화살표(탐색), 부등호(배속) 단축키가 가로채기 동작을 하지 않도록 방어.
3. **MediaSession API 정밀 탐색 및 스크러빙 (`setPositionState` + `seekto`)**:
   - 모바일 잠금화면, 스마트워치, Windows 미디어 위젯에서 재생 바 진행 상황이 실시간 동기화되고, 잠금화면 바를 직접 터치해 원하는 시간대로 스크러빙 탐색(`seekto`) 가능.
4. **비디오 화면 클릭/터치 시 재생/일시정지 토글**:
   - 비디오 화면 터치/클릭 시 직관적으로 재생 및 일시정지 전환.
5. **자막 수동 선택 상태 보존**:
   - 내장 자막 비동기 확인 도중 사용자가 외부 자막이나 '자막 끄기'를 수동 선택한 경우, 비동기 완료 후 덮어쓰지 않도록 가드 추가.
6. **동영상 재생 시 브라우저 탭 타이틀 동적 표시**:
   - 영상 재생 시 브라우저 탭 제목이 `[파일명] - MyCloud Media Player`로 자동 갱신되며, 창을 닫으면 원래대로 복구.
7. **재생 배속 순환 제어**:
   - `0.75x`, `1.0x`, `1.25x`, `1.5x`, `2.0x` 5단계 배속 토글 버튼 및 토스트 피드백 (`>`, `<` 단축키).
### Phase 9: 미디어 포맷 확장, 익스플로러 완벽 상호운용 및 Zero AI Slop 완성 (2026-11-04)
1. **WMV 및 TS 비디오 포맷 지원 확장 (`api.php`, `webplayer.conf`)**:
   - `$videoExts` 목록에 `wmv`와 `ts`를 등록하여 WebExplorer 지원 비디오 포맷과 1:1 완벽 일체화.
   - Apache 설정에 `AddType video/x-ms-wmv .wmv` 및 `AddType video/mp2t .ts`를 추가하여 웹 브라우저 스트리밍 MIME 헤더 최적화.
2. **익스플로러 <-> 미디어 플레이어 상호 연동성 검증**:
   - WebExplorer에서 동영상 클릭 시 `?open=` 매개변수를 통해 미디어 플레이어의 해당 동영상으로 즉시 부드럽게 전환 및 자동 재생.
3. **Zero AI Slop 100% 달성**:
   - `DEVELOPMENT_LOG.md`, `README.md` 내의 잔류 이모지를 텍스트 태그(`[완료]`, `[폴더]`, `[보안]`, `->` 등)로 완전 대체하여 0개 달성.


### Phase 10: 다중 내장 자막 MKV 트랙 인덱스 섀도잉 결함 해결 (2026-11-04)
1. **문제 현상 및 근본 원인 규명**:
   - 현상: 다중 자막이 포함된 MKV 파일 재생 시 UI에서 '한국어 자막'을 선택했으나 실제 화면에는 일본어 자막이 출력되는 불일치 발생.
   - 원인: MKV 파일 내에서 스트림 번호(`stream_id` / `cur_stream`, 0부터 시작)와 내부 트랙 고유 번호(`track_number` / `tnum`, 1부터 시작)는 일반적으로 1씩 차이남(`tnum == cur_stream + 1`).
   - `stream_sub.py`의 `stream_subtitles_cues()` 탐색 루프에서 `if is_sub and (cur_stream == target_stream_idx or tnum == target_stream_idx):` 형태로 `or` 비교를 수행하면서, 한국어 자막(stream 49, tnum 50) 요청 시 직전의 일본어 자막(stream 48, tnum 49) 검사 시점에 `tnum == target_stream_idx` (49 == 49)가 먼저 참(True)으로 평가되어 한 칸 앞의 일본어 자막이 선택·반환되는 트랙 인덱스 섀도잉(Index Shadowing) 결함 발생.
2. **트랙 매칭 조건 정규화 (`stream_sub.py`, `deploy_webplayer.py`)**:
   - 트랙 일치 판정 조건을 `if is_sub and cur_stream == target_stream_idx:`로 단일화하여 `probe`에서 전달된 스트림 ID와 1:1 정확하게 매칭되도록 수정.
3. **RAM 캐시 무효화 및 실기기 검증**:
   - 이전 결함 상태로 `/tmp/webplayer_sub_ram/`에 저장되어 있던 일본어 자막 캐시 파일을 전면 삭제.
   - 실기기(WD My Cloud Gen 1)에 배포 후 76개 트랙의 다국어 MKV 파일(`Sparks.of.Tomorrow...mkv`)을 대상으로 한국어 일반 자막(49), 강제 자막(50), 더빙 자막(51), 일본어 일반/SDH 자막(47, 48)이 각각 100% 정확하게 출력됨을 CLI 및 HTTP 스트리밍 API로 실증 확인.


### Phase 11: 32비트 대용량 파일 크기 계산 최적화 및 목록 조회 10배 고속화 (2026-11-04)
1. **목록 로딩 지연 원인 규명**:
   - 기존 `getSafeFileSize()` 함수가 32비트 정수 보호를 위해 1GB(`1073741824` 바이트) 초과 파일에 대해 리눅스 셸 명령(`timeout 3 stat -c "%s"`)을 실행(`shell_exec`)하도록 작성되어 있었음.
   - 650MHz 저성능 단일 코어 ARMv7 CPU 환경에서 셸 프로세스 1회 fork/exec 시 약 40~60ms가 소요되는데, 1080p 고화질 영상(대부분 1.2GB~1.8GB)이 모여 있는 폴더를 열 때마다 파일 개수만큼 셸 프로세스를 연속 생성(13개 파일 시 650ms 이상)하여 심각한 로딩 딜레이 발생.
   - 특히 '전체 영상 모드(all=1)'에서는 95개 대용량 파일에 대해 프로세스를 95번 연속 실행하면서 무려 6.4초의 로딩 지연이 발생했음.
2. **무포크(Zero-Fork) 4GB 인메모리 크기 판정 구현 (`api.php`)**:
   - 32비트 PHP에서도 `sprintf('%u', $st['size'])`를 사용하면 부호 없는 정수 4GB(4,294,967,295 바이트)까지 프로세스 생성 없이 단 0.001ms 만에 정확한 파일 크기 변환 가능.
   - 단일 `@stat($fullPath)` 시스템 콜 후 할당된 블록 크기(`$st['blocks'] * 512 > 4GB`)가 실제로 4GB를 초과할 때에만 셸 `stat` 명령으로 안전하게 폴백하도록 최적화.
3. **실기기 성능 검증 결과**:
   - 13개 고화질 영상 폴더 조회 시간: **0.815초 -> 0.088초 (약 10배 고속화, 88ms 달성)**
   - 전체 영상(all=1) 재귀 탐색 시간: **6.431초 -> 1.073초 (약 6배 고속화, 83% 시간 단축)**
   - Apache2 재로드 후 라이브 서버 실시간 적용 완료.


### Phase 12: 안드로이드 해상도별 미니 창/재생 창 버튼 잘림 및 비율 찌그러짐 개선 (2026-11-07)
1. **320px~360px 소형/표준 안드로이드 뷰포트에서 창 우측 잘림 해결 (`style.css`, `app.js`)**:
   - 기존 `.modal-dialog`의 `min-width: 380px`가 `@media (max-width: 640px)`에서 해제되지 않아 360px 이하 기기에서 창이 화면보다 커지며 우측 `전체화면`, `닫기(×)` 버튼이 30px~70px 잘리던 문제 수정 (`min-width: 0`, `width: calc(100vw - 12px)` 적용).
   - `centerModalDialog()`, 드래그 경계 계산, `resize` 이벤트에서 뷰포트 여백(`getModalViewportMargin()`)을 모바일 `6px`, 데스크톱 `10px`로 동적 계산하여 화면 밖 이탈을 원천 차단.
2. **미니 창(`.modal-dialog.minimized`) 및 소형 화면(`<=480px`) 헤더 버튼 잘림/찌그러짐 해결 (`style.css`)**:
   - 미니 창(`340px`, 소형 화면에서는 `calc(100vw - 12px)`)과 480px 이하 모바일 화면에서 헤더 액션 버튼의 보조 한글 라벨(`span:not(#video-speed-text)`)만 숨기고 아이콘 및 배속(`1.0x`)은 그대로 유지하여, 6개 버튼 전체가 단 하나도 잘리지 않고 영상 제목(`#player-title-text`) 표시 공간까지 확보.
   - 원형 닫기 버튼(`.btn-close`)에 `flex-shrink: 0`을 추가하여 공간 부족 시 타원형으로 찌그러지는 현상 제거.
3. **미니 창 전환/복원 및 화면 회전 시 창 비율 찌그러짐 해결 (`app.js`, `style.css`)**:
   - `enterMinimize()`에서 `modalDialog.style.height`가 자동(`""`)이었을 때 당시 픽셀 높이(`rect.height`)를 강제 저장해 복원 시 고정 높이로 박제되던 버그를 수정하여, 원래 인라인 스타일(`styleWidth`, `styleHeight`)을 그대로 복원하도록 개선.
   - `.modal-dialog.minimized .video-wrapper`에 `height: auto; aspect-ratio: 16 / 9;`를 명시하여 미니 창 영상 비율 고정.
   - 모바일 가로 모드(`@media (max-height: 480px)`)에서 `.video-wrapper` 최소 높이를 `100px`로 낮춰 하단 자막 컨트롤바(`.modal-footer`)가 잘리지 않도록 개선.

### Phase 13: 자막 선택 상태 초기화, 외부 자막 매칭, MKV Cues 구조 파싱 등 7대 잠재 버그 해결 (2026-11-07)
1. **영상 전환 시 자막 자동 선택 먹통 현상 수정 (`app.js`)**:
   - `openPlayer()` 및 `closePlayer()`에서 `userManuallySelectedSubtitle = false`로 초기화하고, 내장 자막 비동기 탐색(`probe_subs`) 도중 사용자가 먼저 선택한 자막 인덱스가 `renderSubtitleDropdown()` 재렌더링 시 유실되지 않도록 보존 처리.
2. **외부 자막 파일 접두사 오탐(`1화` vs `10화`) 수정 (`api.php`)**:
   - `isMatchingSubtitleBase()` 함수를 도입하여 영상 파일명과 완전히 같거나 구분자(`.`, `_`, `-`, 공백, `[`, `(`)가 이어지는 경우에만 매칭되도록 수정.
3. **전체화면 연속 재생 시 네이티브 자막 트랙(`#webplayer-native-track`) 동기화 및 잔상 제거 (`app.js`)**:
   - `clearSubtitles()`에서 이전 영상의 `currentVttBlobUrl` 해제 및 `<track>` `src` 제거를 수행하고, `<track>` `load` 이벤트 시점에 `track.mode`(`showing`/`hidden`)가 즉시 재적용되도록 보강.
4. **MKV Cues 내장 자막 추출 시 `CuePoint` (`0xBB`) 정식 EBML 경계 파싱 적용 (`stream_sub.py`)**:
   - 기존의 단순 역방향 30바이트 검색(`rfind(b'\xb3', max(0, b7_idx - 30), b7_idx)`)을 제거하고, `CuePoint` (`0xBB`) 최상위 경계 단위 스킵 및 내부 `CueTime`(`0xB3`)/`CueTrackPositions`(`0xB7`) 정식 파싱으로 교체하여 다중 트랙 MKV에서의 타임스탬프 깨짐을 원천 차단.
5. **WebVTT(`.vtt`) 큐 위치 속성 포함 타임스탬프 파싱 및 장시간 자막 탐색 범위 동적 확장 (`app.js`)**:
   - `parseTimestamp()`에서 공백 뒤의 큐 설정값(`line:90%` 등)을 분리하도록 수정하고, `finalizeCues()`에서 계산한 최대 자막 지속시간(`_maxFiniteDur`)을 기반으로 이진 탐색 범위를 동적 확장하여 60초 이상 지속되는 자막이 중간에 사라지지 않도록 개선.
6. **로컬 외부 자막(`#custom-sub-input`) 재선택 및 Blob URL 메모리 해제 (`app.js`)**:
   - 로컬 파일 선택 직후 `customSubInput.value = ''`로 초기화하여 동일 파일 재선택을 지원하고, `closePlayer()` 시 생성된 모든 로컬 자막 Blob URL과 메모리 캐시를 일괄 해제하도록 개선.

### Phase 14: 외부 자막 다국어 인코딩 지원, 중복 avconv 제거, 프로브 캐싱 및 스트리밍 최적화 (2026-11-07)
1. **외부 `.srt`/`.ass`/`.vtt` 자막의 EUC-KR(CP949) 및 UTF-16 인코딩 깨짐 해결 (`app.js`)**:
   - `loadSelectedTrack()`에서 내장 자막 스트림(`isEmbedded === true`)만 스트리밍 리더를 사용하고, 모든 외부 자막(`!isEmbedded`)은 `decodeSubtitleBuffer()`를 거치도록 수정하여 EUC-KR 및 UTF-16LE/BE 인코딩 자막이 한글 깨짐 없이 단일 패스로 즉시 파싱되도록 개선.
2. **내장 자막 0개 파일(MP4 등)에서 `avconv` 중복 실행 제거 및 `probe_subs` 이중 캐싱 (`api.php`, `app.js`)**:
   - `stream_sub.py probe`가 빈 자막 배열(`[]`)을 정상 반환했을 때 `api.php`에서 또다시 `avconv`를 중복 실행하던 조건(`!empty($fastJson['subtitles'])` -> `isset($fastJson['subtitles'])`) 수정.
   - 서버 RAM(`/tmp/webplayer_sub_ram/probe_*.json`) 및 브라우저 메모리(`probeMemoryCache`)에 자막 트랙 탐색 결과를 캐싱하여 재조회 시간을 **682.8ms -> 12.7ms (클라이언트 캐시 적중 시 0ms)**로 단축.
3. **내장 자막 실시간 스트리밍 I/O 및 브라우저 파싱 스로틀링 최적화 (`stream_sub.py`, `app.js`)**:
   - `stream_sub.py`에서 첫 번째 대사는 즉시 flush하여 초기 응답성을 유지하고 이후에는 40줄 단위로 버퍼링하여 시스템 콜 횟수를 97% 절감, `rpos > 0`일 때 블록 읽기 크기를 `4096B -> 1024B`로 줄여 디스크 읽기량을 75% 절감.
   - `app.js`에서 스트리밍 수신 중 전체 재파싱 주기를 220ms 간격으로 스로틀링하고, `<track>` Blob URL 재생성(`syncCuesToTextTrack()`)은 전체화면이거나 스트리밍 완료 시점에만 실행하도록 개선.
4. **폴더/모드 전환 경쟁 상태(Race Condition) 방지 및 비디오 스트림 즉시 해제 (`app.js`, `stream_sub.py`)**:
   - `loadData()`에 `AbortController` 및 요청 시퀀스 검증(`currentLoadDataSeq`)을 도입하여 빠른 모드 전환 시 이전 응답이 화면을 덮어쓰는 현상 차단.
   - `closePlayer()`에서 `videoPlayer.removeAttribute('src'); videoPlayer.load();`를 호출하여 창을 닫는 즉시 백그라운드 비디오 스트림 다운로드를 완전히 종료.
   - `stream_sub.py`에서 `FlagDefault` 미지정 트랙의 기본값을 `0`으로 교정하여 실제 기본 플래그가 설정된 트랙만 `[기본]`으로 표시되도록 개선.

### Phase 15: 스트림 캐시 오염 방지, HTML 엔티티 복원, WebVTT 규격 준수 및 프로세스 환경 안정화 (2026-11-07)
1. **스트림 중단 및 타임아웃 시 불완전 캐시 영구 오염 방지 (`api.php`)**:
   - 자막 스트리밍 도중 클라이언트 연결 끊김(`connection_aborted()`)이나 타임아웃(`timed_out`) 발생 시, 기존에는 임시 파일(`.tmp`)을 완성된 캐시 파일로 무조건 rename하던 심각한 버그 해결.
   - `$timedOut` 추적 및 `$exitCode === 0 && filesize > 0` 검증을 거친 완전한 스트림만 캐시화하도록 개정하고, 불완전 종료 시 임시 파일을 즉시 unlink 삭제하도록 수정.
2. **PHP `proc_open` 하위 프로세스 환경변수 보존 (`api.php`)**:
   - PHP에서 `proc_open` 실행 시 기존 `$procEnv`에 `PATH`와 `LD_LIBRARY_PATH`가 누락되어 avconv 폴백 호출 시 바이너리를 찾지 못하던 문제 해결.
   - 시스템 `PATH` 및 `/usr/local/wdmcserver/lib`를 환경변수에 명시적으로 포함하여 안정적인 서브프로세스 실행 보장.
3. **손상된 미디어로 인한 프로세스 무한 대기 방지 (`api.php`)**:
   - `probe_subs` 실행 시 `stream_sub.py`는 `timeout 5`, `avconv`는 `timeout 8`을 적용하여 손상된 동영상 파일 파싱 시 아파치 워커 프로세스가 좀비 상태로 블로킹되는 결함 원천 차단.
4. **WebVTT 밀리초 롤오버 버그 방지 및 빈 큐 정리 (`app.js`)**:
   - `formatVttTime(sec)`에서 `(sec - Math.floor(sec)) * 1000` 반올림으로 인해 `1000`이 산출되어 `00:00:01.1000`(4자리 ms) 비표준 문자열이 생성되던 버그를 정수 `totalMs` 수학적 계산 방식으로 전면 개정.
   - `buildVttText()`에서 공백/내용 없는 큐로 인해 3연속 줄바꿈(`\n\n\n`)이 발생하여 브라우저 WebVTT 파서가 깨지던 현상을 방지하도록 빈 큐 자동 필터링 적용.
5. **SRT, ASS, SAMI 자막 HTML 엔티티 복원 (`app.js`)**:
   - `.srt` 및 `.ass` 자막 내의 `&quot;`, `&nbsp;`, `&#39;`, `&amp;` 등의 엔티티가 디코딩되지 않아 화면에 원시 엔티티 코드가 노출되던 결함 수정.
   - `decodeHtmlEntities()`를 도입하여 모든 자막 파서에서 엔티티를 완전 복원한 뒤 `escapeHtml()`을 거쳐 안전하고 깔끔하게 렌더링되도록 통일.
6. **속성 주입 및 특수문자 깨짐 방지를 위한 초경량 고속 `escapeHtml` (`app.js`)**:
   - DOM `createElement('div')` 방식이 `"` 및 `'`를 이스케이프하지 않아 `title="${escapeHtml(...)}"` 속성에서 따옴표가 깨지던 문제 해결.
   - 정규식 기반 치환(`&`, `<`, `>`, `"`, `'`)으로 변경하여 DOM 생성 오버헤드를 없애고 HTML 본문과 속성 모두에서 100% 안전성 확보.
7. **파이썬 2/3 호환성 및 ASS 자막 함수 재할당 최적화 (`stream_sub.py`)**:
   - 자막 루프 내부에서 큐마다 `def ms_to_ass`를 수천 번 재정의하던 CPU 낭비를 제거하고 모듈 최상위 함수로 이동.
   - print 구문을 괄호 함수 호출 형식으로 통일하여 파이썬 2.7(NAS 환경)과 파이썬 3 모두에서 문법 에러 없이 완벽히 동작하도록 개선.
8. **HTTP 약한 ETag(Weak ETag `W/`) 304 Not Modified 호환성 보장 (`api.php`)**:
   - 브라우저나 프록시가 `If-None-Match`에 `W/` 접두사를 붙여 전송할 때 문자열 불일치로 304 캐시 응답이 실패하던 현상을 보완.

### Phase 16: 자막 크기 영구 보존, 전진 탐색 리셋 방지 및 로컬스토리지 예외 방어 (2026-11-07)
1. **자막 확대/축소 배율(`subScale`) 세션 유지 누락 버그 해결 (`app.js`)**:
   - 사용자가 자막 크기를 A+/A-로 조절했을 때 `localStorage`에 저장만 되고 앱 시작 시 읽어오지 않아 매 새로고침 시 1.0배율로 초기화되던 버그를 수정하여 저장된 배율이 영구 유지되도록 개선.
2. **동영상 전진 탐색 시 재생 시간 0초 리셋 결함 차단 (`app.js`)**:
   - 영상 메타데이터 수신 전이나 라이브 스트림에서 `videoPlayer.duration`이 `NaN`일 때, 키보드(ArrowRight) 및 블루투스/미디어세션(`seekforward`) 탐색 시 `Math.min(0, ...)`으로 인해 재생 위치가 0초로 강제 되감기되던 결함 수정 (`Infinity` 폴백 가드 적용).
3. **토스트 알림 타이머 중복 충돌 및 지속시간 누락 개선 (`app.js`)**:
   - 단축키 연타 시 이전 타이머가 취소되지 않아 토스트가 비정상적으로 일찍 사라지던 현상을 방지하도록 `toastTimer` 핸들러를 도입하고, 오류 메시지 전용 지속시간(5초 등) 파라미터를 정상 수용하도록 개선.
4. **자막 스트리밍 완료 후 알림 덮어쓰기 방지 (`app.js`)**:
   - 실시간 자막 파싱 중 예약된 디바운스 타이머(`updateTimer`)가 자막 완료 후 뒤늦게 실행되어 "자막 로드 완료" 알림을 덮어쓰던 문제를 방지하도록 완료 시 타이머 즉시 해제.
5. **사파리 개인정보 보호 모드(Private Browsing) 스토리지 예외 차단 (`app.js`)**:
   - 쿠키 차단 환경이나 모바일 사파리 시크릿 모드에서 `localStorage` 접근 시 발생하는 `QuotaExceededError` 또는 `SecurityError` 예외로 인해 JS 실행이 중단되지 않도록 `safeGetItem`, `safeSetItem`, `safeRemoveItem` 래퍼로 안전 캡슐화.

### Phase 17: 정규식 캡처 오프셋 교정, SAMI 동시 대사 소멸 방지 및 자막 파서 내구성 강화 (2026-11-07)
1. **avconv 자막 프로브 시 언어 미지정 트랙 캡처 그룹 시프트 버그 해결 (`api.php`)**:
   - 언어 태그가 생략된 자막 스트림(`Stream #0:2: Subtitle: srt`) 파싱 시, 선택적 그룹 생략으로 인해 코덱명(`srt`)이 언어 변수로 밀려 들어가고 코덱 변수가 `undefined`로 남아 `Notice: Undefined offset` 및 `[내장-SRT] SRT 자막 (SRT)` 라벨 오염이 발생하던 PHP 정규식 결함을 `count($m) >= 4` 분기 처리로 완벽히 해결.
2. **SAMI(`.smi`) 동시 대사 및 한영 다국어 자막 0초 소멸 버그 해결 (`app.js`)**:
   - 한영 다국어 자막이나 두 명 이상의 화자가 동일한 타임스탬프(`<SYNC Start=12345>`)를 가질 때, 겹침 방지 루프가 직후 큐의 시작 시간으로 종료 시간을 앞당겨 앞선 자막(주로 한국어)의 지속시간이 `0초`로 축소되어 화면에서 완전히 증발하던 심각한 버그 해결.
   - 반드시 시작 시간이 더 늦은 다음 큐(`cues[j].start > cues[i].start`)를 탐색하여 종료 시간을 클램핑하도록 교정하고, 빈 `<SYNC>` 태그 수신 시 열려 있는 모든 동시 대사를 일괄 종료하도록 개선.
3. **공백 라인 포함 SRT 자막 블록 병합 방지 (`app.js`)**:
   - `split('\n\n')` 대신 `split(/\n\s*\n/)` 정규식을 적용하여 공백 문자가 포함된 빈 줄로 구분된 SRT 자막 블록들이 하나로 뭉쳐져 뒷부분 자막이 누락되거나 왜곡되는 문제 해결.
4. **ASS/SSA 대사 태그 매칭 유연성 확보 (`app.js`)**:
   - 대소문자 차이(`dialogue:`)나 콜론 앞뒤 공백(`Dialogue :`), 선행 공백이 포함된 ASS 자막 라인도 정상 인식하도록 `/^Dialogue\s*:/i` 정규식 매칭 적용.
5. **타임스탬프 파싱 `NaN` 반환 방지 (`app.js`)**:
   - 비정상적인 타임스탬프 토큰 파싱 시 `NaN`이 반환되어 `Array.prototype.sort()`의 정렬 계약을 깨뜨리고 자막 큐 순서를 뒤섞던 현상을 방지하도록 `isFinite(res) && res >= 0` 안전 반환 보장.

### Phase 18: 하위 디렉토리 ETag 갱신 누락, 서버 HTTP 에러/JSON 파싱 견고화, 16진수 엔티티 복원 및 탐색기 화살표 개선 (2026-11-07)
1. **하위 폴더 파일 수정 시 ETag 304 고착 결함 해결 (`api.php`)**:
   - Linux ext4 파일시스템 특성상 하위 디렉토리 내부의 파일이 추가/삭제/수정되어도 상위 루트 디렉토리의 `filemtime`은 변경되지 않는 특성으로 인해, 파일 개수가 같을 때 클라이언트가 만료된 데이터를 계속 304 Not Modified로 수신하던 버그 해결.
   - `mode=all`에서 재귀 탐색 중 `$maxMtime`을 추적하여 전체 파일/폴더 중 최신 수정 시간을 ETag 계산 해시에 포함하도록 개정.
   - `mode=folder`에서도 해당 디렉토리 내 각 항목의 최신 수정 시간(`$maxFolderMtime`)을 산출하여 개별 파일 수정 시에도 즉각적인 캐시 무효화 및 새 목록 전달 보장.
2. **서버 HTTP 500/HTML 에러 페이지 시 비정상 JSON 파싱 크래시 차단 (`app.js`)**:
   - `loadData()` 및 `probe_subs`에서 서버 응답의 `resp.ok` 여부를 확인하지 않고 곧바로 `resp.json()`을 호출하여 발생하던 `SyntaxError: Unexpected token '<'` 원시 예외 방지.
   - `!resp.ok` 시 `서버 응답 오류 (HTTP ${status})`를 깔끔하게 렌더링하고, JSON 파싱 실패 시에도 안내 메시지를 표시하도록 예외 처리 방어막 구축.
3. **자막 16진수 수치 엔티티 및 유니코드 복원 (`app.js`)**:
   - 기존 10진수 엔티티(`/&#([0-9]{1,5});/`)만 처리하던 파서를 확장하여 16진수 수치 문자 참조(`/&#x([0-9a-fA-F]{1,6});/gi`) 및 `String.fromCodePoint` 지원 추가. 한국어 SAMI/ASS 자막에 사용되는 16진수 특수문자 및 한글이 온전하게 복원되도록 개선.
4. **URL 자동 재생 매칭 시 파일명 경계 구분자 슬래시 검증 (`app.js`)**:
   - URL 인자로 전달된 비디오 자동 재생 처리(`targetVideoRel`) 시 `cleanPath.endsWith(v.rel_path)`를 슬래시 경계 없이 수행하여 `anothersample.mp4`가 `sample.mp4`에 잘못 매칭되던 부분 문자열 오류를 슬래시(`/`) 경계 검증으로 완벽 교정.
5. **검색 필터 활성화 상태에서의 다음/이전 영상 탐색 개선 (`app.js`)**:
   - 검색창에 검색어가 입력되어 목록이 필터링된 경우, 영상 종료 시 자동 재생 및 단축키(Shift+N/P)가 전체 목록이 아닌 현재 화면에 표시된 검색 결과 목록을 기준으로 순차 재생하도록 `getActivePlaylist()` 도입.
6. **익스플로러 바로가기 버튼 화살표 렌더링 개선 (`index.html`, `style.css`)**:
   - 텍스트/유니코드 문자(`->`, `↗`)로 인해 모바일 및 특정 폰트 환경에서 어색하게 보이거나 깨지던 익스플로러 버튼 화살표를 웹플레이어 내 타 버튼들과 동일한 규격의 정밀 벡터 인라인 SVG 우측 화살표로 교체.
   - 마우스 호버 시 화살표가 자연스럽게 이동하는 마이크로 인터랙션 CSS 애니메이션 추가.
7. **키보드 이벤트 핸들러 안전성 보강 (`app.js`)**:
   - `e.target`이 `Document` 또는 `Window`일 때 `e.target.matches` 미지원으로 발생할 수 있는 `TypeError`를 방지하도록 `typeof e.target.matches === 'function'` 검증 적용.
8. **자막 크기 조절 피드백 토스트 및 소수점 정밀도 정리 (`app.js`)**:
   - `updateSubtitleScale` 호출 시 소수점 연산 오차 방지를 위해 2자리 반올림을 적용하고, 자막 크기 변경 시 즉각적인 토스트 알림(`자막 크기: 115%`)을 출력하여 사용자 편의 증대.
9. **파이썬 2/3 `ord` 바이트 인덱싱 호환성 보장 (`stream_sub.py`)**:
   - 파이썬 3 환경에서 `bytes` 인덱싱 시 이미 `int`가 반환되어 `ord()` 호출 시 `TypeError`가 발생하는 문제를 해결하기 위해 모듈 수준의 `ord` 호환성 래퍼를 도입하여 파이썬 2(NAS 환경)와 파이썬 3 모두 완벽 호환 보장.

### Phase 19: Intl.Collator 27.5배 고속 정렬, 문자열 이스케이프 제로 할당, stat 시스템콜 반감 및 Gzip/캐시 압축 최적화 (2026-11-07)
1. **Intl.Collator 인스턴스 재사용 기반 목록 정렬 27.5배 가속 (`app.js`)**:
   - 정렬 루프(`Array.prototype.sort`) 내부에서 반복 호출되던 `a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' })`가 매 비교마다 로케일 옵션 객체를 생성하여 CPU를 점유하던 병목을 제거.
   - 단일 싱글톤 `new Intl.Collator(undefined, { numeric: true, sensitivity: 'base' })` 인스턴스를 사전 생성하여 재사용하도록 개정. 1000개 파일 정렬 벤치마크 기준 1.35초에서 49ms로 27.5배 대폭 가속.
2. **문자열 이스케이프 무할당 패스트패스 도입 (`app.js`)**:
   - `escapeHtml(text)`에서 특수문자(`[&<>"']`)가 없는 95% 이상의 일반 파일명에 대해서도 5회 연속 체이닝 `.replace()`가 호출되어 가비지 컬렉터 부하를 유발하던 현상을 해결.
   - 단일 정규식 사전 검사 `if (!_HTML_CHARS.test(str)) return str;`를 추가하여 특수문자가 없는 경우 0 메모리 할당으로 7.3배 빠르게 즉시 반환하도록 최적화.
3. **단일 `stat` 시스템콜(`getSafeFileStat`) 통합 및 디렉토리 스캔 루프 가지치기 (`api.php`)**:
   - 파일 스캔 시 `getSafeFileSize()`와 `@filemtime()`이 개별적으로 `stat()` 시스템콜을 중복 호출하던 비효율을 `getSafeFileStat()`으로 통합하여 1회의 stat 호출로 파일 크기와 mtime을 동시 획득하도록 단축.
   - `mode=all` 및 `mode=folder`에서 `pathinfo()` 호출 전 `strrpos($item, '.')` 확장자 검사를 우선 수행하여 비미디어 파일에 대한 불필요한 상대 경로 연산 및 정규식 평가를 원천 배제.
   - `mode=folder`에서 1차 순회 시 `$rawVideos`와 `$subtitlesMap`으로 분리 수집하여 2차 순회 시 불필요한 배열 재순회 및 `pathinfo` 재호출 제거.
   - `makeWebUrl()`에 표준 ASCII 영숫자 및 언더바/하이픈/점 경로에 대한 패스트패스를 추가하여 `explode`/`array_map` 배열 할당을 생략.
4. **파이썬 2/3 바이트 서명 결합 호환성 및 무결성 보장 (`stream_sub.py`)**:
   - `cues_data.find(track_sig)` 서명 생성 시 `chr(target_track_num)`을 `struct.pack('>B', target_track_num)` 및 `struct.pack('>H', target_track_num)`으로 교체하여 파이썬 3 환경에서 발생하던 `TypeError: can't concat str to bytes` 예외를 방지하고 파이썬 2/3 간 바이너리 패킹 성능 일치 보장.
5. **Apache mod_deflate Gzip 압축 및 7일 브라우저 캐싱 적용 (`apache/apache_webplayer.conf`, `apache/webplayer.conf`)**:
   - 웹플레이어 디렉토리(`/shares/webplayer`)에 `mod_deflate`를 활성화하여 `app.js`(85KB -> 23KB, 73% 압축), `style.css`(25KB -> 6KB, 76% 압축), `api.php` JSON 응답(45KB -> 7.6KB, 83% 압축)의 전송량을 1/4 이하로 경량화.
   - `.css`, `.js` 정적 에셋에 `Cache-Control: max-age=604800, public`(7일) 헤더를 적용하고, 배포 시 `index.html`의 `?v=...` 쿼리 버전을 자동 갱신하여 첫 방문 이후 네트워크 왕복 시간(0ms) 제거.

### Phase 20: 뷰포트 밖 렌더링 스킵(content-visibility), 검색 정규화 사전 인덱싱 및 자막 매칭 배열 할당 제거 (2026-11-07)
1. **CSS `content-visibility: auto` 기반 뷰포트 외 렌더링 스킵 최적화 (`style.css`)**:
   - 수백 개의 영상 및 폴더 카드가 존재하는 대형 라이브러리(`mode=all`)에서 브라우저가 화면 밖의 카드까지 전체 스타일/레이아웃/페인팅을 계산하던 렌더 트리 부하를 차단.
   - `.folder-card, .video-card`에 `content-visibility: auto; contain-intrinsic-size: auto 200px;`를 지정하고, 리스트 뷰에는 `contain-intrinsic-size: auto 60px;`를 적용하여 뷰포트 내부 요소만 효율적으로 렌더링하도록 개선. 모바일 60fps 스크롤 유지.
2. **검색 키워드 사전 정규화 인덱싱(`_searchKey`)을 통한 타이핑 검색 가속 (`app.js`)**:
   - 검색창 입력 시 매 키 입력마다 수백 개 동영상의 이름과 폴더 경로에 대해 반복 실행되던 `v.name.toLowerCase()` 및 `v.folder.toLowerCase()` 런타임 문자열 할당을 제거.
   - 데이터 수신(`loadData`) 시점에 `_searchKey`를 사전 생성하여 단일 `includes()` 비교로 2배 이상 빠른 실시간 검색 필터링 구현.
3. **자막 타임스탬프 파싱 정규식 분할 제거 및 스트링 인덱스 슬라이싱 (`app.js`)**:
   - 자막 파싱 시 수천 번 반복 호출되던 `parseTimestamp(str)`에서 `str.trim().split(/\s+/)` 정규식 분할을 제거하고 `indexOf(' ')` 기반 인덱스 슬라이싱으로 대체하여 중간 배열 할당을 완전히 제거.
4. **자막 파일명 매칭 인라인 문자 비교 및 비디오 베이스네임 길이 캐싱 (`api.php`)**:
   - `isMatchingSubtitleBase` 함수에서 다음 구분자 문자 검사 시 `in_array($c, array('.', '_', ...))` 배열을 매번 동적 생성하던 PHP 내부 해시테이블 할당을 인라인 동등 비교(`$nextChar === '.' || ...`)로 변경하여 메모리 할당 0화.
   - 비디오 베이스네임의 길이(`$vLen`)를 루프 진입 전 1회만 계산하여 자막 비교 루프에 전달함으로써 불필요한 `strlen()` 재계산 오버헤드 제거.

### Phase 21: 제로 디스크 온디맨드 실시간 MKV -> HLS(MPEG-TS) 리먹싱 엔진 구축 (2026-11-22)
1. **MKV 키프레임(Cues) 정렬 가상 HLS 인덱서 구현 (`stream_sub.py`)**:
   - `hls_info` 서브커맨드를 추가하여 MKV의 `SegmentInfo`(`TimecodeScale`, `Duration`), `Tracks`(비디오/오디오 스트림 및 코덱), `Cues`(전체 IDR 키프레임 타임스탬프)를 디스크 쓰기 없이 수십 ms 내에 고속 파싱.
   - 키프레임 경계에 정확히 맞춘 약 10초 단위 세그먼트 목록을 생성하여, 구버전 `avconv 0.8.13`에서 비-키프레임 탐색 시 발생하던 33-bit PTS 음수 래핑(`95443s`) 현상을 원천 차단.
2. **가상 HLS 매니페스트 및 온디맨드 세그먼트 리먹싱 API (`api.php`)**:
   - `action=hls_manifest`: RAM 캐시(`/tmp/webplayer_sub_ram/hls_*.json`, 최대 40개 자동 정리) 기반으로 `#EXT-X-DISCONTINUITY`가 포함된 표준 RFC 8216 VOD `.m3u8` 매니페스트를 즉석 생성.
   - `action=hls_seg`: 요청된 세그먼트 인덱스(`i`)만 `/usr/local/wdmcserver/bin/avconv -ss <start> -i <mkv> -t <dur> -c:v copy -c:a copy -bsf:v h264_mp4toannexb -f mpegts pipe:1`로 HDD 쓰기 없이 실시간 리먹싱 스트리밍. `connection_aborted()` 및 20초 타임아웃 시 `proc_terminate(9)`로 좀비 프로세스 완전 차단.
3. **자동 감지·폴백·수동 전환 UI 및 오프라인 `hls.js` 지원 (`index.html`, `app.js`, `deploy_webplayer.py`)**:
   - iOS Safari / macOS Safari / Firefox 등 MKV 미지원 브라우저에서는 자동으로 실시간 HLS 리먹싱 모드로 재생(Safari는 네이티브 HLS, 비-Safari는 로컬 `hls.light.min.js` 지연 로드로 LAN 오프라인 완전 지원).
   - Chrome/Edge에서는 0-CPU 원본 직접 재생을 우선 시도하되, 재생 오류(`error`) 발생 시 실시간 HLS 리먹싱으로 자동 폴백.
   - 플레이어 상단에 MKV 전용 **HLS** 수동 전환 버튼(`#btn-hls-remux`)을 추가하여 재생 위치(`currentTime`)를 유지한 채 원본/HLS 모드 간 즉시 전환 가능.

### Phase 22: iOS Safari(AVPlayer) HLS 재생 호환성 완전 해결 및 고속화 (2026-11-23)
1. **MKV `Cues` 비디오 트랙(`CueTrack`) 필터링으로 PTS 역전/중복 버그 근본 해결 (`stream_sub.py`)**:
   - 내장 ASS/SRT 자막이 포함된 MKV(예: `신의 물방울` 등)의 `Cues` 블록에 자막 트랙(Track 3)의 큐 포인트가 비디오 키프레임과 혼재되어 있어, `probe_hls_info()`가 비-키프레임 시점(`7.820s`, `11.690s` 등)을 세그먼트 시작점으로 잡던 치명적 원인 규명 및 수정.
   - `CueTrackPositions`(`0xB7`) 내부의 `CueTrack`(`0xF7`)을 비디오 트랙 번호(`video_track_num`)와 정확히 대조하여 순수 비디오 IDR 키프레임만 추출하도록 수정.
   - `Tracks`의 `CodecPrivate`(`avcC`, AAC `AudioSpecificConfig`) 및 `PixelWidth`/`PixelHeight`를 0ms 비용으로 직접 파싱하여 Master Playlist에 파일별 정확한 `CODECS`(`avc1.XXXXXX,mp4a.40.X`) 및 `RESOLUTION` 제공.
   - 초반 2개 세그먼트는 ~2초(`~1.3~1.9MB`) 고속 스타트업으로 구성하고 이후 세그먼트는 ~4초로 전환하는 하이브리드 분할 적용.
2. **연속 타임라인 MPEG-TS 리먹싱·경계 프레임 중복 방지·동시성 직렬화 및 3배 가속 (`stream_sub.py`, `api.php`)**:
   - `ts_shift` 서브커맨드로 세그먼트 내 33-bit PCR/PTS/DTS를 `+startSec * 90000`만큼 고속 시프트하여 `#EXT-X-DISCONTINUITY` 없는 연속 타임라인 구현(모든 세그먼트 경계 오차 정확히 1프레임 `+0.0420s`).
   - `hls_master` Apple Master Playlist, 정확한 `Content-Length`, `Accept-Ranges: bytes`, HTTP 206 Byte-Range 응답, RAM tmpfs 캐시(`hseg_v3_*`, 최대 4세그먼트 상한) 구현.
   - 비-말단 세그먼트에 `-t (dur - 0.010)`을 적용하여 24/30/60fps MKV에서 다음 세그먼트 IDR 키프레임이 중복 포함되는 현상 차단.
   - `avconv`에 `-probesize 65536 -analyzeduration 0`을 적용해 폰트 첨부가 많은 MKV의 세그먼트 리먹싱 시간을 `1.25s -> 0.42s`(3배) 단축하고, `flock` 직렬화로 iOS CoreMedia 프로브 동시 요청 시 중복 `avconv` 실행 차단.
3. **iOS Safari `<video>` 제스처·로딩·터치 컨트롤 호환성 개선 (`app.js`, `index.html`)**:
   - `openPlayer()`에서 `playerModal.classList.add('active')`를 `attachVideoSource()`보다 먼저 실행하여 `<video>`가 렌더 트리에 표시된 상태에서 사용자 탭 제스처 내 `play()`가 호출되도록 수정.
   - 네이티브 Safari HLS 경로에서 불필요한 `videoPlayer.load()` 선행 호출 및 중복 `loadedmetadata` 리스너 누수를 제거하여 세그먼트 0 조기 중단/재요청 방지.
   - 터치 기기에서 네이티브 `<video controls>` 재생 탭과 충돌하던 `videoPlayer` `click` 토글 핸들러를 데스크톱 전용으로 분기하고 `webkit-playsinline` 속성 추가.

### Phase 23: HLS 세그먼트 인프로세스 PHP 타임스탬프 시프트 및 1-세그먼트 선행 프리페치 가속 (2026-11-23)
1. **인프로세스 PHP 33-bit PCR/PTS/DTS 시프트 전환 (`api.php`)**:
   - 매 세그먼트마다 별도 Python 프로세스를 생성해 순수 루프로 TS 패킷을 순회하던 `stream_sub.py ts_shift`(`0.64s ~ 0.78s`)를 제거하고, 이미 상주 중인 PHP 내부에서 32-bit ARM 부동소수점 정밀도(53-bit mantissa)로 33-bit 타임스탬프를 직접 보정하는 `shiftTsFileInPlace()` 구현.
   - 문자열 비트마스크 사전 필터로 페이로드 패킷의 99% 이상을 `ord()` 호출 없이 건너뛰어 보정 시간을 **`0.71s -> 0.14s`(5배 가속)**로 단축(기존 Python 출력과 MD5 100% 바이트 동일 검증).
2. **비차단 1-세그먼트 선행 프리페치(Lookahead Prefetch) 구현 (`api.php`)**:
   - `api.php` 내부 CLI 모드(`--prefetch`)와 `flock -n hseg_prefetch.lock` 비차단 락을 결합해, NAS 전체에서 동시에 최대 1개의 프리페치 작업만 실행되도록 보장(CPU/RAM 누적 방지).
   - `hls_master` / `hls_manifest` 응답 시 `seg 0`을 백그라운드로 즉시 워밍업하고, `hls_seg`에서 `seg N`을 네트워크로 전송하는 동안 `seg N+1`을 병렬로 RAM 캐시(`hseg_v3_*`, 최대 5세그먼트 상한 및 60초 초과 `.tmp` 자동 정리)에 선행 생성.
   - 실기 아이폰 WAN 재생 로그에서 프리페치 적중 시 `2.7~2.8MB` 세그먼트 전체 응답 시간이 기존 `~2.5s`에서 **`0.92s ~ 0.97s`**로 단축됨을 확인.

### Phase 24: 제로-`avconv` 순수 PHP 직접 MKV -> HLS v7 fMP4(CMAF) 리먹싱 엔진 구축 (2026-11-23)
1. **외부 바이너리(`avconv`/`python`) 완전 배제 순수 PHP fMP4 리먹서 구현 (`fmp4_muxer.php`, `api.php`)**:
   - MKV 내부의 H.264 `SimpleBlock` 페이로드가 MP4 AVCC 길이-접두 NAL 포맷과 동일하고, AAC 페이로드가 MP4 원시 프레임과 동일하며, `CodecPrivate`가 `avcC`/`esds`와 바이트 단위 호환된다는 점을 활용해 `avconv` 프로세스 실행 없이 PHP가 직접 MKV `CueClusterPosition`으로 `fseek()`하여 ISO 14496-12 CMAF `init.mp4` 및 `styp+moof+mdat`(`.m4s`) 세그먼트를 생성.
   - `BlockGroup`(`0xA0`/`0xA1`), Xiph/Fixed/EBML Lacing, `Header Stripping`(`algo=3`), B-프레임(`trun` v1 부호 있는 `composition_time_offset`), 1024-샘플 그리드 정렬 AAC 타임스탬프(`gap=+0`)를 모두 지원하며, 제로카피 직스트리밍으로 3MB 문자열 재할당 및 임시 파일 쓰기를 완전 제거.
   - `Cues` 파서에 인라인 `CuePoint` 파싱과 C-속도 `strpos` 비디오 트랙 사전 필터를 적용해 30개 이상 자막이 든 다국어 MKV의 초기 파싱 시간을 `4.17s -> 0.56s`(7.4배) 단축.
   - 32-bit ARM PHP `fseek()` 한계(2GB 이상 파일) 또는 AC3/MP3/비표준 코덱 MKV에서는 기존 `avconv` MPEG-TS HLS v3 엔진으로 자동 무중단 폴백.
2. **직접 미디어 플레이리스트(`#EXT-X-VERSION:7`) + Gzip 압축 + 2초 세그먼트 전면 전환 (`api.php`, `app.js`, `deploy_webplayer.py`)**:
   - `app.js`에서 `hls_master` 단계를 생략하고 `hls_manifest`를 직접 호출해 초기 WAN 왕복 3회를 제거하고, 비-Range 요청 시 플레이리스트를 `gzencode` 압축(`171KB -> 2.9KB`, 59배 축소) 전송.
   - 전 구간 2초 세그먼트 + fMP4 컨테이너 오버헤드 절감(MPEG-TS 8.5% -> fMP4 0.15%)으로 실측 세그먼트 서버 응답(TTFB) **`74ms ~ 129ms`(기존 대비 11~16배 가속)**, 9분 탐색 포함 전 경계 비디오/오디오 갭 **`+0`**, 임시 RAM 사용량 `24MB -> 128KB`(190배 절감), 하위 프로세스 `0개` 달성.
3. **iOS Safari CoreMedia fMP4 규격 완전 일치 보정 (`fmp4_muxer.php`, `app.js`)**:
   - 실기 로그 분석 결과 iOS AVPlayer는 HLS v7 fMP4(`#EXT-X-MAP`)에서 Master Playlist(`#EXT-X-STREAM-INF:BANDWIDTH,CODECS`) 없이 미디어 플레이리스트를 직접 열 경우 세그먼트 0을 200KB 지점에서 반복 중단하는 현상을 확인하여 `app.js`에서 `hls_master` 진입을 복원(비용 55ms).
   - FFmpeg Apple HLS fMP4 표준 레퍼런스와 1:1 일치하도록 `ftyp`(`iso5`/`iso6`/`mp41`), `avc1` 내 `pasp`(1:1), QuickTime/CoreMedia 4바이트 확장 길이 `esds`(`80 80 80 <len>`), 오디오 `tfhd`/`trex` `default_sample_flags=0x02000000`, IP-only 비디오 `trun v0(0x000305)`, `Content-Type: video/mp4`로 정렬하고 FFmpeg 9.0 라이브 HLS 디코드 0경고/0오류 검증 완료.

### Phase 25: iPhone Safari 전체화면 버튼 수정 및 네이티브 전체화면 자막(`#EXT-X-MEDIA:TYPE=SUBTITLES`) 완전 지원 (2026-11-23)
1. **iOS Safari 전용 전체화면 API 및 이벤트 통합 (`app.js`)**:
   - iPhone Safari는 표준 `requestFullscreen()`/`webkitRequestFullscreen()`을 지원하지 않으므로 `videoPlayer.webkitEnterFullscreen()` / `webkitExitFullscreen()` 폴백을 추가하고, `isFullscreen()`에 `videoPlayer.webkitDisplayingFullscreen`을 포함.
   - `<video>`의 `webkitbeginfullscreen` / `webkitendfullscreen` 이벤트를 등록하여, 페이지의 **전체화면 버튼**과 **Safari 자체 플레이어 전체화면 버튼** 모두에서 전체화면 상태와 자막 전환이 정확히 동기화되도록 수정.
2. **Apple 네이티브 HLS WebVTT 자막 파이프라인 구축 (`api.php`, `app.js`)**:
   - iOS `AVPlayerViewController`는 네이티브 전체화면 전환 시 브라우저 메모리의 `blob:` `<track>`을 읽지 못하므로, `api.php`에 서버측 UTF-8 WebVTT 변환기(`decodeSubtitleToUtf8` + `convertSubContentToVtt`, UTF-16/CP949/UTF-8 자동 디코딩 및 SMI/SRT/ASS/VTT 지원)와 `hls_sub_m3u8` / `hls_sub_vtt` 엔드포인트를 구현.
   - `hls_master`에 외부 매칭 자막(한국어 우선 `DEFAULT=YES`)과 내장 MKV 자막을 `#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs"`로 자동 삽입하여, Safari 자체 플레이어 전체화면·iOS 네이티브 CC 메뉴·AirPlay에서도 자막이 그대로 표시되도록 구현.
   - 일반 `.mp4` 직접 재생 시에도 iOS에서는 `blob:` 대신 HTTP `hls_sub_vtt` URL을 `<track>`에 연결하고, 창모드에서는 네이티브 트랙을 비활성화(`disabled`)해 커스텀 DOM 자막과의 이중 표시를 원천 차단.
