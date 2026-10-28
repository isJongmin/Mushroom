// 브라우저 저장소: 프로필(localStorage)과 방 재입장 정보(sessionStorage).
// ARCHITECTURE 결정 3: `mushroom:profile` = { nickname, avatar(7키) } — 서버에 저장하지 않는다.
// ARCHITECTURE 결정 6: sessionStorage `mushroom:room` = { roomId, nickname, owner(사이클 8) } — 새로고침 재입장용, 나가기·방 삭제에서 지운다.
import { LS_PROFILE, LS_INVENTORY, SS_ROOM, NICK_RE } from './constants.js';
import { normalizeAvatar, pickAvatar } from './avatar-data.js';

/** local 모드 테스트 훅(?as=)이면 프로필 키를 사용자별로 나눈다 (backend/identity.js). */
export function profileKey(as) {
  return as ? `${LS_PROFILE}:as:${as}` : LS_PROFILE;
}

/** 없거나 읽을 수 없으면(JSON 오류, 닉네임 형식 불일치) null → 프로필 최초 화면 (profile.md 1장) */
export function readProfile(key) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const o = JSON.parse(raw);
    if (!o || typeof o !== 'object' || typeof o.nickname !== 'string') return null;
    const nickname = o.nickname.trim();
    if (!NICK_RE.test(nickname)) return null;
    return { nickname, avatar: normalizeAvatar(o.avatar) };
  } catch {
    return null;
  }
}

/** @returns true면 저장 성공, false면 STORAGE 실패 (메모리로 진행) */
export function writeProfile(key, profile) {
  try {
    localStorage.setItem(key, JSON.stringify({ nickname: profile.nickname, avatar: pickAvatar(profile.avatar) }));
    return true;
  } catch {
    return false;
  }
}

export function readRoomSession() {
  try {
    const raw = sessionStorage.getItem(SS_ROOM);
    if (!raw) return null;
    const o = JSON.parse(raw);
    if (!o || typeof o.roomId !== 'string' || !o.roomId || o.roomId.length > 64) return null;
    if (typeof o.nickname !== 'string' || !NICK_RE.test(o.nickname)) return null;
    return { roomId: o.roomId, nickname: o.nickname, owner: o.owner === true };
  } catch {
    return null;
  }
}

/** (사이클 8) owner = 내가 만든 방(createRoom 결과 또는 list_rooms mine). 새로고침 후 방 삭제 버튼 표시용 */
export function writeRoomSession(roomId, nickname, owner = false) {
  try { sessionStorage.setItem(SS_ROOM, JSON.stringify({ roomId, nickname, owner: !!owner })); } catch { /* 재입장만 못 함 */ }
}

export function clearRoomSession() {
  try { sessionStorage.removeItem(SS_ROOM); } catch { /* 무시 */ }
}

// (사이클 9) 인벤토리: localStorage `mushroom:inventory` = { items: ["hat:snail-shell", ..] } (프로필과 같은 방식, 서버 저장 없음).
// local 모드 테스트 훅(?as=)이면 프로필처럼 사용자별 키로 나눈다.
const INV_ITEM_RE = /^(skin|hair|face|top|bottom|shoes|hat):[a-z0-9-]{1,32}$/;
const INV_MAX = 200;

export function inventoryKey(as) {
  return as ? `${LS_INVENTORY}:as:${as}` : LS_INVENTORY;
}

/** 없거나 깨졌으면 [] (형식이 틀린 항목은 버리고 중복 제거) */
export function readInventory(key) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return [];
    const o = JSON.parse(raw);
    const list = o && Array.isArray(o.items) ? o.items : [];
    return [...new Set(list.filter((v) => typeof v === 'string' && INV_ITEM_RE.test(v)))].slice(0, INV_MAX);
  } catch {
    return [];
  }
}

/** @returns true면 저장 성공 */
export function writeInventory(key, items) {
  try {
    localStorage.setItem(key, JSON.stringify({ items: [...new Set(items)].slice(0, INV_MAX) }));
    return true;
  } catch {
    return false;
  }
}
