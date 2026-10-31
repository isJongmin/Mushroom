# Appearance polish — 2026-10-31

- Removed procedural hand and sleeve overlays from rope climbing; preserved the back-facing sprite and climbing bob.
- Removed front cape collars/clasps. Side-facing cloth stays behind the body; rear hair is restored above the cape using the actual cached avatar layers.
- Replaced the quest NPC placeholder with the shared player avatar renderer, a forest ranger outfit, explorer hat, idle breathing and a readable nameplate. Room initialization preloads its assets.

Validation: appearance-layers, boss-motion-costume, garden-boss, profile-jobs, wardrobe-loader, garden and map-protocol tests passed; syntax checks and git diff checks passed. Browser gallery inspected actual front/rear/climbing costume and NPC rendering with no console errors. Live multiplayer was not exercised.

Equipment progression remains a proposal; no loot, economy or skill-unlock behavior changed in this patch.
