// 디자인 정본 값 (docs/design/style-guide.md v3.0, screens/*.md v3.0)과 ARCHITECTURE 블록 아트 계약 값.
// 값을 바꾸려면 정본 문서를 먼저 고친다.

export const FONT_UI =
  'system-ui, -apple-system, "Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans KR", "Noto Sans CJK KR", "Segoe UI", sans-serif';

// style-guide 1장 팔레트 (프런트가 직접 쓰는 색만)
export const PAL = Object.freeze({
  ink: '#1A1626', hb1: '#4A4560', hb2: '#2E2A3E',
  w1: '#E0A868', w2: '#B97A4A', w3: '#8A5232', w4: '#5E3620',
  s1: '#FFE3CC', s2: '#F5C29A', s3: '#D99464',
  white: '#FFFFFF',
  y1: '#FFF2A8', y2: '#F7C948', y3: '#F08A2E', y4: '#A84A1E',
  p1: '#FFC8DC', p2: '#F58AB4', p3: '#B04A78',
  r1: '#FF8E7A', r2: '#E8483E', r3: '#9E2838',
  u1: '#9CC8FF', u2: '#4D7CFE', u3: '#2E3E9E', u4: '#232A5E',
  g1: '#B6E86A', g2: '#6CC443', g3: '#3E8A2E', g4: '#23562A',
  c1: '#FFF6E4', c2: '#F2DDB8', c3: '#C9A47A',
  m1: '#BFF0DC', m2: '#7ED6B4', m3: '#3E9A86',
  k1: '#6EC6F5', k2: '#86D2F8', k3: '#A0DDFA', k4: '#BBE8FC', k5: '#D8F3FE',
  st1: '#C8C4D0', st2: '#8E88A0',
});

// 게임 월드 (ARCHITECTURE "복셀 아트 계약", 사이클 5). 로직/네트워크/그리기 모두 월드 단위.
// 화면 CSS px = 월드 x (P / 2). 에셋 px = 월드 x density(1.5).
export const WORLD = Object.freeze({
  width: 2400,
  height: 540,
  groundY: 440, // 지면선 = 캐릭터 기준점(발) y
  bottomY: 540, // 화면 아래 끝 (월드 맨 아래, 앞 단면 흙/돌까지)
  speed: 160, // 월드 단위/초
  minX: 32,
  maxX: 2368,
  maxDt: 0.1, // 탭 비활성 등으로 생긴 큰 dt는 이 값으로 자른다(초)
  minViewH: 160, // 시야 세로 최소 (월드)
});
// 캐릭터 머리 위 기준선(말풍선 꼬리 끝 위치)의 기본값과 여백 (월드 단위).
// 실제 값은 조합마다 합성 시트 idle 프레임의 맨 위 불투명 행으로 계산한다(avatar.js headTop).
export const HEAD = Object.freeze({
  fallback: 104, // 계산 전/실패 시: 모자 포함 최대 키(시트 157px / 1.5 ≈ 105)
  gap: 4, // 머리(또는 모자) 맨 위와 말풍선 꼬리 끝 사이
});
// 발 그림자 (map handoff 4장 권장: 반투명 타원, 알파 0.25)
export const FOOT_SHADOW = Object.freeze({ rx: 22, ry: 5, color: 'rgba(26, 22, 38, 0.25)' });

export const MOBILE_MAX_WIDTH = 720; // 미만이면 모바일
export const MOBILE_CONTROLS_H = 132; // 모바일 캔버스 아래 조작 영역 (game.md v3 3장: 64 + 68)
export const MOBILE_MIN_CANVAS_H = 160; // 소프트 키보드 시 최소 캔버스 세로
export const DESKTOP_RESERVED_H = 72; // 데스크톱 캔버스 아래 채팅 행 + 여백

/** style-guide 6.1: 표시 배율 P (화면 CSS px / 월드 단위 = P / 2) */
export function pixelScale(vw, vh) {
  return vw >= 1600 && vh >= 900 ? 3 : 2;
}

// 아바타 (ARCHITECTURE "복셀 아트 계약", 사이클 5). manifest.json 값이 우선이고, 아래는 manifest 값이 빠졌거나 깨졌을 때의 기본값이다.
export const AVATAR = Object.freeze({
  frameW: 144, // 시트 px
  frameH: 192,
  anchorX: 72,
  anchorY: 180,
  density: 1.5, // 시트 px / 월드 단위
  frames: Object.freeze(['front', 'front_b', 'side', 'walk0', 'walk1', 'walk2', 'walk3', 'back']),
  animations: Object.freeze({
    idle_front: Object.freeze({ frames: Object.freeze([0, 1]), ms: 600 }),
    idle: Object.freeze({ frames: Object.freeze([2]), ms: 600 }),
    walk: Object.freeze({ frames: Object.freeze([3, 4, 5, 6]), ms: 150 }),
  }),
});
// 아바타 데이터 키 (ARCHITECTURE 인터페이스 계약, 사이클 3): 정확히 7개
export const PART_KEYS = Object.freeze(['skin', 'hair', 'face', 'top', 'bottom', 'shoes', 'hat']);
// manifest layerOrder가 없거나 깨졌을 때의 기본 합성 순서 (art-20261015-voxel-final.md 3장 표와 같음)
export const DEFAULT_LAYER_ORDER = Object.freeze([
  ['hair_back', 'hair', 'source-over'], ['top_back', 'top', 'source-over'], ['skin', 'skin', 'source-over'],
  ['face', 'face', 'source-over'], ['shoes_under', 'shoes', 'source-over'], ['bottom', 'bottom', 'source-over'], ['shoes', 'shoes', 'source-over'],
  ['shade_top', 'top', 'source-atop'], ['top', 'top', 'source-over'], ['shade_hair', 'hair', 'source-atop'],
  ['hat_back', 'hat', 'source-over'], ['hair_front', 'hair', 'source-over'], ['shade_hat', 'hat', 'source-atop'],
  ['hat', 'hat', 'source-over'],
].map(([layer, part, blend]) => Object.freeze({ layer, part, blend })));
export const LAYER_BLENDS = Object.freeze(['source-over', 'source-atop']);
// manifest files가 없거나 깨졌을 때만 요청하는 필수 레이어 (메인 결정 2026-10-15, art check.py 2번:
// 이 레이어들은 해당 파츠의 모든 id에 파일이 있다. hat은 'none' 제외). 그림자/뒷 레이어는 빠진다.
export const REQUIRED_LAYERS = Object.freeze(['skin', 'face', 'hair_front', 'top', 'bottom', 'shoes', 'hat']);
export const HAT_NONE = 'none';

// 캐릭터 생성 카테고리 탭 순서와 글자 (character-create.md v3 5.1)
export const CATEGORY_ORDER = Object.freeze(['skin', 'face', 'hair', 'hat', 'top', 'bottom', 'shoes']);
export const PART_LABELS = Object.freeze({ skin: '피부', face: '얼굴', hair: '머리', hat: '모자', top: '상의', bottom: '하의', shoes: '신발' });

// manifest 각 파츠 첫 항목 (manifest가 없을 때의 기본값과 저장 기본값)
export const DEFAULT_AVATAR = Object.freeze({
  skin: 'light',
  hair: 'black-short',
  face: 'basic',
  top: 'hoodie-black',
  bottom: 'pants-navy',
  shoes: 'sneakers-white',
  hat: 'none',
});

// 사이클 1~2 id -> 사이클 3 id (art-20261014-block-final.md 5장 매핑표). face에는 옛 eyes id가 들어올 수 있다.
export const LEGACY_ALIASES = Object.freeze({
  skin: Object.freeze({ 'skin-light': 'light', 'skin-tan': 'medium', 'skin-dark': 'dark' }),
  hair: Object.freeze({
    'hair-round-black': 'black-short',
    'hair-round-chestnut': 'brown-short',
    'hair-spiky-black': 'black-short',
    'hair-spiky-chestnut': 'brown-short',
    'hair-spiky-mint': 'mint-curly',
    'hair-long-pink': 'pink-long',
    'hair-long-blonde': 'blonde-spiky',
  }),
  face: Object.freeze({
    'eyes-dot': 'basic', 'eyes-round': 'basic', 'eyes-sparkle': 'basic', 'eyes-happy': 'smile', 'eyes-sleepy': 'sleepy',
  }),
  top: Object.freeze({
    'top-tee-red': 'tee-stripe-red',
    'top-hoodie-blue': 'hoodie-white',
    'top-overalls-blue': 'overalls-green',
    'top-vest-green': 'overalls-green',
    'top-cape-mushroom': 'cape-blue',
  }),
  bottom: Object.freeze({
    'bottom-shorts-navy': 'pants-navy',
    'bottom-jeans-blue': 'jeans-blue',
    'bottom-skirt-pink': 'skirt-pink',
    'bottom-pumpkin-green': 'shorts-brown',
  }),
  shoes: Object.freeze({}),
  hat: Object.freeze({}),
});

// style-guide v3 7장 닉네임 라벨, 8장 말풍선 (CSS px)
export const LABEL = Object.freeze({ font: 12, lineH: 16, h: 20, padX: 6, minW: 24, top: 6, textTop: 2, edge: 4 });
export const BUBBLE = Object.freeze({
  font: 14,
  lineH: 18,
  padTop: 6,
  padX: 10,
  padBottom: 8,
  wrapW: 180,
  maxW: 200,
  minW: 40,
  maxLines: 4,
  tipGap: 4, // 꼬리 끝 = 머리 위 기준선(HEAD) - 4
  tailH: 8, // 박스 아래 끝 ~ 꼬리 끝
  edge: 8,
  tailEdge: 10,
  topMin: 4,
  topClamp: 6,
  showMs: 5000,
  fadeMs: 500,
});

// 입력 규칙 (ARCHITECTURE 결정 3, 4)
export const NICK_RE = /^[가-힣a-zA-Z0-9]{2,12}$/;
export const NICK_MAX = 12;
export const ROOM_NAME_MAX = 24;
export const ROOM_PW_MIN = 4;
export const ROOM_PW_MAX = 32;
export const ROOM_CAPACITY = 20;
export const PART_ID_RE = /^[a-z0-9-]{1,32}$/;

// 네트워크
export const CHAT_MAX = 80;
export const CHAT_COOLDOWN_MS = 1000;
export const MOVE_INTERVAL_MS = 100; // 최대 10회/초
export const RECONNECT_DELAYS_MS = Object.freeze([1000, 2000, 4000]);
export const BOOT_TIMEOUT_MS = 8000; // 익명 로그인 + 재입장 대기 상한
export const HEARTBEAT_MS = 20000; // 방 안 하트비트 (ARCHITECTURE 결정 4)
export const LOBBY_POLL_MS = 5000; // 로비 목록 폴링 (lobby.md 3.2)
export const RATE_LOCK_MS = 10000; // RATE_LIMITED 후 주 버튼 잠금 (lobby.md 7, 8.3)
export const LEAVE_WAIT_MS = 1500; // 나가기: leave_room 최대 대기 (room.md 1.2)
export const LOG_DOM_MAX = 200; // 채팅 로그 DOM 상한 (room.md 5.3-8)
export const SYS_LEAVE_DELAY_MS = 3000; // 퇴장 시스템 메시지 지연 (room.md 5.3-6)

// 저장소 키 (ARCHITECTURE 결정 3, 6)
export const LS_PROFILE = 'mushroom:profile';
export const SS_ROOM = 'mushroom:room';
export const SS_LOG_OPEN = 'mushroom:logOpen';
export const SUPABASE_CDN = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.4/+esm';
