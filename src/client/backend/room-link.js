// 방 실시간 연결 상태기계 (ARCHITECTURE 결정 5, 사이클 6). DOM·supabase-js와 분리한 순수 모듈이다.
// 브라우저 전역에 기대지 않으므로 Node에서 그대로 import해 단위 시험할 수 있다.
//
// 지키는 규칙
//   1) 구독(open)은 반드시 join_room 'OK' 뒤에만. 첫 입장은 화면(로비/새로고침)이 이미 join을 마쳤으므로 생략할 수 있고,
//      그 밖의 모든 시도(끊김 복구, NOT_MEMBER 재입장, 다시 시도)는 join → open 순서다.
//   2) 새 시도 전에 이전 채널을 close(= removeChannel)로 완전히 정리한다. 시도는 한 줄(chain)로만 실행되어
//      동시에 열린 채널은 최대 1개다.
//   3) 세대 번호(gen): 상태가 바뀔 때마다(끊김, 재입장, 닫기) 올린다. 늦게 끝난 join/open 콜백은 gen이 다르면 버리고,
//      그때 생긴 채널은 바로 닫는다(고아 채널 없음). 진행 중인 시도에는 AbortSignal로 알린다.
//   4) 채널 오류(CHANNEL_ERROR/TIMED_OUT/CLOSED → onDrop) 또는 시도 실패 시 지수 백오프 1, 2, 4, 8, 16, 30, 30...초.
//   5) join_room이 되돌릴 수 없는 오류(방 없음, 정원, 닉네임, 비밀번호 필요 등)를 주면 'lost'로 끝난다.
//   6) 하트비트(20초)가 NOT_MEMBER면 재입장 1회(조용히). 직전 재입장 시작 후 10초 안의 새 신호는 남은 시간만큼 기다린다.
//   7) check(): 탭이 다시 보일 때. 즉시 하트비트 + 채널 상태 점검, 백오프 대기 중이면 바로 시도.
//
// 상태: idle → connecting → connected ⇄ (rejoining | reconnecting) → lost | failed | closed
//   connecting   첫 연결 시도 중(실패하면 백오프로 다시). initialAttempts번 실패하면 failed.
//   rejoining    NOT_MEMBER 후 조용한 재입장(화면 배너 없음). 일시 오류로 실패하면 reconnecting으로.
//   reconnecting 끊김 후 백오프 재시도 중(화면은 "다시 연결하는 중" 배너).
//   lost         되돌릴 수 없음(로비로).   failed  첫 연결 실패(다시 시도 버튼 → retry()).   closed  나감.

export const BACKOFF_MS = Object.freeze([1000, 2000, 4000, 8000, 16000, 30000]);
export const HEARTBEAT_MS = 20000;
export const REJOIN_GAP_MS = 10000;
export const TRACK_GAP_MS = 2000;

/** join_room이 이 코드로 실패하면 다시 시도해도 소용없다 → lost */
export const TERMINAL_JOIN_CODES = Object.freeze(new Set([
  'ROOM_NOT_FOUND', 'ROOM_FULL', 'NICK_TAKEN', 'NICK_FORMAT', 'WRONG_PASSWORD', 'RATE_LIMITED',
]));

/** idx번째(0부터) 재시도 전 대기(ms): 1, 2, 4, 8, 16, 30, 30, ... 초 */
export function backoffDelay(idx, table = BACKOFF_MS) {
  const i = Math.min(Math.max(0, idx | 0), table.length - 1);
  return table[i];
}

const defaultTimers = {
  set: (fn, ms) => setTimeout(fn, ms),
  clear: (id) => clearTimeout(id),
  now: () => Date.now(),
};

function makeAbort() {
  if (typeof AbortController !== 'undefined') return new AbortController();
  const signal = { aborted: false, onabort: null };
  return { signal, abort() { if (!signal.aborted) { signal.aborted = true; signal.onabort?.(); } } };
}

/**
 * @param o.join   async (signal) => void          join_room (같은 닉네임, 비밀번호 없음). 실패는 err.code를 가진 오류.
 * @param o.open   async (sink, signal) => conn    채널 구독. 구독 완료(SUBSCRIBED + 첫 track) 후 resolve.
 *                 sink.onDrop(reason)를 구독 후 끊김 때 부른다. conn = { close(): Promise, healthy?(): boolean, ... }
 * @param o.heartbeat async () => void              실패 시 err.code === 'NOT_MEMBER'면 재입장
 * @param o.onState (state, info) => void           info: { prev, attempt, delay, code, reason }
 * @param o.onOpen  (conn, { first, gen, after }) => void   새 채널이 열렸을 때(상태 connected 알림 전에)
 * @param o.timers { set, clear, now }               시험용 가짜 시계 주입
 */
export function createRoomLink(o) {
  const join = o.join;
  const open = o.open;
  const heartbeat = o.heartbeat || (() => Promise.resolve());
  const onState = o.onState || (() => {});
  const onOpen = o.onOpen || (() => {});
  const timers = o.timers || defaultTimers;
  const table = o.backoff || BACKOFF_MS;
  const heartbeatMs = o.heartbeatMs ?? HEARTBEAT_MS;
  const rejoinGapMs = o.rejoinGapMs ?? REJOIN_GAP_MS;
  const initialAttempts = o.initialAttempts ?? 3;

  let state = 'idle';
  let gen = 0;
  let conn = null;
  let everConnected = false;
  let skipJoin = false; // 첫 시도만: 화면이 이미 join_room 'OK'를 받았다
  let idx = 0; // 다음 백오프 표 위치
  let fails = 0; // 연속 실패 수 (성공하면 0)
  let waitTimer = null;
  let hbTimer = null;
  let lastRejoinAt = -Infinity;
  let ctl = null; // 진행 중 시도의 AbortController
  let chain = Promise.resolve();
  let busy = false; // 시도 실행 중
  const stats = {
    attempts: 0, joins: 0, opens: 0, closes: 0, drops: 0, stale: 0, heartbeats: 0, notMember: 0, lastDelay: 0,
  };
  /** 시험·디버그용 사건 기록 (최근 200개): [종류, gen] */
  const events = [];
  const ev = (kind, g, extra) => {
    events.push(extra === undefined ? [kind, g] : [kind, g, extra]);
    if (events.length > 200) events.shift();
  };

  function setState(next, info = {}) {
    const prev = state;
    state = next;
    ev(`state:${next}`, gen);
    try { onState(next, { prev, ...info }); } catch (e) { /* 화면 오류가 상태기계를 깨지 않게 */ }
  }

  function stopHeartbeat() {
    if (hbTimer !== null) { timers.clear(hbTimer); hbTimer = null; }
  }
  function clearWait() {
    if (waitTimer !== null) { timers.clear(waitTimer); waitTimer = null; }
  }

  /** 현재 채널을 닫는다(removeChannel). 여러 번 불러도 한 번만 닫는다. */
  async function closeConn() {
    stopHeartbeat();
    const c = conn;
    conn = null;
    if (!c) return;
    stats.closes++;
    ev('close', gen);
    try { await c.close(); } catch { /* 닫기 실패는 무시 */ }
  }

  /** 새 세대를 시작하고 delay 뒤 시도를 줄에 넣는다. 진행 중 시도는 abort. */
  function schedule(delay) {
    const g = ++gen;
    if (ctl) { try { ctl.abort(); } catch { /* 무시 */ } ctl = null; }
    clearWait();
    stats.lastDelay = delay;
    if (delay > 0) {
      waitTimer = timers.set(() => { waitTimer = null; enqueue(g); }, delay);
    } else {
      enqueue(g);
    }
    return g;
  }

  function enqueue(g) {
    chain = chain.then(() => attempt(g)).catch(() => {});
  }

  async function attempt(g) {
    if (g !== gen) return;
    busy = true;
    const c = makeAbort();
    ctl = c;
    stats.attempts++;
    try {
      // (2) 이전 채널을 먼저 완전히 정리한다
      await closeConn();
      if (g !== gen) return;
      // (1) join_room 'OK' 뒤에만 구독
      if (!skipJoin) {
        stats.joins++;
        ev('join', g);
        try {
          await join(c.signal);
        } catch (e) {
          if (g !== gen) return;
          ev('join-fail', g, e && e.code);
          failed(e, 'join');
          return;
        }
        if (g !== gen) { stats.stale++; ev('stale-join', g); return; }
        ev('join-ok', g);
      }
      skipJoin = false;
      stats.opens++;
      ev('open', g);
      let cn;
      try {
        cn = await open({ onDrop: (reason) => dropped(g, reason) }, c.signal);
      } catch (e) {
        if (g !== gen) return;
        ev('open-fail', g, e && e.code);
        failed(e, 'open');
        return;
      }
      // (3) 늦게 도착한 구독 결과: 다른 세대가 시작됐으면 이 채널은 바로 닫는다
      if (g !== gen) {
        stats.stale++;
        ev('stale-open', g);
        try { await cn.close(); } catch { /* 무시 */ }
        return;
      }
      conn = cn;
      const first = !everConnected;
      const after = state;
      everConnected = true;
      idx = 0;
      fails = 0;
      ev('open-ok', g);
      try { onOpen(cn, { first, gen: g, after }); } catch { /* 무시 */ }
      if (g !== gen) return; // onOpen 안에서 닫힘
      setState('connected', { first, after });
      startHeartbeat(g);
    } finally {
      if (ctl === c) ctl = null;
      busy = false;
    }
  }

  function failed(err, phase) {
    const code = err && err.code;
    if (phase === 'join' && TERMINAL_JOIN_CODES.has(code)) {
      lose(code);
      return;
    }
    fails++;
    if (!everConnected && fails >= initialAttempts) {
      gen++;
      setState('failed', { code, attempt: fails });
      return;
    }
    const delay = backoffDelay(idx++, table);
    setState(everConnected ? 'reconnecting' : 'connecting', { code, attempt: fails, delay, phase });
    schedule(delay);
  }

  function lose(code) {
    gen++;
    clearWait();
    stopHeartbeat();
    const c = conn;
    conn = null;
    if (c) { stats.closes++; Promise.resolve().then(() => c.close()).catch(() => {}); }
    setState('lost', { code });
  }

  /** 채널이 구독 후 끊겼다 (어댑터 sink.onDrop). */
  function dropped(g, reason) {
    if (g !== gen || state !== 'connected') return; // 이미 처리 중이거나 지난 세대
    stats.drops++;
    ev('drop', g, reason);
    stopHeartbeat();
    const delay = backoffDelay(idx++, table);
    setState('reconnecting', { reason, attempt: 0, delay });
    schedule(delay);
  }

  /** NOT_MEMBER: 같은 끊김 안의 추가 신호는 무시, 재입장 시도 간격 최소 rejoinGapMs */
  function notMember(source) {
    if (state === 'lost' || state === 'closed' || state === 'failed' || state === 'idle') return;
    if (state === 'rejoining' || state === 'reconnecting' || state === 'connecting' || busy) return;
    stats.notMember++;
    ev('not-member', gen, source);
    stopHeartbeat();
    const now = timers.now();
    const delay = Math.max(0, lastRejoinAt + rejoinGapMs - now);
    lastRejoinAt = now + delay;
    setState('rejoining', { reason: source || 'not_member', delay });
    schedule(delay);
  }

  /** 백오프 대기를 건너뛰고 바로 시도 (배너 버튼, 탭 복귀) */
  function reconnectNow() {
    if (waitTimer === null) return false;
    clearWait();
    stats.lastDelay = 0;
    enqueue(gen);
    return true;
  }

  function startHeartbeat(g) {
    stopHeartbeat();
    hbTimer = timers.set(() => { hbTimer = null; beat(g); }, heartbeatMs);
  }

  function beat(g) {
    if (g !== gen || state !== 'connected') return;
    stats.heartbeats++;
    ev('heartbeat', g);
    startHeartbeat(g);
    Promise.resolve().then(() => heartbeat()).then(() => {}, (e) => {
      if (g === gen && e && e.code === 'NOT_MEMBER') notMember('heartbeat');
    });
  }

  return {
    get state() { return state; },
    get gen() { return gen; },
    get conn() { return conn; },
    stats,
    events,

    /** 첫 연결. joined = 화면이 이미 join_room 'OK'를 받았음(로비/새로고침 재입장). */
    start({ joined = true } = {}) {
      if (state !== 'idle') return;
      skipJoin = !!joined;
      idx = 0;
      fails = 0;
      setState('connecting', { attempt: 0, delay: 0 });
      schedule(0);
    },

    /** failed 상태(첫 연결 실패)에서 다시 시도: join부터 */
    retry() {
      if (state !== 'failed') return;
      skipJoin = false;
      idx = 0;
      fails = 0;
      setState('connecting', { attempt: 0, delay: 0 });
      schedule(0);
    },

    reconnectNow,

    notMember,

    /** 탭이 다시 보일 때: 즉시 하트비트 + 채널 상태 점검 */
    check() {
      ev('check', gen, state);
      if (state === 'connected') {
        const g = gen;
        if (conn && typeof conn.healthy === 'function' && !conn.healthy()) {
          dropped(g, 'stale');
          return;
        }
        beat(g);
        return;
      }
      // 백오프 대기 중이면 바로 시도. rejoining의 10초 간격(무한 루프 방지)은 건너뛰지 않는다.
      if (state === 'reconnecting' || state === 'connecting') reconnectNow();
    },

    /** 나가기/화면 정리: 대기·하트비트 중지, 진행 중 시도 abort, 채널 removeChannel까지 기다린다. */
    async close() {
      if (state === 'closed') { await chain; return; }
      gen++;
      if (ctl) { try { ctl.abort(); } catch { /* 무시 */ } }
      clearWait();
      stopHeartbeat();
      setState('closed');
      await closeConn();
      await chain; // 진행 중 시도가 끝나(또는 버려져) 고아 채널이 남지 않을 때까지
    },
  };
}

/**
 * Presence track 간격 제한 (사이클 6: 최소 2초). 대기 중 요청은 마지막 것 하나로 합친다.
 * run(fn) → fn() 결과 Promise. 같은 대기 구간에 들어온 요청들은 마지막 fn의 결과를 함께 받는다.
 */
export function createTrackLimiter({ minGapMs = TRACK_GAP_MS, timers = defaultTimers } = {}) {
  let last = -Infinity;
  let pending = null; // { timer, fn, waiters: [{resolve, reject}] }
  let count = 0;

  function exec(fn) {
    last = timers.now();
    count++;
    return Promise.resolve().then(fn);
  }

  return {
    run(fn) {
      if (pending) {
        pending.fn = fn;
        return new Promise((resolve, reject) => pending.waiters.push({ resolve, reject }));
      }
      const wait = last + minGapMs - timers.now();
      if (wait <= 0) return exec(fn);
      return new Promise((resolve, reject) => {
        pending = { fn, waiters: [{ resolve, reject }], timer: null };
        pending.timer = timers.set(() => {
          const p = pending;
          pending = null;
          exec(p.fn).then((v) => p.waiters.forEach((w) => w.resolve(v)), (e) => p.waiters.forEach((w) => w.reject(e)));
        }, wait);
      });
    },
    /** 대기 중 요청을 버린다 ('cancelled'로 resolve) */
    cancel() {
      if (!pending) return;
      timers.clear(pending.timer);
      const p = pending;
      pending = null;
      p.waiters.forEach((w) => w.resolve('cancelled'));
    },
    get count() { return count; },
    get pending() { return !!pending; },
  };
}
