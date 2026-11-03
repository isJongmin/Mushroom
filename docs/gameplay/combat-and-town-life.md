# Combat feel and town life

## Combat presentation

Confirmed hits paint a spark/reaction frame, then hold Canvas rendering for 42 ms (62 ms for strong/finishing hits or self damage). Stops have a 180 ms admission interval and cannot be extended by an area attack hitting multiple enemies. Host simulation, movement, collision, cooldowns and network traffic continue. Spectators get local hitstop only from the host-confirmed impact ID matching their own user ID; ordinary remote damage snapshots add reactions without freezing the local view.

Targets receive a brief brightness change, visual recoil and bounded spark particles. Self damage adds a small camera impulse and a warm border. Reduced-motion mode disables holds, shake, recoil and moving particles. Effects clear on travel/teardown and do not change damage, actual knockback or animation/cooldown contracts.

Each regional boss has its own title, portrait, short line and world effect: spores, crystal fissures, roots or ice sigils. These play during the existing five-second pre-battle countdown, end before attack telegraphs begin, skip expired joins and deduplicate snapshot revisions. The ordinary quest card hides while the entrance card is visible.

## Social encounters

Each area has its existing mascot plus a new harmless encounter:

| Region | NPC | Interaction |
| --- | --- | --- |
| Village | 방향치 핀 | Give directions; receive a comic response |
| Quarry | 퇴근왕 두식 | Rock-paper-scissors, no stakes |
| Forest | 낮잠술사 도리 | Flavor-only adventure fortune |
| Frost | 썰렁 대장 포그 | Short cold-weather jokes |

Approach within 130 world units and 75 vertically; use the nearby dialogue button or E. Choices update the portrait dialogue and briefly emit a world reaction. Games do not spend or award items, currency, trait points or stats. Selected avatars are validated against the actual wardrobe manifest.

## Simultaneous mobile actions and guidance

Skills activate on pointerdown, including non-primary touch pointers, with pointer capture per control. Compatibility clicks are ignored; keyboard/assistive clicks remain available. Movement, jump and held attack release only their own pointer. Cancel/lost capture/blur reset the corresponding controls. Skills still enforce death, rope, connection, unlock and cooldown rules.

The combo notification sits eight CSS pixels below the measured minimap bottom, recalculated on layout and map expansion. Mobile skill buttons show icons, locks and cooldowns. Event status uses a short pattern/timer and HP bar.

Movement, skills, bag, traits, NPCs, minimap, taxi, drops and boss encounters each have a short seven-second first-use hint. Seen flags persist separately per local profile; errors writing these flags cannot block play. Hints never grab focus or pause input, appear inside an open dialog when appropriate, and are dismissible. The menu's control guide can be reopened. Permanent helper paragraphs were removed from routine inventory/trait interfaces.

## Taxi, minimap and signs

The taxi is parked at a dedicated western stop (spawn −800, clamped to x245) and serves every unlocked town for free. Destination buttons show the current town and required weapon grade for locked towns. Both selection and travel recheck unlocks, connection, life, proximity (160 horizontal /85 vertical) and travel cooldown. Taxi and portals share area transition logic, clearing transient attacks, restoring per-area snapshots and announcing the new map through existing network presence. Equipment, pets, HP and cooldown progress are retained; taxi arrival uses the destination spawn.

Minimap colors: yellow self, blue other players in this area, green NPCs, pink enemies, lavender portals. Nearby NPC projections use separate lanes when needed. Quest, pet, mentor, mascot, fun NPC and taxi positions are included.

District signs choose a display position at least 160 world units from exploration flags at the same level. For example, the mine entry sign moves onto the y655 platform while the exploration flag stays at ground level at x650. Point IDs, discovery progress, terrain and NPC locations are unchanged.


## Ground drop expiry

Uncollected equipment and coin piles expire three minutes after the host's kill timestamp. Each saved pending drop has an absolute expiry, which is preserved across reloads and travel. Future sender timestamps are clamped to receipt time; expired late packets retain kill evidence and receipt deduplication without restoring ground loot. Old saves lacking timestamps get a single three-minute grace period during their first ensure transaction.

Rendering, companion targeting and auto-pickup ignore expired drops immediately. A once-per-second store transaction removes expired pending records in every region, and the collect transaction rechecks its own deadline. Expiry cannot remove owned inventory or awarded currency. New tests cover boundary timing, legacy migration, delayed/replayed messages and concurrent collect/expiry transactions.

## Validation

35 JavaScript test files cover existing combat/progression/network behavior and the new frame gating, multi-pointer lifecycle, first-use persistence, boss entrance deduplication, RPS outcomes, taxi guards, minimap colors and sign clearance. Browser QA uses dedicated local test profiles and temporary fixtures, including synthetic input/seeded unlocked equipment. Fixed-width fixtures check 360px and 390px portrait and 740×360 landscape minimap gaps. Temporary browser fixtures and the QA-only timer frame driver are not shipped. Real physical multi-touch hardware was not available; simultaneous touch was checked through the actual input binders with distinct pointer IDs.


## Taxi and arrival presentation follow-up

The taxi uses a larger faceted mushroom canopy, luggage rack, checker trim, bevelled wheels and a stop pole. Its shared wardrobe driver is shown both in the cab window and the greeting portrait. Opening the route menu starts with “어디로 가드릴까요~?”. The fun NPC moves slightly east to keep the western stop clear.

Initial entry shows only the town name as an arrival overlay. Routine joining banners/dots and constructor-time quest-card flashes are removed; actual connection errors retain retry actions. Event HUD/results require an explicit local request or observed participation, so cached/unrelated events cannot open a welcome popup.

Every NPC action uses the same compact speech glyph drawn on Canvas before actors. Transparent 44px DOM targets preserve tapping and keyboard focus without painting a layer over characters; their z-index is 1. NPC interaction ranges, taxi unlock rules and travel state remain enforced. A join-time boss card is suppressed without replaying it after the town reveal.

Level-based character growth remains a design proposal; no level/XP or combat balance changes are included.
