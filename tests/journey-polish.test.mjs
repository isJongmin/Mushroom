import assert from 'node:assert/strict';
import {createCanvas} from '@napi-rs/canvas';
import {starterState} from '../src/client/game/progression.js';
import {chapterOf,journeyObjective,journeyTarget,journeyDirection,drawJourneyBeacon} from '../src/client/game/journey.js';
import {createLootFeedback} from '../src/client/game/loot-feedback.js';
import {createGameAudio} from '../src/client/game/game-audio.js';

const state=starterState(),world={maxX:5000,groundY:800,spawn:{x:1600}},map={...world,id:'village',width:5200,spawns:[{platform:'ground',x1:500,x2:700},{platform:'ledge',x1:1700,x2:1800},{platform:'ground',x1:2700,x2:2900}]},player={x:1600,y:800};
assert.equal(chapterOf('village').number,'01');assert.equal(chapterOf('invalid').number,'01');assert.equal(chapterOf('frost').number,'04');
const first=journeyObjective(state,'village');assert.equal(first.action,'mentor');
assert.equal(journeyTarget(first,map,world,state,player).x,1960);
assert.equal(journeyDirection(journeyTarget(first,map,world,state,player),player),'오른쪽 길을 따라가세요');
state.traits.quests['village:hunt20']='active';const hunt=journeyObjective(state,'village');assert.equal(hunt.action,'hunt');
const original=JSON.stringify(map.spawns),target=journeyTarget(hunt,map,world,state,player);assert.equal(target.x,600,'ground route rather than an unreachable nearby ledge');assert.equal(JSON.stringify(map.spawns),original);
assert.equal(journeyDirection(target,{x:600,y:800}),'목표에 도착했습니다');assert.equal(journeyDirection({x:600,y:300},{x:600,y:800}),'위층으로 올라가세요');
state.traits.quests['quarry:explore3']='active';state.traits.explored.quarry=[];
assert.equal(journeyObjective(state,'quarry').action,'explore');assert.equal(journeyTarget(journeyObjective(state,'quarry'),{...map,id:'quarry',platforms:[]},world,state,player).id,'entry');
const render=now=>{const cv=createCanvas(600,400),c=cv.getContext('2d');drawJourneyBeacon(c,target,player,1500,500,1,now,true);assert.equal(c.getTransform().a,1);assert.equal(c.getTransform().e,0);return cv.toBuffer('image/png');};
assert.deepEqual(render(0),render(1200),'reduced-motion beacon remains stationary');
assert.equal(journeyTarget({action:'bag'},map,world,state,player),null);
const feed=createLootFeedback();feed.push({kind:'gold',amount:10},0);feed.push({kind:'gold',amount:20},100);assert.equal(feed.sample(100).length,1);assert.equal(feed.sample(100)[0].amount,30);
for(let n=0;n<5;n++)feed.push({kind:'sword',tier:n},200+n);assert.equal(feed.sample(205).length,3);assert.equal(feed.sample(4000).length,0);feed.clear();
let created=0,resumed=0,closed=0,now=0;
const storage={getItem:()=>null,setItem(){}};
class AudioMock{constructor(){created++;this.state='suspended';this.currentTime=0;this.destination={};}resume(){resumed++;this.state='running';return Promise.resolve();}suspend(){this.state='suspended';return Promise.resolve();}close(){closed++;return Promise.resolve();}createOscillator(){return {frequency:{setValueAtTime(){},exponentialRampToValueAtTime(){}},connect(){},disconnect(){},start(){},stop(){this.onended?.();}};}createGain(){return {gain:{setValueAtTime(){},linearRampToValueAtTime(){},exponentialRampToValueAtTime(){}},connect(){},disconnect(){}};}}
const sound=createGameAudio({storage,Audio:AudioMock,clock:()=>now});assert.equal(created,0);assert.equal(sound.play('loot'),false,'no autoplay');sound.unlock();assert.equal(created,0);assert.equal(sound.toggle(),true);assert.equal(created,1);assert.equal(resumed,1);assert.equal(sound.play('loot'),true);assert.equal(sound.play('loot'),false,'rapid sound spam is throttled');now=100;assert.equal(sound.play('rare'),true);sound.toggle();assert.equal(sound.play('loot'),false);sound.close();assert.equal(closed,1);assert.equal(sound.play('level'),false);
console.log('PASS chapter direction, safe ground/exploration routes, reduced-motion beacon, bounded/merged rewards and opt-in audio lifecycle');
