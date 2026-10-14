// 아트 에셋 로더 (ARCHITECTURE "블록 아트 계약", 사이클 3).
// - assets/avatar/manifest.json + outline.json + 레이어 PNG 시트 (336x64, 7프레임). hair는 hair_back/hair_front 두 장.
// - assets/map/manifest.json + 레이어 PNG
// PNG UI 스킨은 없다(CSS 블록 UI). 매니페스트나 개별 PNG가 없거나 깨지면 그 부분만 빼거나 단색으로 그린다.
// 경로는 모두 이 모듈 기준 상대 경로라 GitHub Pages 하위 경로에서도 동작한다.
import {
  AVATAR, PART_KEYS, PART_ID_RE, DEFAULT_LAYER_ORDER, LAYER_PART, DEFAULT_AVATAR, HAT_NONE, ART,
} from './constants.js';
import { normalizeAvatar } from './avatar-data.js';

const REPO_ROOT = new URL('../../', import.meta.url);
const ASSET_ROOT = new URL('assets/', REPO_ROOT);
const IMAGE_TIMEOUT_MS = 8000;
// 매니페스트가 가리키는 파일은 assets/ 아래 PNG만 허용한다
const SRC_RE = /^assets\/[a-z0-9_\-/]+\.png$/i;
const HEX_RE = /^#[0-9A-Fa-f]{6}$/;

const warned = new Set();
export function warnOnce(key, ...args) {
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

const posInt = (v, d) => (Number.isInteger(v) && v > 0 && v <= 256 ? v : d);
const num = (v, d) => (typeof v === 'number' && Number.isFinite(v) ? v : d);

// ---------------------------------------------------------------------------
// 아바타

function normalizeAnimations(raw, frameCount) {
  const out = {};
  for (const name of ['idle', 'walk']) {
    const a = raw && raw[name];
    const frames = a && Array.isArray(a.frames) ? a.frames.filter((f) => Number.isInteger(f) && f >= 0 && f < frameCount) : [];
    out[name] = frames.length
      ? { frames, ms: posInt(a.ms, AVATAR.animations[name].ms) }
      : { frames: [...AVATAR.animations[name].frames], ms: AVATAR.animations[name].ms };
  }
  return out;
}

/** 선택: manifest aliases ({ part: { old: new } }). 현재 manifest에는 없지만 있으면 받는다. */
function normalizeAliases(raw) {
  const out = Object.fromEntries(PART_KEYS.map((p) => [p, {}]));
  if (!raw || typeof raw !== 'object') return out;
  for (const p of PART_KEYS) {
    const v = raw[p];
    if (!v || typeof v !== 'object') continue;
    for (const [from, to] of Object.entries(v)) {
      if (PART_ID_RE.test(from) && typeof to === 'string' && PART_ID_RE.test(to)) out[p][from] = to;
    }
  }
  return out;
}

function normalizeAvatarManifest(raw) {
  if (!raw || typeof raw !== 'object' || !raw.parts || typeof raw.parts !== 'object') return null;
  const parts = {};
  for (const part of PART_KEYS) {
    const list = Array.isArray(raw.parts[part]) ? raw.parts[part] : [];
    const seen = new Set();
    const clean = [];
    for (const o of list.slice(0, 64)) {
      if (!o || typeof o.id !== 'string' || !PART_ID_RE.test(o.id) || seen.has(o.id)) continue;
      seen.add(o.id);
      clean.push({ id: o.id, label: typeof o.label === 'string' && o.label.trim() ? o.label.trim().slice(0, 40) : o.id });
    }
    if (!clean.length) return null; // 파츠 하나라도 비면 계약 형식이 아니다
    parts[part] = clean;
  }
  const frameNames = Array.isArray(raw.frames) && raw.frames.length && raw.frames.length <= 16 && raw.frames.every((f) => typeof f === 'string')
    ? [...raw.frames] : [...AVATAR.frames];
  const frameCount = frameNames.length;
  const lo = Array.isArray(raw.layerOrder) ? raw.layerOrder.filter((l) => Object.prototype.hasOwnProperty.call(LAYER_PART, l)) : [];
  const layerOrder = lo.length === DEFAULT_LAYER_ORDER.length && new Set(lo).size === lo.length ? lo : [...DEFAULT_LAYER_ORDER];
  const frame = { w: posInt(raw.frame && raw.frame.w, AVATAR.frameW), h: posInt(raw.frame && raw.frame.h, AVATAR.frameH) };
  const anchor = {
    x: Math.round(num(raw.anchor && raw.anchor.x, AVATAR.anchorX)),
    y: Math.round(num(raw.anchor && raw.anchor.y, AVATAR.anchorY)),
  };
  return {
    parts, layerOrder, frame, anchor, frameNames, frameCount,
    animations: normalizeAnimations(raw.animations, frameCount),
    aliases: normalizeAliases(raw.aliases),
    rawPresets: Array.isArray(raw.presets) ? raw.presets.slice(0, 12) : [],
  };
}

function fallbackManifest() {
  const parts = Object.fromEntries(PART_KEYS.map((p) => [p, [{ id: DEFAULT_AVATAR[p], label: DEFAULT_AVATAR[p] }]]));
  return {
    parts,
    layerOrder: [...DEFAULT_LAYER_ORDER],
    frame: { w: AVATAR.frameW, h: AVATAR.frameH },
    anchor: { x: AVATAR.anchorX, y: AVATAR.anchorY },
    frameNames: [...AVATAR.frames],
    frameCount: AVATAR.frames.length,
    animations: normalizeAnimations(null, AVATAR.frames.length),
    aliases: normalizeAliases(null),
    rawPresets: [],
  };
}

/** outline.json → Map<0xRRGGBB, [r,g,b]> */
function parseOutline(raw) {
  const map = new Map();
  if (!raw || typeof raw !== 'object') return map;
  for (const [k, v] of Object.entries(raw)) {
    if (!HEX_RE.test(k) || typeof v !== 'string' || !HEX_RE.test(v)) continue;
    const n = parseInt(v.slice(1), 16);
    map.set(parseInt(k.slice(1), 16), [(n >> 16) & 255, (n >> 8) & 255, n & 255]);
  }
  return map;
}

/** 파츠 id 하나가 쓰는 레이어 목록 (hair → hair_back, hair_front / hat none → 없음) */
export function layersOfPart(part, id, layerOrder = DEFAULT_LAYER_ORDER) {
  if (part === 'hat' && id === HAT_NONE) return [];
  return layerOrder.filter((l) => LAYER_PART[l] === part);
}

/**
 * @returns Promise<{
 *   source: 'manifest'|'fallback', parts, layerOrder, frame, anchor, frameNames, frameCount, frameIndex,
 *   animations, outline: Map, images: Map<'layer/id', HTMLImageElement>, imageCount, imageTotal,
 *   defaultAvatar, presets: [{label, avatar}], sanitizeAvatar(avatar), labelOf(part, id)
 * }>
 */
export async function loadAvatarAssets() {
  const [rawManifest, rawOutline] = await Promise.all([
    fetchJson(new URL('avatar/manifest.json', ASSET_ROOT)),
    fetchJson(new URL('avatar/outline.json', ASSET_ROOT)),
  ]);
  const manifest = normalizeAvatarManifest(rawManifest);
  if (!manifest) warnOnce('avatar:manifest', 'assets/avatar/manifest.json이 없거나 계약 형식이 아닙니다 (단색 대체 아바타로 그립니다)');
  const base = manifest || fallbackManifest();
  const outline = parseOutline(rawOutline);
  if (manifest && !outline.size) warnOnce('avatar:outline', 'assets/avatar/outline.json이 없습니다 (외곽선 색은 RGB x0.45로 계산합니다)');

  const images = new Map();
  let imageTotal = 0;
  if (manifest) {
    // 매니페스트에 있는 파일만 요청한다
    const jobs = [];
    for (const part of PART_KEYS) {
      for (const { id } of base.parts[part]) {
        for (const layer of layersOfPart(part, id, base.layerOrder)) {
          imageTotal++;
          jobs.push(loadImage(new URL(`avatar/${layer}/${id}.png`, ASSET_ROOT)).then((img) => {
            if (img && img.naturalWidth >= base.frame.w && img.naturalHeight >= base.frame.h) images.set(`${layer}/${id}`, img);
            else warnOnce(`avatar:${layer}/${id}`, `파츠 시트를 불러오지 못했습니다: ${layer}/${id}.png (이 레이어는 빼고 그립니다)`);
          }));
        }
      }
    }
    await Promise.all(jobs);
  }

  const ids = Object.fromEntries(PART_KEYS.map((p) => [p, new Set(base.parts[p].map((o) => o.id))]));
  const defaultAvatar = Object.fromEntries(PART_KEYS.map((p) => [p, base.parts[p][0].id]));
  const sanitizeAvatar = (avatar) => normalizeAvatar(avatar, { ids, defaults: defaultAvatar, aliases: base.aliases });
  const presets = [];
  for (const pr of base.rawPresets) {
    if (!pr || typeof pr !== 'object' || !pr.avatar || typeof pr.avatar !== 'object') continue;
    const label = typeof pr.label === 'string' && pr.label.trim() ? pr.label.trim().slice(0, 20) : `조합 ${presets.length + 1}`;
    presets.push(Object.freeze({ label, avatar: Object.freeze(sanitizeAvatar(pr.avatar)) }));
  }
  const fi = (name, d) => { const i = base.frameNames.indexOf(name); return i >= 0 ? i : d; };

  return Object.freeze({
    source: manifest ? 'manifest' : 'fallback',
    parts: base.parts,
    layerOrder: base.layerOrder,
    frame: base.frame,
    anchor: base.anchor,
    frameNames: base.frameNames,
    frameCount: base.frameCount,
    frameIndex: Object.freeze({ front: fi('front', 0), side: fi('side_idle', 1), back: fi('back', base.frameCount - 1) }),
    animations: base.animations,
    outline,
    images,
    imageCount: images.size,
    imageTotal,
    defaultAvatar: Object.freeze(defaultAvatar),
    presets: Object.freeze(presets),
    /** 네트워크/DB에서 온 아바타를 manifest에 있는 id 7개로 맞춘다 (avatar-data.js 규칙). */
    sanitizeAvatar,
    labelOf(part, id) {
      const o = base.parts[part] && base.parts[part].find((x) => x.id === id);
      return o ? o.label : id;
    },
  });
}

// ---------------------------------------------------------------------------
// 맵

/**
 * @returns Promise<{ source: 'manifest'|'fallback', layers: [{ img, parallax, y, repeatX, w, h }], groundImg, groundY, layerCount }>
 * 실패한 레이어는 빠진다 (그 레이어만 빼고 그린다, screens/game.md 7.1).
 */
export async function loadMapAssets() {
  const raw = await fetchJson(new URL('map/manifest.json', ASSET_ROOT));
  const list = raw && Array.isArray(raw.layers) ? raw.layers : null;
  if (!list || !list.length) {
    warnOnce('map:manifest', 'assets/map/manifest.json이 없습니다 (단색 맵으로 그립니다)');
    return Object.freeze({ source: 'fallback', layers: [], groundImg: null, groundY: ART.groundY, layerCount: 0 });
  }
  const groundY = Number.isInteger(raw.groundY) ? raw.groundY : ART.groundY;
  if (groundY !== ART.groundY) warnOnce('map:groundY', `맵 groundY(${groundY})가 계약 값(${ART.groundY})과 다릅니다`);
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
  // 지면 레이어 = parallax 1.0 이면서 반복하지 않는 마지막 레이어 (계약: 마지막 지면 레이어, 너비 1200)
  const ground = [...layers].reverse().find((l) => l.parallax === 1 && !l.repeatX) || null;
  return Object.freeze({
    source: layers.length ? 'manifest' : 'fallback',
    layers,
    groundImg: ground ? ground.img : null,
    groundLayerY: ground ? ground.y : 0,
    groundY,
    layerCount: layers.length,
  });
}
