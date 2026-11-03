import {npcRoster} from '../game/npc-roster.js';
import {regionOf} from '../game/regions.js';
import {bossPatternText} from '../game/garden-boss.js';
import { h,setText } from '../dom.js';
import { gardenActive,GARDEN_LABEL,BOSS_LABEL } from '../game/garden.js';
export function createGardenPanel({onStart,onBoss,onEquip,onReplay,onFocus,onTraits}) {
  const ac=new AbortController(),on=(el,fn)=>el.addEventListener('click',fn,{signal:ac.signal});
  const label=h('strong',{},'버섯마을 지키기'),detail=h('p',{},'3번의 습격을 막고 전용 칭호를 얻으세요.');
  const hp=h('progress',{max:'100',value:'100','aria-label':'버섯밭 내구도'});
  const start=h('button',{class:'garden-cta',type:'button',testid:'garden-start'},'함께 지키기');
  const bossStart=h('button',{class:'garden-cta garden-cta--boss',type:'button',testid:'boss-start'},'버섯왕 도전');
  const traits=h('button',{class:'garden-cta garden-cta--light',type:'button',testid:'npc-traits'},'모험 특성 보기');on(traits,()=>{menuOpen=false;el.hidden=true;onTraits?.();});
  const status=h('span',{class:'garden-status',testid:'garden-status'});
  const el=h('aside',{class:'garden-panel',testid:'garden-panel','aria-label':'협동 이벤트'},h('span',{class:'garden-eyebrow'},'VILLAGE CO-OP'),h('div',{class:'garden-heading'},label,status),detail,hp,start,bossStart,traits);
  const resultTitle=h('h2'),resultDesc=h('p'),stats=h('div',{class:'garden-result__stats'}),reward=h('p',{class:'garden-reward'});
  const equip=h('button',{type:'button',class:'garden-cta',testid:'garden-equip'},'칭호 바로 착용');
  const replay=h('button',{type:'button',class:'garden-cta garden-cta--light',testid:'garden-replay'},'다시 도전');
  const close=h('button',{type:'button',class:'garden-close',testid:'garden-result-close','aria-label':'결과 닫기'},'닫기');
  const result=h('section',{class:'garden-result',role:'region','aria-label':'협동 이벤트 결과',testid:'garden-result',hidden:true},h('span',{class:'garden-eyebrow'},'OUR LITTLE VICTORY'),resultTitle,resultDesc,stats,reward,h('div',{class:'garden-result__actions'},equip,replay,close));
  let resultId='',lastKey='',resultMode='defense',menuOpen=false;
  const dismiss=h('button',{type:'button',class:'quest-menu-close','aria-label':'퀘스트 선택 닫기'},'닫기');el.append(dismiss);on(dismiss,()=>{menuOpen=false;lastKey='';el.hidden=true;onFocus();});
  on(start,()=>{menuOpen=false;onStart();});on(bossStart,()=>{menuOpen=false;(onBoss||onStart)();});on(equip,()=>{onEquip(resultMode);equip.disabled=true;setText(equip,'착용 완료');});on(replay,()=>{result.hidden=true;onReplay(resultMode);onFocus();});on(close,()=>{result.hidden=true;onFocus();});
  return {el,result,open(){menuOpen=true;lastKey='';el.hidden=false;start.focus({preventScroll:true});},
    paint(s,{village,area='village',connected,near,alive,eligible,rewardSaved=true,now=Date.now(),host=true,uid=null,bossHp=0}) {
      el.hidden=!village||(!menuOpen&&!gardenActive(s));if(!village){result.hidden=true;return;}
      const region=regionOf(area);setText(bossStart,region.boss+' 도전');
      const active=gardenActive(s),left=s?Math.max(0,Math.ceil((s.deadline-now)/1000)):0;
      const key=[area,s?.id,s?.rev,left,connected,near,alive,host,bossHp].join(':');if(key===lastKey)return;lastKey=key;
      hp.hidden=!active;hp.value=s?.phase==='boss'?bossHp/s.boss.max*100:s?.hp??100;hp.setAttribute('aria-label',s?.mode==='boss'?'버섯왕 체력':'버섯밭 내구도');
      status.textContent=active?(s?.mode==='boss'?'BOSS':`${s.wave}/3 WAVE`):'QUEST';
      setText(label,active?(s?.mode==='boss'?region.boss:region.event):npcRoster(area).quest.name+' · 도전 선택');
      setText(detail,s?.phase==='boss'?`${bossPatternText[s.boss.pattern]} · HP ${bossHp}/${s.boss.max} · ${left}초`:active?(s.phase==='wave'?`내구도 ${s.hp}% · 적 ${alive}${s.queued?` + 증원 ${s.queued}(${Math.max(0,Math.ceil((s.reinforceAt-now)/1000))}초)`:''} · ${left}초`:`${s.phase==='ready'?'습격 준비':'잠시 숨 고르기'} · ${left}초 후 시작`):'시간차 증원과 급습·강화 몬스터를 막아 마을을 지켜주세요.');
      start.hidden=bossStart.hidden=active;
      start.disabled=!connected || !host || !near || !!s&&now<s.ended+5000;
      bossStart.disabled=start.disabled;
      setText(start,!connected?'연결 중':!host?'동기화 중':!near?npcRoster(area).quest.name+'에게 가까이 이동':s&&now<s.ended+5000?'잠시 후 다시 도전':region.event);
      if(s && ['success','failed'].includes(s.phase)&&s.id!==resultId) {
        resultId=s.id;resultMode=s.mode;result.hidden=false;const success=s.phase==='success';
        setText(resultTitle,success?(s.mode==='boss'?region.boss+' 처치 성공!':region.event+' 성공!'):'다음엔 함께 지켜봐요');
        const mine=s.members.find(m=>m.uid===uid),total=s.members.reduce((n,m)=>n+m.damage,0),share=total?Math.round((mine?.damage??0)/total*100):0;
        setText(resultDesc,`${success?'모두의 공격이 작은 마을을 지켰습니다.':'적이 밭에 닿기 전에 길목에서 막아보세요.'} 내 기여: ${mine?.damage??0} 유효 피해 (${share}%) · ${mine?.kills??0} 처치 · 보스 ${mine?.bossDamage??0} 피해`);
        stats.replaceChildren(...(s.mode==='boss'?[['전투 결과',success?'처치 성공':'재도전'],['내 보스 피해',`${mine?.bossDamage??0}`],['진행 시간',`${Math.round((s.ended-s.started)/1000)}초`]]:[['진행 단계',`${s.wave}/3차`],['함께 처치',`${s.kills}마리`],['남은 내구도',`${s.hp}%`]]).map(([k,v])=>h('div',{},h('strong',{},v),h('span',{},k))));
        setText(reward,eligible&&s.mode==='boss'?`${BOSS_LABEL} 칭호 획득 · 떨어진 골드와 장비를 주워보세요.`:eligible?`${s.mode==='boss'?BOSS_LABEL+' 칭호 · 골드와 장비 드롭':GARDEN_LABEL+' · 코스튬 진행도'} 해금 · ${rewardSaved?'이 브라우저에 저장됐어요.':'저장 공간이 없어 이번 접속에서만 착용할 수 있어요.'}`:success?'이벤트 적을 공격한 참여자에게 칭호가 지급돼요.':'보상은 방어 성공 시 받을 수 있어요.');
        if(area!=='village')setText(reward,eligible?(s.mode==='boss'?'보스 골드·상급 장비가 바닥에 떨어졌어요.':'방어 보상 골드·장비가 바닥에 떨어졌어요.'):'이벤트 적을 공격하고 목표를 완료하세요.');
        equip.hidden=!eligible||area!=='village';equip.disabled=false;setText(equip,s.mode==='boss'?'수호자 칭호 착용':'칭호 바로 착용');
        // Results are non-modal so movement/chat remain available; no focus theft during combat.
      }
    },destroy(){ac.abort();result.remove();el.remove();}};
}
