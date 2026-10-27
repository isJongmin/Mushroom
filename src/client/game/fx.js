// (사이클 8) 슈퍼 점프 이펙트 — 절차적으로 그린다(에셋 없음). 월드 단위로 계산하고 장치 px 컨텍스트(단위행렬)에 그린다.
//   1) 큐브 파티클 버스트: 시작 지점에 작은 정사각형 10~16개(캐릭터 대표 색 + 밝은 색 + 흰색). 3톤(윗면 밝게, 아래 어둡게) 스프라이트를
//      색마다 오프스크린에 한 번 그려 재사용한다(캐시 상한 24). 파티클 전체 상한 160(넘으면 오래된 것부터 버림).
//   2) 잔상: 발동 직후 0.16초 동안 캐릭터 위치·프레임을 4번 기록해 투명도를 줄여 가며 그린다(캐릭터 그리기는 화면이 콜백으로).
//   3) 바람 줄기: 진행 반대쪽으로 흰 줄 5개.
//   모두 0.5초 안에 사라진다. prefers-reduced-motion이면 파티클 5개, 잔상 1개, 줄기 2개, 더 짧게.
import { makeCanvas } from '../avatar.js';

const MAX_PARTICLES = 160;
const SPRITE_PX = 16;
const SPRITE_CACHE_MAX = 24;
const LIFE = 0.5; // 모든 효과의 최대 수명(초)

const clamp255 = (v) => Math.max(0, Math.min(255, Math.round(v)));
const mix = (c, t, a) => c.map((v, i) => clamp255(v + (t[i] - v) * a));
const css = (c) => `rgb(${c[0]},${c[1]},${c[2]})`;
const DEFAULT_TINT = [77, 124, 254]; // u2

export function prefersReducedMotion() {
  try { return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches); } catch { return false; }
}

export function createFx(opts = {}) {
  let reduced = !!opts.reduced;
  const particles = [];
  const ghosts = [];
  const streaks = [];
  const sprites = new Map(); // 'r,g,b' -> canvas
  const stats = { bursts: 0, spritesMade: 0, dropped: 0 };

  function sprite(c) {
    const key = c.join(',');
    let s = sprites.get(key);
    if (s) { sprites.delete(key); sprites.set(key, s); return s; }
    s = makeCanvas(SPRITE_PX, SPRITE_PX);
    const g = s.getContext('2d');
    const n = SPRITE_PX;
    g.fillStyle = css(mix(c, [26, 22, 38], 0.55)); g.fillRect(0, 0, n, n); // 테두리 겸 그림자
    g.fillStyle = css(c); g.fillRect(2, 2, n - 4, n - 4);
    g.fillStyle = css(mix(c, [255, 255, 255], 0.55)); g.fillRect(2, 2, n - 4, 3); g.fillRect(2, 2, 3, n - 4);
    g.fillStyle = css(mix(c, [26, 22, 38], 0.3)); g.fillRect(n - 5, 5, 3, n - 7); g.fillRect(5, n - 5, n - 7, 3);
    sprites.set(key, s);
    stats.spritesMade++;
    while (sprites.size > SPRITE_CACHE_MAX) sprites.delete(sprites.keys().next().value);
    return s;
  }

  /**
   * 이펙트 시작
   * @param kind 'dash-left' | 'dash-right' | 'dash-up'
   * @param x,y 시작 지점 발 위치 (월드)
   * @param tint 캐릭터 대표 색 [r,g,b] | null
   * @param target 잔상을 남길 대상 { x, y, dir } (플레이어 객체, 위치를 읽기만 한다) | null
   */
  function spawn(kind, x, y, tint, target) {
    stats.bursts++;
    const base = Array.isArray(tint) ? tint : DEFAULT_TINT;
    const palette = [sprite(base), sprite(mix(base, [255, 255, 255], 0.45)), sprite([255, 255, 255])];
    const dx = kind === 'dash-left' ? 1 : kind === 'dash-right' ? -1 : 0; // 진행 반대쪽
    const up = kind === 'dash-up';
    const n = reduced ? 5 : 10 + Math.floor(Math.random() * 7);
    for (let i = 0; i < n; i++) {
      const a = up ? Math.PI * (0.15 + 0.7 * Math.random()) // 아래쪽 반원으로 퍼짐
        : (dx > 0 ? 0 : Math.PI) + (Math.random() - 0.5) * 1.6 - (dx > 0 ? 0.35 : -0.35);
      const sp = 120 + Math.random() * 260;
      particles.push({
        x: x + (Math.random() - 0.5) * 16,
        y: y - 8 - Math.random() * 30,
        vx: Math.cos(a) * sp + (up ? 0 : dx * 60),
        vy: up ? Math.abs(Math.sin(a)) * sp * 0.6 - 60 : -Math.abs(Math.sin(a)) * sp * 0.7 - 40,
        size: 5 + Math.random() * 5,
        rot: Math.random() * Math.PI,
        vr: (Math.random() - 0.5) * 10,
        age: 0,
        life: (reduced ? 0.25 : 0.32) + Math.random() * 0.16,
        img: palette[i % 3],
      });
    }
    if (particles.length > MAX_PARTICLES) {
      stats.dropped += particles.length - MAX_PARTICLES;
      particles.splice(0, particles.length - MAX_PARTICLES);
    }
    if (target) ghosts.push({ target, samples: [], age: 0, nextAt: 0, max: reduced ? 1 : 4, life: reduced ? 0.25 : 0.45 });
    const ns = reduced ? 2 : 5;
    for (let i = 0; i < ns; i++) {
      const off = (i - (ns - 1) / 2);
      streaks.push(up
        ? { x: x + off * 11, y: y - 4 + Math.random() * 10, dx: 0, dy: 1, len: 40 + Math.random() * 34, age: 0, life: 0.34 }
        : { x: x + dx * (6 + Math.random() * 10), y: y - 14 - (i * 76) / ns + Math.random() * 6, dx, dy: 0, len: 48 + Math.random() * 40, age: 0, life: 0.34 });
    }
  }

  /** frameOf(target) → 잔상 기록 때 프레임 번호 */
  function update(dt, frameOf) {
    for (let i = particles.length - 1; i >= 0; i--) {
      const p = particles[i];
      p.age += dt;
      if (p.age >= p.life) { particles.splice(i, 1); continue; }
      p.vy += 900 * dt;
      p.vx *= Math.exp(-3 * dt);
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.rot += p.vr * dt;
    }
    for (let i = ghosts.length - 1; i >= 0; i--) {
      const g = ghosts[i];
      g.age += dt;
      if (g.age >= Math.min(LIFE, g.life)) { ghosts.splice(i, 1); continue; }
      if (g.samples.length < g.max && g.age >= g.nextAt) {
        const t = g.target;
        g.samples.push({ x: t.x, y: t.y, dir: t.dir, frame: frameOf ? frameOf(t) : 0, at: g.age });
        g.nextAt = g.age + 0.035;
      }
    }
    for (let i = streaks.length - 1; i >= 0; i--) {
      const s = streaks[i];
      s.age += dt;
      if (s.age >= s.life) streaks.splice(i, 1);
    }
  }

  /** 캐릭터 뒤: 잔상 + 바람 줄기. drawGhost(ctx, target, xDev, yDev, frame, facingLeft, alpha) */
  function drawBack(ctx, camX, camY, k, drawGhost) {
    if (!ghosts.length && !streaks.length) return;
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    for (const g of ghosts) {
      const fade = 1 - g.age / g.life;
      g.samples.forEach((s, i) => {
        // 오래된 기록일수록 흐리게. 현재 캐릭터 위치와 거의 같으면 그리지 않는다
        if (Math.abs(s.x - g.target.x) < 6 && Math.abs(s.y - g.target.y) < 6) return;
        const a = 0.62 * fade * (1 - i / (g.max + 1));
        if (a <= 0.02) return;
        drawGhost(ctx, g.target, Math.round((s.x - camX) * k), Math.round((s.y - camY) * k), s.frame, s.dir < 0, a);
      });
    }
    ctx.lineCap = 'round';
    for (const s of streaks) {
      const t = s.age / s.life;
      const a = 0.9 * (1 - t * t);
      const grow = 0.5 + 0.5 * Math.min(1, t * 3);
      const x0 = (s.x - camX) * k;
      const y0 = (s.y - camY) * k;
      const drift = 40 * t * k;
      ctx.strokeStyle = `rgba(255,255,255,${a.toFixed(3)})`;
      ctx.lineWidth = Math.max(1.5, 3.5 * k);
      ctx.beginPath();
      ctx.moveTo(x0 + s.dx * drift, y0 + s.dy * drift);
      ctx.lineTo(x0 + s.dx * (drift + s.len * grow * k), y0 + s.dy * (drift + s.len * grow * k));
      ctx.stroke();
    }
    ctx.restore();
  }

  /** 캐릭터 앞: 큐브 파티클 */
  function drawFront(ctx, camX, camY, k) {
    if (!particles.length) return;
    ctx.save();
    for (const p of particles) {
      const t = p.age / p.life;
      const s = p.size * k * (1 - 0.4 * t);
      ctx.globalAlpha = t < 0.6 ? 1 : 1 - (t - 0.6) / 0.4;
      ctx.setTransform(1, 0, 0, 1, (p.x - camX) * k, (p.y - camY) * k);
      ctx.rotate(p.rot);
      ctx.drawImage(p.img, -s / 2, -s / 2, s, s);
    }
    ctx.restore();
  }

  return {
    spawn,
    update,
    drawBack,
    drawFront,
    setReduced(v) { reduced = !!v; },
    /** 대상이 사라졌을 때 그 잔상을 지운다 */
    forget(target) { for (let i = ghosts.length - 1; i >= 0; i--) if (ghosts[i].target === target) ghosts.splice(i, 1); },
    clear() { particles.length = 0; ghosts.length = 0; streaks.length = 0; sprites.clear(); },
    get active() { return particles.length + ghosts.length + streaks.length; },
    get counts() { return { particles: particles.length, ghosts: ghosts.length, streaks: streaks.length, sprites: sprites.size, ...stats }; },
  };
}
