// 아바타 합성기 (ARCHITECTURE 픽셀아트 계약, style-guide 5장).
// - manifest의 layerOrder 순서로 파츠 PNG 시트(가로 한 줄, 프레임 32x48)를 한 장의 시트로 합성해 조합별로 캐시한다.
// - 좌우 반전 시트도 함께 캐시한다 (프레임마다 열 c -> w-1-c, 기준점 x=16은 그대로).
// - PNG가 없는 파츠는 style-guide 5.2/5.3 좌표를 따르는 단색 도형으로 대신 그린다.
// - 그리기는 아트 해상도 캔버스(1px = 아트 1px, 스무딩 끔)에 한다. 확대는 호출 쪽이 정수 배율로 한다.
import { PAL, PART_KEYS } from './constants.js';

const CACHE_MAX = 64;

// ---------------------------------------------------------------------------
// 폴백 도형 (프레임 좌표, 32x48)

const SKIN = {
  'skin-light': [PAL.s1, PAL.s2, PAL.w2],
  'skin-tan': [PAL.s2, PAL.s3, PAL.w3],
  'skin-dark': [PAL.w2, PAL.w3, PAL.w4],
};
const HAIR = {
  black: [PAL.hb2, PAL.ink], chestnut: [PAL.w3, PAL.w4], blonde: [PAL.y2, PAL.y4], pink: [PAL.p2, PAL.p3], mint: [PAL.m2, PAL.m3],
};
const TOP = {
  'top-tee-red': [PAL.r2, PAL.r3, false], 'top-hoodie-blue': [PAL.u2, PAL.u3, true],
  'top-overalls-blue': [PAL.c1, PAL.c3, false], 'top-cape-mushroom': [PAL.r2, PAL.r3, true],
};
const BOTTOM = {
  'bottom-shorts-navy': [PAL.u4, PAL.ink], 'bottom-jeans-blue': [PAL.u2, PAL.u3],
  'bottom-skirt-pink': [PAL.p2, PAL.p3], 'bottom-pumpkin-green': [PAL.g2, PAL.g4],
};

// 프레임별 몸 위치 (style-guide 5.3 요약): dy, 앞다리 x, 뒷다리 x, 들린 다리('L'|'M'|null), 앞손 x, 뒷손 x
const POSE = [
  { dy: 0, L: 12, M: 16, lift: null, H: 10, h: 20 },
  { dy: 1, L: 12, M: 16, lift: null, H: 10, h: 20 },
  { dy: 0, L: 15, M: 9, lift: null, H: 7, h: 21 },
  { dy: -1, L: 13, M: 15, lift: 'M', H: 10, h: 20 },
  { dy: 0, L: 9, M: 15, lift: null, H: 14, h: 9 },
  { dy: -1, L: 12, M: 15, lift: 'L', H: 10, h: 20 },
];

function box(c, x, y, w, h, line, fill) {
  c.fillStyle = line;
  c.fillRect(x, y, w, h);
  if (fill && w > 2 && h > 2) {
    c.fillStyle = fill;
    c.fillRect(x + 1, y + 1, w - 2, h - 2);
  }
}

function legRange(p, which) {
  const lifted = p.lift === which;
  return { x: p[which], top: 34 + p.dy, bottom: lifted ? 40 : 42 };
}

function drawSkin(c, id, p) {
  const [base, shade, line] = SKIN[id] || SKIN['skin-light'];
  const dy = p.dy;
  const back = legRange(p, 'M');
  const front = legRange(p, 'L');
  box(c, p.h, 26 + dy, 3, 7, line, shade); // 뒷팔
  box(c, back.x, back.top, 3, back.bottom - back.top + 4, line, shade); // 뒷다리
  box(c, 11, 25 + dy, 9, 9, line, base); // 몸통
  box(c, front.x, front.top, 3, front.bottom - front.top + 4, line, base); // 앞다리
  box(c, 7, 8 + dy, 18, 17, line, base); // 두상
  c.fillStyle = shade;
  c.fillRect(8, 12 + dy, 1, 9);
  c.fillStyle = line;
  c.fillRect(18, 22 + dy, 2, 1); // 입
  box(c, p.H, 26 + dy, 3, 7, line, base); // 앞팔
}

function drawBottom(c, id, p) {
  const [base, line] = BOTTOM[id] || BOTTOM['bottom-shorts-navy'];
  const dy = p.dy;
  const shoe = id === 'bottom-skirt-pink' ? [PAL.r2, PAL.r3] : [PAL.w3, PAL.w4];
  const back = legRange(p, 'M');
  const front = legRange(p, 'L');
  if (id === 'bottom-skirt-pink') {
    box(c, 10, 31 + dy, 11, 6, line, base);
  } else {
    const rows = id === 'bottom-jeans-blue' ? 9 : id === 'bottom-pumpkin-green' ? 3 : 4;
    const wide = id === 'bottom-pumpkin-green' ? 1 : 0;
    box(c, back.x - wide, back.top, 3 + wide * 2, Math.min(rows, back.bottom - back.top + 1), line, base);
    box(c, 11, 31 + dy, 9, 4, line, base);
    box(c, front.x - wide, front.top, 3 + wide * 2, Math.min(rows, front.bottom - front.top + 1), line, base);
  }
  box(c, back.x, back.bottom + 1, 4, 3, shoe[1], shoe[0]);
  box(c, front.x, front.bottom + 1, 4, 3, shoe[1], shoe[0]);
}

function drawTop(c, id, p) {
  const [base, line, longSleeve] = TOP[id] || TOP['top-tee-red'];
  const dy = p.dy;
  box(c, p.h, 26 + dy, 3, longSleeve ? 5 : 3, line, base);
  box(c, 11, 25 + dy, 9, 8, line, base);
  if (id === 'top-overalls-blue') box(c, 13, 29 + dy, 6, 4, PAL.u3, PAL.u2);
  if (id === 'top-cape-mushroom') { c.fillStyle = PAL.c1; c.fillRect(13, 27 + dy, 1, 1); c.fillRect(17, 28 + dy, 1, 1); }
  box(c, p.H, 26 + dy, 3, longSleeve ? 5 : 3, line, base);
}

function drawEyes(c, id, p) {
  const dy = p.dy;
  c.fillStyle = PAL.w4;
  c.fillRect(14, 15 + dy, 2, 1);
  c.fillRect(19, 15 + dy, 2, 1);
  c.fillStyle = PAL.ink;
  if (id === 'eyes-happy') {
    c.fillRect(14, 18 + dy, 1, 1); c.fillRect(15, 17 + dy, 1, 1);
    c.fillRect(19, 17 + dy, 1, 1); c.fillRect(20, 18 + dy, 1, 1);
  } else if (id === 'eyes-sleepy') {
    c.fillRect(13, 18 + dy, 3, 1); c.fillRect(19, 18 + dy, 3, 1);
  } else {
    c.fillRect(14, 16 + dy, 2, 3); c.fillRect(19, 16 + dy, 2, 3);
    c.fillStyle = PAL.white;
    c.fillRect(15, 17 + dy, 1, 1); c.fillRect(20, 17 + dy, 1, 1);
  }
  c.fillStyle = PAL.p2;
  c.fillRect(13, 21 + dy, 1, 1);
  c.fillRect(21, 21 + dy, 2, 1);
}

function drawHair(c, id, p) {
  const m = /-(black|chestnut|blonde|pink|mint)$/.exec(id || '');
  const [base, line] = HAIR[m ? m[1] : 'black'];
  const dy = p.dy;
  const shape = /long/.test(id || '') ? 'long' : /spiky/.test(id || '') ? 'spiky' : 'round';
  box(c, 5, 4 + dy, 22, 11, line, base); // 정수리와 앞머리
  box(c, 5, 10 + dy, 7, shape === 'long' ? 18 : shape === 'round' ? 12 : 7, line, base); // 뒷머리
  box(c, 24, 10 + dy, 3, shape === 'spiky' ? 5 : 9, line, base); // 앞 옆머리
  if (shape === 'spiky') {
    c.fillStyle = line;
    for (const x of [10, 17, 23]) c.fillRect(x, 2 + dy, 1, 2);
  }
}

const FALLBACK = { skin: drawSkin, bottom: drawBottom, top: drawTop, eyes: drawEyes, hair: drawHair };

// ---------------------------------------------------------------------------

export function makeCanvas(w, h) {
  if (typeof OffscreenCanvas !== 'undefined') return new OffscreenCanvas(w, h);
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  return c;
}

/** 아이디 문자열 기반 0..499ms 위상 (style-guide 5.11: idle이 다 같이 숨쉬지 않게) */
export function idleOffset(userId) {
  let x = 2166136261;
  const s = String(userId || '');
  for (let i = 0; i < s.length; i++) { x ^= s.charCodeAt(i); x = Math.imul(x, 16777619); }
  return (x >>> 0) % 500;
}

export function createAvatarRenderer(assets) {
  const cache = new Map(); // key -> { normal, flipped }
  const fw = assets.frame.w;
  const fh = assets.frame.h;
  const ax = assets.anchor.x;
  const ay = assets.anchor.y;
  const frameCount = assets.frameCount;
  const anims = assets.animations;

  function compose(avatar) {
    const sheet = makeCanvas(fw * frameCount, fh);
    const c = sheet.getContext('2d');
    c.imageSmoothingEnabled = false;
    for (const part of assets.layerOrder) {
      const id = avatar[part];
      const img = assets.images.get(`${part}/${id}`);
      if (img) {
        // 시트 프레임 수가 부족하면 있는 프레임만 반복해서 쓴다
        const have = Math.max(1, Math.floor(img.naturalWidth / fw));
        for (let f = 0; f < frameCount; f++) c.drawImage(img, (f % have) * fw, 0, fw, fh, f * fw, 0, fw, fh);
      } else {
        for (let f = 0; f < frameCount; f++) {
          c.save();
          c.translate(f * fw, 0);
          c.beginPath();
          c.rect(0, 0, fw, fh);
          c.clip();
          FALLBACK[part](c, id, POSE[f % POSE.length]);
          c.restore();
        }
      }
    }
    const flipped = makeCanvas(fw * frameCount, fh);
    const fc = flipped.getContext('2d');
    fc.imageSmoothingEnabled = false;
    for (let f = 0; f < frameCount; f++) {
      fc.save();
      fc.translate((f + 1) * fw, 0);
      fc.scale(-1, 1);
      fc.drawImage(sheet, f * fw, 0, fw, fh, 0, 0, fw, fh);
      fc.restore();
    }
    return { normal: sheet, flipped };
  }

  function sheets(avatar) {
    const key = PART_KEYS.map((p) => avatar[p]).join('|');
    let s = cache.get(key);
    if (s) {
      cache.delete(key);
      cache.set(key, s);
      return s;
    }
    s = compose(avatar);
    cache.set(key, s);
    if (cache.size > CACHE_MAX) cache.delete(cache.keys().next().value);
    return s;
  }

  return {
    frameW: fw,
    frameH: fh,
    anchorX: ax,
    anchorY: ay,
    /** 애니메이션 상태와 경과 시간(ms)으로 프레임 번호를 고른다. */
    frameAt(anim, elapsedMs) {
      const a = anims[anim] || anims.idle;
      const i = Math.floor(Math.max(0, elapsedMs) / a.ms) % a.frames.length;
      return a.frames[i];
    },
    /**
     * 아트 해상도 컨텍스트에 그린다.
     * @param ctx 아트 px 컨텍스트 (스무딩 끔)
     * @param x,y 기준점(발 중앙)의 아트 px 정수 좌표
     */
    draw(ctx, avatar, x, y, frame, facingLeft) {
      const s = sheets(avatar);
      const f = Math.min(frameCount - 1, Math.max(0, frame | 0));
      ctx.drawImage(facingLeft ? s.flipped : s.normal, f * fw, 0, fw, fh, x - (facingLeft ? fw - ax : ax), y - ay, fw, fh);
    },
    clear() {
      cache.clear();
    },
    get cacheSize() {
      return cache.size;
    },
  };
}
