# Markdown 문서 위치 정리 설계

## 목적

프로젝트의 Markdown 문서를 한 곳에서 찾을 수 있게 하고, Codex가 새
Markdown 문서를 만들 때 문서 종류에 맞는 기본 위치를 선택하도록 한다.
루트 특수 문서의 자동 발견 기능과 기존 자동화 경로는 유지한다.

## 확인된 현재 상태

- 프로젝트 소유 Markdown은 내장 `IsaacSim/`, `.git/`, 캐시를 제외하고
  28개다.
- `README.md`, `AGENTS.md`, `ARCHITECTURE.md`는 저장소 루트에 있다.
- 일반 프로젝트 문서는 대부분 `docs/` 아래에 이미 분류되어 있다.
- 설계 문서와 구현 계획은 각각 `docs/superpowers/specs/`와
  `docs/superpowers/plans/`에 저장되어 있다.
- `docs/index.md`는 핵심 문서, 실행 계획, 연구 추적 문서를 연결하지만
  Superpowers 문서와 로컬 자동화 문서 위치는 설명하지 않는다.
- 루트의 로컬 전용 `WEEKLY_REPORT_AUTOMATION.md`는
  `scripts/run_weekly_report.sh`가 고정 경로로 읽고, `.git/info/exclude`도
  루트 경로만 제외한다.

## 선택한 구조

혼합형 구조를 사용한다.

```text
README.md
AGENTS.md
ARCHITECTURE.md
WEEKLY_REPORT_AUTOMATION.md  # 로컬 자동화 예외
docs/
├── index.md
├── research-direction.md
├── automation/
├── experiments/
├── meetings/
├── safety/
├── exec-plans/
│   ├── active/
│   └── completed/
└── superpowers/
    ├── specs/
    └── plans/
```

`README.md`, `AGENTS.md`, `ARCHITECTURE.md`는 자동 발견성과 기존 참조를
위해 루트에 유지한다. 기존 일반 문서는 현재의 분야별 `docs/` 위치를
유지한다. 이번 작업에서 문서를 일괄 이동하지 않는다.

`WEEKLY_REPORT_AUTOMATION.md`는 일반적으로 `docs/automation/`에 둘 성격의
문서지만, 현재 로컬 wrapper가 루트 경로를 직접 소비한다. 따라서 이번
작업에서는 루트의 로컬 전용 예외로 유지하고 `docs/index.md`에 위치와
이유를 기록한다. 앞으로 새로 만드는 일반 자동화 운영 문서는
`docs/automation/`에 저장한다.

## 중앙 색인

`docs/index.md`를 Codex와 사용자가 Markdown 위치를 찾는 중앙 진입점으로
사용한다. 다음 범주를 명시한다.

- 루트 특수 문서
- 연구 추적 문서
- 회의 문서
- 안전 문서
- 실험 문서
- 실행 계획
- Superpowers 설계 및 구현 계획
- 자동화 운영 문서
- 로컬 전용 예외 문서

각 항목에는 실제 경로, 용도, 새 문서의 기본 저장 위치를 함께 적는다.
디렉터리 링크는 현재 존재하는 경로만 사용한다. 비어 있는
`docs/automation/`은 새 운영 문서의 기준 위치를 보여 주기 위해
`docs/automation/index.md`로 생성한다.

## Codex 저장 규칙

`AGENTS.md`에 다음 기본 규칙을 추가한다.

| 문서 종류 | 기본 위치 |
|---|---|
| 사용자용 프로젝트 개요 | `README.md` |
| 저장소 전체 Codex 지침 | `AGENTS.md` |
| 최상위 아키텍처 | `ARCHITECTURE.md` |
| 일반 프로젝트 문서 | `docs/`의 가장 가까운 분야별 하위 디렉터리 |
| 회의록 | `docs/meetings/` |
| 연구 방향 | `docs/research-direction.md` |
| 안전 문서 | `docs/safety/` |
| 실험 프로토콜·평가 문서 | `docs/experiments/` |
| 활성 실행 계획 | `docs/exec-plans/active/` |
| 완료 실행 계획 | `docs/exec-plans/completed/` |
| Superpowers 설계 | `docs/superpowers/specs/` |
| Superpowers 구현 계획 | `docs/superpowers/plans/` |
| 자동화 운영 문서 | `docs/automation/` |
| 실험 결과와 실행 메타데이터 | Markdown이 아닌 경우도 포함하여 `artifacts/runs/` |

사용자가 경로를 명시하면 사용자의 경로를 우선한다. 기존 문서와 같은
주제라면 새 파일을 임의로 만들기보다 기존 문서를 갱신한다. 새 범주가
필요하면 먼저 `docs/index.md`에 목적과 위치를 등록한다.

## 변경 범위

수정 또는 생성할 파일은 다음으로 제한한다.

- `AGENTS.md`: Markdown 저장 위치 규칙 추가
- `docs/index.md`: 전체 문서 지도와 기본 저장 위치 보강
- `docs/automation/index.md`: 자동화 운영 문서의 기준 위치 설명
- `tests/unit/test_harness_contract.py`: 중앙 색인과 저장 규칙 계약 검사
- 이 설계 이후 작성할 구현 계획 문서

기존 production Python, ROS2 파일, 자동화 wrapper, 로컬 제외 규칙,
실험 산출물은 변경하지 않는다.

## 링크와 기존 변경 보존

- 루트 특수 문서와 기존 일반 문서를 이동하지 않으므로 기존 링크는
  유지된다.
- 현재 `docs/index.md`에 미커밋 상태로 추가된 Research tracking 절은
  사용자 작업으로 간주하여 그대로 보존하고 그 위에 문서 지도를
  확장한다.
- 기존 `docs/superpowers/`, `docs/meetings/`, `docs/research-direction.md`의
  내용은 수정하지 않고 색인에서만 연결한다.

## 검증

1. 새 계약 테스트를 먼저 추가하고 기존 색인·규칙에서 실패하는지
   확인한다.
2. 문서와 색인을 최소 변경해 테스트를 통과시킨다.
3. `bash scripts/check.sh`를 실행한다.
4. `bash scripts/test_offline.sh`를 실행한다.
5. `git diff --check`와 최종 diff로 production 파일 미변경, 기존 사용자
   변경 보존, 의도한 Markdown 문서만 변경됐는지 확인한다.

라이브 ROS2, Flask, Ollama, Isaac Sim, 실제 LIMO 또는 ROS2 topic publish는
필요하지 않으며 실행하지 않는다.

## 완료 기준

- `docs/index.md` 하나에서 모든 프로젝트 Markdown 범주와 저장 위치를
  확인할 수 있다.
- Codex가 새 Markdown 문서 종류별 기본 저장 위치를 `AGENTS.md`에서
  확인할 수 있다.
- 루트 특수 문서의 위치와 역할이 명시된다.
- 로컬 전용 `WEEKLY_REPORT_AUTOMATION.md` 예외가 이유와 함께 기록된다.
- 기존 링크와 기존 미커밋 문서 변경이 보존된다.
- 관련 offline checks가 통과한다.
