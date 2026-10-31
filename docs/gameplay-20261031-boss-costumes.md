# Boss, costumes and event balance — 2026-10-31

Village event panel now offers a separate **버섯왕 도전** encounter. A five-second preparation leads to a 150-second fight. Its health is 1400 × (1 + 0.65 × (participants−1)), sampled at spawn and capped at 20 participants. The boss appears 260 units to the right of the patch; if that position overlaps a player it waits until clear. No contact damage or forced overlap.

Patterns cycle: stomp (1.8s warning, jump above 85 units), targeted spores (2.2s warning, leave a 105-unit radius), outer ring (1.8s warning, move inside 145 units or jump above 110), then six seconds of weakness (1.5× damage). Warnings show ground ranges plus explicit text. Boss health, phase sequence and target position ride the existing host mob snapshots. Hit processing remains player-authoritative like existing contact damage; local cosmetic rewards are not cheat-proof or cross-device inventory.

Boss appearance, cap/eyes/crown/staff, warnings and costume capes are procedural Canvas assets. Costumes: **새싹 정찰대** after one defense clear, **꽃잎 기사단** after three defense clears, **버섯왕 수호대** after one boss clear. Existing clear records migrate without reset. Costumes have no stats. They can be previewed/equipped/removed in wardrobe and appear to peers through Presence. Prone hides the overlay to avoid clipping. The boss result offers immediate crown-costume equip.

Contribution now counts actual health removed, capped by remaining HP, instead of overkill numbers. It records job, damage, boss-only damage and kills, and displays personal damage share. Existing damage and kill rewards remain shared participation-based; no last-hit-only reward.

## Balance review

See `event-balance-20261031.md` and `scripts/event-balance-report.mjs`. Assumptions: mean damage, every projectile hits a single target, skills used every cooldown, basic uptime reduced by skill animations. Model excludes movement, range, dodges, spread misses and AoE target count. Thus it identifies a raw ceiling disparity, not class win rates.

Event-only multipliers: warrior .85, archer 1.22, mage .85, thief 1.45. Modeled ceilings become approximately 99 DPS each versus 68–117 before. Ordinary world combat is unchanged. Warrior still has melee exposure; mage AoE and archer fan shots differ in practical reach, so empirical solo/party clear rates still need playtesting. These factors are a first-pass event adjustment, not a claim of final balance.

Validation: 11 relevant Node files pass including boss/garden lifecycle, snapshot migration, HP bounds, spawn exclusion, no respawn, costume reward gating, existing attack patterns and projectile collision. Browser local QA verifies boss start/appearance/pattern transitions, wardrobe selection and rendering; no live Supabase multi-user test or statistically meaningful class win-rate trial was run.
