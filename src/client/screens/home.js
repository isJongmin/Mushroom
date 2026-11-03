import {h} from '../dom.js';
import {chapterOf} from '../game/journey.js';
import {readAdventurer} from '../game/portal-model.js';
export function mount(root,app){
 const ac=new AbortController(),on=(el,fn)=>el.addEventListener('click',fn,{signal:ac.signal});
 const profile=app.profile,summary=readAdventurer(app.profileKey);
 const start=h('button',{type:'button',class:'portal-button portal-button--gold',testid:'home-start'},profile?'모험 이어가기':'모험 시작하기',h('span',{'aria-hidden':'true'},'→'));
 const studio=h('button',{type:'button',class:'portal-button portal-button--ghost',testid:'home-studio'},profile?'내 모험가 꾸미기':'캐릭터 먼저 만나보기');
 on(start,()=>app.go(profile?'lobby':'profile',{mode:'first'}));on(studio,()=>app.go('profile',{mode:profile?'edit':'first'}));
 const world=h('section',{id:'home-world',class:'portal-world','aria-label':'네 개의 모험 지역'},h('div',{class:'portal-section-heading'},h('p',{},'THE WORLD AWAITS'),h('h2',{},'작은 문을 열면,',h('br'),'끝없이 이어지는 세계.')));
 const regions=h('div',{class:'portal-regions'});
 for(const [area,name]of [['village','버섯마을'],['quarry','광산마을'],['forest','이끼마을'],['frost','서리마을']]){const chapter=chapterOf(area);regions.append(h('article',{class:'portal-region portal-region--'+area},h('span',{},chapter.number),h('small',{},name),h('h3',{},chapter.title),h('p',{},chapter.line)));}world.append(regions);
 const discover=h('button',{type:'button',class:'portal-scroll',testid:'home-world-link'},'세계 둘러보기 ↓');on(discover,()=>world.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'}));
 const main=h('main',{class:'scr-home',testid:'home-screen'},
  h('header',{class:'portal-header'},h('a',{href:'#',class:'portal-wordmark','aria-label':'버섯마을'},h('span',{},'MUSHROOM'),h('small',{},'VILLAGE')),h('span',{class:'portal-header-note'},'함께 써 내려가는 작은 모험')),
  h('section',{class:'portal-cover','aria-label':'버섯마을 모험 시작'},h('img',{class:'portal-cover-art',src:'assets/ui/forest-keyart-v1.webp',alt:'거대한 나무 아래 버섯 지붕 집들과 돌길이 이어지는 숲속 마을',fetchpriority:'high',decoding:'async',width:1536,height:1024}),h('div',{class:'portal-cover-shade'}),
   h('div',{class:'portal-cover-copy'},h('p',{class:'portal-kicker'},'A LITTLE WORLD. A GRAND ADVENTURE.'),h('h1',{},'작은 발걸음,',h('br'),'커다란 모험.'),h('p',{class:'portal-cover-description'},'숲 너머의 길, 곁을 지키는 동료,',h('br'),'그리고 아직 만나지 못한 나의 이야기.'),
    profile?h('div',{class:'portal-welcome'},h('span',{},`Lv.${summary.level}`),h('strong',{},profile.nickname),h('small',{},'다시 만나 반가워요.')):h('p',{class:'portal-invitation'},'당신의 첫 번째 이야기가 이곳에서 시작됩니다.'),h('div',{class:'portal-cover-actions'},start,studio),discover),
   h('div',{class:'portal-cover-caption'},h('span',{},'01 / 버섯마을'),h('small',{},'평온한 숲에서 시작되는 첫 번째 여정'))),
  h('section',{class:'portal-promises','aria-label':'게임 특징'},...[["20","명까지 함께"],["4","개의 모험 지역"],["4","가지 무기와 스킬"],["3","마리 동행 펫"]].map(([n,label])=>h('div',{},h('strong',{},n),h('span',{},label)))),world,
  h('footer',{class:'portal-footer'},h('span',{},'MUSHROOM VILLAGE'),h('p',{},'서두르지 않아도 괜찮아. 모험은 여기서 기다릴 테니까.')));
 root.append(main);
 return {unmount(){ac.abort();}};
}
