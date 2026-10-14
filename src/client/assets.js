// 아트 에셋 로더 (ARCHITECTURE "픽셀아트 계약").
// - assets/avatar/manifest.json + 파츠 PNG 시트 (192x48, 6프레임)
// - assets/map/manifest.json + 레이어 PNG
// - assets/ui/manifest.json + 9-slice 스킨 PNG (DOM은 CSS 변수로, Canvas는 이미지로)
// 매니페스트나 개별 PNG가 없거나 깨지면 그 부분만 단색 도형 폴백으로 그린다 (avatar.js, game/world.js, CSS).
// 경로는 모두 이 모듈 기준 상대 경로라 GitHub Pages 하위 경로(/Mushroom/)에서도 동작한다.
import {
  DEFAULT_PARTS, DEFAULT_LAYER_ORDER, DEFAULT_AVATAR, DEFAULT_ALIASES, PART_KEYS, PART_ID_RE, AVATAR,
} from './constants.js';

const REPO_ROOT = new URL('../../', import.meta.url);
const ASSET_ROOT = new URL('assets/', REPO_ROOT);
const IMAGE_TIMEOUT_MS = 8000;
// 매니페스트가 가리키는 파일은 assets/ 아래 PNG만 허용한다
const SRC_RE = /^assets\/[a-z0-9_\-/]+\.png$/i;

const warned = new Set();
function warnOnce(key, ...args) {
  if (warned.has(key)) return;
  warned.add(key);
  console.warn('[버섯마을 에셋]', ...args);
}

export function loadImage(url) {
  return new Promise((resolve) => {
    const img = new Image();
    let done = false;
    const finish = (ok) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      img.onload = img.onerror = null;
      resolve(ok && img.naturalWidth > 0 ? img : null);
    };
    const timer = setTimeout(() => finish(false), IMAGE_TIMEOUT_MS);
    img.onload = () => {
      if (typeof img.decode === 'function') img.decode().then(() => finish(true), () => finish(true));
      else finish(true);
    };
    img.onerror = () => finish(false);
    img.decoding = 'async';
    img.src = url.href;
  });
}

async function fetchJson(url) {
  try {
    const res = await fetch(url.href, { cache: 'no-cache' });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

function resolveSrc(src) {
  if (typeof src !== 'string' || !SRC_RE.test(src) || src.includes('..')) return null;
  return new URL(src, REPO_ROOT);
}

const posInt = (v, d) => (Number.isInteger(v) && v > 0 ? v : d);
const num = (v, d) => (typeof v === 'number' && Number.isFinite(v) ? v : d);

// ---------------------------------------------------------------------------
// 아바타

function normalizeAnimations(raw) {
  const out = {};
  for (const name of ['idle', 'walk']) {
    const a = raw && raw[name];
    const frames = a && Array.isArray(a.frames) ? a.frames.filter((f) => Number.isInteger(f) && f >= 0 && f < 64) : [];
    out[name] = frames.length
      ? { frames, ms: posInt(a.ms, AVATAR.animations[name].ms) }
      : { frames: [...AVATAR.animations[name].frames], ms: AVATAR.animations[name].ms };
  }
  return out;
}

/** aliases: { "<oldId>": "<newId>" } 또는 { "<part>": { "<oldId>": "<newId>" } } 둘 다 받는다. */
function normalizeAliases(raw) {
  const out = Object.fromEntries(PART_KEYS.map((p) => [p, { ...(DEFAULT_ALIASES[p] || {}) }]));
  if (!raw || typeof raw !== 'object') return out;
  for (const [k, v] of Object.entries(raw)) {
    if (PART_KEYS.includes(k) && v && typeof v === 'object') {
      for (const [from, to] of Object.entries(v)) {
        if (PART_ID_RE.test(from) && typeof to === 'string' && PART_ID_RE.test(to)) out[k][from] = to;
      }
    } else if (PART_ID_RE.test(k) && typeof v === 'string' && PART_ID_RE.test(v)) {
      const part = PART_KEYS.find((p) => k.startsWith(p + '-') || v.startsWith(p + '-'));
      if (part) out[part][k] = v;
    }
  }
  return out;
}

/** 계약 형식인지 확인한다. 사이클 1 형식(canvas 64x96, SVG)은 계약이 아니므로 null. */
function normalizeAvatarManifest(raw) {
  if (!raw || typeof raw !== 'object' || !raw.frame || typeof raw.frame !== 'object') return null;
  const parts = {};
  let count = 0;
  for (const part of PART_KEYS) {
    const list = raw.parts && Array.isArray(raw.parts[part]) ? raw.parts[part] : [];
    const clean = list
      .filter((o) => o && typeof o.id === 'string' && PART_ID_RE.test(o.id))
      .map((o) => ({ id: o.id, label: typeof o.label === 'string' && o.label.trim() ? o.label.trim().slice(0, 40) : o.id }));
    parts[part] = clean.length ? clean : DEFAULT_PARTS[part].map((o) => ({ ...o }));
    count += clean.length;
  }
  if (!count) return null;
  const lo = Array.isArray(raw.layerOrder) ? raw.layerOrder.filter((p) => PART_KEYS.includes(p)) : [];
  const layerOrder = lo.length === PART_KEYS.length && new Set(lo).size === PART_KEYS.length ? lo : [...DEFAULT_LAYER_ORDER];
  const frame = { w: posInt(raw.frame.w, AVATAR.frameW), h: posInt(raw.frame.h, AVATAR.frameH) };
  const anchor = {
    x: num(raw.anchor && raw.anchor.x, AVATAR.anchorX),
    y: num(raw.anchor && raw.anchor.y, AVATAR.anchorY),
  };
  return { parts, layerOrder, frame, anchor, animations: normalizeAnimations(raw.animations), aliases: normalizeAliases(raw.aliases) };
}

/**
 * @returns Promise<{
 *   source: 'manifest'|'fallback', parts, layerOrder, frame, anchor, animations, frameCount,
 *   images: Map<'part/id', HTMLImageElement>, imageCount, defaultAvatar,
 *   sanitizeAvatar(avatar), labelOf(part, id)
 * }>
 */
export async function loadAvatarAssets() {
  const manifest = normalizeAvatarManifest(await fetchJson(new URL('avatar/manifest.json', ASSET_ROOT)));
  const base = manifest || {
    parts: Object.fromEntries(PART_KEYS.map((p) => [p, DEFAULT_PARTS[p].map((o) => ({ ...o }))])),
    layerOrder: [...DEFAULT_LAYER_ORDER],
    frame: { w: AVATAR.frameW, h: AVATAR.frameH },
    anchor: { x: AVATAR.anchorX, y: AVATAR.anchorY },
    animations: normalizeAnimations(null),
    aliases: normalizeAliases(null),
  };
  const frameCount = Math.max(AVATAR.frames, ...base.animations.idle.frames.map((f) => f + 1), ...base.animations.walk.frames.map((f) => f + 1));

  const images = new Map();
  if (manifest) {
    // 매니페스트에 있는 파일만 요청한다(매니페스트가 없으면 PNG 요청 자체를 하지 않는다)
    const jobs = [];
    for (const part of PART_KEYS) {
      for (const { id } of base.parts[part]) {
        jobs.push(loadImage(new URL(`avatar/${part}/${id}.png`, ASSET_ROOT)).then((img) => {
          if (img && img.naturalWidth >= base.frame.w && img.naturalHeight >= base.frame.h) images.set(`${part}/${id}`, img);
          else warnOnce(`avatar:${part}`, `파츠 시트를 불러오지 못했습니다: ${part}/${id}.png (단색 폴백으로 그립니다)`);
        }));
      }
    }
    await Promise.all(jobs);
  } else {
    warnOnce('avatar:manifest', 'assets/avatar/manifest.json이 없거나 계약 형식이 아닙니다 (단색 폴백으로 그립니다)');
  }

  const idSets = Object.fromEntries(PART_KEYS.map((p) => [p, new Set(base.parts[p].map((o) => o.id))]));
  const defaultAvatar = {};
  for (const p of PART_KEYS) defaultAvatar[p] = idSets[p].has(DEFAULT_AVATAR[p]) ? DEFAULT_AVATAR[p] : base.parts[p][0].id;

  return Object.freeze({
    source: manifest ? 'manifest' : 'fallback',
    parts: base.parts,
    layerOrder: base.layerOrder,
    frame: base.frame,
    anchor: base.anchor,
    animations: base.animations,
    frameCount,
    images,
    imageCount: images.size,
    defaultAvatar,
    /** 네트워크/DB에서 온 아바타를 목록에 있는 id로만 구성한다 (예전 id는 별칭, 없는 id는 기본값). 저장 값은 바꾸지 않는다. */
    sanitizeAvatar(avatar) {
      const out = {};
      for (const p of PART_KEYS) {
        let v = avatar && typeof avatar === 'object' ? avatar[p] : undefined;
        if (typeof v === 'string' && !idSets[p].has(v) && base.aliases[p][v]) v = base.aliases[p][v];
        out[p] = typeof v === 'string' && idSets[p].has(v) ? v : defaultAvatar[p];
      }
      return out;
    },
    labelOf(part, id) {
      const o = base.parts[part] && base.parts[part].find((x) => x.id === id);
      return o ? o.label : id;
    },
  });
}

// ---------------------------------------------------------------------------
// 맵

/**
 * @returns Promise<{ source: 'manifest'|'fallback', layers: [{ img, parallax, y, repeatX, w, h }], groundImg }>
 * 실패한 레이어는 빠진다 (그 레이어만 빼고 그린다, screens/game.md 7.1).
 */
export async function loadMapAssets() {
  const raw = await fetchJson(new URL('map/manifest.json', ASSET_ROOT));
  const list = raw && Array.isArray(raw.layers) ? raw.layers : null;
  if (!list || !list.length) {
    warnOnce('map:manifest', 'assets/map/manifest.json이 없습니다 (단색 맵으로 그립니다)');
    return Object.freeze({ source: 'fallback', layers: [], groundImg: null, layerCount: 0 });
  }
  const specs = list.slice(0, 16).map((l) => {
    const url = l && resolveSrc(l.src);
    if (!url) return null;
    return {
      url,
      name: l.src,
      parallax: Math.min(1, Math.max(0, num(l.parallax, 1))),
      y: Math.round(num(l.y, 0)),
      repeatX: l.repeatX === true,
    };
  });
  const loaded = await Promise.all(specs.map(async (s) => {
    if (!s) return null;
    const img = await loadImage(s.url);
    if (!img) { warnOnce(`map:${s.name}`, `맵 레이어를 불러오지 못했습니다: ${s.name}`); return null; }
    return { img, parallax: s.parallax, y: s.y, repeatX: s.repeatX, w: img.naturalWidth, h: img.naturalHeight, name: s.name };
  }));
  const layers = loaded.filter(Boolean);
  const ground = layers.find((l) => /ground\.png$/i.test(l.name)) || null;
  return Object.freeze({ source: layers.length ? 'manifest' : 'fallback', layers, groundImg: ground ? ground.img : null, groundY: ground ? ground.y : 216, layerCount: layers.length });
}

// ---------------------------------------------------------------------------
// UI 스킨

const UI_DEFAULT_SLICE = { panel: 8, 'button-primary': 8, 'button-secondary': 8, input: 4, chip: 3, bubble: 4, 'label-other': 3, 'label-self': 3 };

function sliceOf(entry, name) {
  const s = entry && Array.isArray(entry.slice) ? entry.slice : null;
  const v = s && Number.isInteger(s[0]) && s[0] > 0 && s[0] <= 32 ? s[0] : UI_DEFAULT_SLICE[name];
  return v;
}

/**
 * UI 스킨을 불러와 CSS 변수(:root)와 html 클래스(skin-panel, skin-btn, skin-input, skin-chip, skin-icons)를 설정한다.
 * 실패한 부분은 CSS 대체 스타일(단색 + 2px 외곽선)로 남는다.
 * @returns Promise<{ source, nine: { bubble, 'label-other', 'label-self' }: {img, slice}, sprites: { 'bubble-tail', ... } }>
 */
export async function loadUiAssets() {
  const raw = await fetchJson(new URL('ui/manifest.json', ASSET_ROOT));
  const empty = Object.freeze({ source: 'fallback', nine: {}, sprites: {}, count: 0 });
  if (!raw || typeof raw !== 'object' || !raw.nine || typeof raw.nine !== 'object') {
    warnOnce('ui:manifest', 'assets/ui/manifest.json이 없습니다 (CSS 대체 스타일로 그립니다)');
    return empty;
  }
  const jobs = [];
  const result = { nine: {}, sprites: {}, css: {} };
  const want = (key, src) => {
    const url = resolveSrc(src);
    if (!url) return Promise.resolve(null);
    const p = loadImage(url).then((img) => {
      if (!img) warnOnce(`ui:${key}`, `UI 스킨을 불러오지 못했습니다: ${src}`);
      return img ? { img, url } : null;
    });
    jobs.push(p);
    return p;
  };

  const nine = raw.nine;
  const single = (name) => {
    const e = nine[name];
    if (!e || typeof e !== 'object') return;
    want(name, e.src).then((r) => { if (r) result.nine[name] = { img: r.img, url: r.url, slice: sliceOf(e, name) }; });
  };
  const states = (name, keys) => {
    const e = nine[name];
    if (!e || typeof e !== 'object' || !e.states || typeof e.states !== 'object') return;
    const slice = sliceOf(e, name);
    const shift = Number.isInteger(e.pressedShift) && e.pressedShift >= 0 && e.pressedShift <= 8 ? e.pressedShift : 2;
    result.nine[name] = { slice, shift, states: {} };
    for (const k of keys) {
      want(`${name}.${k}`, e.states[k]).then((r) => { if (r) result.nine[name].states[k] = { img: r.img, url: r.url }; });
    }
  };
  for (const n of ['panel', 'chip', 'bubble', 'label-other', 'label-self']) single(n);
  states('button-primary', ['normal', 'hover', 'pressed', 'disabled']);
  states('button-secondary', ['normal', 'hover', 'pressed', 'disabled']);
  states('input', ['normal', 'focus', 'error', 'disabled']);
  const sprites = raw.sprites && typeof raw.sprites === 'object' ? raw.sprites : {};
  for (const n of ['bubble-tail', 'icon-mushroom', 'icon-arrow']) {
    want(n, sprites[n]).then((r) => { if (r) result.sprites[n] = { img: r.img, url: r.url }; });
  }
  await Promise.all(jobs);
  // 마지막 .then 콜백까지 끝나도록 한 틱 양보
  await Promise.resolve();
  applyUiCss(result);
  const count = jobs.length;
  return Object.freeze({ source: 'manifest', nine: result.nine, sprites: result.sprites, count });
}

function applyUiCss(r) {
  const root = document.documentElement;
  const set = (k, v) => root.style.setProperty(k, v);
  const url = (u) => `url("${u.href}")`;
  const cls = [];
  const n = r.nine;
  if (n.panel) {
    set('--ui-panel', url(n.panel.url));
    set('--ui-panel-slice', String(n.panel.slice));
    cls.push('skin-panel');
  }
  const btn = (name, short) => {
    const e = n[name];
    if (!e || !e.states.normal) return false;
    for (const k of ['normal', 'hover', 'pressed', 'disabled']) {
      const st = e.states[k] || (k === 'disabled' && n['button-primary'] && n['button-primary'].states.disabled) || e.states.normal;
      set(`--ui-${short}-${k}`, url(st.url));
    }
    set(`--ui-${short}-slice`, String(e.slice));
    set(`--ui-${short}-shift`, `${e.shift * 2}px`);
    return true;
  };
  const okP = btn('button-primary', 'btnp');
  const okS = btn('button-secondary', 'btns');
  if (okP && okS) cls.push('skin-btn');
  if (n.input && n.input.states.normal) {
    for (const k of ['normal', 'focus', 'error', 'disabled']) set(`--ui-input-${k}`, url((n.input.states[k] || n.input.states.normal).url));
    set('--ui-input-slice', String(n.input.slice));
    cls.push('skin-input');
  }
  if (n.chip) {
    set('--ui-chip', url(n.chip.url));
    set('--ui-chip-slice', String(n.chip.slice));
    cls.push('skin-chip');
  }
  if (r.sprites['icon-mushroom']) { set('--ui-icon-mushroom', url(r.sprites['icon-mushroom'].url)); cls.push('skin-icon-mushroom'); }
  if (r.sprites['icon-arrow']) { set('--ui-icon-arrow', url(r.sprites['icon-arrow'].url)); cls.push('skin-icon-arrow'); }
  root.classList.add(...cls);
}
