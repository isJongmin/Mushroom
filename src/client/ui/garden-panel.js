import { h,setText } from '../dom.js';
import { gardenActive,GARDEN_LABEL } from '../game/garden.js';
export function createGardenPanel({onStart,onEquip,onReplay,onFocus}) {
  const ac=new AbortController(),on=(el,fn)=>el.addEventListener('click',fn,{signal:ac.signal});
  const label=h('strong',{},'버섯밭 지키기'),detail=h('p',{},'3번의 습격을 막고 전용 칭호를 얻으세요.');
  const hp=h('progress',{max:'100',value:'100','aria-label':'버섯밭 내구도'});
  const start=h('button',{class:'garden-cta',type:'button',testid:'garden-start'},'함께 지키기');
  const status=h('span',{class:'garden-status',testid:'garden-status'});
  const el=h('aside',{class:'garden-panel',testid:'garden-panel','aria-label':'협동 이벤트'},h('span',{class:'garden-eyebrow'},'VILLAGE CO-OP'),h('div',{class:'garden-heading'},label,status),detail,hp,start);
  const resultTitle=h('h2'),resultDesc=h('p'),stats=h('div',{class:'garden-result__stats'}),reward=h('p',{class:'garden-reward'});
  const equip=h('button',{type:'button',class:'garden-cta',testid:'garden-equip'},'칭호 바로 착용');
  const replay=h('button',{type:'button',class:'garden-cta garden-cta--light',testid:'garden-replay'},'다시 도전');
  const close=h('button',{type:'button',class:'garden-close',testid:'garden-result-close','aria-label':'결과 닫기'},'닫기');
  const result=h('section',{class:'garden-result',role:'region','aria-label':'협동 이벤트 결과',testid:'garden-result',hidden:true},h('span',{class:'garden-eyebrow'},'OUR LITTLE VICTORY'),resultTitle,resultDesc,stats,reward,h('div',{class:'garden-result__actions'},equip,replay,close));
  let resultId='',lastKey='';
  on(start,onStart);on(equip,()=>{onEquip();equip.disabled=true;setText(equip,'착용 완료');});on(replay,()=>{result.hidden=true;onReplay();onFocus();});on(close,()=>{result.hidden=true;onFocus();});
  return {el,result,
    paint(s,{village,connected,near,alive,eligible,rewardSaved=true,now=Date.now(),host=true,uid=null}) {
      el.hidden=!village;if(!village){result.hidden=true;return;}
      const active=gardenActive(s),left=s?Math.max(0,Math.ceil((s.deadline-now)/1000)):0;
      const key=[s?.id,s?.rev,left,connected,near,alive,host].join(':');if(key===lastKey)return;lastKey=key;
      hp.hidden=!active;hp.value=s?.hp??100;
      status.textContent=active?`${s.wave}/3 WAVE`:'CO-OP';
      setText(label,active?'버섯밭을 지켜주세요!':'버섯밭 지키기');
      setText(detail,active?(s.phase==='wave'?`내구도 ${s.hp}% · 남은 적 ${alive} · ${left}초`:`${s.phase==='ready'?'습격 준비':'잠시 숨 고르기'} · ${left}초 후 시작`):'3번의 습격을 막으면 새싹 수호자 칭호를 얻어요.');
      start.hidden=active;
      start.disabled=!connected || !host || !near || !!s&&now<s.ended+5000;
      setText(start,!connected?'연결 중':!host?'동기화 중':!near?'마을 중앙 버섯밭으로 이동':s&&now<s.ended+5000?'잠시 후 다시 도전':'함께 지키기');
      if(s && ['success','failed'].includes(s.phase)&&s.id!==resultId) {
        resultId=s.id;result.hidden=false;const success=s.phase==='success';
        setText(resultTitle,success?'우리의 버섯밭을 지켰어요!':'다음엔 함께 지켜봐요');
        const mine=s.members.find(m=>m.uid===uid);
        setText(resultDesc,`${success?'모두의 공격이 작은 마을을 지켰습니다.':'적이 밭에 닿기 전에 길목에서 막아보세요.'} 내 기여: ${mine?.damage??0} 피해 · ${mine?.kills??0} 처치`);
        stats.replaceChildren(...[['진행 단계',`${s.wave}/3차`],['함께 처치',`${s.kills}마리`],['남은 내구도',`${s.hp}%`]].map(([k,v])=>h('div',{},h('strong',{},v),h('span',{},k))));
        setText(reward,eligible?`${GARDEN_LABEL} 해금 · ${rewardSaved?'이 브라우저에 저장됐어요.':'저장 공간이 없어 이번 접속에서만 착용할 수 있어요.'}`:success?'이벤트 적을 공격한 참여자에게 칭호가 지급돼요.':'보상은 방어 성공 시 받을 수 있어요.');
        equip.hidden=!eligible;equip.disabled=false;setText(equip,'칭호 바로 착용');
        // Results are non-modal so movement/chat remain available; no focus theft during combat.
      }
    },destroy(){ac.abort();result.remove();el.remove();}};
}
