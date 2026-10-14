// 디자인 정본 값 (docs/design/style-guide.md v2.0, screens/*.md). 값을 바꾸려면 디자인 문서를 먼저 고친다.

export const FONT_UI =
  'system-ui, "Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans KR", "Noto Sans CJK KR", "Segoe UI", sans-serif';

// style-guide 1.1 팔레트 (프런트가 직접 쓰는 색만)
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

// 4장: 게임 월드. 월드 단위(로직, 네트워크)와 아트 px(그리기) = 2 : 1
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
  groundY: 220,
  bottomY: 250, // 화면 아래 끝 (4.3)
  headLineY: 176, // 말풍선 머리 위 기준선 (9장)
  minViewH: 80,
});

export const MOBILE_MAX_WIDTH = 720; // 미만이면 모바일
export const MOBILE_CONTROLS_H = 124; // 모바일 캔버스 아래 조작 영역 (game.md 3장)
export const DESKTOP_RESERVED_H = 72; // 데스크톱 캔버스 아래 채팅 행 + 여백
export const UI_SCALE = 2; // U (UI 스킨 PNG 1px = 2 CSS px)

/** style-guide 4.2: 정수 픽셀 배율 P */
export function pixelScale(vw, vh) {
  return vw >= 1600 && vh >= 900 ? 3 : 2;
}

// 5장: 아바타 (ARCHITECTURE 픽셀아트 계약)
export const AVATAR = Object.freeze({
  frameW: 32,
  frameH: 48,
  anchorX: 16,
  anchorY: 46,
  frames: 6,
  animations: Object.freeze({
    idle: Object.freeze({ frames: Object.freeze([0, 1]), ms: 500 }),
    walk: Object.freeze({ frames: Object.freeze([2, 3, 4, 5]), ms: 120 }),
  }),
});
export const PART_KEYS = Object.freeze(['skin', 'hair', 'eyes', 'top', 'bottom']);
export const DEFAULT_LAYER_ORDER = Object.freeze(['skin', 'bottom', 'top', 'eyes', 'hair']);
export const PART_LABELS = Object.freeze({ skin: '피부', hair: '머리', eyes: '눈', top: '상의', bottom: '하의' });
// aria-label 용 ("이전 머리 모양")
export const PART_ARIA = Object.freeze({ skin: '피부색', hair: '머리 모양', eyes: '눈 모양', top: '상의', bottom: '하의' });

// manifest.json이 없거나 깨졌을 때 쓰는 목록 (style-guide 5.10 순서, 첫 항목이 기본값)
export const DEFAULT_PARTS = Object.freeze({
  skin: [
    { id: 'skin-light', label: '밝은 피부' },
    { id: 'skin-tan', label: '보통 피부' },
    { id: 'skin-dark', label: '진한 피부' },
  ],
  hair: [
    { id: 'hair-round-black', label: '단발 · 흑발' },
    { id: 'hair-round-chestnut', label: '단발 · 밤색' },
    { id: 'hair-spiky-black', label: '뾰족 · 흑발' },
    { id: 'hair-spiky-chestnut', label: '뾰족 · 밤색' },
    { id: 'hair-spiky-mint', label: '뾰족 · 민트' },
    { id: 'hair-long-pink', label: '긴머리 · 분홍' },
    { id: 'hair-long-blonde', label: '긴머리 · 금발' },
  ],
  eyes: [
    { id: 'eyes-dot', label: '기본 눈' },
    { id: 'eyes-happy', label: '웃는 눈' },
    { id: 'eyes-sleepy', label: '졸린 눈' },
    { id: 'eyes-sparkle', label: '반짝 눈' },
  ],
  top: [
    { id: 'top-tee-red', label: '빨간 티셔츠' },
    { id: 'top-hoodie-blue', label: '파란 후드티' },
    { id: 'top-overalls-blue', label: '파란 멜빵' },
    { id: 'top-cape-mushroom', label: '버섯 망토' },
  ],
  bottom: [
    { id: 'bottom-shorts-navy', label: '네이비 반바지' },
    { id: 'bottom-jeans-blue', label: '청바지' },
    { id: 'bottom-skirt-pink', label: '분홍 치마' },
    { id: 'bottom-pumpkin-green', label: '초록 호박바지' },
  ],
});

// 사이클 1 id 호환 (style-guide 5.10). 매니페스트 aliases가 있으면 그것을 우선한다.
export const DEFAULT_ALIASES = Object.freeze({
  eyes: Object.freeze({ 'eyes-round': 'eyes-sparkle' }),
  top: Object.freeze({ 'top-vest-green': 'top-overalls-blue' }),
});

export const DEFAULT_AVATAR = Object.freeze({
  skin: 'skin-light',
  hair: 'hair-round-black',
  eyes: 'eyes-dot',
  top: 'top-tee-red',
  bottom: 'bottom-shorts-navy',
});

// 8장 닉네임 라벨, 9장 말풍선 (CSS px)
export const LABEL = Object.freeze({ font: 12, lineH: 16, h: 20, padX: 6, minW: 24, gap: 4, textTop: 2 });
export const BUBBLE = Object.freeze({
  font: 14,
  lineH: 18,
  padX: 12,
  padY: 8,
  maxW: 200,
  minW: 40,
  maxLines: 4,
  tailW: 16,
  tailH: 8,
  tipGap: 4, // 꼬리 끝 = 머리 기준선 - 4
  bodyGap: 6, // 몸통 아래 끝 = 꼬리 끝 - 6
  edge: 8,
  topMin: 4,
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
