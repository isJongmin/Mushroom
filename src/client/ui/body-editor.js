import {h,setText} from '../dom.js';
import {BODY_FIELDS,BODY_PRESETS,DEFAULT_BODY,normalizeBody,bodyKey,withBody} from '../avatar-body.js';

export function createBodyEditor({on,initial,onChange}){
 let value=normalizeBody(initial),enabled=false;
 const controls=new Map(),presets=[];
 const selected=h('strong',{testid:'body-selection'},'균형');
 const reset=h('button',{type:'button',class:'bk-btn',testid:'body-reset',disabled:true},'체형 초기화');
 const presetGrid=h('div',{class:'body-presets',role:'group','aria-label':'체형 프리셋'});
 for(const preset of BODY_PRESETS){
  const canvas=h('canvas',{width:88,height:112,'aria-hidden':'true'});
  const button=h('button',{type:'button',class:'body-preset',testid:'body-preset-'+preset.id,'aria-pressed':'false',disabled:true},canvas,h('strong',{},preset.name),h('small',{},preset.caption));
  on(button,'click',()=>update(preset.values,true));presets.push({preset,button,canvas});presetGrid.append(button);
 }
 const miniCanvas=h('canvas',{width:112,height:136,'aria-hidden':'true'});
 const miniPreview=h('div',{class:'body-mini-preview',testid:'body-mini-preview'},miniCanvas,h('div',{},h('strong',{},'비율 미리보기'),h('span',{},'아래에서 조절하면 바로 반영돼요.')));
 const groups=h('div',{class:'body-groups'});
 for(const group of [...new Set(BODY_FIELDS.map(f=>f.group))]){
  const fieldset=h('fieldset',{class:'body-group'},h('legend',{},group));
  for(const field of BODY_FIELDS.filter(f=>f.group===group)){
   const id='body-'+field.key,output=h('output',{for:id,testid:id+'-value'});
   const slider=h('input',{type:'range',id,min:field.min,max:field.max,step:1,value:value[field.key],disabled:true,testid:id,'aria-describedby':id+'-scale'});
   on(slider,'input',()=>update({...value,[field.key]:Number(slider.value)},false));
   on(slider,'change',()=>{if(enabled)onChange({...value},{commit:true});});
   controls.set(field.key,{slider,output});
   fieldset.append(h('div',{class:'body-slider'},h('div',{class:'body-slider-heading'},h('label',{for:id},field.label),output),slider,h('div',{class:'body-slider-scale',id:id+'-scale'},h('span',{},field.low),h('span',{},'기본 100%'),h('span',{},field.high))));
  }
  groups.append(fieldset);
 }
 const el=h('section',{class:'body-editor',testid:'body-editor','aria-label':'체형 조절'},h('div',{class:'body-editor-heading'},h('div',{},h('p',{class:'body-eyebrow'},'01 / SILHOUETTE'),h('h2',{},'나만의 비율'),h('p',{},'마음에 드는 체형에서, 조금씩 나답게.')),reset),presetGrid,h('p',{class:'body-current'},'현재 체형 · ',selected),miniPreview,h('details',{class:'body-details',open:true},h('summary',{},'세부 비율 조절 · 9개'),groups),h('p',{class:'body-note'},'의상도 체형에 맞춰 함께 변해요. 피격 범위·사거리·능력치는 같아요.'),h('p',{class:'body-note body-note--secondary'},'팔과 손은 상체 비율에 함께 반영돼요. 얼굴은 코디의 표정 항목에서 골라주세요.'));
 function paint(){
  const key=bodyKey(value),match=BODY_PRESETS.find(p=>bodyKey(p.values)===key);
  setText(selected,match?match.name:'직접 조정');
  for(const {preset,button} of presets)button.setAttribute('aria-pressed',String(preset.id===match?.id));
  for(const field of BODY_FIELDS){const {slider,output}=controls.get(field.key);slider.value=String(value[field.key]);setText(output,value[field.key]+'%');slider.setAttribute('aria-valuetext',value[field.key]+'%'+(value[field.key]===100?' · 기본':''));slider.style.setProperty('--body-value',((value[field.key]-field.min)/(field.max-field.min)*100)+'%');}
 }
 function update(next,commit){if(!enabled)return;value=normalizeBody(next);paint();onChange({...value},{commit});}
 on(reset,'click',()=>update(DEFAULT_BODY,true));paint();
 return {el,getValue:()=>({...value}),setValue(next){value=normalizeBody(next);paint();},setEnabled(next){enabled=!!next;reset.disabled=!enabled;for(const {button}of presets)button.disabled=!enabled;for(const {slider}of controls.values())slider.disabled=!enabled;},paintCurrent(renderer,avatar,frame){const ctx=miniCanvas.getContext('2d');ctx.clearRect(0,0,112,136);renderer.draw(ctx,avatar,56,132,.95,frame,false);},paintPresets(renderer,avatar){for(const {preset,canvas}of presets){const av=withBody(avatar,preset.values),ctx=canvas.getContext('2d');ctx.clearRect(0,0,88,112);renderer.draw(ctx,av,44,108,.74,0,false);}}};
}
