#!/usr/bin/env python3
"""버섯마을 local 모드 E2E 테스트 (Python Playwright, Chromium headless). 사이클 4 계약 기준.

- 로그인 없음. 프로필(localStorage) -> 로비 -> 방 흐름. 사용자는 `?as=<이름>`으로 탭마다 나눈다
  (docs/handoff/frontend-20261015-rooms.md 4장). 같은 browser context의 페이지들은 같은 localStorage(= 같은 "서버")와
  BroadcastChannel을 공유한다.

실행:  QA_SCRATCH=<스크래치> python3 -B tests/e2e_local.py [-v] [--only 1,8] [--shots DIR]
  -v          : 실패 항목의 traceback 출력
  --only      : 번호만 실행 (쉼표 구분)
  --shots DIR : 로비/방 스크린샷(데스크톱 1280x800, 모바일 360x640)만 저장하고 종료
환경 변수:
  QA_SCRATCH  : 스크래치 디렉터리. 항목 24가 저장소 사본을 여기에 만든다 (없으면 시스템 임시 폴더).

- 저장소 루트에서 `python3 -m http.server`를 빈 포트로 띄우고 끝나면 반드시 종료한다.
- 외부 네트워크(Supabase, CDN)에 접속하지 않는다. local 모드만 검증한다.
- 결과는 항목별 PASS / FAIL / UNVERIFIED. 확인하지 못한 검사는 UNVERIFIED (사유 기록). 실행하지 않은 것을 PASS로 내지 않는다.
- 테스트 훅: window.__mushroom.getState(), data-testid (frontend-20261015-rooms.md 4장).
- 시간 조작(방 만료, 실패 창, 20명 정원)은 localStorage DB(`mushroom.local.v4.db`)를 직접 고쳐 만든다. 각 항목에 방법을 적었다.
"""
import argparse
import hashlib
import json
import math
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SCRATCH = Path(os.environ.get("QA_SCRATCH") or tempfile.gettempdir())
DB_KEY = "mushroom.local.v4.db"
LOCK_NAME = "mushroom.local.v4.db"
SS_ROOM = "mushroom:room"
LS_LOG_OPEN = "mushroom:logOpen"
PROFILE_KEY = "mushroom:profile:as:{}"  # ?as=<이름> 사용자의 프로필 키
PART_KEYS7 = ["skin", "hair", "face", "top", "bottom", "shoes", "hat"]
CATEGORY_TABS = ["skin", "face", "hair", "hat", "top", "bottom", "shoes"]
MANIFEST = json.loads((ROOT / "assets/avatar/manifest.json").read_text(encoding="utf-8"))
PARTS = {p: [x["id"] for x in MANIFEST["parts"][p]] for p in CATEGORY_TABS}
DEFAULTS = {p: PARTS[p][0] for p in PART_KEYS7}
# 골라서 저장하는 값 (7파츠 모두 기본값과 다르게)
PICK = {"skin": "medium", "face": "smile", "hair": "pink-long", "hat": "mushroom-red",
        "top": "tee-stripe-red", "bottom": "skirt-pink", "shoes": "boots-brown"}
# 사이클 1 형식 저장값(5키, eyes, 옛 id)과 정규화 기대값 (frontend 3장, art 5장)
LEGACY_ROW = {"skin": "skin-light", "hair": "hair-round-black", "eyes": "eyes-dot",
              "top": "top-tee-red", "bottom": "bottom-shorts-navy"}
LEGACY_EXPECT = {"skin": "light", "hair": "black-short", "face": "basic", "top": "tee-stripe-red",
                 "bottom": "pants-navy", "shoes": "sneakers-white", "hat": "none"}
WALK_FRAMES = {2, 3, 4, 5}
PALETTE_COLORS = 42

# 화면 문구 (errors.js / profile.js / lobby.js / room.js 원문)
MSG = {
    "NICK_FORMAT": "2~12자의 한글, 영문, 숫자만 쓸 수 있어요.",
    "ROOM_NAME_FORMAT": "방 이름은 1~24자로 정해 주세요. 줄바꿈 같은 특수 문자는 쓸 수 없어요.",
    "PASSWORD_FORMAT": "비밀번호는 4~32자로 정해 주세요.",
    "TOO_MANY_ROOMS": "방은 동시에 3개까지 만들 수 있어요. 내가 만든 방이 비고 30분이 지나면 사라져요.",
    "WRONG_PASSWORD": "비밀번호가 맞지 않아요. 다시 입력해 주세요.",
    "RATE_LIMITED": "잠시 후 다시 시도해 주세요.",
    "ROOM_FULL": "방이 가득 찼어요. 다른 방을 골라 주세요.",
    "NICK_TAKEN_TITLE": "닉네임이 겹쳐요",
    "NICK_TAKEN_AGAIN": "이 닉네임도 이 방에 있어요. 다른 닉네임을 써 주세요.",
    "SEND_RATE_LIMITED": "잠시 후 다시 보내 주세요.",
    "TEXT_FORMAT": "메시지는 1~80자로 보내 주세요.",
    "NOT_MEMBER": "방과 연결이 끊어졌어요. 로비에서 다시 들어와 주세요.",
    "COOLDOWN": "1초 뒤에 다시 보낼 수 있습니다.",
    "REJOIN_FAILED": "방에 다시 들어가지 못했어요. 목록에서 다시 골라 주세요.",
}
XSS_TAG = "<img src=x onerror=window.__xss=1>"
XSS_NAME = "<img src=x onerror=1>"  # 방 이름 24자 이내, 제어문자 없음
XSS_NICK = XSS_TAG  # 닉네임은 형식 위반으로 거부되어야 한다

BASE = ""  # main()에서 설정
VERBOSE = False
RESULTS = []  # (번호, 제목, 결과, 상세, 검사 목록)
CASES = []  # (번호, 제목, 함수)
TOTAL_TIME = {}


# ---------------------------------------------------------------------------
# 공통 유틸
# ---------------------------------------------------------------------------
def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_server(port):
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1", "--directory", str(ROOT)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return proc
        except OSError:
            time.sleep(0.1)
    proc.terminate()
    raise RuntimeError("http.server 기동 실패")


def new_nick(prefix="Qa"):
    return prefix + secrets.token_hex(3)  # 영문/숫자, 2~12자


def wait_until(fn, timeout=8.0, interval=0.1):
    end = time.time() + timeout
    while True:
        try:
            v = fn()
        except Exception:
            v = None
        if v:
            return v
        if time.time() > end:
            return None
        time.sleep(interval)


class Collector:
    """전체 테스트 동안 모든 페이지의 콘솔 에러와 페이지 에러를 모은다."""

    def __init__(self):
        self.console_errors = []
        self.failed_requests = []

    def attach(self, page, label):
        def on_console(msg):
            if msg.type == "error":
                self.console_errors.append(f"[{label}] {msg.text}")

        page.on("console", on_console)
        page.on("pageerror", lambda e: self.console_errors.append(f"[{label}] pageerror: {e}"))
        page.on("requestfailed", lambda r: self.failed_requests.append(f"[{label}] {r.url}"))


def new_ctx(browser, **kw):
    kw.setdefault("viewport", {"width": 1280, "height": 800})
    return browser.new_context(**kw)


TRACK_JS = """
(() => {
  window.__seen = [];
  const rec = () => {
    const b = document.body;
    const s = b && b.dataset ? b.dataset.screen : null;
    if (s && window.__seen[window.__seen.length - 1] !== s) window.__seen.push(s);
  };
  new MutationObserver(rec).observe(document, { subtree: true, attributes: true, attributeFilter: ['data-screen'] });
})();
"""


def track_screens(ctx):
    ctx.add_init_script(TRACK_JS)


LOCKCOUNT_JS = """
(() => {
  const L = navigator.locks;
  if (!L || !L.request) return;
  const orig = L.request.bind(L);
  window.__lockCount = {};
  L.request = function (name, ...rest) {
    window.__lockCount[name] = (window.__lockCount[name] || 0) + 1;
    return orig(name, ...rest);
  };
})();
"""

# 탭 숨김 흉내: 페이지가 window.__vis = 'hidden'을 보게 한다 (Playwright로 실제 탭을 숨길 수 없음)
VIS_JS = """
(() => {
  Object.defineProperty(document, 'visibilityState', { configurable: true, get() { return window.__vis || 'visible'; } });
  Object.defineProperty(document, 'hidden', { configurable: true, get() { return (window.__vis || 'visible') === 'hidden'; } });
})();
"""


def state(page):
    return page.evaluate("window.__mushroom.getState()")


def sc(page):
    try:
        return state(page)["screen"]
    except Exception:
        return None


def wait_screen(page, name, timeout=10.0):
    if wait_until(lambda: sc(page) == name, timeout) is None:
        raise AssertionError(f"'{name}' 화면으로 전환되지 않음 (현재 {sc(page)})")


def wait_conn(page, want="connected", timeout=12.0):
    if wait_until(lambda: state(page).get("connection") == want, timeout) is None:
        raise AssertionError(f"연결 상태 '{want}' 대기 시간 초과 (현재 {state(page).get('connection')})")


def lobby_ready(page, timeout=10.0):
    if wait_until(lambda: ((state(page).get("lobby") or {}).get("state") == "ready"), timeout) is None:
        raise AssertionError(f"로비 목록 준비 안 됨 (현재 {(state(page).get('lobby') or {}).get('state')})")


def open_as(ctx, col, label, name, *, first_screen=None):
    """?as=<name> 으로 새 탭을 연다. 부팅 후 profile/lobby/room 중 하나가 되면 돌아간다."""
    page = ctx.new_page()
    col.attach(page, label)
    page.goto(f"{BASE}?as={name}")
    if wait_until(lambda: sc(page) in ("profile", "lobby", "room"), 10) is None:
        raise AssertionError(f"[{label}] 부트 후 화면 전환 실패")
    if first_screen:
        wait_screen(page, first_screen)
    return page


def create_profile(page, nick, pick=None):
    """프로필 화면에서 닉네임(과 파츠)을 정하고 입장하기 -> 로비."""
    wait_screen(page, "profile")
    page.get_by_test_id("nickname-input").fill(nick)
    expect(page.get_by_test_id("nickname-status")).to_have_attribute("data-state", "ok", timeout=3000)
    for p, v in (pick or {}).items():
        pick_slot(page, p, v)
    page.get_by_test_id("create-submit").click()
    wait_screen(page, "lobby")
    lobby_ready(page)


def pick_slot(page, part, item_id):
    page.get_by_test_id(f"tab-{part}").click()
    page.get_by_test_id(f"slot-{part}-{item_id}").click()


def rooms_of(page):
    return state(page).get("rooms") or []


def rid_by_name(page, name):
    for r in rooms_of(page):
        if r["name"] == name:
            return r["id"]
    return None


def wait_row(page, name, timeout=8.0):
    rid = wait_until(lambda: rid_by_name(page, name), timeout)
    if rid is None:
        raise AssertionError(f"로비에 '{name}' 방이 없음 (목록 {[r['name'] for r in rooms_of(page)]})")
    return rid


def row_locator(page, rid):
    return page.locator(f'[data-testid="room-row"][data-room-id="{rid}"]')


def enter_from_lobby(page, name, pw=None):
    """로비에서 방 행의 입장 버튼. 잠금 방이면 비밀번호 모달에 pw를 넣는다."""
    rid = wait_row(page, name)
    row_locator(page, rid).get_by_test_id("room-enter").click()
    if pw is not None:
        expect(page.get_by_test_id("modal-password")).to_be_visible(timeout=3000)
        page.get_by_test_id("join-password").fill(pw)
        page.get_by_test_id("join-submit").click()
    wait_screen(page, "room")
    wait_conn(page)
    return rid


def ui_create_room(page, name, pw=None):
    lobby_ready(page)
    page.get_by_test_id("room-create").click()
    expect(page.get_by_test_id("modal-create")).to_be_visible(timeout=3000)
    page.get_by_test_id("create-name").fill(name)
    if pw:
        page.get_by_test_id("create-password").fill(pw)
    page.get_by_test_id("create-submit-room").click()
    wait_screen(page, "room")
    wait_conn(page)
    return state(page)["room"]["id"]


def leave_room(page):
    page.get_by_test_id("room-leave").click()
    wait_screen(page, "lobby")
    lobby_ready(page)


def send_chat(page, text, gap=True):
    """UI로 채팅을 보낸다. 클라이언트 1초 쿨다운을 피하려고 기본으로 1.1초 기다린다."""
    if gap:
        time.sleep(1.1)
    page.get_by_test_id("chat-input").click()
    page.keyboard.type(text)
    page.keyboard.press("Enter")


def players(page):
    return state(page).get("players") or []


def find_player(page, nick):
    for p in players(page):
        if p["nickname"] == nick:
            return p
    return None


LOG_JS = """() => Array.from(document.querySelectorAll('[data-testid="log-item"]')).map((e) => ({
  kind: e.getAttribute('data-kind'), id: e.getAttribute('data-id'), text: e.textContent || '' }))"""


def log_items(page):
    return page.evaluate(LOG_JS)


def count_chat(page, marker):
    """서버 chat 줄(data-id 있음) 중 marker를 포함한 줄 수 (로그 DOM 기준)."""
    return sum(1 for it in log_items(page) if it["id"] and marker in it["text"])


def count_sys(page, text):
    return sum(1 for it in log_items(page) if it["kind"] == "sys" and text in it["text"])


ADAPTER_JS = """async ([fn, args]) => {
  const m = await import('./src/client/backend/local.js');
  const b = m.createLocalBackend();
  await b.init();
  try {
    const v = await b[fn](...args);
    return { ok: true, value: v === undefined ? null : v };
  } catch (e) {
    return { ok: false, code: (e && e.code) || 'NONCODE', msg: String((e && e.message) || e) };
  }
}"""


def adapter(page, fn, *args):
    """같은 페이지의 local 어댑터를 직접 호출한다 (uid = 이 페이지 사용자). 오류는 {ok: false, code}로 돌아온다."""
    return page.evaluate(ADAPTER_JS, [fn, list(args)])


DB_MUT_JS = """async (body) => {
  return navigator.locks.request('mushroom.local.v4.db', async () => {
    const db = JSON.parse(localStorage.getItem('mushroom.local.v4.db') || 'null');
    const fn = new Function('db', 'now', body);
    const r = fn(db, Date.now());
    localStorage.setItem('mushroom.local.v4.db', JSON.stringify(db));
    return r === undefined ? null : r;
  });
}"""


def db_get(page):
    return page.evaluate("() => JSON.parse(localStorage.getItem('mushroom.local.v4.db') || 'null')")


def db_mut(page, body):
    """서버 DB(localStorage)를 같은 잠금으로 고친다. 시간 조작/멤버 강제 삭제/가짜 멤버 주입 전용."""
    return page.evaluate(DB_MUT_JS, body)


def inject_fakes(page, rid, n, tag):
    """활성 가짜 멤버 n명 주입 (DB 행만, Presence 없음). last_seen을 40초 뒤로 두어 테스트 동안 활성 유지."""
    body = (f"const ms = db.members[{json.dumps(rid)}] || (db.members[{json.dumps(rid)}] = {{}});"
            f"for (let i = 0; i < {n}; i++) ms['fake-{tag}-' + i] = {{ nickname: 'Fk{tag}' + String(i).padStart(2, '0'),"
            f" joined_at: now, last_seen_at: now + 40000 }};")
    db_mut(page, body)


def hold_key(page, key, ms):
    page.keyboard.down(key)
    time.sleep(ms / 1000)
    page.keyboard.up(key)


def verdict(checks):
    """checks: [(설명, True | False | None)]. None = 미검증. 값은 bool로 정리한다."""
    checks = [(n, None if ok is None else bool(ok)) for n, ok in checks]
    fails = [n for n, ok in checks if ok is False]
    unv = [n for n, ok in checks if ok is None]
    if fails:
        return ("FAIL", f"실패 {len(fails)}건: " + " | ".join(fails), checks)
    if unv:
        return ("UNVERIFIED", f"미검증 {len(unv)}건: " + " | ".join(unv), checks)
    return ("PASS", f"검사 {len(checks)}건 전부 통과", checks)


def case(num, title):
    def deco(fn):
        CASES.append((num, title, fn))
        return fn

    return deco


# ---------------------------------------------------------------------------
# 1~14: 사이클 4 신규 흐름 (요청 목록 그대로)
# ---------------------------------------------------------------------------
@case(1, "첫 방문 -> 프로필(닉네임 형식 검사, 저장) -> 로비. 재방문은 로비부터")
def t01(browser, col):
    ctx = new_ctx(browser)
    track_screens(ctx)
    checks = []
    try:
        page = open_as(ctx, col, "A", "a")
        checks.append(("첫 방문 화면 = profile", sc(page) == "profile"))
        checks.append(("모드 배지 LOCAL MODE", page.get_by_test_id("mode-badge").inner_text().strip() == "LOCAL MODE"))
        checks.append(("프로필 모드 first (입장하기)", state(page)["create"]["mode"] == "first"
                       and page.get_by_test_id("create-submit").inner_text().strip() == "입장하기"))
        st = page.get_by_test_id("nickname-status")
        checks.append(("빈 입력: 입장하기 비활성(aria-disabled)", page.get_by_test_id("create-submit").get_attribute("aria-disabled") == "true"))
        page.get_by_test_id("nickname-input").fill("가")
        checks.append(("1자 입력: 형식 검사 상태 format/help (입장 불가)",
                       page.get_by_test_id("create-submit").get_attribute("aria-disabled") == "true"))
        page.get_by_test_id("nickname-input").fill("버섯!")
        expect(st).to_have_attribute("data-state", "format", timeout=3000)
        checks.append(("특수문자 닉네임: 형식 오류 문구", st.inner_text().strip() == MSG["NICK_FORMAT"]))
        page.get_by_test_id("nickname-input").press("Enter")
        time.sleep(0.4)
        checks.append(("형식 오류 상태에서 Enter로 저장되지 않음 (profile 유지)", sc(page) == "profile"))
        page.get_by_test_id("nickname-input").fill("버섯이")
        expect(st).to_have_attribute("data-state", "ok", timeout=3000)
        checks.append(("정상 닉네임: 입장하기 활성", page.get_by_test_id("create-submit").get_attribute("aria-disabled") == "false"))
        page.get_by_test_id("create-submit").click()
        wait_screen(page, "lobby")
        lobby_ready(page)
        checks.append(("저장 후 로비 진입, 내 닉네임 표시", page.get_by_test_id("me-nickname").inner_text().strip() == "버섯이"))
        stored = json.loads(page.evaluate("(k) => localStorage.getItem(k)", PROFILE_KEY.format("a")) or "null") or {}
        checks.append(("localStorage mushroom:profile:as:a = {nickname, avatar} (avatar 7키)",
                       stored.get("nickname") == "버섯이" and sorted((stored.get("avatar") or {}).keys()) == sorted(PART_KEYS7)))
        checks.append(("서버 저장 없음: userId는 익명 uid (as-a)", state(page)["userId"] == "as-a"))
        page.reload()
        wait_screen(page, "lobby")
        lobby_ready(page)
        seen = page.evaluate("window.__seen")
        checks.append((f"재방문(새로고침): 로비부터, 프로필 화면 미경유 (기록 {seen})", "profile" not in seen and "lobby" in seen))
    finally:
        ctx.close()
    return verdict(checks)


@case(2, "프로필 수정: 꾸미기 -> 닉네임/파츠 변경 후 저장 반영, Esc(취소)는 미반영")
def t02(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        page = open_as(ctx, col, "A", "a")
        create_profile(page, "QaEditA")
        page.get_by_test_id("profile-edit").click()
        wait_screen(page, "profile")
        checks.append(("꾸미기 -> 수정 모드(프로필 수정, 저장 버튼)",
                       state(page)["create"]["mode"] == "edit" and page.get_by_test_id("profile-title").inner_text().strip() == "프로필 수정"
                       and page.get_by_test_id("create-submit").inner_text().strip() == "저장"))
        checks.append(("수정 모드 닉네임 칸 = 현재 닉네임", page.get_by_test_id("nickname-input").input_value() == "QaEditA"))
        page.get_by_test_id("nickname-input").fill("QaEditB")
        pick_slot(page, "hat", "mushroom-red")
        page.get_by_test_id("create-submit").click()
        wait_screen(page, "lobby")
        lobby_ready(page)
        checks.append(("저장 후 로비 닉네임 반영", page.get_by_test_id("me-nickname").inner_text().strip() == "QaEditB"))
        stored = json.loads(page.evaluate("(k) => localStorage.getItem(k)", PROFILE_KEY.format("a")))
        checks.append(("저장값 반영: nickname=QaEditB, hat=mushroom-red",
                       stored["nickname"] == "QaEditB" and stored["avatar"]["hat"] == "mushroom-red"))
        checks.append(("저장된 avatar 정확히 7키", sorted(stored["avatar"].keys()) == sorted(PART_KEYS7)))

        page.get_by_test_id("profile-edit").click()
        wait_screen(page, "profile")
        page.get_by_test_id("nickname-input").fill("QaEditC")
        pick_slot(page, "hat", "none")
        page.keyboard.press("Escape")
        wait_screen(page, "lobby")
        lobby_ready(page)
        stored2 = json.loads(page.evaluate("(k) => localStorage.getItem(k)", PROFILE_KEY.format("a")))
        checks.append(("Esc(취소): 로비 닉네임 유지 QaEditB", page.get_by_test_id("me-nickname").inner_text().strip() == "QaEditB"))
        checks.append(("Esc(취소): 저장값 변경 없음", stored2 == stored))
        focus = page.evaluate("document.activeElement && document.activeElement.getAttribute('data-testid')")
        checks.append((f"Esc 후 포커스 = 꾸미기 버튼 (실제 {focus})", focus == "profile-edit"))
    finally:
        ctx.close()
    return verdict(checks)


@case(3, "공개 방 생성 -> 다른 사용자 로비에 5초 안에 표시, 인원 정확, 입장 버튼으로 입장")
def t03(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        a = open_as(ctx, col, "A", "a")
        create_profile(a, "QaRoomA")
        b = open_as(ctx, col, "B", "b")
        create_profile(b, "QaRoomB")
        ui_create_room(a, "공개방3")
        t0 = time.time()
        rid = wait_until(lambda: rid_by_name(b, "공개방3"), 8)
        dt = time.time() - t0
        checks.append((f"B 로비에 방 표시 (경과 {dt:.1f}s, 기준 6s 이내: 5초 폴링)", rid is not None and dt <= 6.0))
        if rid:
            row = row_locator(b, rid)
            checks.append(("방 행: 인원 1/20명 (방장 1명)", row.get_by_test_id("room-members").inner_text().strip() == "1/20명"))
            checks.append(("방 행: 공개 방(잠금 아님)", row.get_attribute("data-locked") == "false"))
            checks.append(("방 행: 입장 버튼 활성", row.get_by_test_id("room-enter").is_enabled()))
        enter_from_lobby(b, "공개방3")
        checks.append(("입장 후 B 화면 room, 연결됨", sc(b) == "room"))
        hud_a = wait_until(lambda: a.get_by_test_id("player-count").inner_text().strip() == "2/20명", 4)
        hud_b = wait_until(lambda: b.get_by_test_id("player-count").inner_text().strip() == "2/20명", 4)
        checks.append(("A 방 인원 칩 2/20명 (Presence)", bool(hud_a)))
        checks.append(("B 방 인원 칩 2/20명 (Presence)", bool(hud_b)))
        cnt = adapter(b, "listRooms")
        mem = [r["members"] for r in (cnt.get("value") or []) if r["name"] == "공개방3"]
        checks.append((f"DB 활성 인원 2 (방장 + B, listRooms) (실제 {mem})", mem == [2]))
    finally:
        ctx.close()
    return verdict(checks)


@case(4, "방 이름/비밀번호 형식 오류 문구, 방 3개 초과 TOO_MANY_ROOMS")
def t04(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        a = open_as(ctx, col, "A", "a")
        create_profile(a, "QaFormA")
        a.get_by_test_id("room-create").click()
        modal = a.get_by_test_id("modal-create")
        expect(modal).to_be_visible(timeout=3000)
        checks.append(("빈 이름: 만들기 비활성", a.get_by_test_id("create-submit-room").is_disabled()))
        a.get_by_test_id("create-name").fill("정상이름")
        checks.append(("이름 정상 + 비밀번호 없음: 만들기 활성 (공개 방)", a.get_by_test_id("create-submit-room").is_enabled()))
        a.get_by_test_id("create-name").fill("")
        a.get_by_test_id("create-name").fill("   ")
        checks.append(("공백만: 만들기 비활성", a.get_by_test_id("create-submit-room").is_disabled()))
        a.get_by_test_id("create-name").fill("a\tb")
        checks.append((f"제어문자(탭): 이름 형식 오류 문구",
                       a.get_by_test_id("create-name-help").inner_text().strip() == MSG["ROOM_NAME_FORMAT"]))
        checks.append(("제어문자: 만들기 비활성", a.get_by_test_id("create-submit-room").is_disabled()))
        a.get_by_test_id("create-name").fill("")
        a.get_by_test_id("create-name").press_sequentially("가" * 25)
        n = len(a.get_by_test_id("create-name").input_value())
        checks.append((f"25자 입력: maxlength 24에서 멈춤 (실제 {n})", n == 24))
        a.get_by_test_id("create-password").fill("abc")
        a.evaluate("document.querySelector('[data-testid=\"create-password\"]').blur()")
        expect(a.get_by_test_id("create-password-help")).to_have_text(MSG["PASSWORD_FORMAT"], timeout=3000)
        checks.append(("비밀번호 3자: 형식 오류 문구", True))
        checks.append(("비밀번호 형식 오류: 만들기 비활성", a.get_by_test_id("create-submit-room").is_disabled()))
        a.get_by_test_id("create-password").fill("")
        a.get_by_test_id("create-name").fill("정상이름")
        checks.append(("비밀번호 비움 + 이름 정상: 만들기 활성 (공개 방)", a.get_by_test_id("create-submit-room").is_enabled()))
        a.get_by_test_id("modal-cancel").click()
        expect(modal).to_have_count(0, timeout=3000)
        # 서버 검사 (UI 검사를 우회해도 같은 오류)
        r1 = adapter(a, "createRoom", {"name": "a\nb", "password": None, "nickname": "QaFormA"})
        checks.append((f"서버: 줄바꿈 이름 -> ROOM_NAME_FORMAT (실제 {r1.get('code')})", r1.get("code") == "ROOM_NAME_FORMAT"))
        r2 = adapter(a, "createRoom", {"name": "정상", "password": "abc", "nickname": "QaFormA"})
        checks.append((f"서버: 3자 비밀번호 -> PASSWORD_FORMAT (실제 {r2.get('code')})", r2.get("code") == "PASSWORD_FORMAT"))
        # 3개 초과
        for i in range(1, 4):
            r = adapter(a, "createRoom", {"name": f"꽉찬방{i}", "password": None, "nickname": "QaFormA"})
            checks.append((f"서버: 방 {i}개 생성 (ok)", r.get("ok") is True))
        a.get_by_test_id("room-create").click()
        expect(modal).to_be_visible(timeout=3000)
        a.get_by_test_id("create-name").fill("넷째방")
        a.get_by_test_id("create-submit-room").click()
        banner = a.get_by_test_id("modal-banner")
        expect(banner).to_be_visible(timeout=3000)
        checks.append(("4번째 방: TOO_MANY_ROOMS 문구 (모달 배너)", banner.inner_text().strip() == MSG["TOO_MANY_ROOMS"]))
        checks.append(("TOO_MANY_ROOMS: 모달 유지", a.get_by_test_id("modal-create").is_visible()))
        a.get_by_test_id("modal-cancel").click()
    finally:
        ctx.close()
    return verdict(checks)


@case(5, "잠금 방: 자물쇠, 틀린 비번 WRONG_PASSWORD, 맞는 비번 입장, 6번째 시도 RATE_LIMITED, 1분 뒤 복구")
def t05(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        a = open_as(ctx, col, "A", "a")
        create_profile(a, "QaLockA")
        ui_create_room(a, "잠금방5", pw="pass1234")
        checks.append(("HUD 잠금 방 표시 (room-title에 자물쇠 + 비밀번호 방)", a.get_by_test_id("room-title").locator(".bk-ico--lock").count() == 1))
        leave_room(a)
        rid = wait_row(a, "잠금방5")
        row = row_locator(a, rid)
        checks.append(("로비 행: data-locked=true, 자물쇠 아이콘", row.get_attribute("data-locked") == "true"
                       and row.locator(".bk-ico--lock").count() == 1))

        c = open_as(ctx, col, "C", "c")
        create_profile(c, "QaLockC")
        row_locator(c, wait_row(c, "잠금방5")).get_by_test_id("room-enter").click()
        pw_modal = c.get_by_test_id("modal-password")
        expect(pw_modal).to_be_visible(timeout=3000)
        checks.append(("잠금 방 입장: 비밀번호 모달", pw_modal.is_visible()))
        c.get_by_test_id("join-password").fill("nope1234")
        c.get_by_test_id("join-submit").click()
        expect(c.get_by_test_id("join-password-help")).to_have_text(MSG["WRONG_PASSWORD"], timeout=3000)
        checks.append(("틀린 비밀번호: WRONG_PASSWORD 문구, 모달 유지", pw_modal.is_visible()))
        checks.append(("틀린 비밀번호 후 입력 칸 비움", c.get_by_test_id("join-password").input_value() == ""))
        c.get_by_test_id("join-password").fill("pass1234")
        c.get_by_test_id("join-submit").click()
        wait_screen(c, "room")
        wait_conn(c)
        checks.append(("맞는 비밀번호: 입장 성공 (room)", sc(c) == "room"))
        leave_room(c)

        d = open_as(ctx, col, "D", "d")
        create_profile(d, "QaLockD")
        row_locator(d, wait_row(d, "잠금방5")).get_by_test_id("room-enter").click()
        expect(d.get_by_test_id("modal-password")).to_be_visible(timeout=3000)
        fails = []
        for i in range(5):
            d.get_by_test_id("join-password").fill(f"wrong{i:04d}")
            d.get_by_test_id("join-submit").click()
            ok = wait_until(lambda: d.get_by_test_id("join-password-help").inner_text().strip() == MSG["WRONG_PASSWORD"], 4)
            fails.append(bool(ok))
        checks.append((f"틀린 비밀번호 5회: 매번 WRONG_PASSWORD ({fails})", all(fails)))
        d.get_by_test_id("join-password").fill("pass1234")
        d.get_by_test_id("join-submit").click()
        banner = d.get_by_test_id("modal-banner")
        expect(banner).to_be_visible(timeout=4000)
        checks.append(("6번째 시도(맞는 비밀번호): RATE_LIMITED 문구", banner.inner_text().strip() == MSG["RATE_LIMITED"]))
        checks.append(("RATE_LIMITED: 모달 유지, 입장 안 됨", d.get_by_test_id("modal-password").is_visible() and sc(d) == "lobby"))
        # 1분 창 경과를 재현: 실패 기록의 시각을 61초 전으로 옮긴다 (DB 직접 수정). 주 버튼 10초 잠금도 기다린다.
        db_mut(d, "for (const f of db.failures) { if (f.user_id === 'as-d') f.at = now - 61000; }")
        time.sleep(10.5)
        d.get_by_test_id("join-password").fill("pass1234")
        d.get_by_test_id("join-submit").click()
        wait_screen(d, "room", 8)
        wait_conn(d)
        checks.append(("1분 경과 후 맞는 비밀번호 입장 성공 (실패 기록 시각을 61초 전으로 조정)", sc(d) == "room"))
    finally:
        ctx.close()
    return verdict(checks)


@case(6, "같은 방 닉네임 중복(대소문자 무시) -> NICK_TAKEN 모달 -> 다른 닉네임으로 입장. 다른 방에서는 같은 닉네임 허용")
def t06(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        a = open_as(ctx, col, "A", "a")
        create_profile(a, "QaNickA")
        ui_create_room(a, "닉방6")
        b = open_as(ctx, col, "B", "b")
        create_profile(b, "qanicka")
        row_locator(b, wait_row(b, "닉방6")).get_by_test_id("room-enter").click()
        modal = b.get_by_test_id("modal-nick")
        expect(modal).to_be_visible(timeout=3000)
        checks.append(("대소문자만 다른 닉네임 -> 닉네임 모달", modal.is_visible()))
        checks.append(("모달 제목 '닉네임이 겹쳐요'", modal.locator("h2").inner_text().strip() == MSG["NICK_TAKEN_TITLE"]))
        sug = b.get_by_test_id("room-nick-input").input_value()
        checks.append((f"제안 닉네임 = 프로필 + 2 (실제 {sug})", sug == "qanicka2"))
        b.get_by_test_id("room-nick-submit").click()
        wait_screen(b, "room")
        wait_conn(b)
        checks.append(("다른 닉네임으로 입장, 방 닉네임 = qanicka2", state(b)["room"]["nickname"] == "qanicka2"))
        prof = json.loads(b.evaluate("(k) => localStorage.getItem(k)", PROFILE_KEY.format("b")))
        checks.append(("프로필 닉네임은 그대로 qanicka", prof["nickname"] == "qanicka"))
        checks.append(("A 화면에 B가 qanicka2로 보임", wait_until(lambda: find_player(a, "qanicka2"), 4) is not None))
        r = adapter(b, "joinRoom", {"roomId": state(b)["room"]["id"], "password": None, "nickname": "QANICKA"})
        checks.append((f"서버: 같은 방 대소문자 무시 NICK_TAKEN (실제 {r.get('code')})", r.get("code") == "NICK_TAKEN"))
        # 다른 방: 같은 닉네임 허용
        c = open_as(ctx, col, "C", "c")
        create_profile(c, "QaNickA")
        ui_create_room(c, "닉방6b")
        checks.append(("다른 방에서는 같은 닉네임(QaNickA) 입장 허용", state(c)["room"]["nickname"] == "QaNickA"))
    finally:
        ctx.close()
    return verdict(checks)


@case(7, "20명 제한: 20명 찬 방에 21번째 ROOM_FULL (가짜 활성 멤버 DB 주입 + 실제 탭 2개)")
def t07(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        a = open_as(ctx, col, "A", "a")
        create_profile(a, "QaCapA")
        rid = ui_create_room(a, "정원7")
        inject_fakes(a, rid, 18, "cc")  # 방장 1 + 가짜 18 = 19명
        b = open_as(ctx, col, "B", "b")
        create_profile(b, "QaCapB")
        c = open_as(ctx, col, "C", "c")
        create_profile(c, "QaCapC")
        expect(row_locator(c, rid).get_by_test_id("room-members")).to_have_text("19/20명", timeout=8000)
        checks.append(("19명: 로비 인원 19/20명, 입장 가능", row_locator(c, rid).get_by_test_id("room-enter").is_enabled()))
        enter_from_lobby(b, "정원7")
        checks.append(("20번째 (B) 입장 성공", sc(b) == "room"))
        expect(row_locator(c, rid).get_by_test_id("room-members")).to_have_text("20/20명", timeout=8000)
        checks.append(("로비 가득 참: 20/20명 + is-full", "is-full" in (row_locator(c, rid).get_attribute("class") or "")))
        # C는 낡은 목록(19명)을 보고 있던 상태에서 누른다고 가정: 버튼을 강제로 눌러 서버 ROOM_FULL 경로를 탄다
        row_locator(c, rid).get_by_test_id("room-enter").evaluate("(el) => { el.disabled = false; el.click(); }")
        banner = c.get_by_test_id("lobby-banner")
        expect(banner).to_be_visible(timeout=4000)
        checks.append(("21번째: ROOM_FULL 배너 문구", banner.inner_text().strip() == MSG["ROOM_FULL"]))
        checks.append(("21번째: 로비에 머무름", sc(c) == "lobby"))
        r = adapter(c, "joinRoom", {"roomId": rid, "password": None, "nickname": "QaCapC"})
        checks.append((f"어댑터 직접 호출: ROOM_FULL (실제 {r.get('code')})", r.get("code") == "ROOM_FULL"))
        now_ms = time.time() * 1000
        ms = (db_get(a).get("members") or {}).get(rid) or {}
        active = [m for m in ms.values() if now_ms - m["last_seen_at"] < 60000]  # 가짜 멤버는 last_seen이 미래라 활성
        checks.append((f"DB 활성 멤버 20명 (방장 1 + 가짜 18 + B 1, 실제 {len(active)})", len(active) == 20))
    finally:
        ctx.close()
    return verdict(checks)


@case(8, "방 안: 서로 보임, 이동 반영, 채팅 말풍선 + 양쪽 로그 1번씩, 입/퇴장 시스템 메시지, 인원 표시")
def t08(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        a = open_as(ctx, col, "A", "a")
        create_profile(a, "QaEightA")
        ui_create_room(a, "방8")
        b = open_as(ctx, col, "B", "b")
        create_profile(b, "QaEightB")
        enter_from_lobby(b, "방8")
        c = open_as(ctx, col, "C", "c")
        create_profile(c, "QaEightC")
        enter_from_lobby(c, "방8")
        ok = wait_until(lambda: all(len(players(p)) == 3 for p in (a, b, c)), 5)
        checks.append(("세 화면 모두 서로 보임 (players 3명)", bool(ok)))
        checks.append(("인원 칩 3/20명 (A, B, C)", all(p.get_by_test_id("player-count").inner_text().strip() == "3/20명" for p in (a, b, c))))

        x0 = find_player(b, "QaEightA")["x"]
        hold_key(a, "ArrowRight", 1000)
        moved = wait_until(lambda: find_player(b, "QaEightA")["x"] - x0 >= 100, 4)
        checks.append((f"A 이동(우 1초) -> B 화면 반영 (dx {find_player(b, 'QaEightA')['x'] - x0:.0f}px)", bool(moved)))

        msg = "방8 안녕하세요"
        send_chat(a, msg)
        got_b = wait_until(lambda: find_player(b, "QaEightA") and find_player(b, "QaEightA")["lastChat"] == msg, 4)
        got_c = wait_until(lambda: find_player(c, "QaEightA") and find_player(c, "QaEightA")["lastChat"] == msg, 4)
        checks.append(("채팅 -> B, C 말풍선(lastChat) 수신", bool(got_b) and bool(got_c)))
        checks.append(("B 화면 말풍선 텍스트 = 메시지", (find_player(b, "QaEightA") or {}).get("bubble") == msg))
        time.sleep(0.6)
        cnts = [count_chat(p, msg) for p in (a, b, c)]
        checks.append((f"양쪽 로그에 1번씩 (A, B, C 각각 {cnts})", cnts == [1, 1, 1]))
        checks.append(("내 로그 줄 data-kind=self (A)", any(it["kind"] == "self" and msg in it["text"] for it in log_items(a))))

        # 입장 시스템 메시지: B는 A가 있을 때 들어왔고, C는 A/B가 있을 때 들어왔다.
        sys_b = f"QaEightB님이 들어왔어요"
        sys_c = f"QaEightC님이 들어왔어요"
        wait_until(lambda: count_sys(a, sys_c) >= 1 and count_sys(a, sys_b) >= 1, 4)
        checks.append((f"A 로그: B 입장 1번, C 입장 1번 ({count_sys(a, sys_b)}, {count_sys(a, sys_c)})",
                       count_sys(a, sys_b) == 1 and count_sys(a, sys_c) == 1))
        checks.append((f"처음 본 사람(C 입장 시점의 A, B)은 입장 메시지를 보지 않음: C 로그에 A/B 입장 없음 "
                       f"({count_sys(c, 'QaEightA님이 들어왔어요')}, {count_sys(c, sys_b)})",
                       count_sys(c, "QaEightA님이 들어왔어요") == 0 and count_sys(c, sys_b) == 0))

        # 퇴장: C가 나간다 -> A, B에서 인원 감소 + 퇴장 메시지 1번 (3초 지연)
        leave_room(c)
        hud_a = wait_until(lambda: a.get_by_test_id("player-count").inner_text().strip() == "2/20명", 3)
        checks.append(("C 나감: A 인원 칩 2/20명 (즉시)", bool(hud_a)))
        gone = wait_until(lambda: count_sys(a, "QaEightC님이 나갔어요") == 1, 6)
        checks.append(("C 나감: A 로그 '나갔어요' 1번 (3초 지연 후)", bool(gone)))
        checks.append(("C 나감: B 로그 '나갔어요' 1번", bool(wait_until(lambda: count_sys(b, "QaEightC님이 나갔어요") == 1, 4))))
    finally:
        ctx.close()
    return verdict(checks)


@case(9, "기록: 51개 보낸 뒤 새로 들어온 사람은 최근 50개만 오래된 순으로 본다")
def t09(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        a = open_as(ctx, col, "A", "a")
        create_profile(a, "QaHistA")
        rid = ui_create_room(a, "기록9")
        uid = state(a)["userId"]
        errs = []
        for i in range(1, 52):
            # 1초 제한을 피하려고 같은 사용자의 마지막 전송 시각만 0으로 되돌린다 (DB 직접 수정, 그 밖의 검사는 서버 규칙 그대로)
            db_mut(a, f"db.lastChat[{json.dumps(uid)}] = 0;")
            r = adapter(a, "sendChat", rid, f"msg-{i:02d}")
            if not r.get("ok"):
                errs.append((i, r.get("code")))
        checks.append((f"51개 전송 성공 (실패 {errs[:3]})", not errs))
        wait_until(lambda: count_chat(a, "msg-51") == 1, 5)
        checks.append(("A 로그에 51개 (msg-51 도착)", count_chat(a, "msg-51") == 1))

        c = open_as(ctx, col, "C", "c")
        create_profile(c, "QaHistC")
        enter_from_lobby(c, "기록9")
        # 로그 DOM 기준으로 센다 (getState.chatLog는 시스템 줄까지 포함한 '최근 50줄'이라 메시지 수와 다르다)
        wait_until(lambda: len([it for it in log_items(c) if it["id"]]) >= 50, 6)
        expect_list = [f"msg-{i:02d}" for i in range(2, 52)]
        rows = [it for it in log_items(c) if it["id"]]
        msgs = [next((m for m in expect_list if m in it["text"]), it["text"][:20]) for it in rows]
        checks.append((f"새 입장자 로그 메시지 줄 {len(rows)}개 (기대 50)", len(rows) == 50))
        checks.append(("오래된 순 2번~51번 (DOM 순서), 1번은 없음", msgs == expect_list))
        hist = [it for it in log_items(c) if it["kind"] == "history"]
        checks.append((f"구분 줄 '이전 대화 50개' (실제 {[h['text'] for h in hist]})",
                       any("이전 대화 50개" in h["text"] for h in hist)))
        ids = [int(it["id"]) for it in rows]
        checks.append(("DOM 로그 id 오름차순", ids == sorted(ids)))
        checks.append(("DOM에 msg-01 없음", all("msg-01" not in it["text"] for it in log_items(c))))
    finally:
        ctx.close()
    return verdict(checks)


@case(10, "새로고침 -> 비밀번호 없이 같은 방 재입장. 나가기 -> 로비, 다시 들어갈 때 잠금 방은 비밀번호 필요")
def t10(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        a = open_as(ctx, col, "A", "a")
        create_profile(a, "QaReA")
        rid = ui_create_room(a, "잠금재입장", pw="pass1234")
        a.reload()
        wait_screen(a, "room", 10)
        wait_conn(a)
        checks.append(("새로고침 후 같은 방 재입장 (room.id 동일, 비밀번호 창 없음)",
                       state(a)["room"]["id"] == rid and a.get_by_test_id("modal-dim").count() == 0))
        checks.append(("재입장 후 방 이름/잠금 표시 복구", state(a)["room"]["name"] == "잠금재입장" and state(a)["room"]["locked"] is True))
        ss = a.evaluate("(k) => sessionStorage.getItem(k)", SS_ROOM)
        checks.append(("sessionStorage mushroom:room = {roomId, nickname} 두 키", json.loads(ss) == {"roomId": rid, "nickname": "QaReA"}))
        leave_room(a)
        checks.append(("나가기 -> 로비, sessionStorage 삭제", a.evaluate("(k) => sessionStorage.getItem(k)", SS_ROOM) is None))
        row_locator(a, rid).get_by_test_id("room-enter").click()
        expect(a.get_by_test_id("modal-password")).to_be_visible(timeout=3000)
        checks.append(("나간 뒤 잠금 방 재입장: 비밀번호 모달 (멤버 행 삭제됨)", a.get_by_test_id("modal-password").is_visible()))
        a.get_by_test_id("join-password").fill("pass1234")
        a.get_by_test_id("join-submit").click()
        wait_screen(a, "room")
        wait_conn(a)
        checks.append(("비밀번호 입력 후 재입장 성공", sc(a) == "room"))
    finally:
        ctx.close()
    return verdict(checks)


@case(11, "만료: 활성 0명 30분 경과 방은 목록에서 사라짐 (DB 시각 조작), 29분 방은 유지")
def t11(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        a = open_as(ctx, col, "A", "a")
        create_profile(a, "QaExpA")
        rid_old = ui_create_room(a, "만료31분")
        leave_room(a)
        rid_new = ui_create_room(a, "만료29분")
        leave_room(a)
        checks.append(("나간 뒤 두 방 모두 목록에 있음(활성 0명, 30분 미경과)",
                       rid_by_name(a, "만료31분") and rid_by_name(a, "만료29분")))
        db_mut(a, f"""
            const o = db.rooms[{json.dumps(rid_old)}]; o.last_active_at = now - 31 * 60000;
            for (const m of Object.values(db.members[{json.dumps(rid_old)}] || {{}})) m.last_seen_at = now - 31 * 60000;
            const n = db.rooms[{json.dumps(rid_new)}]; n.last_active_at = now - 29 * 60000;
            for (const m of Object.values(db.members[{json.dumps(rid_new)}] || {{}})) m.last_seen_at = now - 29 * 60000;
        """)
        a.get_by_test_id("room-refresh").click()
        time.sleep(2.5)
        lobby_ready(a)
        checks.append(("31분 경과 방: 목록에서 사라짐", rid_by_name(a, "만료31분") is None))
        checks.append(("29분 방: 아직 목록에 있음", rid_by_name(a, "만료29분") == rid_new))
        checks.append(("31분 방: DB에서도 삭제됨(list_rooms 정리)", rid_old not in (db_get(a).get("rooms") or {})))
    finally:
        ctx.close()
    return verdict(checks)


@case(12, "모달 접근성: focus trap, Esc 취소, 포커스 복귀, 뒤 영역 inert, 딤 클릭 무시")
def t12(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        a = open_as(ctx, col, "A", "a")
        create_profile(a, "QaModalA")
        adapter(a, "createRoom", {"name": "잠금12", "password": "pass1234", "nickname": "QaModalA"})
        wait_row(a, "잠금12")
        inside_js = """(sel) => { const el = document.activeElement; const root = document.querySelector(sel);
          return !!(el && root && root.contains(el)); }"""
        a.get_by_test_id("room-create").click()
        modal = a.get_by_test_id("modal-create")
        expect(modal).to_be_visible(timeout=3000)
        checks.append(("모달 열림: 뒤 main inert", a.evaluate("() => { const m = document.querySelector('main'); return !!(m && m.inert); }") is True))
        checks.append(("모달 열림: body.has-modal", a.evaluate("document.body.classList.contains('has-modal')") is True))
        checks.append(("모달 열림: 포커스가 모달 안", a.evaluate(inside_js, '[data-testid="modal-create"]')))
        ok_tab = []
        for _ in range(12):
            a.keyboard.press("Tab")
            ok_tab.append(a.evaluate(inside_js, '[data-testid="modal-create"]'))
        checks.append((f"Tab 12회: 포커스가 모달 밖으로 나가지 않음 ({sum(ok_tab)}/12)", all(ok_tab)))
        ok_stab = []
        for _ in range(3):
            a.keyboard.press("Shift+Tab")
            ok_stab.append(a.evaluate(inside_js, '[data-testid="modal-create"]'))
        checks.append((f"Shift+Tab 3회: 모달 안 유지 ({sum(ok_stab)}/3)", all(ok_stab)))
        a.mouse.click(5, 5)
        checks.append(("딤(바깥) 클릭: 모달 닫히지 않음", modal.is_visible()))
        a.keyboard.press("Escape")
        expect(modal).to_have_count(0, timeout=3000)
        checks.append(("Esc: 모달 닫힘", True))
        checks.append(("닫힘: 뒤 main inert 해제", a.evaluate("() => { const m = document.querySelector('main'); return !!(m && !m.inert); }") is True))
        checks.append(("닫힘: body.has-modal 제거", a.evaluate("document.body.classList.contains('has-modal')") is False))
        focus = a.evaluate("document.activeElement && document.activeElement.getAttribute('data-testid')")
        checks.append((f"Esc 후 포커스 = 방 만들기 버튼 (실제 {focus})", focus == "room-create"))

        rid = rid_by_name(a, "잠금12")
        row_locator(a, rid).get_by_test_id("room-enter").click()
        pw = a.get_by_test_id("modal-password")
        expect(pw).to_be_visible(timeout=3000)
        a.keyboard.press("Escape")
        expect(pw).to_have_count(0, timeout=3000)
        focus2 = a.evaluate("(() => { const el = document.activeElement; return el ? [el.getAttribute('data-testid'), el.closest('[data-room-id]') && el.closest('[data-room-id]').getAttribute('data-room-id')] : null; })()")
        checks.append((f"비밀번호 모달 Esc: 포커스가 그 방의 입장 버튼으로 복귀 (실제 {focus2})",
                       focus2 is not None and focus2[0] == "room-enter" and focus2[1] == rid))
        checks.append(("로비 유지 (입장 안 함)", sc(a) == "lobby"))
        checks.append(("IME 조합 중 Esc 무시, Safari 15.4 미만 inert 대체 경로", None))
    finally:
        ctx.close()
    return verdict(checks)


@case(13, "모바일 360x640: 로비/방/모달 가로 스크롤과 겹침 없음, 로그 접힘 기본과 안 읽은 수, 펼침 크기")
def t13(browser, col):
    ctx = new_ctx(browser, viewport={"width": 360, "height": 640}, is_mobile=True, has_touch=True, device_scale_factor=2)
    checks = []
    try:
        a = open_as(ctx, col, "A", "a")
        create_profile(a, "모바일방장", pick=PICK)
        adapter(a, "createRoom", {"name": "ABCDEFGHIJKLMNOPQRSTUVWX", "password": "pass1234", "nickname": "모바일방장"})
        adapter(a, "createRoom", {"name": "두번째 방", "password": None, "nickname": "모바일방장"})
        wait_row(a, "두번째 방", 8)
        lobby_ok = a.evaluate("""() => ({
          hscroll: document.documentElement.scrollWidth > document.documentElement.clientWidth,
          vscroll: document.scrollingElement.scrollHeight > document.scrollingElement.clientHeight + 1 })""")
        checks.append(("로비: 가로 스크롤 없음", not lobby_ok["hscroll"]))
        checks.append(("로비: 페이지 자체 세로 스크롤 없음 (목록만 스크롤)", not lobby_ok["vscroll"]))
        name_box = a.locator('[data-testid="room-row"] [data-testid="room-name"]').first.bounding_box()
        enter_box = a.locator('[data-testid="room-row"] [data-testid="room-enter"]').first.bounding_box()
        checks.append(("로비: 방 이름 칸과 입장 버튼 겹치지 않음", name_box["x"] + name_box["width"] <= enter_box["x"] + 1))
        a.get_by_test_id("room-create").click()
        m = a.get_by_test_id("modal-create")
        expect(m).to_be_visible(timeout=3000)
        mb = m.bounding_box()
        checks.append((f"만들기 모달: 화면 안(위 {mb['y']:.0f}, 아래 {mb['y'] + mb['height']:.0f} / 640)",
                       mb["y"] >= 56 and mb["y"] + mb["height"] <= 640))
        checks.append(("모달: 가로 스크롤 없음", not a.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")))
        a.keyboard.press("Escape")
        expect(m).to_have_count(0, timeout=3000)

        ui_create_room(a, "모바일방")
        checks.append(("방 캔버스 360x508 (세로 = 640 - 조작 영역 132)",
                       (lambda bb: abs(bb["width"] - 360) <= 1 and abs(bb["height"] - 508) <= 1)(a.get_by_test_id("game-canvas").bounding_box())))
        toggle = a.get_by_test_id("log-toggle")
        checks.append(("로그 접힘 기본 (aria-expanded=false)", toggle.get_attribute("aria-expanded") == "false"))
        checks.append(("방 화면 가로 스크롤 없음", not a.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")))
        b = open_as(ctx, col, "B", "b")
        create_profile(b, "모바일친구")
        enter_from_lobby(b, "모바일방")
        send_chat(b, "모바일 알림 테스트")
        unread = wait_until(lambda: a.get_by_test_id("log-toggle-unread").is_visible() and a.get_by_test_id("log-toggle-unread").inner_text().strip() == "1", 4)
        checks.append(("접힌 로그 토글에 안 읽은 수 1", bool(unread)))
        toggle.click()
        wait_until(lambda: "is-collapsed" not in (a.get_by_test_id("log-panel").get_attribute("class") or ""), 3)
        pb = a.get_by_test_id("log-panel").bounding_box()
        checks.append((f"펼친 로그 크기 344 x 282 근처 (실제 {pb['width']:.0f}x{pb['height']:.0f})",
                       abs(pb["width"] - 344) <= 4 and 96 <= pb["height"] <= 320))
        cb = a.get_by_test_id("game-canvas").bounding_box()
        checks.append(("펼친 로그가 캔버스 안에 있음", pb["x"] >= cb["x"] - 1 and pb["x"] + pb["width"] <= cb["x"] + cb["width"] + 1))
        checks.append(("펼친 뒤 안 읽은 수 배지 0 (숨김)", not a.get_by_test_id("log-toggle-unread").is_visible()))
        ib = a.get_by_test_id("chat-input").bounding_box()
        checks.append(("채팅 입력이 화면 안", ib["y"] + ib["height"] <= 640 and ib["y"] >= 0))
        a.get_by_test_id("log-fold").click()
        checks.append(("닫기 누르면 토글로 포커스 복귀", a.evaluate("document.activeElement && document.activeElement.getAttribute('data-testid')") == "log-toggle"))
    finally:
        ctx.close()
    return verdict(checks)


@case(14, "로비 폴링: 5초 갱신, 탭 숨김 중 정지, 다시 보이면 즉시 1회 + 재개")
def t14(browser, col):
    ctx = new_ctx(browser)
    ctx.add_init_script(LOCKCOUNT_JS)
    ctx.add_init_script(VIS_JS)
    checks = []
    try:
        a = open_as(ctx, col, "A", "a")
        create_profile(a, "QaPollA")
        lobby_ready(a)
        n0 = a.evaluate("(window.__lockCount || {})['mushroom.local.v4.db'] || 0")
        time.sleep(11)
        n1 = a.evaluate("(window.__lockCount || {})['mushroom.local.v4.db'] || 0")
        checks.append((f"보이는 상태 11초: 목록 요청 {n1 - n0}회 (기대 2회 이상)", n1 - n0 >= 2))
        a.evaluate("() => { window.__vis = 'hidden'; document.dispatchEvent(new Event('visibilitychange')); }")
        time.sleep(1)
        n2 = a.evaluate("(window.__lockCount || {})['mushroom.local.v4.db'] || 0")
        time.sleep(12)
        n3 = a.evaluate("(window.__lockCount || {})['mushroom.local.v4.db'] || 0")
        checks.append((f"숨김 12초: 목록 요청 {n3 - n2}회 (기대 0)", n3 - n2 == 0))
        a.evaluate("() => { window.__vis = 'visible'; document.dispatchEvent(new Event('visibilitychange')); }")
        time.sleep(0.6)
        n4 = a.evaluate("(window.__lockCount || {})['mushroom.local.v4.db'] || 0")
        checks.append((f"다시 보임: 즉시 1회 갱신 (증가 {n4 - n3})", n4 - n3 >= 1))
        time.sleep(6)
        n5 = a.evaluate("(window.__lockCount || {})['mushroom.local.v4.db'] || 0")
        checks.append((f"다시 보인 뒤 6초: 폴링 재개 (증가 {n5 - n4})", n5 - n4 >= 1))
    finally:
        ctx.close()
    return verdict(checks)


@case(15, "필수: 같은 계정 두 탭 동시 접속 -> 한 사람으로 집계, 중복 줄/중복 입장 없음, 한쪽 나가기 영향")
def t15(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        t1 = open_as(ctx, col, "T1", "a")
        create_profile(t1, "QaTabA")
        ui_create_room(t1, "탭방")
        t2 = open_as(ctx, col, "T2", "a")  # 같은 ?as=a: 같은 uid, 같은 프로필 키
        checks.append(("두 번째 탭: 프로필 저장됨 -> 로비", sc(t2) == "lobby"))
        enter_from_lobby(t2, "탭방")
        checks.append(("같은 계정 두 번째 탭 입장 성공 (NICK_TAKEN 없음, 비밀번호 없음)", sc(t2) == "room"))
        checks.append(("두 탭 userId 동일 (as-a)", state(t1)["userId"] == state(t2)["userId"] == "as-a"))
        time.sleep(1.5)
        listed = (adapter(t2, "listRooms").get("value") or [])
        checks.append((f"DB 멤버 1행 (listRooms 인원 1)", [r["members"] for r in listed if r["name"] == "탭방"] == [1]))
        checks.append(("HUD: 인원 칩 1/20명 (같은 사람은 한 명)", t1.get_by_test_id("player-count").inner_text().strip() == "1/20명"
                       and t2.get_by_test_id("player-count").inner_text().strip() == "1/20명"))
        msg = "탭 중복 테스트"
        send_chat(t1, msg)
        time.sleep(0.8)
        checks.append((f"채팅 한 번: 두 탭 로그에 각각 1번 (t1 {count_chat(t1, msg)}, t2 {count_chat(t2, msg)})",
                       count_chat(t1, msg) == 1 and count_chat(t2, msg) == 1))
        checks.append(("두 탭 모두 연결 상태 connected", state(t1)["connection"] == "connected" and state(t2)["connection"] == "connected"))
        # 한쪽에서 나가면 같은 멤버 행이 지워진다 -> 다른 탭은 하트비트에서 NOT_MEMBER -> 자동 재입장 (최대 25초)
        leave_room(t2)
        recovered = wait_until(lambda: state(t1).get("connection") == "connected" and sc(t1) == "room", 28, interval=0.5)
        checks.append((f"한 탭이 나가면 다른 탭: 최대 25초 안 자동 재입장 (같은 멤버 행이라 영향 받음, 설계 확인 필요)",
                       bool(recovered)))
    finally:
        ctx.close()
    return verdict(checks)


@case(16, "필수: 연결 끊김 후 재접속 (멤버 행 강제 삭제 -> 하트비트 NOT_MEMBER -> 자동 재입장; 잠금 방은 실패 -> 로비)")
def t16(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        a = open_as(ctx, col, "A", "a")
        create_profile(a, "QaRecA")
        rid = ui_create_room(a, "재접속방")
        b = open_as(ctx, col, "B", "b")
        create_profile(b, "QaRecB")
        enter_from_lobby(b, "재접속방")
        wait_until(lambda: find_player(a, "QaRecB"), 4)
        uid = state(a)["userId"]
        db_mut(a, f"delete db.members[{json.dumps(rid)}][{json.dumps(uid)}];")  # 서버가 멤버를 잃은 상황
        # (이하 잠금 방 시나리오는 방을 바꾸므로 먼저 나간다)
        seen = []
        t0 = time.time()
        while time.time() - t0 < 32:
            c = state(a).get("connection")
            if not seen or seen[-1] != c:
                seen.append(c)
            if c == "connected" and len(seen) > 1 and sc(a) == "room":
                break
            time.sleep(0.2)
        # 자동 재입장은 조용히 끝난다(성공 시 상태 변화 없음). 서버 행이 다시 생겼는지로 확인한다.
        def row_back(uid_, rid_):
            ms = (db_get(a).get("members") or {}).get(rid_) or {}
            m = ms.get(uid_)
            return m is not None and time.time() * 1000 - m["last_seen_at"] < 30000

        back = wait_until(lambda: row_back(uid, rid), 32, interval=0.3)
        checks.append((f"하트비트 NOT_MEMBER 후 서버 멤버 행 자동 복구 (상태 변화 {seen})", bool(back)))
        checks.append(("재입장 후 방 화면 유지, 닉네임 QaRecA 그대로", sc(a) == "room" and state(a)["room"]["nickname"] == "QaRecA"))
        checks.append(("재입장 후 배너 없음 (끊김 안내 안 뜸)", not a.get_by_test_id("game-banner").is_visible()))
        send_chat(b, "재접속 후 전달 확인")
        checks.append(("재접속 후 B 채팅이 A 로그에 1번", bool(wait_until(lambda: count_chat(a, "재접속 후 전달 확인") == 1, 4))))
        # 같은 세션에서 두 번째 끊김: 설계(room.md 7장)는 끊김마다 자동 재입장 1회. 현재 구현은 첫 시도 이후 플래그가 남는지 확인
        db_mut(a, f"delete db.members[{json.dumps(rid)}][{json.dumps(uid)}];")
        back2 = wait_until(lambda: row_back(uid, rid), 32, interval=0.3)
        banner_shown = a.get_by_test_id("game-banner").is_visible()
        checks.append((f"두 번째 끊김(같은 세션)도 자동 재입장 1회 시도 (설계 7장 기준; 복구 {bool(back2)}, 끊김 배너 {banner_shown})",
                       bool(back2)))
        if banner_shown:
            a.get_by_test_id("reconnect-button").click()
            wait_screen(a, "lobby")
        else:
            leave_room(a)

        # 잠금 방: 자동 재입장은 비밀번호가 없어 실패 -> '로비에서 다시 들어와 주세요' + 로비로
        if sc(a) == "room":
            leave_room(a)
        c_rid = ui_create_room(a, "재접속잠금", pw="pass1234")
        uid_a = state(a)["userId"]
        db_mut(a, f"delete db.members[{json.dumps(c_rid)}][{json.dumps(uid_a)}];")
        banner = a.get_by_test_id("game-banner")
        expect(banner).to_be_visible(timeout=32000)
        checks.append((f"잠금 방 재접속 실패: 배너 문구 (실제 '{banner.inner_text().strip()[:30]}')",
                       MSG["NOT_MEMBER"] in banner.inner_text()))
        a.get_by_test_id("reconnect-button").click()
        wait_screen(a, "lobby")
        checks.append(("배너 버튼 '로비로' -> 로비", sc(a) == "lobby"))
    finally:
        ctx.close()
    return verdict(checks)


@case(17, "탭 닫기 -> 상대 화면에서 제거 (Presence 즉시), 퇴장 메시지 1번, 로비 인원은 활성 60초 규칙")
def t17(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        a = open_as(ctx, col, "A", "a")
        create_profile(a, "QaCloseA")
        ui_create_room(a, "닫기방")
        b = open_as(ctx, col, "B", "b")
        create_profile(b, "QaCloseB")
        enter_from_lobby(b, "닫기방")
        wait_until(lambda: find_player(a, "QaCloseB"), 4)
        rid = state(a)["room"]["id"]
        t0 = time.time()
        b.close()
        gone = wait_until(lambda: find_player(a, "QaCloseB") is None, 6, interval=0.05)
        el = time.time() - t0
        checks.append((f"B 탭 닫기 -> A 화면에서 제거 (경과 {el:.2f}s, 기준 3s 이내)", bool(gone) and el <= 3.0))
        checks.append(("A 인원 칩 1/20명", wait_until(lambda: a.get_by_test_id("player-count").inner_text().strip() == "1/20명", 3) is not None))
        checks.append(("퇴장 메시지 1번 (3초 지연 후)", bool(wait_until(lambda: count_sys(a, "QaCloseB님이 나갔어요") == 1, 6))))
        n_now = [r["members"] for r in rooms_of(a) if r["name"] == "닫기방"]
        right_after = [r["members"] for r in adapter(a, "listRooms")["value"] if r["id"] == rid]
        checks.append((f"닫은 직후 로비 인원은 아직 2명 (활성 60초 규칙, 실제 {right_after})", right_after == [2]))
        # 활성 60초 + 하트비트 간격(20초) 안에 줄어야 한다. 닫은 시점부터 62초 뒤 확인
        remain = 62 - (time.time() - t0)
        if remain > 0:
            time.sleep(remain)
        members_after = [r["members"] for r in adapter(a, "listRooms")["value"] if r["id"] == rid]
        checks.append((f"닫은 뒤 62초: 로비 인원 1명으로 줄어듦 (실제 {members_after})", members_after == [1]))
    finally:
        ctx.close()
    return verdict(checks)


# ---------------------------------------------------------------------------
# 공통 항목 (사이클 3에서 이어짐, 방 흐름으로 옮김)
# ---------------------------------------------------------------------------
@case(18, "XSS: 닉네임 형식 거부, 방 이름/채팅의 <img onerror>가 실행되지 않고 문자열로 표시")
def t18(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        a = open_as(ctx, col, "A", "a")
        wait_screen(a, "profile")
        a.get_by_test_id("nickname-input").press_sequentially(XSS_NICK)
        checks.append(("XSS 닉네임: 형식 오류 상태", a.get_by_test_id("nickname-status").get_attribute("data-state") == "format"))
        a.get_by_test_id("nickname-input").press("Enter")
        time.sleep(0.4)
        checks.append(("XSS 닉네임: Enter로도 저장 안 됨 (profile 유지)", sc(a) == "profile"))
        r = adapter(a, "createRoom", {"name": "xss", "password": None, "nickname": XSS_NICK})
        checks.append((f"서버: XSS 닉네임 NICK_FORMAT (실제 {r.get('code')})", r.get("code") == "NICK_FORMAT"))
        create_profile(a, "QaXssA")
        leave_room(a) if sc(a) == "room" else None
        a.get_by_test_id("room-create").click()
        expect(a.get_by_test_id("modal-create")).to_be_visible(timeout=3000)
        a.get_by_test_id("create-name").fill(XSS_NAME)
        a.get_by_test_id("create-submit-room").click()
        wait_screen(a, "room")
        wait_conn(a)
        checks.append(("방 이름 XSS: 방 화면 제목이 문자열 그대로", a.get_by_test_id("room-title-text").inner_text().strip() == XSS_NAME))
        b = open_as(ctx, col, "B", "b")
        create_profile(b, "QaXssB")
        xss_rid = wait_row(b, XSS_NAME)
        row_name = row_locator(b, xss_rid).get_by_test_id("room-name").inner_text().strip()
        checks.append(("로비 방 이름 XSS: 문자열 그대로", row_name == XSS_NAME))
        checks.append(("로비 방 이름 XSS: img/onerror 요소 없음",
                       b.evaluate("document.querySelectorAll('img').length + document.querySelectorAll('[onerror]').length") == 0))
        enter_from_lobby(b, XSS_NAME)
        send_chat(a, XSS_TAG)
        got = wait_until(lambda: find_player(b, "QaXssA") and find_player(b, "QaXssA")["lastChat"] == XSS_TAG, 4)
        checks.append(("채팅 XSS: B에 문자열로 수신", bool(got)))
        time.sleep(1.0)
        for label, pg in (("A", a), ("B", b)):
            xss = pg.evaluate("typeof window.__xss")
            imgs = pg.evaluate("document.querySelectorAll('img').length")
            onerr = pg.evaluate("document.querySelectorAll('[onerror]').length")
            checks.append((f"{label}: window.__xss 미정의 ({xss})", xss == "undefined"))
            checks.append((f"{label}: img 요소 0개 (실제 {imgs})", imgs == 0))
            checks.append((f"{label}: onerror 속성 요소 0개 (실제 {onerr})", onerr == 0))
        checks.append(("B 로그에 XSS 문자열이 텍스트로 있음", count_chat(b, XSS_TAG) == 1))
    finally:
        ctx.close()
    return verdict(checks)


@case(19, "채팅 80자 초과 제한, 1초 쿨다운(클라이언트), 서버 TEXT_FORMAT/RATE_LIMITED")
def t19(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        a = open_as(ctx, col, "A", "a")
        create_profile(a, "QaChatA")
        ui_create_room(a, "채팅방19")
        b = open_as(ctx, col, "B", "b")
        create_profile(b, "QaChatB")
        enter_from_lobby(b, "채팅방19")
        a.get_by_test_id("chat-input").click()
        a.keyboard.type("가" * 81)
        n = len(a.get_by_test_id("chat-input").input_value())
        checks.append((f"81자 입력: 입력 칸 80자에서 멈춤 (실제 {n})", n == 80))
        checks.append(("글자 수 카운터 80/80", a.get_by_test_id("chat-counter").inner_text().strip() == "80/80"))
        a.keyboard.press("Enter")
        got = wait_until(lambda: find_player(b, "QaChatA") and len(find_player(b, "QaChatA")["lastChat"] or "") == 80, 4)
        checks.append(("80자 메시지 B에 전달", bool(got)))
        a.keyboard.type("두번째")
        a.keyboard.press("Enter")
        hint = a.get_by_test_id("chat-hint")
        expect(hint).to_be_visible(timeout=1000)
        checks.append(("쿨다운 힌트 문구", hint.inner_text().strip() == MSG["COOLDOWN"]))
        checks.append(("쿨다운 중 입력 유지", a.get_by_test_id("chat-input").input_value() == "두번째"))
        checks.append(("쿨다운 중 전송 버튼 비활성", a.get_by_test_id("chat-send").is_disabled()))
        time.sleep(0.2)
        checks.append(("쿨다운 중 B에 미전달", find_player(b, "QaChatA")["lastChat"] != "두번째"))
        time.sleep(1.1)
        a.keyboard.press("Enter")
        got2 = wait_until(lambda: find_player(b, "QaChatA")["lastChat"] == "두번째", 4)
        checks.append(("쿨다운 종료 후 전송 성공", bool(got2)))
        r = adapter(a, "sendChat", state(a)["room"]["id"], "가" * 81)
        checks.append((f"서버: 81자 TEXT_FORMAT (실제 {r.get('code')})", r.get("code") == "TEXT_FORMAT"))
        r = adapter(a, "sendChat", state(a)["room"]["id"], "줄\n바꿈")
        checks.append((f"서버: 줄바꿈 포함 TEXT_FORMAT (실제 {r.get('code')})", r.get("code") == "TEXT_FORMAT"))
        r = adapter(a, "sendChat", state(a)["room"]["id"], "서버 제한")
        checks.append((f"서버: 1초 안 두 번째 RATE_LIMITED (실제 {r.get('code')})", r.get("code") == "RATE_LIMITED"))
    finally:
        ctx.close()
    return verdict(checks)


@case(20, "방 입퇴장 3회 후 리소스 누수 없음 (BroadcastChannel, setInterval, rAF, .screen 수): 로비 기준값과 비교")
def t20(browser, col):
    init = """
    (() => {
      const L = { bcOpen: 0, bcClosed: 0, intervals: new Set(), rafs: new Set() };
      window.__qaLeak = L;
      const OBC = window.BroadcastChannel;
      if (OBC) {
        window.BroadcastChannel = class extends OBC {
          constructor(...a) { super(...a); L.bcOpen++; }
          close() { if (!this.__closed) { this.__closed = true; L.bcClosed++; } return super.close(); }
        };
      }
      const si = window.setInterval, ci = window.clearInterval;
      window.setInterval = function (fn, ms, ...a) { const id = si.call(window, fn, ms, ...a); L.intervals.add(id); return id; };
      window.clearInterval = function (id) { L.intervals.delete(id); return ci.call(window, id); };
      const raf = window.requestAnimationFrame, caf = window.cancelAnimationFrame;
      window.requestAnimationFrame = function (fn) {
        const id = raf.call(window, (t) => { L.rafs.delete(id); fn(t); }); L.rafs.add(id); return id;
      };
      window.cancelAnimationFrame = function (id) { L.rafs.delete(id); return caf.call(window, id); };
    })();
    """
    ctx = new_ctx(browser)
    ctx.add_init_script(init)
    checks = []
    try:
        page = open_as(ctx, col, "L", "l")
        create_profile(page, "QaLeakL")
        ui_create_room(page, "누수방")  # 방 생성은 1회차 입장으로 본다
        leave_room(page)

        def counters(pg):
            return pg.evaluate("""() => { const L = window.__qaLeak;
              return { bcLive: L.bcOpen - L.bcClosed, intervals: L.intervals.size, rafs: L.rafs.size,
                       screens: document.querySelectorAll('.screen').length }; }""")

        time.sleep(0.5)
        base = counters(page)
        checks.append((f"로비 기준값 {base}", base["screens"] == 1))
        rid = rid_by_name(page, "누수방")
        for i in range(1, 4):
            row_locator(page, rid).get_by_test_id("room-enter").click()
            wait_screen(page, "room")
            wait_conn(page)
            time.sleep(0.6)
            inside = counters(page)
            checks.append((f"{i}회차 방 안: 타이머/채널이 실제로 올라감 ({inside})", inside["bcLive"] >= 1 and inside["intervals"] >= 1))
            leave_room(page)
            time.sleep(0.4)
            c = counters(page)
            checks.append((f"{i}회차 나간 뒤 로비 기준값과 같음 (실제 {c})",
                           c["bcLive"] == base["bcLive"] and c["intervals"] == base["intervals"]
                           and c["rafs"] == base["rafs"] and c["screens"] == 1))
        checks.append(("리스너 개수, JS 힙은 DevTools 없이 측정하지 않음", None))
    finally:
        ctx.close()
    return verdict(checks)


# 방 화면 픽셀 검사 (캔버스 스크린샷). 글자(라벨, 말풍선) 영역은 마스크한다.
FILLTEXT_HOOK = """
(() => {
  window.__qaFill = {};
  const orig = CanvasRenderingContext2D.prototype.fillText;
  CanvasRenderingContext2D.prototype.fillText = function (text, x, y, ...rest) {
    try {
      window.__qaFill[String(text)] = { x: x, y: y, w: this.measureText(String(text)).width, align: this.textAlign };
    } catch (e) { /* 기록 실패가 그리기를 막으면 안 된다 */ }
    return orig.call(this, text, x, y, ...rest);
  };
})();
"""

HIDE_ROOM_JS = """() => {
  for (const s of ['.hud', '.hud-row2', '.room-log', '.hud-room', '.bk-count', '.chat-float', '.hint-desktop',
                   '.room-log-toggle', '.hud-banner', '[data-testid="mode-badge"]']) {
    document.querySelectorAll(s).forEach((e) => { e.style.visibility = 'hidden'; });
  }
}"""


def canvas_text_boxes(pg):
    recs = pg.evaluate("window.__qaFill || {}")
    boxes = []
    for text, v in recs.items():
        if v.get("align") == "left":
            l, r = v["x"] - 8, v["x"] + v["w"] + 8
        else:
            half = v["w"] / 2 + 8
            l, r = v["x"] - half, v["x"] + half
        boxes.append((l, v["y"] - 8, r, v["y"] + 18, text))
    return boxes


def pixel_check(png, k, boxes_css, dsf, band_frac=0.35):
    import io
    import numpy as np
    from PIL import Image

    arr = np.asarray(Image.open(io.BytesIO(png)).convert("RGB"))
    H, W, _ = arr.shape
    if H % k or W % k:
        return {"error": f"스크린샷 {W}x{H}가 블록 {k}의 배수가 아님"}
    mask = np.zeros((H, W), dtype=bool)
    for l, t, r, b, _ in boxes_css:
        mask[max(0, int(t * dsf)):min(H, int(b * dsf) + 1), max(0, int(l * dsf)):min(W, int(r * dsf) + 1)] = True
    bh, bw = H // k, W // k
    blocks = arr.reshape(bh, k, bw, k, 3)
    uniform = (blocks == blocks[:, :1, :, :1, :]).all(axis=(1, 3, 4))
    bmask = mask.reshape(bh, k, bw, k).any(axis=(1, 3))
    band_rows = max(1, int(bh * band_frac))
    h_px = band_rows * k
    band = arr[:h_px]
    m = mask[:h_px]
    cx = (band[:, 1:] != band[:, :-1]).any(axis=2) & ~(m[:, 1:] | m[:, :-1])
    cy = (band[1:] != band[:-1]).any(axis=2) & ~(m[1:] | m[:-1])
    mis_x = int(cx[:, np.arange(1, W) % k != 0].sum())
    mis_y = int(cy[np.arange(1, h_px) % k != 0, :].sum())
    return {
        "size": (W, H), "blocks": int(uniform.size),
        "bad_outside": int(np.count_nonzero(~uniform & ~bmask)),
        "band_bad": int(np.count_nonzero(~uniform[:band_rows] & ~bmask[:band_rows])),
        "mis_x": mis_x, "mis_y": mis_y,
        "band_colors": int(len(np.unique(band[~m].reshape(-1, 3), axis=0))),
    }


@case(21, "모바일 360x640 + 데스크톱: 방/로비/프로필 가로 스크롤 없음, 모드 칩 비겹침, 터치 버튼으로 이동")
def t21(browser, col):
    checks = []
    BADGE_JS = """() => {
      const badge = document.querySelector('[data-testid="mode-badge"]');
      if (!badge) return { missing: true, hits: [] };
      const vis = (el) => { const r = el.getBoundingClientRect(); if (r.width <= 0 || r.height <= 0) return false;
        const cs = getComputedStyle(el); return cs.visibility !== 'hidden' && cs.display !== 'none' && parseFloat(cs.opacity) > 0; };
      const br = badge.getBoundingClientRect(); const hits = [];
      for (const el of document.body.querySelectorAll('*')) {
        if (el === badge || el.contains(badge) || badge.contains(el)) continue;
        if (el.closest('[data-testid="world-bg"]') || el.getAttribute('data-testid') === 'game-canvas') continue;
        if (el.children.length > 0 && el.tagName !== 'CANVAS') continue;
        if (!vis(el)) continue;
        const r = el.getBoundingClientRect();
        const ix = Math.min(r.right, br.right) - Math.max(r.left, br.left);
        const iy = Math.min(r.bottom, br.bottom) - Math.max(r.top, br.top);
        if (ix > 0.5 && iy > 0.5) hits.push((el.getAttribute('data-testid') || el.tagName.toLowerCase()) + ' "' + (el.textContent || '').trim().slice(0, 16) + '"');
      }
      return { missing: false, hits };
    }"""
    noh = "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    for tag, vw, vh, dsf, mob in (("1280x800", 1280, 800, 1, False), ("1920x1080", 1920, 1080, 1, False), ("360x640", 360, 640, 2, True)):
        ctx = new_ctx(browser, viewport={"width": vw, "height": vh}, device_scale_factor=dsf, is_mobile=mob, has_touch=mob)
        try:
            page = open_as(ctx, col, f"L{tag}", "a")
            checks.append((f"[{tag}] 프로필: 가로 스크롤 없음", page.evaluate(noh)))
            checks.append((f"[{tag}] 프로필: 모드 칩과 겹침 0 {page.evaluate(BADGE_JS)['hits'][:3]}", not page.evaluate(BADGE_JS)["hits"]))
            create_profile(page, "레이아웃방")
            checks.append((f"[{tag}] 로비: 가로 스크롤 없음", page.evaluate(noh)))
            checks.append((f"[{tag}] 로비: 모드 칩 겹침 0 {page.evaluate(BADGE_JS)['hits'][:3]}", not page.evaluate(BADGE_JS)["hits"]))
            ui_create_room(page, "레이아웃")
            time.sleep(0.4)
            checks.append((f"[{tag}] 방: 가로 스크롤 없음", page.evaluate(noh)))
            res = page.evaluate(BADGE_JS)
            checks.append((f"[{tag}] 방: 모드 칩과 겹치는 요소 0 (실제 {res.get('hits', [])[:3]})", not res.get("hits")))
            if mob:
                cv = page.get_by_test_id("game-canvas").bounding_box()
                checks.append((f"[{tag}] 캔버스 360x508", abs(cv["width"] - 360) <= 1 and abs(cv["height"] - 508) <= 1))
                for tid in ("move-left", "move-right"):
                    bb = page.get_by_test_id(tid).bounding_box()
                    checks.append((f"[{tag}] {tid} 높이 44 이상 (실제 {bb['height']:.0f})", bb["height"] >= 44))
                bb = page.get_by_test_id("move-right").bounding_box()
                cx, cy = bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2
                hit = page.evaluate("([x, y]) => { const e = document.elementFromPoint(x, y); return !!(e && e.closest('[data-testid=move-right]')); }", [cx, cy])
                checks.append(("터치 지점이 오른쪽 버튼에 맞음", hit))
                x0 = state(page)["me"]["x"]
                cdp = ctx.new_cdp_session(page)
                cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": cx, "y": cy}]})
                time.sleep(1.0)
                cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
                time.sleep(0.2)
                dx = state(page)["me"]["x"] - x0
                checks.append((f"터치 1초 홀드로 오른쪽 이동 (dx {dx:.0f}px, 기대 약 160)", dx >= 100))
                checks.append(("이동 후 가로 스크롤 없음", page.evaluate(noh)))
        finally:
            ctx.close()
    return verdict(checks)


@case(22, "픽셀 선명도: 방 캔버스 스크린샷에서 아트 픽셀이 배율 P의 균일 정사각 블록 (HUD 숨김, 라벨 마스크)")
def t22(browser, col):
    try:
        import numpy  # noqa: F401
        import PIL  # noqa: F401
    except ImportError as e:
        return ("UNVERIFIED", f"numpy/Pillow가 없어 픽셀 검사를 하지 못함: {e}", [("픽셀 검사 라이브러리", None)])
    configs = [("데스크톱 1280x800 dpr1", 1280, 800, 1, False, 2),
               ("큰 데스크톱 1920x1080 dpr1", 1920, 1080, 1, False, 3),
               ("모바일 360x640 dpr2", 360, 640, 2, True, 2)]
    checks = []
    for label, vw, vh, dsf, mob, P in configs:
        ctx = new_ctx(browser, viewport={"width": vw, "height": vh}, device_scale_factor=dsf, is_mobile=mob, has_touch=mob)
        ctx.add_init_script(FILLTEXT_HOOK)
        try:
            page = open_as(ctx, col, label, "a")
            create_profile(page, "픽셀방")
            ui_create_room(page, "픽셀")
            time.sleep(0.6)
            c = page.get_by_test_id("game-canvas")
            lay = page.evaluate("""() => { const c = document.querySelector('[data-testid="game-canvas"]'); return { bufW: c.width, bufH: c.height }; }""")
            page.evaluate(HIDE_ROOM_JS)
            time.sleep(0.1)
            png = c.screenshot()
            res = pixel_check(png, P * dsf, canvas_text_boxes(page), dsf)
        finally:
            ctx.close()
        k = P * dsf
        if "error" in res:
            checks.append((f"{label}: {res['error']}", False))
            continue
        checks += [
            (f"{label}: 스크린샷 {res['size'][0]}x{res['size'][1]} = 캔버스 버퍼 {lay['bufW']}x{lay['bufH']}", tuple(res["size"]) == (lay["bufW"], lay["bufH"])),
            (f"{label}: 블록 {k}px 격자 위에서만 색 전환 (비정렬 {res['mis_x'] + res['mis_y']}건)", res["mis_x"] == 0 and res["mis_y"] == 0),
            (f"{label}: 글자/라벨 밖 블록 전부 균일 (불균일 {res['bad_outside']}/{res['blocks']})", res["bad_outside"] == 0),
            (f"{label}: 상단 35% 밴드 블록 균일 (불균일 {res['band_bad']})", res["band_bad"] == 0),
            (f"{label}: 상단 밴드 색 {res['band_colors']}가지 (팔레트 {PALETTE_COLORS}색 이내)", res["band_colors"] <= PALETTE_COLORS),
        ]
    return verdict(checks)


@case(23, "에셋 로드: 4xx/5xx 0건, 요청 실패 0, manifest 2종 + outline 200, 아바타 레이어 43, 맵 5, PNG 고유 48")
def t23(browser, col):
    ctx = new_ctx(browser)
    page = ctx.new_page()
    col.attach(page, "AS")
    ev = {"resp": [], "failed": [], "warn": []}
    page.on("response", lambda r: ev["resp"].append((r.status, r.url)) if "/assets/" in r.url else None)
    page.on("requestfailed", lambda r: ev["failed"].append(r.url) if "/assets/" in r.url else None)
    page.on("console", lambda m: ev["warn"].append(m.text) if m.type == "warning" else None)
    checks = []
    try:
        page.goto(f"{BASE}?as=ast")
        wait_until(lambda: sc(page) in ("profile", "lobby", "room"), 10)
        create_profile(page, "에셋방")
        ui_create_room(page, "에셋")
        time.sleep(1.0)
        st = state(page)
        bad = [(s, u) for s, u in ev["resp"] if s >= 400]
        png_ok = {u for s, u in ev["resp"] if s == 200 and u.endswith(".png")}
        checks.append((f"assets 응답 4xx/5xx 0건 (전체 {len(ev['resp'])}건, 실패 {bad[:3]})", not bad))
        checks.append((f"assets 요청 실패 0건 (실제 {len(ev['failed'])})", not ev["failed"]))
        for m in ("avatar/manifest.json", "avatar/outline.json", "map/manifest.json"):
            checks.append((f"{m} 200 응답", any(s == 200 and u.endswith(m) for s, u in ev["resp"])))
        a = st.get("assets") or {}
        checks.append((f"아바타 로드: source=manifest, 레이어 43 (실제 {a.get('source')}, {a.get('images')}/{a.get('imageTotal')})",
                       a.get("source") == "manifest" and a.get("images") == 43 and a.get("imageTotal") == 43))
        checks.append((f"맵 로드: mapLayers=5, background=True (실제 {a.get('mapLayers')}, {a.get('background')})",
                       a.get("mapLayers") == 5 and a.get("background") is True))
        checks.append((f"PNG 고유 200 응답 {len(png_ok)}건 (기대 48)", len(png_ok) == 48))
        checks.append((f"콘솔 경고 0건 (실제 {len(ev['warn'])}: {ev['warn'][:2]})", not ev["warn"]))
    finally:
        ctx.close()
    return verdict(checks)


def repo_tree(base):
    out = {}
    for sub in ("avatar", "map"):
        d = base / "assets" / sub
        if not d.is_dir():
            continue
        for p in sorted(d.rglob("*")):
            if p.is_file():
                out[str(p.relative_to(base))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def copy_repo(name):
    dst = SCRATCH / "qa4-copies" / name
    if dst.exists():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    return dst


@case(24, "에셋 빌드 재현성: 저장소 사본(산출물 삭제 후)에서 build.py -> avatar/map 바이트 동일 (2회 결정성)")
def t24(browser, col):
    before = repo_tree(ROOT)
    checks = []
    png_repo = sorted(k for k in before if k.endswith(".png"))
    checks.append((f"원본 PNG 개수 = 48 (실제 {len(png_repo)})", len(png_repo) == 48))

    def build_copy(name):
        dst = copy_repo(name)
        for sub in ("avatar", "map"):
            shutil.rmtree(dst / "assets" / sub)
        p = subprocess.run([sys.executable, "-B", str(dst / "assets" / "_src" / "block" / "build.py")],
                           cwd=dst, capture_output=True, text=True, timeout=300)
        return dst, p

    d1, p1 = build_copy("build-1")
    last1 = (p1.stdout.strip().splitlines() or [p1.stderr.strip()[-160:]])[-1]
    checks.append((f"build.py 종료 코드 0 ('{last1}')", p1.returncode == 0))
    t1 = repo_tree(d1)
    checks.append((f"생성 파일 집합 = 원본 ({len(t1)}개)", set(t1) == set(before)))
    diff = [k for k in before if t1.get(k) != before[k]]
    checks.append((f"avatar/map 전체 바이트 동일 {len(before) - len(diff)}/{len(before)} (불일치 {diff[:4]})", not diff))
    d2, p2 = build_copy("build-2")
    t2 = repo_tree(d2)
    checks.append(("두 번째 독립 빌드도 첫 번째와 바이트 동일", p2.returncode == 0 and t2 == t1))
    after = repo_tree(ROOT)
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    checks.append((f"저장소 원본 assets 전후 해시 동일 (변경 {len(changed)}건)", not changed))
    return verdict(checks)


@case(25, "정적 검사 스크립트: assets/_src/block/check.py 통과 (저장소 사본에서 실행)")
def t25(browser, col):
    dst = copy_repo("check")
    p = subprocess.run([sys.executable, "-B", str(dst / "assets" / "_src" / "block" / "check.py")],
                       cwd=dst, capture_output=True, text=True, timeout=300)
    tail = " / ".join(p.stdout.strip().splitlines()[-3:]) or p.stderr.strip()[-200:]
    checks = [
        (f"check.py 종료 코드 0 (출력 끝: {tail})", p.returncode == 0),
        ("출력에 'ALL CHECKS PASSED'", "ALL CHECKS PASSED" in p.stdout),
    ]
    return verdict(checks)


@case(26, "꾸미기 화면(1280x800): 탭 7개, 슬롯 반영, 프리셋 6종, 앞/옆/뒤, 걷기, 탭/슬롯 키보드")
def t26(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        page = open_as(ctx, col, "C", "c")
        wait_screen(page, "profile")
        checks.append(("프로필 매니페스트 로드 (ready)", wait_until(lambda: state(page)["create"].get("ready") is True, 8) is not None))
        cs = state(page)["create"]
        checks.append((f"초기 값 = manifest 첫 항목 7키", cs.get("avatar") == DEFAULTS))
        tabs = page.eval_on_selector_all("[role=tab]", "els => els.map(e => e.getAttribute('data-testid'))")
        checks.append((f"카테고리 탭 7개", sorted(tabs) == sorted(f"tab-{p}" for p in CATEGORY_TABS)))
        for p in CATEGORY_TABS:
            page.get_by_test_id(f"tab-{p}").click()
            sel = page.get_by_test_id(f"tab-{p}").get_attribute("aria-selected")
            n = page.eval_on_selector_all("#slot-grid .bk-slot", "els => els.length")
            checks.append((f"탭 {p}: 선택 표시 + 슬롯 {n}개 = manifest {len(PARTS[p])}", sel == "true" and n == len(PARTS[p])))
        for p, v in PICK.items():
            pick_slot(page, p, v)
        got = state(page)["create"]["avatar"]
        checks.append(("슬롯 선택 7파츠가 미리보기 상태에 반영", got == PICK))
        for i, pr in enumerate(MANIFEST["presets"]):
            page.get_by_test_id(f"preset-{i}").click()
            got = state(page)["create"]["avatar"]
            checks.append((f"프리셋 {i} '{pr['label']}' 적용 (7파츠 일치)", got == pr["avatar"]))
        checks.append(("프리셋 6종", len(MANIFEST["presets"]) == 6 and page.get_by_test_id("preset-6").count() == 0))
        page.get_by_test_id("view-side").click()
        cs = state(page)["create"]
        checks.append(("옆: view=side, frame=1, 걷기 꺼짐", cs.get("view") == "side" and cs.get("frame") == 1 and cs.get("walking") is False))
        page.get_by_test_id("view-back").click()
        cs = state(page)["create"]
        checks.append(("뒤: view=back, frame=6", cs.get("view") == "back" and cs.get("frame") == 6))
        page.get_by_test_id("view-front").click()
        cs = state(page)["create"]
        checks.append(("앞: view=front, frame=0", cs.get("view") == "front" and cs.get("frame") == 0))
        page.get_by_test_id("preview-walk").click()
        time.sleep(0.05)
        frames = set()
        t0 = time.time()
        while time.time() - t0 < 1.2:
            frames.add(state(page)["create"].get("frame"))
            time.sleep(0.03)
        checks.append((f"걷기 프레임 {sorted(f for f in frames if f is not None)} = 2..5 순환", frames - {None} <= WALK_FRAMES and len(frames - {None}) >= 3))
        page.get_by_test_id("view-front").click()
        checks.append(("앞 누르면 걷기 꺼짐", state(page)["create"].get("walking") is False))
        page.get_by_test_id("tab-skin").click()
        page.keyboard.press("ArrowRight")
        checks.append(("탭 키보드: ArrowRight -> face", state(page)["create"].get("tab") == "face"))
        page.keyboard.press("End")
        checks.append(("탭 키보드: End -> shoes", state(page)["create"].get("tab") == "shoes"))
        page.keyboard.press("Home")
        checks.append(("탭 키보드: Home -> skin", state(page)["create"].get("tab") == "skin"))
    finally:
        ctx.close()
    return verdict(checks)


@case(27, "아바타 저장: 프로필에 정확히 7키, 기본값, 사이클 1 형식 정규화(저장값 유지), Presence 옛/깨진 값 정규화")
def t27(browser, col):
    ctx = new_ctx(browser)
    ctx.add_init_script(FILLTEXT_HOOK)
    checks = []
    err0 = None
    try:
        a = open_as(ctx, col, "K", "k")
        wait_screen(a, "profile")
        for p, v in PICK.items():
            pick_slot(a, p, v)
        a.get_by_test_id("nickname-input").fill("아바타키")
        a.get_by_test_id("create-submit").click()
        wait_screen(a, "lobby")
        lobby_ready(a)
        raw = json.loads(a.evaluate("(k) => localStorage.getItem(k)", PROFILE_KEY.format("k")))
        checks.append((f"저장 avatar = 선택값 7키 (실제 {sorted(raw['avatar'].keys())})", raw["avatar"] == PICK and sorted(raw["avatar"]) == sorted(PART_KEYS7)))
        checks.append(("getState.profile.avatar = 선택값", state(a)["profile"]["avatar"] == PICK))

        b = open_as(ctx, col, "K2", "k2")
        create_profile(b, "기본아바타")
        rawb = json.loads(b.evaluate("(k) => localStorage.getItem(k)", PROFILE_KEY.format("k2")))
        checks.append(("선택 없음 = 기본값 7키 저장", rawb["avatar"] == DEFAULTS))

        # 사이클 1 형식 저장값 -> 로비/방에서 정규화, 저장값은 덮어쓰지 않음
        a.evaluate("""([k, av]) => { const o = JSON.parse(localStorage.getItem(k)); o.avatar = av; localStorage.setItem(k, JSON.stringify(o)); }""",
                   [PROFILE_KEY.format("k"), LEGACY_ROW])
        a.reload()
        wait_screen(a, "lobby")
        lobby_ready(a)
        checks.append((f"구 형식 저장값 -> 7키 정규화 (실제 {state(a)['profile']['avatar']})", state(a)["profile"]["avatar"] == LEGACY_EXPECT))
        stored = json.loads(a.evaluate("(k) => localStorage.getItem(k)", PROFILE_KEY.format("k")))["avatar"]
        checks.append(("구 형식 저장값은 읽기만 하고 덮어쓰지 않음", stored == LEGACY_ROW))

        rid = ui_create_room(a, "아바타방")
        legacy = {"skin": "skin-tan", "hair": "hair-spiky-chestnut", "eyes": "eyes-sleepy", "top": "top-vest-green", "bottom": "bottom-jeans-blue"}
        exp_old = {"skin": "medium", "hair": "brown-short", "face": "sleepy", "top": "overalls-green",
                   "bottom": "jeans-blue", "shoes": "sneakers-white", "hat": "none"}
        a.evaluate("""([rid, av]) => { const bc = new BroadcastChannel('mushroom:room:' + rid);
          bc.postMessage({ type: 'presence-join', state: { user_id: 'legacy-cli-0001', nickname: '옛클라', avatar: av, x: 900, y: 440 } });
          bc.close(); }""", [rid, legacy])
        old = wait_until(lambda: find_player(a, "옛클라"), 4)
        checks.append((f"Presence 옛 5키 -> 7키 정규화 (실제 {old and old['avatar']})", bool(old) and old["avatar"] == exp_old))
        a.evaluate("""([rid, av]) => { const bc = new BroadcastChannel('mushroom:room:' + rid);
          bc.postMessage({ type: 'presence-join', state: { user_id: 'broken-cli-0002', nickname: '깨진클라', avatar: av, x: 900, y: 440 } });
          bc.close(); }""", [rid, {"skin": "x" * 40, "hair": 7}])
        broken = wait_until(lambda: find_player(a, "깨진클라"), 4)
        checks.append((f"Presence 깨진 값 -> 기본값 7키 (실제 {broken and broken['avatar']})", bool(broken) and broken["avatar"] == DEFAULTS))
    finally:
        ctx.close()
    return verdict(checks)


@case(28, "애니메이션: 이동 중 walk(frame 2..5), 정지 후 idle(frame 1), 왼쪽 dir=left (로컬과 원격)")
def t28(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        a = open_as(ctx, col, "A", "a")
        create_profile(a, "애니A")
        ui_create_room(a, "애니방")
        b = open_as(ctx, col, "B", "b")
        create_profile(b, "애니B")
        enter_from_lobby(b, "애니방")
        wait_until(lambda: find_player(b, "애니A") and find_player(a, "애니B"), 6)
        time.sleep(0.6)
        me_a = state(a)["me"]
        checks.append((f"정지: 로컬 idle, frame 1 (실제 {me_a['anim']}, {me_a['frame']})", me_a["anim"] == "idle" and me_a["frame"] == 1))
        rp = find_player(b, "애니A")
        checks.append((f"정지: 원격 idle, frame 1 (실제 {rp and rp['anim']}, {rp and rp['frame']})", rp is not None and rp["anim"] == "idle" and rp["frame"] == 1))

        def sample(key, secs):
            loc, rem = [], []
            a.keyboard.down(key)
            t0 = time.time()
            while time.time() - t0 < secs:
                t = time.time() - t0
                m = state(a)["me"]
                loc.append((t, m["anim"], m["frame"], m["dir"]))
                p = find_player(b, "애니A")
                if p is not None:
                    rem.append((t, p["anim"], p["frame"], p["dir"]))
                time.sleep(0.03)
            a.keyboard.up(key)
            return loc, rem

        def share(samples, idx, pred, t_min):
            late = [s for s in samples if s[0] >= t_min]
            return (sum(1 for s in late if pred(s[idx])) / len(late)) if late else 0.0

        loc, rem = sample("ArrowRight", 0.9)
        lf = share(loc, 1, lambda v: v == "walk", 0.15)
        rf = share(rem, 1, lambda v: v == "walk", 0.3)
        wf_l = {s[2] for s in loc if s[1] == "walk" and s[0] >= 0.15}
        wf_r = {s[2] for s in rem if s[1] == "walk" and s[0] >= 0.3}
        checks.append((f"오른쪽 이동: 로컬 walk 비율 {lf:.2f} (기준 0.95)", lf >= 0.95))
        checks.append((f"오른쪽 이동: 로컬 walk 프레임 {sorted(wf_l)} = 2..5 이하, dir 오른쪽", wf_l <= WALK_FRAMES and share(loc, 3, lambda v: v == "right", 0.15) == 1.0))
        checks.append((f"오른쪽 이동: 원격 walk 비율 {rf:.2f} (기준 0.85)", rf >= 0.85))
        checks.append((f"오른쪽 이동: 원격 walk 프레임 {sorted(wf_r)} = 2..5 이하", wf_r <= WALK_FRAMES and wf_r != set()))
        time.sleep(0.6)
        me_a = state(a)["me"]
        rp = find_player(b, "애니A")
        checks.append(("정지 후 로컬 idle frame 1", me_a["anim"] == "idle" and me_a["frame"] == 1))
        checks.append(("정지 후 원격 idle frame 1", rp is not None and rp["anim"] == "idle" and rp["frame"] == 1))
        loc, rem = sample("ArrowLeft", 0.6)
        checks.append((f"왼쪽 이동: 로컬 dir=left 비율 {share(loc, 3, lambda v: v == 'left', 0.15):.2f} (기준 1.0)",
                       share(loc, 3, lambda v: v == "left", 0.15) == 1.0))
        rl = share(rem, 3, lambda v: v == "left", 0.3)
        checks.append((f"왼쪽 이동: 원격 dir=left 비율 {rl:.2f} (기준 0.85)", rl >= 0.85))
    finally:
        ctx.close()
    return verdict(checks)


@case(29, "콘솔 에러 0건 (전체 테스트 동안 수집, main에서 집계)")
def t29(browser, col):
    return None  # main에서 채운다


# ---------------------------------------------------------------------------
# 정적 점검 (파일 읽기, 브라우저 없음)
# ---------------------------------------------------------------------------
def static_migration():
    import re

    sql = (ROOT / "supabase/migrations/20261015000000_rooms.sql").read_text(encoding="utf-8")
    low = sql.lower()
    checks = []
    tables = ["rooms", "room_members", "room_messages", "room_join_failures"]

    grants_bad = []
    for t in tables:
        for m in re.finditer(r"grant\s+[^;]*\bon\s+(table\s+)?public\.%s\b[^;]*;" % t, low):
            if re.search(r"to\s+[^;]*\b(anon|authenticated)\b", m.group(0)):
                grants_bad.append(m.group(0).strip()[:80])
    checks.append((f"테이블 직접 권한 없음: anon/authenticated에 grant 0건 (실제 {grants_bad})", not grants_bad))
    rev_ok = all(re.search(r"revoke\s+all\s+on\s+table\s+public\.%s\s+from\s+public,\s*anon,\s*authenticated" % t, low) for t in tables)
    checks.append(("4개 테이블 revoke all from public, anon, authenticated", rev_ok))
    restrictive = len(re.findall(r"as restrictive for all to anon, authenticated using \(false\)", low))
    checks.append((f"테이블별 restrictive deny 정책 {restrictive}개 (기대 4)", restrictive == 4))
    rls_ok = all(re.search(r"alter\s+table\s+public\.%s\s+enable\s+row\s+level\s+security" % t, low) for t in tables)
    checks.append(("4개 테이블 RLS enable", rls_ok))

    # password_hash 노출 경로: 반환 타입(returns table / returns jsonb / returns text)에 없어야 한다
    funcs = re.findall(r"create or replace function (public|app_private)\.(\w+)\((.*?)\)\s*returns\s+(.*?)\s+language.*?\$\$;",
                       low, flags=re.S)
    leak = [f"{s}.{n}" for s, n, _, ret in funcs if "password_hash" in ret]
    checks.append((f"password_hash가 반환 타입에 없음 (함수 {len(funcs)}개 검사, 노출 {leak})", not leak))
    body_sel = re.findall(r"return\s+query[^;]*password_hash[^;]*;", low)
    checks.append((f"return query 안에 password_hash 없음 (실제 {len(body_sel)}건)", not body_sel))
    jsonb_leak = re.findall(r"jsonb_build_object\([^;]*password_hash", low)
    checks.append((f"send_message 등 jsonb 응답에 password_hash 없음 (실제 {len(jsonb_leak)}건)", not jsonb_leak))
    # 참조 줄은 허용 목록(테이블 정의, 제약, 주석, create_room 저장, join_room 내부 검사)과 대조한다.
    allow = [r"password_hash\s+text", r"constraint rooms_password_hash_format", r"password_hash is (not )?null",
             r"comment on column public\.rooms\.password_hash", r"^\s*--", r"insert into public\.rooms \(name, password_hash",
             r"extensions\.crypt\(p_password, v_room\.password_hash\)", r"v_room\.password_hash is not null"]
    refs = [m.group(0).strip() for m in re.finditer(r"[^\n]*password_hash[^\n]*", low)]
    stray = [r for r in refs if not any(re.search(p, r) for p in allow)]
    checks.append((f"password_hash 참조 {len(refs)}줄 중 허용 목록 밖 {len(stray)}줄 (기대 0)", not stray))

    # 모든 public 함수: security definer + search_path = '' (RPC)
    block_iter = re.finditer(r"create or replace function public\.(\w+)\((.*?)\$\$;", low, flags=re.S)
    no_definer, no_path = [], []
    names = []
    for m in block_iter:
        name, body = m.group(1), m.group(0)
        names.append(name)
        if "security definer" not in body:
            no_definer.append(name)
        if "set search_path = ''" not in body:
            no_path.append(name)
    checks.append((f"public 함수 {len(names)}개 = {sorted(names)}", len(names) == 7))
    checks.append((f"모든 public 함수 security definer ({'누락 ' + str(no_definer) if no_definer else '전부'})", not no_definer))
    checks.append((f"모든 public 함수 set search_path = '' ({'누락 ' + str(no_path) if no_path else '전부'})", not no_path))
    # 권한 문장은 공백이 여러 칸일 수 있다 (정렬된 SQL)
    anon_rev = all(re.search(r"revoke\s+all\s+on\s+function\s+public\.%s\([^)]*\)\s+from\s+public,\s*anon;" % n, low) for n in names)
    auth_grant = all(re.search(r"grant\s+execute\s+on\s+function\s+public\.%s\([^)]*\)\s+to\s+authenticated;" % n, low) for n in names)
    checks.append(("모든 public 함수 anon 실행 회수(revoke from public, anon)", anon_rev))
    checks.append(("모든 public 함수 authenticated만 실행 허용", auth_grant))
    helpers_ok = all(re.search(r"revoke\s+all\s+on\s+function\s+app_private\.%s\([^)]*\)\s+from\s+public,\s*anon,\s*authenticated;" % h, low)
                     for h in ("trim_ws", "require_uid", "room_alive", "is_member"))
    checks.append(("app_private 헬퍼: anon/authenticated 직접 실행 회수", helpers_ok))

    # realtime.messages: 멤버 한정
    rt_recv = re.search(r"create policy mushroom_room_members_receive\s+on realtime\.messages\s+for select\s+to authenticated\s+using \((.*?)\);", low, flags=re.S)
    rt_send = re.search(r"create policy mushroom_room_members_send\s+on realtime\.messages\s+for insert\s+to authenticated\s+with check \((.*?)\);", low, flags=re.S)
    checks.append(("realtime 수신 정책 존재, authenticated 한정", rt_recv is not None))
    checks.append(("realtime 송신 정책 존재, authenticated 한정", rt_send is not None))
    member_only = bool(rt_recv and rt_send and all("can_access_room_topic" in x.group(1) for x in (rt_recv, rt_send)))
    checks.append(("realtime 정책 모두 can_access_room_topic(멤버 행 확인)만 사용", member_only))
    checks.append(("realtime 정책에 using (true) 없음", "using (true)" not in low and "with check (true)" not in low))
    topic_ok = "room:[0-9a-f]{8}" in low and "is_member" in low
    checks.append(("topic 형식 검사(room:<uuid>) 후 is_member 판정", topic_ok))
    checks.append(("map:village 정책 살아 있음 없음 (이전 정책은 주석 처리)",
                   not re.search(r"^create policy .*map", (ROOT / "supabase/migrations/20261014000100_realtime.sql").read_text(encoding="utf-8").lower(), flags=re.M)))
    checks.append(("클라이언트 직접 insert/update/delete 권한 없음 (RPC만)", not grants_bad and rev_ok))
    checks.append(("배포 설정 확인 (Allow public access 끄기, 익명 로그인 켜기)", None))
    checks.append(("실제 Supabase 적용 (RLS 우회 시도, realtime.send의 RLS 통과 여부)", None))
    return checks, leak, body_sel, jsonb_leak


def static_client():
    import re

    checks = []
    src = ROOT / "src/client"
    files = [p for p in src.rglob("*.js")]
    text = {p: p.read_text(encoding="utf-8") for p in files}

    def find(rx):
        out = []
        for p, t in text.items():
            for i, line in enumerate(t.splitlines(), 1):
                if re.search(rx, line) and not line.strip().startswith("//") and not line.strip().startswith("*"):
                    out.append(f"{p.relative_to(ROOT)}:{i}")
        return out

    html = find(r"\binnerHTML\b|\bouterHTML\b|insertAdjacentHTML|document\.write|\beval\s*\(|new Function\(")
    checks.append((f"innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/new Function 0건 (실제 {html[:4]})", not html))
    # 테스트 훅 DB 조작 전용 new Function은 tests/에만 있다
    secrets_hit = find(r"service_role|sk_live|sk_test|eyJ[A-Za-z0-9_-]{20,}")
    checks.append((f"비밀 값(service_role, JWT, secret key) 0건 (실제 {secrets_hit[:3]})", not secrets_hit))
    sb = text.get(src / "backend/supabase.js", "")
    checks.append(("supabase.js 채널 private:true (구독 config)", "private: true" in sb))
    send_chat = re.findall(r"send\(\{[^}]*event:\s*'chat'", sb, flags=re.S)
    checks.append((f"클라이언트가 chat 이벤트를 보내지 않음 (send 'chat' {len(send_chat)}건)", not send_chat))
    code_lines = [ln for ln in sb.splitlines() if ln.strip() and not ln.strip().startswith(("//", "*", "/*"))]
    checks.append(("supabase.js 코드(주석 제외)에 service_role 없음 (anon key만)", not any("service_role" in ln for ln in code_lines)))
    local = text.get(src / "backend/local.js", "")
    store = text.get(src / "store.js", "")
    prof_only = re.search(r"JSON\.stringify\(\{\s*nickname:\s*profile\.nickname,\s*avatar:\s*pickAvatar\(profile\.avatar\)\s*\}\)", store)
    checks.append(("프로필 저장값은 {nickname, avatar}만 (비밀번호/토큰 없음)", prof_only is not None))
    pw_store = re.search(r"setItem\([^)]*(password|pw)[^)]*\)", local, flags=re.I)
    checks.append(("local 모드: 비밀번호 평문 저장 없음 (PBKDF2 해시만)", pw_store is None and "pw_hash" in local))
    checks.append(("config.js 키 비어 있음 (커밋본은 local 모드, 실키 없음)",
                   re.search(r"SUPABASE_(URL|ANON_KEY)\s*=\s*'[^']+'", (src / "config.js").read_text(encoding="utf-8")) is None))
    return checks


# ---------------------------------------------------------------------------
# 스크린샷 (--shots): 로비 3~4개 방(공개/잠금/가득 참), 방 3명 이상 + 말풍선 + 로그
# ---------------------------------------------------------------------------
def build_scene(browser, out_dir, prefix, viewport, mobile, dsf):
    ctx = browser.new_context(viewport=viewport, is_mobile=mobile, has_touch=mobile, device_scale_factor=dsf)
    col = Collector()
    ctx.add_init_script(FILLTEXT_HOOK)
    a = open_as(ctx, col, "A", "a")
    create_profile(a, "버섯친구", pick=PICK)
    rid_pub = ui_create_room(a, "버섯 공개방")
    b = open_as(ctx, col, "B", "b")
    create_profile(b, "분홍소녀", pick={"hair": "pink-long"})
    enter_from_lobby(b, "버섯 공개방")
    c = open_as(ctx, col, "C", "c")
    create_profile(c, "버섯꼬마", pick={"hat": "mushroom-red"})
    enter_from_lobby(c, "버섯 공개방")
    adapter(a, "createRoom", {"name": "비밀 정원", "password": "garden12", "nickname": "버섯친구"})
    full = adapter(a, "createRoom", {"name": "하늘 마법 학교", "password": None, "nickname": "버섯친구"})
    inject_fakes(a, full["value"]["roomId"], 19, "ss")  # 방장 1 + 가짜 19 = 20명 (가득 참)
    d = open_as(ctx, col, "D", "d")
    create_profile(d, "하늘마법")
    lobby_ready(d)
    time.sleep(0.5)
    wait_until(lambda: len(rooms_of(d)) >= 3, 6)
    d.get_by_test_id("room-refresh").click()
    time.sleep(1.2)
    d.screenshot(path=str(out_dir / f"lobby-{prefix}.png"))
    # 방 화면
    send_chat(b, "안녕하세요! 반가워요 :)")
    send_chat(c, "같이 놀아요")
    send_chat(a, "어서 와요")
    time.sleep(0.5)
    if mobile:
        a.get_by_test_id("log-toggle").click()
    time.sleep(0.4)
    a.screenshot(path=str(out_dir / f"room-{prefix}.png"))
    ctx.close()
    return ctx


def capture(browser, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    build_scene(browser, out, "desktop", {"width": 1280, "height": 800}, False, 1)
    build_scene(browser, out, "mobile", {"width": 360, "height": 640}, True, 2)
    print(f"스크린샷 저장: {out}")
    for f in sorted(out.glob("*.png")):
        print("  ", f)


# ---------------------------------------------------------------------------
def print_result(num, title, status, detail, checks):
    print(f"[{status}] {num}. {title}  ({detail})", flush=True)
    for name, ok in checks or []:
        tag = "OK " if ok is True else ("NG " if ok is False else "UNV")
        print(f"      {tag} {name}", flush=True)


def main():
    global BASE, VERBOSE
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", metavar="DIR", help="로비/방 스크린샷만 찍는다")
    ap.add_argument("--only", metavar="N,N", help="번호만 실행")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    VERBOSE = args.verbose
    only = {int(x) for x in args.only.split(",")} if args.only else None

    port = free_port()
    BASE = f"http://127.0.0.1:{port}/"
    server = start_server(port)
    col = Collector()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                if args.shots:
                    capture(browser, Path(args.shots))
                    return 0
                for num, title, fn in CASES:
                    if num == 29 or (only and num not in only):
                        continue
                    t0 = time.time()
                    try:
                        status, detail, checks = fn(browser, col)
                    except Exception as e:  # 테스트 자체 실패는 FAIL로 기록(재현 근거 포함)
                        status = "FAIL"
                        detail = f"예외: {type(e).__name__}: {str(e).splitlines()[0] if str(e) else ''}"
                        checks = [("테스트 실행 중 예외", False)]
                        if VERBOSE:
                            detail += "\n" + traceback.format_exc()
                    RESULTS.append((num, title, status, detail, checks))
                    print_result(num, title, status, f"{time.time() - t0:.1f}s, {detail}", checks)
            finally:
                browser.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()

    if only and 29 not in only:
        pass
    else:
        errs = col.console_errors
        st29 = "PASS" if not errs else "FAIL"
        det29 = f"콘솔/페이지 에러 {len(errs)}건" + ("" if not errs else ": " + " | ".join(errs[:8]))
        RESULTS.append((29, "콘솔 에러 0건 (전체 테스트 동안 수집)", st29, det29, [(det29, not errs)]))
        print(f"[{st29}] 29. 콘솔 에러 0건 (전체 테스트 동안 수집)  ({det29})")
        if col.failed_requests:
            print(f"      참고: 실패한 요청 {len(col.failed_requests)}건 (콘솔 에러와 별개): {col.failed_requests[:3]}")

    # 정적 점검 (30, 31)
    if not only or 30 in only:
        checks30, leak, body_sel, jsonb_leak = static_migration()
        st30 = "FAIL" if any(ok is False for _, ok in checks30) else ("UNVERIFIED" if any(ok is None for _, ok in checks30) else "PASS")
        RESULTS.append((30, "정적 점검: 마이그레이션 (권한, RLS, RPC, realtime 정책)", st30, "", checks30))
        print_result(30, "정적 점검: 마이그레이션 (권한, RLS, RPC, realtime 정책)", st30, "", checks30)
    if not only or 31 in only:
        checks31 = static_client()
        st31 = "FAIL" if any(ok is False for _, ok in checks31) else ("UNVERIFIED" if any(ok is None for _, ok in checks31) else "PASS")
        RESULTS.append((31, "정적 점검: 클라이언트 (innerHTML, 비밀 값, private 채널, chat 송신)", st31, "", checks31))
        print_result(31, "정적 점검: 클라이언트 (innerHTML, 비밀 값, private 채널, chat 송신)", st31, "", checks31)

    print("\n== 요약 ==")
    for num, title, status, _, _ in sorted(RESULTS, key=lambda r: r[0]):
        print(f"{num:>4}  {status:<12} {title}")
    fails = [r for r in RESULTS if r[2] == "FAIL"]
    print(f"\nPASS {sum(r[2] == 'PASS' for r in RESULTS)} / FAIL {len(fails)} / UNVERIFIED {sum(r[2] == 'UNVERIFIED' for r in RESULTS)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
