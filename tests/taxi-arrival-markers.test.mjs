import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createCanvas} from '@napi-rs/canvas';
import {taxiPoint,drawTownTaxi,TAXI_DRIVER} from '../src/client/game/town-taxi.js';
import {areaMap,areaPortals} from '../src/client/game/areas.js';
import {playfulPoint} from '../src/client/game/playful-npcs.js';
import {drawNpcAction} from '../src/client/game/npc-actions.js';
import {eventPanelVisible} from '../src/client/ui/garden-panel.js';
import {createBossEntrance} from '../src/client/game/boss-entrance.js';
const manifest=JSON.parse(readFileSync(new URL('../assets/avatar/manifest.json',import.meta.url))),village=JSON.parse(readFileSync(new URL('../assets/map/manifest.json',import.meta.url)));
for(const [part,id]of Object.entries(TAXI_DRIVER.avatar))assert.ok(manifest.parts[part].some(p=>p.id===id),part+':'+id);
const render=(map,now,reduced)=>{const cv=createCanvas(600,400),c=cv.getContext('2d'),p=taxiPoint(map);drawTownTaxi(c,map,p.x-300,p.y-320,1,now,reduced);assert.deepEqual([c.getTransform().a,c.getTransform().d,c.getTransform().e,c.getTransform().f],[1,1,0,0]);return cv.toBuffer('image/png');};
for(const area of ['village','quarry','forest','frost']){
 const map=areaMap(area,village),p=taxiPoint(map),fun=playfulPoint(map,'fun');assert.ok(p.x<=map.spawn.x-500,'station is away from the central quest NPC line');assert.ok(fun.x-p.x>=170,'taxi pavement and fun NPC no longer overlap');for(const portal of areaPortals(map))assert.ok(Math.abs(portal.x-p.x)>=140,'taxi stays clear of portal labels');
 assert.deepEqual(render(map,0,true),render(map,1800,true));assert.notDeepEqual(render(map,0,false),render(map,800,false));
}
const cv=createCanvas(100,100),c=cv.getContext('2d');drawNpcAction(c,50,50);assert.ok(c.getImageData(50,47,1,1).data[3]>0);c.fillStyle='#102030';c.fillRect(20,20,60,60);assert.deepEqual([...c.getImageData(50,50,1,1).data],[16,32,48,255],'character drawn after marker fully occludes it');
const active={id:'run',phase:'boss',mode:'boss',started:1000};assert.equal(eventPanelVisible(null),false);assert.equal(eventPanelVisible(active),false,'joining an ongoing event does not auto-open quest HUD');assert.equal(eventPanelVisible(active,{observed:true}),true);assert.equal(eventPanelVisible(null,{menuOpen:true}),true);assert.equal(eventPanelVisible({...active,phase:'success'},{observed:true}),false);
const entrance=createBossEntrance();assert.equal(entrance.observe({...active,phase:'ready'},'village',1200,{suppress:true}),null);assert.equal(entrance.observe({...active,phase:'ready'},'village',1600),null,'suppressed join-time boss card does not replay after the town reveal');
console.log('PASS station/portal/NPC clearance, valid shared driver, reduced-motion art, world-marker occlusion and silent initial event/arrival policy');
