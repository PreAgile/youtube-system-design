# ADR 목록

새 결정은 [0000-template.md](0000-template.md)를 복사해 다음 번호로 만듭니다. 초안은 항상 `Proposed`로 올리고, 결정자가 7번 섹션을 직접 쓴 뒤에 `Accepted`로 바꿉니다. 이미 Accepted된 ADR은 고치지 않고, 새 ADR로 대체(Superseded)합니다.

| 번호 | 제목 | 상태 | 관련 요구사항 | 결정 예정 주차 |
|---|---|---|---|---|
| [0001](0001-record-decisions-with-adr.md) | 설계 결정을 ADR로 기록한다 | Accepted | 전체 | W1 |
| [0002](0002-backend-language-and-framework.md) | 백엔드 언어와 프레임워크 | Proposed | FR-2, FR-4, FR-5, NFR-4, NFR-5, NFR-7, NFR-8 | W1 |
| 0003 | 트랜스코딩 작업 큐 (Kafka / RabbitMQ / DB 기반 큐) | 예정 | FR-2, NFR-5 | W2 |
| 0004 | 이벤트 스트림 (조회수, 업로드 완료) | 예정 | FR-5, NFR-6 | W2 |
| [0005](0005-metadata-store.md) | 메타데이터 저장소 (MySQL / PostgreSQL) | Proposed | FR-2, FR-4, NFR-4, NFR-6, NFR-7 | W2 |
| [0006](0006-upload-path.md) | 업로드 방식 (API 서버 경유 / Presigned Multipart) | Proposed | FR-1, NFR-2, NFR-5, NFR-6, NFR-7, NFR-8 | W2 |
| 0007 | 스트리밍 포맷 (HLS / DASH, 세그먼트 길이) | 예정 | FR-3, NFR-3 | W2 |
| 0008 | 캐시 전략 (cache-aside, TTL, hot key) | 예정 | FR-4, NFR-4 | W6 |
| 0009 | 조회수 집계 방식과 중복 제거 | 예정 | FR-5, NFR-6 | W7 |
| 0010 | 상태 변경과 이벤트 발행의 원자성 (Outbox) | 예정 | FR-2, NFR-5 | W5 |
| 0011 | 샤딩 키 (video_id / channel_id) | 예정 | FR-4, NFR-7 | W8 |
| 0012 | 글로벌 리전 토폴로지 | 예정 | NFR-1, NFR-3 | W8 |
