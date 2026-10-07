# 결정 기록

이전 연습의 결정은 외부 백업과 보존 브랜치에 있으며 이번 문제의 선택으로 가져오지 않습니다.

[템플릿](0000-template.md)을 사용해 `0001-주제.md`부터 작성합니다. 사용자가 비교 중이면 Proposed, 선택과 이유를 명확히 결정했으면 Accepted로 기록합니다. LLM 추천만으로 승인하지 않고 이미 명확한 결정에 반복 승인을 요구하지 않습니다.

| ADR | 질문과 선택 | 상태 | 관련 FR/NFR |
|---|---|---|---|
| [0001](0001-upload-progress-and-completion.md) | 업로드 진행 기준과 완료 판정: 저장소 직접 업로드, 재개·완료 시 저장소 조회 | Accepted | FR-1, FR-2, NFR-6, NFR-7 |
| [0002](0002-processing-status-check.md) | 처리 상태 확인: 폴링 (stateless, 현재 규모에서 부하 작음) | Accepted | FR-2, NFR-5 |
| [0003](0003-transcoding-executor.md) | 변환 실행 주체: 자체 작업자 + 작업 대기열 | Accepted | FR-2, NFR-5, NFR-6 |
| [0004](0004-transcoding-failure-handling.md) | 변환 실패 처리: 작업 임대 + 화질별 작업 + 재시도 상한 + 조건부 등록, 대기열은 RDB 작업 표로 시작 | Accepted | FR-2, NFR-5, NFR-6 |
| [0005](0005-playback-segments.md) | 재생 방식: 4초 세그먼트 + 매니페스트, client가 화질 판단(HTTP) | Accepted | FR-3, FR-4, NFR-2, NFR-3, NFR-4, NFR-6, NFR-8 |
| [0006](0006-global-delivery.md) | 글로벌 전달: CDN pull + 중간 캐시 + 예측 기반 선택적 push, 매니페스트 버전 경로, 재생 정보 짧은 CDN 캐시 | Accepted | NFR-2, NFR-4, NFR-6, FR-2, FR-3 |

상세 진행 규칙은 [AGENTS.md](../../AGENTS.md), 현재 대화 위치는 [진행 상태](../interview/progress.md)를 따릅니다. 모든 질문마다 ADR을 만들지는 않습니다. Accepted 결정이 바뀌면 새 ADR로 대체 관계를 남깁니다.
