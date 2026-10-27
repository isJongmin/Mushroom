// 아트 에셋 로더 (ARCHITECTURE "복셀 아트 계약", 사이클 5).
// - assets/avatar/manifest.json: frame/anchor/density/frames/animations/layerOrder({layer,part,blend})/parts/presets.
//   레이어 시트(1152x192, 8프레임)는 부팅 때 받지 않고, 실제로 그릴 조합의 레이어만 필요할 때 받는다(getLayer).
//   레이어 파일 존재는 manifest `files`({layer: [id...]}, art handoff 10절)로만 판단한다(hasLayer, 404 0건).
//   files가 없거나 깨졌으면 필수 레이어(REQUIRED_LAYERS)만 요청한다(그림자/뒷 레이어 생략, 404 없음).
// - assets/map/manifest.json: density/groundY/width + layers(src .png/.webp, parallax, y 월드, repeatX, stretchX)
// PNG UI 스킨은 없다(CSS 블록 UI). 매니페스트나 개별 이미지가 없거나 깨지면 그 부분만 빼거나 단색으로 그린다.
// 경로는 모두 이 모듈 기준 상대 경로라 GitHub Pages 하위 경로에서도 동작한다.
import {
  AVATAR, PART_KEYS, PART_ID_RE, DEFAULT_LAYER_ORDER, LAYER_BLENDS, REQUIRED_LAYERS, DEFAULT_AVATAR, HAT_NONE, WORLD,
} from './constants.js';
import { normalizeAvatar } from './avatar-data.js';
import { normalizePlatforms } from './game/physics.js';

const REPO_ROOT = new URL('../../', import.meta.url);
const ASSET_ROOT = new URL('assets/', REPO_ROOT);
const IMAGE_TIMEOUT_MS = 15000;
// 매니페스트가 가리키는 파일은 assets/ 아래 PNG/WebP만 허용한다
const SRC_RE = /^assets\/[a-z0-9_\-/]+\.(png|webp)$/i;
const LAYER_RE = /^[a-z][a-z0-9_]{0,31}$/;

const warned = new Set();
export function warnOnce(key, ...args) {
  if (warned.has(key)) return;
  warned.add(key);
  console.warn('[버섯마을 에셋]', ...args);
}

/** 이미지를 받아 디코드까지 끝낸다. 실패(네트워크, 디코드, 시간 초과)는 null (예외 없음). */
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
      if (typeof img.decode === 'function') img.decode().then(() => finish(true), () => finish(false));
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

const posInt = (v, d, max = 1024) => (Number.isInteger(v) && v > 0 && v <= max ? v : d);
const num = (v, d) => (typeof v === 'number' && Number.isFinite(v) ? v : d);
const posNum = (v, d) => (typeof v === 'number' && Number.isFinite(v) && v > 0 && v <= 16 ? v : d);

// ---------------------------------------------------------------------------
// 아바타

const ANIM_NAMES = Object.keys(AVATAR.animations);
const OPTIONAL_ANIMS = Object.freeze(['jump', 'fall', 'prone', 'crouch']);

function normalizeAnimations(raw, frameCount) {
  const out = {};
  for (const name of ANIM_NAMES) {
    const a = raw && raw[name];
    const frames = a && Array.isArray(a.frames) ? a.frames.filter((f) => Number.isInteger(f) && f >= 0 && f < frameCount) : [];
    const d = AVATAR.animations[name];
    out[name] = frames.length
      ? { frames, ms: posInt(a.ms, d.ms, 10000) }
      : { frames: d.frames.filter((f) => f < frameCount), ms: d.ms };
    if (!out[name].frames.length) out[name].frames = [0];
  }
  // (사이클 6) 선택 애니메이션: manifest에 있고 프레임 번호가 시트 안일 때만 쓴다.
  // 없으면 넣지 않는다 → avatar.frameAt이 idle 프레임으로 대체 (아트 작업 전 에셋으로도 동작).
  for (const name of OPTIONAL_ANIMS) {
    const a = raw && raw[name];
    const frames = a && Array.isArray(a.frames) ? a.frames.filter((f) => Number.isInteger(f) && f >= 0 && f < frameCount) : [];
    if (frames.length) out[name] = { frames, ms: posInt(a.ms, 600, 10000) };
  }
  // (사이클 8) 엎드리기: prone이 없으면 옛 crouch를 같은 의미로 쓴다(아트 반영 전 호환). 둘 다 없으면 idle.
  if (!out.prone && out.crouch) out.prone = out.crouch;
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

/** layerOrder: [{ layer, part, blend }]. 항목 하나라도 형식이 틀리면 전체를 기본 순서로. */
function normalizeLayerOrder(raw) {
  if (!Array.isArray(raw) || !raw.length || raw.length > 32) return DEFAULT_LAYER_ORDER;
  const seen = new Set();
  const out = [];
  for (const e of raw) {
    if (!e || typeof e !== 'object' || typeof e.layer !== 'string' || !LAYER_RE.test(e.layer) || seen.has(e.layer)
      || !PART_KEYS.includes(e.part) || !LAYER_BLENDS.includes(e.blend)) return DEFAULT_LAYER_ORDER;
    seen.add(e.layer);
    out.push(Object.freeze({ layer: e.layer, part: e.part, blend: e.blend }));
  }
  return Object.freeze(out);
}

/**
 * manifest files ({ layer: [id...] }) = 레이어별 실제 파일 목록 (art handoff 10절, 정본).
 * layerOrder의 모든 레이어 키가 배열이고 모든 원소가 id 형식이어야 유효. 아니면 null(깨짐/없음).
 */
function normalizeFiles(raw, layerOrder) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
  const out = new Map();
  for (const { layer } of layerOrder) {
    const list = raw[layer];
    if (!Array.isArray(list) || list.length > 64 || !list.every((id) => typeof id === 'string' && PART_ID_RE.test(id))) return null;
    out.set(layer, new Set(list));
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
  const layerOrder = normalizeLayerOrder(raw.layerOrder);
  const frame = { w: posInt(raw.frame && raw.frame.w, AVATAR.frameW, 512), h: posInt(raw.frame && raw.frame.h, AVATAR.frameH, 512) };
  const anchor = {
    x: num(raw.anchor && raw.anchor.x, AVATAR.anchorX),
    y: num(raw.anchor && raw.anchor.y, AVATAR.anchorY),
  };
  return {
    parts, layerOrder, frame, anchor, frameNames, frameCount,
    density: posNum(raw.density, AVATAR.density),
    animations: normalizeAnimations(raw.animations, frameCount),
    aliases: normalizeAliases(raw.aliases),
    files: normalizeFiles(raw.files, layerOrder),
    rawPresets: Array.isArray(raw.presets) ? raw.presets.slice(0, 12) : [],
  };
}

function fallbackManifest() {
  const parts = Object.fromEntries(PART_KEYS.map((p) => [p, [{ id: DEFAULT_AVATAR[p], label: DEFAULT_AVATAR[p] }]]));
  return {
    parts,
    layerOrder: DEFAULT_LAYER_ORDER,
    frame: { w: AVATAR.frameW, h: AVATAR.frameH },
    anchor: { x: AVATAR.anchorX, y: AVATAR.anchorY },
    density: AVATAR.density,
    frameNames: [...AVATAR.frames],
    frameCount: AVATAR.frames.length,
    animations: normalizeAnimations(null, AVATAR.frames.length),
    aliases: normalizeAliases(null),
    files: null,
    rawPresets: [],
  };
}

/**
 * @returns Promise<{
 *   source: 'manifest'|'fallback', parts, layerOrder, frame, anchor, density, frameNames, frameCount, frameIndex,
 *   animations, hasLayer(layer, id), getLayer(layer, id) → Promise<img|null>, peekLayer(layer, id) → img|null|undefined,
 *   imageCount, imageTotal, defaultAvatar, presets: [{label, avatar}], sanitizeAvatar(avatar), labelOf(part, id)
 * }>
 * 부팅 때는 manifest만 받는다. 레이어 PNG는 getLayer로 필요할 때(그릴 조합이 생겼을 때) 받는다.
 */
export async function loadAvatarAssets() {
  const rawManifest = await fetchJson(new URL('avatar/manifest.json', ASSET_ROOT));
  const manifest = normalizeAvatarManifest(rawManifest);
  if (!manifest) warnOnce('avatar:manifest', 'assets/avatar/manifest.json이 없거나 계약 형식이 아닙니다 (단색 대체 아바타로 그립니다)');
  const base = manifest || fallbackManifest();
  const ids = Object.fromEntries(PART_KEYS.map((p) => [p, new Set(base.parts[p].map((o) => o.id))]));

  // 레이어 파일 존재 판단: manifest files만 믿는다. files가 없거나 깨졌으면 필수 레이어만 요청(그림자/뒷 레이어는 생략).
  if (manifest && !base.files) warnOnce('avatar:files', 'manifest files가 없거나 형식이 아닙니다 (필수 레이어만 그립니다: 그림자/뒷 레이어 생략)');
  const required = new Set(REQUIRED_LAYERS);
  const layerPart = new Map(base.layerOrder.map((e) => [e.layer, e.part]));
  function hasLayer(layer, id) {
    if (!manifest) return false;
    const part = layerPart.get(layer);
    if (!part || typeof id !== 'string' || !ids[part].has(id)) return false;
    if (part === 'hat' && id === HAT_NONE) return false;
    return base.files ? base.files.get(layer).has(id) : required.has(layer);
  }

  const imgs = new Map(); // 'layer/id' -> { promise, img }
  let loaded = 0;
  function getLayer(layer, id) {
    if (!hasLayer(layer, id)) return Promise.resolve(null);
    const key = `${layer}/${id}`;
    let e = imgs.get(key);
    if (!e) {
      e = { img: undefined, promise: null };
      e.promise = loadImage(new URL(`avatar/${layer}/${id}.png`, ASSET_ROOT)).then((img) => {
        const ok = img && img.naturalWidth >= base.frame.w && img.naturalHeight >= base.frame.h;
        // 경고는 files가 있을 때만 (대체 모드는 시작 때 경고 1회만 남긴다)
        if (!ok && base.files) warnOnce(`avatar:${key}`, `파츠 시트를 불러오지 못했습니다: ${key}.png (이 레이어는 빼고 그립니다)`);
        else loaded++;
        e.img = ok ? img : null;
        return e.img;
      });
      imgs.set(key, e);
    }
    return e.promise;
  }

  const defaultAvatar = Object.fromEntries(PART_KEYS.map((p) => [p, base.parts[p][0].id]));
  const sanitizeAvatar = (avatar) => normalizeAvatar(avatar, { ids, defaults: defaultAvatar, aliases: base.aliases });
  const presets = [];
  for (const pr of base.rawPresets) {
    if (!pr || typeof pr !== 'object' || !pr.avatar || typeof pr.avatar !== 'object') continue;
    const label = typeof pr.label === 'string' && pr.label.trim() ? pr.label.trim().slice(0, 20) : `조합 ${presets.length + 1}`;
    presets.push(Object.freeze({ label, avatar: Object.freeze(sanitizeAvatar(pr.avatar)) }));
  }
  const fi = (name, d) => { const i = base.frameNames.indexOf(name); return i >= 0 ? i : Math.min(d, base.frameCount - 1); };

  return Object.freeze({
    source: manifest ? 'manifest' : 'fallback',
    parts: base.parts,
    layerOrder: base.layerOrder,
    frame: base.frame,
    anchor: base.anchor,
    density: base.density,
    frameNames: base.frameNames,
    frameCount: base.frameCount,
    frameIndex: Object.freeze({ front: fi('front', 0), side: fi('side', 2), back: fi('back', base.frameCount - 1) }),
    animations: base.animations,
    hasLayer,
    getLayer,
    /** 이미 받은 레이어: img, 실패: null, 아직: undefined */
    peekLayer(layer, id) { const e = imgs.get(`${layer}/${id}`); return e ? e.img : undefined; },
    /** 지금까지 받은 레이어 수 / 요청한 레이어 수 */
    get imageCount() { return loaded; },
    get imageTotal() { return imgs.size; },
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
 * @returns Promise<{ source: 'manifest'|'fallback', layers: [{ img, parallax, y, w, h, repeatX, stretchX, name }],
 *   ground, groundY, width, density, layerCount, platforms }>
 * 레이어의 y, w, h는 월드 단위 (w, h = 이미지 px / density). 실패한 레이어는 빠진다 (그 레이어만 빼고 그린다).
 */
export async function loadMapAssets() {
  const raw = await fetchJson(new URL('map/manifest.json', ASSET_ROOT));
  const list = raw && Array.isArray(raw.layers) ? raw.layers : null;
  if (!list || !list.length) {
    warnOnce('map:manifest', 'assets/map/manifest.json이 없습니다 (단색 맵으로 그립니다)');
    return Object.freeze({
      source: 'fallback', layers: [], ground: null, groundY: WORLD.groundY, width: WORLD.width, density: 1.5, layerCount: 0,
      platforms: normalizePlatforms(raw && raw.platforms),
    });
  }
  const density = posNum(raw.density, 1.5);
  const groundY = num(raw.groundY, WORLD.groundY);
  if (groundY !== WORLD.groundY) warnOnce('map:groundY', `맵 groundY(${groundY})가 계약 값(${WORLD.groundY})과 다릅니다`);
  const width = num(raw.width, WORLD.width);
  const specs = list.slice(0, 16).map((l) => {
    const url = l && resolveSrc(l.src);
    if (!url) return null;
    return {
      url,
      name: l.src,
      parallax: Math.min(1, Math.max(0, num(l.parallax, 1))),
      y: num(l.y, 0),
      repeatX: l.repeatX === true,
      stretchX: l.stretchX === true,
    };
  });
  const loaded = await Promise.all(specs.map(async (s) => {
    if (!s) return null;
    const img = await loadImage(s.url);
    if (!img) { warnOnce(`map:${s.name}`, `맵 레이어를 불러오지 못했습니다: ${s.name}`); return null; }
    return Object.freeze({
      img, parallax: s.parallax, y: s.y, repeatX: s.repeatX, stretchX: s.stretchX, name: s.name,
      w: img.naturalWidth / density, h: img.naturalHeight / density,
    });
  }));
  const layers = loaded.filter(Boolean);
  // 지면 레이어 = parallax 1.0 이면서 반복/늘이기 하지 않는 마지막 레이어
  const ground = [...layers].reverse().find((l) => l.parallax === 1 && !l.repeatX && !l.stretchX) || null;
  return Object.freeze({
    source: layers.length ? 'manifest' : 'fallback',
    layers,
    ground,
    sky: layers.find((l) => l.stretchX) || null,
    groundY,
    width,
    density,
    layerCount: layers.length,
    // (사이클 8) 발판 [{ id, x1, x2, y }] (한 방향 통과). 없으면 [] → 지면만.
    platforms: normalizePlatforms(raw.platforms, { width }),
  });
}
