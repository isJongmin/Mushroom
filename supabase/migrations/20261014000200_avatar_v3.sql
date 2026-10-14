-- =============================================================================
-- 버섯마을: 아바타 데이터 v3 (7개 키)
-- 마이그레이션: 20261014000200_avatar_v3.sql
--
-- characters.avatar 형식 변경 (docs/ARCHITECTURE.md "인터페이스 계약", 사이클 3):
--   이전: { skin, hair, eyes, top, bottom }                     5개 키
--   이후: { skin, hair, face, top, bottom, shoes, hat }          7개 키
--   - eyes → face 로 대체. hat은 "none"(모자 없음) 허용.
--   - 각 값은 파츠 id 문자열 ^[a-z0-9-]{1,32}$.
--   - 파츠 id가 manifest에 실제로 있는지는 DB가 검사하지 않는다(기존 방침).
--     manifest에 없는 id는 프런트가 해당 파츠의 기본값(첫 항목)으로 그린다.
--
-- 순서: 잠금 → 기존 check 제약 제거 → 기존 행 변환 → 새 check 제약(같은 이름) 추가.
--
-- [트랜잭션]
-- 이 파일은 하나의 트랜잭션으로 실행되어야 한다(중간 실패 시 제약 없이 남지 않도록).
-- 기존 마이그레이션과 같은 이유로 begin/commit은 넣지 않는다.
--  - supabase CLI(`supabase db push`)는 마이그레이션 파일 단위로 트랜잭션을 감싼다.
--  - 대시보드 SQL Editor는 붙여넣은 스크립트 전체를 한 번에 보내므로(단일 쿼리 메시지)
--    Postgres가 암묵적 단일 트랜잭션으로 실행한다.
--  - psql로 직접 실행할 때는 `psql -1 -f <파일>`(--single-transaction)을 쓴다.
--
-- [재실행]
-- 다시 실행해도 안전하다(drop if exists, 변환은 이미 v3인 행을 그대로 둔다).
--
-- [권한/RLS]
-- 이 파일은 권한·정책을 건드리지 않는다. 20261014000000_characters.sql의
-- grant update (avatar) / 본인 행 RLS / nickname 변경 불가(컬럼 권한)가 그대로 유지된다.
-- (alter table ... drop/add constraint는 grant와 policy에 영향을 주지 않는다)
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 0. 잠금
-- 변환과 새 제약 추가 사이에 구 형식(5개 키) 행이 끼어드는 것을 막는다.
-- (drop constraint도 같은 잠금을 잡지만, 의도를 명시하기 위해 먼저 잡는다)
-- 트랜잭션이 끝날 때까지 다른 세션의 characters 읽기/쓰기는 대기한다. 행 수가 적어 짧다.
-- -----------------------------------------------------------------------------
lock table public.characters in access exclusive mode;


-- -----------------------------------------------------------------------------
-- 1. 기존 check 제약 제거
-- -----------------------------------------------------------------------------
alter table public.characters
  drop constraint if exists characters_avatar_shape;


-- -----------------------------------------------------------------------------
-- 2. 기존 행 변환
--
-- 키별 값 결정 (값이 ^[a-z0-9-]{1,32}$ 문자열일 때만 "유효"로 본다):
--   skin, hair, top, bottom : 기존 값 유지. (구 제약상 항상 유효. 만일 아니면 'basic')
--   face  : 기존 face가 유효하면 유지(재실행 대비) → 아니면 eyes 값 → 아니면 'basic'
--           사이클 1~2의 eyes id(eyes-dot 등)는 새 manifest에 없으므로 프런트가 face 기본값으로
--           그린다(계약). id를 보존해 두면 프런트가 별칭 매핑을 추가할 수도 있다.
--   shoes : 기존 값이 유효하면 유지 → 아니면 'sneakers-white'
--   hat   : 기존 값이 유효하면 유지 → 아니면 'none'
-- 7개 키 외의 키(eyes 포함)는 모두 버린다.
-- 이미 v3 형식인 행은 결과가 같으므로 where 절로 건너뛴다.
-- -----------------------------------------------------------------------------
with converted as (
  select
    c.user_id,
    jsonb_build_object(
      'skin',   case when (c.avatar ->> 'skin')   ~ '^[a-z0-9-]{1,32}$' and jsonb_typeof(c.avatar -> 'skin')   = 'string' then c.avatar ->> 'skin'   else 'basic' end,
      'hair',   case when (c.avatar ->> 'hair')   ~ '^[a-z0-9-]{1,32}$' and jsonb_typeof(c.avatar -> 'hair')   = 'string' then c.avatar ->> 'hair'   else 'basic' end,
      'face',   case when (c.avatar ->> 'face')   ~ '^[a-z0-9-]{1,32}$' and jsonb_typeof(c.avatar -> 'face')   = 'string' then c.avatar ->> 'face'
                     when (c.avatar ->> 'eyes')   ~ '^[a-z0-9-]{1,32}$' and jsonb_typeof(c.avatar -> 'eyes')   = 'string' then c.avatar ->> 'eyes'
                     else 'basic' end,
      'top',    case when (c.avatar ->> 'top')    ~ '^[a-z0-9-]{1,32}$' and jsonb_typeof(c.avatar -> 'top')    = 'string' then c.avatar ->> 'top'    else 'basic' end,
      'bottom', case when (c.avatar ->> 'bottom') ~ '^[a-z0-9-]{1,32}$' and jsonb_typeof(c.avatar -> 'bottom') = 'string' then c.avatar ->> 'bottom' else 'basic' end,
      'shoes',  case when (c.avatar ->> 'shoes')  ~ '^[a-z0-9-]{1,32}$' and jsonb_typeof(c.avatar -> 'shoes')  = 'string' then c.avatar ->> 'shoes'  else 'sneakers-white' end,
      'hat',    case when (c.avatar ->> 'hat')    ~ '^[a-z0-9-]{1,32}$' and jsonb_typeof(c.avatar -> 'hat')    = 'string' then c.avatar ->> 'hat'    else 'none' end
    ) as avatar
  from public.characters c
)
update public.characters c
   set avatar = v.avatar
  from converted v
 where v.user_id = c.user_id
   and c.avatar is distinct from v.avatar;


-- -----------------------------------------------------------------------------
-- 3. 새 check 제약 (이름 유지: characters_avatar_shape)
--
-- object, 정확히 7개 키, 각 값 string ^[a-z0-9-]{1,32}$.
-- 위반 시 23514 / "characters_avatar_shape" (프런트 오류 처리 그대로 사용 가능).
-- 주의: 키가 없으면 jsonb_typeof(...)가 NULL → CHECK는 NULL을 통과로 보므로
-- 전체를 coalesce(..., false)로 감싼다(사이클 1에서 발견한 결함과 같은 처리).
-- 추가 시 기존 행 전체를 검사한다(NOT VALID 아님). 변환이 잘못됐다면 여기서 실패하고
-- 트랜잭션 전체가 롤백된다.
-- -----------------------------------------------------------------------------
alter table public.characters
  add constraint characters_avatar_shape
  check (coalesce(
    jsonb_typeof(avatar) = 'object'
    and avatar ?& array['skin', 'hair', 'face', 'top', 'bottom', 'shoes', 'hat']
    and (avatar - array['skin', 'hair', 'face', 'top', 'bottom', 'shoes', 'hat']) = '{}'::jsonb
    and jsonb_typeof(avatar -> 'skin')   = 'string'
    and jsonb_typeof(avatar -> 'hair')   = 'string'
    and jsonb_typeof(avatar -> 'face')   = 'string'
    and jsonb_typeof(avatar -> 'top')    = 'string'
    and jsonb_typeof(avatar -> 'bottom') = 'string'
    and jsonb_typeof(avatar -> 'shoes')  = 'string'
    and jsonb_typeof(avatar -> 'hat')    = 'string'
    and (avatar ->> 'skin')   ~ '^[a-z0-9-]{1,32}$'
    and (avatar ->> 'hair')   ~ '^[a-z0-9-]{1,32}$'
    and (avatar ->> 'face')   ~ '^[a-z0-9-]{1,32}$'
    and (avatar ->> 'top')    ~ '^[a-z0-9-]{1,32}$'
    and (avatar ->> 'bottom') ~ '^[a-z0-9-]{1,32}$'
    and (avatar ->> 'shoes')  ~ '^[a-z0-9-]{1,32}$'
    and (avatar ->> 'hat')    ~ '^[a-z0-9-]{1,32}$',
    false
  ));

comment on column public.characters.avatar is
  '{skin,hair,face,top,bottom,shoes,hat} 파츠 id(^[a-z0-9-]{1,32}$). hat은 "none" 허용. id 존재 여부는 프런트 manifest 기준(DB 미검사).';
