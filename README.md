# PLM Dashboard

DR 개발현황과 전사 인허가를 분리해 보여 주는 읽기 전용 대시보드다. 업무 입력과 원본 수정은 OpenProject에서 관리한다. 화면은 기존 집계 JSON을 투영하며 원문에 없는 담당·사유·결정·수치를 생성하지 않는다.

## 현재 진입점

| 파일 | 역할 |
|---|---|
| `design_handoff_plm_dashboard/PLM Dashboard.html` | 개발/인허가 화면 진입점 |
| `design_handoff_plm_dashboard/executive-app.js` | 보기·관심 선택·재배치·수동 갱신 |
| `design_handoff_plm_dashboard/style.css` | 화면 스타일 |
| `deploy/windows/dashboard_server.py` | 사설 원천의 고정 집계5경로 읽기 중계 |

관심 과제·필터·접힘·배치는 브라우저 주소별 로컬 설정이다. 자동 폴링이나 OP 업무 쓰기는 하지 않는다. 실제 운영 스냅샷·인증값·사무소 환경설정은 이번 변경에 추가하지 않는다.

## 설정 launcher

설정 launcher는 `deploy/windows/run.ps1`이며 공개 문서는 코드 계약만 설명한다. 실제 운영 절차와 환경설정은 별도로 보존한다.

## 문서와 검증

- [현재 코드 계약과 합성 검증](docs/dashboard-code-contract.md)
- 현장 운영 기록·설정·작업 카드는 공개 레포에 게시하지 않고 별도 보존한다.
- 이전 구현 문서는 Git 이력의 기준 commit `54c2364`에 보존돼 있으며 현재 진입점 설명이 아니다.

```text
node --check design_handoff_plm_dashboard/executive-app.js
node --test tests/*.cjs
python tests/office-server.test.py
```

기존 모듈 테스트는 이전 구현의 회귀 검사로 보존한다. 새 계약 검사는 합성 자료와 loopback만 사용한다. 실제 자료·실명·화면 캡처는 테스트/이슈에 추가하지 않는다.