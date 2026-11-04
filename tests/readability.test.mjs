import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const css=readFileSync(new URL('../src/client/readable-ui.css',import.meta.url),'utf8');
const tokens=Object.fromEntries([...css.matchAll(/--read-([\w-]+):\s*(#[0-9a-f]{6})/gi)].map(m=>[m[1],m[2]]));
function luminance(hex){const channels=hex.slice(1).match(/../g).map(c=>parseInt(c,16)/255).map(c=>c<=.04045?c/12.92:((c+.055)/1.055)**2.4);return channels[0]*.2126+channels[1]*.7152+channels[2]*.0722;}
function contrast(a,b){const x=luminance(a),y=luminance(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);}
const pairs=[['ink','paper'],['muted','paper'],['ink','paper-raised'],['muted','paper-raised'],['light','night'],['night-muted','night'],['light','primary'],['ink','gold'],['danger','paper']];
for(const[a,b]of pairs)assert.ok(contrast(tokens[a],tokens[b])>=4.5,`${a}/${b} contrast ${contrast(tokens[a],tokens[b]).toFixed(2)}`);
for(const[a,b]of [['#4d604c','#dce2d4'],['#f5f4df','#30433b'],['#c5d8c7','#30433b'],['#586c50','#e6eadb']])assert.ok(contrast(a,b)>=4.5,`${a}/${b} contrast`);
const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');assert.ok(html.indexOf('readable-ui.css')>html.indexOf('portal-ui.css'),'readability is the final theme layer');
console.log('PASS measured text/background contrast >=4.5 for paper, night, primary, grade and disabled surfaces');
