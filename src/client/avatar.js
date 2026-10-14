// 아바타 합성기.
// - manifest의 layerOrder 순서로 파츠 SVG를 64x96 캔버스에 겹쳐 그린 뒤, 조합+해상도별로 캐시한다.
// - SVG가 없는 파츠는 style-guide 5.3 영역 좌표를 따르는 단색 도형으로 대신 그린다.
// - 좌우 반전은 기준점 x=32(anchor.x) 기준.
import { AVATAR, COLORS, PART_KEYS } from './constants.js';

const OUTLINE_W = 1.5;
const CACHE_MAX = 96;

// ---------------------------------------------------------------------------
// 폴백 도형 (캔버스 좌표 0..64 x 0..96)

const SKIN = { 'skin-light': '#FFE0C8', 'skin-tan': '#F5C29A', 'skin-dark': '#D9996A' };
const HAIR = { black: '#2E2320', chestnut: '#7A4A2B', blonde: '#F2C14E', pink: '#F28AB2' };
const TOP = { 'top-tee-red': '#E8483E', 'top-hoodie-blue': '#4D7CFE', 'top-vest-green': '#3FB86B' };
const BOTTOM = { 'bottom-shorts-navy': '#2F3E6B', 'bottom-jeans-blue': '#4A6FA5', 'bottom-skirt-pink': '#F79AC0' };
const SHOE = '#6B4226';
const WHITE_SHIRT = '#F7F3EA';
const BLUSH = 'rgba(255,159,176,0.8)';

function rr(c, x, y, w, h, r) {
  c.beginPath();
  c.roundRect(x, y, w, h, r);
}

function fillStroke(c, fill) {
  c.fillStyle = fill;
  c.fill();
  c.stroke();
}

function drawSkin(c, id) {
  const col = SKIN[id] || SKIN['skin-light'];
  rr(c, 24, 66, 7, 18, 2); fillStroke(c, col);
  rr(c, 33, 66, 7, 18, 2); fillStroke(c, col);
  rr(c, 13, 47, 8, 16, 4); fillStroke(c, col);
  rr(c, 43, 47, 8, 16, 4); fillStroke(c, col);
  c.beginPath(); c.arc(17, 65, 3.5, 0, Math.PI * 2); fillStroke(c, col);
  c.beginPath(); c.arc(47, 65, 3.5, 0, Math.PI * 2); fillStroke(c, col);
  rr(c, 21, 46, 22, 22, 6); fillStroke(c, col);
  c.fillStyle = col; c.fillRect(28, 42, 8, 6);
  c.beginPath(); c.moveTo(28, 42); c.lineTo(28, 47); c.moveTo(36, 42); c.lineTo(36, 47); c.stroke();
  rr(c, 16, 8, 32, 36, 14); fillStroke(c, col);
}

function drawBottom(c, id) {
  const col = BOTTOM[id] || BOTTOM['bottom-shorts-navy'];
  if (id === 'bottom-jeans-blue') {
    rr(c, 22, 63, 20, 21, 2); fillStroke(c, col);
    c.beginPath(); c.lineWidth = 1; c.moveTo(32, 66); c.lineTo(32, 84); c.stroke(); c.lineWidth = OUTLINE_W;
  } else if (id === 'bottom-skirt-pink') {
    c.beginPath(); c.moveTo(23, 63); c.lineTo(41, 63); c.lineTo(45, 78); c.lineTo(19, 78); c.closePath(); fillStroke(c, col);
  } else {
    rr(c, 22, 63, 20, 14, 3); fillStroke(c, col);
  }
  for (const x of [23, 32]) {
    c.beginPath(); c.roundRect(x, 83, 9, 9, [2, 2, 3, 3]); fillStroke(c, SHOE);
  }
}

function drawTop(c, id) {
  if (id === 'top-hoodie-blue') {
    const col = TOP[id];
    rr(c, 12, 46, 10, 16, 4); fillStroke(c, col);
    rr(c, 42, 46, 10, 16, 4); fillStroke(c, col);
    rr(c, 20, 45, 24, 24, 6); fillStroke(c, col);
    c.beginPath(); c.lineWidth = 1; c.moveTo(32, 48); c.lineTo(32, 69); c.stroke(); c.lineWidth = OUTLINE_W;
  } else if (id === 'top-vest-green') {
    rr(c, 21, 46, 22, 21, 5); fillStroke(c, TOP[id]);
    c.fillStyle = WHITE_SHIRT; c.fillRect(27, 46.8, 10, 19.4);
    c.beginPath(); c.moveTo(27, 47); c.lineTo(27, 66); c.moveTo(37, 47); c.lineTo(37, 66); c.stroke();
  } else {
    const col = TOP[id] || TOP['top-tee-red'];
    rr(c, 13, 46, 9, 11, 3); fillStroke(c, col);
    rr(c, 42, 46, 9, 11, 3); fillStroke(c, col);
    rr(c, 21, 45, 22, 22, 5); fillStroke(c, col);
  }
}

function drawEyes(c, id) {
  c.fillStyle = BLUSH;
  for (const x of [21.5, 42.5]) { c.beginPath(); c.arc(x, 36, 2.2, 0, Math.PI * 2); c.fill(); }
  c.fillStyle = COLORS.outline;
  for (const x of [25, 39]) {
    if (id === 'eyes-round') {
      c.beginPath(); c.ellipse(x, 31, 2.6, 3.4, 0, 0, Math.PI * 2); c.fill();
      c.fillStyle = '#FFFFFF'; c.beginPath(); c.arc(x + 0.9, 31 - 1.3, 0.9, 0, Math.PI * 2); c.fill();
      c.fillStyle = COLORS.outline;
    } else if (id === 'eyes-happy') {
      c.beginPath(); c.lineWidth = 1.8; c.lineCap = 'round';
      c.arc(x, 32.5, 3, Math.PI * 1.15, Math.PI * 1.85); c.stroke();
      c.lineWidth = OUTLINE_W;
    } else {
      c.beginPath(); c.arc(x, 31, 2.2, 0, Math.PI * 2); c.fill();
    }
  }
}

function drawHair(c, id) {
  const m = /-(black|chestnut|blonde|pink)$/.exec(id || '');
  const col = HAIR[m ? m[1] : 'black'];
  const spiky = /spiky/.test(id || '');
  const sideBottom = spiky ? 36 : 40;
  c.beginPath();
  c.moveTo(12, sideBottom);
  c.lineTo(12, 20);
  if (spiky) {
    c.quadraticCurveTo(12, 8, 18, 6);
    c.lineTo(20, 1); c.lineTo(25, 5); c.lineTo(32, 0); c.lineTo(39, 5); c.lineTo(44, 1);
    c.lineTo(46, 6);
    c.quadraticCurveTo(52, 8, 52, 20);
  } else {
    c.bezierCurveTo(12, 6, 22, 2, 32, 2);
    c.bezierCurveTo(42, 2, 52, 6, 52, 20);
  }
  c.lineTo(52, sideBottom);
  c.lineTo(46, sideBottom);
  c.lineTo(46, 24.5);
  c.lineTo(18, 24.5);
  c.lineTo(18, sideBottom);
  c.closePath();
  fillStroke(c, col);
}

const FALLBACK = { skin: drawSkin, bottom: drawBottom, top: drawTop, eyes: drawEyes, hair: drawHair };

// ---------------------------------------------------------------------------

function makeCanvas(w, h) {
  if (typeof OffscreenCanvas !== 'undefined') return new OffscreenCanvas(w, h);
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  return c;
}

export function createAvatarRenderer(assets) {
  const cache = new Map();
  const cw = assets.canvas.w || AVATAR.w;
  const chh = assets.canvas.h || AVATAR.h;
  const ax = assets.anchor.x;
  const ay = assets.anchor.y;

  function compose(avatar, k) {
    const w = Math.max(1, Math.ceil(cw * k));
    const hgt = Math.max(1, Math.ceil(chh * k));
    const cv = makeCanvas(w, hgt);
    const c = cv.getContext('2d');
    c.scale(w / cw, hgt / chh);
    c.lineJoin = 'round';
    c.lineCap = 'round';
    for (const part of assets.layerOrder) {
      const id = avatar[part];
      const img = assets.images.get(`${part}/${id}`);
      c.save();
      if (img) {
        c.drawImage(img, 0, 0, cw, chh);
      } else {
        c.strokeStyle = COLORS.outline;
        c.lineWidth = OUTLINE_W;
        FALLBACK[part](c, id);
      }
      c.restore();
    }
    return cv;
  }

  function bitmap(avatar, k) {
    const key = PART_KEYS.map((p) => avatar[p]).join('|') + '@' + k.toFixed(3);
    let bmp = cache.get(key);
    if (bmp) {
      cache.delete(key);
      cache.set(key, bmp);
      return bmp;
    }
    bmp = compose(avatar, k);
    cache.set(key, bmp);
    if (cache.size > CACHE_MAX) cache.delete(cache.keys().next().value);
    return bmp;
  }

  return {
    /**
     * @param ctx  CSS px 좌표계 컨텍스트(이미 dpr 변환 적용)
     * @param avatar 정제된 아바타
     * @param sx,sy 기준점(발 중앙)의 화면 CSS px 좌표
     * @param scale 아바타 1 캔버스 px 당 CSS px
     * @param dpr devicePixelRatio
     * @param facingLeft 왼쪽을 보면 true
     */
    draw(ctx, avatar, sx, sy, scale, dpr, facingLeft) {
      const bmp = bitmap(avatar, scale * dpr);
      ctx.save();
      if (facingLeft) {
        ctx.translate(sx, 0);
        ctx.scale(-1, 1);
        ctx.translate(-sx, 0);
      }
      ctx.drawImage(bmp, sx - ax * scale, sy - ay * scale, cw * scale, chh * scale);
      ctx.restore();
    },
    clear() {
      cache.clear();
    },
    get cacheSize() {
      return cache.size;
    },
  };
}
