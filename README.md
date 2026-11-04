# MyCloud Media Player (초경량 NAS 웹 미디어 플레이어)

WD My Cloud Gen 1 (ARMv7 650MHz, 226MB RAM, 5400RPM HDD) 전용으로 설계된 **초경량 Zero-Disk 무손실 미디어 플레이어**입니다.

---

## 📁 디렉터리 및 파일 구조

```
├── webplayer/                  # [웹서버 배포 소스 전용 폴더 - 실제 배포는 이 폴더 기준]
│   ├── index.html              # 웹플레이어 메인 HTML UI
│   ├── style.css               # 모던 다크 티타늄 UI, 반응형 그리드 & GPU 가속 스타일
│   ├── app.js                  # 프론트엔드 플레이어 코어 엔진 (자막 동기화, 디바운스, 연속재생 등)
│   ├── api.php                 # 백엔드 PHP API (디렉터리 탐색, ETag 304, 스트리밍 감독)
│   └── stream_sub.py           # 고속 MKV 자막 온디맨드 디먹서 (Matroska Cues Direct Seek)
├── apache/                     # [아파치 웹서버 설정 폴더]
│   ├── webplayer.conf          # 아파치 웹서버 최적화 설정 (Gzip, KeepAlive, 캐시 제어)
│   └── apache_webplayer.conf   # 동일 설정 파일
├── deploy_webplayer.py         # NAS 원클릭 스마트 배포 스크립트 (webplayer/, apache/ 우선 반영)
├── ssh_client.py               # NAS SSH 자동 접속 클라이언트
├── requirements.txt            # 파이썬 의존성 패키지 (paramiko==3.5.1 고정 - 아래 참고)
└── test_and_tools/             # 실서버 검증, 벤치마크 및 진단 스크립트 모음 (125개 도구)
```

> ⚠️ **NAS의 SSH가 매우 오래됐습니다** (OpenSSH 6.0p1, 2012년/Debian 7). `paramiko`가 5.x부터 이 서버가 쓰는 `ssh-rsa`/`ssh-dss` host key 방식을 아예 지원하지 않으므로, `requirements.txt`에 `paramiko==3.5.1`로 고정돼 있습니다. 이 프로젝트 밖에서 `pip install paramiko`로 최신 버전을 깔면 `ssh_client.py`/`deploy_webplayer.py`가 즉시 깨지니 주의하세요.

---

## 🔧 설치 방법

### 1. 사전 요구사항
- **로컬 PC**: Python 3.8+
- **NAS**: Apache2 + PHP, SSH 접속 가능 (이 프로젝트는 WD My Cloud Gen 1 / Debian 7 기준으로 작성됨)

### 2. 로컬 환경 설정
```bash
git clone https://github.com/kururu-SW-DEV/lightweight-media-server-player.git
cd lightweight-media-server-player

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

> ⚠️ 위 `paramiko==3.5.1` 버전 고정은 필수입니다. 최신 버전을 깔면 이 NAS의 구형 SSH(OpenSSH 6.0p1)에 아예 접속이 안 됩니다.

### 3. NAS 접속 정보 설정 (환경변수)
`ssh_client.py`는 NAS 접속 정보를 하드코딩하지 않고 환경변수로 받습니다. 배포 전에 아래 값을 설정하세요.

```bash
# Windows (cmd)
set NAS_HOST=192.168.0.7
set NAS_PORT=22
set NAS_USERNAME=root
set NAS_PASSWORD=여기에_실제_비밀번호
set NAS_OWNER=root
set NAS_GROUP=share

# macOS/Linux
export NAS_HOST=192.168.0.7
export NAS_PORT=22
export NAS_USERNAME=root
export NAS_PASSWORD=여기에_실제_비밀번호
export NAS_OWNER=root
export NAS_GROUP=share
```

`NAS_OWNER`/`NAS_GROUP`은 배포 후 `webplayer/` 폴더의 소유자·그룹을 지정합니다(윈도우 탐색기에서 직접 수정 가능하도록 권한을 여는 용도). 각각 기본값(`root`, `share`)이 있어 생략 가능합니다.

`NAS_HOST`/`NAS_PORT`/`NAS_USERNAME`은 각각 기본값(`192.168.0.7`, `22`, `root`)이 있어 생략 가능하지만, `NAS_PASSWORD`는 반드시 설정해야 합니다.

### 4. NAS 측 최초 1회 수동 설정
`deploy_webplayer.py`는 `webplayer/`, `apache/` 아래 파일들을 NAS의 `/shares/webplayer`로 복사하고 Apache를 재시작해줄 뿐, 아래 설정은 대신해주지 않습니다. NAS에 SSH로 접속해 최초 1번만 해주세요.

1. **Apache에 설정 포함**: `apache/apache_webplayer.conf`의 내용을 NAS의 Apache 메인 설정(예: `/etc/apache2/apache2.conf`)에 포함시킵니다.
   ```
   Include /shares/webplayer/apache_webplayer.conf
   ```
2. **외부 접속용 계정 생성** (선택, 포트포워딩으로 외부 노출 시 필요 — `apache_webplayer.conf`가 LAN 밖 IP에는 Basic 인증을 요구하도록 이미 구성돼 있음):
   ```bash
   htpasswd -c /etc/apache2/.htpasswd-webplayer <아이디>
   ```
3. Apache를 재시작합니다: `service apache2 restart`

> ℹ️ 정확한 include 경로/문법은 NAS의 Apache 배포판·버전에 따라 다를 수 있습니다. 이 NAS(Debian 7 기반)에서는 위 방식으로 동작을 확인했습니다.

### 5. 배포
로컬에서 코드를 수정한 후 아래 명령어를 실행하면 NAS로 즉시 배포 및 아파치가 재시작됩니다:

```bash
python deploy_webplayer.py
```

### 6. 접속 확인
브라우저에서 `http://<NAS_IP>/player` 로 접속해 플레이어 화면이 뜨는지 확인합니다.

---

## ⚡ 주요 기술적 특징
1. **Strict Zero-Disk Cache**: HDD에 자막/비디오 캐시 파일을 전혀 생성하지 않아 5400RPM HDD I/O 병목 100% 제거.
2. **0ms Matroska Cues Direct Seek**: MKV 자막을 영상 전체 스캔 없이 Cues 인덱스 오프셋(`rpos`)을 통해 0.005초 만에 다이렉트 seek.
3. **고아 프로세스 완전 박멸**: 사용자가 창을 닫거나 영상을 넘길 때 `connection_aborted()` 감지로 백그라운드 프로세스 즉각 종료 (`SIGKILL`).
4. **ETag 304 Not Modified**: 변경 없는 폴더 재진입 시 0ms 즉시 응답으로 네트워크 트래픽 100% 절감.
5. **듀얼 자막 엔진**: 창모드에서는 미려한 리치 DOM 오버레이, 전체화면에서는 네이티브 `video::cue`로 자동 동기화.
6. **최소화(미니 플레이어)**: 플로팅 플레이어 헤더의 [이전][다음][최소화][전체화면] 버튼(단축키: M)으로 창을 화면 우하단 미니 창으로 축소 — 영상은 계속 재생되며 뒤의 폴더 목록을 그대로 탐색 가능. 이전/다음 곡 전환 시에도 최소화 상태 유지.

> 🔒 **외부(포트포워딩 9991) 접속 시 로그인 필요**: `apache/apache_webplayer.conf`에 `192.168.0.0/24`(LAN)는 인증 없이 통과, 그 외 IP는 Basic 인증(`/etc/apache2/.htpasswd-webplayer`)을 요구하도록 설정. `/player`와 `/media` 둘 다 걸려있음(파일 직링크로 인증 우회 방지). 계정 관리는 NAS에서 직접: `htpasswd /etc/apache2/.htpasswd-webplayer <아이디>`.
> 같은 파일에서 **NAS 자체 관리자 화면**(`/var/www/htdocs`, 포트 9991을 그대로 포워딩하면 `/` 경로로 노출됨)도 LAN 밖에서는 아예 403으로 막아둠 — 이건 플레이어용 약한 비밀번호로 지키기엔 위험도가 달라서 로그인 프롬프트 없이 완전 차단.

> ℹ️ **다른 탭에서도 보이는 PiP는 시도 후 제거했습니다.** 브라우저 표준 PiP는 Chrome이 PiP 창 자체에 자막을 그리지 않는 [미해결 이슈](https://issues.chromium.org/issues/40581723) 때문에 자막이 전혀 안 보이고, 커스텀 오버레이까지 띄울 수 있는 Document PiP API는 HTTPS(보안 컨텍스트) 필수라 이 NAS(HTTP)에서는 애초에 동작하지 않습니다.

---

## 🩹 최근 수정 사항 (2026-09-11)

다국어(MULTi) MKV에서 한국어 자막이 안 나오거나 자막 목록 로딩이 느리다는 문제를 원인 분석 후 수정했습니다 (`webplayer/stream_sub.py`).

1. **한국어 트랙 자동 감지 속도**: 여러 개의 `kor` 태그 트랙 중 실제로 한글이 들어있는 트랙을 고르는 로직(`has_hangul_content`)이 후보 트랙마다 파이썬 서브프로세스를 통째로 새로 띄우고 그 트랙의 자막 전체를 다 뽑을 때까지 기다렸습니다. 650MHz 싱글코어에서 이게 병목이었습니다. 서브프로세스 없이 **기존 스트리밍 로직과 동일한 방식으로 파일을 한 번만 seek+read**하도록 고쳐서, 76개 트랙짜리 실측 파일 기준 `probe` 응답이 **2.04초 → 0.39초**로 줄었습니다.
2. **잘못된 자막 트랙이 나가던 버그**: 스트리밍 함수가 트랙을 고를 때 `cur_stream == target_stream_idx` **또는** `tnum == target_stream_idx` 둘 중 하나만 맞아도 매칭시켰습니다. 프론트엔드는 항상 `stream_id`(자막 목록 순번)로만 요청하는데, 트랙이 많은 파일에서는 어떤 트랙의 **MKV 내부 트랙 번호**가 우연히 그 순번과 같아져서 엉뚱한 언어 트랙이 나가는 경우가 있었습니다. `tnum` 매칭 조건을 제거해 순번으로만 매칭하도록 수정.
3. **배포 시 RAM 자막 캐시 미정리**: `/tmp/webplayer_sub_ram`(자막 RAM 캐시)이 `deploy_webplayer.py`의 정리 단계에서 빠져 있어서, 수정 전에 캐시된 잘못된 자막이 코드를 고친 뒤에도 계속 서빙됐습니다. 배포 스크립트의 정리 명령에 이 경로를 추가.
4. **특정 파일만 자막이 통째로 안 나오던 크래시**: Cue의 타임코드(`0xB3`)를 찾는 백워드 바이트 스캔이 드물게 다른 데이터의 우연한 `0xB3` 바이트를 오매칭해서, 크기값이 실제 데이터 범위를 벗어나 `IndexError`로 프로세스 자체가 죽는 경우가 있었습니다(그 트랙은 자막이 0바이트로 응답됨). 범위 체크를 추가해 오매칭 시 조용히 폴백하도록 수정 — `Sparks of Tomorrow` 10개 에피소드 전량 재검증 완료.

**리소스 실측 및 추가 최적화**: 실제 프로파일링 결과 CPU(약 0.73초)와 RAM(약 6.8MB)은 이미 매우 낮고, 체감 대기시간(약 4.6초)의 대부분은 5400RPM 하드디스크의 물리적 seek 지연이었습니다(큐가 파일 안에서 평균 2MB씩 떨어져 있고, seek 자체는 이미 역방향 없이 정렬돼 있어 하드웨어 한계에 근접). 안전하게 더 줄일 수 있는 부분만 적용: Cues 정렬 안전장치 추가, 큐 하나당 디스크에서 읽는 바이트를 4096→2048로 절반 축소. Zero-Disk 원칙(디스크 캐시 금지)은 그대로 유지 — 디스크 캐시를 허용했다면 재생 시점의 seek 지연 자체를 없앨 수 있었지만, 원칙을 지키기로 결정.

---

## 라이선스

[MIT License](LICENSE)
