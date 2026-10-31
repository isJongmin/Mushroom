# Equipment progression proposal

Status: design only, not implemented.

Hunt → loot → equip or sell → fuse → unlock skills → challenge a stronger encounter.

## Initial rules

- Four main-weapon pools: sword, bow, staff and claw, each 25%. Shields use a separate auxiliary pool, so warrior main-weapon progression does not advance twice as fast.
- Equip only class-compatible gear. Show current ATK/DEF, comparison deltas and fusion result before committing.
- Two same-kind, same-grade items become one item of the next grade, with guaranteed success initially. An equipped item cannot silently be consumed.
- Five initial grades: common, uncommon, rare, epic, legendary. Illustrative attack values: 20 / 26 / 34 / 44 / 57; tune against real class attack patterns. Shields principally grant defense.
- Grade advancement consumes 1 / 2 / 4 / 8 / 16 common equivalents. Cap initial grades to keep doubling costs manageable.
- Selling off-class loot funds class equipment boxes or materials; boss/quest rewards guarantee some class progress. Avoid buy/sell arbitrage.
- Keep one attack skill available from the start. Higher weapon milestones unlock auxiliary skills, ultimates or variants. Record highest achieved grade per class so swapping or fusing equipment does not erase learned skills; retain three active skill slots.
- Stronger encounters introduce new patterns and clear unlock requirements. Do not scale every old monster upward with equipment: old enemies becoming easier is part of visible progress.

## Implementation boundary

Current browser-local rewards and peer-hosted combat are insufficient as authority for a permanent shared equipment economy. Persistent item IDs, ownership, creation, sale, fusion and unlock milestones should be validated server-side. Fusion must atomically consume exactly two eligible items and create one output, with idempotency and concurrency protection against simultaneous sale/fusion. Start with inventory/drop/equip/sell, then fusion and skill milestones, then encounter balance.

These are design hypotheses, not measured retention or class-balance results.
