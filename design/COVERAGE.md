# Coverage

The one record of what the assignment covers, what is delivered, and what is left. Updated with every batch. Scope: six art domains and Global Conquest content design (handoff v0.7).

Legend: **done** = delivered in a validated batch · **part** = started, list says what exists · **none** = not started.

Last updated with batch `campaign-atlas-01`.

## A. Interface

| Item | State | Delivered / remaining |
| --- | --- | --- |
| Component system | part | Panel, primary and secondary button, tab, list row, resource chip, section rule, 3 icons, backdrop; all four states. Remaining: checkbox, slider, tooltip, scrollbar, progress bar, full icon set |
| Type and layout rules | done | `design/ui/README.md` |
| Screen viewer | done | `previews/screens.html`: flow + display data, three viewports |
| Startup and main menu | part | Main menu composed. Startup/splash none |
| Campaign, conquest, year, nation, scenario selection | none | |
| Headquarters and commander detail | none | |
| Recruitment | done | With confirm dialog, empty and unaffordable states |
| Shops, trading, taverns | none | |
| Equipment, inventory, technology, academy, promotions | none | |
| Princess and character collection | none | |
| Achievements and rewards | none | |
| Battle HUD and unit inspection | none | |
| Action and purchase confirmation | part | Purchase confirmation done; action confirmation none |
| Dialogue, events, turn notices | none | |
| Victory and defeat | none | |
| Tutorials | none | |
| Settings and pause; save, load, continue | none | |
| Loading, unavailable, empty, error | part | Empty and disabled states shown in recruitment |

## B. Maps

| Item | State | Delivered / remaining |
| --- | --- | --- |
| Seamless terrain method | done | Lattice-repeating grounds, feathered pieces, coast layers; `design/art/maps.md` |
| Water, coast | done | Open sea, shallows, three coast layers |
| Plain, forest | done | Plain, tilled plain, mixed forest |
| Rivers, mountains, snow, desert, wetland, roads | none | |
| Regional composition | part | One demonstration coast scene. No real geography yet |
| Europe map | none | Needs geographic data (decision pending) |
| Americas map | none | |
| World map (4096×2048, chunked) | none | |
| Political overlays | none | Style described in theme; no assets |

## C. Units and animation

| Item | State | Delivered / remaining |
| --- | --- | --- |
| Foot rig and musket drill | done | Five clips, formation, rippling volley |
| Horse rig and sabre drill | done | Five clips, pair formation |
| Infantry | part | French line fusilier, Old Guard grenadier. Remaining: light infantry, every other nation |
| Cavalry | part | French chasseur à cheval. Remaining: heavy cavalry, lancers, irregular horse, every other nation |
| Artillery | none | |
| Naval and transport | none | |
| Defensive units | none | |
| National, regional, elite variants | part | 3 of the 28 distinctive units in `design/global-conquest/units.json` |

## D. Commanders and characters

| Item | State | Delivered / remaining |
| --- | --- | --- |
| Illustration system (one original, data crops) | done | |
| Napoleon | part | Half-length bust and avatar. Remaining: profile, battlefield avatar, story and reward variants |
| Other commanders | none | 40 named in the slice records alone |
| Princess and special characters | none | Roster not yet defined |

## E. Effects

| Item | State | Delivered / remaining |
| --- | --- | --- |
| Effect recipe system | done | Burst, sparks, smoke, debris layers |
| Hit | done | `effects.hit.spark` |
| Muzzle flash and powder smoke | part | Drawn into infantry attack frames; no standalone asset |
| Cannon fire, explosion, standing smoke | none | |
| Movement and selection feedback | none | |
| Skill and status, capture, victory, defeat | none | |
| UI transitions | part | Screen fade and dialog rise in the viewer |

## F. Buildings

| Item | State | Delivered / remaining |
| --- | --- | --- |
| Plan-driven building system | done | 11 primitives, intact and damaged from one plan |
| City, capital, port (western Europe, level 1) | done | |
| Farm, factory, stables, barracks, fort, bridge | none | |
| Levels 2 and 3 | none | |
| Regional families | none | Nine named in the slice records |
| Ownership and selection treatment | none | Proposed in `design/ART-DECISIONS.md`; needs attachment points |

## G. Global Conquest content design

| Item | State | Delivered / remaining |
| --- | --- | --- |
| Starting dates | part | Five proposed with reasoning; awaiting approval |
| Roster, 1805-09 | part | 64 entities, 34 playable; awaiting approval |
| Nation records, 1805-09 | part | 9 of 34 playable |
| Unit definitions | part | 9 shared families, 28 distinctive units for the slice |
| Events | part | 6 for 1805-09 |
| Starting forces as counts and positions | none | In words only |
| Territory records | none | |
| Rosters and records for the other four dates | none | |
| Gameplay vocabulary | blocked | None supplied; provisional stand-in in use |

## Production

| Item | State |
| --- | --- |
| Authoring kit, build, review tools | done |
| Tests for authoring code and design records | done (60 checks) |
| Second, materially different batch for acceptance | none |
