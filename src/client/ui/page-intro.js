import { drawMascot } from '../game/adventure-art.js';
import { h } from '../dom.js';

// Shared game characters, drawn once: no animation loop on menu screens.
export function pageIntro(kind) {
  const profile = kind === 'profile';
  const party=h('canvas',{class:'ui-scene-party',width:560,height:220});
  const c=party.getContext('2d');
  ['quarry','village','forest','frost'].forEach((area,i)=>drawMascot(c,area,85+i*125,190,i===1?1.9:1.45,0,{reduced:true}));
  return h('section', { class: `ui-intro ui-intro--${kind}`, 'aria-label': profile ? '캐릭터 만들기 안내' : '버섯마을 소개' },
    h('div', { class: 'ui-intro__copy' },
      h('p', { class: 'ui-eyebrow' }, 'MUSHROOM · ADVENTURER GUILD'),
      h('h2', {}, profile ? '주인공은 너야.' : '작은 녀석들,', h('br'), profile ? '어떤 모습으로 갈까?' : '모험은 크게!'),
      h('p', { class: 'ui-intro__desc' }, profile ? '무기를 들고, 나만의 모험가를 만들자.\n마을 밖에는 만만치 않은 녀석들이 기다린다.' : '검과 마법, 펫 세 마리. 준비는 끝났다.\n동료와 함께 다음 지역을 돌파하자.'),
      h('div', { class: 'ui-tags' }, h('span', {}, '4가지 무기'), h('span', {}, '자유로운 꾸미기'), h('span', {}, '함께하는 탐험'))),
    h('div', { class: 'ui-intro__scene', 'aria-hidden': 'true' }, h('span', { class: 'ui-scene-label' }, 'THE MUSHROOM CREW'), party),
  );
}
