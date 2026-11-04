# Crowd performance, skill delivery and minimized journey HUD

## Reproduced defects

1. Twenty simultaneous thief ultimates create 180 projectiles. The former 160-entry list silently removed the oldest 20, including their authoritative collision work. Supported room traffic now fits within a bounded 1024-entry simulation pool. Cast overflow prefers ordinary visual entries before an ultimate or authoritative entry.
2. Attack cooldown validation used receiver arrival time with only 15 ms tolerance. A valid three-second sender cadence could be rejected when the second packet arrived 150 ms earlier relative to the first packet. Optional relative cast timestamps and a per-mount session ID permit bounded jitter (at most 250 ms), while receipt deadlines advance from the previous deadline rather than allowing cumulative speedup. Legacy packets retain strict checks; sequence, origin, weapon, damage and skill-unlock validation remain.
3. Host impacts were limited to 40 individual messages per second. The adapters now batch up to 24 acknowledgements into one impact message after at most 40 ms under normal load. Packet rate stays capped at 40 batches/second; pending acknowledgements are bounded at 512. A test sends all 180 acknowledgements in eight messages with no drops. Flat impact messages remain readable.

All room participants should reload after deployment. Older clients do not interpret the new batched acknowledgements; the timestamp extension itself is optional.

## Render work

- At eight players in the same area, or sustained slow frames, presentation switches to a smaller backing-pixel budget and compact remote effects. Own spells keep their complete renderer and all hit/strike simulation runs unchanged.
- Remote spells retain visible, class-colored silhouettes and projectiles rather than disappearing. Remote cosmetic pets reduce to one per owner; own pets remain.
- Pixel budgets: 3.2 million normal / 1.6 million crowded, with DPR caps of 2 / 1.5. Hysteresis avoids switching on every frame.
- Memoize local loadout/stats by saved-state identity and weapon class. Update skill-button DOM only when its displayed tenth-second/state changes.
- The menu offers automatic or compact remote effects, plus an expandable frame-interval/cast/projectile diagnostic readout.

Native-canvas test, 20 simultaneous mixed ultimates, same simulation plans: 34,803 draw calls with full effects versus 2,069 with compact remote effects (94% fewer). One warm run measured 38.2 ms versus 2.1 ms for this renderer alone. These figures are not full-game browser FPS or a 20-device network test.

## Journey window

The chapter window starts minimized, leaving its title and current objective. Expand/minimize is stored per local profile and works even if storage is unavailable. Full objectives, contract rewards and journal access return when expanded.

## Validation

44 JavaScript test files pass. Coverage includes the 180-shot regression, acknowledgement batching and cancellation, sender/arrival jitter, cooldown abuse and reload clocks, replay and malformed packets, bounded render policy, pixel-identical own spell renderer, unchanged authoritative strike plans, cast pool limits, and panel preference persistence. Final browser verification follows deployment.

The separately generated four-character concept board is a design preview. It is not installed as a replacement for saved player sprites in this release.
