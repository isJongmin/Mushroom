import { drawProjectileVisual, drawImpactVisual } from './skill-visuals.js';
import { jobDefinition, abilityDefinition } from './jobs.js';
// (사이클 9) 전투: 판정 상자, 피해 숫자, 슬래시, HP 바, 유령, 비석. ARCHITECTURE "사이클 9 계약".
// 좌표는 월드 단위. 그리기는 장치 px 컨텍스트(단위행렬)에 k = 장치 px / 월드로 하거나, HP 바·숫자처럼 CSS px 컨텍스트에 한다.
// 판정 함수는 DOM이 없어도 동작한다(Node 단위 시험 가능). 그리기 함수는 canvas 컨텍스트만 받는다.
//
// 규칙 요약 (계약 값)
//   공격 쿨다운 0.45초. 판정 상자 = 공격자 앞쪽 가로 70, 세로 70 (발 y 기준 y-75 ~ y-5).
//   PvP 피격자 권위: 피해 8~14, 넉백(공격 방향 수평 300, 위로 250), 무적 0.6초. 최대 HP 100. 부활 무적 2초. 부활 버튼 5초 뒤.
//   몬스터 접촉 피해도 같은 무적·넉백 규칙(방향 = 몬스터에서 멀어지는 쪽).

import { ELEMENT_TINT } from './buffs.js';

export const COMBAT = Object.freeze({
  maxHp: 100,
  cooldown: 0.45, // 초
  attackAnimMs: 240, // attack 애니메이션 2프레임 x 120ms
  boxW: 70,
  boxTop: 75, // 발 위 75
  boxBottom: 5, // 발 위 5
  dmgMin: 8,
  dmgMax: 14,
  knockX: 300,
  knockY: 250,
  knockT: 0.3, // 넉백 수평 속도 유지 시간 (착지하면 끝)
  invuln: 0.6, // 초
  reviveInvuln: 2,
  reviveDelay: 5, // 초: 부활 버튼이 나오기까지
  hurtW: 36, // 캐릭터 피격 상자 (발 기준)
  hurtH: 72,
  hurtHProne: 34,
});

export const randInt = (lo, hi, rnd = Math.random) => lo + Math.floor(rnd() * (hi - lo + 1));

/** 공격 판정 상자 { x1, x2, y1, y2 } (월드). dir = 'left'|'right'|-1|1, w = 가로 (사이클 10 사거리 버프) */
export function attackBox(x, y, dir, w = COMBAT.boxW) {
  const d = dir === 'left' || dir === -1 ? -1 : 1;
  return d > 0
    ? { x1: x, x2: x + w, y1: y - COMBAT.boxTop, y2: y - COMBAT.boxBottom }
    : { x1: x - w, x2: x, y1: y - COMBAT.boxTop, y2: y - COMBAT.boxBottom };
}

/** 캐릭터 피격 상자 (발 중앙 기준) */
export function hurtBox(x, y, prone = false) {
  const h = prone ? COMBAT.hurtHProne : COMBAT.hurtH;
  return { x1: x - COMBAT.hurtW / 2, x2: x + COMBAT.hurtW / 2, y1: y - h, y2: y };
}

export const overlaps = (a, b) => a.x1 < b.x2 && a.x2 > b.x1 && a.y1 < b.y2 && a.y2 > b.y1;

// ---------------------------------------------------------------------------
// 피해 숫자 (메이플처럼 위로 떠오르며 사라짐). CSS px 컨텍스트에 그린다. 숫자만 그리므로 사용자 문자열 없음.

const NUM_LIFE_MS = 900;
const NUM_RISE = 34; // CSS px
const NUM_MAX = 120; // 11타 x 여러 명
const NUM_FONT = '900 22px system-ui, -apple-system, "Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans KR", sans-serif';
// kind: 'hit'(내가/남이 남·몬스터에게 준 피해: 주황) | 'hurt'(내가 받은 피해: 보라) | 'heal'
const NUM_STYLE = {
  hit: { top: '#FFF2A8', bottom: '#F08A2E', line: '#5E2A10' },
  hurt: { top: '#FFC8DC', bottom: '#B04A78', line: '#3A1430' },
  heal: { top: '#D8FFC0', bottom: '#3E8A2E', line: '#163A10', plus: true }, // 회복: 녹색 +n
};

export function createDamageNumbers() {
  const list = [];
  return {
    /** x, y = 월드 (머리 위), at = performance.now() */
    /** stackIndex가 숫자면 그 줄(multi 타 순서)에 놓는다: 한 줄 = 18 월드 위 (11타면 11줄 기둥, 메이플식) */
    add(value, x, y, kind = 'hit', at = performance.now(), stackIndex = null) {
      const v = Math.max(0, Math.round(value));
      if (!Number.isFinite(v)) return;
      // 같은 자리에 겹쳐 쌓이면 조금씩 위로
      let stack = 0;
      if (typeof stackIndex === 'number') stack = stackIndex * 1.8;
      else for (const n of list) if (Math.abs(n.x - x) < 24 && Math.abs(at - n.at) < 300) stack++;
      list.push({ text: (NUM_STYLE[kind] && NUM_STYLE[kind].plus ? '+' : '') + String(v), x, y: y - stack * 10, kind, at });
      if (list.length > NUM_MAX) list.splice(0, list.length - NUM_MAX);
    },
    update(now) {
      for (let i = list.length - 1; i >= 0; i--) if (now - list[i].at >= NUM_LIFE_MS) list.splice(i, 1);
    },
    /** ctx = CSS px 단위(setTransform(dpr)). u = CSS px / 월드 */
    draw(ctx, camX, camY, u, now) {
      if (!list.length) return;
      ctx.save();
      ctx.font = NUM_FONT;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'alphabetic';
      ctx.lineJoin = 'round';
      for (const n of list) {
        if (now < n.at) continue; // (사이클 10) multi: 다음 타 숫자는 80ms 뒤부터
        const t = Math.min(1, (now - n.at) / NUM_LIFE_MS);
        const s = NUM_STYLE[n.kind] || NUM_STYLE.hit;
        const pop = t < 0.12 ? 1 + (0.12 - t) * 3 : 1; // 처음에 살짝 크게
        const sx = (n.x - camX) * u;
        const sy = (n.y - camY) * u - NUM_RISE * (1 - (1 - t) * (1 - t));
        ctx.save();
        ctx.globalAlpha = t < 0.6 ? 1 : 1 - (t - 0.6) / 0.4;
        ctx.translate(sx, sy);
        ctx.scale(pop, pop);
        const g = ctx.createLinearGradient(0, -18, 0, 0);
        g.addColorStop(0, s.top);
        g.addColorStop(1, s.bottom);
        ctx.lineWidth = 5;
        ctx.strokeStyle = s.line;
        ctx.strokeText(n.text, 0, 0);
        ctx.fillStyle = g;
        ctx.fillText(n.text, 0, 0);
        ctx.restore();
      }
      ctx.restore();
    },
    clear() { list.length = 0; },
    get count() { return list.length; },
  };
}

// ---------------------------------------------------------------------------
// HP 바: 가로 40, 세로 5 (CSS px), 빨간 바, 배경 어두운 회색, 테두리 1

export const HPBAR = Object.freeze({ w: 40, h: 5, border: 1, gap: 4 });

/** cx = 가운데 x, top = 바 위 끝 y (CSS px) */
export function drawHpBar(ctx, cx, top, hp, max, alpha = 1) {
  const w = HPBAR.w;
  const h = HPBAR.h;
  const x = Math.round(cx - w / 2);
  const y = Math.round(top);
  const r = Math.max(0, Math.min(1, max > 0 ? hp / max : 0));
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.fillStyle = '#1A1626';
  ctx.fillRect(x - HPBAR.border, y - HPBAR.border, w + HPBAR.border * 2, h + HPBAR.border * 2);
  ctx.fillStyle = '#3B3746';
  ctx.fillRect(x, y, w, h);
  const fw = Math.round(w * r);
  if (fw > 0) {
    ctx.fillStyle = '#E8483E';
    ctx.fillRect(x, y, fw, h);
    ctx.fillStyle = '#FF8E7A';
    ctx.fillRect(x, y, fw, 1);
    ctx.fillStyle = '#9E2838';
    ctx.fillRect(x, y + h - 1, fw, 1);
  }
  ctx.restore();
}

// ---------------------------------------------------------------------------
// 슬래시 (무기 궤적): 몬스터 manifest fx.slash(assets/fx/slash.png, 가로 프레임, 기준점 = 공격자 발)가 있으면 그 그림,
// 없으면 절차적 초승달. 0.2초. (manifest에 없는 파일을 짐작해 요청하지 않는다: 404 방지)

const SLASH_MS = 200;

export function createSlashes() {
  const list = [];
  // loadSprite 결과 { img, frameW, frameH, anchorX, anchorY, density, fps } | null. [0] 기본, [1] 불, [2] 얼음, [3] 번개 (사이클 10)
  const sprites = [null, null, null, null];
  return {
    setSprite(v, el = 0) { sprites[el] = v && v.img ? v : null; },
    get hasImage() { return !!sprites[0]; },
    get elementImages() { return sprites.slice(1).map((v) => !!v); },
    /** owner = 플레이어 객체(위치를 따라감) */
    /** opt = { w(판정 가로, 기본 70), el(속성 0~3) } (사이클 10: 사거리는 길이, 속성은 색) */
    add(owner, dir, opt = {}, at = performance.now()) {
      list.push({ owner, dir: dir < 0 ? -1 : 1, at, w: opt.w || 70, el: opt.el | 0 });
      if (list.length > 40) list.shift();
    },
    update(now) {
      for (let i = list.length - 1; i >= 0; i--) if (now - list[i].at >= SLASH_MS) list.splice(i, 1);
    },
    forget(owner) { for (let i = list.length - 1; i >= 0; i--) if (list[i].owner === owner) list.splice(i, 1); },
    /** 장치 px 컨텍스트 */
    draw(ctx, camX, camY, k, now) {
      if (!list.length) return;
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      for (const s of list) {
        const t = Math.min(1, (now - s.at) / SLASH_MS);
        const o = s.owner;
        const el = Math.max(0, Math.min(3, s.el));
        const spr = sprites[el]; // 속성 시트가 없으면 속성색 절차적 호 (기본 시트로 대체하면 색이 사라진다)
        const stretch = Math.max(1, s.w / 70); // 사거리 버프: 가로로 늘린다
        if (spr) {
          const frames = Math.max(1, Math.floor(spr.img.naturalWidth / spr.frameW));
          const f = Math.min(frames - 1, Math.floor(((now - s.at) / 1000) * spr.fps));
          const sc = k / spr.density;
          ctx.globalAlpha = t < 0.6 ? 1 : 1 - (t - 0.6) / 0.4;
          ctx.setTransform(s.dir * stretch, 0, 0, 1, (o.x - camX) * k, (o.y - camY) * k);
          ctx.drawImage(spr.img, f * spr.frameW, 0, spr.frameW, spr.frameH, -spr.anchorX * sc, -spr.anchorY * sc, spr.frameW * sc, spr.frameH * sc);
          ctx.setTransform(1, 0, 0, 1, 0, 0);
          ctx.globalAlpha = 1;
          continue;
        }
        const cx = (o.x - camX + s.dir * 22) * k;
        const cy = (o.y - camY - 42) * k;
        drawSlashArc(ctx, cx, cy, k, s.dir, t, stretch, ELEMENT_TINT[el]);
      }
      ctx.restore();
    },
    clear() { list.length = 0; },
    get count() { return list.length; },
  };
}

/** 절차적 초승달: 위에서 앞으로 휘두르는 호. t = 0~1 진행 */
export function drawSlashArc(ctx, cx, cy, k, dir, t, stretch = 1, tint = null) {
  const R = 46 * k;
  const sweep = Math.min(1, t / 0.55); // 앞 55% 동안 휘두르고 나머지는 사라짐
  const fade = t < 0.55 ? 1 : 1 - (t - 0.55) / 0.45;
  const a0 = -Math.PI * 0.62;
  const a1 = a0 + Math.PI * 0.95 * sweep;
  const tail = Math.max(a0, a1 - Math.PI * 0.7);
  if (a1 - tail < 0.02) return;
  ctx.save();
  ctx.translate(cx, cy);
  ctx.scale(dir * stretch, 1);
  // 바깥 호 → 안쪽 호(중심을 뒤로 밀어 초승달)
  const inner = R * 0.72;
  const off = R * 0.16;
  const grad = ctx.createRadialGradient(0, 0, inner * 0.6, 0, 0, R);
  const inC = tint ? tint.outer : '156, 200, 255';
  const midC = tint ? tint.outer : '190, 228, 255';
  const edgeC = tint ? tint.inner : '255, 255, 255';
  grad.addColorStop(0, `rgba(${inC}, 0)`);
  grad.addColorStop(0.7, `rgba(${midC}, ${0.8 * fade})`);
  grad.addColorStop(1, `rgba(${edgeC}, ${0.95 * fade})`);
  ctx.beginPath();
  ctx.arc(0, 0, R, tail, a1, false);
  ctx.arc(-off, 0, inner, a1, tail, true);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();
  ctx.lineWidth = Math.max(1, 1.5 * k);
  ctx.strokeStyle = `rgba(${tint ? tint.line : '77, 124, 254'}, ${0.6 * fade})`;
  ctx.beginPath();
  ctx.arc(0, 0, R, tail, a1, false);
  ctx.stroke();
  // 끝 반짝임
  const ex = Math.cos(a1) * R;
  const ey = Math.sin(a1) * R;
  ctx.fillStyle = `rgba(255, 255, 255, ${fade})`;
  ctx.beginPath();
  ctx.arc(ex, ey, 3.5 * k, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

// ---------------------------------------------------------------------------
// 유령과 비석. 스프라이트 { img, anchorX, anchorY, density } 가 있으면 그것, 없으면 절차적 그림.

/** 유령: 발 위치 (x, y) 장치 px, k = 장치 px / 월드, t = 초(둥실) */
export function drawGhost(ctx, sprite, x, y, k, t, facingLeft, alpha = 0.78) {
  const bob = Math.sin(t * 3.2) * 4 * k - 8 * k;
  ctx.save();
  ctx.setTransform(facingLeft ? -1 : 1, 0, 0, 1, x, y + bob);
  ctx.globalAlpha = sprite && sprite.img ? 1 : alpha; // 스프라이트는 반투명이 PNG에 들어 있다
  if (sprite && sprite.img) {
    const s = k / sprite.density;
    const img = sprite.img;
    const fw = sprite.frameW || img.naturalWidth;
    const fh = sprite.frameH || img.naturalHeight;
    const frames = Math.max(1, Math.floor(img.naturalWidth / fw));
    const f = frames > 1 ? Math.floor(t * (sprite.fps || 6)) % frames : 0;
    ctx.drawImage(img, f * fw, 0, fw, fh, -sprite.anchorX * s, -sprite.anchorY * s, fw * s, fh * s);
  } else {
    const u = k;
    ctx.beginPath();
    ctx.moveTo(-18 * u, -4 * u);
    ctx.lineTo(-18 * u, -42 * u);
    ctx.arc(0, -42 * u, 18 * u, Math.PI, 0, false);
    ctx.lineTo(18 * u, -4 * u);
    const wv = Math.sin(t * 6) * 2 * u;
    for (let i = 0; i < 4; i++) {
      const xa = 18 * u - i * 9 * u;
      ctx.quadraticCurveTo(xa - 4.5 * u, (4 + (i % 2 ? -1 : 1) * 2) * u + wv, xa - 9 * u, -4 * u);
    }
    ctx.closePath();
    const g = ctx.createLinearGradient(0, -60 * u, 0, 0);
    g.addColorStop(0, 'rgba(255,255,255,0.98)');
    g.addColorStop(1, 'rgba(200,220,255,0.75)');
    ctx.fillStyle = g;
    ctx.fill();
    ctx.lineWidth = Math.max(1, 2 * u);
    ctx.strokeStyle = 'rgba(110,128,180,0.9)';
    ctx.stroke();
    ctx.fillStyle = '#2E2A3E';
    ctx.beginPath(); ctx.ellipse(3 * u, -44 * u, 2.6 * u, 4 * u, 0, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.ellipse(11 * u, -44 * u, 2.6 * u, 4 * u, 0, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = 'rgba(245,138,180,0.6)';
    ctx.beginPath(); ctx.ellipse(1 * u, -37 * u, 3 * u, 1.6 * u, 0, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.ellipse(14 * u, -37 * u, 3 * u, 1.6 * u, 0, 0, Math.PI * 2); ctx.fill();
  }
  ctx.restore();
}

/** 비석 하나: 바닥 (x, y) 장치 px */
export function drawTombstone(ctx, sprite, x, y, k, squash = 0) {
  ctx.save();
  ctx.setTransform(1 + squash * 0.25, 0, 0, 1 - squash * 0.25, x, y);
  if (sprite && sprite.img) {
    const s = k / sprite.density;
    const fw = sprite.frameW || sprite.img.naturalWidth;
    const fh = sprite.frameH || sprite.img.naturalHeight;
    ctx.drawImage(sprite.img, 0, 0, fw, fh, -sprite.anchorX * s, -sprite.anchorY * s, fw * s, fh * s);
  } else {
    const u = k;
    ctx.beginPath();
    ctx.moveTo(-14 * u, 0);
    ctx.lineTo(-14 * u, -24 * u);
    ctx.arc(0, -24 * u, 14 * u, Math.PI, 0, false);
    ctx.lineTo(14 * u, 0);
    ctx.closePath();
    ctx.fillStyle = '#A9A4B8';
    ctx.fill();
    ctx.lineWidth = Math.max(1, 2 * u);
    ctx.strokeStyle = '#4A4560';
    ctx.stroke();
    ctx.fillStyle = '#C8C4D0';
    ctx.fillRect(-11 * u, -30 * u, 3 * u, 26 * u);
    ctx.fillStyle = '#6A6480';
    ctx.fillRect(-1.5 * u, -32 * u, 3 * u, 16 * u);
    ctx.fillRect(-6 * u, -27 * u, 12 * u, 3 * u);
    ctx.fillStyle = '#5E3620';
    ctx.fillRect(-18 * u, -2 * u, 36 * u, 3 * u);
  }
  ctx.restore();
}

/**
 * 비석 관리: 플레이어마다 1개. 위(160)에서 떨어져 바닥에 꽂히고 먼지가 난다. 부활하면 지운다.
 * surfaceAt(x, y) → 아래 면 y (월드)
 */
export function createTombstones() {
  const stones = new Map(); // owner(user_id) -> { x, y, ground, vy, landedAt, dust: [] }
  const G = 2600;
  return {
    drop(owner, x, ground, now = performance.now()) {
      stones.set(owner, { x, y: ground - 170, ground, vy: 0, landedAt: 0, dust: [], at: now });
    },
    remove(owner) { stones.delete(owner); },
    has(owner) { return stones.has(owner); },
    update(dt, now) {
      for (const s of stones.values()) {
        if (!s.landedAt) {
          s.vy += G * dt;
          s.y += s.vy * dt;
          if (s.y >= s.ground) {
            s.y = s.ground;
            s.landedAt = now;
            for (let i = 0; i < 9; i++) {
              const a = Math.PI * (i / 8);
              s.dust.push({ x: s.x + Math.cos(a) * 6, y: s.ground - 2, vx: Math.cos(a) * (60 + Math.random() * 70), vy: -30 - Math.random() * 60, r: 3 + Math.random() * 4, age: 0, life: 0.45 + Math.random() * 0.2 });
            }
          }
        }
        for (let i = s.dust.length - 1; i >= 0; i--) {
          const d = s.dust[i];
          d.age += dt;
          if (d.age >= d.life) { s.dust.splice(i, 1); continue; }
          d.vy += 260 * dt;
          d.vx *= Math.exp(-4 * dt);
          d.x += d.vx * dt;
          d.y += d.vy * dt;
          d.r += 6 * dt;
        }
      }
    },
    draw(ctx, sprite, camX, camY, k, now) {
      if (!stones.size) return;
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      for (const s of stones.values()) {
        const since = s.landedAt ? (now - s.landedAt) / 1000 : -1;
        const squash = since >= 0 && since < 0.18 ? Math.sin((since / 0.18) * Math.PI) : 0;
        drawTombstone(ctx, sprite, (s.x - camX) * k, (s.y - camY) * k, k, squash);
        for (const d of s.dust) {
          ctx.globalAlpha = 0.55 * (1 - d.age / d.life);
          ctx.fillStyle = '#C9A47A';
          ctx.beginPath();
          ctx.arc((d.x - camX) * k, (d.y - camY) * k, d.r * k, 0, Math.PI * 2);
          ctx.fill();
          ctx.globalAlpha = 1;
        }
        ctx.setTransform(1, 0, 0, 1, 0, 0);
      }
      ctx.restore();
    },
    clear() { stones.clear(); },
    get count() { return stones.size; },
    snapshot() { return [...stones.entries()].map(([owner, s]) => ({ owner, x: Math.round(s.x), y: Math.round(s.y), landed: !!s.landedAt })); },
  };
}

/** 무적 깜빡임: 보일 때 1, 흐릴 때 0.3 (80ms 주기) */
export function blinkAlpha(now, until) {
  if (now >= until) return 1;
  return Math.floor(now / 80) % 2 ? 0.3 : 1;
}

/** Read-only swept collision, ordered by first contact along the shot's direction. */
export function projectileCollision(p, box, mobs, getBox) {
  let best = null;
  for (const mob of mobs) {
    if (mob.s === 'die' || mob.hp <= 0) continue;
    const b = getBox(mob);
    if (!overlaps(box, b)) continue;
    let impactX, impactY = p.y, distance;
    if (Number.isFinite(p.nextX) && Number.isFinite(p.nextY)) {
      // Segment vs expanded target: diagonal shots cannot hit empty corners of a swept AABB.
      const radius = p.radius || 8;
      let enter=0, leave=1, valid=true;
      for (const [from, to, min, max] of [[p.x,p.nextX,b.x1-radius,b.x2+radius],[p.y,p.nextY,b.y1-radius,b.y2+radius]]) {
        const delta=to-from;
        if (Math.abs(delta)<1e-9) { if(from<min||from>max) valid=false; }
        else { const a=(min-from)/delta, z=(max-from)/delta; enter=Math.max(enter,Math.min(a,z)); leave=Math.min(leave,Math.max(a,z)); }
      }
      if(!valid||enter>leave||leave<0||enter>1) continue;
      distance=enter; impactX=p.x+(p.nextX-p.x)*enter; impactY=p.y+(p.nextY-p.y)*enter;
    } else {
      impactX = p.dir > 0 ? Math.max(p.x, b.x1 - 8) : Math.min(p.x, b.x2 + 8);
      distance = (impactX - p.x) * p.dir;
    }
    if (!best || distance < best.distance) best = { mob, impactX, impactY, distance };
  }
  return best;
}

/** Traveling job attacks, simulated identically for spectators; only host hit() mutates mobs. */
export function createJobProjectiles() {
  const list = [], bursts = [];
  const completed = new Map();
  let localSequence = 0;
  function prune(now) {
    for (const [id, at] of completed) if (now - at > 10000) completed.delete(id);
    while (completed.size > 1024) completed.delete(completed.keys().next().value);
  }
  function finish(id, x, y, now, job) {
    prune(now);
    if (completed.has(id)) { const burst=bursts.find(b=>b.id===id); if(burst){burst.x=x;burst.y=y;} return false; }
    completed.set(id, now);
    bursts.push({ id, x, y, at: now, job: job.id, skill: job.skill || 0 });
    if (bursts.length > 160) bursts.shift();
    prune(now);
    return true;
  }
  return {
    /** Host acknowledgement also works before its attack arrives or after a kill snapshot. */
    impact(id, x, y, now, jobId, slot = 0) {
      const p = list.find(p => p.id === id);
      for (let i = list.length - 1; i >= 0; i--) if (list[i].id === id) list.splice(i, 1);
      return finish(id, x, y, now, p?.job || { ...jobDefinition(jobId), skill: slot });
    },
    add(a, now, authoritative = false) {
      const base = jobDefinition(a.job);
      const ability = abilityDefinition(a.job, a.skill ?? 0);
      if (!ability?.speed) return;
      const j = { ...base, speed: ability.speed, splash: ability.splash, targets: ability.targets, skill: a.skill || 0 };
      if (!j.speed) return;
      const count = ability.shots;
      prune(now);
      const attackId = a.user_id && Number.isSafeInteger(a.seq) ? `${a.user_id}:${a.seq}` : `local:${localSequence++}`;
      for (let i = 0; i < count; i++) {
        const id = `${attackId}:${i}`;
        if (completed.has(id) || list.some(p => p.id === id)) continue;
        const dir=a.dir === 'left' ? -1 : 1, clone=ability.pattern==='clones' ? Math.floor(i/3) : 0;
        const angle=ability.pattern==='fan' ? (i-1)*ability.spread : 0;
        const delay=ability.pattern==='fan'?0:ability.pattern==='clones'?clone*180+(i%3)*65:i*85;
        list.push({ id, a, job: j, x: a.x + (clone?(-38+clone*43)*dir:0), y: a.y - 35 - clone*18,
          angle, radius: ability.pattern==='saw'?27:8, distance:0, at:now+delay, authoritative, dir,
          damage: { ...a, hits: Math.ceil((a.hits - i) / count) } });
      }
      if (list.length > 160) list.splice(0, list.length - 160);
    },
    update(dt, now, hit, visualHit) {
      for (let i = list.length - 1; i >= 0; i--) {
        const p = list[i]; if (now < p.at) continue;
        const travel = Math.min(p.job.speed * Math.min(dt, Math.max(0, (now-p.at)/1000)), p.a.w - p.distance);
        const next = p.x + p.dir * Math.cos(p.angle) * travel, nextY=p.y + Math.sin(p.angle)*travel;
        p.nextX=next; p.nextY=nextY;
        const r=p.radius;
        const box = { x1: Math.min(p.x, next) - r, x2: Math.max(p.x, next) + r, y1: Math.min(p.y,nextY) - r, y2: Math.max(p.y,nextY) + r };
        const result = p.authoritative ? hit?.(p, box) : visualHit?.(p, box);
        p.x = result ? (result.impactX ?? result.mob.x) : next;
        p.y = result ? (result.impactY ?? p.y) : nextY;
        p.distance += travel;
        if (result || p.distance >= p.a.w) {
          if (result) finish(p.id, p.x, p.y, now, p.job);
          list.splice(i, 1);
        }
      }
      for (let i = bursts.length - 1; i >= 0; i--) if (now - bursts[i].at > 600) bursts.splice(i, 1);
    },
    draw(ctx, camX, camY, k, now) {
      ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0);
      for (const p of list) if (now >= p.at) drawProjectileVisual(ctx,p,camX,camY,k,now);
      for (const b of bursts) drawImpactVisual(ctx,b,camX,camY,k,now);
      ctx.restore();
    },
    snapshot() { return { shots: list.map(p=>({id:p.id,x:p.x,y:p.y,angle:p.angle,at:p.at,pattern:abilityDefinition(p.a.job,p.a.skill??0).pattern,hits:p.damage.hits})), bursts:bursts.map(b=>({...b})) }; },
    clear() { list.length = 0; bursts.length = 0; completed.clear(); },
    get count() { return list.length; },
  };
}
