# 대시보드 코드 계약

이 문서는 공개 소스의 함수·파일·합성 테스트만 설명한다. 실제 설치 대상, 네트워크 구성, 인증값, 운영 명령, 업무 자료와 현장 검증 기록은 포함하지 않는다.

## 화면

- 진입점은 `design_handoff_plm_dashboard/PLM Dashboard.html`이며 `executive-app.js`와 `style.css`를 사용한다. 기존 모듈은 보존된다.
- `consumeDashboardView()`는 기존 dev/ra 링크의 화면을 선택하고 주소 해시를 정리한다. 메뉴는 주소 해시를 만들지 않으며 마지막 보기 선택을 로컬 설정으로 유지한다.
- `readStaticSourceBundle()`은 runtime 경로가404일 때만 동일 origin의 집계5경로를 읽는다. 그 밖의 HTTP 오류는 기존 오류 경로로 처리한다. 모든 자료 형식·개발 자료 생성시각 정합성을 확인한 뒤 갱신한다.
- `taskOwnerEvidence()`는 담당 필드 미수록·null/빈값·문자열·확인할 형식을 구분한다. 승인 필드 미제공 표시는 원본 시스템의 값 부재를 입증하지 않는다.
- 관심 과제·필터·배치는 브라우저 로컬 상태다. 개발 선택과 전사 인허가 범위를 구분한다. 자동 자료 폴링과 원본 업무 쓰기는 하지 않는다.

## Python 읽기 서버

`deploy/windows/dashboard_server.py`는 명시적 source와 bind 설정이 필요하다. 인증정보가 포함된 origin, origin 아래의 추가 경로, 전체 인터페이스 바인딩은 거부한다. 원천 리다이렉트도 따르지 않는다.

| 입력 | 동작 |
|---|---|
| 승인된 화면 파일3개 | 정적 응답 |
| `/data/health.json`, `/data/insights.json`, `/data/weekly.json`, `/data/ra.json`, `/data/config/tracked-projects.json` | 지정 source의 같은 고정 경로를 GET |
| 미지원 경로 |404 |
| POST/PUT/PATCH/DELETE |405, source 요청 없음 |
| 원천 오류·리다이렉트 |502 |

설정 예시의 placeholder는 실제값이 아니다. `office.local.json`과 생성 자료·실행 파일·로그는 커밋 대상이 아니다. `run.ps1`은 설정을 CLI 인수로 전달하는 최소 launcher이며 설치·방화벽·실행 정책을 변경하지 않는다.

## 검증 범위

- `tests/executive-url.test.cjs`: 합성 location/history/document로 기존 링크 소비, 기본 주소, 메뉴·저장 보기 선택5개 검사.
- `tests/office-server.test.py`: loopback 합성 source로 고정5경로 원문 보존, 쓰기 격리, 미지원 경로, 리다이렉트 차단, query 격리, HEAD와 CLI 검증6개 검사.
- 기존 모듈34개 검사는 이전 구현의 회귀 검사로 그대로 유지한다.
- 로컬에서 Node39개·Python6개와 JavaScript/PowerShell 구문 검사를 통과했다. CI에서도 표준 라이브러리만 사용해 같은 검사를 실행한다.

이 합성 검사는 새 PC의 fresh clone 설치 전체 시험이나 실제 현장 접속 검증을 대신하지 않는다. 그 범위의 완료 여부는 별도 운영 기록을 따른다.