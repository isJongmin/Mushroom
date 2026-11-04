import {cleanSkinColor,withSkinColor,avatarSkinColor,SKIN_SWATCHES} from '../avatar-palette.js';
import {COSTUMES,drawCostume,costumeAvatar} from '../game/reward-costumes.js';
import { readRewards, saveRewards } from '../rewards.js';
import { GARDEN_LABEL,BOSS_LABEL } from '../game/garden.js';
import { drawAbilityEffect } from '../game/skill-visuals.js';
// 프로필 화면: 닉네임 + 캐릭터 꾸미기 (docs/design/screens/profile.md v4, character-create.md v3 3·5장, style-guide 5.12~5.14)
// - 서버와 통신하지 않는다. 저장 = localStorage `mushroom:profile` = { nickname, avatar(7키), skinColor, job } (ARCHITECTURE 결정 3).
// - 모드: first(최초, "입장하기") / edit(로비 "꾸미기"에서, "취소" + "저장").
// - 카테고리 탭 7개 + 아이템 슬롯 그리드(썸네일) + 프리셋 + 회전 미리보기(앞/옆/뒤 + 걷기)는 v3 그대로.
// - 탭/슬롯/프리셋은 assets/avatar/manifest.json 의 parts/presets 로만 만든다(하드코딩 없음).
import { h, setText } from '../dom.js';
import { NICK_RE, NICK_MAX, PART_KEYS, CATEGORY_ORDER, PART_LABELS, HAT_NONE } from '../constants.js';
import { PROFILE_MESSAGES as M } from '../errors.js';
import { createAvatarRenderer, smooth } from '../avatar.js';
import { drawFootShadow } from '../game/world.js';
import { pickAvatar } from '../avatar-data.js';
import { writeProfile } from '../store.js';
import { trimWs, charLength } from '../backend/common.js';
import { normalizeJob } from '../game/jobs.js';

// 미리보기 무대 (사이클 5, 월드 단위): 112x144 = CSS 56x72 x --pv (데스크톱 4 → 224x288, 모바일 3 → 168x216).
// 기준점 (56,128). 배경 = 맵 전체를 카메라 (mapX, mapY)로 그린 작은 장면 (지면선 440 → 무대 128). mapX는 소품이 적은 잔디 구간.
const STAGE = Object.freeze({ w: 112, h: 144, ax: 56, ay: 128, mapX: 1460, mapY: 440 - 128 });

// 슬롯/프리셋 썸네일 자르기 (시트 px, front 프레임 144x192 안의 정사각형): 얼굴/머리(모자 포함) 또는 몸.
const HEAD_CROP = Object.freeze({ x: 16, y: 26, size: 112 });
const TOP_CROP = Object.freeze({ x: 22, y: 92, size: 100 }); // 어깨~무릎
const BOTTOM_CROP = Object.freeze({ x: 27, y: 104, size: 90 }); // 허리~발
const SHOES_CROP = Object.freeze({ x: 32, y: 112, size: 80 }); // 무릎~발끝 (측면 발끝 y 186까지)
const THUMB = Object.freeze({
  skin: { parts: ['skin', 'face'], crop: HEAD_CROP },
  face: { parts: ['skin', 'face'], crop: HEAD_CROP },
  hair: { parts: ['skin', 'face', 'hair'], crop: HEAD_CROP },
  hat: { parts: ['skin', 'face', 'hair', 'hat'], crop: HEAD_CROP },
  top: { parts: ['skin', 'face', 'top'], crop: TOP_CROP },
  bottom: { parts: ['skin', 'face', 'bottom'], crop: BOTTOM_CROP },
  shoes: { parts: ['skin', 'face', 'shoes'], crop: SHOES_CROP },
});
const THUMB_SIZE = 40;
const PRESET_CROP = HEAD_CROP;
const VIEWS = Object.freeze([['front', '앞'], ['side', '옆'], ['back', '뒤']]);

export function mount(root, app, opts = {}) {
  const editMode = opts.mode === 'edit' && !!app.profile;
  const ac = new AbortController();
  const on = (el, type, fn, o) => el.addEventListener(type, fn, { signal: ac.signal, ...o });
  let alive = true;
  let assets = null;
  let renderer = null;
  let avatar = null;
  let skinColor=cleanSkinColor(editMode?app.profile.skinColor:null);
  let paletteTimer=0;
  let query='';
  let ready = false;
  const creating = false; // 처리 중 상태 없음 (동기 저장, profile.md 6장)
  let composing = false;
  let errorShown = false; // 한 번 오류를 보인 뒤에는 매 입력마다 즉시 갱신 (5.2)
  let selectedJob = normalizeJob(app.profile?.job);
  let activeTab = 'hair'; // 첫 진입 = 머리 (5.1)
  let view = 'front'; // front | side | back
  let walking = false;
  let walkStart = 0;
  let previewAttackAt = -Infinity;
  let raf = 0;
  let cancelRepaint = () => {};
  const nick = { value: '', status: 'empty' };

  // --- 요소 ---------------------------------------------------------------

  // 미리보기
  const stageCanvas = h('canvas', { width: String(STAGE.w), height: String(STAGE.h), 'aria-hidden': 'true' });
  const stageDots = h('span', { class: 'bk-dots', 'aria-hidden': 'true' }, h('i'), h('i'), h('i'));
  const previewEl = h('div', { class: 'bk-preview', testid: 'avatar-preview' },
    h('div', { class: 'bk-well' }, h('div', { class: 'bk-preview__stage' }, stageCanvas, stageDots)));
  const viewBtns = {};
  for (const [key, label] of VIEWS) {
    viewBtns[key] = h('button', {
      type: 'button', class: 'bk-btn', role: 'radio', 'aria-checked': String(key === view), testid: `view-${key}`,
      tabindex: key === view ? '0' : '-1', 'aria-label': `미리보기 ${label}모습`,
    }, label);
  }
  const viewGroup = h('div', { class: 'bk-tabs', role: 'radiogroup', 'aria-label': '미리보기 방향' }, VIEWS.map(([k]) => viewBtns[k]));
  const walkBtn = h('button', { type: 'button', class: 'bk-btn bk-btn--latch', testid: 'preview-walk', 'aria-pressed': 'false' },
    h('span', { class: 'bk-ico bk-ico--arrow', 'aria-hidden': 'true' }), '걷기');
  const previewIdentity=h('strong',{class:'atelier-preview-name'},'아직 이름 없는 모험가');
  const previewCaption=h('div',{class:'atelier-preview-caption'},h('small',{},'YOUR ADVENTURER'),previewIdentity);
  const prevArea = h('div', { class: 'create-prev create-left' }, previewCaption,previewEl, h('div', { class: 'bk-preview__ctrl' }, viewGroup, walkBtn));

  // 프리셋, 탭, 슬롯
  const presetGrid = h('div', { class: 'bk-presets', role: 'group', 'aria-label': '추천 조합' });
  const extraPresetGrid = h('div', { class: 'bk-presets', role: 'group', 'aria-label': '추가 추천 조합' });
  const morePresetLabel = h('span');
  const presetMore = h('details', { class: 'preset-more', testid: 'more-presets', hidden: true },
    h('summary', { class: 'bk-btn' }, morePresetLabel,
      h('span', { class: 'preset-more__expand' }, '펼치기'),
      h('span', { class: 'preset-more__collapse' }, '접기')),
    extraPresetGrid);
  const tabBtns = {};
  for (const part of CATEGORY_ORDER) {
    tabBtns[part] = h('button', {
      type: 'button', class: 'bk-btn', role: 'tab', id: `tab-${part}`, testid: `tab-${part}`,
      'aria-selected': String(part === activeTab), 'aria-controls': 'slot-grid', tabindex: part === activeTab ? '0' : '-1', disabled: true,
    }, part==='face'?'눈·표정':PART_LABELS[part]);
  }
  const tabList = h('div', { class: 'bk-tabs bk-tabs--cat', role: 'tablist', 'aria-label': '꾸미기 항목' }, CATEGORY_ORDER.map((p) => tabBtns[p]));
  const slotGrid = h('div', { class: 'bk-slots', role: 'radiogroup', id: 'slot-grid', testid: 'slot-grid', 'aria-labelledby': `tab-${activeTab}` });
  const currentLine = h('p', { class: 'bk-help', testid: 'current-part', 'aria-live': 'polite' });
  const partsBanner = h('div', { class: 'bk-banner bk-banner--error', role: 'alert', testid: 'manifest-error', hidden: true }, M.MANIFEST);
  const partsBody = h('div', {},
    h('h2', { class: 'section-title' }, '추천 조합'), presetGrid, presetMore,
    h('h2', { class: 'section-title' }, '꾸미기'), tabList, slotGrid, currentLine);
  const skinPicker=h('input',{type:'color',value:skinColor||'#fad6c0',testid:'skin-color-picker','aria-label':'피부색 직접 고르기',disabled:true});
  const skinHex=h('input',{type:'text',value:skinColor||'#fad6c0',testid:'skin-color-hex','aria-label':'피부색 HEX',maxlength:7,spellcheck:'false',disabled:true});
  const skinHelp=h('span',{class:'wardrobe-color-help',testid:'skin-color-status'},'#RRGGBB 형식으로 입력할 수 있어요.');
  const skinReset=h('button',{type:'button',class:'bk-btn',testid:'skin-color-reset',disabled:true},'기본 피부색');
  const skinControls=h('section',{class:'wardrobe-skin',testid:'skin-color-controls',hidden:true,'aria-label':'피부색 직접 지정'},h('div',{},h('strong',{},'나만의 피부색'),h('p',{},'색을 직접 고르거나, 아래 기본 톤에서 선택하세요.')),h('div',{class:'wardrobe-color-row'},skinPicker,skinHex,skinReset),skinHelp);
  function syncSkinInputs(){const color=skinColor||SKIN_SWATCHES.find(s=>s.id===avatar?.skin)?.color||'#fad6c0';skinPicker.value=skinHex.value=color;skinHex.removeAttribute('aria-invalid');}
  function applySkin(color,commit=false){if(!ready)return;skinColor=color;avatar=withSkinColor({...avatar,skin:'light'},skinColor);skinPicker.value=color;skinHex.value=color;skinHex.removeAttribute('aria-invalid');setText(skinHelp,'선택한 색을 미리보기에 반영했어요.');clearTimeout(paletteTimer);if(commit){paletteTimer=0;drawPreview();paintSlots();}else paletteTimer=setTimeout(()=>{paletteTimer=0;if(alive){drawPreview();paintSlots();}},100);}
  on(skinPicker,'input',()=>applySkin(skinPicker.value));on(skinPicker,'change',()=>applySkin(skinPicker.value,true));
  on(skinHex,'input',()=>{const color=cleanSkinColor(skinHex.value);if(color)applySkin(color);else{skinHex.setAttribute('aria-invalid','true');setText(skinHelp,'# 뒤에 6자리 색상 코드를 입력하세요.');}});
  on(skinReset,'click',()=>{if(!ready)return;skinColor=null;avatar=withSkinColor({...avatar,skin:'light'},null);skinPicker.value=skinHex.value='#fad6c0';skinHex.removeAttribute('aria-invalid');drawPreview();paintSlots();});
  const search=h('input',{type:'search',class:'bk-input wardrobe-search',testid:'wardrobe-search','aria-label':'코디 이름 검색',placeholder:'색상이나 스타일 이름으로 찾아보세요',disabled:true});
  on(search,'input',()=>{query=search.value.trim().toLowerCase();if(ready)buildSlots();});
  const wardrobeCount=h('span',{class:'wardrobe-count',testid:'wardrobe-count','aria-live':'polite'});
  const wardrobeEmpty=h('p',{class:'bk-help',testid:'wardrobe-empty',hidden:true},'검색 결과가 없어요. 다른 색상이나 이름으로 찾아보세요.');
  partsBody.insertBefore(h('div',{class:'wardrobe-toolbar'},search,wardrobeCount),slotGrid);
  partsBody.insertBefore(skinControls,slotGrid);partsBody.append(wardrobeEmpty);
  const partsArea = h('div', { class: 'create-parts' }, partsBanner,partsBody);

  // 닉네임 (5장)
  const nickInput = h('input', {
    id: 'nickname', class: 'bk-input bk-input--with-end', type: 'text', testid: 'nickname-input', placeholder: '마을에서 불릴 이름', maxlength: String(NICK_MAX),
    autocomplete: 'off', autocapitalize: 'off', spellcheck: 'false', enterkeyhint: 'done', 'aria-describedby': 'nickname-status',
  });
  on(nickInput,'input',()=>setText(previewIdentity,nickInput.value.trim()||'아직 이름 없는 모험가'));
  const nickCounter = h('span', { class: 'bk-counter', testid: 'nickname-counter', 'aria-hidden': 'true', hidden: true });
  const statusIcon = h('span', { class: 'status-icon', 'aria-hidden': 'true', hidden: true });
  const statusText = h('span', {});
  const status = h('p', { id: 'nickname-status', class: 'bk-help nick-status', testid: 'nickname-status', 'aria-live': 'polite' }, statusIcon, statusText);
  const nickArea = h('div', { class: 'create-nick bk-field' },
    h('label', { for: 'nickname', class: 'bk-label-text' }, '닉네임'),
    h('div', { class: 'bk-input-wrap' }, nickInput, h('span', { class: 'bk-input-end' }, nickCounter)),
    status);

  const randomStyle=h('button',{type:'button',class:'bk-btn',testid:'atelier-random'},'랜덤 코디');
  const resetStyle=h('button',{type:'button',class:'bk-btn',testid:'atelier-reset'},'처음 모습');
  on(randomStyle,'click',()=>{if(ready&&assets.presets.length)applyPreset(Math.floor(Math.random()*assets.presets.length));});
  on(resetStyle,'click',()=>{if(!ready)return;clearTimeout(paletteTimer);skinColor=cleanSkinColor(editMode?app.profile.skinColor:null);avatar=withSkinColor(editMode?assets.sanitizeAvatar(app.profile.avatar):assets.defaultAvatar,skinColor);syncSkinInputs();paintSlots();drawPreview();announcePart(activeTab);});
  partsBody.prepend(h('div',{class:'atelier-tools'},h('span',{},'작은 변화로, 나다운 모습'),h('div',{},randomStyle,resetStyle)));
  const weaponHint=h('p',{class:'create-job bk-help',testid:'weapon-hint'},'직업은 착용한 무기로 결정돼요. 가방에서 무기를 바꾸면 공격과 스킬도 바뀝니다.');

  // 버튼 (6장): 비활성은 aria-disabled (눌렀을 때 형식 오류를 보여 주기 위해 클릭은 받는다)
  const submit = h('button', {
    type: 'button', class: editMode ? 'bk-btn bk-btn--primary' : 'bk-btn bk-btn--primary bk-btn--block', testid: 'create-submit', 'aria-disabled': 'true',
  }, editMode ? '저장' : '입장하기');
  const cancelBtn = editMode ? h('button', { type: 'button', class: 'bk-btn', testid: 'profile-cancel' }, '취소') : null;
  const ctaArea = h('div', { class: 'create-cta' }, editMode ? h('div', { class: 'cta-pair' }, cancelBtn, submit) : submit);

  const rewards=readRewards(app.profileKey);
  const titleBtn=h('button',{type:'button',class:'bk-btn',testid:'garden-title-toggle','aria-pressed':String(rewards.equipped),disabled:!rewards.unlocked},rewards.unlocked?(rewards.equipped?'칭호 착용 중':'칭호 착용'):'아직 잠겨 있어요');
  on(titleBtn,'click',()=>{rewards.equipped=!rewards.equipped;titleBtn.setAttribute('aria-pressed',String(rewards.equipped));setText(titleBtn,rewards.equipped?'칭호 착용 중':'칭호 착용');});
  const rewardArea=h('section',{class:'reward-studio','aria-label':'모험 보상'},h('div',{},h('h3',{},rewards.bossClears>0?BOSS_LABEL:GARDEN_LABEL),h('p',{},rewards.unlocked?`버섯왕 ${rewards.bossClears}회 처치 · 마을 방어 ${rewards.clears}회 성공`:'마을 중앙의 버섯밭 지키기에 성공하면 해금돼요.')),titleBtn);
  const costumeButtons=[];
  const costumeList=h('div',{class:'costume-list'});
  for(const costume of COSTUMES){
    if(costume.id==='royal-guardian'&&!rewards.legacyRoyal)continue;
    const unlocked=costume.unlocked(rewards),cv=h('canvas',{width:'180',height:'220','aria-hidden':'true'});
    const c=cv.getContext('2d');drawCostume(c,costume.id,90,205,2,{back:true});drawCostume(c,costume.id,90,205,2);
    const btn=h('button',{type:'button',class:'bk-btn costume-card',testid:`costume-${costume.id}`,disabled:!unlocked,'aria-pressed':String(rewards.costume===costume.id)},cv,h('strong',{},costume.name),h('span',{},unlocked?'선택하여 착용 / 해제':'미해금'),h('small',{},costume.need));
    costumeButtons.push({btn,id:costume.id});on(btn,'click',()=>{rewards.costume=rewards.costume===costume.id?null:costume.id;for(const v of costumeButtons)v.btn.setAttribute('aria-pressed',String(v.id===rewards.costume));lastDrawn='';drawPreview();});costumeList.append(btn);
  }
  const costumeArea=h('section',{class:'reward-studio','aria-label':'해금 코스튬'},h('h3',{},'모험으로 얻는 코스튬'),h('p',{},`버섯밭 방어 ${rewards.clears}회 · 버섯왕 ${rewards.bossClears}회 처치`),costumeList);
  const modeSlot = h('span', { class: 'mode-slot' });
  const footRow = h('div', { class: 'card-foot', testid: 'profile-note' }, app.mode === 'local' ? modeSlot : null, h('span', {}, M.NOTE));
  const title = h('h2', { class: 'card-title', tabindex: '-1', testid: 'profile-title' }, editMode ? '나의 캐릭터 꾸미기' : '첫 모험을 준비해요');
  const card = h('section', { class: 'bk-panel card-create', 'aria-labelledby': 'profile-title', testid: 'profile-card' },
    h('div', { class: 'card-head' }, h('div', {}, h('p', { class: 'ui-eyebrow' }, 'CHARACTER STUDIO'), title), h('span', { class: 'ui-step' }, '나만의 모험가')),
    h('div', { class: 'create-grid' }, prevArea, partsArea, nickArea, weaponHint, ctaArea),
    h('details',{class:'atelier-archive',open:editMode},h('summary',{},'모험으로 해금하는 칭호와 의상'),rewardArea,costumeArea), footRow);
  title.id = 'profile-title';
  const logo = h('h1', { class: 'bk-logo bk-logo--sm' }, h('span', { class: 'bk-ico bk-ico--mush', 'aria-hidden': 'true' }), '버섯마을');
  const backBtn = h('button', { type: 'button', class: 'bk-btn', testid: 'profile-back' }, editMode?'로비로 돌아가기':'시작 화면');
  on(backBtn, 'click', () => editMode?doCancel():app.go('home'));
  root.append(h('main', { class: 'scr-auth', 'data-mode': editMode ? 'edit' : 'first' },
    h('header', { class: 'ui-profile-header' }, logo, backBtn),h('section',{class:'portal-page-heading'},h('p',{},'01 / CHARACTER ATELIER'),h('h1',{},'너의 이야기는,',h('br'),'어떤 모습일까?'),h('span',{},'마음에 드는 모습을 고르고, 마을에서 불릴 이름을 지어주세요.')),card));
  if (app.mode === 'local') app.placeModeBadge(modeSlot);

  // --- 미리보기 그리기 ---------------------------------------------------------
  // 무대 캔버스 백킹(CSS x dpr)에 바로 그린다. k = 장치 px / 월드 = pv/2 x dpr. 스무딩 켬.
  let map = null;
  let pv = 4;
  let dpr = 1;
  let k = 2;
  let lastDrawn = ''; // 마지막으로 그린 (조합, 프레임) — 같은 그림이면 다시 그리지 않는다
  let shownOnce = false;
  let lastReadyAvatar=null;

  function sizeStage() {
    const v = parseInt(getComputedStyle(previewEl).getPropertyValue('--pv'), 10);
    pv = Number.isInteger(v) && v > 0 ? v : 4;
    dpr = Math.max(1, Math.min(3, Math.round(window.devicePixelRatio || 1)));
    k = (pv / 2) * dpr;
    const w = Math.round(STAGE.w * k);
    const hgt = Math.round(STAGE.h * k);
    if (stageCanvas.width !== w || stageCanvas.height !== hgt) { stageCanvas.width = w; stageCanvas.height = hgt; }
    lastDrawn = '';
  }

  // 배경 = 방과 같은 맵 그리기(drawMap)를 카메라 (mapX, mapY)로 (패럴랙스 레이어 포함 작은 장면)
  function drawStageBg(c) {
    const w=stageCanvas.width,ht=stageCanvas.height;
    c.clearRect(0,0,w,ht);
    const light=c.createRadialGradient(w*.5,ht*.4,0,w*.5,ht*.5,w*.7);light.addColorStop(0,'#c5d4b980');light.addColorStop(1,'#a9bca000');c.fillStyle=light;c.fillRect(0,0,w,ht);
    c.fillStyle='#82917c22';c.beginPath();c.ellipse(w*.5,STAGE.ay*k,w*.36,ht*.055,0,0,Math.PI*2);c.fill();
  }

  function previewFrame(now) {
    if (now - previewAttackAt < 650) return renderer.frameAt('attack', Math.min(239, now - previewAttackAt));
    if (walking) return renderer.frameAt('walk', now - walkStart);
    if (view === 'front') return renderer.frameAt('idle_front', now - walkStart); // 앞 = 숨쉬기 0,1
    return renderer.frameIndex[view];
  }

  function drawPreview(now = performance.now(), force = true) {
    const fr = renderer && avatar ? previewFrame(now) : -1;
    const dressed=avatar?costumeAvatar(avatar,rewards.costume):avatar;
    const ok = !!(renderer && avatar && renderer.isReady(dressed));
    const key = `${ok ? PART_KEYS.map((p) => avatar[p]).join('|') : '-'}#${avatarSkinColor(avatar)||''}#${fr}#${now - previewAttackAt < 650 ? Math.floor(now / 16) : selectedJob}`;
    if (!force && key === lastDrawn) return;
    lastDrawn = key;
    const c = stageCanvas.getContext('2d');
    c.setTransform(1, 0, 0, 1, 0, 0);
    smooth(c);
    drawStageBg(c);
    if (renderer && avatar) {
      const fx = STAGE.ax * k;
      const fy = STAGE.ay * k;
      if (ok) drawFootShadow(c, fx, fy, k);
      if(!ok)renderer.ready(dressed);
      if(ok)lastReadyAvatar=dressed;
      const shown=ok?dressed:lastReadyAvatar||avatar,shownReady=renderer.isReady(shown);
      const previewK=k;
      const outfit={fit:renderer.costumeFit(shown,fr),side:view==='side',rear:view==='back',time:now,moving:walking};
      if(shownReady)drawCostume(c,rewards.costume,fx,fy,previewK,{...outfit,back:true});renderer.draw(c,shown,fx,fy,previewK,fr,false);if(shownReady)drawCostume(c,rewards.costume,fx,fy,previewK,outfit);if(shownReady&&view==='back'&&rewards.costume)renderer.drawBackHair(c,shown,fx,fy,previewK,fr);
      drawAbilityEffect(c, selectedJob, 0, fx, fy, k, now-previewAttackAt);
    }
    if (ok && !shownOnce) { shownOnce = true; stageDots.hidden = true; }
  }

  // 앞(숨쉬기)과 걷기는 애니메이션: 프레임이 바뀔 때만 다시 그린다
  function loop(now) {
    raf = 0;
    if (!alive) return;
    drawPreview(now, false);
    if (walking || view === 'front' || now - previewAttackAt < 650) raf = requestAnimationFrame(loop);
  }
  function stopLoop() { if (raf) cancelAnimationFrame(raf); raf = 0; }
  function startLoop() { if (!raf && alive && ready && (walking || view === 'front' || performance.now() - previewAttackAt < 650)) raf = requestAnimationFrame(loop); }

  function setView(next) {
    view = next;
    for (const [v] of VIEWS) {
      viewBtns[v].setAttribute('aria-checked', String(v === view));
      viewBtns[v].tabIndex = v === view ? 0 : -1;
    }
  }
  function setWalking(on) {
    walking = on;
    walkBtn.setAttribute('aria-pressed', String(on));
    stopLoop();
    walkStart = performance.now();
    if (on) setView('side');
    startLoop();
    drawPreview();
  }

  // --- 썸네일 -----------------------------------------------------------------
  function thumbCanvas(sizeCss) {
    const cv = h('canvas', { 'aria-hidden': 'true' });
    cv.width = sizeCss * dpr;
    cv.height = sizeCss * dpr;
    return cv;
  }
  /** src가 null이면(합성 중) 비워 두고, 합성이 끝나면 renderer onUpdate로 다시 칠한다. */
  function paintThumb(cv, src, crop) {
    const c = cv.getContext('2d');
    c.setTransform(1, 0, 0, 1, 0, 0);
    smooth(c);
    c.clearRect(0, 0, cv.width, cv.height);
    if (src) c.drawImage(src, crop.x, crop.y, crop.size, crop.size, 0, 0, cv.width, cv.height);
  }

  // --- 슬롯 그리드 --------------------------------------------------------------
  let slots = []; // [{ id, btn, canvas }]

  function buildSlots() {
    const part = activeTab;
    slotGrid.setAttribute('aria-labelledby', `tab-${part}`);
    skinControls.hidden=part!=='skin';
    const items=assets.parts[part].filter(item=>!query||item.label.toLowerCase().includes(query));
    setText(wardrobeCount,`${items.length} / ${assets.parts[part].length}개`);wardrobeEmpty.hidden=items.length>0;
    slots = items.map((item) => {
      const isNone = part === 'hat' && item.id === HAT_NONE;
      const canvas = isNone ? null : thumbCanvas(THUMB_SIZE * 2);
      const btn = h('button', {
        type: 'button', class: 'bk-slot', role: 'radio', 'aria-checked': 'false', 'aria-label': item.label,
        testid: `slot-${part}-${item.id}`, 'data-id': item.id, tabindex: '-1', disabled: creating,
      }, isNone ? h('span', { class: 'bk-slot__none', 'aria-hidden': 'true' }) : canvas,h('span',{class:'wardrobe-slot-label'},item.label));
      return { id: item.id, btn, canvas };
    });
    slotGrid.replaceChildren(...slots.map((s) => s.btn));
    paintSlots();
  }

  function paintSlots() {
    const part = activeTab;
    const spec = THUMB[part];
    const focusIndex=Math.max(0,slots.findIndex(s=>avatar[part]===s.id&&!(part==='skin'&&skinColor)));
    for (const [i,s] of slots.entries()) {
      const sel = avatar[part] === s.id&&!(part==='skin'&&skinColor);
      s.btn.setAttribute('aria-checked', String(sel));
      s.btn.tabIndex = i===focusIndex ? 0 : -1;
      if (s.canvas) paintThumb(s.canvas, renderer.thumb({ ...avatar, [part]: s.id }, spec.parts), spec.crop);
    }
  }

  let presetCanvases = [];
  function paintPresets() {
    presetCanvases.forEach((cv, i) => {
      if (i < 6 || presetMore.open) paintThumb(cv, renderer.thumb(assets.presets[i].avatar, PART_KEYS), PRESET_CROP);
    });
  }
  on(presetMore, 'toggle', () => { if (ready && presetMore.open) paintPresets(); });
  function buildPresets() {
    presetGrid.replaceChildren();
    extraPresetGrid.replaceChildren();
    presetMore.hidden = assets.presets.length <= 6;
    setText(morePresetLabel, `다른 코디 ${Math.max(0, assets.presets.length - 6)}개`);
    presetCanvases = [];
    assets.presets.forEach((p, i) => {
      const cv = thumbCanvas(THUMB_SIZE);
      presetCanvases.push(cv);
      if (i < 6 || presetMore.open) paintThumb(cv, renderer.thumb(p.avatar, PART_KEYS), PRESET_CROP);
      const btn = h('button', { type: 'button', class: 'bk-btn', testid: `preset-${i}`, 'data-label': p.label, disabled: creating }, cv, h('span', {}, p.label));
      on(btn, 'click', () => applyPreset(i));
      (i < 6 ? presetGrid : extraPresetGrid).appendChild(btn);
    });
  }

  function announce(text) { setText(currentLine, text); }
  function announcePart(part) { announce(`${PART_LABELS[part]}: ${assets.labelOf(part, avatar[part])}`); }

  function selectPart(part, id) {
    if (creating || !ready || (avatar[part] === id&&!(part==='skin'&&skinColor))) return;
    if(part==='skin'){skinColor=null;skinPicker.value=skinHex.value=SKIN_SWATCHES.find(s=>s.id===id)?.color||'#fad6c0';skinHex.removeAttribute('aria-invalid');}
    avatar = withSkinColor({ ...avatar, [part]: id },skinColor);
    paintSlots();
    drawPreview();
    announcePart(part);
  }

  function applyPreset(i) {
    if (creating || !ready) return;
    const p = assets.presets[i];
    if (!p) return;
    skinColor=null;avatar = withSkinColor(assets.sanitizeAvatar(p.avatar),null);syncSkinInputs(); // manifest에 없는 id는 기본값
    paintSlots();
    drawPreview();
    announce(`추천 조합 적용: ${p.label}`);
  }

  function setTab(part, focus) {
    if (!ready || part === activeTab) { if (focus) tabBtns[part].focus(); return; }
    activeTab = part;query='';search.value='';
    for (const p of CATEGORY_ORDER) {
      tabBtns[p].setAttribute('aria-selected', String(p === part));
      tabBtns[p].tabIndex = p === part ? 0 : -1;
    }
    buildSlots();
    announcePart(part);
    if (focus) tabBtns[part].focus();
  }

  function gridColumns() {
    if (slots.length < 2) return 1;
    const top = slots[0].btn.offsetTop;
    let n = 0;
    for (const s of slots) { if (s.btn.offsetTop !== top) break; n++; }
    return Math.max(1, n);
  }

  // --- 닉네임 상태 (5.2) -------------------------------------------------------
  // empty: 안내 / ok: 형식 맞음 / format: 형식 오류
  const STATUS = {
    empty: { cls: '', text: M.HELP },
    ok: { cls: 'bk-help--ok', text: M.OK, check: true },
    format: { cls: 'bk-help--error', text: M.NICK_FORMAT },
  };

  function setStatus(s) {
    nick.status = s;
    const d = STATUS[s];
    status.className = `bk-help nick-status ${d.cls}`.trim();
    status.dataset.state = s;
    setText(statusText, d.text);
    statusIcon.className = d.check ? 'status-icon bk-ico bk-ico--check' : 'status-icon';
    statusIcon.hidden = !d.check;
    if (s === 'format') nickInput.setAttribute('aria-invalid', 'true');
    else nickInput.removeAttribute('aria-invalid');
    updateSubmit();
  }

  function canSubmit() {
    return ready && nick.status === 'ok';
  }
  function updateSubmit() {
    submit.setAttribute('aria-disabled', String(!canSubmit()));
  }

  function updateCounter() {
    const n = charLength(nickInput.value);
    nickCounter.hidden = n === 0;
    setText(nickCounter, `${n}/${NICK_MAX}`);
  }

  /**
   * trigger: 'input' | 'blur' | 'submit'
   * 처음 입력하는 동안 1자일 때는 안내 상태. 오류는 (a) 2자 이상 불일치 (b) blur 때 불일치(빈 값 제외) (c) 버튼 누름 때 불일치.
   * 한 번 오류를 보인 뒤에는 매 입력마다 즉시 갱신.
   */
  function evaluate(trigger = 'input') {
    updateCounter();
    if (composing) return; // 조합 중에는 직전 상태 유지
    const v = trimWs(nickInput.value);
    nick.value = v;
    if (NICK_RE.test(v)) { setStatus('ok'); return; }
    const show = errorShown || trigger === 'submit' || (v && (trigger === 'blur' || charLength(v) >= 2));
    if (show) {
      errorShown = true;
      setStatus('format');
    } else setStatus('empty');
  }

  // --- 저장 -----------------------------------------------------------------
  let done = false;
  function doSave() {
    if (done) return;
    composing = false;
    evaluate('submit');
    if (!canSubmit()) {
      if (nick.status === 'format') nickInput.focus();
      return;
    }
    if(skinHex.getAttribute('aria-invalid')==='true'){setTab('skin',false);skinHex.focus();return;}
    done = true;
    const profile = { nickname: nick.value, avatar: pickAvatar(avatar), job: selectedJob, skinColor:cleanSkinColor(skinColor) };
    app.profile = profile;
    const latestRewards=readRewards(app.profileKey);
    latestRewards.equipped=latestRewards.unlocked && rewards.equipped;
    latestRewards.costume=COSTUMES.some(c=>c.id===rewards.costume&&c.unlocked(latestRewards))?rewards.costume:null;
    if (!saveRewards(app.profileKey,latestRewards)) app.storageFailed = true;
    if (!writeProfile(app.profileKey, profile)) app.storageFailed = true; // 막지 않고 메모리로 진행 (6.1)
    app.go('lobby');
  }
  function doCancel() {
    if (done || !editMode) return;
    done = true;
    app.go('lobby', { focus: 'edit' });
  }

  function showManifestError() {
    partsBanner.hidden = false;
    partsBody.hidden = true;
    ready = false;
    updateSubmit();
  }

  // --- 이벤트 -------------------------------------------------------------
  on(nickInput, 'compositionstart', () => { composing = true; });
  on(nickInput, 'compositionend', () => { composing = false; evaluate(); });
  on(nickInput, 'input', (e) => { if (!e.isComposing) composing = false; evaluate(); });
  on(nickInput, 'blur', () => { composing = false; evaluate('blur'); });
  on(nickInput, 'keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (e.isComposing || e.keyCode === 229) return;
      doSave();
    }
  });
  on(submit, 'click', () => doSave());
  if (cancelBtn) on(cancelBtn, 'click', () => doCancel());
  // Esc: 수정 모드에서 "취소"와 같다 (IME 조합 중이면 무시)
  on(window, 'keydown', (e) => {
    if (e.key !== 'Escape' || !editMode || e.isComposing || e.keyCode === 229) return;
    e.preventDefault();
    doCancel();
  });

  // 방향/걷기 (3.2): 앞/뒤를 누르면 걷기를 끈다. 걷기를 켜면 옆으로.
  for (const [k] of VIEWS) {
    on(viewBtns[k], 'click', () => {
      if (creating) return;
      if (walking && k !== 'side') { walking = false; walkBtn.setAttribute('aria-pressed', 'false'); }
      stopLoop();
      if (view !== k) walkStart = performance.now();
      setView(k);
      startLoop();
      drawPreview();
    });
  }
  on(viewGroup, 'keydown', (e) => {
    const keys = VIEWS.map(([k]) => k);
    const i = keys.indexOf(view);
    let n = -1;
    if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') n = (i + keys.length - 1) % keys.length;
    else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') n = (i + 1) % keys.length;
    if (n < 0) return;
    e.preventDefault();
    viewBtns[keys[n]].click();
    viewBtns[keys[n]].focus();
  });
  on(walkBtn, 'click', () => { if (!creating) setWalking(!walking); });

  // 카테고리 탭 (roving tabindex, 좌/우, Home/End)
  for (const p of CATEGORY_ORDER) on(tabBtns[p], 'click', () => { if (!creating) setTab(p, false); });
  on(tabList, 'keydown', (e) => {
    const i = CATEGORY_ORDER.indexOf(activeTab);
    let n = -1;
    if (e.key === 'ArrowLeft') n = (i + CATEGORY_ORDER.length - 1) % CATEGORY_ORDER.length;
    else if (e.key === 'ArrowRight') n = (i + 1) % CATEGORY_ORDER.length;
    else if (e.key === 'Home') n = 0;
    else if (e.key === 'End') n = CATEGORY_ORDER.length - 1;
    if (n < 0 || creating) return;
    e.preventDefault();
    setTab(CATEGORY_ORDER[n], true);
  });

  // 슬롯 (radio 동작: 클릭/Enter/Space 선택, 방향키 이동 + 선택)
  on(slotGrid, 'click', (e) => {
    const btn = e.target.closest('.bk-slot');
    if (!btn || !slotGrid.contains(btn) || btn.disabled) return;
    selectPart(activeTab, btn.dataset.id);
  });
  on(slotGrid, 'keydown', (e) => {
    if (creating || !slots.length) return;
    const i = Math.max(0, slots.findIndex((s) => s.id === avatar[activeTab]));
    const cols = gridColumns();
    let n = -1;
    if (e.key === 'ArrowLeft') n = i - 1;
    else if (e.key === 'ArrowRight') n = i + 1;
    else if (e.key === 'ArrowUp') n = i - cols;
    else if (e.key === 'ArrowDown') n = i + cols;
    else if (e.key === 'Home') n = 0;
    else if (e.key === 'End') n = slots.length - 1;
    else return;
    e.preventDefault();
    n = Math.max(0, Math.min(slots.length - 1, n));
    selectPart(activeTab, slots[n].id);
    slots[n].btn.focus();
  });

  let resizeTimer = 0;
  on(window, 'resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      if (!alive) return;
      sizeStage();
      drawPreview();
    }, 100);
  });

  // --- 테스트 훅 ---------------------------------------------------------------
  app.providers.profile = () => ({
    mode: editMode ? 'edit' : 'first',
    ready,
    avatar: avatar ? pickAvatar(avatar) : null,
    nickname: nickInput.value,
    job: selectedJob,
    skinColor:cleanSkinColor(skinColor),
    nicknameStatus: nick.status,
    tab: activeTab,
    view,
    walking,
    frame: renderer && avatar ? previewFrame(performance.now()) : null,
    slots: slots.length,
    presets: assets ? assets.presets.length : 0,
  });

  // --- 시작 -----------------------------------------------------------------
  if (editMode) nickInput.value = app.profile.nickname;
  setText(previewIdentity,nickInput.value||'아직 이름 없는 모험가');
  setStatus('empty');
  evaluate('input');
  sizeStage();
  drawPreview();
  app.assets.then((a) => {
    if (!alive) return;
    assets = a;
    if (!a || a.source !== 'manifest') { stageDots.hidden = true; showManifestError(); return; }
    // 레이어는 그릴 조합이 생길 때 받는다. 합성이 끝날 때마다 다음 프레임에 미리보기/썸네일을 다시 칠한다.
    let repaintRaf = 0;
    renderer = createAvatarRenderer(a, {
      onUpdate() {
        if (repaintRaf || !alive) return;
        repaintRaf = requestAnimationFrame(() => {
          repaintRaf = 0;
          if (!alive || !ready) return;
          drawPreview();
          paintSlots();
          paintPresets();
        });
      },
    });
    cancelRepaint = () => { if (repaintRaf) cancelAnimationFrame(repaintRaf); repaintRaf = 0; };
    // 최초: manifest 각 파츠 첫 항목 / 수정: 저장 값 (manifest에 없는 id는 기본값, 저장하면 그 값으로 고쳐 저장)
    avatar = withSkinColor(editMode?a.sanitizeAvatar(app.profile.avatar):a.defaultAvatar,skinColor);
    ready = true;
    syncSkinInputs();
    skinPicker.disabled=skinHex.disabled=skinReset.disabled=search.disabled=false;
    for (const p of CATEGORY_ORDER) tabBtns[p].disabled = false;
    buildPresets();
    buildSlots();
    announcePart(activeTab);
    drawPreview();
    startLoop();
    updateSubmit();
  }, () => {
    if (!alive) return;
    stageDots.hidden = true;
    showManifestError();
  });
  // 진입 포커스 = 제목 (모바일에서 키보드가 바로 올라와 미리보기를 가리지 않게, 8장)
  title.focus({ preventScroll: true });

  return {
    unmount() {
      alive = false;
      clearTimeout(resizeTimer);
      clearTimeout(paletteTimer);
      stopLoop();
      cancelRepaint();
      ac.abort();
      if (app.providers.profile) app.providers.profile = null;
      renderer?.clear();
    },
  };
}
