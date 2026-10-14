// 월드 배경. assets/map/background.svg가 있으면 월드 크기(2400x540)로 래스터화해 캐시하고,
// 없으면 style-guide 1.1 팔레트로 하늘/구름/언덕/잔디/흙을 직접 그린다(폴백).
import { COLORS, WORLD } from '../constants.js';

const MAX_BG_PIXELS = 16_000_000;
const MAX_BG_SIDE = 16384;

// 고정 배치(난수 없음 → 모든 클라이언트가 같은 풍경)
const CLOUDS = [
  [140, 70, 1.0], [520, 120, 0.8], [860, 60, 1.2], [1180, 110, 0.9], [1500, 70, 1.1],
  [1820, 130, 0.8], [2150, 80, 1.0], [2350, 150, 0.7],
];

function drawCloud(c, x, y, s) {
  // 타원마다 경로를 새로 시작해야 서브패스 사이 연결선(삼각형 잔상)이 생기지 않는다
  for (const [dx, dy, rx, ry] of [[0, 0, 46, 18], [-26, 4, 26, 14], [28, 5, 24, 13], [4, -12, 24, 16]]) {
    c.beginPath();
    c.ellipse(x + dx * s, y + dy * s, rx * s, ry * s, 0, 0, Math.PI * 2);
    c.fill();
  }
}

function drawProcedural(c, x0, x1) {
  const g = c.createLinearGradient(0, 0, 0, WORLD.groundY);
  g.addColorStop(0, COLORS.skyTop);
  g.addColorStop(1, COLORS.skyBottom);
  c.fillStyle = g;
  c.fillRect(x0, 0, x1 - x0, WORLD.groundY);

  c.fillStyle = COLORS.cloud;
  for (const [cx, cy, s] of CLOUDS) if (cx + 90 * s > x0 && cx - 90 * s < x1) drawCloud(c, cx, cy, s);

  // 먼 언덕
  c.fillStyle = COLORS.hillFar;
  c.beginPath();
  const step = 20;
  const start = Math.max(0, Math.floor(x0 / step) * step - step);
  const end = Math.min(WORLD.width, x1 + step);
  c.moveTo(start, WORLD.groundY);
  for (let x = start; x <= end; x += step) {
    const y = 360 + Math.sin(x / 190) * 28 + Math.sin(x / 73 + 1.3) * 10;
    c.lineTo(x, y);
  }
  c.lineTo(end, WORLD.groundY);
  c.closePath();
  c.fill();

  // 잔디 띠 440~468
  const w = x1 - x0;
  c.fillStyle = COLORS.grass;
  c.fillRect(x0, WORLD.groundY, w, WORLD.grassBottom - WORLD.groundY);
  c.fillStyle = COLORS.grassLight;
  c.fillRect(x0, WORLD.groundY, w, 1);
  c.fillStyle = COLORS.grassDark;
  c.fillRect(x0, WORLD.grassBottom - 4, w, 4);
  // 흙 468~540
  c.fillStyle = COLORS.soil;
  c.fillRect(x0, WORLD.grassBottom, w, WORLD.height - WORLD.grassBottom);
  c.fillStyle = COLORS.soilLight;
  c.fillRect(x0, WORLD.grassBottom, w, 3);
  c.fillStyle = COLORS.soilDark;
  c.fillRect(x0, WORLD.height - 14, w, 14);
  // 자갈 몇 개
  c.fillStyle = COLORS.soilDark;
  for (let x = Math.floor(x0 / 97) * 97; x < x1; x += 97) {
    c.beginPath();
    c.ellipse(x + ((x * 7) % 40), 492 + ((x * 13) % 22), 4, 2.5, 0, 0, Math.PI * 2);
    c.fill();
  }
}

export function createWorldRenderer(assets) {
  let bg = null; // { canvas, k }

  function bgFor(k) {
    if (!assets.background) return null;
    let kk = k;
    if (WORLD.width * kk > MAX_BG_SIDE) kk = MAX_BG_SIDE / WORLD.width;
    if (WORLD.width * WORLD.height * kk * kk > MAX_BG_PIXELS) kk = Math.sqrt(MAX_BG_PIXELS / (WORLD.width * WORLD.height));
    if (bg && Math.abs(bg.k - kk) < 1e-3) return bg.canvas;
    const cv = document.createElement('canvas');
    cv.width = Math.ceil(WORLD.width * kk);
    cv.height = Math.ceil(WORLD.height * kk);
    const c = cv.getContext('2d');
    try {
      c.drawImage(assets.background, 0, 0, cv.width, cv.height);
    } catch {
      return null;
    }
    bg = { canvas: cv, k: kk };
    return cv;
  }

  return {
    get usingSvg() {
      return !!assets.background;
    },
    /** ctx는 CSS px 좌표계. s = 논리→CSS 배율. */
    draw(ctx, camX, camY, viewW, viewH, s, dpr) {
      ctx.save();
      ctx.scale(s, s);
      ctx.translate(-camX, -camY);
      drawProcedural(ctx, camX, camX + viewW);
      const bgc = bgFor(s * dpr);
      if (bgc) ctx.drawImage(bgc, 0, 0, WORLD.width, WORLD.height);
      ctx.restore();
    },
    reset() {
      bg = null;
    },
  };
}
