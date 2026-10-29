# Fine-pixel character and monster revision

Base: `f6e29ff173f33a4dee1e58ed638f2fb8234256e0`.
Review branch: `art/fine-pixel-preview`.
Publishing: user approval is required before pushing these changes to `main`.

## Visual changes

- Avatar surface cell: 3.64 -> 1.82 asset pixels. Geometry stays at the existing fine SDF resolution; changing this surface constant does not shrink the character.
- Slimmer torso and limbs, lower portrait camera, softer skin texture, clearer clothing colors and cooler fill light against the existing warm village.
- Rebuild every existing skin, face, hairstyle, top, bottom, shoe and hat. Saved part IDs and customization remain compatible.
- Generate all 13 existing source poses, including the two attack poses that were absent from the previously installed 11-frame manifest.
- Five monster species: frame-local 2 px clusters, one 64-color palette per species animation, restrained warm grading. Movement, damage, anchors, frame order and hitboxes are preserved.
- Runtime `pixelArt` flag disables smoothing only while a monster is drawn. Canvas state is restored afterwards.
- Versioned sprite URLs keep previously cached 11-frame avatar sheets separate from this 13-frame release.
- Contact shadows use a warm neutral tint and reduced clothing contribution, calibrated against full-geometry reference renders.

## Sources and rebuild

```bash
OPENBLAS_NUM_THREADS=1 python assets/_src/voxel/build.py --jobs 6 --src-out assets/_src/voxel/out/fine-pixel
python assets/_src/art2d_mob/build.py snail mushroom slime bat golem
python assets/_src/review_fine_pixel.py --before-ref f6e29ff173f33a4dee1e58ed638f2fb8234256e0
python assets/_src/voxel/check.py --fast --src-out assets/_src/voxel/out/fine-pixel
```

Review boards under `assets/_src/fine-pixel-review/` are composed from the runtime sprite sheets. The village board uses the existing map and its world-to-image scale; it is an art composition, not a browser screenshot. `motion.gif` cycles through every avatar pose. The map itself is unchanged.

## Validation

- Five monster sheets: dimensions, nonempty animation frames, 2 px cluster alignment and unchanged gameplay metadata checked.
- Pixel finishing repeatability checked on a sample input.
- Runtime normalization and draw path checked for every species, including restoration of the canvas smoothing state.
- Full browser and live Supabase integration are outside this asset-only validation.

Avatar validation completed: all 112 installed PNGs decode, manifest/files agree,
all 13 poses fit the existing frame and anchor rules, and the six presets plus
40 randomized outfits pass the bounds checks. The six preset layer-vs-full RGB
errors are 5.887, 4.142, 3.952, 2.648, 4.965 and 5.350 (existing limit: 6/255).
Alpha error remains below 0.21/255 (existing limit: 2/255).
`check.py --fast --src-out assets/_src/voxel/out/fine-pixel` passed; the expensive
second complete determinism build was not run. Monster finishing repeatability
was checked separately. All five review files decode and the motion GIF contains
all 13 poses.
