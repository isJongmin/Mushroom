// 닉네임 라벨(style-guide v3 7장)과 말풍선(8장) Canvas 레시피.
// 화면 해상도 컨텍스트(setTransform(dpr)로 CSS px 단위)에 fillRect 와 fillText 만으로 그린다.
// 위치 기준은 기준점 화면 좌표(ax, fy)와 머리 위 기준선(아트 52px)뿐이다. 사용자 문자열은 fillText로만 그린다.
import { BUBBLE, LABEL, PAL, FONT_UI, ART } from '../constants.js';

const LABEL_FONT = `700 ${LABEL.font}px ${FONT_UI}`;
const BUBBLE_FONT = `700 ${BUBBLE.font}px ${FONT_UI}`;
const ELLIPSIS = '…';

const even = (v) => Math.ceil(v / 2) * 2;
const round2 = (v) => Math.round(v / 2) * 2;
const clamp = (v, lo, hi) => Math.max(lo, Math.min(v, hi));

/** 계단 테두리 2px: 네 변만 칠하고 모서리 2x2는 비운다. */
function stepBorder(ctx, x, y, w, h, color) {
  ctx.fillStyle = color;
  ctx.fillRect(x, y - 2, w, 2);
  ctx.fillRect(x, y + h, w, 2);
  ctx.fillRect(x - 2, y, 2, h);
  ctx.fillRect(x + w, y, 2, h);
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

/** 말풍선 레이아웃 (8.1): 글자 폭 180 줄바꿈, 가로 = 가장 긴 줄 + 20 (40~200, 짝수), 세로 = 줄 x 18 + 14 */
export function layoutBubble(ctx, text) {
  ctx.save();
  ctx.font = BUBBLE_FONT;
  const lines = wrapText(ctx, text, BUBBLE.wrapW, BUBBLE.maxLines);
  let tw = 0;
  for (const l of lines) tw = Math.max(tw, ctx.measureText(l).width);
  ctx.restore();
  const w = Math.min(BUBBLE.maxW, even(Math.max(BUBBLE.minW, Math.ceil(tw) + BUBBLE.padX * 2)));
  const h = lines.length * BUBBLE.lineH + BUBBLE.padTop + BUBBLE.padBottom;
  return { lines, w, h };
}

export function bubbleAlpha(ageMs) {
  if (ageMs >= BUBBLE.showMs) return 0;
  const fadeStart = BUBBLE.showMs - BUBBLE.fadeMs;
  if (ageMs <= fadeStart) return 1;
  return 1 - (ageMs - fadeStart) / BUBBLE.fadeMs;
}

/**
 * 말풍선 (8.2 위치, 8.1 모양).
 * @param ax 기준점 화면 x (CSS px) = (artX - camX) * P
 * @param fy 발바닥 선 화면 y (CSS px) = (220 - camY) * P
 * @param P  아트 배율
 * @param canvasW 캔버스 CSS 폭
 * @returns 그린 박스 {bx, by, w, h, tx, ty, tail} (검증용)
 */
export function drawBubble(ctx, layout, ax, fy, P, canvasW, alpha) {
  if (alpha <= 0) return null;
  const { lines, w, h } = layout;
  const ty = fy - ART.headLine * P - BUBBLE.tipGap; // 꼬리 끝
  let by = ty - BUBBLE.tailH - h;
  let tail = true;
  if (by - 2 < BUBBLE.topMin) { by = BUBBLE.topClamp; tail = false; }
  const bx = clamp(round2(ax - w / 2), BUBBLE.edge, Math.max(BUBBLE.edge, canvasW - w - BUBBLE.edge));
  const tx = clamp(round2(ax), bx + BUBBLE.tailEdge, bx + w - BUBBLE.tailEdge);
  const b = by + h;

  ctx.save();
  ctx.globalAlpha = alpha;
  stepBorder(ctx, bx, by, w, h, PAL.hb2);
  ctx.fillStyle = PAL.white;
  ctx.fillRect(bx, by, w, h);
  ctx.fillStyle = PAL.c2;
  ctx.fillRect(bx, b - 2, w, 2);
  if (tail) {
    const C = PAL.c2;
    const L = PAL.hb2;
    const r = (color, x, y, ww, hh) => { ctx.fillStyle = color; ctx.fillRect(x, y, ww, hh); };
    r(C, tx - 4, b, 8, 2);
    r(L, tx - 6, b + 2, 2, 2); r(C, tx - 4, b + 2, 8, 2); r(L, tx + 4, b + 2, 2, 2);
    r(L, tx - 4, b + 4, 2, 2); r(C, tx - 2, b + 4, 4, 2); r(L, tx + 2, b + 4, 2, 2);
    r(L, tx - 2, b + 6, 4, 2);
  }
  ctx.font = BUBBLE_FONT;
  ctx.textAlign = 'left';
  ctx.textBaseline = 'top';
  ctx.fillStyle = PAL.ink;
  for (let i = 0; i < lines.length; i++) {
    ctx.fillText(lines[i], bx + BUBBLE.padX, by + BUBBLE.padTop + BUBBLE.lineH * i + (BUBBLE.lineH - BUBBLE.font) / 2);
  }
  ctx.restore();
  return { bx, by, w, h, tx, ty, tail };
}

/**
 * 닉네임 라벨 (7장). 위 = 발바닥 선 + 6, 높이 20, 가로 = 글자 폭 + 12 (짝수, 최소 24).
 * @returns 그린 박스 {bx, by, w, h}
 */
export function drawLabel(ctx, text, ax, fy, isSelf, canvasW) {
  ctx.save();
  ctx.font = LABEL_FONT;
  const tw = Math.ceil(ctx.measureText(text).width);
  const w = Math.max(LABEL.minW, even(tw + LABEL.padX * 2));
  const h = LABEL.h;
  const bx = clamp(round2(ax - w / 2), LABEL.edge, Math.max(LABEL.edge, canvasW - w - LABEL.edge));
  const by = Math.round(fy) + LABEL.top;
  if (isSelf) {
    stepBorder(ctx, bx, by, w, h, PAL.y4);
    ctx.fillStyle = PAL.y2; ctx.fillRect(bx, by, w, h);
    ctx.fillStyle = PAL.y1; ctx.fillRect(bx, by, w, 2);
    ctx.fillStyle = PAL.y3; ctx.fillRect(bx, by + h - 2, w, 2);
  } else {
    stepBorder(ctx, bx, by, w, h, PAL.ink);
    ctx.fillStyle = PAL.hb2; ctx.fillRect(bx, by, w, h);
    ctx.fillStyle = PAL.hb1; ctx.fillRect(bx, by, w, 2);
  }
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  const cx = bx + w / 2;
  const ty = by + LABEL.textTop + (LABEL.lineH - LABEL.font) / 2;
  if (isSelf) {
    ctx.fillStyle = PAL.y1; ctx.fillText(text, cx, ty + 1);
    ctx.fillStyle = PAL.ink; ctx.fillText(text, cx, ty);
  } else {
    ctx.fillStyle = PAL.ink; ctx.fillText(text, cx + 1, ty + 1);
    ctx.fillStyle = PAL.white; ctx.fillText(text, cx, ty);
  }
  ctx.restore();
  return { bx, by, w, h };
}
