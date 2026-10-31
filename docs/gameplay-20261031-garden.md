# 버섯밭 지키기 — 2026-10-31

## Player flow

Lobby introduces the event and shows browser-local clear count. Enter a room and stand within 260 world units of the village spawn / mushroom patch to start. Living participants can request a start; the elected area host validates proximity and handles the encounter. Solo play is allowed.

- 5-second preparation; 3 waves; 4-second breathers; 40-second deadline per wave.
- 3 / 4 / 5 enemies for solo, +2 per additional player up to +8 (maximum 12 per wave). Player count is sampled at wave creation.
- Dedicated event enemies approach from both sides, marked with gold rings and arrows. Existing class attacks and damage collision handle them.
- 100 garden durability. Each enemy that reaches the patch costs 20. Zero durability or an unfinished wave timeout fails. Clearing wave 3 with durability remaining succeeds. Enemies are removed at the terminal result; event enemies never enter normal respawn queues.
- Result card includes wave, kills, remaining durability and personal damage/kills. Close keeps free movement/chat available. Restart has a 5-second cooldown and still requires proximity.
- Participants who damage an event enemy during a successful run unlock the cosmetic **새싹 수호자**. It can be equipped immediately or toggled in the character studio. The nameplate is broadcast with Presence.

## State and limits

`game/garden.js` owns a bounded serializable state machine. State rides existing 5Hz `mobs` messages, not an extra channel. `garden-start` is the only new request type. `backend/common.js` validates fields, bounds and participants; room checks the elected host and area. Old/stale run revisions cannot overwrite newer state. The mob snapshot and encounter state are inherited on host change. Recent area snapshots expire after 30 seconds without updates; abandoned events reset instead of auto-clearing absent enemies. Disconnected clients do not advance the encounter.

Event zone is appended consistently to village zones. It reuses bounded mob simulation and spawn exclusion around players. If both spawn lanes are occupied the encounter retries without advancing; partially available lanes spawn the safe subset. A dedicated zone prevents world monsters contributing to the objective or event kills respawning.

Rewards live beside the existing local profile under `<profileKey>:garden-rewards`, not inside avatar assets. Repeated terminal packets do not grant duplicate rewards (session set plus last 64 completed run IDs). Storage failures are reported on the result. This is a cosmetic local progression system, not a server-verified economy; peer-hosted broadcast and local storage retain existing client-trust limitations. No currency, purchase or competitive leaderboard is attached.

## Verification

10 relevant Node test files pass: garden, jobs, profile-jobs, map-protocol, projectiles-respawn, skill-patterns, ultimate-choreography, areas, wardrobe-loader, normal-skill-visuals. Existing avatar-hat raster test could not run because its `@napi-rs/canvas` dependency is absent; avatar rendering code/assets are unchanged.

Browser local mode: room creation, start and enemy waves, two-client state agreement, reward/result UI from a deterministic encounter fixture, title unlock/equipment in real wardrobe, lobby record, and 390px mobile layout. Fixture pages are preview-only and are not committed. No live Supabase multi-user session or full human-play balance study was performed.
