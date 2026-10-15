// 작은 DOM 헬퍼. 문자열 자식은 항상 텍스트 노드로 들어간다(innerHTML을 쓰지 않는다).

/**
 * h('button', { class: 'btn', dataset: { testid: 'x' }, onclick: fn }, '텍스트', childEl)
 * - on* 함수는 쓰지 않는다(해제 경로 관리를 위해 리스너는 listen()으로 붙인다).
 */
export function h(tag, attrs, ...children) {
  const el = document.createElement(tag);
  if (attrs) {
    for (const [k, v] of Object.entries(attrs)) {
      if (v === undefined || v === null || v === false) continue;
      if (k === 'class') el.className = v;
      else if (k === 'text') el.textContent = String(v);
      else if (k === 'testid') el.setAttribute('data-testid', v);
      else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
      else if (v === true) el.setAttribute(k, '');
      else el.setAttribute(k, String(v));
    }
  }
  append(el, children);
  return el;
}

function append(el, children) {
  for (const c of children) {
    if (c === undefined || c === null || c === false) continue;
    if (Array.isArray(c)) append(el, c);
    else if (c instanceof Node) el.appendChild(c);
    else el.appendChild(document.createTextNode(String(c)));
  }
}

/** 사용자 문자열을 넣을 때는 항상 이 함수(textContent)를 쓴다. */
export function setText(el, text) {
  el.textContent = text == null ? '' : String(text);
}

export function show(el, visible) {
  el.hidden = !visible;
}

export function wait(ms, signal) {
  return new Promise((resolve) => {
    const t = setTimeout(resolve, ms);
    if (signal) signal.addEventListener('abort', () => { clearTimeout(t); resolve(); }, { once: true });
  });
}
