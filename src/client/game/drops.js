// (사이클 10) 버프 드롭: 목록(30초 소멸, 마지막 5초 깜빡임), 떨어짐·둥실·빛. ARCHITECTURE "사이클 10 계약".
// 그림: manifest fx 버프 구슬 시트(가로 5프레임 range,multi,element,power,speed)가 있으면 그것, 없으면 절차적 구슬(buffs.drawBuffOrb).
// 몬스터 manifest dropBag(받침)이 있으면 아래에 깐다.
import { BUFF_IDS, drawBuffOrb } from './buffs.js';

export const DROP_TTL_MS = 30000;
export const PICK_RANGE = Object.freeze({ x: 44, y: 60 }); // Z 줍기 범위 (발 기준)
export const TOUCH_RANGE = Object.freeze({ x: 26, y: 56 }); // 닿으면 자동 줍기
const DROP_MAX = 40;
const FALL_MS = 380;
const ORB_WORLD = 26; // 지름 (월드)

export function createDrops() {
  const map = new Map(); // id -> { id, buff, x, y, fromY, at, expires, fresh }
  return {
    /** 새 드롭(또는 재전송). ground = 아래 면 y. ttl = 남은 ms (재전송) */
    add(d, ground, now = performance.now()) {
      if (map.has(d.id)) return false;
      const ttl = typeof d.ttl === 'number' && d.ttl > 0 ? Math.min(DROP_TTL_MS, d.ttl) : DROP_TTL_MS;
      map.set(d.id, { id: d.id, buff: d.buff, x: d.x, y: ground, fromY: Math.min(ground, d.y - 24), at: now, expires: now + ttl, fresh: ttl === DROP_TTL_MS });
      while (map.size > DROP_MAX) map.delete(map.keys().next().value);
      return true;
    },
    remove(id) { return map.delete(id); },
    get(id) { return map.get(id) || null; },
    update(now) { for (const [id, d] of map) if (now >= d.expires) map.delete(id); },
    /** 발 (x, y)에서 range 안의 가장 가까운 드롭 */
    nearest(x, y, range = PICK_RANGE) {
      let best = null;
      let bd = Infinity;
      for (const d of map.values()) {
        const dx = Math.abs(d.x - x);
        if (dx > range.x || Math.abs(d.y - y) > range.y) continue;
        if (dx < bd) { bd = dx; best = d; }
      }
      return best;
    },
    /** 장치 px 컨텍스트. orb = 구슬 시트 스프라이트 | null, bag = 받침 스프라이트 | null */
    draw(ctx, camX, camY, k, now, orb, bag) {
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
        if (d.expires - now < 5000 && Math.floor(now / 150) % 2) continue; // 사라지기 5초 전 깜빡임
        const bob = Math.sin(now / 320 + d.x) * 3;
        const cx = (d.x - camX) * k;
        const cy = (y - camY - ORB_WORLD / 2 - 8 + bob) * k;
        ctx.globalAlpha = 0.25;
        ctx.fillStyle = '#1A1626';
        ctx.beginPath();
        ctx.ellipse(cx, (d.y - camY) * k, 11 * k, 3 * k, 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1;
        if (bag) {
          const fr = Math.max(1, Math.floor(bag.img.naturalWidth / bag.frameW));
          const f = Math.floor((now / 1000) * bag.fps) % fr;
          const sc = k / bag.density;
          ctx.drawImage(bag.img, f * bag.frameW, 0, bag.frameW, bag.frameH, cx - bag.anchorX * sc, (y - camY + bob) * k - bag.anchorY * sc, bag.frameW * sc, bag.frameH * sc);
        }
        const fi = BUFF_IDS.indexOf(d.buff);
        if (orb && fi >= 0 && orb.img.naturalWidth >= (fi + 1) * orb.frameW) {
          const s = ORB_WORLD * k * 1.2;
          ctx.drawImage(orb.img, fi * orb.frameW, 0, orb.frameW, orb.frameH, cx - s / 2, cy - s / 2, s, s);
        } else {
          drawBuffOrb(ctx, d.buff, cx, cy, (ORB_WORLD / 2) * k, 0.6 + 0.4 * Math.sin(now / 200));
        }
      }
      ctx.restore();
    },
    clear() { map.clear(); },
    get size() { return map.size; },
    list() { return [...map.values()]; },
  };
}
