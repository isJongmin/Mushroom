import {h} from '../dom.js';
import {openModal} from './modal.js';
import {journalChapters,journeySummary,journeyActionLabel} from '../game/journey-journal.js';

export function createJourneyJournal({main,getState,getArea,onGuide,onFocus}){
  let modal=null,ac=null,destroyed=false;
  function close(){ac?.abort();modal?.close();modal=null;onFocus?.();}
  const button=(text,action,id)=>{const b=h('button',{type:'button',class:'gp-button',testid:id},text);b.addEventListener('click',action,{signal:ac.signal});return b;};
  return {
    open(){
      if(destroyed)return;
      ac?.abort();ac=new AbortController();
      const state=getState(),area=getArea(),summary=journeySummary(state,area);if(!summary)return;
      const body=h('div',{class:'journey-journal'},
        h('header',{class:'journal-heading'},h('div',{},h('small',{},'THE ADVENTURE JOURNAL'),h('h2',{id:'journal-title'},'나의 모험 수첩')),button('닫기',close,'journal-close')),
        h('p',{class:'journal-intro'},'지나온 길은 기록으로, 다음 한 걸음은 새로운 이야기로.'),
        h('section',{class:'journal-current'},h('small',{},'지금 이어갈 이야기'),h('h3',{},summary.goal.title),h('p',{},summary.goal.detail),
          h('strong',{},`의뢰 ${summary.contract.current} / 20 · 완료 보상 ${summary.contract.reward}`),h('progress',{max:20,value:summary.contract.current,'aria-label':'사냥 의뢰 진행'}),
          h('p',{},summary.levelHint),h('p',{},summary.skillHint),
          button(journeyActionLabel(summary.goal),()=>{close();onGuide();},'journal-guide')));
      const chapters=h('div',{class:'journal-chapters'});
      const records=journalChapters(state);
      for(const chapter of records){
        const card=h('section',{class:'journal-chapter'+(chapter.unlocked?' is-unlocked':''),'data-area':chapter.area},
          h('div',{class:'journal-chapter-top'},h('span',{},chapter.chapter.number),h('small',{},chapter.area===area?'현재 지역':chapter.unlocked?'입장 가능':'아직 잠긴 길')),
          h('h3',{},chapter.name),h('p',{},chapter.chapter.line),
          h('div',{class:'journal-record'},h('span',{},`사냥 ${chapter.kills.toLocaleString()}마리`),h('span',{},`수련 ${chapter.claimed} / ${chapter.goals.length}`)));
        const quests=h('ul',{class:'journal-quests'});
        for(const goal of chapter.goals)quests.append(h('li',{},h('span',{},goal.label),h('strong',{},goal.claimed?'완료':goal.ready?'보상 수령 가능':`${goal.current} / ${goal.target}`)));
        card.append(quests);
        if(!chapter.unlocked){const previous=records.find(c=>c.next?.id===chapter.area);card.append(h('p',{class:'journal-lock'},previous?.next?.requirement||'이전 지역에서 여정을 이어가세요'));}
        chapters.append(card);
      }
      body.append(chapters,h('p',{class:'journal-save-note'},'기록과 장비는 현재 브라우저에 저장됩니다.'));
      modal=openModal({main,titleId:'journal-title',testid:'journey-journal',children:[body],onCancel:close,canEscape:()=>true});
      modal.section.classList.add('journal-modal');
    },
    destroy(){destroyed=true;ac?.abort();modal?.close({restoreFocus:false});modal=null;},
  };
}
