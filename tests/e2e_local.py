#!/usr/bin/env python3
"""버섯마을 local 모드 E2E 테스트 (Python Playwright, Chromium headless). 사이클 5 계약 기준 (복셀 아트).

- 로그인 없음. 프로필(localStorage) -> 로비 -> 방 흐름. 사용자는 `?as=<이름>`으로 탭마다 나눈다
  (docs/handoff/frontend-20261015-rooms.md 4장). 같은 browser context의 페이지들은 같은 localStorage(= 같은 "서버")와
  BroadcastChannel을 공유한다.

실행:  QA_SCRATCH=<스크래치> python3 -B tests/e2e_local.py [-v] [--only 1,8] [--shots DIR]
  -v          : 실패 항목의 traceback 출력
  --only      : 번호만 실행 (쉼표 구분)
  --shots DIR : 로비/방 스크린샷(데스크톱 1280x800, 모바일 360x640)만 저장하고 종료
환경 변수:
  QA_SCRATCH  : 스크래치 디렉터리. 항목 24~25가 저장소 사본을 여기에 만든다 (없으면 시스템 임시 폴더).
  QA_FULL_BUILD=1 : 전체 결정성 재빌드(복셀 아바타 check 무옵션, 맵 build 후 md5 비교)를 함께 실행.

- 저장소 루트에서 `python3 -m http.server`를 빈 포트로 띄우고 끝나면 반드시 종료한다.
- 기본은 local 모드로 연다: LocalBrowser가 모든 new_context에 sessionStorage `mushroom.mode`='local' init script를 붙인다
  (URL 쿼리를 바꾸지 않으므로 ?as=, goto, reload, 새 탭 모두 적용). supabase 모드를 검사할 때만 force_local=False로 연다.
- 외부 네트워크 요청은 37~39번에서만 다룬다(Supabase, CDN 차단 확인). 나머지는 local 모드만 검증한다.
- 37번은 이 컨테이너처럼 supabase.co와 CDN이 차단된 환경을 전제로 한다. 차단이 아니면 그 검사는 미검증(UNVERIFIED)이다.
- 결과는 항목별 PASS / FAIL / UNVERIFIED. 확인하지 못한 검사는 UNVERIFIED (사유 기록). 실행하지 않은 것을 PASS로 내지 않는다.
- 테스트 훅: window.__mushroom.getState(), data-testid (frontend-20261015-rooms.md 4장).
- 시간 조작(방 만료, 실패 창, 20명 정원)은 localStorage DB(`mushroom.local.v4.db`)를 직접 고쳐 만든다. 각 항목에 방법을 적었다.
"""
import argparse
import base64
import hashlib
import json
import math
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.parse
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
WALK_FRAMES = {3, 4, 5, 6}  # 사이클 5: walk = [3,4,5,6]
FULL_BUILD = os.environ.get('QA_FULL_BUILD') == '1'  # 전체 결정성 재빌드(항목 24, 25): 약 12~15분, 한 번만
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


# local 강제: 앱은 sessionStorage `mushroom.mode` = 'local'이면 local 모드로 뜬다 (backend/index.js localForced).
# 모든 문서가 로드될 때 init script가 먼저 실행되므로 goto, reload, 새 탭, ?as= 진입이 모두 local이 된다.
MODE_LOCAL_JS = """
(() => {
  try { sessionStorage.setItem('mushroom.mode', 'local'); } catch (e) { /* 저장 불가: 앱이 URL/hash 스위치로만 판단 */ }
})();
"""


class LocalBrowser:
    """Playwright Browser 래퍼. new_context()가 만든 컨텍스트마다 local 강제 init script를 붙인다.
    force_local=False로 부르면 강제하지 않는다(37~39번 supabase 모드와 모드 스위치 검사용)."""

    def __init__(self, browser):
        self._b = browser

    def new_context(self, force_local=True, **kw):
        ctx = self._b.new_context(**kw)
        if force_local:
            ctx.add_init_script(MODE_LOCAL_JS)
        return ctx

    def __getattr__(self, name):
        return getattr(self._b, name)


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
        # 사이클 8 계약: { roomId, nickname, owner } (owner는 방장 여부, 방장 삭제 기능에 쓴다)
        checks.append(("sessionStorage mushroom:room = {roomId, nickname, owner} (owner = 방장 여부)", json.loads(ss) == {"roomId": rid, "nickname": "QaReA", "owner": True}))
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


# ---------------------------------------------------------------------------
# 복셀 아트(사이클 5) 그리기 검사 헬퍼: 캔버스 호출 기록 훅, 캐릭터 마스크, 텍스트 위치
# 게임 동작은 바꾸지 않는다. 그리기 호출을 기록하고, __qaNoSprite일 때만 캐릭터 프레임 그리기를 건너뛴다.
# ---------------------------------------------------------------------------
RENDER_HOOK = """
(() => {
  const isGame = (cv) => !!(cv && cv.getAttribute && cv.getAttribute('data-testid') === 'game-canvas');
  window.__qaFill = {};         // 텍스트 -> {x, y, w, align, t}: 게임 캔버스 fillText의 마지막 호출
  window.__qaSprite = null;     // 마지막 캐릭터 프레임 그리기: {dx, dy, dw, dh, smooth, quality, t} (장치 px)
  window.__qaSpriteCount = 0;
  window.__qaSmoothBad = 0;     // 스무딩이 꺼진 상태로 그린 캐릭터 프레임 수
  window.__qaNoSprite = false;  // true면 캐릭터 프레임 그리기만 건너뛴다 (마스크 측정용)
  window.__qaFirstSprite = null;
  window.__qaFirstDraw = null;  // 게임 캔버스에 처음 그린 이미지 시각 (맵 포함)
  const ft = CanvasRenderingContext2D.prototype.fillText;
  CanvasRenderingContext2D.prototype.fillText = function (text, x, y, ...rest) {
    try {
      if (isGame(this.canvas)) {
        window.__qaFill[String(text)] = { x: x, y: y, w: this.measureText(String(text)).width, align: this.textAlign, t: performance.now() };
      }
    } catch (e) { /* 기록 실패가 그리기를 막으면 안 된다 */ }
    return ft.call(this, text, x, y, ...rest);
  };
  const di = CanvasRenderingContext2D.prototype.drawImage;
  CanvasRenderingContext2D.prototype.drawImage = function (img, ...args) {
    try {
      if (isGame(this.canvas)) {
        const t = performance.now();
        if (window.__qaFirstDraw === null) window.__qaFirstDraw = t;
        // 캐릭터 프레임: drawImage(img, sx, sy, 144, 192, dx, dy, dw, dh)
        if (args.length === 8 && args[2] === 144 && args[3] === 192) {
          if (window.__qaNoSprite) return;
          window.__qaSpriteCount++;
          if (!this.imageSmoothingEnabled) window.__qaSmoothBad++;
          window.__qaSprite = { dx: args[4], dy: args[5], dw: args[6], dh: args[7], smooth: this.imageSmoothingEnabled, quality: this.imageSmoothingQuality, t: t };
          if (window.__qaFirstSprite === null) window.__qaFirstSprite = t;
        }
      }
    } catch (e) { /* 기록 실패가 그리기를 막으면 안 된다 */ }
    return di.call(this, img, ...args);
  };
})();
"""
FILLTEXT_HOOK = RENDER_HOOK  # 이전 이름 호환 (꾸미기/방 공용 훅)

HIDE_ROOM_JS = """() => {
  for (const s of ['.hud', '.hud-row2', '.room-log', '.hud-room', '.bk-count', '.chat-float', '.hint-desktop',
                   '.room-log-toggle', '.hud-banner', '[data-testid="mode-badge"]']) {
    document.querySelectorAll(s).forEach((e) => { e.style.visibility = 'hidden'; });
  }
}"""

# 사이클 5 계약 상수 (ARCHITECTURE "복셀 아트 계약", art-20261015-voxel-final.md 10절)
REQUIRED_LAYERS = ["skin", "face", "hair_front", "top", "bottom", "shoes", "hat"]  # 프런트 constants.js와 같음
AVATAR_FILES = MANIFEST.get("files") or {}
# (사이클 10) 맵 상수는 전부 맵 manifest에서 읽는다. 고정 숫자 금지 (지면 440, 폭 2400, 레이어 5 등은 맵 교체 때 깨진다).
MAP_MANIFEST = json.loads((ROOT / "assets/map/manifest.json").read_text(encoding="utf-8"))
GROUND_Y = MAP_MANIFEST["groundY"]
WORLD_W = MAP_MANIFEST["width"]
WORLD_H = MAP_MANIFEST["height"]
WORLD_BOTTOM = WORLD_H  # 세로 카메라 기준은 맵 높이(프런트 world.height). 발 위치는 아래 camY로 환산한다
MAP_LAYER_COUNT = len(MAP_MANIFEST["layers"])
MAP_SPAWN = MAP_MANIFEST.get("spawn") or {}
MOB_MANIFEST = json.loads((ROOT / "assets/mob/manifest.json").read_text(encoding="utf-8"))
FX_MANIFEST = MOB_MANIFEST.get("fx") or {}
# (사이클 10) 아바타 시트 프레임 수는 manifest에서 읽는다 (11 = 사이클 8 시트, 13 = 사이클 10 시트 + attack)
AVATAR_FRAMES = MANIFEST.get("frames") or []
AVATAR_FRAME_W = MANIFEST["frame"]["w"]
AVATAR_FRAME_H = MANIFEST["frame"]["h"]
AVATAR_SHEET_W = AVATAR_FRAME_W * len(AVATAR_FRAMES)
ANIM = MANIFEST.get("animations") or {}
# 프런트 기준 발 위치(지면선 y)는 camY로 환산한다. camY는 getState().world.camY (카메라가 맵 세로에 맞춰 움직임)
CONFIGS_ROOM = [
    ("데스크톱 1280x800 dpr1 (P2)", 1280, 800, 1, False, 2),
    ("큰 데스크톱 1920x1080 dpr1 (P3)", 1920, 1080, 1, False, 3),
    ("모바일 360x640 dpr2 (P2)", 360, 640, 2, True, 2),
]


def even(v):
    """프런트 overlay.js even(): 올림해서 짝수."""
    return math.ceil(v / 2) * 2


def fresh_text(pg, max_age_ms=400):
    """최근 프레임(max_age_ms 이내)에 게임 캔버스에 그린 텍스트 기록만 돌려준다 (라벨/말풍선 위치)."""
    return pg.evaluate("""(age) => { const now = performance.now(); const out = {};
      for (const [k, v] of Object.entries(window.__qaFill || {})) { if (now - v.t <= age) out[k] = v; }
      return out; }""", max_age_ms)


def sprite_info(pg):
    return pg.evaluate("() => window.__qaSprite")


def wait_sprite(pg, timeout=8.0):
    return wait_until(lambda: pg.evaluate("() => !!window.__qaSprite"), timeout)


WALK_SPEED = 160  # constants.js WORLD.speed (월드 단위/초)


def spread(mover, min_gap=130, max_gap=150):
    """mover를 같은 방의 가장 가까운 다른 사람과 min_gap~max_gap(월드 단위) 거리에 둔다.
    (사이클 6 수정) 스폰은 300 + 무작위(0~599)라 두 사람이 모바일 시야 밖(컬링 여유 밖)에 떨어질 수 있다.
    제품은 그 밖의 캐릭터를 그리지 않으므로 라벨/말풍선 기록이 없다. 간헐 실패(항목 35)의 원인은 테스트 쪽 랜덤 스폰이다.
    그래서 거리를 시야 안(max_gap 이하)으로 맞춘다. 필요한 만큼만 누르고(160/초), 매번 상태를 다시 읽어 보정한다."""
    goal_mid = (min_gap + max_gap) / 2
    for _ in range(12):
        st = state(mover)
        me = st["me"]
        others = [p for p in st["players"] if p["user_id"] != me["user_id"]]
        if not others:
            return False
        near = min(others, key=lambda p: abs(p["x"] - me["x"]))
        d = me["x"] - near["x"]
        if min_gap <= abs(d) <= max_gap:
            return True
        side = 1 if d >= 0 else -1  # 지금 서 있는 쪽을 유지
        delta = (near["x"] + side * goal_mid) - me["x"]
        hold_key(mover, "ArrowRight" if delta > 0 else "ArrowLeft", min(1500, max(30, abs(delta) / WALK_SPEED * 1000)))
        time.sleep(0.1)
    st = state(mover)
    me = st["me"]
    return any(min_gap <= abs(me["x"] - p["x"]) <= max_gap for p in st["players"] if p["user_id"] != me["user_id"])


def sprite_stats(with_png, without_png, sp):
    """캐릭터 마스크 = (캐릭터 있음 - 캐릭터 없음) 차이 픽셀 중 캐릭터 프레임 사각형 안.
    - 고유 색: 마스크 내부(가장자리에서 2px 안쪽)의 RGB 종류 수
    - 경계 블렌딩: 마스크 가장자리 픽셀 중 내부 팔레트에 없는 색(계단이면 0, 스무딩이면 많음)의 비율
    """
    import io
    import numpy as np
    from PIL import Image

    A = np.asarray(Image.open(io.BytesIO(with_png)).convert("RGB")).astype(int)
    Bg = np.asarray(Image.open(io.BytesIO(without_png)).convert("RGB")).astype(int)
    if A.shape != Bg.shape:
        return {"error": f"스크린샷 크기가 다름 {A.shape} / {Bg.shape}"}
    H, W, _ = A.shape
    box = np.zeros((H, W), dtype=bool)
    x0, y0 = max(0, int(sp["dx"])), max(0, int(sp["dy"]))
    x1, y1 = min(W, int(sp["dx"] + sp["dw"])), min(H, int(sp["dy"] + sp["dh"]))
    box[y0:y1, x0:x1] = True
    mask = (np.abs(A - Bg).sum(-1) > 9) & box
    res = {"mask": int(mask.sum())}
    if res["mask"] < 1500:
        return res
    inner = mask.copy()
    for _ in range(2):
        inner = inner & np.roll(inner, 1, 0) & np.roll(inner, -1, 0) & np.roll(inner, 1, 1) & np.roll(inner, -1, 1)
    border = np.argwhere(mask & ~inner)
    inner_cols = set(map(tuple, A[inner].tolist()))
    crisp = sum(1 for yy, xx in border if tuple(A[yy, xx].tolist()) in inner_cols)
    res.update(colors=len(inner_cols), border=len(border),
               blend=round(1 - crisp / max(1, len(border)), 3))
    return res


def avatar_key(url):
    """'.../assets/avatar/<layer>/<id>.png' -> (layer, id). 아바타 PNG가 아니면 None."""
    parts = urllib.parse.urlparse(url).path.split("/")
    if len(parts) >= 3 and parts[-3] == "avatar" and parts[-1].endswith(".png"):
        return (parts[-2], parts[-1][:-4])
    return None


def asset_bytes(pg):
    return pg.evaluate("""() => { const es = performance.getEntriesByType('resource').filter((e) => e.name.includes('/assets/'));
      return { bytes: es.reduce((s, e) => s + (e.transferSize || 0), 0), n: es.length,
               png: es.filter((e) => e.name.endsWith('.png')).length }; }""")


def sample_frames(pg, secs):
    seen = set()
    t0 = time.time()
    while time.time() - t0 < secs:
        f = state(pg)["create"].get("frame")
        if f is not None:
            seen.add(f)
        time.sleep(0.03)
    return seen


COMPOSITE_JS = """async (presets) => {
  const A = await import('./src/client/avatar.js');
  const S = await import('./src/client/assets.js');
  const assets = await S.loadAvatarAssets();
  const r = A.createAvatarRenderer(assets, {});
  const out = [];
  for (const av of presets) {
    const e = await r.ready(av);
    if (!e || !e.normal) { out.push(null); continue; }
    const cv = e.normal;
    const d = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data;
    let s = '';
    for (let i = 0; i < d.length; i += 0x8000) s += String.fromCharCode.apply(null, d.subarray(i, i + 0x8000));
    out.push({ w: cv.width, h: cv.height, b64: btoa(s), headTop: e.headTop });
  }
  return out;
}"""

HEADTOP_JS = """async (avatars) => {
  const A = await import('./src/client/avatar.js');
  const S = await import('./src/client/assets.js');
  const assets = await S.loadAvatarAssets();
  const r = A.createAvatarRenderer(assets, {});
  const out = [];
  for (const av of avatars) { const e = await r.ready(av); out.push(e ? e.headTop : null); }
  return out;
}"""


def diff_stats(a, b):
    """assets/_src/voxel/build.py diff_stats와 같은 식 (프리멀티 RGB 평균 절대차 /255, 알파 MAE)."""
    import numpy as np

    a = a.astype(float)
    b = b.astype(float)
    pa = a[..., :3] * a[..., 3:4] / 255
    pb = b[..., :3] * b[..., 3:4] / 255
    d = np.abs(pa - pb).mean(-1)
    w = np.maximum(a[..., 3], b[..., 3]) / 255
    return dict(mean_abs_rgb=round(float((d * w).sum() / max(w.sum(), 1)), 3),
                p95=round(float(np.percentile(d[w > 0.05], 95)), 2),
                alpha_mae=round(float(np.abs(a[..., 3] - b[..., 3]).mean()), 3))


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


@case(22, "스무딩 렌더 품질: 캐릭터 그리기마다 imageSmoothingEnabled=true(quality high), image-rendering 계단 아님, 캐릭터 영역 비어 있지 않음, 경계가 블렌딩됨(계단/블록 아님)")
def t22(browser, col):
    try:
        import numpy  # noqa: F401
        import PIL  # noqa: F401
    except ImportError as e:
        return ("UNVERIFIED", f"numpy/Pillow가 없어 픽셀 검사를 하지 못함: {e}", [("픽셀 검사 라이브러리", None)])
    checks = []
    for label, vw, vh, dsf, mob, _P in CONFIGS_ROOM:
        ctx = new_ctx(browser, viewport={"width": vw, "height": vh}, device_scale_factor=dsf, is_mobile=mob, has_touch=mob)
        ctx.add_init_script(RENDER_HOOK)
        try:
            page = open_as(ctx, col, label, "a")
            create_profile(page, "스무딩방", pick=PICK)
            ui_create_room(page, "스무딩")
            if wait_sprite(page) is None:
                raise AssertionError("캐릭터 프레임이 그려지지 않음")
            time.sleep(0.3)
            sp = sprite_info(page)
            bad = page.evaluate("() => window.__qaSmoothBad")
            rend = page.evaluate("() => getComputedStyle(document.querySelector('[data-testid=\"game-canvas\"]')).imageRendering")
            page.evaluate(HIDE_ROOM_JS)
            time.sleep(0.1)
            cv = page.get_by_test_id("game-canvas")
            with_png = cv.screenshot()
            page.evaluate("() => { window.__qaNoSprite = true; }")
            time.sleep(0.25)
            without_png = cv.screenshot()
            page.evaluate("() => { window.__qaNoSprite = false; }")
        finally:
            ctx.close()
        res = sprite_stats(with_png, without_png, sp)
        if "error" in res:
            checks.append((f"{label}: {res['error']}", False))
            continue
        checks += [
            (f"{label}: 캐릭터 그리기 전부 스무딩 켬 (스무딩 꺼진 호출 {bad}, smooth={sp['smooth']}, quality={sp['quality']})",
             bad == 0 and sp["smooth"] is True and sp["quality"] == "high"),
            (f"{label}: 캔버스 image-rendering={rend} (pixelated/crisp-edges 아님)", rend not in ("pixelated", "crisp-edges")),
            (f"{label}: 캐릭터 영역 비어 있지 않음 (마스크 픽셀 {res['mask']}, 기준 1500 이상)", res["mask"] >= 1500),
            (f"{label}: 캐릭터 고유 색 {res.get('colors')}가지 (기준 100 이상; 블록 팔레트 {PALETTE_COLORS}색 초과)",
             res.get("colors", 0) >= 100),
            (f"{label}: 경계 블렌딩 비율 {res.get('blend')} (기준 0.25 이상; 계단 아트면 0 근처)", res.get("blend", 0) >= 0.25),
        ]
    return verdict(checks)


@case(23, "에셋 로드: 4xx/5xx 0, 요청 실패 0, outline.json 요청 0, manifest 2종 200, 요청 PNG는 전부 manifest files 안, 조합에 필요한 레이어 전부 로드, 맵 5 레이어, 콘솔 경고 0")
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
        create_profile(page, "에셋방", pick=PICK)
        ui_create_room(page, "에셋")
        wait_sprite(page)
        time.sleep(0.8)
        st = state(page)
        avatar = st["profile"]["avatar"]
        bad = [(s, u) for s, u in ev["resp"] if s >= 400]
        ok_png = {avatar_key(u) for s, u in ev["resp"] if s == 200 and avatar_key(u)}
        outline = [u for _, u in ev["resp"] if "outline.json" in u]
        allowed = {(L, i) for L, ids in AVATAR_FILES.items() for i in ids}
        need = set()
        for e in MANIFEST["layerOrder"]:
            i = avatar[e["part"]]
            if i in AVATAR_FILES.get(e["layer"], []) and not (e["part"] == "hat" and i == "none"):
                need.add((e["layer"], i))
        a = st.get("assets") or {}
        checks.append((f"assets 응답 4xx/5xx 0건 (전체 {len(ev['resp'])}건, 실패 {bad[:3]})", not bad))
        checks.append((f"assets 요청 실패 0건 (실제 {len(ev['failed'])})", not ev["failed"]))
        checks.append((f"outline.json 요청 0건 (폐기 파일, 실제 {len(outline)})", not outline))
        for m in ("avatar/manifest.json", "map/manifest.json"):
            checks.append((f"{m} 200 응답", any(s == 200 and u.endswith(m) for s, u in ev["resp"])))
        checks.append((f"요청한 아바타 PNG {len(ok_png)}장 전부 manifest files 목록 안 (목록 밖 {sorted(ok_png - allowed)[:3]})",
                       ok_png <= allowed))
        checks.append((f"이 조합의 필요 레이어 {len(need)}장 전부 200 (누락 {sorted(need - ok_png)[:3]})", need <= ok_png))
        checks.append((f"아바타 로드: source=manifest, images = imageTotal ({a.get('images')}/{a.get('imageTotal')})",
                       a.get("source") == "manifest" and a.get("images") == a.get("imageTotal") and a.get("images", 0) > 0))
        checks.append((f"맵 로드: mapLayers = manifest layers {MAP_LAYER_COUNT}, background=True (실제 {a.get('mapLayers')}, {a.get('background')})",
                       a.get("mapLayers") == MAP_LAYER_COUNT and a.get("background") is True))
        checks.append((f"콘솔 경고 0건 (실제 {len(ev['warn'])}: {ev['warn'][:2]})", not ev["warn"]))
    finally:
        ctx.close()
    return verdict(checks)


def repo_tree(base):
    """assets/ 아래 모든 파일의 sha256 (원본 불변 확인용, __pycache__ 제외)."""
    out = {}
    d = base / "assets"
    if not d.is_dir():
        return out
    for p in sorted(d.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts:
            out[str(p.relative_to(base))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def copy_repo(name):
    dst = SCRATCH / "qa5-copies" / name
    if dst.exists():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    return dst


def run_py(args, cwd, timeout):
    """사본 안에서 python3 -B 로 실행한다. (원본 저장소에서는 실행하지 않는다)"""
    p = subprocess.run([sys.executable, "-B", *args], cwd=cwd, capture_output=True, text=True, timeout=timeout)
    lines = p.stdout.strip().splitlines()
    tail = " / ".join(lines[-2:]) if lines else p.stderr.strip()[-160:]
    return p, tail


@case(24, "아바타 원본 검사 (사본): 배포 시트가 manifest frames 수 x 144 x 192 인지(11 또는 13 프레임) + manifest files 합 = 디스크 PNG 수, voxel/check.py --fast는 원본 프레임 수가 배포와 같을 때만 판정(다르면 UNVERIFIED), 원본 assets 불변")
def t24(browser, col):
    before = repo_tree(ROOT)
    manifest = json.loads((ROOT / "assets/avatar/manifest.json").read_text(encoding="utf-8"))
    # 기대값: manifest files({layer: [id, ...]})가 가리키는 경로 집합. 프레임 수는 manifest frames에서 읽는다.
    listed = {f"assets/avatar/{layer}/{pid}.png" for layer, ids in manifest["files"].items() for pid in ids}
    disk = {k for k in before if k.startswith("assets/avatar/") and k.endswith(".png")}
    nf = len(manifest.get("frames") or [])
    checks = [(f"manifest files 합 {len(listed)}장 = 디스크 PNG {len(disk)}장, 같은 파일 집합 "
               f"(목록 밖 {sorted(disk - listed)[:3]}, 파일 없음 {sorted(listed - disk)[:3]})",
               len(listed) > 0 and listed == disk)]
    checks.append((f"manifest frames {nf}개 (11 또는 13), 프레임 144x192 (배포 시트 {nf * 144}x192)", nf in (11, 13)))
    # 원본 검사는 원본(build.py)이 만든 프레임 수가 배포와 같을 때만 판정한다. 다르면 아트 교체 전이므로 UNVERIFIED.
    src_text = (ROOT / "assets/_src/voxel/check.py").read_text(encoding="utf-8")
    src_13 = "len(B.FRAMES) == 13" in src_text
    src_nf = 13 if src_13 else 11
    dst = copy_repo("voxel-fast")
    p, tail = run_py([str(dst / "assets/_src/voxel/check.py"), "--fast"], dst, 900)
    run_ok = p.returncode == 0 and "결과: 통과" in p.stdout
    if nf == src_nf:
        checks.append((f"voxel/check.py --fast 통과 (배포 {nf}프레임 = 원본 {src_nf}프레임, 출력 끝: {tail})", run_ok))
    else:
        checks.append((f"voxel/check.py --fast: 배포 {nf}프레임 != 원본 {src_nf}프레임 (아트 교체 전). 실행 결과 종료 {p.returncode}, 출력 끝: {tail}. 교체 후 재실행하면 판정", None))
    if FULL_BUILD:
        dfull = copy_repo("voxel-full")
        pf, tailf = run_py([str(dfull / "assets/_src/voxel/check.py")], dfull, 2400)
        checks.append((f"전체 결정성 재빌드 voxel/check.py (무옵션, 임시 폴더 재빌드 포함) 종료 0 (출력 끝: {tailf})",
                       pf.returncode == 0 and "결과: 통과" in pf.stdout) if nf == src_nf else
                      ("전체 결정성 재빌드: 프레임 수 불일치로 생략", None))
    else:
        checks.append(("전체 결정성 재빌드 voxel/check.py (약 6분): 이번 실행은 생략, QA_FULL_BUILD=1로 한 번 실행", None))
    after = repo_tree(ROOT)
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    checks.append((f"원본 assets 전후 해시 동일 (변경 {len(changed)}건 {changed[:3]})", not changed))
    return verdict(checks)


@case(25, "맵 원본 검사 (사본): assets/_src/map_canva/check.py 통과 (사이클 10 Canva 맵: manifest 레이어 수, 파일, 발판/로프 도달, 스폰, 결정성 옵션). 맵 상수는 manifest에서 읽음")
def t25(browser, col):
    dst = copy_repo("map-check")
    p, tail = run_py([str(dst / "assets/_src/map_canva/check.py")], dst, 900)
    last = p.stdout.strip().splitlines()[-1:] or [""]
    checks = [(f"map_canva/check.py 종료 0 (출력 끝: {tail})", p.returncode == 0),
              ("마지막 줄 'OK'", last == ["OK"])]
    checks.append((f"맵 상수 manifest 기준: 레이어 {MAP_LAYER_COUNT}개, 폭 {WORLD_W}, 높이 {WORLD_H}, groundY {GROUND_Y}, 스폰 {MAP_SPAWN}", bool(MAP_LAYER_COUNT) and bool(WORLD_W)))
    if FULL_BUILD:
        map_dst = dst / "assets" / "map"
        shutil.rmtree(map_dst)
        pb, tailb = run_py([str(dst / "assets/_src/map_canva/build.py"), "--out", str(map_dst)], dst, 1800)
        same = {}
        if pb.returncode == 0:
            for f in sorted((ROOT / "assets/map").iterdir()):
                g = map_dst / f.name
                same[f.name] = g.exists() and hashlib.sha256(g.read_bytes()).hexdigest() == hashlib.sha256(f.read_bytes()).hexdigest()
        checks.append((f"맵 전체 재빌드 build.py (사본) 종료 0 (출력 끝: {tailb})", pb.returncode == 0))
        checks.append((f"맵 전체 재빌드 결과 원본과 바이트 동일 ({sum(same.values())}/{len(same)}, 다른 파일 {[k for k, v in same.items() if not v]})",
                       bool(same) and all(same.values())))
        pd, taild = run_py([str(dst / "assets/_src/map_canva/check.py"), "--determinism"], dst, 1500)
        checks.append((f"map_canva/check.py --determinism 종료 0 (출력 끝: {taild})", pd.returncode == 0))
    else:
        checks.append(("맵 전체 재빌드 md5 비교 + --determinism: 이번 실행은 생략, QA_FULL_BUILD=1로 한 번 실행", None))
    return verdict(checks)


@case(26, "꾸미기 화면(1280x800): 탭 7개, 슬롯 반영, 프리셋 6종, 앞(숨쉬기 0/1)/옆(2)/뒤(7), 걷기(3..6), 탭/슬롯 키보드")
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
        checks.append((f"옆: view=side, frame={cs.get('frame')} (기대 2), 걷기 꺼짐",
                       cs.get("view") == "side" and cs.get("frame") == 2 and cs.get("walking") is False))
        page.get_by_test_id("view-back").click()
        cs = state(page)["create"]
        checks.append((f"뒤: view=back, frame={cs.get('frame')} (기대 7)", cs.get("view") == "back" and cs.get("frame") == 7))
        page.get_by_test_id("view-front").click()
        front = sample_frames(page, 1.4)
        checks.append((f"앞: 숨쉬기 프레임 {sorted(front)} (기대 0과 1 둘 다 관측, 그 밖 없음)", front == {0, 1}))
        page.get_by_test_id("preview-walk").click()
        walk = sample_frames(page, 1.2)
        checks.append((f"걷기 프레임 {sorted(walk)} = 3..6 순환 (3종 이상, 그 밖 없음)", walk <= WALK_FRAMES and len(walk) >= 3))
        page.get_by_test_id("view-front").click()
        checks.append(("앞 누르면 걷기 꺼짐", state(page)["create"].get("walking") is False))
        page.get_by_test_id("tab-skin").click()
        page.keyboard.press("ArrowRight")
        checks.append(("탭 키보드: ArrowRight -> face", state(page)["create"].get("tab") == "face"))
        page.keyboard.press("End")
        checks.append(("탭 키보드: End -> shoes", state(page)["create"].get("tab") == "shoes"))
        page.keyboard.press("Home")
        checks.append(("탭 키보드: Home -> skin", state(page)["create"].get("tab") == "skin"))
        thumbs = page.evaluate("""() => Array.from(document.querySelectorAll('#slot-grid canvas, .bk-presets canvas')).map((c) => {
          try { const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let n = 0;
                for (let i = 3; i < d.length; i += 4) if (d[i] > 8) n++; return n; } catch (e) { return -1; } })""")
        empty = [i for i, n in enumerate(thumbs) if n <= 0]
        checks.append((f"썸네일 캔버스 {len(thumbs)}개 전부 그려짐 (불투명 픽셀 0인 것 {len(empty)}개, 색인 {empty[:4]})",
                       len(thumbs) >= 6 + 3 and not empty))
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
        # 누락 키(shoes, hat)는 manifest 각 파츠의 첫 항목(기본값)으로 채워진다. 기본값은 아트 개정 때 바뀔 수 있어 manifest에서 읽는다.
        _parts = json.loads((ROOT / "assets/avatar/manifest.json").read_text(encoding="utf-8"))["parts"]
        exp_old = {"skin": "medium", "hair": "brown-short", "face": "sleepy", "top": "overalls-green",
                   "bottom": "jeans-blue", "shoes": _parts["shoes"][0]["id"], "hat": _parts["hat"][0]["id"]}
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


@case(28, "애니메이션: 이동 중 walk(frame 3..6), 정지 후 idle(frame 2, 인게임 정지), 왼쪽 dir=left (로컬과 원격)")
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
        checks.append((f"정지: 로컬 idle, frame 2 (실제 {me_a['anim']}, {me_a['frame']})", me_a["anim"] == "idle" and me_a["frame"] == 2))
        rp = find_player(b, "애니A")
        checks.append((f"정지: 원격 idle, frame 2 (실제 {rp and rp['anim']}, {rp and rp['frame']})", rp is not None and rp["anim"] == "idle" and rp["frame"] == 2))

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
        checks.append((f"오른쪽 이동: 로컬 walk 프레임 {sorted(wf_l)} = 3..6 이하, dir 오른쪽",
                       wf_l <= WALK_FRAMES and share(loc, 3, lambda v: v == "right", 0.15) == 1.0))
        checks.append((f"오른쪽 이동: 원격 walk 비율 {rf:.2f} (기준 0.85)", rf >= 0.85))
        checks.append((f"오른쪽 이동: 원격 walk 프레임 {sorted(wf_r)} = 3..6 이하", wf_r <= WALK_FRAMES and wf_r != set()))
        time.sleep(0.6)
        me_a = state(a)["me"]
        rp = find_player(b, "애니A")
        checks.append((f"정지 후 로컬 idle frame 2 (실제 {me_a['frame']})", me_a["anim"] == "idle" and me_a["frame"] == 2))
        checks.append((f"정지 후 원격 idle frame 2 (실제 {rp and rp['frame']})", rp is not None and rp["anim"] == "idle" and rp["frame"] == 2))
        loc, rem = sample("ArrowLeft", 0.6)
        checks.append((f"왼쪽 이동: 로컬 dir=left 비율 {share(loc, 3, lambda v: v == 'left', 0.15):.2f} (기준 1.0)",
                       share(loc, 3, lambda v: v == "left", 0.15) == 1.0))
        rl = share(rem, 3, lambda v: v == "left", 0.3)
        checks.append((f"왼쪽 이동: 원격 dir=left 비율 {rl:.2f} (기준 0.85)", rl >= 0.85))
    finally:
        ctx.close()
    return verdict(checks)


# ---------------------------------------------------------------------------
# 사이클 5 신규 (복셀 아트 계약): (a) 파일 목록 대체, (b) 발 위치, (c) 프리셋 정답 근사,
# (d) 라벨/말풍선 배치, (e) 로딩 성능
# ---------------------------------------------------------------------------
@case(32, "(a) manifest files 대체 동작: files 키 없음/객체 아님/레이어 누락 -> 필수 레이어만 요청, 404 0. 깨진 PNG 1장이면 그 레이어만 빠짐 (콘솔 error 0, 경고 1회)")
def t32(browser, col):
    checks = []
    variants = [("files 키 없음", "del"), ("files가 객체가 아님", "bad"), ("files에 hat 키 누락", "partial")]
    for label, kind in variants:
        ctx = new_ctx(browser)
        ctx.add_init_script(RENDER_HOOK)
        ev = {"resp": [], "failed": [], "warn": [], "err": []}

        def handler(route, kind=kind):
            resp = route.fetch()
            body = resp.json()
            if kind == "del":
                body.pop("files", None)
            elif kind == "bad":
                body["files"] = "깨짐"
            else:
                body.get("files", {}).pop("hat", None)
            route.fulfill(response=resp, body=json.dumps(body, ensure_ascii=False), headers={"content-type": "application/json"})

        ctx.route("**/assets/avatar/manifest.json", handler)
        page = ctx.new_page()
        page.on("response", lambda r: ev["resp"].append((r.status, r.url)) if "/assets/" in r.url else None)
        page.on("requestfailed", lambda r: ev["failed"].append(r.url) if "/assets/" in r.url else None)

        def on_console(m, ev=ev):
            if m.type == "warning":
                ev["warn"].append(m.text)
            elif m.type == "error":
                ev["err"].append(m.text)

        page.on("console", on_console)
        try:
            page.goto(f"{BASE}?as=fb")
            wait_until(lambda: sc(page) in ("profile", "lobby", "room"), 10)
            create_profile(page, "폴백방", pick=PICK)
            ui_create_room(page, "폴백")
            wait_sprite(page)
            time.sleep(0.6)
            st = state(page)
            bad = [(s, u) for s, u in ev["resp"] if s >= 400]
            req = {avatar_key(u) for s, u in ev["resp"] if s == 200 and avatar_key(u)}
            layers = {L for L, _ in req}
            exp = set()
            for L in REQUIRED_LAYERS:
                part = next(e["part"] for e in MANIFEST["layerOrder"] if e["layer"] == L)
                i = PICK[part]
                if not (part == "hat" and i == "none"):
                    exp.add((L, i))
            warn_files = [w for w in ev["warn"] if "manifest files" in w]
            checks.append((f"[{label}] 아바타 로드 source=manifest (실제 {st['assets'].get('source')})", st["assets"].get("source") == "manifest"))
            checks.append((f"[{label}] 4xx/5xx 0건 (실제 {len(bad)}: {bad[:2]})", not bad))
            checks.append((f"[{label}] 요청 실패 0건 (실제 {len(ev['failed'])})", not ev["failed"]))
            checks.append((f"[{label}] 요청 레이어가 필수 목록 안 (밖 {sorted(layers - set(REQUIRED_LAYERS))})", layers <= set(REQUIRED_LAYERS)))
            checks.append((f"[{label}] 그림자/뒷 레이어(shade_*, *_back) 요청 없음 (실제 {sorted(layers & {'shade_top', 'shade_hair', 'shade_hat', 'hair_back', 'top_back', 'hat_back'})})",
                           not (layers & {"shade_top", "shade_hair", "shade_hat", "hair_back", "top_back", "hat_back"})))
            checks.append((f"[{label}] 이 조합의 필수 레이어 {len(exp)}장 전부 200 (누락 {sorted(exp - req)[:3]})", exp <= req))
            checks.append((f"[{label}] 캐릭터 그리기 발생 (__qaSpriteCount {page.evaluate('() => window.__qaSpriteCount')}) 그리고 콘솔 error 0",
                           page.evaluate("() => window.__qaSpriteCount") > 0 and not ev["err"]))
            checks.append((f"[{label}] 대체 경고 1회 (실제 {len(warn_files)})", len(warn_files) == 1))
        finally:
            ctx.close()
    # 깨진 PNG 1장: manifest는 정상. hair_front/pink-long.png 한 장만 손상 -> 그 레이어만 빠지고 콘솔 error 0, 경고 1회
    ctx = new_ctx(browser)
    ctx.add_init_script(RENDER_HOOK)
    ctx.route("**/assets/avatar/hair_front/pink-long.png",
              lambda r: r.fulfill(status=200, body=b"not-a-png", headers={"content-type": "image/png"}))
    ev = {"resp": [], "failed": [], "warn": [], "err": []}
    page = ctx.new_page()
    col.attach(page, "BROKEN")
    page.on("response", lambda r: ev["resp"].append((r.status, r.url)) if "/assets/" in r.url else None)
    page.on("requestfailed", lambda r: ev["failed"].append(r.url) if "/assets/" in r.url else None)

    def on_console_b(m):
        if m.type == "warning":
            ev["warn"].append(m.text)
        elif m.type == "error":
            ev["err"].append(m.text)

    page.on("console", on_console_b)
    try:
        page.goto(f"{BASE}?as=brk")
        wait_until(lambda: sc(page) in ("profile", "lobby", "room"), 10)
        create_profile(page, "깨짐방", pick=PICK)
        ui_create_room(page, "깨짐")
        wait_sprite(page)
        time.sleep(0.6)
        bad = [(st_, u) for st_, u in ev["resp"] if st_ >= 400]
        broken_warn = [w for w in ev["warn"] if "hair_front/pink-long.png" in w]
        checks += [
            (f"[깨진 PNG 1장] 캐릭터 그리기 발생 (__qaSpriteCount {page.evaluate('() => window.__qaSpriteCount')}), 나머지 레이어로 합성",
             page.evaluate("() => window.__qaSpriteCount") > 0),
            (f"[깨진 PNG 1장] 4xx/5xx 0건, 요청 실패 0건 (실제 {len(bad)} / {len(ev['failed'])})", not bad and not ev["failed"]),
            (f"[깨진 PNG 1장] 콘솔 error 0건 (실제 {len(ev['err'])}: {ev['err'][:2]})", not ev["err"]),
            (f"[깨진 PNG 1장] 경고 1회: 파츠 시트 불러오기 실패 hair_front/pink-long (실제 {len(broken_warn)})", len(broken_warn) == 1),
        ]
    finally:
        ctx.close()
    return verdict(checks)


@case(33, "(b) 발 위치: 기준점(발 중앙)이 지면선 y=440에 놓이고, 발 아래 1~8단위는 잔디, 앞 가장자리는 8단위 이후, 흙/돌은 22단위 이후 (getState + 장치 좌표 + 화면 픽셀)")
def t33(browser, col):
    import io
    import numpy as np
    from PIL import Image

    checks = []
    for label, vw, vh, dsf, mob, _P in CONFIGS_ROOM:
        ctx = new_ctx(browser, viewport={"width": vw, "height": vh}, device_scale_factor=dsf, is_mobile=mob, has_touch=mob)
        ctx.add_init_script(RENDER_HOOK)
        try:
            page = open_as(ctx, col, label, "a")
            create_profile(page, "발위치", pick=PICK)
            ui_create_room(page, "발")
            wait_sprite(page)
            time.sleep(0.3)
            st = state(page)
            me = st["me"]
            lay = st["assets"]["layout"]
            sp = sprite_info(page)
            page.evaluate(HIDE_ROOM_JS)
            time.sleep(0.1)
            png = page.get_by_test_id("game-canvas").screenshot()
            # 왼쪽으로 조금 이동 -> 반전 시트. 기준점 x는 같은 규칙(round((x - camX) x k))을 따라야 한다.
            x_pre, sp_pre, dir_pre = me["x"], sp, me["dir"]
            hold_key(page, "ArrowLeft", 350)
            time.sleep(0.4)
            st2 = state(page)
            x_flip, sp_flip, dir_flip = st2["me"]["x"], sprite_info(page), st2["me"]["dir"]
        finally:
            ctx.close()
        P, dpr = lay["P"], dsf
        k = (P / 2) * dpr  # 장치 px / 월드
        s = k / 1.5  # 장치 px / 시트 px (밀도 1.5)
        # 지면선 장치 y = (지면 월드 y - camY) x k (camY = 프런트 카메라 위 끝, getState().world.camY). 맵 세로 크기와 무관하다.
        cam_y = st["world"]["camY"]
        if cam_y is None:
            raise AssertionError("world.camY가 없음 (카메라 미계산)")
        fy_dev = round((GROUND_Y - cam_y) * k)  # 프런트 render(): 지면선 장치 y
        anchor_dev = sp["dy"] + 180 * s  # 프레임 기준점(시트 y 180)의 장치 y
        A = np.asarray(Image.open(io.BytesIO(png)).convert("RGB")).astype(int)
        H, W, _ = A.shape
        green = lambda px: (px[..., 1] > px[..., 0] + 8) & (px[..., 1] > px[..., 2] + 8)  # noqa: E731
        cx = sp["dx"] + 72 * s  # 기준점 x (시트 x 72)
        xs = sorted({int(round(cx + f * sp["dw"])) for f in (-0.45, -0.38, 0.38, 0.45)})
        xs = [x for x in xs if 0 <= x < W]
        # 발바닥 선 아래 행마다 녹색 비율 (xs: 발 좌우 0.38~0.45 dw, 그림자 타원 밖). 단위 = 월드(=CSS px at P2)
        frac = {}
        for d in range(1, int(60 * k) + 1):
            y = fy_dev + d
            if y >= H:
                break
            frac[d] = float(green(A[y][xs]).mean()) if xs else 0.0

        def band(w0, w1):
            ds = [d for d in frac if w0 * k <= d <= w1 * k]
            return float(np.mean([frac[d] for d in ds])) if ds else float("nan")

        edge = next((d for d in sorted(frac) if frac[d] < 0.5), None)  # 잔디 -> 흙 첫 행
        edge_w = (edge / k) if edge is not None else float("nan")
        g_grass = band(1, 8)
        g_face = band(22, 26)
        k_w = lay["viewW"]

        def anchor_expect(xw):
            # cameraFor 와 동일: camX 를 장치 px 격자에 맞춘 뒤 (x - camX) * k
            cam = min(max(xw - k_w / 2, 0), max(0, WORLD_W - k_w))
            cam = round(cam * k) / k
            return (xw - cam) * k

        def is_left(d):
            return d in (-1, "left")

        checks += [
            (f"{label}: 오른쪽 보기 기준점 x 장치 {sp_pre['dx'] + 72 * s:.1f} = 기대 {anchor_expect(x_pre)} (x {x_pre:.0f}, 허용 1px)",
             abs(sp_pre["dx"] + 72 * s - anchor_expect(x_pre)) <= 1),
            (f"{label}: 왼쪽 보기(반전) 기준점 x 장치 {sp_flip['dx'] + 72 * s:.1f} = 기대 {anchor_expect(x_flip)} (dir {dir_flip}, x {x_flip:.0f}, 허용 1px)",
             is_left(dir_flip) and not is_left(dir_pre) and abs(sp_flip["dx"] + 72 * s - anchor_expect(x_flip)) <= 1),
            (f"{label}: 상태 me.y = {me['y']} (기대 440)", me["y"] == GROUND_Y),
            (f"{label}: 기준점 장치 y {anchor_dev:.1f} = 지면선 장치 y {fy_dev} (차 {abs(anchor_dev - fy_dev):.1f}px, 허용 1px)",
             abs(anchor_dev - fy_dev) <= 1),
            (f"{label}: 발 아래 1~8단위 잔디(녹색) 비율 {g_grass:.2f} (기대 0.80 이상)", g_grass >= 0.8),
            (f"{label}: 잔디 앞 가장자리 실측 발 아래 +{edge_w:.1f}단위 (기대 8 이상: 발이 앞 가장자리 안쪽 잔디 위)",
             edge_w >= 8),
            (f"{label}: 22~26단위 아래 흙/돌 앞면 녹색 비율 {g_face:.2f} (기대 0.20 이하)", g_face <= 0.2),
        ]
    return verdict(checks)


@case(34, "(c) 프리셋 6종: 프런트 합성 시트 vs 아트 정답(assets/_src/voxel/out/truth/presetN.png) 근사 일치 (art check.py 허용치: 프리멀티 RGB 평균 <= 6.0, 알파 MAE <= 2.0)")
def t34(browser, col):
    import numpy as np
    from PIL import Image

    TOL_MEAN, TOL_ALPHA = 6.0, 2.0  # assets/_src/voxel/build.py TOL_MEAN / TOL_ALPHA
    ctx = new_ctx(browser)
    checks = []
    try:
        page = open_as(ctx, col, "C", "c")
        wait_screen(page, "profile")
        out = page.evaluate(COMPOSITE_JS, [pr["avatar"] for pr in MANIFEST["presets"]])
    finally:
        ctx.close()
    for i, (pr, res) in enumerate(zip(MANIFEST["presets"], out)):
        tag = f"preset{i + 1} {pr['label']}"
        truth_path = ROOT / "assets/_src/voxel/out/truth" / f"preset{i + 1}.png"
        if res is None or not truth_path.exists():
            checks.append((f"{tag}: 프런트 합성 또는 정답 파일 없음", False))
            continue
        fe = np.frombuffer(base64.b64decode(res["b64"]), dtype=np.uint8).reshape(res["h"], res["w"], 4)
        truth = np.asarray(Image.open(truth_path).convert("RGBA"))
        if fe.shape != truth.shape:
            checks.append((f"{tag}: 크기 다름 {fe.shape} / {truth.shape}", False))
            continue
        st = diff_stats(fe, truth)
        opaque = int((fe[..., 3] > 8).sum())
        checks.append((f"{tag}: 평균 {st['mean_abs_rgb']:.2f} (<= {TOL_MEAN}), p95 {st['p95']}, 알파 MAE {st['alpha_mae']:.2f} (<= {TOL_ALPHA}), 불투명 {opaque}px",
                       st["mean_abs_rgb"] <= TOL_MEAN and st["alpha_mae"] <= TOL_ALPHA and opaque > 1000))
        ht = res.get("headTop")
        checks.append((f"{tag}: 머리 맨 위 headTop {ht:.1f} (키 약 월드 85~106; 문서 90~105 근사)",
                       ht is not None and 85 <= ht <= 106))
    return verdict(checks)


CONFIGS_LAYOUT = CONFIGS_ROOM


@case(35, "(d) 라벨/말풍선: 라벨은 발 아래(발바닥 선 +6), 말풍선 꼬리는 머리 위(머리 맨 위 + 4, 꼬리 -4 = 8px 간격), 라벨/말풍선끼리 겹침 없음, 캔버스 안 (P2/P3/모바일)")
def t35(browser, col):
    checks = []
    for label, vw, vh, dsf, mob, _P in CONFIGS_LAYOUT:
        ctx = new_ctx(browser, viewport={"width": vw, "height": vh}, device_scale_factor=dsf, is_mobile=mob, has_touch=mob)
        ctx.add_init_script(RENDER_HOOK)
        try:
            a = open_as(ctx, col, label + " A", "a")
            create_profile(a, "라벨가", pick=PICK)
            ui_create_room(a, "라벨방")
            b = open_as(ctx, col, label + " B", "b")
            create_profile(b, "라벨나", pick={"hair": "pink-long"})
            enter_from_lobby(b, "라벨방")
            sep = spread(b, 130)
            wait_sprite(a)
            send_chat(a, "안녕하세요")
            send_chat(b, "반가워요")
            time.sleep(0.25)
            st = state(a)
            lay = st["assets"]["layout"]
            u = lay["P"] / 2  # CSS px / 월드
            fy = (GROUND_Y - st["world"]["camY"]) * u  # 발바닥 선 (CSS px) = (지면 월드 y - camY) x P/2
            rec = fresh_text(a)
            me = st["me"]
            pb = next(p for p in st["players"] if p["nickname"] == "라벨나")
            heads = a.evaluate(HEADTOP_JS, [me["avatar"], pb["avatar"]])
            rects = []
            for who, p, msg, head in (("A", me, "안녕하세요", heads[0]), ("B", pb, "반가워요", heads[1])):
                lr = rec.get(p["nickname"])
                br = rec.get(msg)
                if lr is None or br is None:
                    checks.append((f"{label} {who}: 라벨/말풍선 텍스트 기록 없음", False))
                    continue
                ltop = lr["y"] - 4  # 라벨 박스 위 = 텍스트 y - (textTop 2 + (lineH-font)/2 2)
                lw = max(24, even(math.ceil(lr["w"]) + 12))
                lrect = (lr["x"] - lw / 2, ltop, lr["x"] + lw / 2, ltop + 20)
                bx, by = br["x"] - 10, br["y"] - 8  # 말풍선 박스 = 텍스트 x - padX(10), 텍스트 y - padTop(6) - 2
                bw = min(200, max(40, even(math.ceil(br["w"]) + 20)))
                bh = 18 + 6 + 8
                ty = by + bh + 8  # 꼬리 끝 = 박스 아래 + tailH 8
                brect = (bx, by, bx + bw, by + bh)
                gap = (fy - head * u) - ty  # 머리 맨 위 ~ 꼬리 끝 (CSS px)
                exp_gap = 4 * u + 4  # HEAD.gap(4) x u + tipGap(4)
                rects += [(f"{who} 라벨", lrect), (f"{who} 말풍선", brect)]
                checks += [
                    (f"{label} {who}: 라벨 위 {ltop:.1f} = 발바닥 선 {fy:.1f}+6 (기대 {round(fy) + 6}, 허용 1px)",
                     abs(ltop - (round(fy) + 6)) <= 1.5),
                    (f"{label} {who}: 말풍선 꼬리 간격 {gap:.1f}px (머리 맨 위 {head:.1f}w, 기대 {exp_gap:.1f} +-1.5px)",
                     abs(gap - exp_gap) <= 1.5),
                    (f"{label} {who}: 말풍선 캔버스 안 (x {bx:.0f}..{bx + bw:.0f} / 폭 {lay['cssW']}, y {by:.0f} >= 0)",
                     bx >= -0.5 and bx + bw <= lay["cssW"] + 0.5 and by >= 0),
                ]
            overl = []
            for i in range(len(rects)):
                for j in range(i + 1, len(rects)):
                    (n1, r1), (n2, r2) = rects[i], rects[j]
                    if min(r1[2], r2[2]) - max(r1[0], r2[0]) > 0 and min(r1[3], r2[3]) - max(r1[1], r2[1]) > 0:
                        overl.append(f"{n1}~{n2}")
            checks.append((f"{label}: 라벨/말풍선 사이 겹침 0건 (실제 {overl or '없음'}; 발 간격 {'확보' if sep else '미확보'})", not overl and sep))
        finally:
            ctx.close()
    return verdict(checks)


@case(36, "(e) 로딩 성능: 콜드 = 새 페이지 + HTTP 캐시 끔 (열기 -> 로비 -> 방 입장 -> 첫 캐릭터 프레임), 웜 = 같은 페이지 재입장. 실패 기준: 15초 초과 또는 전송 10MB 초과")
def t36(browser, col):
    checks = []
    ctx = new_ctx(browser)  # 같은 컨텍스트 = 같은 localStorage 서버 (방/프로필 공유)
    ctx.add_init_script(RENDER_HOOK)
    try:
        h = open_as(ctx, col, "H", "h")
        create_profile(h, "성능호스트", pick=PICK)
        ui_create_room(h, "성능방")
        w = open_as(ctx, col, "W", "p")  # 프로필 준비용 페이지 (닫는다)
        create_profile(w, "성능나", pick=PICK)
        w.close()
        # 콜드: 새 페이지를 HTTP 캐시 끈 상태로 연다 (CDP Network.setCacheDisabled). 프로필은 저장돼 있다.
        p = ctx.new_page()
        col.attach(p, "P")
        cdp = ctx.new_cdp_session(p)
        cdp.send("Network.enable")
        cdp.send("Network.setCacheDisabled", {"cacheDisabled": True})
        p.goto(f"{BASE}?as=p")
        wait_until(lambda: sc(p) in ("profile", "lobby", "room"), 10)
        lobby_ready(p)
        rid = wait_row(p, "성능방")
        p.evaluate("() => { window.__qaT0 = performance.now(); }")
        row_locator(p, rid).get_by_test_id("room-enter").click()
        wait_screen(p, "room", 20)
        wait_conn(p, timeout=20)
        wait_until(lambda: p.evaluate("() => window.__qaFirstSprite") is not None, 20)
        t = p.evaluate("() => ({ t0: window.__qaT0, fs: window.__qaFirstSprite, fd: window.__qaFirstDraw })")
        cold_nav = t["fs"] / 1000  # performance.now()는 문서 시작 기준 -> 열기부터 첫 캐릭터 프레임까지
        cold_click = (t["fs"] - t["t0"]) / 1000  # 입장 클릭부터
        cold_first_draw = (t["fd"] - t["t0"]) / 1000
        cold_bytes = asset_bytes(p)
        leave_room(p)
        p.evaluate("() => { window.__qaFirstSprite = null; window.__qaT0 = performance.now(); }")
        row_locator(p, rid).get_by_test_id("room-enter").click()
        wait_screen(p, "room", 20)
        wait_conn(p, timeout=20)
        wait_until(lambda: p.evaluate("() => window.__qaFirstSprite") is not None, 20)
        t2 = p.evaluate("() => ({ t0: window.__qaT0, fs: window.__qaFirstSprite })")
        warm_click = (t2["fs"] - t2["t0"]) / 1000
        mb = cold_bytes["bytes"] / 1048576
        checks += [
            (f"콜드 열기 -> 첫 캐릭터 프레임 {cold_nav:.2f}s (열기, 로비, 입장 포함; 기준 15s 이하)", cold_nav <= 15),
            (f"콜드 입장 클릭 -> 첫 캐릭터 프레임 {cold_click:.2f}s (첫 맵/이미지 그리기 {cold_first_draw:.2f}s; 기준 15s 이하)", cold_click <= 15),
            (f"콜드 자산 전송 {mb:.2f}MB, 요청 {cold_bytes['n']}건 (PNG {cold_bytes['png']}건; 기준 10MB 이하)", cold_bytes["bytes"] <= 10 * 1048576),
            (f"웜 재입장 클릭 -> 첫 캐릭터 프레임 {warm_click:.2f}s (참고; 기준 15s 이하)", warm_click <= 15),
        ]
    finally:
        ctx.close()
    return verdict(checks)


@case(29, "콘솔 에러 0건 (전체 테스트 동안 수집, main에서 집계)")
def t29(browser, col):
    return None  # main에서 채운다


# ---------------------------------------------------------------------------
# 37~39: 실행 모드 (docs/handoff/frontend-20261027-supabase-config.md, QA 확인 항목 2)
# 37은 supabase.co와 CDN이 차단된 환경을 전제로 한다. 38과 39는 force_local=False로 연 컨텍스트에서 모드 규칙을 본다.
# ---------------------------------------------------------------------------
LOCAL_HOSTS = {"127.0.0.1", "localhost", ""}  # "" = data:/about: 등 호스트 없는 URL


def host_of(url):
    return urllib.parse.urlsplit(url).hostname or ""


def track_external(page):
    """127.0.0.1 밖으로 나가는 요청 URL 목록을 모은다 (request 이벤트, 계속 수집)."""
    seen = []

    def on_request(r):
        if host_of(r.url) not in LOCAL_HOSTS:
            seen.append(r.url)

    page.on("request", on_request)
    return seen


@case(37, "supabase 모드 기본 진입(쿼리·hash 없음): LOCAL MODE 배지 없음(supabase 모드는 배지 숨김 설계), CDN 차단 -> 로비 오류 화면과 다시 시도, pageerror 0")
def t37(browser, col):
    ctx = browser.new_context(force_local=False)
    checks = []
    page_errors = []
    failed = []  # requestfailed URL
    try:
        page = ctx.new_page()
        # 콘솔 오류는 전역 집계(29번)에 넣지 않는다: CDN 차단 때문에 생기는 리소스 오류는 기대 동작이다.
        page.on("pageerror", lambda e: page_errors.append(str(e)))
        page.on("requestfailed", lambda r: failed.append(r.url))
        page.goto(BASE)
        if wait_until(lambda: sc(page) in ("profile", "lobby", "room"), 10) is None:
            raise AssertionError(f"쿼리 없이 열기: 부트 후 화면 전환 실패 (현재 {sc(page)})")
        checks.append(("쿼리 없이 열기 -> mode = supabase", state(page)["mode"] == "supabase"))

        def badge_hidden(pg):
            """supabase 모드는 배지를 숨긴다 (main.js hidden, 설계 결정). 요소가 없거나 보이지 않으면 통과."""
            b = pg.get_by_test_id("mode-badge")
            return b.count() == 0 or not b.is_visible()

        checks.append(("프로필 화면: LOCAL MODE 배지 없음 (배지 숨김)", badge_hidden(page)))

        # 프로필을 저장해 로비까지 간다 (handoff (a) 방법). 로비는 방 목록을 CDN 없이 못 받는다.
        preset = MANIFEST["presets"][0]["avatar"]
        page.evaluate("(v) => localStorage.setItem('mushroom:profile', v)",
                      json.dumps({"nickname": "버섯이", "avatar": preset}, ensure_ascii=False))
        page.reload()
        if wait_until(lambda: sc(page) in ("lobby", "room"), 15) is None:
            raise AssertionError(f"프로필 저장 뒤 로비 전환 실패 (현재 {sc(page)})")
        checks.append(("로비: LOCAL MODE 배지 없음 (배지 숨김)", badge_hidden(page)))

        err = page.get_by_test_id("room-error")
        cdn_failed = [u for u in failed if host_of(u) in ("cdn.jsdelivr.net", "supabase.co")]
        blocked = bool(cdn_failed)
        checks.append((f"외부 요청(CDN/supabase.co) 실패 기록 = 차단 확인 (실패 {len(cdn_failed)}건)",
                       True if blocked else None))
        if blocked:
            shown = wait_until(lambda: err.count() > 0 and err.is_visible(), 20)
            checks.append(("로비 오류 화면(room-error) 표시", bool(shown)))
            retry = page.get_by_test_id("room-retry")
            checks.append(("'다시 시도' 버튼 표시(문구 일치)",
                           bool(shown) and retry.count() > 0 and retry.inner_text().strip() == "다시 시도"))
            if shown:
                retry.click()
                again = wait_until(lambda: err.count() > 0 and err.is_visible(), 10)
                checks.append(("'다시 시도' 클릭 후 오류 화면 다시 표시(차단 중), 화면 깨짐 없음", bool(again)))
        else:
            checks.append(("오류 화면/다시 시도 검사: 외부 요청이 차단되지 않은 환경이라 미검증", None))
        checks.append((f"pageerror 0건 (앱 예외, 실제 {page_errors[:2]})", len(page_errors) == 0))
    finally:
        ctx.close()
    return verdict(checks)


@case(38, "#local(또는 ?mode=local) 진입 = LOCAL MODE 배지, 외부 요청 0건, pageerror 0")
def t38(browser, col):
    checks = []
    for label, path in (("#local", "#local"), ("?mode=local", "?mode=local")):
        ctx = browser.new_context(force_local=False)
        try:
            page = ctx.new_page()
            ext = track_external(page)
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto(BASE + path)
            if wait_until(lambda: sc(page) in ("profile", "lobby", "room"), 10) is None:
                raise AssertionError(f"{label}: 부트 후 화면 전환 실패 (현재 {sc(page)})")
            checks.append((f"{label}: mode = local", state(page)["mode"] == "local"))
            b = page.get_by_test_id("mode-badge")
            checks.append((f"{label}: LOCAL MODE 배지 보임",
                           b.count() > 0 and b.is_visible() and b.inner_text().strip() == "LOCAL MODE"))
            time.sleep(1.5)  # 초기 요청이 모두 나갈 시간
            checks.append((f"{label}: 외부 요청 0건 (실제 {ext[:3]})", not ext))
            checks.append((f"{label}: pageerror 0건 (실제 {errs[:2]})", not errs))
        finally:
            ctx.close()
    return verdict(checks)


@case(39, "모드 스위치 규칙: ?mode=local 저장/유지/해제, #local 우선, #localx·#local&x 비해당, 수동 sessionStorage")
def t39(browser, col):
    checks = []

    def boot(page, path):
        page.goto(BASE + path)
        if wait_until(lambda: sc(page) in ("profile", "lobby", "room"), 10) is None:
            raise AssertionError(f"{path or '(쿼리 없음)'}: 부트 후 화면 전환 실패 (현재 {sc(page)})")
        return state(page)["mode"]

    def ss(page):
        return page.evaluate("(k) => sessionStorage.getItem(k)", "mushroom.mode")

    # 탭 A: ?mode=local -> 저장 -> 쿼리 없이 새로고침해도 local -> ?mode=supabase로 해제
    ctx = browser.new_context(force_local=False)
    try:
        a = ctx.new_page()
        checks.append(("?mode=local -> mode = local", boot(a, "?mode=local") == "local"))
        checks.append(("?mode=local -> sessionStorage mushroom.mode = 'local'", ss(a) == "local"))
        checks.append(("쿼리 없이 열기(같은 탭) -> sessionStorage로 local 유지", boot(a, "") == "local"))
        checks.append(("?mode=supabase -> mode = supabase", boot(a, "?mode=supabase") == "supabase"))
        checks.append(("?mode=supabase -> sessionStorage 삭제(null)", ss(a) is None))
    finally:
        ctx.close()

    # 탭 B: 비슷한 hash는 해당 없음, #local은 쿼리 mode=supabase보다 우선
    ctx = browser.new_context(force_local=False)
    try:
        b = ctx.new_page()
        checks.append(("#localx -> supabase (정확히 #local만 인식)", boot(b, "#localx") == "supabase"))
        b2 = ctx.new_page()
        checks.append(("#local&x -> supabase (정확히 #local만 인식)", boot(b2, "#local&x") == "supabase"))
        b3 = ctx.new_page()
        checks.append(("?mode=supabase#local -> local (hash가 우선)", boot(b3, "?mode=supabase#local") == "local"))
        checks.append(("?mode=supabase#local -> sessionStorage 삭제(null)", ss(b3) is None))
    finally:
        ctx.close()

    # 탭 C: 쿼리·hash 없이 sessionStorage만 local로 둔 경우 (init script로 주입)
    ctx = browser.new_context(force_local=False)
    try:
        ctx.add_init_script("try { sessionStorage.setItem('mushroom.mode', 'local'); } catch (e) {}")
        c = ctx.new_page()
        checks.append(("sessionStorage mushroom.mode = local (쿼리 없음) -> mode = local", boot(c, "") == "local"))
    finally:
        ctx.close()
    return verdict(checks)


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


SECRET_SKIP = {".git", "tests", "__pycache__"}  # 테스트 파일은 규칙 문자열을 담고 있으므로 제외
CONFIG_REL = "src/client/config.js"
JWT_RX = re.compile(r"eyJ[A-Za-z0-9_-]{20,}(?:\.[A-Za-z0-9_-]*){0,2}")  # JWT 흔적 (헤더 시작 eyJ)
FORBID_ANY = ("sb_secret_", "sk_live", "sk_test")  # docs 제외, 어떤 텍스트 파일에도 0건
FORBID_CODE = ("service_role",)  # 코드 파일의 비주석 줄에서만 0건 (주석과 문서 설명은 허용)
CODE_EXT = {".js", ".mjs", ".html", ".css", ".json", ".sql", ".py"}
COMMENT_PREFIX = ("//", "/*", "*", "--", "#")


def jwt_role(token):
    """JWT payload의 role. 디코드 실패 시 None (= anon이 아니므로 실패로 본다)."""
    parts = token.split(".")
    if len(parts) < 2:
        return None
    seg = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(seg)).get("role")
    except Exception:  # noqa: BLE001 - 형식이 깨진 토큰은 실패 처리
        return None


def text_files():
    """저장소 안의 텍스트 파일 (.git, tests, __pycache__ 제외, 바이너리는 건너뜀). yield (상대 경로 parts, 본문)."""
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT)
        if any(part in SECRET_SKIP for part in rel.parts):
            continue
        try:
            body = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        yield rel, body


def secret_scan():
    """비밀 점검. 반환: (secrets_hit, cfg_roles)
    - secrets_hit: 위반 목록. 빈 목록이면 통과.
        · JWT가 config.js 밖에 있음
        · config.js JWT 중 payload role이 anon이 아닌 것 (또는 디코드 실패)
        · sb_secret_ / sk_live / sk_test 문자열 (docs 제외)
        · service_role 문자열이 코드 파일의 비주석 줄에 있음
    - cfg_roles: config.js에 있는 JWT들의 role 목록 (정보용)"""
    secrets_hit = []
    cfg_roles = []
    for rel, body in text_files():
        rel_s = rel.as_posix()
        in_docs = rel.parts[0] == "docs"
        if rel_s == CONFIG_REL:
            for tok in JWT_RX.findall(body):
                role = jwt_role(tok)
                cfg_roles.append(role)
                if role != "anon":
                    secrets_hit.append(f"{rel_s} JWT role={role}")
        else:
            for _ in JWT_RX.findall(body):
                secrets_hit.append(f"{rel_s} (JWT)")
        if not in_docs:
            for w in FORBID_ANY:
                if w in body:
                    secrets_hit.append(f"{rel_s} ({w})")
        if rel.suffix in CODE_EXT:
            for i, line in enumerate(body.splitlines(), 1):
                s = line.strip()
                if s.startswith(COMMENT_PREFIX):
                    continue
                for w in FORBID_CODE:
                    if w in line:
                        secrets_hit.append(f"{rel_s}:{i} ({w})")
    return secrets_hit, cfg_roles


def static_client():
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
    secrets_hit, cfg_roles = secret_scan()
    checks.append((f"비밀 값 0건: config.js 밖 JWT, anon 아닌 JWT, sb_secret_/sk_live/sk_test, 코드의 service_role (실제 {secrets_hit[:8]})",
                   not secrets_hit))
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
    cfg_bad = [r for r in cfg_roles if r != "anon"]
    checks.append((f"config.js JWT payload role = anon 전부 (JWT {len(cfg_roles)}개, role {cfg_roles}, anon 아님 {len(cfg_bad)}개)",
                   not cfg_bad))
    return checks


# ---------------------------------------------------------------------------
# 스크린샷 (--shots): 로비 3~4개 방(공개/잠금/가득 참), 방 3명 이상 + 말풍선 + 로그
# ---------------------------------------------------------------------------
def build_scene(browser, out_dir, prefix, viewport, mobile, dsf):
    """--shots: 로비(방 4개 이상)와 방 화면(4명, 서로 다른 프리셋, 말풍선, 채팅 로그)을 찍는다."""
    ctx = browser.new_context(viewport=viewport, is_mobile=mobile, has_touch=mobile, device_scale_factor=dsf)
    col = Collector()
    ctx.add_init_script(RENDER_HOOK)
    a = open_as(ctx, col, "A", "a")
    create_profile(a, "버섯친구", pick=PICK)
    ui_create_room(a, "버섯 공개방")
    adapter(a, "createRoom", {"name": "비밀 정원", "password": "garden12", "nickname": "버섯친구"})
    full = adapter(a, "createRoom", {"name": "하늘 마법 학교", "password": None, "nickname": "버섯친구"})
    inject_fakes(a, full["value"]["roomId"], 19, "ss")  # 방장 1 + 가짜 19 = 20명 (가득 참)
    b = open_as(ctx, col, "B", "b")
    create_profile(b, "분홍소녀", pick={"hair": "pink-long", "top": "blouse-white", "bottom": "skirt-pink", "shoes": "maryjane-red"})
    enter_from_lobby(b, "버섯 공개방")
    c = open_as(ctx, col, "C", "c")
    create_profile(c, "버섯꼬마", pick={"hat": "mushroom-red", "top": "overalls-green", "bottom": "jeans-blue", "shoes": "boots-brown"})
    enter_from_lobby(c, "버섯 공개방")
    d = open_as(ctx, col, "D", "d")
    create_profile(d, "하늘마법", pick=MANIFEST["presets"][4]["avatar"])
    lobby_ready(d)
    wait_until(lambda: len(rooms_of(d)) >= 3, 6)
    d.get_by_test_id("room-refresh").click()
    time.sleep(1.2)
    d.screenshot(path=str(out_dir / f"lobby-{prefix}.png"))
    enter_from_lobby(d, "버섯 공개방")
    # 위치를 떨어뜨린다 (스폰은 300~900 무작위). 라벨이 겹치지 않도록 다른 사람과 130 이상 간격.
    for pg in (b, c, d):
        spread(pg, 130)
    send_chat(b, "안녕하세요! 반가워요 :)")
    send_chat(c, "같이 놀아요")
    send_chat(a, "어서 와요")
    send_chat(d, "여기 좋다!")
    time.sleep(0.4)
    if mobile:
        a.get_by_test_id("log-toggle").click()
    time.sleep(0.3)
    a.screenshot(path=str(out_dir / f"room-{prefix}.png"))
    ctx.close()


def profile_shot(browser, out: Path):
    """꾸미기 화면 (1280x800): 프리셋 하나를 골라 파츠 탭과 미리보기가 보이는 상태."""
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    col = Collector()
    page = open_as(ctx, col, "P", "pf")
    wait_screen(page, "profile")
    for p, v in MANIFEST["presets"][2]["avatar"].items():
        pick_slot(page, p, v)
    page.get_by_test_id("nickname-input").fill("모자소년")
    time.sleep(0.8)
    page.screenshot(path=str(out / "profile-desktop.png"))
    ctx.close()


def capture(browser, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    build_scene(browser, out, "desktop", {"width": 1280, "height": 800}, False, 1)
    build_scene(browser, out, "mobile", {"width": 360, "height": 640}, True, 2)
    profile_shot(browser, out)
    print(f"스크린샷 저장: {out}")
    for f in sorted(out.glob("*.png")):
        print("  ", f)


# ---------------------------------------------------------------------------

def print_result(num, title, status, detail, checks):
    print(f"[{status}] {num}. {title}  ({detail})", flush=True)
    for name, ok in checks or []:
        tag = "OK " if ok is True else ("NG " if ok is False else "UNV")
        print(f"      {tag} {name}", flush=True)


# ---------------------------------------------------------------------------
# 40~46: 사이클 6 (11프레임 시트, 점프·숙이기, 연결 끊김 수정). frontend handoff 7장 1~6 + 시트/manifest 검사
# ---------------------------------------------------------------------------
DEBUG_DROP_JS = """([rid, uid, fail]) => {
  const bc = new BroadcastChannel('mushroom:room:' + rid);
  bc.postMessage({ type: 'debug-drop', user_id: uid, fail: fail });
  setTimeout(() => bc.close(), 300);
}"""
# 매 프레임 상태를 기록한다 (nick이 없으면 나, 있으면 그 닉네임의 원격 캐릭터)
REC_JS = """([ms, nick]) => {
  window.__rec = [];
  window.__recDone = false;
  const t0 = performance.now();
  const step = () => {
    const st = window.__mushroom.getState();
    const p = nick ? (st.players || []).find((q) => q.nickname === nick) : st.me;
    if (p) window.__rec.push({ t: performance.now(), x: p.x, y: p.y, s: p.s, anim: p.anim, frame: p.frame });
    if (performance.now() - t0 < ms) requestAnimationFrame(step);
    else window.__recDone = true;
  };
  requestAnimationFrame(step);
}"""


def adapter_stats(pg):
    return ((state(pg).get("net") or {}).get("adapter")) or {}


def link_stats(pg):
    return ((state(pg).get("net") or {}).get("link")) or {}


def focus_canvas(pg):
    pg.evaluate("() => { const c = document.querySelector('[data-testid=game-canvas]'); if (c) c.focus({ preventScroll: true }); }")


def start_rec(pg, ms, nick=None):
    pg.evaluate(REC_JS, [ms, nick])


def rec_rows(pg):
    return pg.evaluate("() => window.__rec || []")


def wait_rec_done(pg, timeout=8.0):
    return wait_until(lambda: pg.evaluate("() => !!window.__recDone"), timeout, 0.1)


def collapse(seq):
    out = []
    for v in seq:
        if not out or out[-1] != v:
            out.append(v)
    return out


def pair_in_room(ctx, col, nick_a, nick_b, room):
    """A가 방을 만들고 B가 들어온다. 서로 보일 때까지 기다린다. 반환 (a, b, room_id)."""
    a = open_as(ctx, col, "A", "a")
    create_profile(a, nick_a)
    rid = ui_create_room(a, room)
    b = open_as(ctx, col, "B", "b")
    create_profile(b, nick_b)
    enter_from_lobby(b, room)
    wait_until(lambda: find_player(a, nick_b) is not None, 6)
    wait_until(lambda: find_player(b, nick_a) is not None, 6)
    return a, b, rid


def jump_trace(rows, key):
    """녹화 샘플 -> 최고 높이(440 - 최소 y), 체공 시간(첫 공중 샘플 ~ 첫 지상 샘플), 상태 순서, 상태별 프레임.
    key = 's'(로컬 물리 상태) 또는 'anim'(화면이 쓰는 애니메이션 이름)."""
    ys = [r["y"] for r in rows]
    seq = collapse([r[key] for r in rows])
    frames = {}
    for r in rows:
        frames.setdefault(r["anim"], set()).add(r["frame"])
    air = [i for i, r in enumerate(rows) if r["anim"] in ("jump", "fall")]
    air_s = None
    if air:
        j = min(air[-1] + 1, len(rows) - 1)
        air_s = (rows[j]["t"] - rows[air[0]]["t"]) / 1000
    return {
        "apex": round(GROUND_Y - min(ys), 1) if ys else None,
        "air_s": None if air_s is None else round(air_s, 3),
        "seq": seq,
        "frames": {k: sorted(v, key=lambda z: -1 if z is None else z) for k, v in frames.items()},
        "y_end": ys[-1] if ys else None,
    }


@case(40, "아바타 시트 (manifest 기준, 11프레임 사이클 8 또는 13프레임 사이클 10): frames 이름, 애니메이션 인덱스(jump/fall/prone 또는 crouch, attack 있으면 [11,12] 120ms), 기존 idle_front/idle/walk 유지, files 전 PNG 가 manifest 프레임 수 x 144 x 192 RGBA, 점프/낙하/엎드림/공격 프레임 비어 있지 않고 서로 다름")
def t40(browser, col):
    import numpy as np
    from PIL import Image

    checks = []
    fr = AVATAR_FRAMES
    n = len(fr)
    checks.append((f"frames 개수 {n} 은 11(사이클 8) 또는 13(사이클 10, attack 포함)", n in (11, 13)))
    pose_name = "prone" if "prone" in ANIM else "crouch"  # 프런트는 옛 crouch도 같은 의미로 받는다
    want = {"jump": [8], "fall": [9], pose_name: [10]}
    if n == 13:
        want["attack"] = [11, 12]
    for name, idx in want.items():
        e = ANIM.get(name) or {}
        ms_want = 120 if name == "attack" else 200
        checks.append((f"animations.{name} = frames {idx}, {ms_want}ms (실제 {e})", e.get("frames") == idx and e.get("ms") == ms_want))
    if n == 13:
        checks.append((f"frames 11, 12 = attack0, attack1 (실제 {fr[11:13]})", fr[11:13] == ["attack0", "attack1"]))
    got = {k: (ANIM.get(k) or {}).get("frames") for k in ("idle_front", "idle", "walk")}
    checks.append((f"기존 애니메이션 유지: idle_front [0,1], idle [2], walk [3,4,5,6] (실제 {got})",
                   got == {"idle_front": [0, 1], "idle": [2], "walk": [3, 4, 5, 6]}))
    fm = MANIFEST.get("frame") or {}
    anc = MANIFEST.get("anchor") or {}
    checks.append((f"프레임 144x192, 기준점 (72,180) 유지 (실제 {fm}, {anc})", fm == {"w": 144, "h": 192} and anc == {"x": 72, "y": 180}))
    paths = [(layer, pid) for layer, ids in (MANIFEST.get("files") or {}).items() for pid in ids]
    bad, weak, same = [], [], []
    pose_idx = [i for i in range(8, n) if fr[i] in ("jump", "fall", pose_name) or fr[i].startswith("attack")]
    for layer, pid in paths:
        p = ROOT / "assets/avatar" / layer / f"{pid}.png"
        if not p.exists():
            bad.append(f"{layer}/{pid} 없음")
            continue
        im = Image.open(p)
        if im.size != (AVATAR_SHEET_W, AVATAR_FRAME_H) or im.mode != "RGBA":
            bad.append(f"{layer}/{pid} {im.size} {im.mode}")
            continue
        arr = np.asarray(im)
        fs = []
        side = int((arr[:, 2 * AVATAR_FRAME_W:3 * AVATAR_FRAME_W, 3] > 0).sum())  # 측면 정지(프레임 2)의 알파 픽셀 수
        for idx in pose_idx:
            f = arr[:, idx * AVATAR_FRAME_W:(idx + 1) * AVATAR_FRAME_W, :]
            nn = int((f[:, :, 3] > 0).sum())
            if not layer.endswith("_back") and side > 0 and nn < 0.25 * side:
                weak.append(f"{layer}/{pid}#{idx}({nn}/{side})")
            fs.append(f)
        filled = [f for f in fs if (f[:, :, 3] > 0).any()]
        if any(np.array_equal(filled[i], filled[j]) for i in range(len(filled)) for j in range(i + 1, len(filled))):
            same.append(f"{layer}/{pid}")
    checks.append((f"files 전 PNG {len(paths)}장 모두 {AVATAR_SHEET_W}x{AVATAR_FRAME_H} RGBA (문제 {bad[:3] or '없음'})", bool(paths) and not bad))
    checks.append((f"몸 앞 레이어 포즈 프레임 {pose_idx} 알파 >= 측면 정지(2) 대비 25% (약함 {weak[:3] or '없음'})", not weak))
    checks.append((f"포즈 프레임끼리 서로 다름 (같은 파일 {same[:3] or '없음'})", not same))
    return verdict(checks)


@case(41, "Presence track 횟수 (로컬, 1280x800): 입장 시 track 1, 새 멤버 입장에 기존 멤버 track 증가 없음, 10초 이동·점프 후에도 1, move 10회/초 이하, 재연결 1회(debug-drop)마다 +1")
def t41(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        a = open_as(ctx, col, "A", "a")
        create_profile(a, "트랙41A")
        rid = ui_create_room(a, "트랙41")
        b = open_as(ctx, col, "B", "b")
        create_profile(b, "트랙41B")
        enter_from_lobby(b, "트랙41")
        wait_until(lambda: find_player(a, "트랙41B") is not None, 6)
        time.sleep(0.5)
        checks.append((f"방장 입장 후 track = 1 (실제 {adapter_stats(a).get('track')})", adapter_stats(a).get("track") == 1))
        checks.append((f"B 입장 track = 1 (실제 {adapter_stats(b).get('track')})", adapter_stats(b).get("track") == 1))
        checks.append((f"새 멤버 입장 후 A의 track 그대로 1 (실제 {adapter_stats(a).get('track')})", adapter_stats(a).get("track") == 1))
        focus_canvas(a)
        time.sleep(0.2)
        mv0 = adapter_stats(a).get("moveSent", 0)
        t0 = time.time()
        while time.time() - t0 < 10:
            hold_key(a, "ArrowRight", 300)
            a.keyboard.press("Space")
            hold_key(a, "ArrowLeft", 300)
            a.keyboard.press("KeyW")
        el = time.time() - t0
        ad = adapter_stats(a)
        n_move = ad.get("moveSent", 0) - mv0
        checks.append((f"10초 이동+점프 후 track 그대로 1 (실제 {ad.get('track')})", ad.get("track") == 1))
        checks.append((f"move 송신 {n_move}회 / {el:.1f}초 = {n_move / el:.1f}회/초 (10회/초 이하, 움직임 확인 위해 20회 이상)",
                       20 <= n_move <= 10 * el + 2))
        uid_a = state(a)["userId"]
        tr0 = adapter_stats(a).get("track")
        a.evaluate(DEBUG_DROP_JS, [rid, uid_a, 0])
        wait_until(lambda: state(a).get("connection") != "connected", 3)
        wait_conn(a, "connected", 15)
        tr1 = adapter_stats(a).get("track")
        checks.append((f"재연결 1회 후 track +1 (실제 {tr0} -> {tr1})", tr1 - tr0 == 1))
    finally:
        ctx.close()
    return verdict(checks)


@case(42, "점프 궤적 (1280x800, 로컬 + 원격 B 화면): 최고 높이 104~106, 체공 0.60~0.70초, 착지 y=440, 상태 idle→jump→fall→idle, 프레임 jump 8 / fall 9 / idle 2, 원격 최고 103~107")
def t42(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        a, b, _ = pair_in_room(ctx, col, "점프42A", "점프42B", "점프42")
        focus_canvas(a)
        time.sleep(0.4)
        m = state(a)["me"]
        checks.append((f"시작: 지면 y=440, idle (y {m['y']}, s {m['s']})", m["y"] == GROUND_Y and m["s"] == "idle"))
        start_rec(a, 2400)
        start_rec(b, 2400, "점프42A")
        time.sleep(0.2)
        a.keyboard.press("ArrowUp")
        wait_rec_done(a, 6)
        wait_rec_done(b, 6)
        la = jump_trace(rec_rows(a), "s")
        ra = jump_trace(rec_rows(b), "anim")
        checks.append((f"로컬 최고 높이 {la['apex']} (기대 104~106)", la["apex"] is not None and 104 <= la["apex"] <= 106))
        checks.append((f"로컬 체공 {la['air_s']}초 (기대 0.60~0.70)", la["air_s"] is not None and 0.60 <= la["air_s"] <= 0.70))
        checks.append((f"로컬 상태 순서 {la['seq']} (기대 idle, jump, fall, idle)", la["seq"] == ["idle", "jump", "fall", "idle"]))
        checks.append((f"로컬 착지 y {la['y_end']} (기대 440)", la["y_end"] == GROUND_Y))
        checks.append((f"로컬 프레임 jump {la['frames'].get('jump')} / fall {la['frames'].get('fall')} / idle {la['frames'].get('idle')} (기대 [8] / [9] / [2])",
                       la["frames"].get("jump") == [8] and la["frames"].get("fall") == [9] and set(la["frames"].get("idle", [2])) == {2}))
        rs = ra["seq"]
        checks.append((f"원격 최고 높이 {ra['apex']} (기대 103~107)", ra["apex"] is not None and 103 <= ra["apex"] <= 107))
        checks.append((f"원격 체공 {ra['air_s']}초 (기대 0.55~0.75)", ra["air_s"] is not None and 0.55 <= ra["air_s"] <= 0.75))
        checks.append((f"원격 상태 순서 {rs} (jump 다음 fall, walk·crouch 없음)",
                       "jump" in rs and "fall" in rs and rs.index("jump") < rs.index("fall") and "walk" not in rs and "prone" not in rs))
        checks.append((f"원격 착지 y {ra['y_end']} (기대 440)", ra["y_end"] == GROUND_Y))
        checks.append((f"원격 프레임 jump {ra['frames'].get('jump')} / fall {ra['frames'].get('fall')} (기대 [8] / [9])",
                       ra["frames"].get("jump") == [8] and ra["frames"].get("fall") == [9]))
    finally:
        ctx.close()
    return verdict(checks)


@case(43, "숙이기 (1280x800): ↓/S 누르는 동안 s=crouch·frame 10, 숙인 채 ←/→ x 불변, 숙인 채 Space 점프 없음, 해제 후 idle(frame 2), 원격 B 화면에서 A의 prone 프레임 10")
def t43(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        a, b, _ = pair_in_room(ctx, col, "숙이기43A", "숙이기43B", "숙이기43")
        focus_canvas(a)
        time.sleep(0.4)
        m0 = state(a)["me"]
        checks.append((f"시작: 지면 idle (y {m0['y']}, s {m0['s']})", m0["y"] == GROUND_Y and m0["s"] == "idle"))
        start_rec(b, 3000, "숙이기43A")
        a.keyboard.down("ArrowDown")
        time.sleep(0.25)
        m1 = state(a)["me"]
        checks.append((f"↓ 누르는 동안: s prone, frame 10 (실제 {m1['s']}, {m1['frame']})", m1["s"] == "prone" and m1["frame"] == 10))
        a.keyboard.down("ArrowRight")
        time.sleep(0.35)
        m2 = state(a)["me"]
        a.keyboard.up("ArrowRight")
        time.sleep(0.1)
        checks.append((f"숙인 채 → 키: x 불변 (x {m1['x']} -> {m2['x']}), s prone", abs(m2["x"] - m1["x"]) < 0.5 and m2["s"] == "prone"))
        a.keyboard.press("Space")
        time.sleep(0.35)
        m3 = state(a)["me"]
        checks.append((f"숙인 채 Space: 점프 없음 (y {m3['y']}, s {m3['s']})", m3["y"] == GROUND_Y and m3["s"] == "prone"))
        a.keyboard.up("ArrowDown")
        time.sleep(0.3)
        m4 = state(a)["me"]
        checks.append((f"↓ 뗌: idle 복귀, frame 2 (s {m4['s']}, frame {m4['frame']})", m4["s"] == "idle" and m4["frame"] == 2))
        wait_rec_done(b, 6)
        cf = sorted({r["frame"] for r in rec_rows(b) if r["anim"] == "prone"}, key=lambda z: -1 if z is None else z)
        checks.append((f"원격 B 화면: A의 prone 프레임 {cf} (기대 [10])", cf == [10]))
    finally:
        ctx.close()
    return verdict(checks)


@case(44, "채팅 입력 중 이동·점프·숙이기 키 9종 무시(글자만 입력), 캔버스 포커스 중 Space/↑/↓ 페이지 스크롤 없음, 로그 목록 포커스 중 → 는 캐릭터 이동 안 함, 버튼 포커스 중 Space = 버튼 동작 (1280x800)")
def t44(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        a = open_as(ctx, col, "A", "a")
        create_profile(a, "키입력44")
        ui_create_room(a, "키44")
        time.sleep(0.4)
        m0 = state(a)["me"]
        inp = a.get_by_test_id("chat-input")
        inp.click()
        keys = ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Space", "KeyA", "KeyD", "KeyW", "KeyS"]
        bad = []
        for k in keys:
            a.keyboard.down(k)
            time.sleep(0.12)
            m = state(a)["me"]
            if abs(m["x"] - m0["x"]) >= 0.5 or m["y"] != GROUND_Y or m["s"] != "idle":
                bad.append((k, m["x"], m["y"], m["s"]))
            a.keyboard.up(k)
            time.sleep(0.05)
        checks.append((f"채팅 입력 중 이동·점프·숙이기 키 9종 무시 (위반 {bad or '없음'})", not bad))
        val = inp.input_value()
        checks.append((f"글자 키만 입력됨 (값 {val!r}, 기대 ' adws')", val == " adws"))
        still = a.evaluate("() => document.activeElement && document.activeElement.getAttribute('data-testid')")
        checks.append((f"키를 눌러도 입력 칸 포커스 유지 (실제 {still})", still == "chat-input"))

        # 페이지 스크롤: 스크롤 가능한 페이지로 만든 뒤 캔버스 포커스에서 Space/↓/↑를 누른다
        a.evaluate("() => { const d = document.createElement('div'); d.id = 'qa-spacer'; d.style.height = '3000px'; document.body.appendChild(d); window.scrollTo(0, 0); }")
        scrollable = a.evaluate("() => document.documentElement.scrollHeight > window.innerHeight + 100")
        focus_canvas(a)
        time.sleep(0.2)
        for k in ("ArrowDown", "Space", "ArrowUp"):
            a.keyboard.press(k)
            time.sleep(0.15)
        sy = a.evaluate("() => window.scrollY")
        a.evaluate("() => { const d = document.getElementById('qa-spacer'); if (d) d.remove(); }")
        if scrollable:
            checks.append((f"캔버스 포커스: Space/↓/↑ 페이지 스크롤 없음 (scrollY {sy})", sy == 0))
        else:
            checks.append(("캔버스 포커스 스크롤 검사: 페이지가 스크롤되지 않는 구조라 미검증", None))
        time.sleep(0.8)

        # 로그 목록 포커스 중 방향키는 목록에 양보 (캐릭터 이동 안 함)
        lg = a.get_by_test_id("chat-log")
        if lg.count() and lg.is_visible():
            lg.focus()
            x1 = state(a)["me"]["x"]
            a.keyboard.down("ArrowRight")
            time.sleep(0.3)
            a.keyboard.up("ArrowRight")
            x2 = state(a)["me"]["x"]
            checks.append((f"로그 목록 포커스 중 →: 캐릭터 이동 안 함 (x {x1} -> {x2})", abs(x2 - x1) < 0.5))
        else:
            checks.append(("로그 목록 포커스 검사: 로그 목록이 보이지 않아 미검증", None))

        # 버튼 포커스 중 Space는 버튼 동작 (점프 아님)
        fold = a.get_by_test_id("log-fold")
        if fold.count() and fold.is_visible():
            before = fold.get_attribute("aria-expanded")
            fold.focus()
            a.keyboard.press("Space")
            time.sleep(0.3)
            after = fold.get_attribute("aria-expanded")
            m = state(a)["me"]
            checks.append((f"버튼 포커스 중 Space = 버튼 동작 (aria-expanded {before} -> {after}), 점프 없음 (y {m['y']}, s {m['s']})",
                           before != after and m["y"] == GROUND_Y and m["s"] == "idle"))
        else:
            checks.append(("버튼 포커스 Space 검사: 접기 버튼이 보이지 않아 미검증", None))
    finally:
        ctx.close()
    return verdict(checks)


@case(45, "360x640 모바일 (dpr2, 터치): 버튼 4개(move-left, move-right, crouch, jump) 보임·높이 44 이상·겹침 0·캔버스 아래/채팅 위·가로 안, 캔버스 360x508, 가로 스크롤 없음, 중앙점 히트 = 해당 버튼, 탭 점프, 누르고 있기 숙이기 + 오른쪽 이동 없음")
def t45(browser, col):
    ctx = new_ctx(browser, viewport={"width": 360, "height": 640}, device_scale_factor=2, is_mobile=True, has_touch=True)
    checks = []
    try:
        a = open_as(ctx, col, "A", "a")
        create_profile(a, "모바일45")
        ui_create_room(a, "모바일45방")
        time.sleep(0.6)
        names = ["move-left", "move-right", "crouch", "jump"]
        bx = {t: a.get_by_test_id(t).bounding_box() for t in names + ["game-canvas", "chat-input"]}
        if any(v is None for v in bx.values()):
            checks.append((f"보이지 않는 요소: {[k for k, v in bx.items() if v is None]}", False))
            return verdict(checks)
        cv = bx["game-canvas"]
        checks.append((f"캔버스 360x508 유지 (실제 {cv['width']:.0f}x{cv['height']:.0f})", abs(cv["width"] - 360) <= 1 and abs(cv["height"] - 508) <= 1))
        hs = {t: round(bx[t]["height"], 1) for t in names}
        checks.append((f"터치 버튼 4개 보임, 높이 44 이상 (실제 {hs})", all(h >= 44 for h in hs.values())))

        def ov(p, q):
            return (min(p["x"] + p["width"], q["x"] + q["width"]) - max(p["x"], q["x"]) > 0.5
                    and min(p["y"] + p["height"], q["y"] + q["height"]) - max(p["y"], q["y"]) > 0.5)

        pairs = [f"{p}~{q}" for i, p in enumerate(names) for q in names[i + 1:] if ov(bx[p], bx[q])]
        checks.append((f"버튼끼리 겹침 0 (겹친 쌍 {pairs or '없음'})", not pairs))
        below = all(bx[t]["y"] >= cv["y"] + cv["height"] - 0.5 for t in names)
        above_chat = all(bx[t]["y"] + bx[t]["height"] <= bx["chat-input"]["y"] + 0.5 for t in names)
        checks.append(("버튼은 캔버스 아래, 채팅 입력 위", below and above_chat))
        inside = all(bx[t]["x"] >= -0.5 and bx[t]["x"] + bx[t]["width"] <= 360.5 for t in names)
        checks.append(("버튼 가로 범위 0~360 안", inside))
        sw = a.evaluate("() => document.documentElement.scrollWidth")
        checks.append((f"가로 스크롤 없음 (scrollWidth {sw}, 기대 360 이하)", sw <= 360))
        hits = {}
        for t in names:
            c = bx[t]
            hits[t] = a.evaluate(
                "([x, y]) => { const el = document.elementFromPoint(x, y); const h = el && el.closest('[data-testid]'); return h ? h.getAttribute('data-testid') : null; }",
                [c["x"] + c["width"] / 2, c["y"] + c["height"] / 2])
        checks.append((f"버튼 중앙점 히트 = 해당 버튼 (실제 {hits})", all(hits[t] == t for t in names)))

        a.get_by_test_id("jump").tap()
        seen = []
        t0 = time.time()
        while time.time() - t0 < 1.0:
            seen.append(state(a)["me"]["s"])
            time.sleep(0.03)
        mj = state(a)["me"]
        checks.append((f"탭 점프: jump 관측, 착지 후 y 440·idle (관측 순서 {collapse(seen)}, 최종 y {mj['y']} s {mj['s']})",
                       "jump" in seen and mj["y"] == GROUND_Y and mj["s"] == "idle"))

        crouch = a.get_by_test_id("crouch")
        right = a.get_by_test_id("move-right")
        crouch.dispatch_event("pointerdown")
        time.sleep(0.25)
        s1 = state(a)["me"]
        right.dispatch_event("pointerdown")
        time.sleep(0.35)
        s2 = state(a)["me"]
        right.dispatch_event("pointerup")
        crouch.dispatch_event("pointerup")
        time.sleep(0.3)
        s3 = state(a)["me"]
        checks.append((f"누르고 있기 숙이기: s prone, frame 10 (실제 {s1['s']}, {s1['frame']})", s1["s"] == "prone" and s1["frame"] == 10))
        checks.append((f"숙인 채 오른쪽 버튼: x 불변 (x {s1['x']} -> {s2['x']})", abs(s2["x"] - s1["x"]) < 0.5 and s2["s"] == "prone"))
        checks.append((f"손 뗌: idle 복귀 (s {s3['s']})", s3["s"] == "idle"))
    finally:
        ctx.close()
    return verdict(checks)


@case(46, "재연결 (local 훅 debug-drop fail=2, 1280x800): 끊김 배너 -> 약 7초 뒤 자동 복구(배너 숨김), 대기 4초 구간 '지금 연결' 표시, 시도마다 join→join-ok→open, join 3·open 3·drops +1·track +1, 로그 끊김/다시 연결, 복구 후 이동 반영")
def t46(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        a, b, rid = pair_in_room(ctx, col, "재연결46A", "재연결46B", "재연결46")
        time.sleep(0.3)
        lk0 = link_stats(b)
        ad0 = adapter_stats(b)
        uid_b = state(b)["userId"]
        b.evaluate(DEBUG_DROP_JS, [rid, uid_b, 2])
        banner = b.get_by_test_id("game-banner")
        shown = wait_until(lambda: banner.is_visible(), 3)
        checks.append(("끊김 직후 배너 표시 (game-banner)", bool(shown)))
        t0 = time.time()
        conns = []
        btn_seen = False
        recovered = False
        while time.time() - t0 < 15:
            c = state(b).get("connection")
            if not conns or conns[-1] != c:
                conns.append(c)
            if b.get_by_test_id("reconnect-button").is_visible():
                btn_seen = True
            if c == "connected" and not banner.is_visible():
                recovered = True
                break
            time.sleep(0.1)
        dt = time.time() - t0
        checks.append((f"자동 복구: 배너 숨김 + connected ({dt:.1f}초, 기준 15초 이내, 연결 상태 순서 {conns})", recovered))
        checks.append(("'지금 연결' 버튼: 대기 4초 이상 구간에서 표시 (설계 RECONNECT_BUTTON_MIN_MS 4000)", btn_seen))
        time.sleep(0.4)
        lk1 = link_stats(b)
        ad1 = adapter_stats(b)
        dj = lk1.get("joins", 0) - lk0.get("joins", 0)
        do = lk1.get("opens", 0) - lk0.get("opens", 0)
        dd = lk1.get("drops", 0) - lk0.get("drops", 0)
        dtr = ad1.get("track", 0) - ad0.get("track", 0)
        checks.append((f"join 3회 (실패 2 + 성공 1) (실제 {dj})", dj == 3))
        checks.append((f"open 3회 (실제 {do})", do == 3))
        checks.append((f"drops +1 (실제 {dd})", dd == 1))
        checks.append((f"Presence track +1 (성공한 구독 1회, 실패 시도에는 track 없음) (실제 {dtr})", dtr == 1))
        evs = lk1.get("events") or []
        last_drop = max((i for i, e in enumerate(evs) if e and e[0] == "drop"), default=-1)
        seq = [e[0] for e in evs[last_drop + 1:] if e and e[0] in ("join", "join-ok", "open", "open-ok", "open-fail", "join-fail")]
        exp = ["join", "join-ok", "open", "open-fail", "join", "join-ok", "open", "open-fail", "join", "join-ok", "open", "open-ok"]
        checks.append((f"시도 순서 join→join-ok→open (실패 2회 후 성공) (실제 {seq})", seq == exp))
        logs = [it["text"] for it in log_items(b)]
        checks.append(("로그: '연결이 끊어졌어요' 줄", any("연결이 끊어졌어요" in t for t in logs)))
        checks.append(("로그: '다시 연결됐어요' 줄", any("다시 연결됐어요" in t for t in logs)))
        px = lambda: (find_player(b, "재연결46A") or {}).get("x", 0)  # noqa: E731
        xa0 = px()
        focus_canvas(a)
        hold_key(a, "ArrowRight", 600)
        moved = wait_until(lambda: px() - xa0 >= 50, 4)
        checks.append((f"복구 후 A 이동이 B 화면에 반영 (dx {px() - xa0:.0f}, 기준 50 이상)", bool(moved)))
    finally:
        ctx.close()
    return verdict(checks)


# ---------------------------------------------------------------------------
# 사이클 10 (ARCHITECTURE "사이클 10 계약" + "변경(2026-10-29 사용자)"): 버프 10스택, 상한 w420 hits11 dmax170,
# 쿨다운 최소 0.10, HP 회복 아이템 heal, 호스트 인계, 로프, 카메라 경계, 자동 줍기와 Z, 위조 atk, 사망 시 버프 초기화.
# 값은 전부 계약 문서에서 옮긴 상수다. 프런트 값을 그대로 믿지 않고 공식으로 다시 계산해 비교한다.
# ---------------------------------------------------------------------------
def c10_pair(ctx, col, nick_a, nick_b, room):
    """pair_in_room과 같지만 두 탭 모두 ?debug로 연다 (버프 주입 훅 사용)."""
    a = c10_open_debug(ctx, col, "A", "a")
    create_profile(a, nick_a)
    rid = ui_create_room(a, room)
    b = c10_open_debug(ctx, col, "B", "b")
    create_profile(b, nick_b)
    enter_from_lobby(b, room)
    wait_until(lambda: find_player(a, nick_b) is not None, 6)
    wait_until(lambda: find_player(b, nick_a) is not None, 6)
    return a, b, rid


C10_BUFFS = ["range", "multi", "element", "power", "speed"]
C10_STACK_MAX = 10
C10_CAP = {"w": 420, "hits": 11, "dmax": 170, "el": 3}  # 받는 쪽 상한 (계약)
C10_HEAL = 30
C10_MAX_HP = 100
C10_BUFF_MS = 60000


def c10_exp_attack(stacks):
    """계약 공식으로 기대 공격 값. stacks = {버프 id: 스택}. 상한 적용 후 값."""
    g = lambda k: stacks.get(k, 0)  # noqa: E731
    es = g("element")
    tier = 0 if es == 0 else (1 if es <= 3 else (2 if es <= 6 else 3))  # 1~3 불, 4~6 얼음, 7~10 번개
    pb = min(40, 4 * g("power"))  # power +4/스택, 최대 +40
    return {
        "w": min(C10_CAP["w"], 70 + 35 * g("range")),  # range: 판정 가로 70 + 35/스택, 최대 420
        "hits": min(C10_CAP["hits"], 1 + g("multi")),  # multi: 타수 1 + 스택, 최대 11
        "dmin": 8 + pb, "dmax": 14 + pb,
        "el": tier,
        "cooldown": max(0.10, 0.45 * (0.8 ** g("speed"))),  # speed: 0.45 x 0.8^스택, 최소 0.10
    }


def c10_open_debug(ctx, col, label, name):
    """?debug 탭(버프 주입 훅 window.__mushroomDebug 사용). 부팅 후 프로필/로비/방 중 하나."""
    page = ctx.new_page()
    col.attach(page, label)
    page.goto(f"{BASE}?as={name}&debug")
    if wait_until(lambda: sc(page) in ("profile", "lobby", "room"), 10) is None:
        raise AssertionError(f"[{label}] 부트 후 화면 전환 실패")
    return page


def c10_buff_stacks(page):
    return {b["id"]: b["stacks"] for b in cb(page)["buffs"]}


def cb(page):
    return state(page)["combat"]


def c10_inject(page, bid, n=1):
    for _ in range(n):
        page.evaluate("(id) => window.__mushroomDebug.buff(id)", bid)


def c10_clear(page):
    page.evaluate("() => window.__mushroomDebug.clearBuffs()")


def c10_attack_ok(att, exp):
    return (att["w"] == exp["w"] and att["hits"] == exp["hits"] and att["dmin"] == exp["dmin"]
            and att["dmax"] == exp["dmax"] and att["el"] == exp["el"] and abs(att["cooldown"] - exp["cooldown"]) < 0.001)


def c10_fake_event(page, event, payload, sender="qa-fake-sender"):
    """같은 방 채널에 게임 이벤트를 가짜 발신자 이름으로 넣는다 (local 어댑터 envelope: {type:'ev', event, payload, from})."""
    rid = state(page)["room"]["id"]
    page.evaluate("""([rid, event, payload, from]) => { const bc = new BroadcastChannel('mushroom:room:' + rid);
      bc.postMessage({ type: 'ev', event, payload, from }); setTimeout(() => bc.close(), 300); }""",
                  [rid, event, payload, sender])


def c10_forged_atk(page, victim_x, victim_y, sender_uid, **over):
    """sender_uid가 victim 앞쪽에서 휘두른 것처럼 atk를 보낸다. over는 w/hits/dmin/dmax/el 덮어쓰기."""
    p = {"user_id": sender_uid, "x": victim_x - 20, "y": victim_y, "dir": "right", "seq": 1,
         "w": 70, "hits": 1, "dmin": 1, "dmax": 1, "el": 0}
    p.update(over)
    c10_fake_event(page, "atk", p, sender=sender_uid)


def c10_face(page, toward):
    """toward(사람 객체)가 있는 쪽을 보게 한다 (짧게 누른다)."""
    me = state(page)["me"]
    d = toward["x"] - me["x"]
    if abs(d) < 1:
        return
    key = "ArrowRight" if d > 0 else "ArrowLeft"
    hold_key(page, key, 60)
    time.sleep(0.15)


@case(47, "버프 값 (계약 2026-10-29): 5종 각각 1~10스택 공식 일치(w, hits, dmin/dmax, el 색 tier, 쿨다운 0.45x0.8^s 최소 0.10), 11번째 줍기는 10에서 멈춤, 전부 10스택일 때 상한 값 (디버그 주입)")
def t47(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        a = c10_open_debug(ctx, col, "A", "c10a")
        create_profile(a, "버프47")
        ui_create_room(a, "버프47방")
        wait_sprite(a)
        time.sleep(0.3)
        for bid in C10_BUFFS:
            bad = []
            for k in range(1, C10_STACK_MAX + 1):
                c10_clear(a)
                c10_inject(a, bid, k)
                c = cb(a)
                got_s = c10_buff_stacks(a).get(bid)
                exp = c10_exp_attack({bid: k})
                if got_s != k or not c10_attack_ok(c["attack"], exp):
                    bad.append(f"{k}스택: 스택 {got_s}, 공격 {c['attack']} 기대 {exp}")
            checks.append((f"{bid} 1~10스택 공식 일치 (불일치 {bad[:2] or '없음'})", not bad))
        c10_clear(a)
        c10_inject(a, "range", 11)
        checks.append((f"range 11번 줍기: 스택 10에서 멈춤 (실제 {c10_buff_stacks(a).get('range')})", c10_buff_stacks(a).get("range") == 10))
        checks.append((f"range 10스택: w 420 (상한, 실제 {cb(a)['attack']['w']})", cb(a)["attack"]["w"] == 420))
        c10_clear(a)
        for bid in C10_BUFFS:
            c10_inject(a, bid, 10)
        exp = c10_exp_attack({b: 10 for b in C10_BUFFS})
        att = cb(a)["attack"]
        checks.append((f"5종 모두 10스택: 공격 값 기대 {exp} (실제 {att})", c10_attack_ok(att, exp)))
        checks.append((f"5종 모두 10스택: 쿨다운 최소 0.10 (실제 {att['cooldown']})", abs(att["cooldown"] - 0.10) < 0.001))
        checks.append((f"5종 모두 10스택: hits 11, el 3(번개) (실제 hits {att['hits']}, el {att['el']})", att["hits"] == 11 and att["el"] == 3))
        # 주의: element 피해 배율(+20%/스택, 최대 +200%)은 attack 상태에 노출되지 않는다. el 상한 3과 함께 전달 방식이 계약에 빠져 있어 미검증.
        checks.append(("element 피해 배율 +200% 실측 (el 상한 3과 전달 방식 계약 미정: 미검증)", None))
        c10_clear(a)
        checks.append(("clearBuffs 후 기본 공격 값 (w 70, hits 1, 8~14, el 0, 0.45초)",
                       c10_attack_ok(cb(a)["attack"], c10_exp_attack({}))))
    finally:
        ctx.close()
    return verdict(checks)


@case(48, "버프 시간 (계약 60초): 다시 주우면 시간 60초로 갱신, 만료는 그 버프만 사라짐 (speed를 30초 뒤 다시 주움, range는 60초 뒤 사라지고 speed는 남음). 약 62초 대기")
def t48(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        a = c10_open_debug(ctx, col, "A", "c10t")
        create_profile(a, "시간48")
        ui_create_room(a, "시간48방")
        wait_sprite(a)
        c10_clear(a)
        c10_inject(a, "range", 1)
        c10_inject(a, "speed", 1)
        t0 = time.time()
        left = {b["id"]: b["leftMs"] for b in cb(a)["buffs"]}
        checks.append((f"주운 직후 남은 시간 약 60초 (range {left.get('range')}, speed {left.get('speed')})",
                       left.get("range", 0) > 59000 and left.get("speed", 0) > 59000))
        time.sleep(30)
        c10_inject(a, "speed", 1)  # 시간 갱신 + 스택 2
        sp = {b["id"]: (b["stacks"], b["leftMs"]) for b in cb(a)["buffs"]}
        checks.append((f"speed 다시 주움: 스택 2, 시간 60초로 갱신 (실제 {sp.get('speed')})",
                       sp.get("speed", (0, 0))[0] == 2 and sp.get("speed", (0, 0))[1] > 59000))
        wait_until(lambda: "range" not in c10_buff_stacks(a), 40, 0.5)
        elapsed = time.time() - t0
        ids_after = c10_buff_stacks(a)
        checks.append((f"range는 주운 뒤 약 60초에 사라짐 (경과 {elapsed:.1f}초, 남은 버프 {ids_after})",
                       "range" not in ids_after and 59 <= elapsed <= 65))
        checks.append((f"speed는 그대로 남음 (60초 시점 기준 약 30초 남음, 실제 {ids_after.get('speed')})",
                       ids_after.get("speed") == 2))
        checks.append(("range 사라진 뒤 공격 값 사거리 70으로 복귀 (실제 w 기대 70)", cb(a)["attack"]["w"] == 70))
    finally:
        ctx.close()
    return verdict(checks)


@case(49, "HP 회복 아이템 heal (계약 2026-10-29): 줍는 즉시 HP +30, 최대 100 초과 불가, 버프 목록에는 안 들어감, 다른 클라이언트 화면에 hp 전파. 공격 맞춘 뒤 회복 (가짜 발신자 drop 주입)")
def t49(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        a, b, rid = c10_pair(ctx, col, "회복49A", "회복49B", "회복49")
        time.sleep(0.5)
        uid_a = state(a)["userId"]
        # B를 A 앞 가까이 세운다. 가짜 atk(A 이름)로 B의 HP를 낮춘다: 한 번 11타 x 1 = 11 피해
        spread(b, 40, 60)
        time.sleep(0.2)
        pb = find_player(a, "회복49B")
        for i in range(5):
            c10_forged_atk(b, pb["x"], pb["y"], uid_a, hits=11, dmin=1, dmax=1, el=0, w=420)
            time.sleep(0.7)  # 무적 0.6초 지나고
        hp_low = state(b)["combat"]["hp"]
        checks.append((f"가짜 공격 5번(11타 x 1)으로 B HP 낮춤: 기대 45 (실제 {hp_low})", hp_low == 45))
        # heal 드롭을 가짜 발신자로 주입. B 위치(지면)에 놓으면 자동으로 줍는다
        drop_id = "qa-heal-1"
        gy = state(b)["combat"]["world"]["groundY"]
        c10_fake_event(b, "drop", {"id": drop_id, "buff": "heal", "x": int(state(b)["me"]["x"]), "y": gy, "ttl": 30000}, sender="qa-fake-drop")
        ok_pick = wait_until(lambda: state(b)["combat"]["hp"] == 75, 4)
        checks.append((f"heal 줍기: HP +30 (45 -> 75, 실제 {state(b)['combat']['hp']})", ok_pick is not None))
        checks.append((f"heal은 버프 목록에 없음 (실제 {c10_buff_stacks(b)})", "heal" not in c10_buff_stacks(b)))
        seen = wait_until(lambda: (find_player(a, "회복49B") or {}).get("hp") == 75, 4)
        checks.append((f"다른 클라이언트 A 화면에 B HP 75 전파 (실제 {(find_player(a, '회복49B') or {}).get('hp')})", seen is not None))
        # 최대 100 초과 불가: 75 + 30 -> 100
        c10_fake_event(b, "drop", {"id": "qa-heal-2", "buff": "heal", "x": int(state(b)["me"]["x"]), "y": gy, "ttl": 30000}, sender="qa-fake-drop")
        capped = wait_until(lambda: state(b)["combat"]["hp"] == 100, 4)
        checks.append((f"heal 두 번째: 75 + 30 은 100에서 멈춤 (실제 {state(b)['combat']['hp']})", capped is not None))
        time.sleep(0.2)
        checks.append((f"최대 HP 100 초과 없음 (실제 {state(b)['combat']['hp']})", state(b)["combat"]["hp"] == 100))
        seen2 = wait_until(lambda: (find_player(a, "회복49B") or {}).get("hp") == 100, 4)
        checks.append((f"A 화면에도 HP 100 전파 (실제 {(find_player(a, '회복49B') or {}).get('hp')})", seen2 is not None))
    finally:
        ctx.close()
    return verdict(checks)


@case(50, "PvP 위조 atk 상한과 무적 순서 (계약 2026-10-29): hits 99 -> 11타만, w 999 -> 420, el 9 -> 3, 같은 무적 시간 안 두 번째 atk는 0타, 무적 0.6초 뒤 다시 맞음, 사망하면 버프 초기화")
def t50(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        a, b, rid = c10_pair(ctx, col, "상한50A", "상한50B", "상한50")
        time.sleep(0.5)
        uid_a = state(a)["userId"]
        spread(b, 40, 60)
        pb = find_player(a, "상한50B")
        s0 = cb(b)["stats"]
        # 1) hits 99, w 999 -> 상한 11타, w 420. 1타 = 1 피해 (dmin = dmax = 1, el 0)
        c10_forged_atk(b, pb["x"], pb["y"], uid_a, hits=99, w=999, dmin=1, dmax=1, el=0)
        time.sleep(0.4)
        s1 = cb(b)["stats"]
        hp1 = cb(b)["hp"]
        checks.append((f"위조 hits 99: 11타만 적용 (pvpHitCount +{s1['pvpHitCount'] - s0['pvpHitCount']}, 기대 +11)",
                       s1["pvpHitCount"] - s0["pvpHitCount"] == 11))
        checks.append((f"위조 hits 99: atkCapped +1 (실제 +{s1['atkCapped'] - s0['atkCapped']})", s1["atkCapped"] - s0["atkCapped"] == 1))
        checks.append((f"위조 hits 99: HP 100 - 11 = 89 (실제 {hp1})", hp1 == 89))
        # 2) 무적 0.6초 안의 두 번째 atk는 0타
        c10_forged_atk(b, pb["x"], pb["y"], uid_a, hits=11, dmin=1, dmax=1, el=0, w=420)
        time.sleep(0.3)
        s2 = cb(b)["stats"]
        checks.append((f"무적 중 두 번째 atk: 추가 타 0 (pvpHitCount +{s2['pvpHitCount'] - s1['pvpHitCount']})",
                       s2["pvpHitCount"] == s1["pvpHitCount"] and cb(b)["hp"] == hp1))
        # 3) 무적이 풀린 뒤: el 9 -> 3, dmax 1 x 1.6 -> 2, 10타 = 20
        time.sleep(0.6)
        c10_forged_atk(b, pb["x"], pb["y"], uid_a, hits=10, w=999, dmin=1, dmax=1, el=9)
        time.sleep(0.4)
        s3 = cb(b)["stats"]
        hp3 = cb(b)["hp"]
        checks.append((f"위조 el 9 / w 999 / 10타: 10타 적용, HP 89 - 20 = 69 (실제 hp {hp3}, 타 +{s3['pvpHitCount'] - s2['pvpHitCount']})",
                       s3["pvpHitCount"] - s2["pvpHitCount"] == 10 and hp3 == 69))
        checks.append((f"위조 el 9: atkCapped 추가 (+{s3['atkCapped'] - s2['atkCapped']}, 기대 +1 이상)", s3["atkCapped"] - s2["atkCapped"] >= 1))
        # 4) 사망하면 버프 초기화. B 버프 주입 후 한 방에 죽인다 (dmin = dmax = 170, 1타)
        c10_inject(b, "range", 3)
        c10_inject(b, "power", 2)
        checks.append((f"사망 전 B 버프 있음 ({c10_buff_stacks(b)})", len(c10_buff_stacks(b)) == 2))
        time.sleep(0.7)
        c10_forged_atk(b, pb["x"], pb["y"], uid_a, hits=1, w=420, dmin=170, dmax=170, el=0)
        time.sleep(0.4)
        checks.append((f"사망(HP 0): dead True, 버프 모두 사라짐 (dead {cb(b)['dead']}, 버프 {c10_buff_stacks(b)})",
                       cb(b)["dead"] is True and c10_buff_stacks(b) == {}))
        checks.append(("element 피해 배율 실측 (el 상한 3과 전달 방식 계약 미정: 미검증)", None))
    finally:
        ctx.close()
    return verdict(checks)


@case(51, "호스트 인계: 호스트(사전순 최소 user_id) 탭을 닫으면 남은 탭이 호스트가 되고 몬스터 시뮬레이션을 이어 간다 (끊긴 뒤 몬스터 id 유지, 계속 움직임)")
def t51(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        a, b, rid = c10_pair(ctx, col, "호스트51A", "호스트51B", "호스트51")
        wait_until(lambda: cb(a).get("host") is not None and cb(b).get("host") is not None, 4)
        time.sleep(2.0)  # 첫 연결 1.5초 뒤 호스트 시뮬레이션 시작
        host_uid = cb(a)["host"]
        checks.append((f"호스트 두 탭 합의 (A {cb(a)['host']}, B {cb(b)['host']})", cb(a)["host"] == cb(b)["host"]))
        hp_page, other = (a, b) if state(a)["userId"] == host_uid else (b, a)
        checks.append((f"호스트 탭 시뮬레이션 중 (simulating {cb(hp_page)['simulating']})", cb(hp_page)["simulating"] is True))
        ids_before = {m["id"] for m in cb(other)["mobs"]}
        checks.append((f"몬스터 존재 (호스트 시뮬 {len(ids_before)}마리)", len(ids_before) > 0))
        time.sleep(0.5)
        hp_page.close()
        ok = wait_until(lambda: cb(other)["isHost"] is True and cb(other)["simulating"] is True, 8)
        checks.append((f"호스트 탭 닫음 -> 남은 탭이 호스트 + 시뮬레이션 시작 (isHost {cb(other)['isHost']}, sim {cb(other)['simulating']})", ok is not None))
        xs1 = {m["id"]: m["x"] for m in cb(other)["mobs"]}
        time.sleep(2.0)
        mobs2 = cb(other)["mobs"]
        ids_after = {m["id"] for m in mobs2}
        kept = ids_before & ids_after
        checks.append((f"인계 후 몬스터 id 유지 (이전 {len(ids_before)}, 이후 유지 {len(kept)})", len(kept) >= max(1, len(ids_before) - 2)))
        moved = [m for m in mobs2 if m["id"] in xs1 and abs(m["x"] - xs1[m["id"]]) >= 1]
        checks.append((f"인계 후 몬스터가 계속 움직임 (움직인 {len(moved)}마리)", len(moved) >= 1))
        checks.append(("인계 후 호스트 시뮬레이션 다시 생성됨 (mobs 목록 비지 않음)", len(mobs2) > 0))
    finally:
        ctx.close()
    return verdict(checks)


@case(52, "로프 (맵 manifest l-rope-cafe1, 13개 중 1개): ↑로 잡기, 160/초 오르기(1초 기준 120~200), 위끝에서 발판(y 612)에 올라서기, 올라선 뒤 ↑를 계속 눌러도 뛰지 않음. 나머지 12개 로프와 뛰어내리기는 미검증")
def t52(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        page = c10_open_debug(ctx, col, "A", "c10r")
        create_profile(page, "로프52")
        ui_create_room(page, "로프52방")
        wait_sprite(page)
        time.sleep(0.4)
        rope = next(r for r in MAP_MANIFEST["ropes"] if r["id"] == "l-rope-cafe1")
        rx, ry1, ry2 = rope["x"], rope["y1"], rope["y2"]
        focus_canvas(page)
        # 지면에서 로프 x까지 걷는다 (왼쪽으로). 스폰 1647 -> 490 약 1157 단위
        for _ in range(12):
            d = rx - state(page)["me"]["x"]
            if abs(d) <= 4:
                break
            hold_key(page, "ArrowRight" if d > 0 else "ArrowLeft", min(3000, max(40, abs(d) / WALK_SPEED * 1000)))
            time.sleep(0.1)
        me = state(page)["me"]
        checks.append((f"로프 x {rx} 근처에 섬 (실제 x {me['x']:.0f}, 허용 +-12)", abs(me["x"] - rx) <= 12))
        y0 = me["y"]
        hold_key(page, "ArrowUp", 900)
        time.sleep(0.15)
        st1 = state(page)["me"]
        dy = y0 - st1["y"]
        checks.append((f"↑로 잡기: 상태 climb (실제 {st1['s']})", st1["s"] == "climb"))
        checks.append((f"0.9초 ↑: 160/초 근사 이동 {dy:.0f} (기대 120~200)", 120 <= dy <= 200))
        hold_key(page, "ArrowUp", 2200)  # 위끝 612까지 + 계속 누름
        time.sleep(0.4)
        top = state(page)["me"]
        checks.append((f"위끝에서 발판에 올라섬 (y {top['y']}, 기대 612 +-2, 상태 {top['s']})",
                       abs(top["y"] - ry1) <= 2 and top["s"] != "climb"))
        time.sleep(0.5)
        still = state(page)["me"]
        checks.append((f"올라선 뒤 누르고 있던 ↑로 바로 뛰지 않음 (y {still['y']}, 기대 612 +-2)", abs(still["y"] - ry1) <= 2))
        checks.append(("나머지 12개 로프 잡기/뛰어내리기/일반 점프 + 로프로 모든 발판 도달 (미검증, 계약 점검 항목)", None))
    finally:
        ctx.close()
    return verdict(checks)


@case(53, "카메라 경계 (3840 맵, 1280x800): 시작 위치에서 camX = 플레이어 기준 클램프, 왼쪽 끝 camX 0, 오른쪽 끝 camX = width - viewW. 약 35초 걸림")
def t53(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        page = c10_open_debug(ctx, col, "A", "c10c")
        create_profile(page, "카메라53")
        ui_create_room(page, "카메라53방")
        wait_sprite(page)
        time.sleep(0.4)
        st = state(page)
        vw = st["assets"]["layout"]["viewW"]
        W = WORLD_W
        exp0 = min(max(st["me"]["x"] - vw / 2, 0), max(0, W - vw))
        cam0 = st["world"]["camX"]
        checks.append((f"시작: camX {cam0} = 기대 {exp0:.0f} (맵 폭 {W}, 시야 {vw}, 허용 2)", cam0 is not None and abs(cam0 - exp0) <= 2))
        focus_canvas(page)
        for _ in range(40):  # 왼쪽 끝
            if state(page)["me"]["x"] <= 40:
                break
            hold_key(page, "ArrowLeft", 800)
        time.sleep(0.4)
        cl = state(page)["world"]["camX"]
        checks.append((f"왼쪽 끝: camX {cl} = 0 (허용 1)", cl is not None and abs(cl) <= 1))
        for _ in range(60):  # 오른쪽 끝
            if state(page)["me"]["x"] >= W - 40:
                break
            hold_key(page, "ArrowRight", 800)
        time.sleep(0.4)
        cr = state(page)["world"]["camX"]
        checks.append((f"오른쪽 끝: camX {cr} = 맵 폭 - 시야 {W - vw:.0f} (허용 1)", cr is not None and abs(cr - (W - vw)) <= 1))
        cv = state(page)["world"]
        checks.append((f"camY 값 존재 (세로 카메라, 실제 {cv['camY']})", cv["camY"] is not None))
    finally:
        ctx.close()
    return verdict(checks)


@case(54, "줍기: 닿으면 자동으로 주움(범위 26), 범위 밖(35)은 자동으로 안 줍고 Z(범위 44)로 주움, 드롭은 주어진 ttl 뒤 사라짐 (가짜 발신자 drop 주입, 한 탭)")
def t54(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        page = c10_open_debug(ctx, col, "A", "c10z")
        create_profile(page, "줍기54")
        ui_create_room(page, "줍기54방")
        wait_sprite(page)
        time.sleep(0.4)
        focus_canvas(page)
        gy = state(page)["combat"]["world"]["groundY"]
        mx = int(state(page)["me"]["x"])
        c10_fake_event(page, "drop", {"id": "qa-z-1", "buff": "multi", "x": mx + 35, "y": gy, "ttl": 30000}, sender="qa-fake-drop")
        time.sleep(0.8)
        checks.append((f"범위 밖(35) 드롭은 자동으로 안 주움 (버프 {c10_buff_stacks(page)})", "multi" not in c10_buff_stacks(page)))
        page.keyboard.press("KeyZ")
        ok = wait_until(lambda: c10_buff_stacks(page).get("multi") == 1, 3)
        checks.append((f"Z로 주움: multi 1스택 (실제 {c10_buff_stacks(page)})", ok is not None))
        c10_fake_event(page, "drop", {"id": "qa-auto-1", "buff": "range", "x": int(state(page)["me"]["x"]), "y": gy, "ttl": 30000}, sender="qa-fake-drop")
        ok2 = wait_until(lambda: c10_buff_stacks(page).get("range") == 1, 3)
        checks.append((f"닿으면 자동 줍기 (Z 없이): range 1스택 (실제 {c10_buff_stacks(page)})", ok2 is not None))
        c10_fake_event(page, "drop", {"id": "qa-ttl-1", "buff": "speed", "x": int(state(page)["me"]["x"]) + 300, "y": gy, "ttl": 2000}, sender="qa-fake-drop")
        time.sleep(0.3)
        present = any(d["id"] == "qa-ttl-1" for d in cb(page)["drops"])
        time.sleep(2.2)
        gone = not any(d["id"] == "qa-ttl-1" for d in cb(page)["drops"])
        checks.append((f"ttl 2초 드롭: 처음엔 있고(present {present}), 2초 뒤 사라짐 (gone {gone})", present and gone))
        checks.append(("골렘 드롭 2개, 몬스터 처치 드롭 확률 (실제 처치 필요, 미검증)", None))
    finally:
        ctx.close()
    return verdict(checks)


@case(55, "버프 HUD (360x640 모바일, dpr2): 버프 3종 주입 시 아이콘이 화면 안에 있고 가로 스크롤 없음, 스택 표시 (x10), 버프 없으면 바 숨김")
def t55(browser, col):
    ctx = new_ctx(browser, viewport={"width": 360, "height": 640}, device_scale_factor=2, is_mobile=True, has_touch=True)
    checks = []
    try:
        page = c10_open_debug(ctx, col, "M", "c10m")
        create_profile(page, "모바일55")
        ui_create_room(page, "모바일55방")
        wait_sprite(page)
        time.sleep(0.4)
        c10_clear(page)
        checks.append(("버프 없음: 버프 바 숨김 (buff-range 요소 없음)", page.get_by_test_id("buff-range").count() == 0))
        c10_inject(page, "range", 10)
        c10_inject(page, "multi", 3)
        c10_inject(page, "speed", 2)
        time.sleep(0.4)
        box = page.get_by_test_id("buff-range").bounding_box()
        checks.append((f"range 아이콘 화면 안 (box {box})", bool(box) and box["x"] >= 0 and box["x"] + box["width"] <= 360 and box["y"] >= 0))
        sw = page.evaluate("() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]")
        checks.append((f"가로 스크롤 없음 (scrollWidth/clientWidth {sw})", sw[0] <= sw[1]))
        txt = page.get_by_test_id("buff-range").text_content() or ""
        checks.append((f"range 10스택 표시 'x10' (실제 '{txt.strip()}')", "10" in txt))
    finally:
        ctx.close()
    return verdict(checks)



C10_VITAL_STEP = 20
C10_VITAL_MAX = 300


def c10_pick_drop(page, buff, did, sender="qa-fake-drop"):
    """page 바로 위치에 buff 드롭을 놓는다. 자동 줍기로 page가 줍는다."""
    st = state(page)
    gy = st["combat"]["world"]["groundY"]
    c10_fake_event(page, "drop", {"id": did, "buff": buff, "x": int(st["me"]["x"]), "y": gy, "ttl": 30000}, sender=sender)


@case(56, "vital (계약 2026-10-29 사용자): 주우면 최대 HP +20 과 현재 HP +20, 10스택, 최대 HP 300에서 멈춤(11번째는 변화 없음), 다른 클라이언트 A 화면에 max와 hp 전파")
def t56(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        a, b, rid = c10_pair(ctx, col, "생명56A", "생명56B", "생명56")
        time.sleep(0.4)
        c10_pick_drop(b, "vital", "qa-vital-1")
        ok1 = wait_until(lambda: state(b)["me"]["max"] == 120, 4)
        checks.append((f"vital 1회: 최대 HP 120 (실제 max {state(b)['me']['max']})", ok1 is not None))
        checks.append((f"vital 1회: 현재 HP 120 (실제 hp {state(b)['me']['hp']})", state(b)["me"]["hp"] == 120))
        seen = wait_until(lambda: (find_player(a, "생명56B") or {}).get("max") == 120 and (find_player(a, "생명56B") or {}).get("hp") == 120, 4)
        pa = find_player(a, "생명56B") or {}
        checks.append((f"A 화면에 B max 120 / hp 120 전파 (실제 max {pa.get('max')}, hp {pa.get('hp')})", seen is not None))
        checks.append((f"vital은 버프 줄 스택으로 보임 (실제 {c10_buff_stacks(b)})", c10_buff_stacks(b).get("vital") == 1))
        for i in range(2, 11):
            c10_pick_drop(b, "vital", f"qa-vital-{i}")
            time.sleep(0.25)
        ok10 = wait_until(lambda: state(b)["me"]["max"] == 300, 6)
        checks.append((f"vital 10스택: 최대 HP 300 (실제 max {state(b)['me']['max']})", ok10 is not None))
        checks.append((f"vital 10스택: 현재 HP 300 (실제 hp {state(b)['me']['hp']})", state(b)["me"]["hp"] == 300))
        checks.append((f"vital 10스택: 스택 10 (실제 {c10_buff_stacks(b).get('vital')})", c10_buff_stacks(b).get("vital") == 10))
        c10_pick_drop(b, "vital", "qa-vital-11")
        time.sleep(0.8)
        me = state(b)["me"]
        checks.append((f"11번째 vital: 최대 HP 300 상한 (실제 max {me['max']}, hp {me['hp']}, 스택 {c10_buff_stacks(b).get('vital')})",
                       me["max"] == 300 and me["hp"] <= 300 and c10_buff_stacks(b).get("vital") == 10))
        seen300 = wait_until(lambda: (find_player(a, "생명56B") or {}).get("max") == 300, 4)
        checks.append((f"A 화면에 max 300 전파 (실제 {(find_player(a, '생명56B') or {}).get('max')})", seen300 is not None))
    finally:
        ctx.close()
    return verdict(checks)


@case(57, "vital 사망 복귀: 사망하면 최대 HP 100으로 돌아가고 버프 줄에서 사라짐, 부활 HP 100 (최대 100), 다른 클라이언트에도 max 100 전파. 한 대 맞혀 죽인다")
def t57(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        a, b, rid = c10_pair(ctx, col, "복귀57A", "복귀57B", "복귀57")
        time.sleep(0.4)
        for i in range(1, 6):
            c10_pick_drop(b, "vital", f"qa-v57-{i}")
            time.sleep(0.25)
        wait_until(lambda: state(b)["me"]["max"] == 200, 5)
        checks.append((f"사망 전 최대 HP 200 (vital 5스택, 실제 {state(b)['me']['max']})", state(b)["me"]["max"] == 200))
        uid_a = state(a)["userId"]
        pb = find_player(a, "복귀57B")
        # 200 HP를 한 번에 0으로: 170 + 170 (두 번째는 무적 0.6초 뒤)
        c10_forged_atk(b, pb["x"], pb["y"], uid_a, hits=1, w=420, dmin=170, dmax=170, el=0)
        time.sleep(0.8)
        c10_forged_atk(b, pb["x"], pb["y"], uid_a, hits=1, w=420, dmin=170, dmax=170, el=0)
        dead = wait_until(lambda: state(b)["me"]["dead"] is True, 4)
        checks.append((f"사망 (dead True)", dead is not None))
        me = state(b)["me"]
        checks.append((f"사망 후 최대 HP 100 복귀 (실제 max {me['max']})", me["max"] == 100))
        checks.append((f"사망 후 vital 버프 줄에서 사라짐 (실제 {c10_buff_stacks(b)})", "vital" not in c10_buff_stacks(b)))
        seen = wait_until(lambda: (find_player(a, "복귀57B") or {}).get("max") == 100, 4)
        checks.append((f"A 화면에 B max 100 전파 (실제 {(find_player(a, '복귀57B') or {}).get('max')})", seen is not None))
        ok_rev = wait_until(lambda: state(b)["combat"]["reviveVisible"] is True, 8)
        checks.append(("부활 버튼 표시 (5초 뒤)", ok_rev is not None))
        if ok_rev is not None:
            b.get_by_test_id("revive").click()
        rv = wait_until(lambda: state(b)["me"]["dead"] is False, 4)
        me2 = state(b)["me"]
        checks.append((f"부활: HP 100, 최대 HP 100 (실제 hp {me2['hp']}, max {me2['max']})", rv is not None and me2["hp"] == 100 and me2["max"] == 100))
    finally:
        ctx.close()
    return verdict(checks)


@case(58, "HP 바 비율: max 기준 비율 (hp/max). 상태값으로 비율 확인(hp 245/300 = 0.817)과 A 화면 전파. 픽셀로 그린 바 길이는 프런트 캔버스 계측 훅이 없어 미검증")
def t58(browser, col):
    ctx = new_ctx(browser)
    checks = []
    try:
        a, b, rid = c10_pair(ctx, col, "바58A", "바58B", "바58")
        time.sleep(0.4)
        for i in range(1, 11):
            c10_pick_drop(b, "vital", f"qa-b58-{i}")
            time.sleep(0.25)
        wait_until(lambda: state(b)["me"]["max"] == 300, 6)
        uid_a = state(a)["userId"]
        pb = find_player(a, "바58B")
        for i in range(5):  # 11 x 1 = 11 피해씩 5번 = 55 -> 245/300
            c10_forged_atk(b, pb["x"], pb["y"], uid_a, hits=11, dmin=1, dmax=1, el=0, w=420)
            time.sleep(0.7)
        me = state(b)["me"]
        ratio = me["hp"] / me["max"]
        checks.append((f"B hp {me['hp']} / max {me['max']} = 비율 {ratio:.3f} (기대 245/300 = 0.817)", me["hp"] == 245 and me["max"] == 300))
        seen = wait_until(lambda: (find_player(a, "바58B") or {}).get("hp") == 245, 4)
        pa = find_player(a, "바58B") or {}
        checks.append((f"A 화면 B 비율 {pa.get('hp')}/{pa.get('max')} 전파 (기대 245/300)", seen is not None and pa.get("max") == 300))
        checks.append(("HP 바 픽셀 길이 (머리 위 가로 40 중 비율 채움) (캔버스 계측 없음: 미검증)", None))
    finally:
        ctx.close()
    return verdict(checks)



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
            browser = LocalBrowser(pw.chromium.launch(headless=True))
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
