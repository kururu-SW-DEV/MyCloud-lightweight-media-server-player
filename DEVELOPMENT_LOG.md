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
   - `--bg-card`: `#1e293b` ➔ `#182235` (WebExplorer와 동일한 다크 슬레이트 블루)
   - `--bg-hover`: `#334155` ➔ `#26334d`
   - `--text-main`: `#f8fafc` ➔ `#f1f5f9` (슬레이트 100)
   - `--border-card: rgba(255, 255, 255, 0.08);` 추가 및 카드/네비바/검색창 테두리 적용
   - `--radius`: `10px` ➔ `8px` 일치화
   - `--shadow`: `0 2px 8px rgba(0, 0, 0, 0.28);`
2. **컴포넌트 스타일 정밀 일치**:
   - 검색창: 라운드 알약형(`20px`) ➔ 모던 라운드 사각(`7px`, `border-card`, 포커스 시 시안 글로우 `0 0 0 2px rgba(56, 189, 248, 0.15)`).
   - 카드 테두리: 기본 `border: 1px solid var(--border-card);`, 호버 시 `border-color: rgba(56, 189, 248, 0.4);`.
   - 썸네일 그라디언트: `#182235` 베이스로 일치화.
   - 모달 다이얼로그: `#111827` 베이스, 10px 곡률, 미세 보더 적용.

### Phase 7: 익스플로러 ↔ 미디어 플레이어 상호 전환 버튼 완전 통일화 (2026-11-04)
1. **버튼 위치 대칭성 확보**:
   - 미디어 플레이어 상단 네비바 우측(`.nav-actions`)과 익스플로러 상단 네비바 우측(`.nav-actions`)의 동일 위치에 상호 전환 버튼 배치.
2. **버튼 스타일 및 네이밍 통일 (`.btn-nav-switch`)**:
   - 공통 클래스 `.btn.btn-secondary.btn-nav-switch` 정의 (패딩 `7px 12px`, 모서리 `7px`, 배경 `var(--bg-hover)`, 테두리 `rgba(255, 255, 255, 0.08)`, 호버 시 시안 글로우).
   - 표기 규격: `Explorer ↗` (플레이어 측) ↔ `Player ↗` (익스플로러 측).
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
