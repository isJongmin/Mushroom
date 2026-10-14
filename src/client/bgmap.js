// 로그인/캐릭터 생성 화면 배경: 게임 맵 레이어 재사용 (screens/login.md 2.1).
// - 레이어마다 아트 해상도 캔버스 1장을 만들고 CSS로 P배 확대한다 (image-rendering: pixelated).
// - 카메라 왕복(초당 10 아트 px)은 Web Animations API의 steps()로 정수 아트 px 단위로만 움직인다.
//   JS 프레임 루프(rAF)를 쓰지 않으므로 숨은 탭에서는 브라우저가 알아서 멈춘다.
// - prefers-reduced-motion이면 camX = 300 고정.
import { h } from './dom.js';
import { ART, pixelScale } from './constants.js';
import { drawFallbackMap, drawLayer } from './game/world.js';

const PAN_SPEED = 10; // 아트 px / 초
const STILL_CAM_X = 300;

export function createBackgroundMap(mapPromise) {
  const ac = new AbortController();
  const el = h('div', { class: 'bg-map', 'aria-hidden': 'true' });
  document.body.prepend(el);
  let map = null;
  let anims = [];
  let alive = true;
  let resizeTimer = 0;
  const reduce = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;

  function build() {
    if (!alive || !map) return;
    for (const a of anims) a.cancel();
    anims = [];
    el.replaceChildren();
    const vw = document.documentElement.clientWidth || window.innerWidth;
    const vh = window.innerHeight || document.documentElement.clientHeight;
    const P = pixelScale(vw, vh);
    const viewW = Math.ceil(vw / P);
    const viewH = Math.ceil(vh / P);
    const camY = ART.bottomY - viewH;
    const range = Math.max(0, ART.width - viewW);
    const still = !!(reduce && reduce.matches) || typeof el.animate !== 'function';
    const camStill = Math.min(STILL_CAM_X, range);
    const duration = (range / PAN_SPEED) * 1000;
    el.style.width = `${viewW * P}px`;
    el.style.height = `${viewH * P}px`;

    const layers = map.layers.length
      ? map.layers
      : [{ fallback: true, parallax: 1, y: camY, w: ART.width, h: viewH }];
    for (const layer of layers) {
      const travel = Math.floor(range * layer.parallax);
      const cw = Math.min(viewW + travel, 4096);
      const cv = document.createElement('canvas');
      cv.width = cw;
      cv.height = layer.h;
      const c = cv.getContext('2d');
      c.imageSmoothingEnabled = false;
      if (layer.fallback) drawFallbackMap(c, 0, camY, cw, viewH);
      else drawLayer(c, layer, 0, layer.y, cw);
      cv.className = 'bg-layer';
      Object.assign(cv.style, {
        left: '0px',
        top: `${(layer.y - camY) * P}px`,
        width: `${cw * P}px`,
        height: `${layer.h * P}px`,
      });
      el.appendChild(cv);
      if (still) {
        cv.style.transform = `translateX(${-Math.floor(camStill * layer.parallax) * P}px)`;
      } else if (travel > 0 && duration > 0) {
        anims.push(cv.animate(
          [{ transform: 'translateX(0px)' }, { transform: `translateX(${-travel * P}px)` }],
          { duration, iterations: Infinity, direction: 'alternate', easing: `steps(${travel}, end)` },
        ));
      }
    }
    el.classList.add('ready');
  }

  mapPromise.then((m) => {
    if (!alive) return;
    map = m;
    build();
  }, () => { /* 실패하면 k1 바탕 그대로 (경고는 로더가 1회 남긴다) */ });

  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(build, 150);
  }, { signal: ac.signal });
  if (reduce && reduce.addEventListener) reduce.addEventListener('change', build, { signal: ac.signal });

  return {
    destroy() {
      alive = false;
      ac.abort();
      clearTimeout(resizeTimer);
      for (const a of anims) a.cancel();
      anims = [];
      el.remove();
    },
  };
}
