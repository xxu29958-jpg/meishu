# Art decisions

The record of what has been decided about how this game looks, and why. Newest decisions at the top of each section. Asset-level detail lives in `design/art/` and `design/ui/`.

## Identity: Campaign Atlas

One idea carries every domain: **the war as it looked on the maps, prints and desks of the men who fought it.** Hand-coloured engraving, not painting and not cartoon.

- **Line.** A warm sepia-black ink contour of slightly uneven weight. Heavier on silhouettes, lighter inside.
- **Colour.** Flat gouache washes in a limited palette, toned as if on laid paper. Form comes from a second darker wash and from engraver's hatching, not from soft gradients.
- **Palette roles.** Painters ask for roles (`ink`, `grass`, `fr_blue`, `ui_brass`), never hex values. A batch's `palette.json` is the only place colour lives, so a theme can be re-toned without touching a painter.
- **Light.** Upper left. Buildings, portraits and interface are lit from there and cast to the lower right. Units and flags take top light only, because `mirror-x` would otherwise flip their lighting when they face left.
- **Finish.** A fine paper grain over everything; no glow or blur except where an effect or a selected control calls for it.

### Tone: iron and blood (Owner direction, 2026-11-10)

The first pass was gentle: pastel washes, visible hex rules, toy-soldier proportions. The Owner's correction: this is the age of iron and blood, a world of empires, invasion and gunpowder, and the art must carry strength, tension and historical gravity. Applied as:

- Deeper inks and harder contrast; storm-toned seas with engraved lining; darker, less saturated country.
- Soldiers at about five and a half heads with weathered faces, drawn as formed bodies of men rather than single figures: a file of three infantry, a pair of troopers.
- Interface in brass, oxblood enamel, gunmetal and worn parchment on a desk lit by one lamp, corners in shadow.
- Damage is drawn plainly: burnt roofs, breached walls, standing smoke.

Still to push in later batches: relief shading for mountains, weather, battle-worn unit variants, war-map annotation (frontiers, march lines) on the strategic map.

## Maps: continuous, hexes underneath (Owner direction, 2026-11-10)

**Hexes must not be visually obvious.** The map is one continuous painted landscape; the hex grid is gameplay structure and placement logic only.

- No grid lines and no hex-shaped terrain blocks in any terrain art. An optional grid overlay (`maps.grid.hex`) exists for the game to show on demand.
- Ground textures repeat on the hex lattice, so pieces can overlap their neighbours freely.
- Land pieces are larger than the hex and end in a feathered, wandering edge.
- Coasts are under-layers whose unions form one organic shoreline.
- Strategic maps (Europe, Americas, world) will be painted as continuous cartography from geographic data and delivered in chunks; the terrain kit composes what sits on them and serves battle maps.

Recipe, formats and the plan for the world map: `design/art/maps.md`.

## Units

- Neutral ids carry the theme's default look: in `campaign-atlas-01`, `units.infantry.line` is a French fusilier and `units.cavalry.light` a French chasseur à cheval. National variants are new ids, `units.<entity>.<unit>`.
- A unit is a **drill** (poses and clip timing) performed by a **look** (uniform and kit). Both are data. New regiments are look records; new arms are drills.
- Frame counts are set by the action, not by a fixed grid: infantry 8/8/6/10/5, cavalry 8/8/7/6/5 for idle/move/attack/recover/finish.
- The muzzle flash and first smoke are drawn into the attack frames. The v1 manifest has no attachment points, so a separate muzzle effect could not be placed. See Questions.
- Musket carried on the viewer's side in both facings: historically the left shoulder, correct only when facing left. A consequence of `mirror-x`, accepted for legibility.

Research and adjustments by unit: `design/art/units.md`.

## Portraits

- One original drawing per character on the 512×640 bust canvas; every crop is the same drawing re-rendered through a crop box, never a resample.
- Each character records what is documented and what is interpreted (`character.json`).
- Heads are drawn slightly over life against the body, as state portraits of the period were, which also helps the avatar read.

## Buildings

- Bird's-eye vignettes assembled from a small primitive library by plan data; a regional family is a new plan file.
- One shared ground point and projection for every building.
- **No ownership flags are painted in.** Proposed treatment: the game draws the owner's `identity.*.flag` at a mast point and tints a base ring with `map_color`. The mast point is not expressible in manifest v1. See Questions.

## Interface

- Design canvas 1280×720, safe inset 48, minimum touch target 48.
- Four states are painted per control: pressed sinks and darkens, selected takes a gilt rule and glow, disabled loses colour and relief.
- No text in any image. Type, spacing and wrapping rules: `design/ui/README.md`.

## Questions raised for integration

1. **Attachment points.** Muzzle, flag mast and similar points need a place in the manifest. Proposal for a v2: optional `points: {"muzzle": [x, y], ...}` per asset in frame pixels, with optional per-frame overrides. Compatible: v1 readers ignore it if the schema allows the field; it needs a `contract_version` bump because v1 rejects unknown fields.
2. **Layered map drawing.** The coast recipe needs all coast layers drawn before any land piece. Can the renderer draw terrain in passes?
3. **Frame sizes beyond the recommended canvases.** Land pieces are 176×198 and coast aprons 240×270 so they can overlap neighbours. Display sizes keep the 8:9 ratio.
4. **Region chunks.** ASSET-SPEC describes 516×516 chunks for regional maps but no id or placement convention. Proposal in `design/art/maps.md`.
