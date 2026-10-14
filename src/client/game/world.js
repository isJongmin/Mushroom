// 맵 그리기 (style-guide 4.3~4.5, 6장). 모든 좌표는 아트 px 정수, 아트 해상도 캔버스(스무딩 끔)에 그린다.
// assets/map/manifest.json 레이어가 있으면 패럴랙스로, 없으면 팔레트 단색 도형으로 그린다 (폴백).
import { PAL, ART } from '../constants.js';

/** 레이어 하나를 그린다. ox = -floor(camX * parallax), repeatX면 시야 끝까지 반복. */
export function drawLayer(ctx, layer, camX, camY, viewW) {
  const ox = -Math.floor(camX * layer.parallax);
  const y = layer.y - camY;
  const w = layer.w;
  if (layer.repeatX) {
    let x = ox % w;
    if (x > 0) x -= w;
    for (; x < viewW; x += w) ctx.drawImage(layer.img, x, y);
  } else if (ox < viewW && ox + w > 0) {
    ctx.drawImage(layer.img, ox, y);
  }
}

// 폴백: 하늘 밴드(6.2), 먼 언덕, 잔디/흙 (6.6 색만 따름)
const SKY_BANDS = [[PAL.k1, 0, 60], [PAL.k2, 60, 105], [PAL.k3, 105, 140], [PAL.k4, 140, 170], [PAL.k5, 170, 220]];

function hillY(x, base, a, b) {
  // 정수 계단 언덕 (난수 없음 → 모든 클라이언트가 같은 풍경)
  return Math.round(base + Math.sin(x / a) * 10 + Math.sin(x / b + 1.3) * 5);
}

export function drawFallbackMap(ctx, camX, camY, viewW, viewH) {
  for (const [col, y0, y1] of SKY_BANDS) {
    ctx.fillStyle = col;
    ctx.fillRect(0, y0 - camY, viewW, y1 - y0);
  }
  // 먼 산 (parallax 0.2), 언덕 (0.3)
  for (const [col, top, base, a, b, par] of [[PAL.m1, PAL.white, 160, 60, 23, 0.2], [PAL.m2, PAL.m1, 190, 45, 17, 0.3]]) {
    const ox = Math.floor(camX * par);
    for (let x = 0; x < viewW; x++) {
      const hy = hillY(x + ox, base, a, b);
      ctx.fillStyle = top;
      ctx.fillRect(x, hy - camY, 1, 1);
      ctx.fillStyle = col;
      ctx.fillRect(x, hy + 1 - camY, 1, ART.groundY - hy);
    }
  }
  // 지면 (잔디 윗면 = y 220)
  const g = ART.groundY - camY;
  ctx.fillStyle = PAL.g1; ctx.fillRect(0, g, viewW, 1);
  ctx.fillStyle = PAL.g2; ctx.fillRect(0, g + 1, viewW, 5);
  ctx.fillStyle = PAL.g3; ctx.fillRect(0, g + 6, viewW, 1);
  ctx.fillStyle = PAL.g4; ctx.fillRect(0, g + 7, viewW, 2);
  ctx.fillStyle = PAL.w3; ctx.fillRect(0, g + 9, viewW, Math.max(0, viewH - (g + 9)));
  // 흙 반점 (16px 격자)
  ctx.fillStyle = PAL.w4;
  const start = Math.floor(camX / 16) * 16;
  for (let wx = start; wx < camX + viewW + 16; wx += 16) {
    const k = (wx / 16) | 0;
    ctx.fillRect(wx - camX + (k * 7) % 12, g + 14 + (k * 5) % 9, 2, 1);
    ctx.fillRect(wx - camX + (k * 11) % 13, g + 30 + (k * 3) % 8, 2, 1);
  }
}

/**
 * 시야 전체를 그린다: k1 채움 → 맵 레이어(또는 폴백).
 * @param map loadMapAssets() 결과
 */
export function drawMap(ctx, map, camX, camY, viewW, viewH) {
  ctx.fillStyle = PAL.k1;
  ctx.fillRect(0, 0, viewW, viewH);
  if (map && map.layers.length) {
    for (const layer of map.layers) drawLayer(ctx, layer, camX, camY, viewW);
  } else {
    drawFallbackMap(ctx, camX, camY, viewW, viewH);
  }
}

/** style-guide 4.5-3: 발 그림자 (기준점 아트 x, 지면 y) */
export function drawFootShadow(ctx, ax, groundY) {
  ctx.fillStyle = PAL.g3;
  ctx.fillRect(ax - 6, groundY, 12, 1);
  ctx.fillRect(ax - 5, groundY + 1, 10, 1);
}

/** style-guide 4.3 카메라 */
export function cameraFor(playerArtX, viewW, viewH) {
  const camX = Math.min(Math.max(Math.round(playerArtX - viewW / 2), 0), Math.max(0, ART.width - viewW));
  const camY = ART.bottomY - viewH;
  return { camX, camY };
}
