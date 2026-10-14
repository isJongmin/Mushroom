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

// 게임 월드 (style-guide v3 6장). 월드 단위(로직, 네트워크)와 아트 px(그리기) = 2 : 1
export const WORLD = Object.freeze({
  width: 2400,
  height: 540,
  groundY: 440,
  speed: 160, // 월드 단위/초
  minX: 32,
  maxX: 2368,
  maxDt: 0.1, // 탭 비활성 등으로 생긴 큰 dt는 이 값으로 자른다(초)
});
export const ART = Object.freeze({
  perWorld: 2, // 월드 2단위 = 아트 1px
  width: 1200,
  height: 270,
  groundY: 220, // 지면선 (ARCHITECTURE 블록 아트 계약)
  bottomY: 250, // 화면 아래 끝 (style-guide 6.2)
  headLine: 52, // 말풍선 머리 위 기준선: 기준점에서 아트 52px 위 (style-guide 8.2)
  minViewH: 80,
});

export const MOBILE_MAX_WIDTH = 720; // 미만이면 모바일
export const MOBILE_CONTROLS_H = 132; // 모바일 캔버스 아래 조작 영역 (game.md v3 3장: 64 + 68)
export const MOBILE_MIN_CANVAS_H = 160; // 소프트 키보드 시 최소 캔버스 세로
export const DESKTOP_RESERVED_H = 72; // 데스크톱 캔버스 아래 채팅 행 + 여백

/** style-guide 6.1: 정수 픽셀 배율 P */
export function pixelScale(vw, vh) {
  return vw >= 1600 && vh >= 900 ? 3 : 2;
}

// 아바타 (ARCHITECTURE 블록 아트 계약). manifest.json 값이 우선이고, 아래는 manifest가 없거나 깨졌을 때의 기본값이다.
export const AVATAR = Object.freeze({
  frameW: 48,
  frameH: 64,
  anchorX: 24,
  anchorY: 60,
  frames: Object.freeze(['front', 'side_idle', 'side_walk0', 'side_walk1', 'side_walk2', 'side_walk3', 'back']),
  animations: Object.freeze({
    idle: Object.freeze({ frames: Object.freeze([1]), ms: 500 }),
    walk: Object.freeze({ frames: Object.freeze([2, 3, 4, 5]), ms: 150 }),
  }),
});
// 아바타 데이터 키 (ARCHITECTURE 인터페이스 계약, 사이클 3): 정확히 7개
export const PART_KEYS = Object.freeze(['skin', 'hair', 'face', 'top', 'bottom', 'shoes', 'hat']);
// 합성 레이어 순서 (hair는 hair_back / hair_front 두 레이어)
export const DEFAULT_LAYER_ORDER = Object.freeze(['hair_back', 'skin', 'face', 'bottom', 'shoes', 'top', 'hair_front', 'hat']);
export const LAYER_PART = Object.freeze({
  hair_back: 'hair', skin: 'skin', face: 'face', bottom: 'bottom', shoes: 'shoes', top: 'top', hair_front: 'hair', hat: 'hat',
});
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

// style-guide v3 7장 닉네임 라벨, 8장 말풍선 (CSS px, U=2 고정)
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
  tipGap: 4, // 꼬리 끝 = 머리 위 기준선 - 4
  tailH: 8, // 박스 아래 끝 ~ 꼬리 끝
  edge: 8,
  tailEdge: 10,
  topMin: 4,
  topClamp: 6,
  showMs: 5000,
  fadeMs: 500,
});

// 입력 규칙
export const ID_RE = /^[a-z0-9_]{4,16}$/;
export const PW_MIN = 8;
export const NICK_RE = /^[가-힣a-zA-Z0-9]{2,12}$/;
export const PART_ID_RE = /^[a-z0-9-]{1,32}$/;

// 네트워크
export const CHAT_MAX = 80;
export const CHAT_COOLDOWN_MS = 1000;
export const MOVE_INTERVAL_MS = 100; // 최대 10회/초
export const NICK_DEBOUNCE_MS = 500;
export const RECONNECT_DELAYS_MS = Object.freeze([1000, 2000, 4000]);
export const BOOT_TIMEOUT_MS = 3000;

export const CHANNEL_NAME = 'map:village';
export const SUPABASE_CDN = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.4/+esm';
