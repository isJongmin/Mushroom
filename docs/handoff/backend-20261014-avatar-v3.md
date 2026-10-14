# backend → main: 아바타 데이터 v3 (7개 키) 마이그레이션 (2026-10-14, 사이클 3)

## 변경 파일
- `supabase/migrations/20261014000200_avatar_v3.sql` — 신규. 기존 마이그레이션 2개는 수정하지 않음.
- `supabase/README.md` — 마이그레이션 목록/적용 순서, 아바타 형식(3절, 5절), 변환 규칙(8절), 테이블 요약, 배포 순서 주의 갱신.
- 커밋하지 않음.

## 마이그레이션 내용 (`20261014000200_avatar_v3.sql`)
한 트랜잭션으로 실행(CLI는 파일 단위로 감싸고, SQL Editor는 한 번에 붙여넣은 스크립트를 암묵적 단일 트랜잭션으로 실행. 기존 파일과 같은 이유로 begin/commit은 넣지 않음. psql은 `-1`).
1. `lock table public.characters in access exclusive mode` — 변환과 새 제약 사이에 구 형식 행이 끼어들지 않게.
2. `drop constraint if exists characters_avatar_shape`
3. 기존 행 변환:
   - `skin, hair, top, bottom`: 유지
   - `face`: 기존 `face`(재실행 대비) → 없으면 `eyes` 값 그대로(예 `eyes-dot`) → 없으면 `"basic"`
   - `shoes`: 없으면 `"sneakers-white"`, `hat`: 없으면 `"none"`
   - `eyes`와 그 밖의 키 삭제
   - face를 `basic`으로 통일하지 않고 eyes id를 보존한 이유: 계약상 프런트가 manifest에 없는 id를 기본값으로 그리므로 결과는 같고, 필요하면 프런트가 구 id → 새 id 별칭을 둘 수 있다.
4. `add constraint characters_avatar_shape` (같은 이름): object, 키 `skin, hair, face, top, bottom, shoes, hat` 정확히 7개(누락·추가 모두 거부), 각 값 string `^[a-z0-9-]{1,32}$`. 누락 키 NULL 통과 방지를 위해 `coalesce(..., false)`. NOT VALID 아님(기존 행 전체 검사).
5. `comment on column avatar` 갱신.
- 파츠 id 실존 여부는 DB에서 검사하지 않음(기존 방침).
- 권한/RLS는 건드리지 않음: `grant update (avatar)`, 본인 행 RLS 3정책, nickname 변경 불가(컬럼 권한) 그대로. 검증으로 확인.
- 재실행 안전(drop if exists, 이미 v3인 행은 갱신 안 함).

## 테이블 구조 변화
`public.characters.avatar` check `characters_avatar_shape`만 변경. 컬럼/인덱스/정책/권한/RPC 변경 없음.

## 프런트용 새 avatar 형식
```json
{ "skin":"skin-light", "hair":"hair-round-black", "face":"basic", "top":"top-tee-red",
  "bottom":"bottom-jeans-blue", "shoes":"sneakers-white", "hat":"none" }
```
- 정확히 7개 키, 모든 값 문자열 `^[a-z0-9-]{1,32}$`. `hat` 없음은 `"none"`(키 생략/null 불가). `eyes` 키를 보내면 거부.
- 위반 시 `23514` + `characters_avatar_shape` (오류 처리 코드 변경 불필요).
- insert/update API, 오류 코드, Realtime 형식은 그대로. update도 7개 키 전체를 보낸다.
- 기존 사용자 데이터는 `face`에 구 eyes id(`eyes-dot` 등), 나머지에 구 id(`hair-round-black` 등)가 남는다 → manifest에 없는 id는 해당 파츠 기본값으로 그릴 것.
- 현재 `src/client/constants.js`의 `PART_KEYS`가 `['skin','hair','eyes','top','bottom']`이다. 이 마이그레이션 적용 후 이 상태의 프런트는 캐릭터 생성이 `23514`로 실패한다 → **새 프런트와 같은 시점에 적용**.
- Presence로 받는 avatar는 DB를 거치지 않으므로 구 클라이언트의 5키 객체가 올 수 있다 → 수신 측에서 7키로 정규화(누락 키는 기본값) 후 그릴 것.

## 사용자(메인 경유) 작업
- SQL Editor에서 `20261014000200_avatar_v3.sql` 전체를 한 번에 Run(또는 `supabase db push`). 확인 쿼리는 README 적용 순서 5번.

## 검증 결과
환경: 로컬 PostgreSQL 16.15 임시 클러스터 + Supabase 스텁(anon/authenticated/service_role, `auth.users`, `auth.uid()`=JWT claims sub, public 스키마 default privileges 재현). 스크래치 디렉터리에서 실행, 종료 후 클러스터 삭제.

- 마이그레이션 3개 순서 적용(`psql -1 -f`, ON_ERROR_STOP): **통과**
- 자동 테스트 69건: **69 통과 / 0 실패**
  - 적용 전: 구 5키 insert 성공, 7키 거부(구 제약 확인)
  - 변환: 사이클 1 행 2건 → 7키, face=구 eyes 값, shoes=`sneakers-white`, hat=`none`, eyes 없음, nickname 불변
  - 제약 메타: 이름 유지·1개·validated, 정의에 face/shoes/hat 포함·eyes 없음, 다른 제약 목록 불변
  - 권한 유지: RLS on, 정책 3개, authenticated UPDATE 컬럼=avatar만, INSERT 컬럼=user_id/nickname/avatar, anon 권한 없음
  - 새 형식 insert 성공(hat `none`, hat 다른 id, 32자/숫자/하이픈 경계)
  - 거부 23514(20종): 6키(hat/shoes/face 각각 누락), 8키(추가 키, eyes 추가), face 대신 eyes 7키, 구 5키, 값 숫자/null/대문자/빈 문자열/33자/공백·밑줄/`../`/개행/객체, 배열·문자열·빈 객체·json null. SQL null → 23502
  - update: 본인 새 형식 성공, 본인 구형식·8키·hat 제거 23514, 타인 행 0행·불변, 조건 없는 update는 본인 1행만, nickname·nickname+avatar·user_id·created_at 42501, anon 42501, sub 없음 0행
  - 회귀: pkey 중복 23505, 닉네임 대소문자 중복 23505, 닉네임 형식 23514, 타인 user_id insert 42501, created_at insert 42501, upsert 42501, delete 42501, authenticated 전체 select, anon select/insert/RPC 42501, RPC 대소문자 무시, auth.users 삭제 cascade
- 재실행: 오류 없음, 데이터 변화 0, 제약 1개: **통과**
- SQL Editor 방식(파일 전체를 단일 쿼리 메시지로 전송): 변환 결과 동일: **통과**
- 원자성: 파일 끝에 오류 주입 시 `psql -1`과 단일 쿼리 방식 모두 구 제약·구 데이터(eyes 2행) 그대로 롤백: **통과**
- 동시성: 마이그레이션 트랜잭션 진행 중 다른 세션의 구 형식 insert → 커밋까지 대기 후 23514, eyes 행 0: **통과**
- **미검증**: 실제 Supabase(PG 15/17, PostgREST 경유 `error.code`/`error.message` 형식), supabase CLI의 실제 트랜잭션 래핑, 대시보드 SQL Editor 실제 동작, Realtime.

## QA 확인 항목
1. 기존(사이클 1~2) 계정 로그인 → 캐릭터가 face/shoes/hat 기본값으로 정상 표시(구 id 때문에 깨지지 않음).
2. 새 계정 생성: 7키 avatar insert 성공, hat `none`·다른 hat 모두 저장.
3. 권한 우회(supabase-js/REST): `insert`에 `eyes` 포함 또는 6키/8키 → 23514, `update({ nickname })` → 42501, 타인 행 `update({ avatar })` → 0행, `update({ avatar: <5키> })` → 23514, 값에 대문자/`../`/33자 → 23514.
4. Presence 위조: 구 5키 또는 이상한 avatar를 track해도 다른 클라이언트가 깨지지 않는지(프런트 정규화).
5. 구 버전 프런트가 열려 있는 상태에서 마이그레이션 적용 시 캐릭터 생성 실패(예상 동작, 새 프런트 배포 필요).
