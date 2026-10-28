// (사이클 9) 드롭 아이템: 목록(60초 소멸), 떨어짐·둥실·반짝임 그리기, 아이콘 지연 로드와 대체 그림.
// 아이템 id = "<파츠 키>:<파츠 id>". 아이콘 assets/avatar/icon/<파츠 키>/<id>.png (64x64, 투명, 캐릭터 아트 소유).
// 아이콘이 없으면 (1) 아바타 렌더러 썸네일(그 파츠 레이어만 front 프레임) (2) 그것도 없으면 파츠 색 상자.
import { loadImage } from '../assets.js';
import { parseItem } from './mobs.js';

export const DROP_TTL_MS = 60000;
export const PICK_RANGE = Object.freeze({ x: 44, y: 60 });
const DROP_MAX = 40;
const FALL_MS = 380;
const ICON_WORLD = 30; // 월드 단위 크기

const REPO_ROOT = new URL('../../../', import.meta.url);

// 썸네일 자르기 (시트 px, front 프레임 144x192) — 프로필 화면과 같은 값
export const ITEM_CROP = Object.freeze({
  hat: { x: 16, y: 10, size: 112 },
  hair: { x: 16, y: 26, size: 112 },
  face: { x: 16, y: 26, size: 112 },
  skin: { x: 16, y: 26, size: 112 },
  top: { x: 22, y: 92, size: 100 },
  bottom: { x: 27, y: 104, size: 90 },
  shoes: { x: 32, y: 112, size: 80 },
});
const PART_COLOR = { hat: '#F58AB4', top: '#4D7CFE', bottom: '#3E8A2E', shoes: '#B97A4A', hair: '#F7C948', face: '#FFE3CC', skin: '#F5C29A' };

/** 아이콘 이미지 지연 로드 (없으면 null로 기억해 다시 요청하지 않는다) */
/** allow(item) → false면 요청하지 않는다(아바타 manifest에 없는 파츠: 아이콘도 아직 없다, 404 방지) */
export function createItemIcons({ onLoad, allow } = {}) {
  const map = new Map();
  return {
    get(item) {
      const it = parseItem(item);
      if (!it || (allow && !allow(item))) return null;
      let e = map.get(item);
      if (!e) {
        e = { img: null, state: 'loading' };
        map.set(item, e);
        loadImage(new URL(`assets/avatar/icon/${it.part}/${it.id}.png`, REPO_ROOT)).then((img) => {
          e.img = img;
          e.state = img ? 'ready' : 'none';
          if (img) onLoad?.(item);
        });
      }
      return e.img;
    },
    clear() { map.clear(); },
    get size() { return map.size; },
  };
}

/**
 * 아이템 그림 하나를 (cx, cy) 가운데에 size(ctx 단위) 크기로.
 * thumbFn(item) → { src: canvas, crop } | null (아바타 렌더러 썸네일 대체)
 */
export function drawItemIcon(ctx, item, cx, cy, size, icons, thumbFn) {
  const img = icons ? icons.get(item) : null;
  if (img) { ctx.drawImage(img, cx - size / 2, cy - size / 2, size, size); return 'icon'; }
  const th = thumbFn ? thumbFn(item) : null;
  if (th && th.src) {
    const c = th.crop;
    ctx.drawImage(th.src, c.x, c.y, c.size, c.size, cx - size / 2, cy - size / 2, size, size);
    return 'thumb';
  }
  const it = parseItem(item);
  const col = (it && PART_COLOR[it.part]) || '#C9A47A';
  const s = size * 0.7;
  const x = cx - s / 2;
  const y = cy - s / 2;
  ctx.fillStyle = '#1A1626';
  ctx.fillRect(x - 2, y - 2, s + 4, s + 4);
  ctx.fillStyle = col;
  ctx.fillRect(x, y, s, s);
  ctx.fillStyle = 'rgba(255,255,255,0.55)';
  ctx.fillRect(x, y, s, Math.max(2, s * 0.12));
  ctx.fillStyle = '#FFF2A8';
  ctx.fillRect(cx - s * 0.08, y, s * 0.16, s);
  ctx.fillRect(x, cy - s * 0.08, s, s * 0.16);
  return 'box';
}

/** 드롭 목록. surfaceAt(x, y) → 아래 면 y */
export function createDrops() {
  const map = new Map(); // id -> { id, item, x, y, fromY, at, expires }
  return {
    /** 새 드롭(또는 재전송). ttl = 남은 ms (재전송) */
    add(d, ground, now = performance.now()) {
      if (map.has(d.id)) return false;
      const ttl = typeof d.ttl === 'number' && d.ttl > 0 ? Math.min(DROP_TTL_MS, d.ttl) : DROP_TTL_MS;
      map.set(d.id, { id: d.id, item: d.item, x: d.x, y: ground, fromY: Math.min(ground, d.y - 24), at: now, expires: now + ttl, fresh: ttl === DROP_TTL_MS });
      while (map.size > DROP_MAX) map.delete(map.keys().next().value);
      return true;
    },
    remove(id) { return map.delete(id); },
    get(id) { return map.get(id) || null; },
    update(now) {
      for (const [id, d] of map) if (now >= d.expires) map.delete(id);
    },
    /** 발 (x, y) 가까운 드롭 (줍기 범위 안, 가장 가까운 것) */
    nearest(x, y) {
      let best = null;
      let bd = Infinity;
      for (const d of map.values()) {
        const dx = Math.abs(d.x - x);
        if (dx > PICK_RANGE.x || Math.abs(d.y - y) > PICK_RANGE.y) continue;
        if (dx < bd) { bd = dx; best = d; }
      }
      return best;
    },
    /** 장치 px 컨텍스트 */
    draw(ctx, camX, camY, k, now, icons, thumbFn, bagSprite) {
      if (!map.size) return;
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      for (const d of map.values()) {
        const age = now - d.at;
        let y = d.y;
        if (d.fresh && age < FALL_MS) { // 떨어지며 살짝 튕긴다
          const t = age / FALL_MS;
          y = d.fromY + (d.y - d.fromY) * t * t - Math.sin(t * Math.PI) * 26;
        }
        const left = d.expires - now;
        if (left < 5000 && Math.floor(now / 150) % 2) continue; // 사라지기 5초 전 깜빡임
        const bob = Math.sin(now / 320 + d.x) * 3;
        const cx = (d.x - camX) * k;
        const cy = (y - camY - ICON_WORLD / 2 - 6 + bob) * k;
        // 그림자
        ctx.globalAlpha = 0.25;
        ctx.fillStyle = '#1A1626';
        ctx.beginPath();
        ctx.ellipse(cx, (d.y - camY) * k, 12 * k, 3 * k, 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1;
        if (bagSprite) { // 아트 드롭 받침 (반짝이, 2프레임)
          const fw = bagSprite.frameW;
          const fr = Math.max(1, Math.floor(bagSprite.img.naturalWidth / fw));
          const f = Math.floor((now / 1000) * bagSprite.fps) % fr;
          const sc = k / bagSprite.density;
          ctx.drawImage(bagSprite.img, f * fw, 0, fw, bagSprite.frameH, cx - bagSprite.anchorX * sc, (y - camY + bob) * k - bagSprite.anchorY * sc, fw * sc, bagSprite.frameH * sc);
        }
        drawItemIcon(ctx, d.item, cx, cy, ICON_WORLD * k, icons, thumbFn);
        // 반짝임 (4갈래 별, 돌며 깜빡)
        const ph = (now / 700 + d.x * 0.01) % 1;
        const a = Math.sin(ph * Math.PI);
        const r = (4 + 4 * a) * k;
        const sx = cx + ICON_WORLD * 0.38 * k;
        const sy = cy - ICON_WORLD * 0.38 * k;
        ctx.globalAlpha = a;
        ctx.fillStyle = '#FFFFFF';
        ctx.beginPath();
        ctx.moveTo(sx, sy - r); ctx.lineTo(sx + r * 0.25, sy - r * 0.25); ctx.lineTo(sx + r, sy); ctx.lineTo(sx + r * 0.25, sy + r * 0.25);
        ctx.lineTo(sx, sy + r); ctx.lineTo(sx - r * 0.25, sy + r * 0.25); ctx.lineTo(sx - r, sy); ctx.lineTo(sx - r * 0.25, sy - r * 0.25);
        ctx.closePath();
        ctx.fill();
        ctx.globalAlpha = 1;
      }
      ctx.restore();
    },
    clear() { map.clear(); },
    get size() { return map.size; },
    list() { return [...map.values()]; },
  };
}
