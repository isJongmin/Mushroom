#!/usr/bin/env python3
"""버섯마을 local 모드 E2E 테스트 (Python Playwright, Chromium headless). 사이클 3 계약 기준.

실행:  python3 tests/e2e_local.py [--shots DIR] [-v]
  --shots DIR : 화면 스크린샷만 찍고 종료 (login/create/game, 데스크톱 1280x800 + 모바일 360x640)
  -v          : 실패 항목의 traceback 출력
환경 변수:
  QA_SCRATCH  : 스크래치 디렉터리. 항목 17/18이 저장소 사본을 여기에 만든다 (없으면 시스템 임시 폴더).

- 저장소 루트에서 `python3 -m http.server`를 빈 포트로 띄우고, 끝나면 반드시 종료한다.
- 브라우저는 이미 설치된 Chromium을 쓴다. playwright/pip/npm 설치는 하지 않는다.
- 테스트 훅: window.__mushroom.getState(), data-testid 셀렉터 (docs/handoff/frontend-20261014-block.md 4장).
- 항목 17/18은 저장소 원본을 건드리지 않는다. build.py/check.py는 사본에서만 실행한다.
- 각 실행은 고유한 아이디/닉네임을 쓴다 (실행끼리 충돌하지 않는다).
- 항목별 결과: PASS / FAIL / UNVERIFIED. 실행하지 않은 항목은 PASS로 내지 않는다.
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
PW = "qa-pass-1234"  # 8자 이상
XSS = "<img src=x onerror=window.__xss=1>"
SCREEN_LOGIN, SCREEN_CREATE, SCREEN_GAME = "login", "create", "game"
LS_CHARACTERS = "mushroom.local.characters.v1"  # backend/local.js
WALK_FRAMES = {2, 3, 4, 5}  # ARCHITECTURE 블록 아트 계약: walk = 2,3,4,5

# 설계 문서의 오류 문구 (docs/design/screens/login.md, character-create.md, game.md)
MSG_ID_FORMAT = "아이디는 영문 소문자, 숫자, 밑줄(_)을 사용해 4~16자로 입력하세요."
MSG_PW_SHORT = "비밀번호는 8자 이상 입력하세요."
MSG_ID_TAKEN = "이미 사용 중인 아이디입니다."
MSG_LOGIN_FAILED = "아이디 또는 비밀번호가 올바르지 않습니다."
MSG_NICK_TAKEN = "이미 사용 중인 닉네임입니다."
MSG_NICK_FORMAT = "2~12자의 한글, 영문, 숫자만 사용할 수 있습니다."
MSG_COOLDOWN = "1초 뒤에 다시 보낼 수 있습니다."

# 사이클 3 아바타 계약: 정확히 7개 키
PART_KEYS7 = ["skin", "hair", "face", "top", "bottom", "shoes", "hat"]
CATEGORY_TABS = ["skin", "face", "hair", "hat", "top", "bottom", "shoes"]  # character-create.md 5.1 순서
MANIFEST = json.loads((ROOT / "assets/avatar/manifest.json").read_text(encoding="utf-8"))
PARTS = {p: [x["id"] for x in MANIFEST["parts"][p]] for p in CATEGORY_TABS}
DEFAULTS = {p: PARTS[p][0] for p in PART_KEYS7}  # manifest 각 파츠 첫 항목 (hat = none)

# 테스트 기본 아바타 (ARCHITECTURE 계약 7키, art handoff 3장 id)
AVATAR = {"skin": "light", "hair": "black-short", "face": "basic", "top": "hoodie-black",
          "bottom": "pants-navy", "shoes": "sneakers-white", "hat": "none"}
# 골라서 저장하는 값 (7파츠 모두 기본값과 다르게)
PICK = {"skin": "medium", "face": "smile", "hair": "pink-long", "hat": "mushroom-red",
        "top": "tee-stripe-red", "bottom": "skirt-pink", "shoes": "boots-brown"}
# 사이클 1 형식 저장값 (5키, eyes, 옛 id)과 정규화 기대값 (frontend 3장, art 5장 매핑표)
LEGACY_ROW = {"skin": "skin-light", "hair": "hair-round-black", "eyes": "eyes-dot",
              "top": "top-tee-red", "bottom": "bottom-shorts-navy"}
LEGACY_EXPECT = {"skin": "light", "hair": "black-short", "face": "basic", "top": "tee-stripe-red",
                 "bottom": "pants-navy", "shoes": "sneakers-white", "hat": "none"}

BASE = ""  # main()에서 설정
VERBOSE = False
RESULTS = []  # (번호, 제목, 결과, 근거)
CASES = []  # (번호, 제목, 함수)


# ---------------------------------------------------------------------------
# 서버/공통 유틸
# ---------------------------------------------------------------------------
def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_server(port):
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1", "--directory", str(ROOT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
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


def new_id():
    return "q" + secrets.token_hex(5)  # 11자, ^[a-z0-9_]{4,16}$


def new_nick():
    return "Qa" + secrets.token_hex(3)  # 8자, 영문/숫자


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


def state(page):
    return page.evaluate("window.__mushroom.getState()")


def screen(page):
    try:
        return state(page)["screen"]
    except Exception:
        return None


def create_state(page):
    return state(page).get("create") or {}


def wait_create_ready(page, timeout=8.0):
    return wait_until(lambda: create_state(page).get("ready") is True, timeout)


def wait_screen(page, name, timeout=8.0):
    if wait_until(lambda: screen(page) == name, timeout) is None:
        raise AssertionError(f"'{name}' 화면으로 전환되지 않음 (현재 {screen(page)})")


def wait_connected(page, timeout=12.0):
    if wait_until(lambda: state(page)["connection"] == "connected", timeout) is None:
        raise AssertionError(f"연결(connected) 대기 시간 초과 (현재 {state(page)['connection']})")


def open_page(ctx, col, label):
    page = ctx.new_page()
    col.attach(page, label)
    page.goto(BASE)
    if wait_until(lambda: screen(page) in (SCREEN_LOGIN, SCREEN_CREATE, SCREEN_GAME), 10) is None:
        raise AssertionError(f"[{label}] 부트 후 화면 전환 실패")
    return page


def signup(page, uid, pw=PW):
    page.get_by_test_id("toggle-signup").click()
    page.get_by_test_id("login-id").fill(uid)
    page.get_by_test_id("login-pw").fill(pw)
    page.get_by_test_id("login-pw-confirm").fill(pw)
    page.get_by_test_id("login-submit").click()
    wait_screen(page, SCREEN_CREATE)
    wait_create_ready(page)


def login(page, uid, pw=PW):
    page.get_by_test_id("login-id").fill(uid)
    page.get_by_test_id("login-pw").fill(pw)
    page.get_by_test_id("login-submit").click()


def pick_slot(page, part, item_id):
    """탭을 누르고 그 탭의 슬롯을 고른다 (슬롯은 현재 탭 것만 DOM에 있다)."""
    page.get_by_test_id(f"tab-{part}").click()
    page.get_by_test_id(f"slot-{part}-{item_id}").click()


def create_char(page, nick):
    page.get_by_test_id("nickname-input").fill(nick)
    expect(page.get_by_test_id("nickname-status")).to_have_attribute("data-state", "available", timeout=5000)
    page.get_by_test_id("create-submit").click()
    wait_screen(page, SCREEN_GAME)
    wait_connected(page)


def logout_game(page):
    page.get_by_test_id("logout").click()
    wait_screen(page, SCREEN_LOGIN)


def players(page):
    return state(page)["players"]


def find_player(page, nick):
    for p in players(page):
        if p["nickname"] == nick:
            return p
    return None


def adapter_call(page, expr):
    """페이지에서 같은 로컬 어댑터 모듈을 가져와 호출한다. 실패하면 오류 코드를 돌려준다."""
    js = f"""(async () => {{
      const m = await import('./src/client/backend/local.js');
      const b = m.createLocalBackend();
      try {{ return {{ ok: true, value: await ({expr}) }}; }}
      catch (e) {{ return {{ ok: false, code: e && e.code }}; }}
    }})()"""
    return page.evaluate(js)


def hold_key(page, key, ms):
    page.keyboard.down(key)
    time.sleep(ms / 1000)
    page.keyboard.up(key)


def place_near(pg, target_x, offset):
    """pg의 캐릭터를 target_x + offset (월드 단위) 근처로 옮긴다. 키 길이는 이동 속도 160/초로 계산."""
    me = state(pg)["me"]
    dx = (target_x + offset) - me["x"]
    if abs(dx) >= 2:
        hold_key(pg, "ArrowRight" if dx > 0 else "ArrowLeft", abs(dx) / 160 * 1000)
    time.sleep(0.3)


def send_chat(page, text):
    page.get_by_test_id("chat-input").click()
    page.keyboard.type(text)
    page.keyboard.press("Enter")


def make_pair(browser, col):
    """같은 브라우저 컨텍스트의 두 탭(같은 localStorage/BroadcastChannel, 세션은 탭별)."""
    ctx = browser.new_context()
    a = open_page(ctx, col, "A")
    b = open_page(ctx, col, "B")
    return ctx, a, b


def verdict(checks):
    failed = [name for name, ok in checks if not ok]
    detail = "; ".join(name for name, ok in checks)
    if failed:
        return ("FAIL", "실패: " + " | ".join(failed) + " || 전체: " + detail)
    return ("PASS", detail)


# ---------------------------------------------------------------------------
# 테스트 항목
# ---------------------------------------------------------------------------
def case(num, title):
    def deco(fn):
        CASES.append((num, title, fn))
        return fn

    return deco


@case(1, "회원가입 -> 캐릭터 생성(머리 탭 슬롯 선택) -> 게임 진입, 7키 저장, 새로고침 세션 복구")
def t01(browser, col):
    ctx = browser.new_context()
    page = open_page(ctx, col, "A")
    checks = []
    try:
        uid, nick = new_id(), new_nick()
        checks.append(("로그인 화면 시작", screen(page) == SCREEN_LOGIN))
        checks.append(("모드 배지 LOCAL MODE", page.get_by_test_id("mode-badge").inner_text().strip() == "LOCAL MODE"))
        signup(page, uid)
        checks.append(("가입 후 생성 화면", screen(page) == SCREEN_CREATE))
        pick_slot(page, "hair", "brown-short")  # 기본 black-short -> brown-short (슬롯 클릭)
        create_char(page, nick)
        me = state(page)["me"]
        checks.append(("게임 진입, 닉네임 저장", me is not None and me["nickname"] == nick))
        checks.append(("슬롯 선택 저장(hair=brown-short)", me is not None and me["avatar"]["hair"] == "brown-short"))
        checks.append(("저장 avatar 정확히 7키", me is not None and sorted(me["avatar"]) == sorted(PART_KEYS7)))
        checks.append(("본인 목록에 포함", find_player(page, nick) is not None))
        page.reload()
        wait_screen(page, SCREEN_GAME)
        wait_connected(page)
        me2 = state(page)["me"]
        checks.append(("새로고침 후 게임 세션 복구", me2 is not None and me2["nickname"] == nick))
        checks.append(("새로고침 후 avatar 유지", me2 is not None and me2["avatar"]["hair"] == "brown-short"))
    finally:
        ctx.close()
    return verdict(checks)


@case(2, "가입/로그인 오류 메시지 (아이디 형식, 비밀번호 8자 미만, 중복 아이디, 틀린 비밀번호)")
def t02(browser, col):
    ctx = browser.new_context()
    page = open_page(ctx, col, "A")
    checks = []
    try:
        page.get_by_test_id("toggle-signup").click()
        page.get_by_test_id("login-id").fill("Bad-ID")
        page.get_by_test_id("login-pw").fill(PW)
        page.get_by_test_id("login-pw-confirm").fill(PW)
        page.get_by_test_id("login-submit").click()
        err = page.get_by_test_id("error-id")
        expect(err).to_be_visible(timeout=3000)
        checks.append(("아이디 형식 오류 문구", err.inner_text().strip() == MSG_ID_FORMAT))

        page.get_by_test_id("login-id").fill(new_id())
        page.get_by_test_id("login-pw").fill("1234567")
        page.get_by_test_id("login-pw-confirm").fill("1234567")
        page.get_by_test_id("login-submit").click()
        expect(page.get_by_test_id("error-pw")).to_be_visible(timeout=3000)
        checks.append(("비밀번호 8자 미만 문구", page.get_by_test_id("error-pw").inner_text().strip() == MSG_PW_SHORT))

        uid = new_id()
        signup(page, uid)
        page2 = open_page(ctx, col, "A2")
        page2.get_by_test_id("toggle-signup").click()
        page2.get_by_test_id("login-id").fill(uid)
        page2.get_by_test_id("login-pw").fill(PW)
        page2.get_by_test_id("login-pw-confirm").fill(PW)
        page2.get_by_test_id("login-submit").click()
        expect(page2.get_by_test_id("error-id")).to_be_visible(timeout=3000)
        checks.append(("중복 아이디 문구", page2.get_by_test_id("error-id").inner_text().strip() == MSG_ID_TAKEN))
        page2.close()

        page.get_by_test_id("logout").click()
        wait_screen(page, SCREEN_LOGIN)
        login(page, uid, "wrong-pass-999")
        banner = page.get_by_test_id("error-message")
        expect(banner).to_be_visible(timeout=3000)
        checks.append(("틀린 비밀번호 문구", banner.inner_text().strip() == MSG_LOGIN_FAILED))
        checks.append(("틀린 비밀번호 후 비밀번호 칸 비움", page.get_by_test_id("login-pw").input_value() == ""))
        checks.append(("로그인 화면 유지", screen(page) == SCREEN_LOGIN))
    finally:
        ctx.close()
    return verdict(checks)


@case(3, "닉네임 중복(대소문자 무시) 거부, 형식 위반 거부 (UI와 어댑터 직접 호출)")
def t03(browser, col):
    ctx, a, b = make_pair(browser, col)
    checks = []
    try:
        nick = new_nick() + "Ab"  # 10자
        signup(a, new_id())
        create_char(a, nick)

        signup(b, new_id())
        b_nick = b.get_by_test_id("nickname-input")
        status = b.get_by_test_id("nickname-status")

        b_nick.fill(nick.lower())
        expect(status).to_have_attribute("data-state", "taken", timeout=5000)
        checks.append(("소문자 변형 중복 표시", status.inner_text().strip() == MSG_NICK_TAKEN))
        checks.append(("중복이면 생성 버튼 비활성", b.get_by_test_id("create-submit").is_disabled()))
        b.keyboard.press("Enter")
        time.sleep(0.5)
        checks.append(("Enter로도 생성 안 됨(생성 화면 유지)", screen(b) == SCREEN_CREATE))
        r = adapter_call(b, f"b.createCharacter({nick.lower()!r}, {AVATAR!r})")
        checks.append(("어댑터 직접 호출: NICK_TAKEN(대소문자 무시)", r.get("ok") is False and r.get("code") == "NICK_TAKEN"))

        b_nick.fill(nick)
        expect(status).to_have_attribute("data-state", "taken", timeout=5000)
        checks.append(("같은 대소문자 중복 표시", True))

        b_nick.fill("a")
        expect(status).to_have_attribute("data-state", "format", timeout=3000)
        checks.append(("1자 닉네임 형식 오류", status.inner_text().strip() == MSG_NICK_FORMAT))
        for bad in ["abc_1", "홍 길", "닉-네임"]:
            b_nick.fill(bad)
            expect(status).to_have_attribute("data-state", "format", timeout=3000)
        checks.append(("밑줄/공백/하이픈 형식 오류", True))

        b_nick.fill("")
        b_nick.press_sequentially("가" * 13)
        checks.append(("닉네임 12자 입력 제한(maxlength)", len(b_nick.input_value()) == 12))
        r2 = adapter_call(b, f"b.createCharacter({'<'!r} + 'x1', {AVATAR!r})")
        checks.append(("어댑터: 형식 위반 닉네임 NICK_FORMAT", r2.get("code") == "NICK_FORMAT"))
    finally:
        ctx.close()
    return verdict(checks)


@case(4, "계정당 캐릭터 1개: 생성 후 다시 생성 화면으로 갈 수 없음 (어댑터 CHAR_EXISTS 포함)")
def t04(browser, col):
    ctx = browser.new_context()
    page = open_page(ctx, col, "A")
    checks = []
    try:
        uid, nick = new_id(), new_nick()
        signup(page, uid)
        create_char(page, nick)
        page.reload()
        wait_screen(page, SCREEN_GAME)
        wait_connected(page)
        checks.append(("새로고침 후 게임(생성 화면 아님)", screen(page) == SCREEN_GAME))
        page.evaluate("""() => {
          window.__seen = [];
          const rec = () => { const s = document.body.dataset.screen;
            if (window.__seen[window.__seen.length - 1] !== s) window.__seen.push(s); };
          new MutationObserver(rec).observe(document.body, { attributes: true, attributeFilter: ['data-screen'] });
        }""")
        page.get_by_test_id("logout").click()
        wait_screen(page, SCREEN_LOGIN)
        login(page, uid)
        wait_screen(page, SCREEN_GAME)
        wait_connected(page)
        seen = page.evaluate("window.__seen")
        checks.append((f"재로그인 시 생성 화면을 거치지 않음 (기록 {seen})", "create" not in seen))
        r = adapter_call(page, f"b.createCharacter({'Qb' + new_nick()[2:]!r}, {AVATAR!r})")
        checks.append(("어댑터 2번째 생성: CHAR_EXISTS", r.get("code") == "CHAR_EXISTS"))
        r2 = adapter_call(page, f"b.isNicknameTaken({nick!r})")
        checks.append(("실패한 2번째 생성은 저장되지 않음(기존 닉네임만 존재)", r2.get("ok") and r2.get("value") is True))
        me = state(page)["me"]
        checks.append(("기존 캐릭터 닉네임 유지", me is not None and me["nickname"] == nick))
    finally:
        ctx.close()
    return verdict(checks)


@case(5, "두 페이지 동시 접속: 서로의 존재, 이동 반영, 채팅 반영")
def t05(browser, col):
    ctx, a, b = make_pair(browser, col)
    checks = []
    try:
        a_nick, b_nick = new_nick(), new_nick()
        signup(a, new_id())
        create_char(a, a_nick)
        signup(b, new_id())
        create_char(b, b_nick)
        ok = wait_until(lambda: find_player(a, b_nick) and find_player(b, a_nick), 6)
        checks.append(("서로의 존재 확인(목록)", bool(ok)))
        checks.append(("접속 중 2명 표시", wait_until(lambda: a.get_by_test_id("player-count").inner_text().strip() == "접속 중 2명", 4) is not None))

        x0 = find_player(b, a_nick)["x"]
        hold_key(a, "ArrowRight", 1000)
        moved = wait_until(lambda: find_player(b, a_nick)["x"] - x0 >= 100, 4)
        dx = find_player(b, a_nick)["x"] - x0
        checks.append((f"A 이동(1초 우측) B 화면에 반영 (dx={dx:.0f}px, 기대 약 160)", bool(moved)))

        text = "안녕 B 테스트"
        send_chat(a, text)
        got = wait_until(lambda: find_player(b, a_nick)["lastChat"] == text, 4)
        checks.append(("A 채팅 -> B 수신 (lastChat)", bool(got)))
        checks.append(("A 채팅 -> A 본인 lastChat", state(a)["me"]["lastChat"] == text))

        send_chat(b, "B에서 보냄")
        got2 = wait_until(lambda: find_player(a, b_nick)["lastChat"] == "B에서 보냄", 4)
        checks.append(("B 채팅 -> A 수신 (양방향)", bool(got2)))
    finally:
        ctx.close()
    return verdict(checks)


@case(6, "XSS: 닉네임 생성 시도와 채팅의 <img onerror> 입력이 실행/주입되지 않음")
def t06(browser, col):
    ctx, a, b = make_pair(browser, col)
    checks = []
    try:
        signup(a, new_id())
        a_nick_input = a.get_by_test_id("nickname-input")
        a_nick_input.press_sequentially(XSS)
        expect(a.get_by_test_id("nickname-status")).to_have_attribute("data-state", "format", timeout=3000)
        checks.append(("XSS 닉네임: 형식 오류로 거부", True))
        a.keyboard.press("Enter")
        time.sleep(0.5)
        checks.append(("XSS 닉네임: 생성 화면 유지", screen(a) == SCREEN_CREATE))
        r = adapter_call(a, f"b.createCharacter({XSS!r}, {AVATAR!r})")
        checks.append(("XSS 닉네임 어댑터 직접 호출: NICK_FORMAT", r.get("code") == "NICK_FORMAT"))

        a_nick = new_nick()
        create_char(a, a_nick)
        signup(b, new_id())
        create_char(b, new_nick())
        wait_until(lambda: find_player(b, a_nick), 6)

        send_chat(a, XSS)
        got = wait_until(lambda: find_player(b, a_nick)["lastChat"] == XSS, 4)
        checks.append(("XSS 채팅 수신(문자열로 보관됨)", bool(got)))
        time.sleep(1.0)  # onerror는 비동기이므로 잠시 기다린다
        for label, pg in (("A", a), ("B", b)):
            xss = pg.evaluate("typeof window.__xss")
            imgs = pg.evaluate("document.querySelectorAll('img').length")
            bad = pg.evaluate("document.documentElement.innerHTML.includes('onerror')")
            checks.append((f"{label}: window.__xss 미정의 ({xss})", xss == "undefined"))
            checks.append((f"{label}: DOM img 요소 0개 (실제 {imgs})", imgs == 0))
            checks.append((f"{label}: DOM 어디에도 onerror 문자열 없음", not bad))
    finally:
        ctx.close()
    return verdict(checks)


@case(7, "채팅 80자 초과 입력 제한, 1초 쿨다운")
def t07(browser, col):
    ctx, a, b = make_pair(browser, col)
    checks = []
    try:
        signup(a, new_id())
        create_char(a, new_nick())
        signup(b, new_id())
        create_char(b, new_nick())
        a_nick = state(a)["me"]["nickname"]
        wait_until(lambda: find_player(b, a_nick), 6)

        a.get_by_test_id("chat-input").click()
        a.keyboard.type("가" * 81)
        n = len(a.get_by_test_id("chat-input").input_value())
        checks.append((f"81자 입력 시 입력칸 80자에서 멈춤 (실제 {n})", n == 80))
        checks.append(("글자 수 카운터 80/80", a.get_by_test_id("chat-counter").inner_text().strip() == "80/80"))
        a.keyboard.press("Enter")
        got = wait_until(lambda: len(find_player(b, a_nick)["lastChat"] or "") == 80, 4)
        checks.append(("80자 메시지 B에 전달", bool(got)))

        send_chat_text = "두번째"
        a.keyboard.type(send_chat_text)
        a.keyboard.press("Enter")
        hint = a.get_by_test_id("chat-hint")
        expect(hint).to_be_visible(timeout=1000)
        checks.append(("쿨다운 힌트 문구", hint.inner_text().strip() == MSG_COOLDOWN))
        checks.append(("쿨다운 중 입력 유지", a.get_by_test_id("chat-input").input_value() == send_chat_text))
        checks.append(("쿨다운 중 전송 버튼 비활성", a.get_by_test_id("chat-send").is_disabled()))
        time.sleep(0.2)
        checks.append(("쿨다운 중 B에 미전달", find_player(b, a_nick)["lastChat"] != send_chat_text))

        time.sleep(1.1)
        a.keyboard.press("Enter")
        got2 = wait_until(lambda: find_player(b, a_nick)["lastChat"] == send_chat_text, 4)
        checks.append(("쿨다운 종료 후 전송 성공", bool(got2)))
    finally:
        ctx.close()
    return verdict(checks)


@case(8, "탭 닫기 -> 다른 탭에서 플레이어 제거 (6초 이내)")
def t08(browser, col):
    ctx, a, b = make_pair(browser, col)
    checks = []
    try:
        signup(a, new_id())
        a_nick = new_nick()
        create_char(a, a_nick)
        signup(b, new_id())
        b_nick = new_nick()
        create_char(b, b_nick)
        wait_until(lambda: find_player(a, b_nick), 6)
        t0 = time.time()
        b.close()
        gone = wait_until(lambda: find_player(a, b_nick) is None, 8, interval=0.05)
        elapsed = time.time() - t0
        checks.append((f"B 탭 닫기 후 A에서 제거 (경과 {elapsed:.2f}s, 기준 6s 이내)", bool(gone) and elapsed <= 6.0))
        checks.append(("접속 중 1명으로 감소", wait_until(lambda: a.get_by_test_id("player-count").inner_text().strip() == "접속 중 1명", 3) is not None))
    finally:
        ctx.close()
    return verdict(checks)


@case(9, "로그아웃 -> 로그인 화면, 다른 탭에서 제거")
def t09(browser, col):
    ctx, a, b = make_pair(browser, col)
    checks = []
    try:
        signup(a, new_id())
        a_nick = new_nick()
        create_char(a, a_nick)
        signup(b, new_id())
        b_nick = new_nick()
        create_char(b, b_nick)
        wait_until(lambda: find_player(a, b_nick), 6)
        t0 = time.time()
        b.get_by_test_id("logout").click()
        wait_screen(b, SCREEN_LOGIN)
        checks.append(("로그아웃 후 로그인 화면", screen(b) == SCREEN_LOGIN))
        gone = wait_until(lambda: find_player(a, b_nick) is None, 8, interval=0.05)
        elapsed = time.time() - t0
        checks.append((f"A 화면에서 B 제거 (경과 {elapsed:.2f}s, 기준 6s 이내)", bool(gone) and elapsed <= 6.0))
        checks.append(("로그아웃 후 세션 제거(새로고침해도 로그인 화면)", (b.reload() or True) and wait_until(lambda: screen(b) == SCREEN_LOGIN, 6) is not None))
    finally:
        ctx.close()
    return verdict(checks)


@case(11, "모바일 360x640: 가로 스크롤 없음, 캔버스 360x508, 터치 버튼으로 이동")
def t11(browser, col):
    ctx = browser.new_context(viewport={"width": 360, "height": 640}, is_mobile=True, has_touch=True, device_scale_factor=2)
    page = open_page(ctx, col, "M")
    checks = []

    def no_hscroll(pg):
        return pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")

    try:
        checks.append(("로그인 화면 가로 스크롤 없음", no_hscroll(page)))
        signup(page, new_id())
        checks.append(("생성 화면 가로 스크롤 없음", no_hscroll(page)))
        create_char(page, new_nick())
        checks.append(("게임 화면 가로 스크롤 없음", no_hscroll(page)))
        canvas_box = page.get_by_test_id("game-canvas").bounding_box()
        # 사이클 3 (frontend 2장, style-guide v3 6장): 모바일 캔버스 = 화면 폭 전체, 세로 = 화면 높이 - 조작 영역 132
        exp_w = math.floor(360 / 2) * 2
        exp_h = math.floor((640 - 132) / 2) * 2  # 508
        checks.append((f"캔버스 {exp_w}x{exp_h} (세로 = 640 - 조작 영역 132) (실제 {canvas_box['width']:.0f}x{canvas_box['height']:.0f})",
                       abs(canvas_box["width"] - exp_w) <= 1 and abs(canvas_box["height"] - exp_h) <= 1))
        for tid in ("move-left", "move-right"):
            bb = page.get_by_test_id(tid).bounding_box()
            checks.append((f"{tid} 높이 44px 이상 (실제 {bb['height']:.0f})", bb["height"] >= 44))
        chat_bb = page.get_by_test_id("chat-input").bounding_box()
        checks.append(("채팅 입력이 화면 안에 보임", chat_bb["y"] + chat_bb["height"] <= 640))

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
        checks.append((f"터치 1초 홀드로 오른쪽 이동 (dx={dx:.0f}px, 기대 약 160)", dx >= 100))
        checks.append(("이동 후에도 가로 스크롤 없음", no_hscroll(page)))
    finally:
        ctx.close()
    return verdict(checks)


@case(12, "로그인/로그아웃 3회 반복 후 리소스 누수 징후 없음 (BroadcastChannel, interval, rAF, 화면 DOM)")
def t12(browser, col):
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
    ctx = browser.new_context()
    ctx.add_init_script(init)
    page = open_page(ctx, col, "L")
    checks = []
    uid = new_id()

    def counters(pg):
        return pg.evaluate("""() => { const L = window.__qaLeak;
          return { bcLive: L.bcOpen - L.bcClosed, intervals: L.intervals.size, rafs: L.rafs.size,
                   screens: document.querySelectorAll('.screen').length }; }""")

    try:
        signup(page, uid)
        create_char(page, new_nick())
        time.sleep(0.5)
        c = counters(page)
        checks.append((f"게임 중 기준값 (bc 1, interval 2, rAF 1, screen 1) 실제 {c}",
                       c == {"bcLive": 1, "intervals": 2, "rafs": 1, "screens": 1}))
        for i in range(1, 4):
            logout_game(page)
            time.sleep(0.3)
            c = counters(page)
            checks.append((f"{i}회차 로그아웃 후 잔여 0 (실제 {c})",
                           c["bcLive"] == 0 and c["intervals"] == 0 and c["rafs"] == 0 and c["screens"] == 1))
            login(page, uid)
            wait_screen(page, SCREEN_GAME)
            wait_connected(page)
            time.sleep(0.5)
            c = counters(page)
            checks.append((f"{i}회차 재로그인 후 게임 기준값 (실제 {c})",
                           c == {"bcLive": 1, "intervals": 2, "rafs": 1, "screens": 1}))
        logout_game(page)
        time.sleep(0.3)
        c = counters(page)
        checks.append(("3회 반복 후 최종 잔여 0", c["bcLive"] == 0 and c["intervals"] == 0 and c["rafs"] == 0))
    finally:
        ctx.close()
    result = verdict(checks)
    if result[0] == "PASS":
        result = ("PASS", result[1] + " / 미측정: 리스너 개수, JS 힙(브라우저 DevTools 필요)")
    return result


# ---------------------------------------------------------------------------
# 픽셀/레이아웃 (사이클 3: 블록 아트, ARCHITECTURE "블록 아트 계약")
# ---------------------------------------------------------------------------
# 캔버스 글자(닉네임 라벨, 말풍선)는 fillText로 그린다. 위치와 정렬을 읽으려고 호출을 가로챈다.
# 그리기 동작은 바꾸지 않는다. 기록은 window.__qaFill[글자] = {x, y, w, align} (CSS px, 캔버스 기준).
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

# 검사 전 HUD 숨김 (DOM 글자 안티에일리어싱이 캔버스 스크린샷에 섞이지 않게). 레이아웃은 그대로 둔다.
HIDE_OVERLAY_JS = """() => {
  for (const s of ['.hud', '.hud-banner', '.chat-float', '.hint-desktop', '[data-testid="mode-badge"]']) {
    document.querySelectorAll(s).forEach((e) => { e.style.visibility = 'hidden'; });
  }
}"""

# LOCAL MODE 배지와 겹치는 "잎" 요소 찾기. 배지의 조상/자손은 제외.
# 제외: 게임 캔버스(HUD는 캔버스 위에 겹치는 설계, game.md 1장), 장식 배경 .bk-world(aria-hidden, 패널 뒤, frontend 6장 16번)
BADGE_JS = """
() => {
  const badge = document.querySelector('[data-testid="mode-badge"]');
  if (!badge) return { missing: true, hits: [] };
  const vis = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return false;
    const cs = getComputedStyle(el);
    return cs.visibility !== 'hidden' && cs.display !== 'none' && parseFloat(cs.opacity) > 0;
  };
  const br = badge.getBoundingClientRect();
  const hits = [];
  for (const el of document.body.querySelectorAll('*')) {
    if (el === badge || el.contains(badge) || badge.contains(el)) continue;
    if (el.closest('[data-testid="world-bg"]')) continue;
    if (el.getAttribute('data-testid') === 'game-canvas') continue;
    if (el.children.length > 0 && el.tagName !== 'CANVAS') continue;
    if (!vis(el)) continue;
    const r = el.getBoundingClientRect();
    const ix = Math.min(r.right, br.right) - Math.max(r.left, br.left);
    const iy = Math.min(r.bottom, br.bottom) - Math.max(r.top, br.top);
    if (ix > 0.5 && iy > 0.5) {
      const name = el.getAttribute('data-testid') || el.tagName.toLowerCase();
      hits.push(name + ' "' + (el.textContent || '').trim().slice(0, 16) + '"');
    }
  }
  return { missing: false, badge: [br.x, br.y, br.width, br.height], hits };
}
"""

PALETTE_COLORS = 42  # style-guide 1장: 아트는 팔레트 42색만 쓴다


def canvas_layout(pg):
    return pg.evaluate("""() => {
      const c = document.querySelector('[data-testid="game-canvas"]');
      if (!c) return null;
      const r = c.getBoundingClientRect();
      return { cssW: r.width, cssH: r.height, bufW: c.width, bufH: c.height, dpr: window.devicePixelRatio };
    }""")


def canvas_text_boxes(pg):
    """캔버스에 그린 글자의 CSS px 마스크 사각형. 닉네임 라벨 박스(테두리 포함: 글자 기준 y-6 ~ y+18)를 덮는다.
    말풍선(left 정렬)은 이 검사 장면에 없다(항목 13은 채팅을 보내지 않는다)."""
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
    """캔버스 스크린샷(PNG bytes)에서 아트 블록(k x k 디바이스 px) 균일성과 전환 위치를 검사한다.
    글자/라벨 영역(boxes_css)은 계약상 화면 해상도이므로 제외한다. 상단 band_frac 밴드는 글자가 없는 하늘/산 영역."""
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
    # 색이 바뀌는 경계가 k의 배수 위치에만 있어야 블록이 정사각형이고 흐림(보간)이 없다
    cx = (band[:, 1:] != band[:, :-1]).any(axis=2) & ~(m[:, 1:] | m[:, :-1])
    cy = (band[1:] != band[:-1]).any(axis=2) & ~(m[1:] | m[:-1])
    mis_x = int(cx[:, np.arange(1, W) % k != 0].sum())
    mis_y = int(cy[np.arange(1, h_px) % k != 0, :].sum())
    return {
        "size": (W, H),
        "blocks": int(uniform.size),
        "bad_outside": int(np.count_nonzero(~uniform & ~bmask)),
        "band_bad": int(np.count_nonzero(~uniform[:band_rows] & ~bmask[:band_rows])),
        "mis_x": mis_x,
        "mis_y": mis_y,
        "band_colors": int(len(np.unique(band[~m].reshape(-1, 3), axis=0))),
    }


@case(13, "픽셀 선명도: 캔버스 스크린샷에서 아트 픽셀이 배율 P의 균일 정사각 블록 (흐림/비정렬 없음, HUD 숨김 + 라벨 박스 마스크)")
def t13(browser, col):
    try:
        import numpy  # noqa: F401
        import PIL  # noqa: F401
    except ImportError as e:
        return ("UNVERIFIED", f"numpy/Pillow가 없어 픽셀 검사를 하지 못함: {e}")
    # (이름, 뷰포트 W, H, devicePixelRatio, 모바일 여부, 기대 P). P는 style-guide 6.1 (1600x900 이상이면 3)
    configs = [
        ("데스크톱 1280x800 dpr1", 1280, 800, 1, False, 2),
        ("큰 데스크톱 1920x1080 dpr1", 1920, 1080, 1, False, 3),
        ("모바일 360x640 dpr2", 360, 640, 2, True, 2),
    ]
    checks = []
    for label, vw, vh, dsf, mob, P in configs:
        ctx = browser.new_context(viewport={"width": vw, "height": vh}, device_scale_factor=dsf,
                                  is_mobile=mob, has_touch=mob)
        ctx.add_init_script(FILLTEXT_HOOK)
        try:
            page = open_page(ctx, col, label)
            signup(page, new_id())
            create_char(page, new_nick())
            time.sleep(0.6)
            lay = canvas_layout(page)
            page.evaluate(HIDE_OVERLAY_JS)
            time.sleep(0.1)
            png = page.get_by_test_id("game-canvas").screenshot()
            boxes = canvas_text_boxes(page)
            res = pixel_check(png, P * dsf, boxes, dsf)
        finally:
            ctx.close()
        k = P * dsf
        if "error" in res:
            checks.append((f"{label}: {res['error']}", False))
            continue
        checks += [
            (f"{label}: 스크린샷 {res['size'][0]}x{res['size'][1]} = 캔버스 버퍼 {lay['bufW']}x{lay['bufH']}",
             tuple(res["size"]) == (lay["bufW"], lay["bufH"])),
            (f"{label}: 블록 {k}px(P={P} x dpr {dsf}) 격자 위에서만 색 전환 (비정렬 {res['mis_x'] + res['mis_y']}건)",
             res["mis_x"] == 0 and res["mis_y"] == 0),
            (f"{label}: 글자/라벨 영역 밖 블록 전부 균일 (불균일 {res['bad_outside']}/{res['blocks']})",
             res["bad_outside"] == 0),
            (f"{label}: 상단 35% 밴드 블록 균일 (불균일 {res['band_bad']})", res["band_bad"] == 0),
            (f"{label}: 상단 밴드 색 {res['band_colors']}가지 (팔레트 {PALETTE_COLORS}색 이내, 흐림이면 급증)",
             res["band_colors"] <= PALETTE_COLORS),
        ]
    return verdict(checks)


def share(samples, idx, pred, t_min):
    """t_min 이후 샘플 중 pred(값)을 만족하는 비율."""
    late = [s for s in samples if s[0] >= t_min]
    if not late:
        return 0.0
    return sum(1 for s in late if pred(s[idx])) / len(late)


def walk_frames(samples, t_min=0.0):
    return {s[2] for s in samples if s[0] >= t_min and s[1] == "walk"}


def sample_move(a, b, key, secs, a_nick):
    """key를 secs 동안 누르며 로컬(a)과 원격(b) 화면의 anim/frame/dir을 기록한다.
    샘플 = (경과 초, anim, frame, dir)"""
    loc, rem = [], []
    a.keyboard.down(key)
    t0 = time.time()
    while time.time() - t0 < secs:
        t = time.time() - t0
        m = state(a)["me"]
        loc.append((t, m["anim"], m["frame"], m["dir"]))
        p = find_player(b, a_nick)
        if p is not None:
            rem.append((t, p["anim"], p["frame"], p["dir"]))
        time.sleep(0.03)
    a.keyboard.up(key)
    return loc, rem


def wait_idle(a, b, a_nick, timeout=1.5):
    t0 = time.time()
    li = ri = None
    while time.time() - t0 < timeout and (li is None or ri is None):
        if li is None and state(a)["me"]["anim"] == "idle":
            li = time.time() - t0
        p = find_player(b, a_nick)
        if ri is None and p and p["anim"] == "idle":
            ri = time.time() - t0
        time.sleep(0.02)
    return li, ri


@case(14, "애니메이션: 이동 중 walk(frame 2..5), 정지 후 idle(frame 1), 왼쪽 이동 dir=left (로컬과 원격 탭 모두)")
def t14(browser, col):
    ctx, a, b = make_pair(browser, col)
    checks = []
    try:
        a_nick, b_nick = new_nick(), new_nick()
        signup(a, new_id())
        create_char(a, a_nick)
        signup(b, new_id())
        create_char(b, b_nick)
        wait_until(lambda: find_player(b, a_nick) and find_player(a, b_nick), 6)
        time.sleep(0.6)
        me_a = state(a)["me"]
        checks.append((f"정지 상태 로컬 anim=idle, frame=1 (실제 {me_a['anim']}, {me_a['frame']})",
                       me_a["anim"] == "idle" and me_a["frame"] == 1))
        rp = find_player(b, a_nick)
        checks.append((f"정지 상태 원격 anim=idle, frame=1 (실제 {rp and rp['anim']}, {rp and rp['frame']})",
                       rp is not None and rp["anim"] == "idle" and rp["frame"] == 1))

        # 오른쪽 이동 0.9초
        loc, rem = sample_move(a, b, "ArrowRight", 0.9, a_nick)
        lf = share(loc, 1, lambda v: v == "walk", 0.15)
        rf = share(rem, 1, lambda v: v == "walk", 0.3)
        checks.append((f"오른쪽 이동: 로컬 anim=walk 비율 {lf:.2f} (0.15s 이후, 기준 0.95 이상)", lf >= 0.95))
        checks.append((f"오른쪽 이동: 로컬 walk 프레임 {sorted(walk_frames(loc))} = 2..5 이하, dir 오른쪽",
                       walk_frames(loc, 0.15) <= WALK_FRAMES and share(loc, 3, lambda v: v == "right", 0.15) == 1.0))
        checks.append((f"오른쪽 이동: 원격 anim=walk 비율 {rf:.2f} (0.3s 이후, 기준 0.85 이상)", rf >= 0.85))
        checks.append((f"오른쪽 이동: 원격 walk 프레임 {sorted(walk_frames(rem, 0.3))} = 2..5 이하, dir 오른쪽",
                       walk_frames(rem, 0.3) <= WALK_FRAMES and walk_frames(rem, 0.3) != set() and share(rem, 3, lambda v: v == "right", 0.3) == 1.0))

        li, ri = wait_idle(a, b, a_nick)
        checks.append((f"정지 후 로컬 idle 전환 {li if li is None else round(li, 3)}s (기준 0.3s 이내)", li is not None and li <= 0.3))
        checks.append((f"정지 후 원격 idle 전환 {ri if ri is None else round(ri, 3)}s (기준 0.5s 이내)", ri is not None and ri <= 0.5))
        me_a = state(a)["me"]
        rp = find_player(b, a_nick)
        checks.append((f"정지 후 로컬 frame=1 (실제 {me_a['frame']})", me_a["anim"] == "idle" and me_a["frame"] == 1))
        checks.append((f"정지 후 원격 frame=1 (실제 {rp and rp['frame']})", rp is not None and rp["anim"] == "idle" and rp["frame"] == 1))

        # 왼쪽 이동 0.6초: dir = left
        loc, rem = sample_move(a, b, "ArrowLeft", 0.6, a_nick)
        checks.append((f"왼쪽 이동: 로컬 dir=left 비율 {share(loc, 3, lambda v: v == 'left', 0.15):.2f} (기준 1.0)",
                       share(loc, 3, lambda v: v == "left", 0.15) == 1.0))
        rl = share(rem, 3, lambda v: v == "left", 0.3)
        checks.append((f"왼쪽 이동: 원격 dir=left 비율 {rl:.2f} (0.3s 이후, 기준 0.85 이상)", rl >= 0.85))
        checks.append((f"왼쪽 이동: 원격 walk 프레임 {sorted(walk_frames(rem, 0.3))} = 2..5 이하",
                       walk_frames(rem, 0.3) <= WALK_FRAMES and walk_frames(rem, 0.3) != set()))
        li, ri = wait_idle(a, b, a_nick)
        rp = find_player(b, a_nick)
        checks.append((f"왼쪽 정지 후 원격 idle(frame 1) 유지, dir=left 유지 (frame {rp and rp['frame']}, dir {rp and rp['dir']})",
                       rp is not None and rp["anim"] == "idle" and rp["frame"] == 1 and rp["dir"] == "left"))
    finally:
        ctx.close()
    return verdict(checks)


@case(15, "에셋 로드: 404/실패 0, manifest 2종 + outline 200, 아바타 레이어 43, 맵 5, PNG 고유 응답 48")
def t15(browser, col):
    ctx = browser.new_context()
    page = ctx.new_page()
    col.attach(page, "AS")
    ev = {"resp": [], "failed": [], "warn": []}
    page.on("response", lambda r: ev["resp"].append((r.status, r.url)) if "/assets/" in r.url else None)
    page.on("requestfailed", lambda r: ev["failed"].append(r.url) if "/assets/" in r.url else None)
    page.on("console", lambda m: ev["warn"].append(m.text) if m.type == "warning" else None)
    checks = []
    try:
        page.goto(BASE)
        wait_until(lambda: screen(page) in (SCREEN_LOGIN, SCREEN_CREATE, SCREEN_GAME), 10)
        signup(page, new_id())
        create_char(page, new_nick())
        time.sleep(1.0)
        st = state(page)
        bad = [(s, u) for s, u in ev["resp"] if s >= 400]
        png_ok = {u for s, u in ev["resp"] if s == 200 and u.endswith(".png")}
        checks.append((f"assets 응답 4xx/5xx 0건 (전체 {len(ev['resp'])}건, 실패 {bad[:3]})", not bad))
        checks.append((f"assets 요청 실패(requestfailed) 0건 (실제 {len(ev['failed'])})", not ev["failed"]))
        for m in ("avatar/manifest.json", "avatar/outline.json", "map/manifest.json"):
            checks.append((f"{m} 200 응답", any(s == 200 and u.endswith(m) for s, u in ev["resp"])))
        a = st.get("assets") or {}
        checks.append((f"아바타 로드: source=manifest, 레이어 43 (실제 {a.get('source')}, images {a.get('images')}, total {a.get('imageTotal')})",
                       a.get("source") == "manifest" and a.get("images") == 43 and a.get("imageTotal") == 43))
        checks.append((f"맵 로드: mapLayers=5, background=True (실제 {a.get('mapLayers')}, {a.get('background')})",
                       a.get("mapLayers") == 5 and a.get("background") is True))
        checks.append((f"PNG 고유 200 응답 {len(png_ok)}건 (기대 48 = 아바타 43 + 맵 5)", len(png_ok) == 48))
        checks.append((f"콘솔 경고 0건 (실제 {len(ev['warn'])}: {ev['warn'][:2]})", not ev["warn"]))
    finally:
        ctx.close()
    return verdict(checks)


def label_check(pg, nick, prefix):
    lay = canvas_layout(pg)
    rec = pg.evaluate("(n) => (window.__qaFill || {})[n] || null", nick)
    if not rec:
        return [(f"{prefix}: 닉네임 라벨 그리기 기록 없음", False)]
    half = rec["w"] / 2 + 8  # 라벨 박스 = 글자 폭 + 12, 테두리 2px 포함
    l, r = rec["x"] - half, rec["x"] + half
    t, b = rec["y"] - 6, rec["y"] + 18  # 기준선(fillText y) 기준 테두리 포함 위/아래
    ok = l >= 0 and r <= lay["cssW"] and t >= 0 and b <= lay["cssH"]
    return [(f"{prefix}: 닉네임 라벨이 캔버스 안 (x {l:.0f}~{r:.0f}, y {t:.0f}~{b:.0f} / 캔버스 {lay['cssW']:.0f}x{lay['cssH']:.0f})", ok)]


def badge_check(pg, prefix):
    res = pg.evaluate(BADGE_JS)
    if res.get("missing"):
        return [(f"{prefix}: LOCAL MODE 배지 존재", False)]
    hits = res["hits"]
    return [(f"{prefix}: LOCAL MODE 배지와 겹치는 요소 0개 (실제 {len(hits)}: {hits[:4]})", not hits)]


@case(16, "레이아웃: 1280x800 / 1920x1080 / 360x640에서 가로 스크롤 없음, LOCAL MODE 비겹침, 닉네임 라벨 캔버스 안, 모바일 하단 빈 공간 없음")
def t16(browser, col):
    checks = []
    viewports = [("1280x800", 1280, 800, 1, False), ("1920x1080", 1920, 1080, 1, False), ("360x640", 360, 640, 2, True)]
    for tag, vw, vh, dsf, mob in viewports:
        ctx = browser.new_context(viewport={"width": vw, "height": vh}, device_scale_factor=dsf,
                                  is_mobile=mob, has_touch=mob)
        ctx.add_init_script(FILLTEXT_HOOK)
        try:
            page = open_page(ctx, col, tag)
            checks.append((f"[{tag}] 로그인: 가로 스크롤 없음", page.evaluate(
                "document.documentElement.scrollWidth <= document.documentElement.clientWidth")))
            checks += badge_check(page, f"[{tag}] 로그인")
            signup(page, new_id())
            checks.append((f"[{tag}] 생성: 가로 스크롤 없음", page.evaluate(
                "document.documentElement.scrollWidth <= document.documentElement.clientWidth")))
            checks += badge_check(page, f"[{tag}] 생성")
            nick = new_nick()
            create_char(page, nick)
            time.sleep(0.4)
            checks.append((f"[{tag}] 게임: 가로 스크롤 없음", page.evaluate(
                "document.documentElement.scrollWidth <= document.documentElement.clientWidth")))
            checks += badge_check(page, f"[{tag}] 게임")
            checks += label_check(page, nick, f"[{tag}] 게임")
            if mob:
                send = page.get_by_test_id("chat-send").bounding_box()
                gap = vh - (send["y"] + send["height"])
                checks.append((f"[{tag}] 하단 빈 공간 없음 (채팅 버튼 아래 여백 {gap:.0f}px, 기준 12px 이하)", gap <= 12))
        finally:
            ctx.close()
    return verdict(checks)


def repo_tree(base):
    """assets/avatar, assets/map 아래 모든 파일의 sha256 (경로 -> 해시)."""
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
    dst = SCRATCH / "qa3-copies" / name
    if dst.exists():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    return dst


@case(17, "에셋 빌드 재현성: 저장소 사본(산출물 삭제 후)에서 build.py 실행 -> assets/avatar, assets/map이 원본과 바이트 동일 (2회 결정성)")
def t17(browser, col):
    before = repo_tree(ROOT)
    checks = []
    png_repo = sorted(k for k in before if k.endswith(".png"))
    checks.append((f"원본 PNG 개수 = 48 (아바타 43 + 맵 5) (실제 {len(png_repo)})", len(png_repo) == 48))

    def build_copy(name):
        dst = copy_repo(name)
        for sub in ("avatar", "map"):
            shutil.rmtree(dst / "assets" / sub)  # 산출물을 지우고 소스만으로 다시 만들게 한다
        p = subprocess.run([sys.executable, "-B", str(dst / "assets" / "_src" / "block" / "build.py")],
                           cwd=dst, capture_output=True, text=True, timeout=300)
        return dst, p

    d1, p1 = build_copy("build-1")
    last1 = (p1.stdout.strip().splitlines() or [p1.stderr.strip()[-160:]])[-1]
    checks.append((f"build.py 종료 코드 0 ('{last1}')", p1.returncode == 0))
    t1 = repo_tree(d1)
    checks.append((f"생성 파일 집합 = 원본 ({len(t1)}개, 누락 {sorted(set(before) - set(t1))[:3]}, 여분 {sorted(set(t1) - set(before))[:3]})",
                    set(t1) == set(before)))
    diff = [k for k in before if t1.get(k) != before[k]]
    checks.append((f"avatar/map 전체 바이트 동일 {len(before) - len(diff)}/{len(before)} (불일치 {diff[:4]})", not diff))

    d2, p2 = build_copy("build-2")
    t2 = repo_tree(d2)
    checks.append(("두 번째 독립 빌드도 첫 번째와 바이트 동일 (결정적)", p2.returncode == 0 and t2 == t1))

    after = repo_tree(ROOT)
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    checks.append((f"저장소 원본 assets 전후 해시 동일 (변경 {len(changed)}건: {changed[:3]})", not changed))
    return verdict(checks)


@case(18, "정적 검사 스크립트: assets/_src/block/check.py 통과 (저장소 사본에서 실행)")
def t18(browser, col):
    dst = copy_repo("check")
    p = subprocess.run([sys.executable, "-B", str(dst / "assets" / "_src" / "block" / "check.py")],
                       cwd=dst, capture_output=True, text=True, timeout=300)
    tail = " / ".join(p.stdout.strip().splitlines()[-3:]) or p.stderr.strip()[-200:]
    checks = [
        (f"check.py 종료 코드 0 (출력 끝: {tail})", p.returncode == 0),
        ("출력에 'ALL CHECKS PASSED'", "ALL CHECKS PASSED" in p.stdout),
    ]
    return verdict(checks)


@case(19, "캐릭터 생성 화면(1280x800): 탭 7개, 슬롯 선택 반영, 프리셋 6종, 앞/옆/뒤, 걷기 미리보기, 키보드")
def t19(browser, col):
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    page = open_page(ctx, col, "C")
    checks = []
    try:
        signup(page, new_id())
        checks.append(("생성 화면 매니페스트 로드 (ready)", wait_create_ready(page) is not None))
        cs = create_state(page)
        checks.append((f"초기 값 = manifest 첫 항목 7키 {cs.get('avatar')}", cs.get("avatar") == DEFAULTS))

        tabs = page.eval_on_selector_all("[role=tab]", "els => els.map(e => e.getAttribute('data-testid'))")
        checks.append((f"카테고리 탭 7개 {tabs}", sorted(tabs) == sorted(f"tab-{p}" for p in CATEGORY_TABS)))
        for p in CATEGORY_TABS:
            page.get_by_test_id(f"tab-{p}").click()
            sel = page.get_by_test_id(f"tab-{p}").get_attribute("aria-selected")
            n = page.eval_on_selector_all("#slot-grid .bk-slot", "els => els.length")
            checks.append((f"탭 {p}: 선택 표시 + 슬롯 {n}개 = manifest {len(PARTS[p])}", sel == "true" and n == len(PARTS[p])))

        for p, v in PICK.items():
            checks.append((f"계약 id 존재: {p}={v}", v in PARTS[p]))
        for p, v in PICK.items():
            pick_slot(page, p, v)
        got = create_state(page)["avatar"]
        checks.append((f"슬롯 선택 7파츠가 미리보기 상태에 반영 {got}", got == PICK))

        for i, pr in enumerate(MANIFEST["presets"]):
            page.get_by_test_id(f"preset-{i}").click()
            got = create_state(page)["avatar"]
            checks.append((f"프리셋 {i} '{pr['label']}' 적용 (7파츠 일치)", got == pr["avatar"]))
        tab = create_state(page)["tab"]
        checks.append(("프리셋 적용 후 현재 탭 슬롯 표시가 값을 따름",
                       page.get_by_test_id(f"slot-{tab}-{got[tab]}").get_attribute("aria-checked") == "true"))
        checks.append(("프리셋 버튼 정확히 6개", page.get_by_test_id("preset-6").count() == 0
                       and len(MANIFEST["presets"]) == 6))

        page.get_by_test_id("view-side").click()
        cs = create_state(page)
        checks.append((f"옆: view=side, frame=1, 걷기 꺼짐 (실제 {cs.get('view')}, {cs.get('frame')}, {cs.get('walking')})",
                       cs.get("view") == "side" and cs.get("frame") == 1 and cs.get("walking") is False))
        page.get_by_test_id("view-back").click()
        cs = create_state(page)
        checks.append((f"뒤: view=back, frame=6 (실제 {cs.get('view')}, {cs.get('frame')})", cs.get("view") == "back" and cs.get("frame") == 6))
        page.get_by_test_id("view-front").click()
        cs = create_state(page)
        checks.append((f"앞: view=front, frame=0, aria-checked (실제 {cs.get('view')}, {cs.get('frame')})",
                       cs.get("view") == "front" and cs.get("frame") == 0
                       and page.get_by_test_id("view-front").get_attribute("aria-checked") == "true"))

        page.get_by_test_id("preview-walk").click()
        time.sleep(0.05)
        cs = create_state(page)
        checks.append(("걷기 켜짐: aria-pressed=true, view=side, walking=true",
                       cs.get("walking") is True and cs.get("view") == "side"
                       and page.get_by_test_id("preview-walk").get_attribute("aria-pressed") == "true"))
        frames = set()
        t0 = time.time()
        while time.time() - t0 < 1.2:
            frames.add(create_state(page).get("frame"))
            time.sleep(0.03)
        checks.append((f"걷기 프레임 {sorted(f for f in frames if f is not None)} = 2..5 순환", frames <= WALK_FRAMES | {None} and len(frames - {None}) >= 3))
        page.get_by_test_id("view-front").click()
        cs = create_state(page)
        checks.append(("앞 누르면 걷기 꺼짐 (walking=false, frame=0)", cs.get("walking") is False and cs.get("frame") == 0))

        # 키보드: 탭 방향키/Home/End (activeTab 기준), 슬롯 방향키
        page.get_by_test_id("tab-skin").click()
        page.keyboard.press("ArrowRight")
        checks.append(("탭 키보드: ArrowRight -> face", create_state(page).get("tab") == "face"))
        page.keyboard.press("End")
        checks.append(("탭 키보드: End -> shoes", create_state(page).get("tab") == "shoes"))
        page.keyboard.press("Home")
        checks.append(("탭 키보드: Home -> skin", create_state(page).get("tab") == "skin"))
        page.get_by_test_id("tab-hair").click()
        ids = PARTS["hair"]
        page.get_by_test_id(f"slot-hair-{ids[0]}").click()  # 앞 단계에서 머리를 바꿨으므로 시작점을 첫 항목으로 맞춘다
        page.keyboard.press("ArrowRight")
        checks.append((f"슬롯 키보드: ArrowRight -> {ids[1]}", create_state(page)["avatar"]["hair"] == ids[1]))
        page.keyboard.press("End")
        checks.append((f"슬롯 키보드: End -> {ids[-1]}", create_state(page)["avatar"]["hair"] == ids[-1]))
        page.keyboard.press("Home")
        checks.append((f"슬롯 키보드: Home -> {ids[0]}", create_state(page)["avatar"]["hair"] == ids[0]))
    finally:
        ctx.close()
    return verdict(checks)


@case(20, "저장 avatar: 정확히 7키, 선택 값과 일치 (getState와 localStorage 원본 모두, 선택 없음 = 기본값)")
def t20(browser, col):
    checks = []
    for label, pick, expect in (("선택 값", PICK, PICK), ("기본값(선택 없음)", {}, DEFAULTS)):
        ctx = browser.new_context()
        page = open_page(ctx, col, label)
        try:
            signup(page, new_id())
            wait_create_ready(page)
            for p, v in pick.items():
                pick_slot(page, p, v)
            create_char(page, new_nick())
            me = state(page)["me"]
            raw = page.evaluate("(k) => localStorage.getItem(k)", LS_CHARACTERS)
            stored = json.loads(raw)[me["user_id"]]["avatar"]
            checks.append((f"[{label}] getState.me.avatar == 기대값", me["avatar"] == expect))
            checks.append((f"[{label}] localStorage avatar 키 정확히 7개 {sorted(stored)}", sorted(stored) == sorted(PART_KEYS7)))
            checks.append((f"[{label}] localStorage 값 == 기대값", stored == expect))
            checks.append((f"[{label}] hat 키 값 = {expect['hat']}", stored.get("hat") == expect["hat"]))
        finally:
            ctx.close()
    return verdict(checks)


@case(21, "호환: 사이클 1 저장값(5키, eyes, 옛 id) -> 새로고침 시 에러 없이 게임, 7키 정규화, 저장값 유지, Presence 옛 형식 정규화")
def t21(browser, col):
    ctx = browser.new_context()
    page = open_page(ctx, col, "K")
    checks = []
    try:
        signup(page, new_id())
        create_char(page, new_nick())
        me0 = state(page)["me"]
        uid, nick = me0["user_id"], me0["nickname"]
        err0 = len(col.console_errors)
        page.evaluate("""([key, uid, nick, avatar]) => {
            const all = JSON.parse(localStorage.getItem(key) || '{}');
            all[uid] = { user_id: uid, nickname: nick, avatar: avatar, created_at: new Date().toISOString() };
            localStorage.setItem(key, JSON.stringify(all));
        }""", [LS_CHARACTERS, uid, nick, LEGACY_ROW])
        page.reload()
        wait_screen(page, SCREEN_GAME)
        wait_connected(page)
        me = state(page)["me"]
        checks.append(("구 형식 저장값으로 게임 진입 (새로고침)", screen(page) == SCREEN_GAME and me is not None))
        checks.append((f"정규화 7키 = 기대값 (실제 {me and me['avatar']})", me is not None and me["avatar"] == LEGACY_EXPECT))
        stored = json.loads(page.evaluate("(k) => localStorage.getItem(k)", LS_CHARACTERS))[uid]["avatar"]
        checks.append((f"저장값은 읽기만 하고 덮어쓰지 않음 (eyes 키 유지: {stored == LEGACY_ROW})", stored == LEGACY_ROW))

        # 깨진 저장값 -> 파츠 기본값
        broken = {"skin": "<img src=x>", "hair": 5, "eyes": "x y", "top": None}
        page.evaluate("""([key, uid, avatar]) => {
            const all = JSON.parse(localStorage.getItem(key) || '{}');
            all[uid].avatar = avatar;
            localStorage.setItem(key, JSON.stringify(all));
        }""", [LS_CHARACTERS, uid, broken])
        page.reload()
        wait_screen(page, SCREEN_GAME)
        wait_connected(page)
        me = state(page)["me"]
        checks.append((f"깨진 저장값 -> 기본값 7키 (실제 {me and me['avatar']})", me is not None and me["avatar"] == DEFAULTS))

        # Presence로 받는 옛 형식(5키, eyes, 옛 id)과 깨진 값: 수신 측에서 7키로 정규화
        page.evaluate("""() => {
          const bc = new BroadcastChannel('mushroom:map:village');
          const send = (u, n, av) => bc.postMessage({ type: 'presence-join', state: { user_id: u, nickname: n, avatar: av, x: 900, y: 440 } });
          send('legacy-cli-0001', '옛클라', { skin: 'skin-tan', hair: 'hair-spiky-chestnut', eyes: 'eyes-sleepy', top: 'top-vest-green', bottom: 'bottom-jeans-blue' });
          send('broken-cli-0002', '깨진클라', { skin: 'x'.repeat(40), hair: 7 });
          window.__qaBc = bc;
        }""")
        old = wait_until(lambda: find_player(page, "옛클라"), 4)
        exp_old = {"skin": "medium", "hair": "brown-short", "face": "sleepy", "top": "overalls-green",
                   "bottom": "jeans-blue", "shoes": "sneakers-white", "hat": "none"}
        checks.append((f"Presence 옛 5키 -> 7키 정규화 (실제 {old and old['avatar']})", bool(old) and old["avatar"] == exp_old))
        broken_p = wait_until(lambda: find_player(page, "깨진클라"), 4)
        checks.append((f"Presence 깨진 값 -> 기본값 (실제 {broken_p and broken_p['avatar']})",
                       bool(broken_p) and broken_p["avatar"] == DEFAULTS))
        page.evaluate("() => { window.__qaBc && window.__qaBc.close(); }")

        new_err = len(col.console_errors) - err0
        checks.append((f"구 형식/깨진 값 처리 중 콘솔·페이지 에러 0건 (실제 {new_err})", new_err == 0))
    finally:
        ctx.close()
    return verdict(checks)


TITLE_10 = "콘솔 에러 0건 (전체 테스트 동안 수집)"  # 집계는 main()에서 모든 항목 뒤에 수행


# ---------------------------------------------------------------------------
# 스크린샷 모드 (qa3: 게임 화면에는 프리셋 4명과 말풍선)
# ---------------------------------------------------------------------------
def capture(browser, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    col = Collector()
    # 데스크톱 1280x800
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    a = open_page(ctx, col, "A")
    time.sleep(0.6)  # 로그인 화면 페이드 인
    a.screenshot(path=str(out / "login-desktop.png"))
    signup(a, new_id())
    a.get_by_test_id("preset-0").click()
    a.get_by_test_id("tab-hair").click()
    a.get_by_test_id("nickname-input").fill("버섯친구")
    expect(a.get_by_test_id("nickname-status")).to_have_attribute("data-state", "available", timeout=5000)
    time.sleep(0.3)
    a.screenshot(path=str(out / "create-desktop.png"))
    a.get_by_test_id("create-submit").click()
    wait_screen(a, SCREEN_GAME)
    wait_connected(a)
    others = []
    for label, preset, nick in (("B", 1, "분홍소녀"), ("C", 3, "버섯꼬마"), ("D", 4, "하늘마법")):
        pg = open_page(ctx, col, label)
        signup(pg, new_id())
        pg.get_by_test_id(f"preset-{preset}").click()
        pg.get_by_test_id("nickname-input").fill(nick)
        expect(pg.get_by_test_id("nickname-status")).to_have_attribute("data-state", "available", timeout=5000)
        pg.get_by_test_id("create-submit").click()
        wait_screen(pg, SCREEN_GAME)
        wait_connected(pg)
        others.append((pg, nick))
    for _, nick in others:
        wait_until(lambda n=nick: find_player(a, n), 6)
    send_chat(others[0][0], "안녕하세요! 반가워요 :)")
    time.sleep(0.5)
    a.screenshot(path=str(out / "game-desktop.png"))
    ctx.close()

    # 모바일 360x640 (dpr 2)
    ctx = browser.new_context(viewport={"width": 360, "height": 640}, is_mobile=True, has_touch=True, device_scale_factor=2)
    m = open_page(ctx, col, "M")
    time.sleep(0.6)
    m.screenshot(path=str(out / "login-mobile.png"))
    signup(m, new_id())
    m.get_by_test_id("preset-1").click()
    m.get_by_test_id("nickname-input").fill("모바일친구")
    expect(m.get_by_test_id("nickname-status")).to_have_attribute("data-state", "available", timeout=5000)
    time.sleep(0.3)
    m.screenshot(path=str(out / "create-mobile.png"))
    m.screenshot(path=str(out / "create-mobile-full.png"), full_page=True)
    m.get_by_test_id("create-submit").click()
    wait_screen(m, SCREEN_GAME)
    wait_connected(m)
    n = open_page(ctx, col, "N")
    signup(n, new_id())
    n.get_by_test_id("preset-3").click()
    n.get_by_test_id("nickname-input").fill("옆친구")
    expect(n.get_by_test_id("nickname-status")).to_have_attribute("data-state", "available", timeout=5000)
    n.get_by_test_id("create-submit").click()
    wait_screen(n, SCREEN_GAME)
    wait_connected(n)
    wait_until(lambda: find_player(n, "모바일친구"), 6)
    wait_until(lambda: find_player(m, "옆친구"), 6)
    place_near(n, state(m)["me"]["x"], 90)  # 360px 화면 안(±180 월드)에 두 명이 들어오게
    send_chat(n, "모바일 말풍선")
    time.sleep(0.5)
    m.screenshot(path=str(out / "game-mobile.png"))
    ctx.close()
    print(f"스크린샷 저장: {out}")
    for f in sorted(out.glob("*.png")):
        print("  ", f)


# ---------------------------------------------------------------------------
def main():
    global BASE, VERBOSE
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", metavar="DIR", help="스크린샷만 찍는다")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    VERBOSE = args.verbose

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
                    t0 = time.time()
                    try:
                        status, detail = fn(browser, col)
                    except Exception as e:  # 테스트 자체 실패는 FAIL로 기록(재현 근거 포함)
                        status = "FAIL"
                        detail = f"예외: {type(e).__name__}: {str(e).splitlines()[0] if str(e) else ''}"
                        if VERBOSE:
                            detail += "\n" + traceback.format_exc()
                    RESULTS.append((num, title, status, detail))
                    print(f"[{status}] {num}. {title}  ({time.time() - t0:.1f}s)", flush=True)
                    print(f"      {detail}", flush=True)
            finally:
                browser.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()

    # 항목 10: 전체 콘솔 에러
    errs = col.console_errors
    st10 = "PASS" if not errs else "FAIL"
    det10 = f"콘솔/페이지 에러 {len(errs)}건" + ("" if not errs else ": " + " | ".join(errs[:8]))
    RESULTS.append((10, TITLE_10, st10, det10))
    print(f"[{st10}] 10. {TITLE_10}\n      {det10}")
    if col.failed_requests:
        print(f"참고: 실패한 요청 {len(col.failed_requests)}건 (콘솔 에러와 별개)")

    print("\n== 요약 ==")
    for num, title, status, _ in sorted(RESULTS, key=lambda r: r[0]):
        print(f"{num:>4}  {status:<12} {title}")
    fails = [r for r in RESULTS if r[2] == "FAIL"]
    print(f"\nPASS {sum(r[2] == 'PASS' for r in RESULTS)} / FAIL {len(fails)} / UNVERIFIED {sum(r[2] == 'UNVERIFIED' for r in RESULTS)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
