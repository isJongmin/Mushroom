// 디자인 정본 값 (docs/design/style-guide.md, screens/*.md). 값을 바꾸려면 디자인 문서를 먼저 고친다.

export const FONT_UI =
  'system-ui, "Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans KR", "Noto Sans CJK KR", "Segoe UI", sans-serif';

export const COLORS = Object.freeze({
  skyTop: '#8FD8FF',
  skyBottom: '#D6F3FF',
  cloud: '#FFFFFF',
  hillFar: '#B8E6A0',
  grassLight: '#9BE35A',
  grass: '#6CC443',
  grassDark: '#3E9A2A',
  soilLight: '#C98B55',
  soil: '#A46A3C',
  soilDark: '#7A4A28',
  letterbox: '#1B140E',
  outline: '#2B2118',
  bubbleBg: '#FFFFFF',
  bubbleBorder: '#2B2118',
  bubbleText: '#2B2118',
  labelBg: 'rgba(43,33,24,0.72)',
  labelText: '#FFFFFF',
  labelSelfBg: '#FF8A3D',
  labelSelfText: '#2B1A10',
  border: '#D9C8B4',
});

// 4장: 게임 월드
export const WORLD = Object.freeze({
  width: 2400,
  height: 540,
  groundY: 440,
  grassBottom: 468,
  speed: 160, // px/s
  minX: 32,
  maxX: 2368,
  bobAmp: 2,
  bobPeriod: 0.4,
  maxDt: 0.1, // 탭 비활성 등으로 생긴 큰 dt는 이 값으로 자른다(초)
});

export const VIEW_DESKTOP = Object.freeze({ w: 960, h: 540, camY: 0 });
export const VIEW_MOBILE = Object.freeze({ w: 480, h: 270, camY: 200 });
export const MOBILE_MAX_WIDTH = 720; // 미만이면 모바일
export const CANVAS_MAX = Object.freeze({ w: 1280, h: 720 });

// 5장: 아바타
export const AVATAR = Object.freeze({ w: 64, h: 96, anchorX: 32, anchorY: 92, headTopY: 4 });
export const PART_KEYS = Object.freeze(['skin', 'hair', 'eyes', 'top', 'bottom']);
export const DEFAULT_LAYER_ORDER = Object.freeze(['skin', 'bottom', 'top', 'eyes', 'hair']);
export const PART_LABELS = Object.freeze({ skin: '피부', hair: '머리', eyes: '눈', top: '상의', bottom: '하의' });
// aria-label 용 ("이전 머리 모양")
export const PART_ARIA = Object.freeze({ skin: '피부색', hair: '머리 모양', eyes: '눈 모양', top: '상의', bottom: '하의' });

// manifest.json이 없거나 깨졌을 때 쓰는 목록 (style-guide 5.4 / 5.6 순서 그대로)
export const DEFAULT_PARTS = Object.freeze({
  skin: [
    { id: 'skin-light', label: '밝은 피부' },
    { id: 'skin-tan', label: '보통 피부' },
    { id: 'skin-dark', label: '진한 피부' },
  ],
  hair: [
    { id: 'hair-round-black', label: '둥근 단발 · 흑발' },
    { id: 'hair-round-chestnut', label: '둥근 단발 · 밤색' },
    { id: 'hair-spiky-black', label: '뾰족 머리 · 흑발' },
    { id: 'hair-spiky-chestnut', label: '뾰족 머리 · 밤색' },
  ],
  eyes: [
    { id: 'eyes-dot', label: '점 눈' },
    { id: 'eyes-round', label: '큰 눈' },
    { id: 'eyes-happy', label: '웃는 눈' },
  ],
  top: [
    { id: 'top-tee-red', label: '빨간 티셔츠' },
    { id: 'top-hoodie-blue', label: '파란 후드티' },
    { id: 'top-vest-green', label: '초록 조끼' },
  ],
  bottom: [
    { id: 'bottom-shorts-navy', label: '네이비 반바지' },
    { id: 'bottom-jeans-blue', label: '청바지' },
    { id: 'bottom-skirt-pink', label: '분홍 치마' },
  ],
});

export const DEFAULT_AVATAR = Object.freeze({
  skin: 'skin-light',
  hair: 'hair-round-black',
  eyes: 'eyes-dot',
  top: 'top-tee-red',
  bottom: 'bottom-shorts-navy',
});

// 6장, 7장
export const LABEL = Object.freeze({ font: 12, lineH: 16, padX: 6, padY: 2, radius: 4, gap: 4 });
export const BUBBLE = Object.freeze({
  font: 14,
  lineH: 18,
  padX: 12,
  padY: 8,
  maxW: 200,
  minW: 40,
  maxLines: 4,
  radius: 12,
  border: 2,
  tailW: 12,
  tailH: 8,
  tailGap: 6, // 머리 최상단 위 6 화면 px
  edge: 8,
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
