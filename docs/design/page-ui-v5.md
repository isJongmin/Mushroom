# Page UI v5 — 2026-10-30

The profile studio, lobby, room list and lobby dialogs use a warm cream / forest-green visual system. `src/client/page-ui.css` is the page-only override loaded after the legacy UI kit and game styles. It supersedes the old block-only/no-rounded-corners rules for these pages. Combat behavior and the game HUD remain on the existing skin.

- Shared introduction uses the existing village artwork; no remote font or image dependency.
- Profile: branded header, return-to-lobby action in edit mode, preview/nickname column, wardrobe, full-width job picker and save row. Mobile orders preview, nickname, jobs, wardrobe, actions.
- Lobby: profile header, village introduction, room list, empty/loading/error states and room creation/password/deletion dialogs.
- Rounded controls, clear checked/disabled/hover/focus states, quieter borders and typography. Existing ARIA, keyboard interaction, focus trap and safe text rendering are retained.
- Mobile layouts at 719px; intermediate layout at 850px; reduced-motion support.

Validation: profile/wardrobe tests; browser local-mode profile save, job change, wardrobe tab switching, room creation and entry. Desktop plus 390px iframe viewport inspected; no horizontal overflow. Real Supabase multiplayer was not part of this UI verification.

## Proposed gameplay follow-up (not implemented)

1. Exploration journal: find hidden landmarks and monster entries, earn cosmetic titles and show recent discoveries in the lobby. Progress should persist in an authoritative account model before cross-device rewards are promised; current profiles are browser-local.
2. Short cooperative encounters: rescue a villager, escort a lantern, defend a mushroom patch; clear beginning/end and a shared reward rather than competing for last hits.
3. Boss with readable patterns and a stagger window: turn movement, dodge timing and ultimate cooldowns into decisions.
4. Run-specific three-way skill modifiers: arrow ricochet vs charged shot; claw chains vs lightning marks. Choose attacks that change behavior, not flat damage alone.
5. Team result cards: highlight rescues, exploration and boss staggers as well as damage; quick rematch with the same party.

Recommended first slice: one small cooperative event, one cosmetic milestone, one result card. Measure completion, voluntary replay and class balance before adding more systems.
