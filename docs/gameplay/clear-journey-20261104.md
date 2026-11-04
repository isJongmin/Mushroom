# Readability and a clearer adventure loop

The final theme layer pairs dark readable text with opaque paper surfaces and light readable text with dark world overlays. Supporting copy, item grades, quest descriptions, chat, disabled skills and empty states retain contrast rather than fading text through opacity. Rarity remains visible through its label and item border. `tests/readability.test.mjs` measures the palette pairs and verifies a minimum 4.5 contrast ratio; this does not replace visual review of all composited screens.

The journey HUD now shows the existing 20-kill contract counter, actual guaranteed weapon/gold reward, and the approximate hunt count to the next level. The primary action names the destination or opens the relevant existing task UI. New adventurers start with a guide to the first mentor. Accepted boss/defense quests point to the event NPC rather than falling back to generic hunting.

The adventure journal presents all four chapters, unlocked destinations, real kill/quest records, remaining quest evidence, current skill unlock requirements and the next action. Reading it does not award resources or change saved progression. A collected weapon that improves the active weapon's type produces a dismissible comparison shortcut; it never automatically equips or spends currency. First kills and completed contracts receive short feedback through the existing bounded loot feed.

The reward economy, paid-free model, save schema and multiplayer authority are unchanged. Tests verify that advertised contract rewards match actual loot transactions, boundary counts, class-specific skill hints, nonmutating journal reads, upgrade comparisons and accepted boss guidance. All 43 JavaScript test files pass before deployment verification.
