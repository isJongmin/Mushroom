# Hair silhouettes and RPG wardrobe — 2026-10-29

The seven-part avatar save contract is unchanged. All previous IDs and sprite sheets remain valid. This expansion adds 20 IDs and four presets; it does not assign equipment or combat abilities. Job-themed accessories belong to their top layer, so ordinary wardrobe mixing still works.

| Category | New IDs |
| --- | --- |
| Hair | `bald`, `wolf-cut`, `mohawk`, `pompadour` |
| Top | `warrior-armor`, `archer-ranger`, `mage-robe`, `thief-jacket` |
| Bottom | `warrior-greaves`, `ranger-trousers`, `mage-trousers`, `thief-trousers` |
| Shoes | `warrior-sabatons`, `ranger-boots`, `mage-boots`, `thief-boots` |
| Hat | `warrior-circlet`, `ranger-cap`, `mage-hat`, `thief-hood` |

Hair geometry is independently modeled: bald is fully transparent; wolf cut has long feathered nape/side layers; mohawk leaves shaved sides around one central crest; pompadour has a swept, raised front roll. They do not share a recolored base mesh. `black-wolfcut` remains as a separate existing style.

The warrior has plate chest armor, oversized shoulder plates, bracers and a sheathed sword. The archer has a forest cape, bow, quiver and individually modeled arrows. The mage has a flared robe, bell sleeves, tall stepped hat and crystal staff. The thief has a split jacket, crossed straps, hood and dagger. Staff and dagger follow arm bones in existing walking and attack poses. All assets use the existing 13 animation frames and front/back layer splitting.

Editable source is `assets/_src/voxel/adventure.py`, installed from `model.py`. The bald exception in `build.py` preserves valid transparent PNGs so the explicit selection always has files in the manifest. The generated manifest includes Korean labels and four cohesive presets.

Regenerate all assets with `python assets/_src/voxel/build.py --jobs 4`. For incremental builds, use `--only category:id,... --no-truth`; existing sheets are preserved. Review the new hair without hats and all job presets with `python assets/_src/voxel/adventure_preview.py`; the board includes front, side, back, attack and prone views. Run `python tests/avatar-wardrobe.test.py` to verify the catalog, transparent bald layers, unique geometry, 13-frame dimensions and frame-edge clearance.

Validation: all three wardrobe checks pass. The 20-part incremental build rendered 260 part/pose tasks in 254.8 seconds with four workers. All 52 job preset/pose combinations fit the existing viewport by projected geometry bounds. Only `manifest.json` changes among previously tracked runtime avatar assets; all existing PNG bytes remain unchanged. The review board was inspected before handoff.
