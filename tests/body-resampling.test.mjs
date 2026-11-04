import assert from 'node:assert/strict';
import {createCanvas} from '@napi-rs/canvas';
import {bodySampleWeights,deformBodySheet} from '../src/client/avatar-body-raster.js';
import {normalizeBody,bodyY,sourceBodyY,bodyWidth} from '../src/client/avatar-body.js';
for(const scale of [.1,.13,.5,1,1.5,2])for(const center of [40,40.25,40.5,40.75]){
 const weights=bodySampleWeights(center,scale,144);assert(Math.abs(weights.reduce((n,[,w])=>n+w,0)-1)<1e-8);
}
assert.deepEqual(bodySampleWeights(40,2,144),[[40,1]]);
assert(bodySampleWeights(40,.1,144).length>=10,'shrinking samples the covered area rather than one texel pair');
for(const head of [10,100,200])for(const legLength of [10,100,200]){
 const body=normalizeBody({head,legLength});
 for(const join of [104,116,136,148]){const e=.0001,left=(bodyY(body,join)-bodyY(body,join-e))/e,right=(bodyY(body,join+e)-bodyY(body,join))/e;assert(Math.abs(left-right)<.001,'continuous slope at '+join);}
 for(let y=0;y<=192;y+=.25)assert(Math.abs(sourceBodyY(body,bodyY(body,y))-y)<1e-6);
 assert.equal(bodyWidth(body,100),head/100,'lower face retains the same horizontal scale as the forehead');
}
const source=createCanvas(144,192),c=source.getContext('2d');for(let x=0;x<144;x++){c.fillStyle=x%2?'white':'black';c.fillRect(x,0,1,192);}
const out=deformBodySheet(source,normalizeBody({feet:13}),{frameW:144,frameH:192,anchorX:72,makeCanvas:createCanvas}),g=out.avatarGeometry;
const values=[];for(let dx=-5;dx<=5;dx++)values.push(out.getContext('2d').getImageData(g.ax+dx,190-g.top,1,1).data[0]);
assert(Math.max(...values)-Math.min(...values)<40,'minified stripes stay near their averaged tone instead of aliasing between black/white');
assert(values.every(v=>v>100&&v<155));
console.log('PASS area-filtered 13% stripe shrink, cubic exact texel reconstruction, preserved lower-face ratio and continuous/invertible neck/hip curves');
