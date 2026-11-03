const avatar=(hair,hat,top,bottom,shoes,skin='medium',face='basic')=>({hair,hat,top,bottom,shoes,skin,face});
export const MENTORS=Object.freeze({
 village:{name:'검성 하겐',title:'새벽 검술의 계승자',color:'#e0b76a',weapon:'sword',avatar:avatar('espresso-crop','warrior-circlet','warrior-armor','warrior-greaves','warrior-sabatons'),greeting:'검이 크다고 강한 건 아니다. 내 검? 크기도 하지. 네 안의 힘도 깨워볼까?',accept:'좋다. 이 마을에서 네 실력을 증명해라. 이미 쌓아온 경험도 인정하겠다.',complete:'흔들리지 않는 의지가 느껴지는군. 이 힘을 네 것으로 만들어라.'},
 quarry:{name:'철권 바르칸',title:'수정 갱도의 수호무인',color:'#b8a1ef',weapon:'claw',avatar:avatar('mohawk','thief-hood','thief-jacket','cargo-black','warrior-sabatons','dark'),greeting:'광석은 두드릴수록 빛나고, 모험가는 싸울수록 단단해진다. 한 번 벼려볼까?',accept:'수정과 강철보다 단단한 의지를 보여라. 이전의 발자취도 증거로 삼겠다.',complete:'훌륭하다. 이제 네 의지는 강철보다 단단하다.'},
 forest:{name:'대현자 아르웬',title:'세계수의 오랜 스승',color:'#94c791',weapon:'staff',avatar:avatar('silver-bob','mage-hat','mage-robe','mage-trousers','mage-boots','light','sleepy'),greeting:'흐아암… 백 년만 더 자려 했는데. 배움에 목마른 눈빛이로구나. 수련을 시작할까?',accept:'세계수가 네 수련을 지켜볼 것이다. 숲에 남긴 경험 역시 잊히지 않는다.',complete:'세계수가 너를 기억한다. 이 빛이 앞으로의 길을 밝혀주리라.'},
 frost:{name:'빙설군주 카이론',title:'영원의 서리를 다스리는 자',color:'#9fdaed',weapon:'sword',avatar:avatar('black-wolfcut','warrior-circlet','cape-blue','warrior-greaves','chunky-white','light'),greeting:'내 숨결에도 얼지 않는군. 좋아. 마지막 수련이다. …따뜻한 차는 끝나고 마시지.',accept:'빙하가 네 한계를 시험할 것이다. 지금까지의 싸움도 실력의 일부다.',complete:'서리조차 너를 꺾지 못했군. 이제 이 힘은 네 것이다.'},
});
export const mentorOf=area=>MENTORS[area]||MENTORS.village;
export const mentorPoint=world=>({x:Math.min(world.maxX-180,(world.spawn?.x??900)+360),y:world.groundY});
export function mentorMarker(goals){return goals.some(g=>g.ready)?'?':goals.some(g=>g.status==='available')?'!':goals.some(g=>g.status==='active')?'…':'수련';}
export function drawMentor(c,point,camX,camY,k,{area,avatar,renderer,now,drawItem}){
 const m=mentorOf(area),x=(point.x-camX)*k,y=(point.y-camY)*k;if(x<-150*k||x>c.canvas.width+150*k)return;
 c.save();c.fillStyle=m.color+'28';c.beginPath();c.ellipse(x,y-2*k,32*k,7*k,0,0,Math.PI*2);c.fill();c.strokeStyle=m.color;c.lineWidth=1.5*k;c.beginPath();c.ellipse(x,y-2*k,28*k,6*k,0,0,Math.PI*2);c.stroke();
 renderer?.draw(c,avatar,x,y,k,renderer.frameAt('idle_front',now),false);drawItem?.(c,m.weapon,x+24*k,y-24*k,.7*k,m.color,4,{held:true});
 c.fillStyle='#233c3c';c.fillRect(x-62*k,y+7*k,124*k,19*k);c.font=`700 ${10*k}px system-ui`;c.textAlign='center';c.fillStyle=m.color;c.fillText(m.name,x,y+20*k);c.restore();
}
