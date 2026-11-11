# Interface system

Design canvas **1280×720** landscape, safe inset **48**, minimum touch target **48**. Screens are composed from the batch's `ui.*` assets by a flow file; text comes from display data; nothing is baked into images.

View it: `python tools/preview.py`, then `/previews/screens.html`.

## Files

| File | Holds |
| --- | --- |
| `flows/<name>.json` | Page compositions: nodes with design coordinates, which asset skins them, bindings, actions |
| `data/<name>.json` | Representative display data, including deliberately awkward strings |
| `previews/screens.js` | The viewer. Holds interaction state only: screen, selection, pressed, dialog, scroll, clock |
| `previews/screens.css` | Type styles and the rules below |

## Components (delivered in `campaign-atlas-01`)

| Asset | Frame | Stretch L,T,R,B | Use |
| --- | --- | --- | --- |
| `ui.panel.command` | 480×280 | 30,30,30,30 | Parchment sheet in an iron-bound frame: panels and dialogs |
| `ui.button.primary` | 240×72 | 30,24,30,28 | Oxblood: the one action a screen is for |
| `ui.button.secondary` | 240×72 | 30,24,30,28 | Gunmetal: back, cancel, lesser choices |
| `ui.tab.folio` | 168×56 | 18,20,18,6 | Folio tabs above a panel |
| `ui.list.row` | 440×72 | 14,12,14,12 | List rows; the selected row is the red one |
| `ui.chip.resource` | 168×44 | 42,14,18,14 | Resource readout with an icon well |
| `ui.rule.section` | 320×20 | 40,0,40,0 | Section divider |
| `ui.icon.gold`, `.men`, `.guns` | 48×48 | none | Resource icons |
| `ui.backdrop.desk` | 1600×720 | none | Screen backdrop, wide enough for 20:9 |

Every control carries `normal`, `pressed`, `selected`, `disabled`. Static pieces (rule, backdrop) map all four clips to one frame.

## State design

- **Normal.** Full colour, lit bevel.
- **Pressed.** Sinks 2 px, darkens, loses the highlight, gains an inner shadow.
- **Selected.** Gilt inner rule and corner plates; buttons, chips and icons add a warm glow. Rows turn oxblood with a gilt marker.
- **Disabled.** Colour and contrast drained; label in grey without its shadow. Still legible.
- **Focus** (keyboard, controller): a gold outer glow, drawn by the layout, not a fifth frame.

## Type

Serif, set by the layout. Preview stack: Noto Serif CJK SC, Noto Serif, Georgia. Sizes are logical pixels on the 720-high canvas.

| Style | Size / weight | Use |
| --- | --- | --- |
| title | 44 / 900, tracked | Screen title on the backdrop |
| kicker | 18 / 700, wide tracking, gilt | Over-title, section name |
| heading | 26 / 900 | Panel heading; up to 2 lines |
| row | 20 / 700 | Row and name text; one line, ellipsis |
| body | 18 / 400 | Running text; clamp at the node's line count |
| meta, note | 15 | Secondary line |
| button | 22 / 700, tracked, cream with shadow | Button labels; one line |
| price, chip, stat | 17-20 / 700, tabular figures | Numbers |

Rules:

- Numbers use tabular lining figures and are right-aligned in lists so digits stack.
- A price field holds eight digits with separators (`12,345,678`) at 116 px. Names give way first: they ellipsise, numbers never do.
- Names and headings wrap to the stated line count and then ellipsise. Body text clamps.
- Chinese titles to 24 characters fit the heading width at 26 px on two lines.
- Padding inside a panel: 28 from the frame to content. Between rows: 6. Between stacked buttons: 12.

## Adapting to the screen

Each node names the edge it keeps: `ax` left, center, right or stretch; `ay` top, center, bottom or stretch. On 20:9 the left column stays left, the right panel stays right, and lists stretch. On a 4:3 tablet panels grow downward and footers stay at the bottom. Controls never shrink below their design size; lists scroll.

## Screens

| Screen | Status |
| --- | --- |
| Main menu | Composed: title, four actions (one disabled), scenario card with flag, portrait and summary |
| Recruitment | Composed: resource chips, tabs with one unavailable, scrolling selectable list, empty state, animated unit detail, unaffordable state |
| Confirm recruitment | Composed: modal over a dimmed screen |
| Everything else in ART-BRIEF | Not started: mode, year, nation and scenario selection; headquarters and commander detail; shop, trade, tavern; equipment, inventory, technology, academy, promotions; collection; achievements and rewards; battle HUD and unit inspection; dialogue, events, turn notices; victory and defeat; tutorial; settings and pause; save and load; loading and error |

## Not done

Checkbox, slider, tooltip, scrollbar art, progress bar; a full icon set; number entry; transitions beyond screen fade and dialog rise; Chinese-language display data for a wrapping check.
