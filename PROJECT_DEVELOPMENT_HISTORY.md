# MyCloud Media Player 제작 과정 기록서 (Project Development History)

- **프로젝트 명**: MyCloud Media Player (초경량 NAS 웹 미디어 플레이어)
- **개발 기간**: 2026-09 ~ 2026-11-23 (총 26개 Phase)
- **타겟 서버**: WD My Cloud Gen 1 (ARMv7 650MHz, 32-bit Debian Wheezy, 226MB RAM, 5400RPM HDD, Apache 2.4, PHP 5.6.7, Python 2.7, avconv 0.8.13)
- **배포 경로**: `/shares/webplayer/` (웹 URL: `/player/`, 미디어 루트: `/shares/Public/`)
- **로컬 저장소**: `C:\Users\nzlhu\Desktop\AI 작업\3. 경량 서버용 미디어 플레이어\`
- **최신 안정 버전**: `v20261123_1` (Phase 26 감사 및 검증 완료)

---

## 1. 프로젝트 배경과 하드웨어 제약 조건

WD My Cloud Gen 1은 2013년 출시된 초저전력 단일 베이 NAS로, 현대적인 미디어 서버(Plex, Jellyfin 등)를 구동하기에는 극단적인 하드웨어 제약을 갖고 있습니다.

| 항목 | 하드웨어 / OS 사양 | 설계에 미친 핵심 제약 |
| :--- | :--- | :--- |
| CPU | Mindspeed Comcerto 2000 (ARMv7 650MHz, 32-bit) | 실시간 비디오 트랜스코딩 불가, 프로세스 fork 1회당 40~60ms 소요 |
| RAM | 총 226MB (OS 제외 가용 약 90~120MB) | 대용량 버퍼/캐시 할당 불가, `/tmp` tmpfs 엄격 상한 필수 |
| Storage | 5400RPM SATA HDD | 랜덤 쓰기/디스크 캐시 시 헤드 경합 및 슬립 방해 -> **Zero-Disk 원칙** |
| 런타임 | PHP 5.6 (32-bit, `PHP_INT_MAX = 2.14GB`), Python 2.7, `avconv 0.8.13` | 2.14GB 초과 파일 `filesize()` 음수 오버플로, `fseek()` 2GB 한계, PHP 5.6 `usort` 비안정 정렬 |
| SSH | OpenSSH 6.0p1 (레거시 `ssh-rsa` 호스트 키) | 로컬 배포 도구 `paramiko==3.5.1` 고정 필요 |

이러한 환경에서 **외부 트랜스코딩 서버 없이**, **HDD 디스크 쓰기 0바이트**를 유지하면서 **PC(Chrome/Edge/Firefox), Android, iPhone/iPad Safari** 모든 기기에서 고화질 MKV/MP4 영상과 다국어 내장·외부 자막을 즉각 스트리밍할 수 있는 초경량 웹 미디어 플레이어를 단계적으로 설계·고도화했습니다.

---

## 2. 최종 시스템 아키텍처

```
[Client: PC / Android / iPhone Safari]
  │
  ├─ UI & Control (index.html, style.css, app.js)
  │   ├─ 폴더/전체 탐색 (ETag 304, Intl.Collator 27.5x 정렬, content-visibility: auto)
  │   ├─ 재생 엔진
  │   │   ├─ Chrome/Edge (MP4/MKV): 원본 HTTP Range 직접 스트리밍 (실패 시 HLS 자동 폴백)
  │   │   ├─ iOS/macOS Safari (MKV): 네이티브 HLS v7 fMP4 (Master -> Media -> init.mp4 + .m4s)
  │   │   └─ Firefox/비-Safari (MKV): 오프라인 로컬 hls.light.min.js (MSE)
  │   └─ 듀얼 자막 엔진
  │       ├─ Desktop/Android 창모드: 커스텀 DOM 오버레이 (SRT/ASS/SAMI/VTT, CP949/UTF-16/UTF-8)
  │       ├─ Desktop/Android 전체화면: WebVTT Blob <track> (video::cue 동적 스타일 동기화)
  │       └─ iPhone/iPad Safari: 네이티브 HLS #EXT-X-MEDIA:TYPE=SUBTITLES (RFC 8216 X-TIMESTAMP-MAP)
  │
  ▼ HTTP (LAN 무인증 / WAN Basic Auth + mod_deflate Gzip + 7일 정적 캐시)
[Apache 2.4 -> /shares/webplayer/api.php]
  │
  ├─ 디렉토리/메타 API (?dir=, ?all=1): getSafeFileStat() 32비트 무포크 4GB 대응 + ETag 304
  ├─ 순수 PHP HLS v7 fMP4 리먹서 (fmp4_muxer.php):
  │   └─ <2GB H.264+AAC MKV -> avconv/python 0회, 직접 fseek() + 제로카피 .m4s (TTFB 74~129ms)
  ├─ 폴백 HLS v3 MPEG-TS 리먹서 (api.php + stream_sub.py + avconv):
  │   └─ >=2GB 또는 AC3/MP3/비표준 MKV -> 인프로세스 PHP TS 시프트 + 비차단 1-세그먼트 프리페치
  ├─ 고속 자막 엔진 (stream_sub.py + api.php):
  │   ├─ Matroska EBML Cues Direct Seek (<10ms 프로브, 실시간 파이프 스트리밍)
  │   └─ 서버측 UTF-8 WebVTT 변환기 (hls_sub_m3u8 / hls_sub_vtt, 중복 ASS 큐 제거)
  └─ 휘발성 RAM 캐시 (/tmp/webplayer_sub_ram, tmpfs, 자동 상한 정리로 1~2MB 유지)
       │
       ▼ Read-Only (HDD 쓰기 0바이트)
[/shares/Public (5400RPM HDD 미디어 저장소)]
```

### 현재 배포 소스 구성 (`webplayer/`)

| 파일 | 크기 | 라인 수 | 주요 역할 |
| :--- | ---: | ---: | :--- |
| `api.php` | 74.6 KB | 1,798 | 디렉토리/검색 API, 보안 검증, HLS Master/Media/TS/WebVTT 엔드포인트, 프리페치 CLI |
| `fmp4_muxer.php` | 42.5 KB | 1,024 | 제로-`avconv` 순수 PHP 직접 MKV -> HLS v7 fMP4(CMAF) 리먹싱 엔진 |
| `stream_sub.py` | 45.0 KB | 1,123 | Matroska EBML 파서, Cues Direct Seek 자막 추출기, HLS 키프레임 인덱서 |
| `app.js` | 104.6 KB | 2,552 | 프론트엔드 SPA, 플로팅/미니 플레이어, HLS 제어, 듀얼 자막 파서, MediaSession API |
| `style.css` | 30.7 KB | 1,417 | 다크 슬레이트 테마(WebExplorer 통일), 반응형 그리드/리스트, GPU 가속 자막 스타일 |
| `index.html` | 16.0 KB | 191 | 시맨틱 마크업, 선형 모노크롬 SVG 아이콘, 배포 시 자동 `?v=` 캐시 버스팅 |
| `hls.light.min.js` | 296.5 KB | 1 | 비-Safari 브라우저용 오프라인 내장 HLS.js MSE 엔진 |

---

## 3. 단계별 제작 과정 연대기 (Stage 1 ~ Stage 6, Phase 1 ~ 26)

### Stage 1: Zero-Disk 기반 확립 및 고속 MKV 자막 엔진 구축 (Phase 1 ~ 2)
- **목표**: HDD 쓰기 없이 10GB+ MKV 내부의 다국어 자막을 수십 ms 내에 탐지하고 실시간으로 브라우저에 전달.
- **핵심 구현**:
  - `stream_sub.py`에 Python 2.7 순수 Matroska EBML 파서를 구현하여 `SeekHead` -> `Tracks` -> `Cues` 인덱스로 직행.
  - `avconv` 전체 스캔(2.5초 이상) 대신 `CueClusterPosition` + `CueRelativePosition(rpos)`로 자막 블록만 직접 seek하여 추출.
  - 다국어(76트랙) MKV에서 한국어 트랙 감지 시 서브프로세스 반복 생성을 제거하여 프로브 응답을 **2.04초 -> 0.39초**로 단축.
  - `deploy_webplayer.py` 배포 스크립트에 `/tmp/webplayer_sub_ram/*` 초기화 단계를 통합.

### Stage 2: 보안 전면 감사 및 32-bit 아키텍처 한계 돌파 (Phase 3 ~ 4)
- **목표**: 외부 포트포워딩(WAN) 노출 환경에서의 보안 취약점 차단 및 32비트 PHP 파일 크기 오버플로 해결.
- **핵심 구현**:
  - **보안 방어**: `validateRelativePath()`로 `..`, 이중 URL 인코딩(`%252e%252e`), Null 바이트(`\0`, `%00`) 차단. `is_link()`로 심볼릭 링크 탈출 및 `/tmp/webplayer_sub_ram` 하이재킹 방어. Apache `Options -Indexes` 및 WAN 구간 Basic Auth + NAS 관리자 페이지(`/var/www/htdocs`) 외부 403 완전 차단.
  - **프로세스 감독**: 자막 파이프에 `stream_set_timeout(15)`와 `connection_aborted()` 감지를 결합하여 탭 닫기/영상 전환 시 백그라운드 프로세스를 즉각 `SIGKILL(9)`로 정리.
  - **32-bit 2.14GB 정수 오버플로 해결**: 32비트 PHP에서 3GB 영화의 `filesize()`가 음수로 반전되어 목록에서 사라지던 결함을 64비트 대응 크기 계산으로 해결(3GB 스파스 파일 실측 검증).

### Stage 3: 모던 UI 개편, WebExplorer 통합 및 목록 10배 고속화 (Phase 5 ~ 11)
- **목표**: WebExplorer와 동일한 디자인 언어로 UI를 정제하고, 저사양 NAS의 폴더/전체 탐색 지연을 극한까지 단축.
- **핵심 구현**:
  - **Zero AI Slop / 100% Monochrome SVG**: 모든 컬러 이모지를 제거하고 WebExplorer와 동일한 다크 슬레이트 블루 팔레트(`#0f172a` / `#182235` / `#38bdf8`) 및 Linear SVG 벡터 아이콘으로 통일.
  - **양방향 원클릭 연동**: 상단 우측 `Explorer ->` <-> `Player ->` 버튼 및 `?open=Public/...` 경로 자동 정규화 재생 지원.
  - **미디어 편의성 강화**: 5단계 배속(`0.75x ~ 2.0x`), 전체 데스크톱 단축키(`Space`, `Arrow`, `F`, `M`, `B`, `+/-`, `[/]`, `Shift+N/P`), 잠금화면/블루투스 제어용 MediaSession API(`setPositionState`, `seekto`) 통합.
  - **트랙 인덱스 섀도잉 수정 (Phase 10)**: 76트랙 MKV에서 `cur_stream`과 `tnum`(1-based)을 `or`로 비교해 엉뚱한 언어(일본어)가 출력되던 버그를 `cur_stream` 단일 매칭으로 교정.
  - **무포크(Zero-Fork) 4GB 파일 크기 판정 (Phase 11)**: 1GB 이상 파일마다 `shell_exec("stat")`을 호출하던 병목을 `sprintf('%u', $st['size'])` 인메모리 변환(4GB 초과 블록일 때만 `stat` 폴백)으로 교체하여 폴더 조회를 **815ms -> 88ms (약 10배)**, 전체 영상 스캔을 **6.43s -> 1.07s (6배)** 가속.

### Stage 4: 반응형 미니 플레이어, 자막 내구성 및 프론트/백엔드 미세 최적화 (Phase 12 ~ 20)
- **목표**: 모바일 소형 화면부터 대형 라이브러리까지 60fps 체감 반응성과 자막·캐시 무결성 확보.
- **핵심 구현**:
  - **모바일/미니 플레이어 레이아웃 (Phase 12)**: 320~360px 안드로이드 뷰포트의 우측 버튼 잘림, 미니 창 전환/복원 시 비율 찌그러짐, 가로 모드 하단 툴바 잘림 전면 수정.
  - **자막 파서 & 캐시 무결성 (Phase 13 ~ 18)**:
    - 외부 자막 접두사 오탐(`1화` vs `10화`) 방지(`isMatchingSubtitleBase`).
    - MKV `CuePoint(0xBB)` 정식 EBML 경계 파싱, EUC-KR(CP949)/UTF-16 외부 자막 디코딩, HTML 10진/16진 엔티티 복원, SAMI 동시 대사 0초 증발 버그 해결, WebVTT 밀리초 롤오버 방지.
    - 스트림 중단/타임아웃 시 불완전 `.tmp` 캐시 오염 차단, `probe_subs` 이중 캐싱(**683ms -> 12.7ms**), 하위 폴더 수정 시 ETag 304 고착 해결(`$maxMtime` 추적 + `W/` 약한 ETag 호환).
  - **프론트/서버 고속화 (Phase 19 ~ 20)**:
    - `Intl.Collator` 싱글톤 재사용으로 1,000개 파일 정렬 **1,350ms -> 49ms (27.5배 가속)**.
    - `escapeHtml()` 무할당 패스트패스(7.3배), CSS `content-visibility: auto` 뷰포트 밖 렌더링 스킵, `_searchKey` 사전 정규화 인덱싱.
    - `getSafeFileStat()` 단일 `stat` 통합, Apache `mod_deflate` Gzip(전송량 73~83% 절감) 및 7일 브라우저 캐싱.

### Stage 5: 제로-디스크 실시간 MKV -> HLS 리먹싱 4단계 진화 (Phase 21 ~ 24)
iPhone/iPad Safari 및 Firefox는 MKV 컨테이너를 네이티브로 재생할 수 없었습니다. 이 제약을 650MHz ARM NAS에서 해결하기 위해 **4단계 아키텍처 진화**를 거쳤습니다.

1. **1세대 — `avconv` 온디맨드 MPEG-TS HLS (Phase 21)**:
   - `stream_sub.py hls_info`로 MKV 키프레임 기준 ~10초 세그먼트 가상 `.m3u8` 생성, 요청된 세그먼트만 `avconv -c:v copy -c:a copy -bsf:v h264_mp4toannexb`로 무손실 리먹싱.
2. **2세대 — iOS Safari(AVPlayer) 호환성 해결 (Phase 22)**:
   - 실기 iPhone에서 로딩 스피너가 멈추는 현상 원인 규명: 내장 자막이 있는 MKV의 `Cues`에 자막 트랙(Track 3) 큐 포인트가 섞여 비-키프레임 시점 탐색 및 `-1.8s` PTS 역전이 발생.
   - `CueTrack(0xF7) == video_track_num` 엄격 필터링, 33-bit PCR/PTS/DTS 연속 타임라인 시프트, 비-말단 세그먼트 `-t (dur - 0.010)` 중복 키프레임 제거, `-probesize 65536 -analyzeduration 0` 적용(리먹싱 3배 단축), `flock` 직렬화 및 HTTP 206 Byte-Range 응답 구현으로 **실기 iPhone 재생 최초 성공**.
3. **3세대 — 인프로세스 PHP 시프트 + 선행 프리페치 (Phase 23)**:
   - 매 세그먼트마다 Python을 띄워 TS 타임스탬프를 보정하던 `0.71s` 병목을 PHP 인프로세스 `shiftTsFileInPlace()`로 교체(**0.14s, 5배 가속**, MD5 바이트 동일).
   - `flock -n` 기반 비차단 1-세그먼트 선행 프리페치(`--prefetch`)로 세그먼트 응답을 `~2.5s -> 0.92~0.97s`로 단축.
4. **4세대 — 제로-`avconv` 순수 PHP 직접 MKV -> HLS v7 fMP4(CMAF) 엔진 (Phase 24)**:
   - *"지금보다 4배 이상 빨라야 한다"*는 요구를 달성하기 위해 `avconv`와 `python` 실행 자체를 완전히 제거하는 발상 전환.
   - MKV 내부의 H.264 `SimpleBlock` 페이로드가 MP4 AVCC와 동일하고 AAC 원시 프레임 및 `CodecPrivate`(`avcC`/`esds`)가 ISO 14496-12 CMAF와 바이트 단위 호환된다는 점에 착안해 **`fmp4_muxer.php`**를 순수 PHP로 직접 작성.
   - `CueClusterPosition`으로 직접 `fseek()` -> 제로카피 `styp + moof + mdat`(`.m4s`) 직스트리밍, `BlockGroup`, Xiph/Fixed/EBML Lacing, Header Stripping, B-프레임(`trun v1` signed CTO), 1024-샘플 그리드 AAC(`gap=+0`) 및 C-속도 `strpos` Cues 필터링(`4.17s -> 0.56s`) 구현.
   - 실기 iPhone에서 발견된 Apple CoreMedia 엄격 규격을 분석해 **Master Playlist(`hls_master`) 진입 복원**, `ftyp(iso5/iso6/mp41)`, `pasp(1:1)`, 4바이트 QuickTime `esds(80 80 80 <len>)`, 오디오 `default_sample_flags=0x02000000`, IP-only 비디오 `trun v0(0x000305)`, `Content-Type: video/mp4`로 1:1 정렬.
   - **최종 성과**: 세그먼트 서버 응답(TTFB) **`74ms ~ 129ms`(기존 대비 11~16배 가속)**, 플레이리스트 Gzip **`2.9KB`(59배 축소)**, 임시 RAM **`128KB`(190배 절감)**, 하위 프로세스 **`0개`**. 2GB 이상 파일 및 AC3/MP3/비표준 코덱 MKV는 3세대 `avconv` MPEG-TS HLS v3로 자동 무중단 폴백.

### Stage 6: iPhone Safari 전체화면·네이티브 자막 완성 및 전수 버그 감사 (Phase 25 ~ 26)
- **iPhone Safari 전체화면 & 네이티브 자막 (Phase 25)**:
  - iPhone Safari에서 표준 `requestFullscreen()` 미지원으로 전체화면 버튼이 작동하지 않던 문제를 `videoPlayer.webkitEnterFullscreen()` / `webkitExitFullscreen()` + `webkitbeginfullscreen`/`webkitendfullscreen` 이벤트 통합으로 해결.
  - iOS `AVPlayerViewController` 전체화면에서 DOM 오버레이와 `blob:` `<track>`이 무시되는 WebKit 제약을 해결하기 위해, `api.php`에 서버측 UTF-8 WebVTT 변환기(UTF-16/CP949/UTF-8, SMI/SRT/ASS/VTT, 중복 ASS 큐 제거)와 `hls_sub_m3u8` / `hls_sub_vtt` 엔드포인트를 구축하고 `hls_master`에 `#EXT-X-MEDIA:TYPE=SUBTITLES`로 삽입.
  - 실기 로그 분석을 통해 창모드에서 네이티브 트랙을 `disabled` 하면 `AVPlayer`가 자막 수신을 취소하고 전체화면 진입 후 JS 재활성화를 무시하는 특성을 파악하여, iOS에서는 시작부터 네이티브 자막을 `showing`으로 유지(`useIOSNativeCaptions()`)하고 RFC 8216 §3.5 필수 `X-TIMESTAMP-MAP=MPEGTS:0,LOCAL:00:00:00.000`을 추가하여 **iPhone 창모드·전체화면 모두 자막 완벽 표시 달성**.
- **전수 버그 감사 및 최종 검증 (Phase 26)**:
  - 전체 코드 정적/동적 감사를 통해 **실제 버그 8건**을 추가 발견하고 전량 수정·재검증 완료:
    1. PHP 5.6 비안정 `usort()`가 60자막 MKV에서 한국어 일반 자막(367큐) 대신 강제 자막(15큐)을 `DEFAULT=YES`로 뒤섞던 버그 -> `is_forced` + `orig_idx` 안정 정렬로 교정.
    2. 다중 자막 MKV의 `avconv` MPEG-TS 폴백(`probe_hls_info`)이 5초 타임아웃(HTTP 404)으로 실패하던 버그 -> C-속도 `cues_data.find()` 사전 필터 적용으로 `200 OK` 복구.
    3. 외부 자막 변환 캐시(`vtt2_ext_*.vtt`)가 RAM 캐시 정리에서 누락되어 무한 누적되던 누수 -> 공용 `pruneVttRamCache()`로 상한 관리 통합.
    4. 서버측 WebVTT 변환기의 동시 대사 SMI 잘림 및 공백 줄 포함 SRT/WebVTT `NOTE`/`STYLE` 파싱 보강.
    5. `fmp4_muxer.php`의 32비트 PHP 미지정 크기 EBML(`0x01FFFFFFFFFFFFFF`) 오버플로 방어(`fmp4ClampEnd`), `fmp4ReadExact()`, 64KB 이후 `SegmentInfo` 탐색, `esds` 길이 가드.
    6. iOS HLS 자막 전환 시 JS fetch 완료 전 즉각 트랙 전환, 로컬 자막 파일과 서버 HLS 트랙 충돌 방지, 다중 외부 자막 `extRank` 매칭.
    7. `attachVideoSource()` 비-HLS 경로의 `loadedmetadata` 리스너 누수 제거 및 중복 코드 정리.

---

## 4. 핵심 성능 개선 지표 요약 (Before vs After)

| 영역 | 초기 / 이전 방식 | 최종 최적화 상태 | 개선 폭 |
| :--- | :--- | :--- | :--- |
| 폴더 목록 조회 (고화질 13편) | 815ms (`shell_exec` stat) | **88ms** (무포크 32비트 stat) | **9.3배 가속** |
| 전체 영상 스캔 (`all=1`, 135편) | 6,431ms | **902ms** (304 재조회 636ms) | **7.1배 가속** |
| 프론트엔드 1,000개 파일 정렬 | 1,350ms (`localeCompare`) | **49ms** (`Intl.Collator`) | **27.5배 가속** |
| MKV 내장 자막 프로브 (76트랙) | 2,040ms (서브프로세스 반복) | **12.7ms** (RAM 캐시) / **0ms** (클라이언트 캐시) | **160배+ 가속** |
| MKV -> HLS 세그먼트 TTFB | 1,100 ~ 2,500ms (`avconv` + Python) | **74 ~ 129ms** (순수 PHP fMP4) | **11 ~ 16배 가속** |
| 다중 자막 MKV HLS 초기 인덱싱 | 4,170ms (Python 폴백 5s+ 타임아웃) | **560ms** (C-속도 `strpos` 필터) | **7.4배 가속** |
| HLS 미디어 플레이리스트 전송량 | 171 KB (비압축) | **2.9 KB** (Gzip) | **59배 축소** |
| HLS 임시 RAM 사용량 | ~24 MB (`avconv` TS 세그먼트) | **128 KB ~ 1.3 MB** (인덱스/VTT만 유지) | **18 ~ 190배 절감** |
| 재생 중 NAS 하위 프로세스 수 | 1~2개 (`avconv` / `python`) | **0개** (순수 PHP 제로카피 스트리밍) | **CPU 부하 최소화** |
| HDD 디스크 캐시 쓰기 | 0 B | **0 B** (Strict Zero-Disk 준수) | **HDD 수명·슬립 보호** |

---

## 5. 개발 과정에서 얻은 주요 플랫폼 교훈

1. **32-bit ARM PHP 5.6의 함정**:
   - `filesize()`는 2.14GB 초과 시 음수로 오버플로되며, `fseek()`는 2GB까지만 안전합니다.
   - EBML 미지정 크기(`0x01FFFFFFFFFFFFFF`)를 `(int)`로 캐스팅하면 int32 래핑이 발생하므로 반드시 float 비교 후 클램핑해야 합니다.
   - PHP 5.6의 `usort()`는 **비안정 정렬**이므로 동점 조건이 존재할 경우 반드시 명시적 인덱스 타이브레이커를 포함해야 합니다.
2. **Apple CoreMedia / iOS Safari HLS v7 엄격 규격**:
   - HLS v7 fMP4(`#EXT-X-MAP`)는 반드시 `BANDWIDTH`와 `CODECS`가 선언된 Master Playlist를 통해 진입해야 합니다.
   - `init.mp4`의 `ftyp`(`iso5`), `pasp(1:1)`, 4바이트 확장 길이 `esds(80 80 80 <len>)`, 오디오 `default_sample_flags=0x02000000`, `Content-Type: video/mp4` 중 하나라도 어긋나면 AVPlayer가 조용히 재생을 중단합니다.
3. **iOS `AVPlayerViewController` 전체화면 자막 메커니즘**:
   - iPhone Safari 전체화면은 DOM 계층을 벗어나 시스템 네이티브 플레이어로 전환되므로 커스텀 DOM 오버레이와 `blob:` `<track>`이 모두 차단됩니다.
   - `#EXT-X-MEDIA:TYPE=SUBTITLES` 네이티브 트랙은 창모드에서 한 번이라도 `disabled`로 끄면 전체화면 진입 후 JS 재활성화가 무시되므로 처음부터 `showing`으로 유지하고, WebVTT 헤더에 RFC 8216 `X-TIMESTAMP-MAP=MPEGTS:0,LOCAL:00:00:00.000`을 반드시 포함해야 합니다.

---

## 6. 최종 통합 검증 결과 (2026-11-23)

- **정적 문법 검사**: `php -l api.php` / `fmp4_muxer.php` 통과, `node --check app.js` 통과, `python -m py_compile stream_sub.py` 통과.
- **보안 검증**: `..`, `%2e%2e`, `%252e%252e`, `../../etc/passwd`, 비자막 확장자 접근, 음수 세그먼트 인덱스 전량 차단(HTTP 400/404/JSON 거부).
- **디코딩 무결성 (FFmpeg 9.0 라이브 HTTP HLS)**:
  - IP-only AAC MKV(`Kami no Shizuku`): `exit 0`, 경고 0건, 오류 0건.
  - B-frame HE-AAC 60자막 MKV(`Sparks of Tomorrow`): `exit 0`, 경고 0건, 오류 0건, 기본 자막 한국어 일반(367큐) 정상 매칭, MPEG-TS 폴백 `hls_seg[0]` HTTP 200 정상 응답.
- **브라우저 재생 검증**:
  - 헤드리스 Chrome 네이티브 HLS 및 `hls.light.min.js` MSE 강제 경로 모두 `1920x1080`, `readyState=4`, 120초 탐색 및 자막 동기화 성공, 콘솔 오류/예외 0건.
  - 실기 iPhone Safari WAN(`:9991`) 스트리밍 및 전체화면 네이티브 자막 정상 동작 확인.
- **NAS 리소스 건전성**: 가용 RAM `93 MB / 226 MB`, `/tmp/webplayer_sub_ram/` `1.3 MB`, 잔존 고아 프로세스 `0개`.
