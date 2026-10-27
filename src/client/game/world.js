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

export function drawFallbackMap(ctx, camX, camY, k, Wd, Hd) {
  const rect = (col, x, y, w, h) => { ctx.fillStyle = col; ctx.fillRect(R(x * k), R(y * k), Math.ceil(w * k), Math.ceil(h * k)); };
  for (const [col, y0, y1] of SKY_BANDS) rect(col, 0, y0 - camY, Wd / k, y1 - y0);
  for (const [col, base, a, b, par] of [[PAL.m1, 330, 120, 46, 0.2], [PAL.m2, 380, 90, 34, 0.3]]) {
    const ox = camX * par;
    for (let x = 0; x < Wd / k; x += 4) {
      const hy = base + Math.sin((x + ox) / a) * 20 + Math.sin((x + ox) / b + 1.3) * 10;
      rect(col, x, hy - camY, 4, WORLD.groundY - hy);
    }
  }
  const g = WORLD.groundY - camY;
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
    drawFallbackMap(ctx, camX, camY, k, Wd, Hd);
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

/** 카메라 (월드 단위): 플레이어를 가로 가운데, 화면 아래 끝 = 월드 bottomY(540). k로 장치 px 정수에 맞춘다. */
export function cameraFor(playerX, viewW, viewH, k) {
  let camX = Math.min(Math.max(playerX - viewW / 2, 0), Math.max(0, WORLD.width - viewW));
  let camY = WORLD.bottomY - viewH;
  if (k > 0) { camX = R(camX * k) / k; camY = R(camY * k) / k; }
  return { camX, camY };
}
