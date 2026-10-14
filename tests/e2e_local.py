#!/usr/bin/env python3
"""버섯마을 local 모드 E2E 테스트 (Python Playwright, Chromium headless).

실행:  python3 tests/e2e_local.py [--shots DIR] [-v]
  --shots DIR : 화면 스크린샷만 찍고 종료 (데스크톱/모바일 로그인, 생성, 게임)
  -v          : 실패 항목의 traceback 출력

- 저장소 루트에서 `python3 -m http.server`를 빈 포트로 띄우고, 끝나면 반드시 종료한다.
- 브라우저는 이미 설치된 Chromium을 쓴다. playwright/pip/npm 설치는 하지 않는다.
- 테스트 훅: window.__mushroom.getState(), data-testid 셀렉터 (docs/handoff/frontend-20261014-client.md 5장).
- 각 실행은 고유한 아이디/닉네임을 쓴다 (실행끼리 충돌하지 않는다).
- 항목별 결과: PASS / FAIL / UNVERIFIED. 실행하지 않은 항목은 PASS로 내지 않는다.
"""
import argparse
import secrets
import socket
import subprocess
import sys
import time
import traceback
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PW = "qa-pass-1234"  # 8자 이상
XSS = "<img src=x onerror=window.__xss=1>"
SCREEN_LOGIN, SCREEN_CREATE, SCREEN_GAME = "login", "create", "game"

# 설계 문서의 오류 문구 (docs/design/screens/login.md, character-create.md, game.md)
MSG_ID_FORMAT = "아이디는 영문 소문자, 숫자, 밑줄(_)을 사용해 4~16자로 입력하세요."
MSG_PW_SHORT = "비밀번호는 8자 이상 입력하세요."
MSG_ID_TAKEN = "이미 사용 중인 아이디입니다."
MSG_LOGIN_FAILED = "아이디 또는 비밀번호가 올바르지 않습니다."
MSG_NICK_TAKEN = "이미 사용 중인 닉네임입니다."
MSG_NICK_FORMAT = "2~12자의 한글, 영문, 숫자만 사용할 수 있습니다."
MSG_COOLDOWN = "1초 뒤에 다시 보낼 수 있습니다."

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


AVATAR = {"skin": "skin-light", "hair": "hair-round-black", "eyes": "eyes-dot",
          "top": "top-tee-red", "bottom": "bottom-shorts-navy"}


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


def login(page, uid, pw=PW):
    page.get_by_test_id("login-id").fill(uid)
    page.get_by_test_id("login-pw").fill(pw)
    page.get_by_test_id("login-submit").click()


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


# ---------------------------------------------------------------------------
# 테스트 항목
# ---------------------------------------------------------------------------
def case(num, title):
    def deco(fn):
        CASES.append((num, title, fn))
        return fn

    return deco


@case(1, "회원가입 -> 캐릭터 생성 -> 게임 진입, 새로고침 시 세션 복구")
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
        page.get_by_test_id("part-next-hair").click()  # 머리 모양을 기본값에서 바꿔 저장 확인
        create_char(page, nick)
        me = state(page)["me"]
        checks.append(("게임 진입, 닉네임 저장", me is not None and me["nickname"] == nick))
        checks.append(("선택한 파츠 저장(hair)", me is not None and me["avatar"]["hair"] == "hair-round-chestnut"))
        checks.append(("본인 목록에 포함", find_player(page, nick) is not None))
        page.reload()
        wait_screen(page, SCREEN_GAME)
        wait_connected(page)
        me2 = state(page)["me"]
        checks.append(("새로고침 후 게임 세션 복구", me2 is not None and me2["nickname"] == nick))
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

        # 중복 아이디: 먼저 계정을 만든 뒤 새 탭에서 같은 아이디로 가입
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

        # 틀린 비밀번호: 로그아웃 후 로그인 화면에서 시도
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


@case(3, "닉네임 중복(대소문자 무시) 거부, 형식 위반 거부")
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

        # 13자 입력은 maxlength 12로 막힌다
        b_nick.fill("")
        b_nick.press_sequentially("가" * 13)
        checks.append(("닉네임 12자 입력 제한(maxlength)", len(b_nick.input_value()) == 12))
        r2 = adapter_call(b, f"b.createCharacter({'<'!r} + 'x1', {AVATAR!r})")
        checks.append(("어댑터: 형식 위반 닉네임 NICK_FORMAT", r2.get("code") == "NICK_FORMAT"))
    finally:
        ctx.close()
    return verdict(checks)


@case(4, "계정당 캐릭터 1개: 생성 후 다시 생성 화면으로 갈 수 없음")
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
        # 화면 전환 기록: body[data-screen] 변화를 모두 기록한다 (reload 이후에 설치)
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

        # 쿨다운: 바로 다음 메시지는 나가지 않고 힌트가 뜬다
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


TITLE_10 = "콘솔 에러 0건 (전체 테스트 동안 수집)"  # 집계는 main()에서 모든 항목 뒤에 수행


@case(11, "모바일 360x640: 가로 스크롤 없음, 터치 버튼으로 이동")
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
        checks.append((f"캔버스 328px 폭 (실제 {canvas_box['width']:.0f}x{canvas_box['height']:.0f})",
                       abs(canvas_box["width"] - 328) <= 1))
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


def verdict(checks):
    failed = [name for name, ok in checks if not ok]
    detail = "; ".join(name for name, ok in checks)
    if failed:
        return ("FAIL", "실패: " + " | ".join(failed) + " || 전체: " + detail)
    return ("PASS", detail)


# ---------------------------------------------------------------------------
# 스크린샷 모드
# ---------------------------------------------------------------------------
def capture(browser, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    col = Collector()
    # 데스크톱
    ctx = browser.new_context(viewport={"width": 1280, "height": 720})
    a = open_page(ctx, col, "A")
    a.screenshot(path=str(out / "desktop-01-login.png"))
    a.get_by_test_id("toggle-signup").click()
    a.screenshot(path=str(out / "desktop-02-signup.png"))
    signup(a, new_id())
    a.get_by_test_id("nickname-input").fill("버섯친구")
    expect(a.get_by_test_id("nickname-status")).to_have_attribute("data-state", "available", timeout=5000)
    a.screenshot(path=str(out / "desktop-03-create.png"))
    a.get_by_test_id("create-submit").click()
    wait_screen(a, SCREEN_GAME)
    wait_connected(a)
    b = open_page(ctx, col, "B")
    signup(b, new_id())
    create_char(b, "마을이웃")
    wait_until(lambda: find_player(a, "마을이웃"), 6)
    send_chat(a, "안녕하세요! 반가워요 :)")
    hold_key(a, "ArrowRight", 600)
    time.sleep(0.4)
    a.screenshot(path=str(out / "desktop-04-game.png"))
    ctx.close()
    # 모바일
    ctx = browser.new_context(viewport={"width": 360, "height": 640}, is_mobile=True, has_touch=True, device_scale_factor=2)
    m = open_page(ctx, col, "M")
    m.screenshot(path=str(out / "mobile-01-login.png"))
    signup(m, new_id())
    m.get_by_test_id("nickname-input").fill("모바일친구")
    expect(m.get_by_test_id("nickname-status")).to_have_attribute("data-state", "available", timeout=5000)
    m.screenshot(path=str(out / "mobile-02-create.png"))
    m.get_by_test_id("create-submit").click()
    wait_screen(m, SCREEN_GAME)
    wait_connected(m)
    time.sleep(0.5)
    m.screenshot(path=str(out / "mobile-03-game.png"))
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
