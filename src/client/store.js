// 브라우저 저장소: 프로필(localStorage)과 방 재입장 정보(sessionStorage).
// ARCHITECTURE 결정 3: `mushroom:profile` = { nickname, avatar(7키) } — 서버에 저장하지 않는다.
// ARCHITECTURE 결정 6: sessionStorage `mushroom:room` = { roomId, nickname, owner(사이클 8) } — 새로고침 재입장용, 나가기·방 삭제에서 지운다.
import { LS_PROFILE, SS_ROOM, NICK_RE } from './constants.js';
import { normalizeAvatar, pickAvatar } from './avatar-data.js';
import { normalizeJob } from './game/jobs.js';

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
    return { nickname, avatar: normalizeAvatar(o.avatar), job: normalizeJob(o.job) };
  } catch {
    return null;
  }
}

/** @returns true면 저장 성공, false면 STORAGE 실패 (메모리로 진행) */
export function writeProfile(key, profile) {
  try {
    localStorage.setItem(key, JSON.stringify({ nickname: profile.nickname, avatar: pickAvatar(profile.avatar), job: normalizeJob(profile.job) }));
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
