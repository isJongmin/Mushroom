// 아바타 렌더러 (ARCHITECTURE "블록 아트 계약", 사이클 3).
// 파이프라인:
//   1. 합성: manifest layerOrder(hair_back → skin → face → bottom → shoes → top → hair_front → hat) 순서로
//      레이어 PNG 시트(48x64 x 7프레임 = 336x64)를 한 장에 겹친다. hat "none"과 불러오지 못한 레이어는 뺀다.
//   2. 외곽선: 합성 결과의 투명 픽셀 중 4방향 이웃(아래, 왼쪽, 오른쪽, 위 순)에 불투명 픽셀이 있으면
//      그 이웃 색을 outline.json 으로 바꾼 색(없으면 RGB x0.45)으로 칠한다. 이웃은 같은 프레임 안에서만 본다.
//   3. 반전: 왼쪽 보기용으로 프레임마다 좌우 반전한 시트를 만든다(외곽선까지 끝난 결과를 뒤집는다).
//   외형 조합(7개 id)마다 1회 계산해 LRU 캐시에 둔다. 썸네일(생성 화면)은 같은 1~2단계를 front 프레임 하나에만 한다.
// 그리기는 아트 해상도 컨텍스트(1px = 아트 1px, 스무딩 끔)에 한다. 확대는 호출 쪽이 정수 배율로 한다.
import { PAL, PART_KEYS, LAYER_PART, HAT_NONE } from './constants.js';

const SHEET_CACHE_MAX = 64;
const THUMB_CACHE_MAX = 256;
const DARKEN = 0.45;

export function makeCanvas(w, h) {
  if (typeof OffscreenCanvas !== 'undefined') return new OffscreenCanvas(w, h);
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  return c;
}

function ctx2d(cv, readback) {
  const c = cv.getContext('2d', readback ? { willReadFrequently: true } : undefined);
  c.imageSmoothingEnabled = false;
  return c;
}

/**
 * 합성 결과에 바깥 실루엣 1px 외곽선을 그린다 (제자리 수정).
 * @param cv 프레임을 가로로 이어 붙인 캔버스 (프레임 폭 fw)
 * @param outline Map<0xRRGGBB, [r,g,b]>
 */
export function applySilhouetteOutline(cv, fw, outline) {
  const W = cv.width;
  const H = cv.height;
  const c = ctx2d(cv, true);
  const img = c.getImageData(0, 0, W, H);
  const src = img.data;
  const dst = new Uint8ClampedArray(src); // 원본(src)만 보고 판단한다 (새로 칠한 외곽선은 이웃으로 보지 않음)
  const frames = Math.floor(W / fw);
  const DIRS = [[0, 1], [-1, 0], [1, 0], [0, -1]]; // 아래, 왼쪽, 오른쪽, 위
  for (let f = 0; f < frames; f++) {
    const x0 = f * fw;
    for (let y = 0; y < H; y++) {
      for (let x = 0; x < fw; x++) {
        const i = (y * W + x0 + x) * 4;
        if (src[i + 3] !== 0) continue;
        for (const [dx, dy] of DIRS) {
          const nx = x + dx;
          const ny = y + dy;
          if (nx < 0 || nx >= fw || ny < 0 || ny >= H) continue;
          const j = (ny * W + x0 + nx) * 4;
          if (src[j + 3] === 0) continue;
          const key = (src[j] << 16) | (src[j + 1] << 8) | src[j + 2];
          const line = outline.get(key);
          if (line) {
            dst[i] = line[0]; dst[i + 1] = line[1]; dst[i + 2] = line[2];
          } else {
            dst[i] = Math.floor(src[j] * DARKEN); dst[i + 1] = Math.floor(src[j + 1] * DARKEN); dst[i + 2] = Math.floor(src[j + 2] * DARKEN);
          }
          dst[i + 3] = 255;
          break;
        }
      }
    }
  }
  img.data.set(dst);
  c.putImageData(img, 0, 0);
}

// ---------------------------------------------------------------------------
// 대체 아바타: 매니페스트가 아예 없을 때만 쓰는 단순 블록 인형 (프레임 48x64, 기준점 24,60 기준)

function drawFallbackFrame(c, fi, frameNames) {
  const name = frameNames[fi] || 'side_idle';
  const walk = /^side_walk(\d)$/.exec(name);
  const step = walk ? [2, 0, -2, 0][Number(walk[1]) % 4] : 0;
  c.fillStyle = PAL.u4; // 다리
  c.fillRect(19 - step, 48, 4, 12);
  c.fillRect(25 + step, 48, 4, 12);
  c.fillStyle = PAL.hb2; // 몸통
  c.fillRect(17, 34, 14, 15);
  c.fillStyle = PAL.s1; // 머리
  c.fillRect(14, 14, 20, 20);
  c.fillStyle = PAL.hb2; // 머리카락
  c.fillRect(13, 10, 22, 6);
  if (name !== 'back') {
    c.fillStyle = PAL.ink;
    const ex = name === 'front' ? 19 : 25;
    c.fillRect(ex, 23, 2, 3);
    c.fillRect(ex + 7, 23, 2, 3);
  } else {
    c.fillStyle = PAL.hb2;
    c.fillRect(14, 16, 20, 12);
  }
}

// ---------------------------------------------------------------------------

/** 아바타의 레이어 목록 [[layer, id], ...] (layerOrder 순서). onlyParts가 있으면 그 파츠만. */
export function layersOf(assets, avatar, onlyParts) {
  const out = [];
  for (const layer of assets.layerOrder) {
    const part = LAYER_PART[layer];
    if (onlyParts && !onlyParts.includes(part)) continue;
    const id = avatar[part];
    if (typeof id !== 'string' || (part === 'hat' && id === HAT_NONE)) continue;
    out.push([layer, id]);
  }
  return out;
}

export function createAvatarRenderer(assets) {
  const fw = assets.frame.w;
  const fh = assets.frame.h;
  const ax = assets.anchor.x;
  const ay = assets.anchor.y;
  const frameCount = assets.frameCount;
  const anims = assets.animations;
  const sheetCache = new Map(); // key -> { normal, flipped }
  const thumbCache = new Map(); // key -> canvas (fw x fh, front 프레임 1장)

  const lru = (map, max, key, make) => {
    let v = map.get(key);
    if (v) { map.delete(key); map.set(key, v); return v; }
    v = make();
    map.set(key, v);
    if (map.size > max) map.delete(map.keys().next().value);
    return v;
  };

  /** layers를 frames(프레임 번호 배열) 위치에 합성 + 외곽선 */
  function composeLayers(layers, frames) {
    const cv = makeCanvas(fw * frames.length, fh);
    const c = ctx2d(cv, true);
    if (assets.source === 'fallback') {
      frames.forEach((f, k) => {
        c.save();
        c.translate(k * fw, 0);
        drawFallbackFrame(c, f, assets.frameNames);
        c.restore();
      });
    } else {
      for (const [layer, id] of layers) {
        const img = assets.images.get(`${layer}/${id}`);
        if (!img) continue; // 실패한 레이어는 빼고 그린다
        const have = Math.max(1, Math.floor(img.naturalWidth / fw));
        frames.forEach((f, k) => c.drawImage(img, (f % have) * fw, 0, fw, fh, k * fw, 0, fw, fh));
      }
    }
    applySilhouetteOutline(cv, fw, assets.outline);
    return cv;
  }

  function buildSheets(avatar) {
    const all = Array.from({ length: frameCount }, (_, i) => i);
    const normal = composeLayers(layersOf(assets, avatar), all);
    const flipped = makeCanvas(normal.width, fh);
    const fc = ctx2d(flipped);
    for (let f = 0; f < frameCount; f++) {
      fc.save();
      fc.translate((f + 1) * fw, 0);
      fc.scale(-1, 1);
      fc.drawImage(normal, f * fw, 0, fw, fh, 0, 0, fw, fh);
      fc.restore();
    }
    return { normal, flipped };
  }

  const keyOf = (avatar) => PART_KEYS.map((p) => avatar[p]).join('|');

  function sheets(avatar) {
    return lru(sheetCache, SHEET_CACHE_MAX, keyOf(avatar), () => buildSheets(avatar));
  }

  return {
    frameW: fw,
    frameH: fh,
    anchorX: ax,
    anchorY: ay,
    frameIndex: assets.frameIndex,
    /** 애니메이션 이름과 경과 시간(ms)으로 시트 프레임 번호를 고른다. */
    frameAt(anim, elapsedMs) {
      const a = anims[anim] || anims.idle;
      const i = Math.floor(Math.max(0, elapsedMs) / a.ms) % a.frames.length;
      return a.frames[i];
    },
    /** 미리 합성해 둔다(첫 그리기 끊김 방지). */
    warm(avatar) {
      sheets(avatar);
    },
    /**
     * 아트 해상도 컨텍스트에 그린다.
     * @param x,y 기준점(두 발 사이 바닥 중앙)의 아트 px 정수 좌표
     * @param facingLeft true면 반전 시트 (기준점 x 기준 좌우 반전)
     */
    draw(ctx, avatar, x, y, frame, facingLeft) {
      const s = sheets(avatar);
      const f = Math.min(frameCount - 1, Math.max(0, frame | 0));
      const left = facingLeft ? x - (fw - ax) : x - ax;
      ctx.drawImage(facingLeft ? s.flipped : s.normal, f * fw, 0, fw, fh, left, y - ay, fw, fh);
    },
    /**
     * 썸네일용: front 프레임에 지정 파츠 레이어만 합성 + 외곽선한 fw x fh 캔버스 (캐시).
     * @param avatar 7개 키 아바타
     * @param onlyParts 합성할 파츠 목록 (style-guide 5.12 표)
     */
    thumb(avatar, onlyParts) {
      const layers = layersOf(assets, avatar, onlyParts);
      const key = `${assets.frameIndex.front}:${layers.map((l) => l.join('/')).join('|')}`;
      return lru(thumbCache, THUMB_CACHE_MAX, key, () => composeLayers(layers, [assets.frameIndex.front]));
    },
    clear() {
      sheetCache.clear();
      thumbCache.clear();
    },
    get cacheSize() {
      return sheetCache.size;
    },
  };
}
