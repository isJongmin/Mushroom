// 아트 에셋 로더. assets/avatar/manifest.json을 런타임에 fetch 한다.
// 매니페스트나 개별 SVG가 없거나 깨지면 그 부분만 단색 도형 폴백(avatar.js)으로 그린다.
// 경로는 모두 이 모듈 기준 상대 경로라 GitHub Pages 하위 경로(/Mushroom/)에서도 동작한다.
import { DEFAULT_PARTS, DEFAULT_LAYER_ORDER, DEFAULT_AVATAR, PART_KEYS, PART_ID_RE, AVATAR } from './constants.js';

const ASSET_ROOT = new URL('../../assets/', import.meta.url);
const MANIFEST_URL = new URL('avatar/manifest.json', ASSET_ROOT);
const BACKGROUND_URL = new URL('map/background.svg', ASSET_ROOT);
const IMAGE_TIMEOUT_MS = 8000;

function loadImage(url) {
  return new Promise((resolve) => {
    const img = new Image();
    let done = false;
    const finish = (ok) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      img.onload = img.onerror = null;
      resolve(ok ? img : null);
    };
    const timer = setTimeout(() => finish(false), IMAGE_TIMEOUT_MS);
    img.onload = () => {
      if (typeof img.decode === 'function') img.decode().then(() => finish(true), () => finish(img.naturalWidth > 0));
      else finish(true);
    };
    img.onerror = () => finish(false);
    img.decoding = 'async';
    img.src = url.href;
  });
}

function normalizeManifest(raw) {
  if (!raw || typeof raw !== 'object') return null;
  const parts = {};
  let usedManifest = false;
  for (const part of PART_KEYS) {
    const list = raw.parts && Array.isArray(raw.parts[part]) ? raw.parts[part] : null;
    const clean = list
      ? list
          .filter((o) => o && typeof o.id === 'string' && PART_ID_RE.test(o.id))
          .map((o) => ({ id: o.id, label: typeof o.label === 'string' && o.label.trim() ? o.label.trim().slice(0, 40) : o.id }))
      : [];
    if (clean.length) {
      parts[part] = clean;
      usedManifest = true;
    } else {
      parts[part] = DEFAULT_PARTS[part].map((o) => ({ ...o }));
    }
  }
  if (!usedManifest) return null;
  const lo = Array.isArray(raw.layerOrder) ? raw.layerOrder.filter((p) => PART_KEYS.includes(p)) : [];
  const layerOrder = lo.length === PART_KEYS.length && new Set(lo).size === PART_KEYS.length ? lo : [...DEFAULT_LAYER_ORDER];
  const num = (v, d) => (typeof v === 'number' && Number.isFinite(v) && v > 0 ? v : d);
  const canvas = { w: num(raw.canvas && raw.canvas.w, AVATAR.w), h: num(raw.canvas && raw.canvas.h, AVATAR.h) };
  const anchor = { x: num(raw.anchor && raw.anchor.x, AVATAR.anchorX), y: num(raw.anchor && raw.anchor.y, AVATAR.anchorY) };
  return { parts, layerOrder, canvas, anchor };
}

async function fetchManifest() {
  try {
    const res = await fetch(MANIFEST_URL.href, { cache: 'no-cache' });
    if (!res.ok) return null;
    return normalizeManifest(await res.json());
  } catch {
    return null;
  }
}

/**
 * @returns Promise<{
 *   source: 'manifest'|'fallback', parts, layerOrder, canvas, anchor,
 *   images: Map<'part/id', HTMLImageElement>, background: HTMLImageElement|null,
 *   sanitizeAvatar(avatar), labelOf(part, id), defaultAvatar
 * }>
 */
export async function loadAssets() {
  const [manifest, background] = await Promise.all([fetchManifest(), loadImage(BACKGROUND_URL)]);
  const base = manifest || {
    parts: Object.fromEntries(PART_KEYS.map((p) => [p, DEFAULT_PARTS[p].map((o) => ({ ...o }))])),
    layerOrder: [...DEFAULT_LAYER_ORDER],
    canvas: { w: AVATAR.w, h: AVATAR.h },
    anchor: { x: AVATAR.anchorX, y: AVATAR.anchorY },
  };

  const images = new Map();
  if (manifest) {
    // 매니페스트에 있는 파일만 요청한다(매니페스트가 없으면 SVG 요청 자체를 하지 않는다)
    const jobs = [];
    for (const part of PART_KEYS) {
      for (const { id } of base.parts[part]) {
        const url = new URL(`avatar/${part}/${id}.svg`, ASSET_ROOT);
        jobs.push(loadImage(url).then((img) => { if (img) images.set(`${part}/${id}`, img); }));
      }
    }
    await Promise.all(jobs);
  }

  const idSets = Object.fromEntries(PART_KEYS.map((p) => [p, new Set(base.parts[p].map((o) => o.id))]));
  const defaultAvatar = {};
  for (const p of PART_KEYS) defaultAvatar[p] = idSets[p].has(DEFAULT_AVATAR[p]) ? DEFAULT_AVATAR[p] : base.parts[p][0].id;

  return Object.freeze({
    source: manifest ? 'manifest' : 'fallback',
    parts: base.parts,
    layerOrder: base.layerOrder,
    canvas: base.canvas,
    anchor: base.anchor,
    images,
    imageCount: images.size,
    background,
    defaultAvatar,
    /** 네트워크/DB에서 온 아바타를 목록에 있는 id로만 구성한다(없는 id는 기본값). */
    sanitizeAvatar(avatar) {
      const out = {};
      for (const p of PART_KEYS) {
        const v = avatar && typeof avatar === 'object' ? avatar[p] : undefined;
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
