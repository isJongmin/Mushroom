// 로그인 / 회원가입 화면 (docs/design/screens/login.md)
import { h, setText } from '../dom.js';
import { ID_RE, PW_MIN } from '../constants.js';
import { LOGIN_MESSAGES as M, toAppError } from '../errors.js';

export function mount(root, app, opts = {}) {
  const ac = new AbortController();
  const on = (el, type, fn) => el.addEventListener(type, fn, { signal: ac.signal });
  let alive = true;
  let mode = 'login'; // 'login' | 'signup'
  let busy = false;

  // --- 요소 (login.md v3 2장, ui-kit.css 클래스) ----------------------------
  const tabLogin = h('button', { type: 'button', class: 'bk-btn', role: 'tab', id: 'tab-login', testid: 'toggle-login', 'aria-controls': 'auth-form' }, '로그인');
  const tabSignup = h('button', { type: 'button', class: 'bk-btn', role: 'tab', id: 'tab-signup', testid: 'toggle-signup', 'aria-controls': 'auth-form' }, '회원가입');
  const tabs = h('div', { class: 'bk-tabs', role: 'tablist', 'aria-label': '로그인 또는 회원가입' }, tabLogin, tabSignup);
  const banner = h('div', { class: 'bk-banner bk-banner--error', role: 'alert', testid: 'error-message', hidden: true });

  const idInput = h('input', {
    id: 'login-id', type: 'text', class: 'bk-input', testid: 'login-id', autocomplete: 'username', autocapitalize: 'none',
    spellcheck: 'false', maxlength: '16', inputmode: 'latin', 'aria-describedby': 'login-id-help login-id-error',
  });
  const idHelp = h('p', { id: 'login-id-help', class: 'bk-help' }, '영문 소문자, 숫자, 밑줄(_) 4~16자');
  const idError = h('p', { id: 'login-id-error', class: 'bk-help bk-help--error', testid: 'error-id', hidden: true });

  const pwInput = h('input', {
    id: 'login-pw', type: 'password', class: 'bk-input bk-input--with-end', testid: 'login-pw', autocomplete: 'current-password',
    maxlength: '72', 'aria-describedby': 'login-pw-help login-pw-error',
  });
  const pwToggle = h('button', { type: 'button', class: 'bk-link', testid: 'pw-toggle', 'aria-pressed': 'false', 'aria-label': '비밀번호 보기' }, '보기');
  const pwHelp = h('p', { id: 'login-pw-help', class: 'bk-help', hidden: true }, '8자 이상');
  const pwError = h('p', { id: 'login-pw-error', class: 'bk-help bk-help--error', testid: 'error-pw', hidden: true });

  const pw2Input = h('input', {
    id: 'login-pw2', type: 'password', class: 'bk-input', testid: 'login-pw-confirm', autocomplete: 'new-password',
    maxlength: '72', 'aria-describedby': 'login-pw2-error',
  });
  const pw2Error = h('p', { id: 'login-pw2-error', class: 'bk-help bk-help--error', testid: 'error-pw-confirm', hidden: true });
  const pw2Field = h('div', { class: 'bk-field' },
    h('label', { for: 'login-pw2', class: 'bk-label-text' }, '비밀번호 확인'),
    h('div', { class: 'bk-input-wrap' }, pw2Input),
    pw2Error);

  const submitLabel = h('span', {}, '로그인');
  const spinner = h('span', { class: 'bk-dots', 'aria-hidden': 'true', hidden: true }, h('i'), h('i'), h('i'));
  const submit = h('button', { type: 'submit', class: 'bk-btn bk-btn--primary bk-btn--block auth-submit', testid: 'login-submit' }, spinner, submitLabel);

  // Tab 순서: 탭 → 아이디 → 비밀번호 → (확인) → 보기 토글 → 제출 (login.md 7장). 토글은 DOM상 입력 끝 요소이지만
  // 회원가입 모드에서는 tabindex 로 확인 필드 뒤에 오게 할 수 없으므로 DOM 순서(비밀번호 바로 뒤)를 따른다.
  const form = h('form', { id: 'auth-form', class: 'auth-form', novalidate: true, role: 'tabpanel' },
    h('div', { class: 'bk-field' },
      h('label', { for: 'login-id', class: 'bk-label-text' }, '아이디'),
      h('div', { class: 'bk-input-wrap' }, idInput),
      idHelp, idError),
    h('div', { class: 'bk-field' },
      h('label', { for: 'login-pw', class: 'bk-label-text' }, '비밀번호'),
      h('div', { class: 'bk-input-wrap' }, pwInput, h('span', { class: 'bk-input-end' }, pwToggle)),
      pwHelp, pwError),
    pw2Field,
    submit,
  );

  const modeSlot = h('span', { class: 'mode-slot' });
  const modeRow = app.mode === 'local'
    ? h('div', { class: 'card-foot' }, modeSlot, h('span', {}, '이 브라우저에만 저장됩니다'))
    : null;
  const panel = h('section', { class: 'bk-panel card-login' },
    h('p', { class: 'bk-logo-sub' }, '친구들과 함께 노는 작은 마을'),
    tabs,
    banner,
    form,
    modeRow,
  );
  const card = h('main', { class: 'scr-auth' },
    h('h1', { class: 'bk-logo' }, h('span', { class: 'bk-ico bk-ico--mush', 'aria-hidden': 'true' }), h('span', {}, '버섯마을')),
    panel,
  );
  root.append(card);
  if (modeRow) app.placeModeBadge(modeSlot);

  // --- 상태 표시 ----------------------------------------------------------
  const fields = {
    id: { input: idInput, error: idError, help: idHelp },
    pw: { input: pwInput, error: pwError, help: pwHelp },
    pw2: { input: pw2Input, error: pw2Error, help: null },
  };

  function setFieldError(name, code) {
    const f = fields[name];
    if (code) {
      setText(f.error, M[code]);
      f.error.hidden = false;
      if (f.help) f.help.hidden = true;
      f.input.setAttribute('aria-invalid', 'true');
    } else {
      f.error.hidden = true;
      setText(f.error, '');
      if (f.help) f.help.hidden = name === 'pw' ? mode !== 'signup' : false;
      f.input.removeAttribute('aria-invalid');
    }
    f.code = code || null;
  }

  function setBanner(code) {
    if (code) {
      setText(banner, M[code] || M.SERVER);
      banner.hidden = false;
    } else {
      banner.hidden = true;
      setText(banner, '');
    }
  }

  function validate(name) {
    const id = idInput.value;
    const pw = pwInput.value;
    if (name === 'id') return ID_RE.test(id) ? null : 'ID_FORMAT';
    if (name === 'pw') return mode === 'signup' && pw.length < PW_MIN ? 'PW_SHORT' : null;
    if (name === 'pw2') return mode === 'signup' && pw2Input.value !== pw ? 'PW_MISMATCH' : null;
    return null;
  }

  function updateSubmitEnabled() {
    const emptyPw = mode === 'login' && pwInput.value.length === 0;
    submit.disabled = busy || emptyPw;
  }

  function setMode(next) {
    mode = next;
    const signup = mode === 'signup';
    tabLogin.setAttribute('aria-selected', String(!signup));
    tabSignup.setAttribute('aria-selected', String(signup));
    tabLogin.tabIndex = signup ? -1 : 0;
    tabSignup.tabIndex = signup ? 0 : -1;
    pwInput.value = '';
    pw2Input.value = '';
    pw2Field.hidden = !signup;
    pwInput.setAttribute('autocomplete', signup ? 'new-password' : 'current-password');
    setText(submitLabel, signup ? '가입하고 시작하기' : '로그인');
    setBanner(null);
    for (const n of Object.keys(fields)) setFieldError(n, null);
    updateSubmitEnabled();
  }

  function setBusy(b, label) {
    busy = b;
    for (const el of [idInput, pwInput, pw2Input, pwToggle, tabLogin, tabSignup]) el.disabled = b;
    spinner.hidden = !b;
    setText(submitLabel, b ? label : mode === 'signup' ? '가입하고 시작하기' : '로그인');
    updateSubmitEnabled();
  }

  // --- 제출 ---------------------------------------------------------------
  async function doSubmit() {
    if (busy) return;
    setBanner(null);
    const order = mode === 'signup' ? ['id', 'pw', 'pw2'] : ['id'];
    let first = null;
    for (const n of order) {
      const code = validate(n);
      setFieldError(n, code);
      if (code && !first) first = n;
    }
    if (mode === 'login' && !pwInput.value) first = first || 'pw';
    if (first) {
      fields[first].input.focus();
      return;
    }
    const signup = mode === 'signup';
    setBusy(true, signup ? '가입 중' : '로그인 중');
    try {
      const session = signup
        ? await app.backend.signUp(idInput.value, pwInput.value)
        : await app.backend.signIn(idInput.value, pwInput.value);
      if (!alive) return;
      submit.disabled = true;
      await app.routeAfterAuth(session);
    } catch (err) {
      if (!alive) return;
      const e = toAppError(err);
      setBusy(false);
      let code = e.code;
      if (!signup && (code === 'ID_TAKEN' || code === 'ID_FORMAT' || code === 'PW_SHORT')) code = 'LOGIN_FAILED';
      if (code === 'ID_TAKEN' || code === 'ID_FORMAT') {
        setFieldError('id', code);
        idInput.focus();
      } else if (code === 'PW_SHORT') {
        setFieldError('pw', code);
        pwInput.focus();
      } else if (code === 'LOGIN_FAILED') {
        setBanner('LOGIN_FAILED');
        pwInput.value = '';
        updateSubmitEnabled();
        pwInput.focus();
      } else {
        setBanner(code === 'NETWORK' ? 'NETWORK' : 'SERVER');
      }
    }
  }

  // --- 이벤트 -------------------------------------------------------------
  on(tabLogin, 'click', () => { if (mode !== 'login') setMode('login'); });
  on(tabSignup, 'click', () => { if (mode !== 'signup') setMode('signup'); });
  on(tabs, 'keydown', (e) => {
    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
      e.preventDefault();
      setMode(mode === 'login' ? 'signup' : 'login');
      (mode === 'login' ? tabLogin : tabSignup).focus();
    }
  });
  on(pwToggle, 'click', () => {
    const showing = pwInput.type === 'text';
    pwInput.type = showing ? 'password' : 'text';
    pw2Input.type = showing ? 'password' : 'text';
    pwToggle.setAttribute('aria-pressed', String(!showing));
    pwToggle.setAttribute('aria-label', showing ? '비밀번호 보기' : '비밀번호 숨기기');
    setText(pwToggle, showing ? '보기' : '숨기기');
  });

  for (const [name, f] of Object.entries(fields)) {
    on(f.input, 'blur', () => {
      if (busy || !f.input.value) return;
      if (name === 'pw' && mode !== 'signup') return;
      setFieldError(name, validate(name));
    });
    on(f.input, 'input', () => {
      // 이미 표시된 오류는 규칙을 통과하는 순간 지운다
      if (f.code && !validate(name)) setFieldError(name, null);
      if (name === 'pw' && fields.pw2.code && !validate('pw2')) setFieldError('pw2', null);
      updateSubmitEnabled();
    });
  }

  on(form, 'submit', (e) => { e.preventDefault(); });
  on(form, 'keydown', (e) => {
    if (e.key !== 'Enter') return;
    if (e.target.tagName !== 'INPUT') return;
    e.preventDefault();
    if (e.isComposing || e.keyCode === 229) return;
    if (e.target === idInput) { pwInput.focus(); return; }
    doSubmit();
  });
  on(submit, 'click', (e) => { e.preventDefault(); doSubmit(); });

  setMode('login');
  if (opts.banner) setBanner(opts.banner);
  idInput.focus();

  return {
    unmount() {
      alive = false;
      ac.abort();
    },
  };
}
