import assert from 'node:assert/strict';
import { bossPatternOrder } from '../src/client/game/garden-boss.js';
import { createGardenPanel } from '../src/client/ui/garden-panel.js';
import { installDomFixture } from './helpers/dom-fixture.mjs';

const fixture = installDomFixture({});
const panel = createGardenPanel({});
panel.el.classList = { toggle() {} };
panel.open();
const detail = fixture.all(panel.el).find(node => node.tagName === 'P');
const options = { village: true, area: 'quarry', connected: true, near: true, now: 1000, bossHp: 300 };
const names = ['수정 융기', '수정 광선', '수정 파쇄', '약점 노출'];
for (const [rev, pattern] of bossPatternOrder('quarry').entries()) {
  panel.paint({ id: 'kragg', rev, mode: 'boss', phase: 'boss', deadline: 150000,
    boss: { pattern, max: 500 } }, options);
  assert.equal(detail.textContent, `${names[rev]} · 149초`);
}
panel.paint({ id: 'kragg', rev: 4, mode: 'boss', phase: 'boss', deadline: 150000,
  boss: { pattern: 'future-pattern', max: 500 } }, options);
assert.equal(detail.textContent, '보스 전투 중 · 149초');
