# NPC quests, mobile boss and attached rewards — 2026-10-31

## Quest entry

Village NPC **숲지기 모리** stands 165 world units left of the patch. Click the exclamation marker above the NPC to open the quest chooser, then select **버섯마을 지키기** or **버섯왕 도전**. It accepts starts within 230 horizontal units / 100 vertical units of the NPC. The persistent idle quest card is replaced by this interaction. Active objective progress and terminal results remain visible automatically. NPC marker supports keyboard focus and is hidden outside the viewport/area.

## Motion and hit geometry

Boss art is now made entirely from faceted cuboids: stepped mushroom cap, cream stem, legs, arms, staff and mushroom circlet. No rounded/ellipse boss silhouette. Stomp compresses, leaps up to 260 world units toward a preselected landing point, then lands and recovers. Spore phase runs with short hops; ring phase bounds back toward the arena center. The home and phase origin are included in sanitized state, so host takeover reproduces the same trajectory.

Host simulation updates the boss's real x/y every frame; mob snapshots preserve airborne y on handoff. Ground attacks therefore do not hit the grounded hitbox while the boss is high overhead. Warning ranges and damage checks use the same predicted landing point. Motion is bounded to the arena; the exposed phase stays still for a readable punish window.

## Defense pressure

Existing initial waves are retained, with 2/3/4 delayed reinforcements five seconds after wave 1/2/3 starts. Solo totals rise from 12 to 21 enemies. Wave completion waits for the queued reinforcements. Crowded lanes retry safely, timeout still takes priority, and simultaneous invaders remain capped at 12 (global cap unchanged).

Variants: **급습 슬라임**, 1.65× base speed and .9× HP; **단단한 버섯**, .9× speed and 1.7× HP. Wave 2/3 select mixed lanes, and marks identify the fast/tough variants. There are no attack-upgrade drops or permanent stat changes.

## Costume fitting

`royal-guardian` reward/save ID remains stable; display name is **버섯 왕관과 망토**. A low mushroom-decorated circlet replaces the generic pointed crown. It occupies the hat rendering layer while equipped, leaving the stored original hat intact. All reward capes now have narrow fabric collars and attached clasps, not detached shoulder pads.

The avatar renderer measures head top/center and shoulder placement from each composite frame, caching only anchors. Outfit follows facing, walking sway and back/climbing view; prone hides it. Cape back layers draw behind the body; the collar/clasp draw in front. Existing reward unlock conditions are unchanged.

Validation: 12 relevant Node test files pass (including motion/costume regression, quest state/reinforcements, protocols, projectiles and prior skill choreography). Browser QA checks NPC selection, actual boss movement/pattern progression, wardrobe front/back fitting, 390px mobile NPC interaction/menu layout, delayed reinforcement arrival and local runtime logs. Reward fitting uses a preview-only fixture on a QA profile; no fixture is committed. Live Supabase multiplayer and statistically meaningful solo difficulty/clear rates are not measured here.

## Progression discussion (proposal, not implemented)

Prefer a limited permanent level/mastery track that unlocks skill variations over unrestricted damage inflation. Keep the three currently available skills; e.g. offer a choice of upgrades at levels 3/6/9, with modest capped stat growth. Share encounter XP among active contributors rather than awarding only last hits. Persist power-affecting progression authoritatively before introducing competitive or valuable rewards. This remains a design proposal pending the user's choice.
