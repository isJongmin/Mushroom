# Arcade RPG presentation

The game now shares dark navy panels, warm metal borders, strong gold headings, mint growth values and coral attack controls. Inventory, NPC dialogue, traits, character selection and lobby use the same skin in `arcade-rpg.css`, loaded after layout styles. Existing interaction labels, tab semantics, focus traps and compact bag shortcut remain in place.

## World and characters

| Region | Local mascot | Entry landmark / scenery |
| --- | --- | --- |
| Village | Popo, mushroom courier | Mailbox, guild pennants |
| Quarry | Ttakkong, mole engineer | Crystal cart, luminous ore |
| Forest | Lumi, sleepy seed spirit | Sleeping tree, seed lanterns |
| Frost | Bosong, cold-sensitive snow spirit | Scarf snowman, ice bells, snowy firs and mountain peaks |

Canvas artwork lives in `game/adventure-art.js`; all props are cosmetic. Mascots are sorted with scene actors by foot position, culled outside the viewport and never create quest/reward state. Pet faces blink and react to loot, damage and attack. An optional cosmetic neck scarf follows the avatar rig; it is suppressed while climbing, prone or wearing reward costumes. Existing face, hair and wardrobe assets remain selected by the user.

Region arrival appears for 2.8 seconds and then disappears through the existing frame loop, without extra timers. Motion preferences freeze mascot bobbing/blinking, scarf flutter and scenery sway. Artwork does not alter terrain, collision, movement, pet spacing, three-pet limits, damage, quests or saved progression.

## Validation

29 JavaScript test files passed. New real-Canvas checks cover distinct region silhouettes, biome renders, transform restoration, reduced motion, offscreen culling and costume/climb scarf suppression. Browser checks covered the actual local character/lobby/village/inventory screens, plus isolated real-component NPC/trait/inventory panels inside a 390×844 iframe and region scenery fixtures. Fixtures use starter data and were removed before committing; no production saves were changed.
