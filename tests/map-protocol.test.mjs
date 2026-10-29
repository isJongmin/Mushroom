import assert from 'node:assert/strict';
import { cleanPresenceState, cleanGameEvent, GAME_EVENTS, stampGameEvent } from '../src/client/backend/common.js';
import { cleanMove } from '../src/client/game/physics.js';

const events = {
  impact: { host: 'host', id: 'peer:2:0', x: 100, y: 170, job: 'archer' },
  atk: { user_id: 'peer', x: 100, y: 200, dir: 'left', seq: 2, job: 'mage' },
  hp: { user_id: 'peer', hp: 50, max: 100, dead: false },
  mobs: { host: 'host', t: 2, list: [{ id: 'mob1', kind: 'snail', x: 1, y: 2, hp: 4 }] },
  drop: { host: 'host', id: 'drop1', buff: 'heal', x: 1, y: 2 },
  pick: { user_id: 'peer', drop_id: 'drop1' },
  picked: { host: 'host', user_id: 'peer', drop_id: 'drop1', buff: 'heal' },
};
const avatar = { hair: 'original' };
const presence = { user_id: 'peer', nickname: 'Peer', avatar, x: 100, y: 200 };
const move = { user_id: 'peer', x: 100, y: 200, dir: 'left', s: 'climb', fx: 'dash-up' };
for (const mapId of [undefined, 'village', 'forest', 'quarry', '__proto__', '../forest', {}, null]) {
  const expected = ['forest', 'quarry'].includes(mapId) ? mapId : 'village';
  const p = cleanPresenceState({ ...presence, mapId });
  assert.equal(p.mapId, expected);
  assert.equal(p.avatar, avatar);
  assert.deepEqual({ ...p, mapId: undefined }, { ...presence, mapId: undefined });
  assert.deepEqual(cleanMove({ ...move, mapId }), { ...move, mapId: expected });
  for (const event of GAME_EVENTS) {
    const legacy = cleanGameEvent(event, events[event]);
    assert.ok(legacy);
    assert.equal(legacy.mapId, 'village');
    assert.deepEqual(cleanGameEvent(event, { ...events[event], mapId }), { ...legacy, mapId: expected });
    assert.equal(stampGameEvent(event, { ...events[event], mapId: expected }, 'self').mapId, expected);
  }
}
assert.equal(cleanMove({ ...move, x: NaN, mapId: 'forest' }), null);
assert.equal(cleanPresenceState({ mapId: 'forest' }), null);
assert.equal(cleanGameEvent('hp', { mapId: 'forest' }), null);
assert.equal(cleanGameEvent('unknown', { mapId: 'forest' }), null);
console.log('Map protocol: legacy defaults, all events, malformed areas, avatar and movement shape pass');
