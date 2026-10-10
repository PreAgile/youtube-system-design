# 결정 기록

이전 연습의 결정은 외부 백업과 보존 브랜치에 있으며 이번 문제의 선택으로 가져오지 않습니다.

[템플릿](0000-template.md)을 사용해 `0001-주제.md`부터 작성합니다. 사용자가 비교 중이면 Proposed, 선택과 이유를 명확히 결정했으면 Accepted로 기록합니다. LLM 추천만으로 승인하지 않고 이미 명확한 결정에 반복 승인을 요구하지 않습니다.

| ADR | 질문과 선택 | 상태 | 관련 FR/NFR |
|---|---|---|---|
| [0001](0001-upload-progress-and-completion.md) | 원본 전송 진행·완료 판정: 저장소 직접 업로드, 재개·완료 시 저장소 조회 (현재 완료 용어는 0009 참고) | Accepted | FR-1, FR-2, NFR-6, NFR-7 |
| [0002](0002-processing-status-check.md) | 처리 상태 확인: 폴링 (stateless, 현재 규모에서 부하 작음) | Accepted | FR-2, NFR-5 |
| [0003](0003-transcoding-executor.md) | 변환 실행 주체: 자체 작업자 + 작업 대기열 | Accepted | FR-2, NFR-5, NFR-6 |
| [0004](0004-transcoding-failure-handling.md) | 변환 실패 처리: 작업 임대 + 화질별 작업 + 재시도 상한 + 조건부 등록, 대기열은 RDB 작업 표로 시작 | Accepted | FR-2, NFR-5, NFR-6 |
| [0005](0005-playback-segments.md) | 재생 방식: 4초 세그먼트 + 매니페스트, client가 화질 판단(HTTP) | Accepted | FR-3, FR-4, NFR-2, NFR-3, NFR-4, NFR-6, NFR-8 |
| [0006](0006-global-delivery.md) | 글로벌 전달: CDN pull + 중간 캐시 + 예측 기반 선택적 push, 매니페스트 버전 경로, 재생 정보 짧은 CDN 캐시 | Accepted | NFR-2, NFR-4, NFR-6, FR-2, FR-3 |
| [0007](0007-global-upload-path.md) | 해외 업로드: 청크 병렬 업로드 + 가까운 엣지 중계, 저장 기준은 한국 Storage | Accepted | FR-1, NFR-7, NFR-5 |
| [0008](0008-object-storage-s3.md) | 객체 저장소: Amazon S3(한국 리전), 원본은 S3 Standard | Accepted | FR-1, NFR-7, NFR-2 |
| [0009](0009-all-renditions-ready.md) | 업로드 완료·재생 가능: 전체 대상 화질 준비 후 표시. 전체 영상 준비 시간 측정, p95 5분은 검증 전 후보값 | Accepted | FR-1, FR-2, FR-3, NFR-5, NFR-7 |

ADR-0009는 0001·0002의 완료 용어, 0002·0003·0004의 기준 화질 준비 p95 5분 전제, 0006의 화질 순차 공개 전제를 부분 대체합니다. 기존 ADR의 다른 결정은 유지하며 각 기록 상단에서 현재 적용 기준을 안내합니다.

상세 진행 규칙은 [AGENTS.md](../../AGENTS.md), 현재 대화 위치는 [진행 상태](../interview/progress.md)를 따릅니다. 모든 질문마다 ADR을 만들지는 않습니다. Accepted 결정이 바뀌면 새 ADR로 대체 관계를 남깁니다.
