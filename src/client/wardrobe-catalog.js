import {SKIN_SWATCHES} from './avatar-palette.js';
// Colorways reuse complete original pose sheets; no geometry stretching or extra PNG requests.
const variants=[];
const add=(part,id,label,source,color,reference,mode='material')=>variants.push(Object.freeze({part,id,label,source,color,reference,mode}));
for(const s of SKIN_SWATCHES.slice(3))add('skin',s.id,s.label,'light',s.color,'#fad6c0','skin');
for(const [id,name,color]of [['blue','푸른','#487daa'],['green','초록','#537d55'],['amber','호박','#b27c32'],['violet','보랏빛','#785aa3'],['gray','회색','#697582']])for(const [source,expression]of [['basic','기본'],['wink','윙크'],['sleepy','나른']])add('face',`${source}-${id}`,`${name} 눈 · ${expression}`,source,color,'#5a3428','eyes');
for(const [id,label,source,color,ref]of [
 ['ash-long','애쉬 시스루','black-seethrough','#8e8c96','#27232c'],['cocoa-long','코코아 시스루','black-seethrough','#72503f','#27232c'],['wine-long','와인 시스루','black-seethrough','#713f53','#27232c'],['silver-wolf','실버 울프컷','black-wolfcut','#b5bac6','#1f1c23'],['blue-wolf','블루블랙 울프컷','black-wolfcut','#394c64','#1f1c23'],['violet-wolf','바이올렛 울프컷','black-wolfcut','#6c5485','#1f1c23'],['peach-bob','피치 단발','sky-bob','#ddad98','#8fcbf0'],['sage-bob','세이지 단발','sky-bob','#92a58e','#8fcbf0'],['cream-bob','크림 단발','sky-bob','#d9c58f','#8fcbf0'],['cocoa-bob','모카 단발','sky-bob','#89654c','#8fcbf0'],['blue-crop','블루 크롭','espresso-crop','#4b6377','#44302a'],['silver-crop','실버 크롭','espresso-crop','#a7aeb7','#44302a'],['rose-buns','로즈 스페이스 번','copper-spacebuns','#b87986','#b66d46'],['lavender-buns','라벤더 스페이스 번','copper-spacebuns','#9a84b1','#b66d46'],['mint-twintail','민트 양갈래','black-twintail','#8dbdab','#30231f'],['copper-short','코퍼 숏컷','brown-short','#b9744b','#7a4a2e'],
])add('hair',id,label,source,color,ref,'hair');
for(const [source,name,ref,colors]of [
 ['hoodie-lavender','후드','#bca8ec',[['sage','세이지','#8fa58a'],['rose','더스티 로즈','#bf8f9e'],['ocean','오션 블루','#7598b8'],['ochre','오커','#c5a365']]],
 ['cardigan-cream','가디건','#dcc6a0',[['rose','로즈','#c793a3'],['blue','더스티 블루','#829eaf'],['forest','포레스트','#6d8a71'],['lavender','라벤더','#a397bb']]],
 ['varsity-navy','바시티','#25304e',[['green','아이비 그린','#355e4d'],['brown','코코아','#695044'],['plum','플럼','#60465e'],['teal','틸','#355d67']]],
 ['puffer-mint','패딩','#a9e3c8',[['peach','피치','#e5b9a3'],['blue','스카이','#a2c2dc'],['lilac','라일락','#c9b5de'],['sand','샌드','#d4c3a4']]],
])for(const [id,label,color]of colors)add('top',`${id}-${name==='후드'?'hoodie':name==='가디건'?'cardigan':name==='바시티'?'varsity':'puffer'}`,`${label} ${name}`,source,color,ref);
for(const [source,name,ref,colors]of [
 ['denim-wide','와이드 데님','#a9c3e6',[['indigo','인디고','#536d94'],['gray','스톤 그레이','#92989b'],['sage','세이지','#95a58d'],['sand','샌드','#c2af8e']]],
 ['skirt-check','체크 스커트','#b89581',[['plum','플럼','#9d809a'],['forest','포레스트','#7b937a'],['navy','네이비','#657795']]],
 ['cargo-black','카고 팬츠','#2b2930',[['khaki','카키','#7d8357'],['taupe','토프','#9a8778'],['blue','더스티 블루','#6a8195']]],
])for(const [id,label,color]of colors)add('bottom',`${id}-${source==='denim-wide'?'denim':source==='skirt-check'?'skirt':'cargo'}`,`${label} ${name}`,source,color,ref);
export const WARDROBE_VARIANTS=Object.freeze(variants);
export function expandWardrobe(raw){
 if(!raw?.parts||!raw?.files||!Array.isArray(raw.layerOrder)||!Object.values(raw.parts).every(Array.isArray)||!Object.values(raw.files).every(Array.isArray)||!raw.layerOrder.every(e=>e&&typeof e.layer==='string'&&typeof e.part==='string'))return {manifest:raw,variants:new Map()};
 const manifest={...raw,parts:Object.fromEntries(Object.entries(raw.parts).map(([p,items])=>[p,items.map(i=>({...i}))])),files:Object.fromEntries(Object.entries(raw.files).map(([l,ids])=>[l,[...ids]])),presets:Array.isArray(raw.presets)?[...raw.presets]:[]},map=new Map();
 for(const v of WARDROBE_VARIANTS){if(!manifest.parts[v.part]?.some(p=>p.id===v.source)||manifest.parts[v.part].some(p=>p.id===v.id))continue;
  manifest.parts[v.part].push({id:v.id,label:v.label});map.set(v.part+'/'+v.id,v);
  for(const e of manifest.layerOrder)if(e.part===v.part&&manifest.files[e.layer]?.includes(v.source))manifest.files[e.layer].push(v.id);
 }
 const looks=[
 ['세이지 숲 산책',{hair:'cocoa-long',face:'basic-green',top:'sage-hoodie',bottom:'sand-denim',hat:'none'}],['블루 아카데미',{hair:'silver-wolf',face:'basic-blue',top:'blue-cardigan',bottom:'indigo-denim',hat:'none'}],['로즈 가든',{hair:'rose-buns',face:'wink-violet',top:'rose-cardigan',bottom:'plum-skirt',hat:'none'}],['아이비 레인저',{hair:'copper-short',face:'basic-amber',top:'green-varsity',bottom:'khaki-cargo',hat:'ranger-cap'}],['라일락 소풍',{hair:'cream-bob',face:'basic-violet',top:'lilac-puffer',bottom:'gray-denim',hat:'none'}],['오션 데이',{hair:'blue-crop',face:'basic-gray',top:'ocean-hoodie',bottom:'blue-cargo',hat:'cap-white'}],['코코아 클래식',{hair:'cocoa-bob',face:'basic-amber',top:'brown-varsity',bottom:'taupe-cargo',hat:'none'}],['피치 피크닉',{hair:'peach-bob',face:'wink-green',top:'peach-puffer',bottom:'sand-denim',hat:'none'}],
 ];
 const base=raw.presets?.[0]?.avatar||Object.fromEntries(Object.entries(raw.parts).map(([p,items])=>[p,items[0].id]));
 manifest.presets=[...looks.map(([label,avatar])=>({label,avatar:{...base,...avatar}})),...manifest.presets];
 return {manifest,variants:map};
}
