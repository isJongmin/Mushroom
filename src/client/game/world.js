// 맵 그리기 (ARCHITECTURE "복셀 아트 계약" 맵, art-20261015-voxel-map.md 4장).
// 좌표는 월드 단위, 그리기는 백킹 해상도(장치 px) 컨텍스트에 변환 없이(setTransform 단위행렬) 한다.
// k = 장치 px / 월드 1단위 = (P / 2) x dpr. 레이어 경계는 장치 px 정수로 반올림해 반복 타일 사이 틈을 없앤다.
// 레이어: 배열 앞쪽이 뒤. x 오프셋 = -camX x parallax (월드). repeatX면 월드 너비(w = px / density) 주기로 시야 끝까지 반복.
// stretchX(하늘)는 parallax와 상관없이 시야 전체 너비로 늘린다. 스무딩 켬(quality high).
// 매니페스트가 없으면 팔레트 단색 도형으로 그린다 (폴백).
import { PAL, WORLD, FOOT_SHADOW } from '../constants.js';
import { smooth } from '../avatar.js';

const R = Math.round;

/** 레이어 하나를 그린다. */
export function drawLayer(ctx, layer, camX, camY, k, Wd) {
  const img = layer.img;
  const iw = img.naturalWidth;
  const ih = img.naturalHeight;
  const y0 = R((layer.y - camY) * k);
  const y1 = R((layer.y + layer.h - camY) * k);
  if (y1 <= y0) return;
  if (layer.stretchX) {
    if (y0 > 0) ctx.drawImage(img, 0, 0, iw, 1, 0, 0, Wd, y0); // 시야가 월드 위로 넘치면 첫 행을 늘려 채운다
    ctx.drawImage(img, 0, 0, iw, ih, 0, y0, Wd, y1 - y0);
    return;
  }
  const tw = layer.w * k;
  let start = -camX * layer.parallax * k;
  if (layer.repeatX) {
    start %= tw;
    if (start > 0) start -= tw;
    for (let i = 0; start + i * tw < Wd; i++) {
      const xa = R(start + i * tw);
      const xb = R(start + (i + 1) * tw);
      if (xb > xa) ctx.drawImage(img, 0, 0, iw, ih, xa, y0, xb - xa, y1 - y0);
    }
  } else if (start < Wd && start + tw > 0) {
    const xa = R(start);
    ctx.drawImage(img, 0, 0, iw, ih, xa, y0, R(start + tw) - xa, y1 - y0);
  }
}

// 폴백: 하늘 밴드, 먼 언덕, 잔디/흙 (월드 단위)
const SKY_BANDS = [[PAL.k1, -400, 120], [PAL.k2, 120, 210], [PAL.k3, 210, 280], [PAL.k4, 280, 340], [PAL.k5, 340, 440]];

export function drawFallbackMap(ctx, camX, camY, k, Wd, Hd, groundY = WORLD.groundY) {
  const off = groundY - WORLD.groundY; // (사이클 9) 큰 맵: 하늘/언덕을 지면 기준으로 내린다
  const rect = (col, x, y, w, h) => { ctx.fillStyle = col; ctx.fillRect(R(x * k), R(y * k), Math.ceil(w * k), Math.ceil(h * k)); };
  for (const [col, y0, y1] of SKY_BANDS) rect(col, 0, y0 + off - camY - (y0 === -400 ? 2000 : 0), Wd / k, y1 - y0 + (y0 === -400 ? 2000 : 0));
  for (const [col, base, a, b, par] of [[PAL.m1, 330, 120, 46, 0.2], [PAL.m2, 380, 90, 34, 0.3]]) {
    const ox = camX * par;
    const bb = base + off;
    for (let x = 0; x < Wd / k; x += 4) {
      const hy = bb + Math.sin((x + ox) / a) * 20 + Math.sin((x + ox) / b + 1.3) * 10;
      rect(col, x, hy - camY, 4, groundY - hy);
    }
  }
  const g = groundY - camY;
  rect(PAL.g1, 0, g, Wd / k, 2);
  rect(PAL.g2, 0, g + 2, Wd / k, 10);
  rect(PAL.g4, 0, g + 12, Wd / k, 4);
  rect(PAL.w3, 0, g + 16, Wd / k, Math.max(0, Hd / k - (g + 16)));
}

/**
 * 시야 전체를 그린다: 바탕 채움 → 맵 레이어(또는 폴백).
 * @param map loadMapAssets() 결과
 * @param camX,camY 시야 왼쪽 위 (월드)
 * @param k 장치 px / 월드 단위
 * @param Wd,Hd 캔버스 백킹 크기 (장치 px)
 */
export function drawMap(ctx, map, camX, camY, k, Wd, Hd) {
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  smooth(ctx);
  ctx.fillStyle = PAL.k1;
  ctx.fillRect(0, 0, Wd, Hd);
  if (map && map.layers.length) {
    for (const layer of map.layers) drawLayer(ctx, layer, camX, camY, k, Wd);
  } else {
    drawFallbackMap(ctx, camX, camY, k, Wd, Hd, map && typeof map.groundY === 'number' ? map.groundY : WORLD.groundY);
  }
}

/**
 * 발 그림자: 기준점 아래 반투명 타원 (월드 rx 22, ry 5, 알파 0.25). x, y, k는 ctx 단위.
 * (사이클 6) 그림자는 지면에 그대로 두고, 점프 높이 h(월드)에 따라 작고 흐려진다: 최고 높이(105)에서 크기 55%, 알파 35%.
 */
export function drawFootShadow(ctx, x, y, k, h = 0) {
  const t = Math.min(1, Math.max(0, h / 105));
  const s = 1 - 0.45 * t;
  ctx.save();
  ctx.globalAlpha = 1 - 0.65 * t;
  ctx.fillStyle = FOOT_SHADOW.color;
  ctx.beginPath();
  ctx.ellipse(x, y, FOOT_SHADOW.rx * k * s, FOOT_SHADOW.ry * k * s, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

/**
 * 카메라 (월드 단위): 플레이어를 가로 가운데. 세로는 camY(없으면 화면 아래 끝 = 월드 bottomY(540)). k로 장치 px 정수에 맞춘다.
 */
export function cameraFor(playerX, viewW, viewH, k, camYIn, world = WORLD) {
  // (사이클 10) 맵이 시야보다 좁으면 가운데 정렬(양옆은 바탕색), 넓으면 0 ~ width - viewW로 자른다
  let camX = world.width <= viewW ? (world.width - viewW) / 2 : Math.min(Math.max(playerX - viewW / 2, 0), world.width - viewW);
  let camY = typeof camYIn === 'number' && Number.isFinite(camYIn) ? camYIn : world.bottomY - viewH;
  if (k > 0) { camX = R(camX * k) / k; camY = R(camY * k) / k; }
  return { camX, camY };
}

/**
 * (사이클 8) 세로 카메라 목표: 기준 발 높이 refY가 시야 위에서 66% 지점에 오도록 하되,
 * 아래로는 지금 구도(화면 아래 끝 = 월드 540)를 넘지 않고 위로는 맵 위 끝(top)을 넘지 않는다(하늘 위 빈 곳 안 보임).
 * 지면 근처(refY 440)에서는 지금 구도 그대로다. 시야가 맵 세로보다 크면 지금 구도 고정.
 */
export const CAM_FOOT_RATIO = 0.66;
export function camYTarget(refY, viewH, top = 0, bottomY = WORLD.bottomY) {
  const base = bottomY - viewH;
  if (base <= top) return base;
  return Math.min(base, Math.max(top, refY - viewH * CAM_FOOT_RATIO));
}

/** QA/디버그용 발판 윤곽 (sessionStorage mushroom.debug.platforms = '1'일 때만 화면이 부른다) */
export function drawPlatformDebug(ctx, platforms, camX, camY, k) {
  ctx.save();
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  for (const p of platforms) {
    const x = R((p.x1 - camX) * k);
    const w = R((p.x2 - camX) * k) - x;
    const y = R((p.y - camY) * k);
    ctx.fillStyle = 'rgba(94, 54, 32, 0.85)';
    ctx.fillRect(x, y, w, Math.max(2, R(10 * k)));
    ctx.fillStyle = 'rgba(108, 196, 67, 0.95)';
    ctx.fillRect(x, y, w, Math.max(2, R(3 * k)));
  }
  ctx.restore();
}

/**
 * (사이클 9) 맵 manifest(width, height, groundY, spawn)에서 월드 값을 만든다. 값이 없으면 기존 2400 / 540 / 440.
 * height가 없으면 groundY 440일 때 540, 그 밖은 groundY + 100. spawn = { x, y } (y 없으면 groundY).
 * @returns { width, height, groundY, bottomY, minX, maxX, speed, maxDt, minViewH, spawn: { x, y } | null }
 */
export function worldFromMap(map) {
  const n = (v, lo, hi) => (typeof v === 'number' && Number.isFinite(v) && v >= lo && v <= hi ? v : null);
  const width = n(map && map.width, 400, 40000) ?? WORLD.width;
  const groundY = n(map && map.groundY, 60, 20000) ?? WORLD.groundY;
  let height = n(map && map.height, groundY + 10, 40000);
  if (height === null) height = groundY === WORLD.groundY ? WORLD.height : groundY + 100;
  const minX = WORLD.minX;
  const maxX = Math.max(minX + 1, width - (WORLD.width - WORLD.maxX));
  let spawn = null;
  let sp = map && map.spawn;
  if (Array.isArray(sp)) sp = sp.length ? sp[Math.floor(Math.random() * sp.length)] : null;
  if (sp && typeof sp === 'object' && n(sp.x, -1e6, 1e6) !== null) {
    const y = n(sp.y, 0, groundY);
    spawn = { x: Math.min(maxX, Math.max(minX, sp.x)), y: y === null ? groundY : y };
  }
  return Object.freeze({
    width, height, groundY, bottomY: height, minX, maxX, speed: WORLD.speed, maxDt: WORLD.maxDt, minViewH: WORLD.minViewH, spawn,
  });
}

/** (사이클 10) ?debug 로프 선 (그림은 아트 ground 레이어에 같은 좌표로 있다) */
export function drawRopeDebug(ctx, ropes, camX, camY, k) {
  ctx.save();
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.lineCap = 'round';
  for (const r of ropes) {
    const x = R((r.x - camX) * k);
    ctx.strokeStyle = 'rgba(232, 72, 62, 0.9)';
    ctx.lineWidth = Math.max(2, R(3 * k));
    ctx.beginPath(); ctx.moveTo(x, R((r.y1 - camY) * k)); ctx.lineTo(x, R((r.y2 - camY) * k)); ctx.stroke();
    ctx.strokeStyle = 'rgba(232, 72, 62, 0.35)'; // 잡는 범위 ±12
    ctx.lineWidth = 1;
    ctx.strokeRect(R((r.x - 12 - camX) * k), R((r.y1 - camY) * k), R(24 * k), R((r.y2 - r.y1) * k));
  }
  ctx.restore();
}
