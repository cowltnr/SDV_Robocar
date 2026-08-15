# Markdown 문서 위치 정리 실행 계획

## Status

Completed

## Baseline and fixed conditions

- Baseline: 내장·vendor·cache를 제외한 현재 checkout의 Markdown 28개와
  기존 `docs/index.md`.
- Fixed: 루트 특수 문서와 모든 기존 문서 경로를 유지한다.
- Changed: `AGENTS.md`, `docs/index.md`, `docs/automation/index.md`, harness test.
- Excluded: production Python, ROS2, 자동화 wrapper, 로컬 제외 규칙, 실험
  산출물.
- Baseline verification: sandbox 안의 `bash scripts/check.sh`는 LibreOffice
  dconf 쓰기 제한으로 Weekly Report 테스트 5개가 실패했고, 동일 명령을
  sandbox 밖에서 재실행했을 때 15개 테스트가 모두 통과했다.

## Metrics and acceptance criteria

- 중앙 색인 한 곳에서 모든 Markdown 범주와 기본 저장 위치를 확인할 수
  있다.
- `AGENTS.md`에 Markdown 저장 규칙이 있다.
- 로컬 weekly report 예외와 이유가 설명된다.
- 기존 Research tracking 변경과 기존 문서 경로가 보존된다.
- focused contract test와 전체 offline checks가 통과한다.

## Progress log

- 혼합형 문서 구조 설계 승인 완료.
- 구현 계획 작성 완료.
- 기준선 offline check 완료.
- Markdown 위치 계약 테스트가 새 규칙 부재로 실패하는 RED를 확인했다.
- `AGENTS.md`, `docs/index.md`, `docs/automation/index.md`를 최소 범위로
  갱신하고 focused test GREEN을 확인했다.
- `bash scripts/check.sh`와 `bash scripts/test_offline.sh`를 sandbox 밖에서
  실행해 각각 16개 테스트 통과를 확인했다.
- `git diff --check`가 통과했고 production tracked diff가 없음을 확인했다.

## Decision log

- 루트 특수 문서를 유지하는 혼합형 구조를 사용한다.
- `WEEKLY_REPORT_AUTOMATION.md`는 wrapper 호환성을 위해 루트에 유지한다.
- 기존 문서는 이동하지 않고 중앙 색인과 향후 기본 저장 규칙을 추가한다.

## Completion notes

- 변경 범위는 Markdown 지침·색인·자동화 문서 진입점, harness 계약 테스트,
  설계 및 실행 계획으로 제한했다.
- 루트 특수 문서와 기존 일반 문서는 이동하지 않았다.
- 기존 Research tracking hunk와 현재 untracked 회의·연구·발표 문서는
  사용자 작업으로 보존했다.
- `WEEKLY_REPORT_AUTOMATION.md`는 로컬 wrapper의 고정 경로 때문에 루트에
  유지했다.
- sandbox 내부 전체 검사는 LibreOffice dconf 경로 쓰기 제한으로 실패하므로
  LibreOffice 테스트가 포함된 전체 검증은 sandbox 밖에서 수행해야 한다.
- Live ROS2, Flask, Ollama, Isaac Sim, 실제 LIMO 또는 ROS2 topic publish는
  실행하지 않았다.
