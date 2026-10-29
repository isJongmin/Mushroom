import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { AREA_IDS, areaMap, areaPortals, nearbyPortal, normalizeMapId, sameArea, minimapPoint } from '../src/client/game/areas.js';
import { normalizeZones, normalizeMobManifest } from '../src/client/game/mobs.js';
import { normalizePlatforms, normalizeRopes, createBody, stepBody } from '../src/client/game/physics.js';
const village=JSON.parse(readFileSync(new URL('../assets/map/manifest.json',import.meta.url)));
const mobs=normalizeMobManifest(JSON.parse(readFileSync(new URL('../assets/mob/manifest.json',import.meta.url))));
assert.equal(normalizeMapId('../forest'),'village');
for(const id of AREA_IDS){
 const map=areaMap(id,village);
 const platforms=normalizePlatforms(map.platforms,{width:map.width,groundY:map.groundY});
 const ropes=normalizeRopes(map.ropes,{width:map.width,groundY:map.groundY});
 const zones=normalizeZones(map.spawns,platforms,{width:map.width,groundY:map.groundY},mobs.kinds);
 assert.ok(zones.length>0);
 for(const z of zones) for(const k of z.mobs) assert.ok(mobs.kinds.has(k));
 for(const portal of areaPortals(map)){
  const next=areaMap(portal.to,village),back=areaPortals(next).find(p=>p.id===portal.entry);
  assert.equal(back.to,id);assert.equal(back.entry,portal.id);
  assert.equal(nearbyPortal(map,{x:portal.x,y:portal.y,dead:false}).to,portal.to);
  assert.equal(nearbyPortal(map,{x:portal.x,y:portal.y-100}),null);
  assert.equal(nearbyPortal(map,{x:portal.x,y:portal.y,dead:true}),null);
 }
 if(id!=='village')for(const rope of ropes){
  assert.ok(platforms.some(p=>p.y===rope.y1&&p.x1<rope.x&&p.x2>rope.x));
  const body=createBody(rope.x,map.groundY,map.groundY);
  for(let i=0;i<240;i++)stepBody(body,{up:true,dir:0,jump:false},1/60,{ropes,platforms,minX:20,maxX:map.width-20,groundY:map.groundY});
  assert.ok(body.y<=map.groundY-100,'rope is reachable from ground');
 }
 const dot=minimapPoint(map,map.width,map.groundY);
 assert.ok(dot.x<=204 && dot.y<=88 && Number.isFinite(dot.y));
}
assert.equal(sameArea({mapId:'forest'},{mapId:'quarry'}),false);
assert.equal(sameArea({},{mapId:'village'}),true);
console.log('PASS connected portal graph, safe use bounds, all biome monsters, reachable ropes and minimap projection');
