# YouTube System Design

YouTube의 핵심 경로(업로드, 트랜스코딩, 재생, 메타데이터, 조회수)를 시스템 디자인 인터뷰 형식으로 설계하고, 백엔드를 실제로 구현해 로컬에서 측정한 수치로 설계를 검증하는 프로젝트입니다.

## 원칙

1. 모든 설계 결정은 ADR로 남긴다. ADR 없는 결정은 코드에 들어가지 않는다.
2. 모든 결정은 FR 또는 NFR 하나 이상에 연결된다. 연결되지 않으면 범위 밖으로 뺀다.
3. 숫자는 로컬에서 측정한 단위 용량에서 출발한다. DAU 1억 규모는 그 단위 용량을 환산하고, 로컬에서 증명할 수 없는 부분만 글로벌 설계로 따로 다룬다.
4. 언어, 프레임워크, 인프라 선택도 예외 없이 ADR로 근거를 남긴다.

## 범위

| 구분 | 내용 |
|---|---|
| In scope | FR-1 업로드, FR-2 트랜스코딩, FR-3 스트리밍 재생, FR-4 메타데이터 조회, FR-5 조회수 집계 |
| Stretch | 좋아요, 구독 피드, 제목 검색 |
| Out of scope | 추천, 라이브 스트리밍, 광고, Content ID, DRM, 댓글, 프론트엔드 |

범위를 자른 이유는 [docs/design/00-scope.md](docs/design/00-scope.md)에 둡니다.

## 문서 구조

```
docs/
  adr/          설계 결정 기록 (템플릿: 0000-template.md)
  design/       요구사항, API, 데이터 모델, HLD, 딥다이브
  capacity/     로컬 측정 방법, 측정 결과, DAU 1억 환산, 글로벌 설계
  interview/    발표 순서, 꼬리질문 대비
  roadmap.md    주차별 진행 계획
excalidraw/     다이어그램 원본 (.excalidraw)
```

## 결정 현황

[docs/adr/README.md](docs/adr/README.md)에서 모든 ADR의 상태를 봅니다.

## PR 리뷰

모든 변경은 PR로 올립니다. 리뷰는 코드 품질보다 결정의 논리(왜, 트레이드오프, 왜 최선인가)를 먼저 검증하며, 기준은 [docs/review-policy.md](docs/review-policy.md)입니다. CI(`scripts/check_design.py`)는 ADR 구조, 요구사항 연결, Accepted ADR 불변을 검사하고, 리뷰 봇은 같은 기준으로 논리의 빈틈을 찾습니다. 모든 지적은 반영하거나 근거를 들어 반박합니다.

| 서비스 | 설정 파일 |
|---|---|
| CodeRabbit | `.coderabbit.yaml` |
| Qodo Merge | `.pr_agent.toml` |
| Sourcery | 기본 설정 |
