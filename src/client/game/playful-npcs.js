import {REGION_CHARACTER,drawMascot} from './adventure-art.js';
const avatar=(hair,hat,top,bottom,shoes,face='smile')=>({hair,hat,top,bottom,shoes,skin:'medium',face});
export const FUN_NPCS=Object.freeze({
 village:{name:'방향치 핀',role:'길을 묻는 모험가',game:'directions',color:'#e3bb78',avatar:avatar('blonde-spiky','explorer-brown','varsity-navy','shorts-brown','hightop-black'),greeting:'출구를 찾은 지 세 시간째야. 근데 여기 빵 냄새가 좋아서 급하진 않아.'},
 quarry:{name:'퇴근왕 두식',role:'가위바위보 광부',game:'rps',color:'#a6dae2',avatar:avatar('mohawk','beanie-yellow','overalls-green','cargo-black','boots-brown','wink'),greeting:'광석은 내일도 있어. 가위바위보 한 판 할래? 지는 쪽이 마음으로 야근하기!'},
 forest:{name:'낮잠술사 도리',role:'오늘의 모험운',game:'fortune',color:'#c4db9a',avatar:avatar('mint-curly','ranger-cap','cardigan-sage','widepants-cream','maryjane-red','sleepy'),greeting:'나뭇잎이 네 모험운을 알려줬어. 아니, 방금 꿈에서 본 것 같기도…'},
 frost:{name:'썰렁 대장 포그',role:'추위보다 차가운 농담',game:'joke',color:'#c3e7ef',avatar:avatar('pink-long','beanie-sage','puffer-mint','pants-navy','chunky-white'),greeting:'눈사람이 화나면? …열받으면 안 되니까 항상 침착하지. 한 개 더 들을래?'},
});
export const funNpcOf=area=>FUN_NPCS[area]||FUN_NPCS.village;
export const playfulPoint=(map,kind)=>({x:Math.max(200,(map.spawn?.x??900)-(kind==='mascot'?330:570)),y:map.groundY});
export function nearbyPlayful(map,player){
 if(!player||player.dead)return null;
 return ['mascot','fun'].map(kind=>({kind,...playfulPoint(map,kind)})).filter(p=>Math.abs(p.x-player.x)<=130&&Math.abs(p.y-player.y)<=75).sort((a,b)=>Math.abs(a.x-player.x)-Math.abs(b.x-player.x))[0]||null;
}
const MASCOT_LINES={
 village:['또 길을 잃었어. 그래도 네가 웃으면 배달 성공이지!','빠른 발이 내 특기야. 방향 감각은… 배송 중이야.','이 소포는 비밀이야. 살짝만 말하면 버섯 모양 쿠키야.'],
 quarry:['반짝이는 건 일단 주워! 내 도시락 뚜껑일 수도 있지만.','안전모는 머리를 지켜주고, 간식은 기분을 지켜줘.','내가 찾은 제일 귀한 광물? 퇴근석. 아직 못 찾았어.'],
 forest:['안녕… 방금 인사한 건 꿈이 아니지?','광합성 중이야. 누워 있는 것처럼 보이겠지만.','내 새싹이 흔들리면 바람이야. 내가 흔들리면 졸린 거야.'],
 frost:['안아줘도 안 녹아. 이 목도리가 생각보다 튼튼하거든.','눈요정도 추위를 타냐고? 그래서 목도리를 했지!','눈송이는 전부 다르대. 내 양말은 왜 양쪽이 같을까?'],
};
const fortunes=['오늘의 모험운: 길을 잃으면 새로운 길을 발견한다!','오늘의 모험운: 쉬어가는 것도 훌륭한 작전이다.','오늘의 모험운: 펫을 보고 웃을 일이 생긴다.','오늘의 모험운: 한 번 더 도전할 용기가 행운을 부른다.'];
const jokes=['빙하가 넘어지면? 빙그르르. 내가 먼저 웃을게.','눈이 길을 잃으면? 눈앞이 캄캄하지.','여기서 제일 따뜻한 건? 네가 농담을 끝까지 들어주는 마음.','내 농담 때문에 더 추워졌다고? 난방비는 마음으로 낼게.'];
export const rpsResult=(player,opponent)=>{const a=['가위','바위','보'].indexOf(player),b=['가위','바위','보'].indexOf(opponent);return a<0||b<0?null:a===b?'draw':(a-b+3)%3===1?'win':'lose';};
export function playfulChoices(area,kind){
 if(kind==='mascot')return ['인사하기','특기 보여줘'];
 switch(funNpcOf(area).game){case 'rps':return ['가위','바위','보'];case 'directions':return ['왼쪽이야','오른쪽이야'];case 'fortune':return ['나뭇잎 뽑기'];default:return ['농담 하나 더'];}
}
export function playfulReply(area,kind,choice,turn=0,random=Math.random){
 if(!playfulChoices(area,kind).includes(choice))return null;
 if(kind==='mascot'){const lines=MASCOT_LINES[area]||MASCOT_LINES.village;return {text:lines[(Math.max(0,turn)+(choice==='특기 보여줘'?1:0))%lines.length],emote:choice==='특기 보여줘'?'♪':'!'};}
 const game=funNpcOf(area).game;
 if(game==='rps'){const opponent=['가위','바위','보'][Math.min(2,Math.max(0,Math.floor(random()*3)))],outcome=rpsResult(choice,opponent);return {text:`너는 ${choice}, 나는 ${opponent}! ${outcome==='win'?'네 승리! 내 마음이 야근 중이야.':outcome==='draw'?'무승부! 우리 둘 다 퇴근하자.':'내 승리! 야근은 농담이고, 한 판 더 할래?'}`,emote:outcome==='win'?'짝짝':'!',outcome,opponent};}
 if(game==='directions')return {text:choice==='왼쪽이야'?'왼쪽! …내 왼쪽? 네 왼쪽? 일단 빵집부터 들를까.':'오른쪽! 확실히 기억했어. 근데 내가 어느 쪽을 보고 있었더라?',emote:'?'};
 if(game==='fortune')return {text:fortunes[Math.max(0,turn)%fortunes.length]+' 실제 능력치는 변하지 않아. 마음만 든든하게!',emote:'반짝'};
 return {text:jokes[Math.max(0,turn)%jokes.length],emote:'…'};
}
export function playfulIdentity(area,kind){return kind==='mascot'?{...REGION_CHARACTER[area]||REGION_CHARACTER.village,greeting:'잠깐 쉬어 갈래? 네 모험 이야기도 궁금해!'}:funNpcOf(area);}
export function drawFunNpc(c,map,camX,camY,k,now,{renderer,avatar,reduced=false,emote=null}={}){
 const s=funNpcOf(map.id),p=playfulPoint(map,'fun'),x=(p.x-camX)*k,y=(p.y-camY)*k;if(x<-120*k||x>c.canvas.width+120*k)return;
 c.save();renderer?.draw(c,avatar,x,y,k,renderer.frameAt('idle_front',reduced?0:now),false);
 c.fillStyle='#16293be8';c.fillRect(x-64*k,y+10*k,128*k,20*k);c.font=`700 ${10*k}px system-ui`;c.textAlign='center';c.fillStyle=s.color;c.fillText(s.name,x,y+24*k);
 if(emote){c.fillStyle='#fff0bf';c.font=`900 ${17*k}px system-ui`;c.fillText(emote,x,y-103*k);}c.restore();
}
export function drawPlayfulPortrait(cv,area,kind,renderer,avatar){const c=cv.getContext('2d');c.clearRect(0,0,cv.width,cv.height);if(kind==='mascot')drawMascot(c,area,64,136,1.65,0,{reduced:true});else renderer?.draw(c,avatar,64,155,1.65,0,false);}
export function drawPlayfulReaction(c,map,kind,camX,camY,k,now,reaction,reduced=false){
 if(!reaction||now>=reaction.until)return;const p=playfulPoint(map,kind),age=1800-(reaction.until-now),lift=reduced?0:Math.min(12,age/80);
 c.save();c.translate((p.x-camX)*k,(p.y-camY-(kind==='fun'?112:90)-lift)*k);c.scale(k,k);c.font='800 13px system-ui';c.textAlign='center';c.globalAlpha=Math.min(1,(reaction.until-now)/250);c.fillStyle='#172b3de8';c.fillRect(-24,-16,48,25);c.fillStyle='#ffe5a7';c.fillText(reaction.text,0,1);c.restore();
}
