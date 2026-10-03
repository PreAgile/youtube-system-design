# 데이터 모델: 영상의 상태를 어디에 두고 어떻게 읽고 쓰나

영상 하나는 바이트(원본, 세그먼트, 재생 목록)와 상태(제목, 공개 범위, 처리 단계, 해상도별 준비 여부)로 나뉩니다. 바이트는 객체 스토리지에, 상태는 관계형 DB에 둡니다. 이 문서는 상태 쪽을 다룹니다. 어떤 DB를 쓰는지는 ADR-0005에서 정합니다.

요구사항 ID는 [00-scope.md](00-scope.md)를 따릅니다.

## 1. 무엇을 어디에 두나

| 데이터 | 저장소 | 이유 |
|---|---|---|
| 원본, 세그먼트(`.ts`), 재생 목록(`.m3u8`) | 객체 스토리지 | 바이트. 크고, 한 번 쓰면 바뀌지 않고, CDN이 그대로 캐시함 |
| 영상 메타데이터와 처리 상태 | RDB | 상태 전이를 조건부 갱신으로 막아야 하고, 채널별 목록 같은 범위 조회가 필요함 |
| 해상도별 변환 상태 | RDB | 워커 재시도에도 한 줄만 생겨야 함(NFR-7) |
| 업로드 세션 | RDB | 완료 요청의 멱등 판단 기준(업로드 방식 ADR) |
| 비공개 영상의 시청 권한 | RDB | 재생 전에 검사해야 하는 관계(FR-3) |
| 조회수 | 별도 집계 경로 | 핫 영상 하나에 초당 약 170건. 영상 행을 조회마다 갱신하지 않음(ADR-0009) |
| 자주 읽는 메타데이터 사본 | 캐시 | 메타데이터 읽기 피크 초당 약 6만 9,000건(ADR-0008) |

## 2. 엔티티

### channels

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `channel_id` | BIGINT, PK | 시간순으로 증가하는 ID(3장) |
| `owner_user_id` | BIGINT | 채널 소유자 |
| `name` | VARCHAR | 채널 이름 |
| `created_at` | TIMESTAMP | |

### videos

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `video_id` | BIGINT, PK | 내부 ID. 시간순으로 증가. 외부에 노출하지 않음 |
| `public_id` | CHAR(11), UNIQUE | 주소와 API에 쓰는 무작위 ID(3장) |
| `channel_id` | BIGINT | 소속 채널 |
| `title`, `description` | VARCHAR, TEXT | FR-4 |
| `visibility` | ENUM(`public`, `unlisted`, `private`) | 접근 정책(6장) |
| `status` | ENUM(4장 상태) | 처리 단계 |
| `published_at` | TIMESTAMP, NULL | 처음 재생 가능해진 시각. 불변식: NULL이 아니면 한 번 이상 PLAYABLE이 됐고, 다시 NULL로 돌아가지 않음 |
| `duration_ms` | INT, NULL | 워커가 `ffprobe`로 채움 |
| `version` | INT | 행이 바뀔 때마다 1 증가(상태 전이 포함). 메타데이터 수정의 낙관적 잠금과 캐시의 옛 값 판별(7-4)에 씀 |
| `created_at`, `updated_at` | TIMESTAMP | |

인덱스:

- `(channel_id, visibility, published_at, video_id)`: 채널별 공개 영상 최신순 목록(5장 R2)
- `public_id` 유일 인덱스: 주소로 들어온 조회

### upload_sessions

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `video_id` | BIGINT, PK | 영상 하나에 업로드 세션 하나 |
| `storage_upload_id` | VARCHAR | 스토리지의 멀티파트 `uploadId` |
| `object_key` | VARCHAR | `originals/{video_id}` |
| `declared_size`, `part_size` | BIGINT | 완료 시 파트 합계 검증 |
| `status` | ENUM(`OPEN`, `COMPLETED`, `ABORTED`) | 완료 멱등의 기준(4-2) |
| `completed_size` | BIGINT, NULL | 완료 시 확인한 실제 크기. 재시도에 같은 결과를 돌려주는 근거 |
| `created_at`, `expires_at` | TIMESTAMP | 미완료 업로드 정리 기한 |

### video_renditions

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `video_id`, `resolution` | BIGINT, ENUM(`360p`, `480p`, `720p`, `1080p`) | 복합 PK. 해상도당 한 줄 |
| `status` | ENUM(`PENDING`, `PROCESSING`, `READY`, `FAILED`) | |
| `attempt` | INT | 시도 번호. 재시도마다 1 증가. 출력 경로(`videos/{id}/{res}/a{attempt}/`)에 넣어 시도끼리 섞이지 않게 함 |
| `failure_count` | INT | 자동 재시도 판단 기준(4-3) |
| `playlist_key` | VARCHAR, NULL | READY일 때 해상도별 재생 목록 위치 |
| `bandwidth` | INT, NULL | 마스터 재생 목록의 `BANDWIDTH` 값 |
| `updated_at` | TIMESTAMP | |

`(video_id, resolution)`이 PK이므로, 워커가 같은 작업을 두 번 처리해도 줄이 두 개 생기지 않습니다.

### video_grants

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `video_id`, `user_id` | BIGINT | 복합 PK. 비공개 영상을 볼 수 있도록 공유받은 사용자 |
| `granted_at` | TIMESTAMP | |

## 3. ID: 내부 ID와 공개 ID를 나눈다

**내부 ID(`video_id`, `channel_id`)는 시간순으로 증가하는 BIGINT**입니다(설계 가정).

- 새 행이 항상 인덱스 끝에 붙어, 삽입이 페이지 여기저기를 쪼개지 않습니다. 특히 PK 순서로 행을 저장하는 DB(클러스터형 인덱스)에서 차이가 큽니다.
- 보조 인덱스마다 PK가 함께 저장되는 DB에서는 PK가 짧을수록 인덱스가 작습니다. BIGINT는 8바이트, UUID 문자열은 36바이트입니다.
- 샤딩(ADR-0011) 뒤에도 DB 시퀀스 없이 애플리케이션이 만들 수 있어야 하므로, 시각과 노드 번호, 순번을 조합하는 방식(Snowflake 계열)을 씁니다.

**그러나 시간순 ID는 추측할 수 있습니다.** 어떤 영상의 ID를 알면 그 주변 번호를 차례로 넣어 다른 영상을 찾을 수 있습니다. 일부공개(`unlisted`)는 "링크를 아는 사람만 본다"는 정책이라([YouTube 고객센터](https://support.google.com/youtube/answer/157177)), 링크가 추측 가능하면 정책이 무너집니다. 그래서 **주소와 API에는 무작위 `public_id`만 씁니다.** 64비트 난수를 URL에 안전한 문자 11자로 표현하고, 충돌하면 다시 뽑습니다. 내부 ID는 DB와 서비스 사이에서만 씁니다.

## 4. 상태 머신

### 4-1. 영상 상태

```
UPLOADING ──완료──▶ UPLOADED ──첫 작업 시작──▶ PROCESSING ──첫 해상도 READY──▶ PLAYABLE ──전 해상도 READY──▶ READY
    │                                             │
    └── 세션 만료, 업로드 소실 ──▶ ABORTED           └── 모든 해상도가 FAILED ──▶ FAILED ──재처리──▶ PROCESSING
```

| 상태 | 뜻 | 크리에이터에게 | 시청자에게 |
|---|---|---|---|
| UPLOADING | 파트 전송 중 | 업로드 중 | 안 보임 |
| UPLOADED | 원본 확정, 작업 대기 | 처리 대기 | 안 보임 |
| PROCESSING | 인코딩 중, 준비된 해상도 없음 | 처리 중 | 안 보임 |
| PLAYABLE | 하나 이상의 해상도 준비 | 해상도별 진행 상황, 실패한 해상도 표시 | 준비된 해상도로 재생 |
| READY | 전 해상도 준비 | 완료 | 전 해상도 |
| FAILED | 준비된 해상도 없이 모두 실패 | 실패, 재처리 가능(NFR-5) | 안 보임 |
| ABORTED | 업로드가 완료되지 않고 끝남(세션 만료, 스토리지의 업로드 소실). 원본이 없어 재처리할 수 없는 끝 상태 | 업로드 실패, 다시 업로드 필요 | 안 보임 |

### 4-2. 업로드 완료: 세션과 영상을 한 트랜잭션으로

스토리지의 멀티파트 완료는 DB 트랜잭션 밖에서 일어나는 외부 호출입니다. 그래서 순서와 경계를 이렇게 둡니다.

1. `upload_sessions.status`를 읽습니다. `COMPLETED`면 스토리지를 부르지 않고 저장된 결과(`completed_size`, 영상 상태)를 그대로 돌려줍니다.
2. `OPEN`이면 파트 목록과 합계를 검증하고 스토리지에 완료를 요청합니다. 검증 단계의 파트 목록 조회든 완료 요청이든, 업로드 세션이 이미 없다는 오류나 같은 키에 객체가 이미 있다는 조건부 쓰기 실패(`412`)가 오면(앞선 요청이 스토리지 완료까지 하고 DB 반영 전에 죽은 경우) 객체의 크기와 체크섬을 확인하고 3으로 갑니다. 객체가 없으면 세션과 영상을 `ABORTED`로 바꿉니다. 판단 규칙은 [ADR-0006](../adr/0006-upload-path.md)의 완료의 멱등을 따릅니다.
3. 한 트랜잭션에서 아래를 모두 바꿉니다.

```sql
UPDATE upload_sessions SET status = 'COMPLETED', completed_size = ?
 WHERE video_id = ? AND status = 'OPEN';
UPDATE videos SET status = 'UPLOADED', updated_at = NOW()
 WHERE video_id = ? AND status = 'UPLOADING';
-- 트랜스코딩 작업 발행 기록도 같은 트랜잭션에 넣는다 (ADR-0010)
```

첫 UPDATE의 영향 행이 0이면 트랜잭션을 되돌리고 세션을 다시 읽습니다. `COMPLETED`면 다른 요청이 먼저 완료한 것이므로 1의 결과를 돌려줍니다. `ABORTED`면 업로드가 중단된 것이므로 클라이언트에 새 업로드를 요청합니다. 아래 만료 정리의 순서 때문에, 스토리지 완료에 성공한 요청이 `ABORTED`를 만나는 경우는 생기지 않습니다. 생기면 불변식 위반으로 기록합니다.

#### 만료 정리: 스토리지의 결과를 먼저 확정하고 DB가 따른다

완료 요청은 세션을 `OPEN`으로 읽은 뒤 트랜잭션 밖에서 스토리지 완료를 부릅니다. 그 사이 만료 정리가 DB를 먼저 `ABORTED`로 바꾸면, 스토리지에는 완성된 원본이 있는데 세션은 `ABORTED`, 영상은 갈 곳이 없는 상태가 됩니다. 그래서 만료 정리는 **DB보다 스토리지를 먼저 끝냅니다.**

1. 대상은 `status = 'OPEN' AND expires_at < NOW()`인 세션입니다. `COMPLETED` 세션은 절대 건드리지 않습니다.
2. `AbortMultipartUpload`로 스토리지의 업로드를 중단합니다. 성공하든 업로드가 없다는 오류가 오든 3으로 갑니다.
3. `HeadObject`로 `originals/{video_id}`가 있는지 봅니다.
   - **없으면:** 이 `uploadId`는 중단됐고, 같은 키에 쓰는 다른 업로드도 없으므로(ADR-0006 복구 경로) 원본이 나중에 생길 수 없습니다. 한 트랜잭션에서 세션을 `ABORTED`로, 영상을 `UPLOADING`에서 `ABORTED`로 바꿉니다(각각 `WHERE status = 'OPEN'`, `WHERE status = 'UPLOADING'` 조건부).
   - **있으면:** 완료 요청이 중단보다 먼저 스토리지 완료에 성공한 것입니다. DB는 바꾸지 않고 `OPEN`으로 둡니다. 그 완료 요청이 3단계 트랜잭션을 마치거나, 요청이 죽었으면 클라이언트의 재시도가 복구 경로로 마칩니다. 정리 작업은 이 세션을 "완료 반영 대기"로 기록하고, 다음 주기에도 같은 판단을 반복합니다.
4. `storage_upload_id`가 비어 있는 세션(업로드 시작 도중 API가 죽은 경우)은 중단할 업로드도, 완료할 수 있는 요청도 없으므로 2, 3 없이 DB만 바꾸고, 스토리지 쪽은 lifecycle 규칙이 지웁니다. 스토리지의 lifecycle 규칙(`AbortIncompleteMultipartUpload`)은 이미 완료된 업로드에는 영향이 없습니다([S3 문서](https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpu-abort-incomplete-mpu-lifecycle-config.html)).

이 순서는 **같은 `uploadId`에 대한 완료와 중단 중 하나만 성공한다**는 스토리지의 성질에 기댑니다. 중단된 업로드는 완료할 수 없고, 완료된 업로드는 중단할 대상이 없습니다. 완료와 중단이 거의 동시에 올 때도 둘 중 하나만 이기는지는 W4에서 MinIO로 두 호출을 동시에 반복해 확인합니다. 둘 다 성공하는 경우가 한 번이라도 나오면 이 순서는 성립하지 않고, 세션 행을 선점하는 방식으로 바꿔야 합니다.

**대안: 완료 요청이 세션을 선점한다.** 완료 요청이 `OPEN → COMPLETING`으로 선점하면 정리 작업이 그 세션을 건너뛸 수 있습니다. 하지만 ADR-0006이 이 상태를 두지 않기로 한 이유(선점한 요청이 죽으면 그 선점을 풀 만료 규칙이 또 필요함)가 그대로 남습니다. DB 행 잠금을 스토리지 호출 동안 잡는 방법도 있지만, 큰 객체의 완료 호출은 오래 걸릴 수 있어 커넥션과 잠금을 그만큼 묶어 둡니다. 위 순서가 치르는 비용은 만료된 세션마다 스토리지 호출 2번이고, 만료되는 세션은 업로드의 일부(ADR-0006 4-5 가정 5%, 초당 1건 미만)라 작습니다.

이 순서는 ADR-0006의 "완료의 멱등" 규칙을 보완하는 결정입니다. 아직 ADR이 없으므로 이 문서의 제안으로 두고, ADR-0006을 Accepted로 결정할 때 그 ADR에 함께 넣어 확정합니다.

### 4-3. 해상도별 상태와 영상 상태의 대응

해상도 행의 종단 상태(READY, FAILED) 조합으로 영상 상태를 정합니다.

| 해상도 행의 조합 | 영상 상태 |
|---|---|
| 아직 종단 상태가 없음 | PROCESSING |
| READY 1개 이상, 나머지는 진행 중이거나 FAILED | PLAYABLE (실패한 해상도가 있어도 유지) |
| 전부 READY | READY |
| 전부 FAILED | FAILED |

**자동 재시도:** 해상도 작업이 실패하면 `failure_count`를 올리고, 3회 미만이면 `attempt`를 올려 `PENDING`으로 되돌립니다. 3회째 실패하면 `FAILED`로 둡니다(횟수는 가정).

**전이 SQL:** 모두 조건부 갱신이고, 해상도 행 갱신과 영상 상태 갱신을 한 트랜잭션에 넣습니다. **각 트랜잭션의 첫 문장(해상도 행 갱신)이 정확히 1행을 바꿨을 때만 영상 상태를 갱신합니다.** 0행이면 그 자리에서 트랜잭션을 되돌리고 결과를 버립니다. 아래 SQL에서는 줄였지만, `videos`를 바꾸는 모든 UPDATE는 `version = version + 1`을 함께 씁니다(7-4).

```sql
-- 워커가 작업을 잡음
BEGIN;
UPDATE video_renditions SET status = 'PROCESSING'
 WHERE video_id = ? AND resolution = ? AND status = 'PENDING' AND attempt = ?;
-- 영향 행이 1이 아니면 ROLLBACK. 다른 워커가 잡았거나 attempt가 바뀐 작업이므로 처리하지 않음
UPDATE videos SET status = 'PROCESSING'
 WHERE video_id = ? AND status = 'UPLOADED';
COMMIT;

-- 해상도 하나 성공
BEGIN;
UPDATE video_renditions SET status = 'READY', playlist_key = ?, bandwidth = ?
 WHERE video_id = ? AND resolution = ? AND status = 'PROCESSING' AND attempt = ?;
-- 영향 행이 1이 아니면 ROLLBACK. 옛 시도의 결과이므로 버림
UPDATE videos SET status = 'PLAYABLE', published_at = COALESCE(published_at, NOW())
 WHERE video_id = ? AND status = 'PROCESSING';
UPDATE videos SET status = 'READY'
 WHERE video_id = ? AND status = 'PLAYABLE'
   AND NOT EXISTS (SELECT 1 FROM video_renditions
                    WHERE video_id = ? AND status <> 'READY');
COMMIT;

-- 해상도 하나가 재시도 한도를 넘겨 실패
BEGIN;
UPDATE video_renditions SET status = 'FAILED', failure_count = failure_count + 1
 WHERE video_id = ? AND resolution = ? AND status = 'PROCESSING' AND attempt = ?;
-- 영향 행이 1이 아니면 ROLLBACK
UPDATE videos SET status = 'FAILED'
 WHERE video_id = ? AND status = 'PROCESSING'
   AND NOT EXISTS (SELECT 1 FROM video_renditions
                    WHERE video_id = ? AND status <> 'FAILED');
COMMIT;
```

`attempt` 조건 덕분에, 임대가 만료된 옛 워커가 늦게 끝나도 새 시도의 행을 바꾸지 못합니다. 영상 상태 갱신은 그 조건을 통과한 뒤에만 실행되므로, 옛 워커가 해상도 행은 못 바꾸고 영상만 `PLAYABLE`로 올려 `published_at`을 찍는 일도 없습니다. `published_at`은 2장의 불변식상 되돌릴 수 없으므로, 이 순서를 어기면 준비된 해상도가 없는 영상이 목록(R2)에 영구히 나옵니다.

### 4-4. 재처리 (NFR-5)

크리에이터나 운영자가 재처리를 요청하면 한 트랜잭션에서 실패한 해상도만 다시 엽니다.

```sql
UPDATE video_renditions SET status = 'PENDING', attempt = attempt + 1, failure_count = 0
 WHERE video_id = ? AND status = 'FAILED';
UPDATE videos SET status = 'PROCESSING'
 WHERE video_id = ? AND status = 'FAILED';
-- PLAYABLE에서 실패한 해상도만 재처리하면 영상은 PLAYABLE을 유지한다
```

`attempt`가 올라가므로 이전 시도의 워커가 아직 돌고 있어도 그 결과는 반영되지 않고, 출력 경로도 달라 파일이 섞이지 않습니다. 원본은 `originals/{video_id}`에 그대로 있으므로 언제든 다시 처리할 수 있습니다. 상태 전이와 작업 발행을 원자적으로 묶는 방법은 ADR-0010에서 다룹니다.

## 5. 접근 패턴

| # | 요청 | 피크 규모 | 조회 방법 | 읽는 곳 |
|---|---|---|---|---|
| R1 | 영상 상세 | 메타데이터 읽기 약 6만 9,000건/초의 대부분 | `public_id` 유일 인덱스 조회 | 캐시 → 복제본, 응답 전 권한 검사(6장) |
| R2 | 채널 공개 영상 최신순 목록 (FR-4) | R1보다 적음 | `(channel_id, visibility, published_at, video_id)` 인덱스 역순 범위 조회, 커서 페이지 | 캐시 → 복제본 |
| R3 | 재생 정보 (준비된 해상도, 재생 목록 위치) | 재생 시작 약 1만 7,400건/초 | `video_renditions` PK 범위 조회 | 캐시 → 복제본, 응답 전 권한 검사 |
| R4 | 크리에이터가 보는 자기 영상 상태 | 작음 | R1과 같음 | **캐시를 거치지 않고** 자기 쓰기를 반영한 곳(7-3) |
| W1 | 업로드 시작 (videos + upload_sessions 삽입) | 약 17건/초 | 한 트랜잭션 | 프라이머리 |
| W2 | 상태 전이, 해상도별 갱신 | 영상당 약 10건, 약 170건/초 | 4장 조건부 갱신 | 프라이머리 |
| W3 | 메타데이터 수정 | 작음 | `version` 조건부 갱신 | 프라이머리 |

R2는 오프셋 페이지(`LIMIT 20 OFFSET 10000`)를 쓰지 않습니다. 뒤로 갈수록 앞의 행을 모두 읽고 버려야 하기 때문입니다. 마지막으로 본 `(published_at, video_id)`를 커서로 넘겨 그 뒤부터 읽습니다.

```sql
SELECT public_id, title, published_at FROM videos
 WHERE channel_id = ? AND visibility = 'public'
   AND published_at IS NOT NULL
   AND (published_at, video_id) < (?, ?)
 ORDER BY published_at DESC, video_id DESC
 LIMIT 20;
```

인덱스 앞 두 컬럼(`channel_id`, `visibility`)은 같음 조건이라, 인덱스에서 그 채널의 공개 영상 구간으로 바로 들어가 최신순으로 20개만 읽고 멈춥니다. 재생 가능 여부는 `status IN (...)` 대신 `published_at IS NOT NULL`로 거릅니다. 2장의 불변식(한 번 재생 가능해지면 NULL로 돌아가지 않음) 때문에 두 조건이 같고, 이쪽이 인덱스 범위 안에서 처리됩니다. 비공개나 처리 중인 영상이 많은 채널이어도 그 행을 훑지 않습니다. 실제 실행 계획은 W3에서 ADR-0005가 고른 DB로 확인합니다.

## 6. 접근 권한 (FR-3)

### 6-1. 공개 범위별 정책

| `visibility` | 볼 수 있는 사람 | 목록(R2)에 나오나 |
|---|---|---|
| `public` | 누구나 | 예 |
| `unlisted` | `public_id`가 든 링크를 아는 사람 누구나. 로그인 불필요 | 아니오 |
| `private` | 채널 소유자와 `video_grants`에 있는 사용자 | 아니오 |

YouTube도 비공개 영상은 "본인과 본인이 선택한 사람", 일부공개는 "링크가 있는 누구나"로 정의합니다([YouTube 고객센터](https://support.google.com/youtube/answer/157177)). 일부공개 링크를 회전하거나 폐기하는 기능은 범위 밖이며, 필요하면 `public_id`를 새로 발급하는 것으로 대신합니다.

### 6-2. 캐시가 있어도 권한은 매번 검사한다

캐시에는 **사용자와 무관한 영상 레코드**(공개 범위, 채널 소유자 포함)만 둡니다. "이 사용자에게 보여 줄 응답"은 캐시하지 않습니다.

```
요청 → 캐시(또는 DB)에서 영상 레코드 조회
     → 권한 검사: public/unlisted면 통과. private면 요청자가 소유자이거나 video_grants에 있는지 확인
     → 통과하면 응답, 아니면 404 (존재 여부도 숨김)
```

- 권한 검사는 캐시 조회 **뒤, 응답 전**에 API가 합니다. 캐시가 권한 판단을 대신하지 않습니다.
- `video_grants` 조회는 비공개 영상에서만 일어나므로 전체 부하에서 작습니다.
- 재생(R3)의 세그먼트는 CDN이 주므로 API가 매번 검사할 수 없습니다. 그래서 재생 정보 API가 권한을 확인한 뒤에만 짧게 유효한 서명 URL을 줍니다(ADR-0007, ADR-0008).
- 공개 범위를 `public`에서 `private`로 바꾸면 캐시 항목을 버전 표식으로 바꿉니다(7-4). 그 뒤로는 복제본이 아직 옛 `public` 행을 주더라도 캐시에 다시 들어가지 않고, 권한 검사도 그 옛 행으로 하지 않습니다. 이미 발급된 서명 URL은 만료 시각까지 유효하므로, 이 시간이 권한 변경의 최대 지연입니다.

## 7. 읽기와 쓰기를 나누는 방법

### 7-1. 숫자로 본 모양

- 읽기: 메타데이터 피크 약 6만 9,000건/초. 캐시 히트율을 95%로 가정하면 DB에 닿는 것은 약 3,500건/초입니다.
- 쓰기: 약 170건/초. 요청 수로 읽기의 약 400분의 1입니다.
- 크기(가정): 영상 한 행을 인덱스 포함 약 2KB, 해상도 행 4개를 합쳐 영상당 약 3KB로 두면, 하루 50만 편은 약 1.5GB, 1년 약 550GB, 5년 약 2.7TB입니다.

### 7-2. 단계별 구성

| 단계 | 구성 | 다음 단계로 넘어가는 신호 |
|---|---|---|
| 1 | 프라이머리 1대 + 캐시 | 캐시 미스 읽기가 프라이머리 CPU나 버퍼 풀을 채움 |
| 2 | 프라이머리 1대(쓰기) + 읽기 복제본 N대 + 캐시 | 데이터가 한 대의 메모리와 디스크를 넘어, 백업, 복구, 스키마 변경, 복제본 추가에 걸리는 시간이 운영 한계를 넘음 |
| 3 | 샤딩(ADR-0011) | |

쓰기 약 170건/초는 프라이머리 한 대로 충분합니다. 그래서 이 시스템이 샤딩하는 이유는 **쓰기 처리량이 아닙니다.** 읽기는 복제본을 늘려 해결하고, 샤딩은 데이터가 수 TB로 커지면서 한 대로 다루는 운영 작업(백업과 복구 시간, 스키마 변경 시간, 새 복제본을 만드는 시간, 버퍼 풀에 들어가지 않는 작업 집합)이 한계에 닿을 때 합니다. 위 가정이면 몇 년 뒤의 일이고, 그 시점은 W8에서 로컬 측정과 함께 다시 계산합니다.

### 7-3. 복제 지연과 read-your-writes (NFR-6)

복제본은 프라이머리보다 조금 늦게 따라옵니다. 크리에이터가 제목을 고치고 바로 새로고침했는데 복제본이 아직 옛 제목을 주면 "수정이 안 됐다"고 보입니다. 그래서 읽는 사람에 따라 읽는 곳을 나눕니다.

| 읽는 사람 | 읽는 곳 | 방법 |
|---|---|---|
| 일반 시청자 | 캐시 → 복제본 | 약간 늦어도 됨(NFR-6). 단, 쓰기보다 옛 값이 캐시에 다시 들어가지는 않음(7-4) |
| 자기 영상을 보는 크리에이터 | 캐시를 거치지 않고, 자기 쓰기가 반영된 복제본 | 캐시는 쓰기 직후 표식이 들어가기 전까지 옛 값을 줄 수 있으므로 읽지 않음. 쓰기 뒤 받은 복제 위치(트랜잭션 ID나 로그 위치)를 세션에 들고 있다가, 복제본이 그 위치까지 따라온 것을 확인하고 읽음. 제한 시간 안에 못 따라오면 프라이머리에서 읽음 |

두 번째 방법을 DB가 얼마나 기본으로 지원하는지가 ADR-0005의 판단 기준 중 하나입니다.

### 7-4. 캐시와 DB의 순서

쓰기는 DB에 먼저 반영하고 그다음 캐시를 고칩니다. 캐시를 먼저 고치면, 그 사이 들어온 읽기가 옛 값을 DB에서 읽어 캐시에 다시 넣을 수 있습니다.

**DB 뒤에 캐시를 지우는 것만으로는 부족합니다.** 2단계부터 캐시 미스는 복제본에서 읽습니다. 삭제한 직후의 캐시 미스가 아직 쓰기를 따라오지 못한 복제본을 읽으면, 옛 값이 다시 캐시에 들어가 TTL이 끝날 때까지 남습니다. 제목이라면 늦게 보이는 것으로 끝나지만, 공개 범위라면 `private`로 바꾼 영상이 캐시에서 `public`으로 남아 권한 검사(6-2)를 통과하고 서명 URL까지 발급됩니다.

그래서 캐시 항목에 `videos.version`을 붙이고, **옛 버전이 새 버전을 덮지 못하게 합니다.**

| 단계 | 하는 일 |
|---|---|
| 쓰기 | DB 커밋 뒤, 캐시 항목을 지우는 대신 **버전 표식** `{min_version: 새 version}`으로 덮어씀. 표식은 레코드와 같은 TTL을 가짐 |
| 읽기: 레코드 히트 | 그대로 씀 |
| 읽기: 미스 또는 표식 히트 | 복제본에서 읽음. 읽은 행의 `version`이 표식의 `min_version`보다 작으면 그 행은 버리고 프라이머리에서 읽음 |
| 캐시 채우기 | 캐시의 현재 값이 비었거나, 표식의 `min_version` 이하이거나, 더 낮은 버전의 레코드일 때만 씀. 비교와 쓰기는 캐시 안에서 원자적으로(Redis라면 Lua 스크립트) |

이렇게 하면 쓰기 뒤에 캐시에 들어갈 수 있는 값은 그 쓰기 이후의 버전뿐입니다. 쓰기 전에 복제본을 읽은 요청이 늦게 캐시를 채우려 해도, 이미 들어간 표식보다 버전이 낮아 거절됩니다. 표식이 있는 동안 복제본이 덜 따라온 미스는 프라이머리로 가지만, 복제 지연(초 단위) 동안 바뀐 영상에서만 생기므로 프라이머리 부하는 작습니다.

남는 빈틈은 **표식 쓰기 자체가 실패하는 경우**입니다. 캐시 장애로 표식을 못 쓰면 옛 레코드가 TTL까지 남습니다. 이 쓰기는 요청을 실패시키지 않고 재시도로 넘기며(ADR-0010의 발행 경로를 함께 쓸지 결정), 그래도 실패하면 레코드 TTL이 옛 값이 남을 수 있는 최대 시간입니다. 공개 범위에서는 이 TTL이 권한 변경의 최대 지연에 더해지므로, ADR-0008은 TTL을 정할 때 이 시간을 함께 봅니다.

**검토한 대안**

| 대안 | 버린 이유 |
|---|---|
| 캐시 미스는 항상 프라이머리에서 채움 | 캐시 미스 약 3,500건/초가 전부 프라이머리로 가서 2단계에서 복제본을 둔 이유가 사라짐 |
| 지연 이중 삭제(커밋 뒤 삭제, 몇 초 뒤 한 번 더 삭제) | 두 번째 삭제 시점보다 복제 지연이 길면 그대로 깨짐. 보장이 복제 지연의 추측에 걸림 |
| 캐시 항목에 GTID를 붙임 | 같은 효과지만 GTID 비교는 DB 제품에 묶이고, 샤딩(ADR-0011) 뒤에는 샤드마다 GTID 집합이 달라짐. `version`은 행 하나의 단조 증가 값이라 DB와 샤딩에 무관함 |

이 문서가 정하는 것은 "쓰기보다 옛 값이 캐시에 다시 들어가지 않는다"는 불변식과 그 기본안입니다. TTL 값, 핫 키에서 표식이 걸렸을 때 복제본으로 몰리는 읽기를 하나로 묶는 방법(single-flight)은 ADR-0008에서 정하고, 완료 판단은 W6에서 복제 지연을 일부러 만든 상태로 공개 범위를 바꿔 옛 값이 캐시에 다시 들어가는지 측정해서 합니다.

## 8. 아직 정하지 않은 것

| 항목 | 정할 곳 |
|---|---|
| RDB 제품 | ADR-0005 |
| 상태 전이와 이벤트 발행의 원자성 | ADR-0010 |
| 캐시 TTL, 핫 키(표식이 걸렸을 때의 single-flight 포함), 표식 쓰기의 재시도 경로, 서명 URL 유효 시간 | ADR-0007, ADR-0008, ADR-0010 |
| 조회수 저장과 반영 | ADR-0009 |
| 샤딩 키, 샤딩 뒤 채널 목록 조회 | ADR-0011 |
| 360p가 준비되면 바로 공개할지, 크리에이터가 고를지 | 멘토 세션 뒤 결정 |
| 자동 재시도 횟수(3회 가정) | W5 트랜스코딩 구현 |
