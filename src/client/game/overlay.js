// 닉네임 라벨(style-guide 6장)과 말풍선(7장). 모두 화면 CSS px 기준이며 Canvas fillText로만 그린다.
import { BUBBLE, LABEL, COLORS, FONT_UI } from '../constants.js';

const LABEL_FONT = `700 ${LABEL.font}px ${FONT_UI}`;
const BUBBLE_FONT = `400 ${BUBBLE.font}px ${FONT_UI}`;
const ELLIPSIS = '…';

/** 공백 기준 줄바꿈, 공백 없는 긴 글은 글자 단위. 최대 줄 수를 넘으면 마지막 줄 끝을 …으로 자른다. */
export function wrapText(ctx, text, maxWidth, maxLines) {
  const fits = (s) => ctx.measureText(s).width <= maxWidth;
  const lines = [];
  const words = text.split(/ +/).filter((w) => w.length);
  let cur = '';
  const pushChars = (word) => {
    // 글자(코드포인트) 단위로 쪼개 넣는다
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
  let last = Array.from(out[maxLines - 1]);
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
  const w = Math.min(BUBBLE.maxW, Math.max(BUBBLE.minW, Math.ceil(tw) + BUBBLE.padX * 2));
  const h = lines.length * BUBBLE.lineH + BUBBLE.padY * 2;
  return { lines, w, h };
}

export function bubbleAlpha(ageMs) {
  if (ageMs >= BUBBLE.showMs) return 0;
  const fadeStart = BUBBLE.showMs - BUBBLE.fadeMs;
  if (ageMs <= fadeStart) return 1;
  return 1 - (ageMs - fadeStart) / BUBBLE.fadeMs;
}

/**
 * @param tipX,tipY 꼬리 끝(아바타 머리 위)의 화면 좌표
 * @param viewW 캔버스 CSS 폭 (좌우 8px 안으로 밀어 넣기)
 */
export function drawBubble(ctx, layout, tipX, tipY, viewW, alpha) {
  if (alpha <= 0) return;
  const { lines, w, h } = layout;
  const bottom = tipY - BUBBLE.tailH;
  const top = bottom - h;
  let left = tipX - w / 2;
  left = Math.max(BUBBLE.edge, Math.min(left, viewW - BUBBLE.edge - w));
  // 꼬리 밑변은 본체의 둥근 모서리를 피해서 놓고, 끝은 항상 아바타 x를 가리킨다
  const half = BUBBLE.tailW / 2;
  const baseX = Math.max(left + BUBBLE.radius + half, Math.min(tipX, left + w - BUBBLE.radius - half));

  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.lineWidth = BUBBLE.border;
  ctx.lineJoin = 'round';
  ctx.strokeStyle = COLORS.bubbleBorder;
  ctx.fillStyle = COLORS.bubbleBg;

  ctx.beginPath();
  ctx.roundRect(left, top, w, h, BUBBLE.radius);
  ctx.fill();
  ctx.stroke();

  // 꼬리: 본체 테두리를 덮어 이어 붙이고 양옆만 테두리
  ctx.beginPath();
  ctx.moveTo(baseX - half, bottom - 1);
  ctx.lineTo(tipX, tipY);
  ctx.lineTo(baseX + half, bottom - 1);
  ctx.closePath();
  ctx.fill();
  ctx.beginPath();
  ctx.moveTo(baseX - half, bottom);
  ctx.lineTo(tipX, tipY);
  ctx.lineTo(baseX + half, bottom);
  ctx.stroke();

  ctx.fillStyle = COLORS.bubbleText;
  ctx.font = BUBBLE_FONT;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  const cx = left + w / 2;
  for (let i = 0; i < lines.length; i++) {
    ctx.fillText(lines[i], cx, top + BUBBLE.padY + BUBBLE.lineH * i + BUBBLE.lineH / 2);
  }
  ctx.restore();
}

/** 라벨 상단 = 발 화면 y + 4, 가로 중심 = 기준점 x */
export function drawLabel(ctx, text, cx, footY, isSelf) {
  ctx.save();
  ctx.font = LABEL_FONT;
  const tw = Math.ceil(ctx.measureText(text).width);
  const w = tw + LABEL.padX * 2;
  const h = LABEL.lineH + LABEL.padY * 2;
  const x = Math.round(cx - w / 2);
  const y = Math.round(footY + LABEL.gap);
  ctx.fillStyle = isSelf ? COLORS.labelSelfBg : COLORS.labelBg;
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, LABEL.radius);
  ctx.fill();
  ctx.fillStyle = isSelf ? COLORS.labelSelfText : COLORS.labelText;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(text, x + w / 2, y + h / 2 + 0.5);
  ctx.restore();
}
