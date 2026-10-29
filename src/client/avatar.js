// 아바타 렌더러 (ARCHITECTURE "복셀 아트 계약", 사이클 5).
// 파이프라인:
//   1. 지연 로드: 조합(7개 id)이 처음 필요할 때 manifest layerOrder의 레이어 중 파일이 있는 것만
//      assets.getLayer로 받는다(파일 존재는 assets.hasLayer, 404 없음). 실패한 레이어는 빼고 합성한다.
//   2. 합성: 조합 전용 투명 오프스크린(1152x192 = 8프레임)에 layerOrder 순서로 시트를 통째로 그린다.
//      entry.blend = 'source-over' | 'source-atop'(shade_* 그림자: 지금까지 그린 픽셀에만 덮임).
//      기준 구현은 assets/_src/voxel/build.py composite() (프런트 결과와 픽셀 비교, handoff 참고).
//   3. 반전(왼쪽 보기): 프레임마다 좌우 반전한 시트를 처음 필요할 때 만든다(프레임 중심 x = 기준점 x).
//   4. 머리 위 높이: idle 프레임의 맨 위 불투명 행 → 기준점에서 월드 몇 단위 위인지(headTop, 말풍선 위치).
//   외형 조합마다 1회 계산해 LRU 캐시에 둔다. 썸네일은 front 프레임 하나에 지정 파츠만 합성한다(별도 LRU).
// 그리기: 호출 쪽 컨텍스트(백킹 해상도)에 고품질 스무딩으로 바로 그린다. 크기 = 시트 px / density x 배율.
// 외곽선 없음 (이전 1px 실루엣 외곽선과 outline.json은 폐기).
import { PAL, PART_KEYS, HEAD } from './constants.js';

// 1152x192 RGBA ≈ 0.88MB. 반전 시트까지 최대 약 1.8MB/조합. 방 최대 20명 + 프로필/로비 미리보기 여유.
const SHEET_CACHE_MAX = 48;
// 썸네일 캔버스는 프레임 1장(144x192 ≈ 0.1MB). 슬롯 최대 8 x 탭 7 + 프리셋 6 + 로비 1.
const THUMB_CACHE_MAX = 72;
const ALPHA_TOP = 8; // 머리 위 높이 계산 때 불투명으로 보는 알파

export function makeCanvas(w, h) {
  if (typeof OffscreenCanvas !== 'undefined') return new OffscreenCanvas(w, h);
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  return c;
}

/** 고품질 스무딩 설정 (복셀 계약: imageSmoothingEnabled = true, quality 'high') */
export function smooth(ctx) {
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';
  return ctx;
}

/** 아바타의 레이어 목록 [{layer, part, blend, id}] (layerOrder 순서, 파일이 있는 것만). onlyParts가 있으면 그 파츠만. */
export function layersOf(assets, avatar, onlyParts) {
  const out = [];
  for (const e of assets.layerOrder) {
    if (onlyParts && !onlyParts.includes(e.part)) continue;
    const id = avatar[e.part];
    if (!assets.hasLayer(e.layer, id)) continue;
    out.push({ layer: e.layer, part: e.part, blend: e.blend, id });
  }
  return out;
}

/**
 * @param assets loadAvatarAssets() 결과
 * @param opts.onUpdate 합성이 끝날 때마다(여러 개는 한 번으로 묶어) 부른다. 화면이 다시 그리는 용도.
 */
export function createAvatarRenderer(assets, opts = {}) {
  const fw = assets.frame.w;
  const fh = assets.frame.h;
  const ax = assets.anchor.x;
  const ay = assets.anchor.y;
  const density = assets.density;
  const frameCount = assets.frameCount;
  const anims = assets.animations;
  const idleFrame = (anims.idle && anims.idle.frames[0]) || 0;
  const sheetCache = new Map(); // key -> entry { state: 'loading'|'ready', normal, flipped, headTop }
  const thumbCache = new Map(); // key -> entry { state, canvas }
  let gen = 0; // clear() 이후 끝난 합성은 버린다
  let onUpdate = typeof opts.onUpdate === 'function' ? opts.onUpdate : null;
  let notifyQueued = false;
  const stats = { composites: 0, totalMs: 0, maxMs: 0, lastMs: 0 };

  function notify() {
    if (notifyQueued || !onUpdate) return;
    notifyQueued = true;
    queueMicrotask(() => { notifyQueued = false; if (onUpdate) onUpdate(); });
  }

  const touch = (map, key) => {
    const v = map.get(key);
    if (v) { map.delete(key); map.set(key, v); }
    return v;
  };
  const evict = (map, max) => {
    while (map.size > max) map.delete(map.keys().next().value);
  };

  /** 레이어를 frames 위치(프레임 번호 배열)에 합성. 레이어 받기가 끝나야 resolve. */
  async function compose(layers, frames) {
    const imgs = await Promise.all(layers.map((l) => assets.getLayer(l.layer, l.id)));
    // 모자 안쪽 머리카락은 챙 아래부터만 그린다. 리본은 머리를 덮지 않는다.
    // 합성에 실제 모자가 포함될 때만 적용하므로 헤어 선택 썸네일은 유지한다.
    const hatIndexes = layers.map((l, i) => l.part === 'hat' && l.id !== 'ribbon-pink' ? i : -1).filter((i) => i >= 0 && imgs[i]);
    let hairTops = null;
    if (hatIndexes.length) {
      const mask = makeCanvas(fw, fh);
      const mc = mask.getContext('2d');
      hairTops = frames.map((f) => {
        mc.clearRect(0, 0, fw, fh);
        for (const i of hatIndexes) {
          if (layers[i].blend !== 'source-over') continue;
          const img = imgs[i];
          const have = Math.max(1, Math.floor(img.naturalWidth / fw));
          mc.drawImage(img, (f % have) * fw, 0, fw, fh, 0, 0, fw, fh);
        }
        const data = mc.getImageData(0, 0, fw, fh).data;
        // 챙은 기울어져 있으므로 전역 최하단 대신 열별 경계를 사용한다.
        // 3px 겹침으로 안티앨리어싱 경계의 투명한 틈도 채운다.
        const tops = Array(fw).fill(null);
        for (let x = 0; x < fw; x++) {
          for (let y = fh - 1; y >= 0; y--) {
            if (data[(y * fw + x) * 4 + 3] > 32) { tops[x] = Math.max(0, y - 3); break; }
          }
        }
        const occupied = tops.map((v, x) => v === null ? -1 : x).filter((x) => x >= 0);
        if (!occupied.length) return Array(fw).fill(0);
        for (let x = 0; x < fw; x++) if (tops[x] === null) {
          let nearest = occupied[0];
          for (const j of occupied) if (Math.abs(j - x) < Math.abs(nearest - x)) nearest = j;
          tops[x] = tops[nearest];
        }
        return tops;
      });
    }
    const t0 = performance.now();
    const all = frames.length === frameCount && frames.every((f, i) => f === i);
    const cv = makeCanvas(fw * frames.length, fh);
    const c = cv.getContext('2d');
    c.imageSmoothingEnabled = false; // 1:1 복사
    for (let i = 0; i < layers.length; i++) {
      const img = imgs[i];
      if (!img) continue; // 받지 못한 레이어는 빼고 그린다
      c.save();
      if (hairTops && layers[i].part === 'hair') {
        c.beginPath();
        hairTops.forEach((tops, k) => tops.forEach((top, x) => c.rect(k * fw + x, top, 1, fh - top)));
        c.clip();
      }
      c.globalCompositeOperation = layers[i].blend;
      if (all && img.naturalWidth >= fw * frameCount) {
        c.drawImage(img, 0, 0, fw * frameCount, fh, 0, 0, fw * frameCount, fh);
      } else {
        const have = Math.max(1, Math.floor(img.naturalWidth / fw));
        frames.forEach((f, k) => c.drawImage(img, (f % have) * fw, 0, fw, fh, k * fw, 0, fw, fh));
      }
      c.restore();
      c.globalCompositeOperation = 'source-over';
    }
    return { cv, ms: performance.now() - t0 };
  }

  function headTopOf(cv, frame = idleFrame) {
    try {
      const c = cv.getContext('2d');
      const data = c.getImageData(frame * fw, 0, fw, fh).data;
      for (let y = 0; y < fh; y++) {
        for (let x = 0; x < fw; x++) if (data[(y * fw + x) * 4 + 3] > ALPHA_TOP) return (ay - y) / density;
      }
    } catch { /* 읽기 실패: 기본값 */ }
    return HEAD.fallback;
  }

  function flipSheet(normal) {
    const flipped = makeCanvas(normal.width, fh);
    const c = flipped.getContext('2d');
    c.imageSmoothingEnabled = false;
    for (let f = 0; f < frameCount; f++) {
      c.setTransform(-1, 0, 0, 1, (f + 1) * fw, 0);
      c.drawImage(normal, f * fw, 0, fw, fh, 0, 0, fw, fh);
    }
    c.setTransform(1, 0, 0, 1, 0, 0);
    return flipped;
  }

  const keyOf = (avatar) => PART_KEYS.map((p) => avatar[p]).join('|');

  /** 조합 시트 엔트리 (없으면 합성 시작) */
  function request(avatar) {
    const key = keyOf(avatar);
    let e = touch(sheetCache, key);
    if (e) return e;
    e = { state: 'loading', normal: null, flipped: null, headTop: HEAD.fallback, promise: null };
    sheetCache.set(key, e);
    evict(sheetCache, SHEET_CACHE_MAX);
    if (assets.source !== 'manifest') {
      e.state = 'ready';
      e.promise = Promise.resolve(e);
      return e;
    }
    const g = gen;
    const all = Array.from({ length: frameCount }, (_, i) => i);
    e.promise = compose(layersOf(assets, avatar), all).then(({ cv, ms }) => {
      if (g !== gen) return e;
      e.normal = cv;
      e.headTop = headTopOf(cv);
      e.state = 'ready';
      stats.composites++;
      stats.totalMs += ms;
      stats.lastMs = ms;
      stats.maxMs = Math.max(stats.maxMs, ms);
      notify();
      return e;
    }, () => {
      e.state = 'ready'; // 그릴 것 없음
      return e;
    });
    return e;
  }

  // 매니페스트가 아예 없을 때만 쓰는 단순 인형 (월드 단위, 기준점 원점)
  function drawFallback(ctx, frame, k) {
    const name = assets.frameNames[frame] || 'side';
    const walk = /^walk(\d)$/.exec(name);
    const step = walk ? [4, 0, -4, 0][Number(walk[1]) % 4] : 0;
    const r = (col, x, y, w, h) => { ctx.fillStyle = col; ctx.fillRect(x * k, y * k, w * k, h * k); };
    r(PAL.u4, -10 - step, -24, 8, 24);
    r(PAL.u4, 2 + step, -24, 8, 24);
    r(PAL.hb2, -14, -50, 28, 28);
    r(PAL.s1, -22, -92, 44, 42);
    r(PAL.hb2, -24, -98, 48, 12);
  }

  return {
    frameW: fw,
    frameH: fh,
    density,
    /** 프레임 크기(월드 단위) */
    worldW: fw / density,
    worldH: fh / density,
    frameIndex: assets.frameIndex,
    stats,
    /** 애니메이션 이름과 경과 시간(ms)으로 시트 프레임 번호를 고른다. */
    frameAt(anim, elapsedMs) {
      const a = anims[anim] || anims.idle;
      const i = Math.floor(Math.max(0, elapsedMs) / a.ms) % a.frames.length;
      return a.frames[i];
    },
    /** 합성을 미리 시작한다. 합성이 끝나면 resolve (실패해도 resolve). */
    ready(avatar) {
      return request(avatar).promise;
    },
    isReady(avatar) {
      const e = sheetCache.get(keyOf(avatar));
      return !!e && e.state === 'ready';
    },
    /** 머리(모자 포함) 맨 위가 기준점에서 몇 월드 단위 위인지. 합성 전이면 기본값. */
    headTop(avatar) {
      const e = sheetCache.get(keyOf(avatar));
      return e && e.state === 'ready' ? e.headTop : HEAD.fallback;
    },
    /**
     * (사이클 8) 프레임별 머리 위 높이(프레임 알파 bbox 맨 위). 엎드리기처럼 키가 낮은 프레임의 말풍선 위치용.
     * 조합·프레임마다 1회 계산해 캐시한다. 합성 전이면 idle 기준값.
     */
    headTopFrame(avatar, frame) {
      const e = sheetCache.get(keyOf(avatar));
      if (!e || e.state !== 'ready') return HEAD.fallback;
      const f = frame | 0;
      if (!e.normal || f === idleFrame || f < 0 || f >= frameCount) return e.headTop;
      if (!e.tops) e.tops = new Map();
      let v = e.tops.get(f);
      if (v === undefined) { v = headTopOf(e.normal, f); e.tops.set(f, v); }
      return v;
    },
    /**
     * (사이클 8) 캐릭터 대표 색 [r, g, b]: idle 프레임 몸통 부분(기준점 위 25~60 월드)의 불투명 픽셀 평균. 이펙트 색용.
     * 조합마다 1회 계산. 합성 전이거나 실패하면 null.
     */
    tintOf(avatar) {
      const e = sheetCache.get(keyOf(avatar));
      if (!e || e.state !== 'ready' || !e.normal) return null;
      if (e.tint !== undefined) return e.tint;
      e.tint = null;
      try {
        const y0 = Math.max(0, Math.round(ay - 60 * density));
        const y1 = Math.min(fh, Math.round(ay - 25 * density));
        const data = e.normal.getContext('2d').getImageData(idleFrame * fw, y0, fw, y1 - y0).data;
        let r = 0; let g = 0; let b = 0; let n = 0;
        for (let i = 0; i < data.length; i += 4) {
          if (data[i + 3] < 200) continue;
          r += data[i]; g += data[i + 1]; b += data[i + 2]; n++;
        }
        if (n) e.tint = [Math.round(r / n), Math.round(g / n), Math.round(b / n)];
      } catch { /* 읽기 실패 */ }
      return e.tint;
    },
    /**
     * 기준점(발 중앙 바닥)을 (x, y)에 두고 그린다. 좌표 단위는 ctx의 현재 단위, k = 그 단위 / 월드 1단위.
     * 합성이 아직이면 합성을 시작하고 false (그리지 않음).
     * @param facingLeft true면 반전 시트 (기준점 x 기준 좌우 반전)
     */
    draw(ctx, avatar, x, y, k, frame, facingLeft) {
      const e = request(avatar);
      if (e.state !== 'ready') return false;
      const f = Math.min(frameCount - 1, Math.max(0, frame | 0));
      if (assets.source !== 'manifest') {
        ctx.save();
        ctx.translate(x, y);
        if (facingLeft) ctx.scale(-1, 1);
        drawFallback(ctx, f, k);
        ctx.restore();
        return true;
      }
      if (!e.normal) return false;
      if (facingLeft && !e.flipped) e.flipped = flipSheet(e.normal);
      const s = k / density; // ctx 단위 / 시트 px
      const ox = facingLeft ? fw - ax : ax; // 반전 시트에서 기준점 x
      smooth(ctx);
      ctx.drawImage(facingLeft ? e.flipped : e.normal, f * fw, 0, fw, fh, x - ox * s, y - ay * s, fw * s, fh * s);
      return true;
    },
    /**
     * 썸네일용: front 프레임에 지정 파츠 레이어만 합성한 fw x fh 캔버스 (캐시). 아직이면 합성을 시작하고 null.
     * @param onlyParts 합성할 파츠 목록
     */
    thumb(avatar, onlyParts, frame = assets.frameIndex.front) {
      const layers = layersOf(assets, avatar, onlyParts);
      const key = `${frame}:${layers.map((l) => `${l.layer}/${l.id}`).join('|')}`;
      let e = touch(thumbCache, key);
      if (!e) {
        e = { state: 'loading', canvas: null };
        thumbCache.set(key, e);
        evict(thumbCache, THUMB_CACHE_MAX);
        const g = gen;
        compose(layers, [frame]).then(({ cv }) => {
          if (g !== gen) return;
          e.canvas = cv;
          e.state = 'ready';
          notify();
        }, () => { e.state = 'ready'; });
      }
      return e.canvas;
    },
    setOnUpdate(fn) {
      onUpdate = typeof fn === 'function' ? fn : null;
    },
    clear() {
      gen++;
      onUpdate = null;
      sheetCache.clear();
      thumbCache.clear();
    },
    get cacheSize() {
      return sheetCache.size;
    },
  };
}
