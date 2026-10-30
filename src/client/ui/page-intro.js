import { h } from '../dom.js';

// Editorial page introduction; the scene uses the same village artwork as the game.
export function pageIntro(kind) {
  const profile = kind === 'profile';
  return h('section', { class: `ui-intro ui-intro--${kind}`, 'aria-label': profile ? '캐릭터 만들기 안내' : '버섯마을 소개' },
    h('div', { class: 'ui-intro__copy' },
      h('p', { class: 'ui-eyebrow' }, 'A LITTLE WORLD, A NEW ADVENTURE'),
      h('h2', {}, profile ? '모험의 시작은,' : '오늘도, 가볍게', h('br'), profile ? '나다운 모습으로.' : '버섯마을 한 바퀴.'),
      h('p', { class: 'ui-intro__desc' }, profile ? '마음에 드는 스타일과 직업을 골라보세요.\n작은 마을에서 새로운 친구와 모험이 기다려요.' : '친구와 수다를 나누고, 낯선 숲을 탐험하고.\n함께할 방을 고르면 우리의 모험이 시작돼요.'),
      h('div', { class: 'ui-tags' }, h('span', {}, '4가지 직업'), h('span', {}, '자유로운 꾸미기'), h('span', {}, '함께하는 탐험'))),
    h('div', { class: 'ui-intro__scene', 'aria-hidden': 'true' }, h('span', { class: 'ui-scene-label' }, 'MEET YOU IN THE VILLAGE'), h('span', { class: 'ui-scene-dot' })),
  );
}
