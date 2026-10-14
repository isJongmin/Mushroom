// 닉네임 라벨(style-guide 8장)과 말풍선(9장). 화면 해상도(CSS px, dpr 변환된 컨텍스트)에서 그린다.
// 배경은 UI 스킨 9-slice(U=2)를 Canvas로 직접 그리고, 스킨이 없으면 같은 크기의 단색 픽셀 상자로 그린다.
// 글자는 Canvas fillText로만 그린다 (사용자 문자열을 HTML로 해석하지 않는다).
import { BUBBLE, LABEL, PAL, FONT_UI, UI_SCALE } from '../constants.js';

const LABEL_FONT = `700 ${LABEL.font}px ${FONT_UI}`;
const BUBBLE_FONT = `700 ${BUBBLE.font}px ${FONT_UI}`;
const ELLIPSIS = '…';
const U = UI_SCALE;

const even = (v) => Math.ceil(v / 2) * 2;
const roundEven = (v) => Math.round(v / 2) * 2;

/** 9-slice: 모서리는 slice x U 크기 그대로, 변과 가운데는 늘린다 (스무딩 끔). */
export function drawNine(ctx, img, slice, x, y, w, h) {
  const sw = img.naturalWidth || img.width;
  const sh = img.naturalHeight || img.height;
  const s = slice;
  const d = s * U;
  const mw = Math.max(0, w - 2 * d);
  const mh = Math.max(0, h - 2 * d);
  const smw = sw - 2 * s;
  const smh = sh - 2 * s;
  const cols = [[0, s, x, d], [s, smw, x + d, mw], [sw - s, s, x + d + mw, d]];
  const rows = [[0, s, y, d], [s, smh, y + d, mh], [sh - s, s, y + d + mh, d]];
  for (const [sy, shh, dy, dh] of rows) {
    if (dh <= 0 || shh <= 0) continue;
    for (const [sx, sww, dx, dw] of cols) {
      if (dw <= 0 || sww <= 0) continue;
      ctx.drawImage(img, sx, sy, sww, shh, dx, dy, dw, dh);
    }
  }
}

/** 스킨이 없을 때: 2px 외곽선 + 모서리 2px 깎은 픽셀 상자 */
function pixelBox(ctx, x, y, w, h, line, fill) {
  ctx.fillStyle = line;
  ctx.fillRect(x + 2, y, w - 4, h);
  ctx.fillRect(x, y + 2, w, h - 4);
  ctx.fillStyle = fill;
  ctx.fillRect(x + 2, y + 2, w - 4, h - 4);
}

function shadowText(ctx, text, x, y, color, shadow, sx, sy) {
  ctx.fillStyle = shadow;
  ctx.fillText(text, x + sx, y + sy);
  ctx.fillStyle = color;
  ctx.fillText(text, x, y);
}

/** 공백 기준 줄바꿈, 공백 없는 긴 글은 글자 단위. 최대 줄 수를 넘으면 마지막 줄 끝을 …으로 자른다. */
export function wrapText(ctx, text, maxWidth, maxLines) {
  const fits = (s) => ctx.measureText(s).width <= maxWidth;
  const lines = [];
  const words = text.split(/ +/).filter((w) => w.length);
  let cur = '';
  const pushChars = (word) => {
    for (const ch of Array.from(word)) {
      if (fits(cur + ch)) cur += ch;
      else {
        if (cur) lines.push(cur);
        cur = ch;
      }
    }
  };
  for (const word of words) {
    const candidate = cur ? cur + ' ' + word : word;
    if (fits(candidate)) {
      cur = candidate;
    } else if (fits(word)) {
      if (cur) lines.push(cur);
      cur = word;
    } else {
      if (cur) cur += ' ';
      if (cur && !fits(cur)) { lines.push(cur.trimEnd()); cur = ''; }
      pushChars(word);
    }
    if (lines.length > maxLines) break;
  }
  if (cur) lines.push(cur);
  if (lines.length <= maxLines) return lines;
  const out = lines.slice(0, maxLines);
  const last = Array.from(out[maxLines - 1]);
  while (last.length && !fits(last.join('') + ELLIPSIS)) last.pop();
  out[maxLines - 1] = last.join('').trimEnd() + ELLIPSIS;
  return out;
}

/** 말풍선 레이아웃을 한 번만 계산해 둔다(텍스트가 바뀔 때만). */
export function layoutBubble(ctx, text) {
  ctx.save();
  ctx.font = BUBBLE_FONT;
  const lines = wrapText(ctx, text, BUBBLE.maxW - BUBBLE.padX * 2, BUBBLE.maxLines);
  let tw = 0;
  for (const l of lines) tw = Math.max(tw, ctx.measureText(l).width);
  ctx.restore();
  const w = even(Math.min(BUBBLE.maxW, Math.max(BUBBLE.minW, Math.ceil(tw) + BUBBLE.padX * 2)));
  const h = even(lines.length * BUBBLE.lineH + BUBBLE.padY * 2);
  return { lines, w, h };
}

export function bubbleAlpha(ageMs) {
  if (ageMs >= BUBBLE.showMs) return 0;
  const fadeStart = BUBBLE.showMs - BUBBLE.fadeMs;
  if (ageMs <= fadeStart) return 1;
  return 1 - (ageMs - fadeStart) / BUBBLE.fadeMs;
}

/**
 * @param ui loadUiAssets() 결과 (없으면 단색 폴백)
 * @param anchorX 기준점 화면 x (CSS px)
 * @param headY 머리 위 기준선 화면 y (아트 y 176)
 * @param viewW 캔버스 CSS 폭
 */
export function drawBubble(ctx, ui, layout, anchorX, headY, viewW, alpha) {
  if (alpha <= 0) return;
  const { lines, w, h } = layout;
  const tipX = Math.round(anchorX);
  const tipY = Math.round(headY) - BUBBLE.tipGap;
  let bottom = tipY - BUBBLE.bodyGap;
  let top = bottom - h;
  let tail = true;
  if (top < BUBBLE.topMin) {
    top = BUBBLE.topMin;
    bottom = top + h;
    tail = false;
  }
  let left = roundEven(tipX - w / 2);
  left = Math.max(BUBBLE.edge, Math.min(left, viewW - BUBBLE.edge - w));
  const tailLeft = Math.max(left + BUBBLE.edge, Math.min(tipX - BUBBLE.tailW / 2, left + w - BUBBLE.edge - BUBBLE.tailW));

  const body = ui && ui.nine && ui.nine.bubble;
  const tailImg = ui && ui.sprites && ui.sprites['bubble-tail'];
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.imageSmoothingEnabled = false;
  if (body) drawNine(ctx, body.img, body.slice, left, top, w, h);
  else {
    pixelBox(ctx, left, top, w, h, PAL.hb2, PAL.white);
    ctx.fillStyle = PAL.c2;
    ctx.fillRect(left + 2, top + h - 4, w - 4, 2);
  }
  if (tail) {
    if (tailImg) ctx.drawImage(tailImg.img, tailLeft, bottom - 2, BUBBLE.tailW, BUBBLE.tailH);
    else {
      // 8x4 꼬리를 2배로 (style-guide 7.6 모양)
      ctx.fillStyle = PAL.hb2;
      ctx.fillRect(tailLeft + 2, bottom, 12, 2);
      ctx.fillRect(tailLeft + 4, bottom + 2, 8, 2);
      ctx.fillRect(tailLeft + 6, bottom + 4, 4, 2);
      ctx.fillStyle = PAL.white;
      ctx.fillRect(tailLeft + 4, bottom - 2, 8, 2);
      ctx.fillRect(tailLeft + 4, bottom, 8, 2);
      ctx.fillRect(tailLeft + 6, bottom + 2, 4, 2);
    }
  }
  ctx.font = BUBBLE_FONT;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  const cx = left + w / 2;
  for (let i = 0; i < lines.length; i++) {
    const ty = top + BUBBLE.padY + BUBBLE.lineH * i + BUBBLE.lineH / 2;
    shadowText(ctx, lines[i], cx, ty, PAL.ink, PAL.c2, 1, 1);
  }
  ctx.restore();
}

/** 라벨 위 = 발바닥 화면 y + 4, 가로 중심 = 기준점 화면 x (2의 배수). */
export function drawLabel(ctx, ui, text, anchorX, footY, isSelf, viewW) {
  ctx.save();
  ctx.font = LABEL_FONT;
  const tw = Math.ceil(ctx.measureText(text).width);
  const w = Math.max(LABEL.minW, even(tw + LABEL.padX * 2));
  const h = LABEL.h;
  let x = roundEven(anchorX) - w / 2;
  x = Math.max(4, Math.min(x, viewW - 4 - w));
  const y = Math.round(footY) + LABEL.gap;
  ctx.imageSmoothingEnabled = false;
  const skin = ui && ui.nine && ui.nine[isSelf ? 'label-self' : 'label-other'];
  if (skin) drawNine(ctx, skin.img, skin.slice, x, y, w, h);
  else if (isSelf) pixelBox(ctx, x, y, w, h, PAL.y4, PAL.y3);
  else pixelBox(ctx, x, y, w, h, PAL.ink, PAL.hb2);
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  const tx = x + w / 2;
  const ty = y + LABEL.textTop + LABEL.lineH / 2;
  if (isSelf) shadowText(ctx, text, tx, ty, PAL.ink, PAL.y1, 0, 1);
  else shadowText(ctx, text, tx, ty, PAL.white, PAL.ink, 1, 1);
  ctx.restore();
}
