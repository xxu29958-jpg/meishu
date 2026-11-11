# Global Conquest · content design

Status: **proposal 0.1, awaiting Owner approval.** Nothing here is engine data. These are versioned design inputs for the integration team; the runtime image manifest stays separate (`submissions/<batch>/`).

Check the records with `python tools/validate_design.py`.

## What is in this directory

| File | Holds |
| --- | --- |
| `scenarios.json` | Five proposed starting dates, why each day, what the world looks like on it, build order |
| `roster-1805-09.json` | All 64 entities for 1 September 1805 and how each is represented |
| `nations-1805-09.json` | Full records for nine participants across six regions (the representative slice) |
| `units.json` | 9 shared unit families and 28 distinctive units for the slice |
| `events-1805-09.json` | Six events as state-triggered rules with their historical occasion kept apart |
| `vocabulary.json` | **Provisional** rating and relation terms (see Open decisions) |
| `sources.json` | Works relied on, with an honest note of which were read and which recalled |

Every record keeps three things apart: **history** (what was so on the date, with confidence and sources), **proposal** (balance and mechanics, in relative 1-5 ratings), and **art** (asset ids and whether that art exists yet).

## Starting dates

Recommended: **1805-09-01, 1798-07-01, 1812-06-18, 1810-09-16, 1815-03-20**, built in that order. Each is a day on which the big outcomes are still open and the world outside Europe differs in kind from the other four: a French army in Africa and a living Mysore (1798); every great power free to choose (1805); Spanish America in revolt under a French peace (1810); two invasions in one week (1812); France alone (1815). If scope must shrink, keep the first three. `scenarios.json` gives the reasoning and the dates considered and set aside.

## How entities are represented

One government per record is the wrong model for 1805: much of the world is governed by dependents, companies and nations without a single government. The roster uses five classes.

- **Playable** (34): a campaign of its own, in three tiers. Major (8): France, Britain, Russia, Austria, Prussia, Spain, the Ottoman Empire, the Qing. Medium (14) and minor (12) include Persia, the Marathas, the Sikh Empire, Japan, Việt Nam, Siam, Burma, Egypt, the United States, Haiti, Sokoto, Asante, Ethiopia, Oman, Diriyah and Hawaiʻi.
- **Independent** (4): on the map with its own government, run by the game, not offered as a campaign (Kandy, the Hausa kingdoms, the Papal States, Sardinia).
- **Dependent** (12): bound to an overlord, with a written way out through events (Italy, the Batavian Commonwealth, New Spain, Brazil, the Cape).
- **Associated** (4): fights as an arm of another participant with its own recruitment pool (the East India Company, British North America).
- **Regional system** (10): no single government to conquer. See below.

A smaller power is playable when its position gives decisions, not when it has a name. Haiti, Sokoto and the Marathas are in the slice because their campaigns are unlike a great power's: survive, found a state, hold a confederacy together.

### The regional system

Plains and woodland nations of North America, the Mapuche, the lesser German states, the Malay sultanates, the Central Asian khanates, the West and southern African kingdoms and the peoples of Oceania are not empty land and not conquest targets with capitals. The proposal is one shared mechanic with regional data:

- Each region has a **standing** toward every neighbouring participant (hostile, wary, trading, allied) that changes with what that participant does there.
- A region supplies **defenders** when entered (regional unit looks, the region's terrain advantage) and **raids** or **trade** across its edge according to standing.
- Some regions hold a **rising**: a condition under which they become a playable or game-run participant (Tecumseh's confederacy from 1810-09; the Zulu kingdom late in the window; the Confederation of the Rhine by event).

This needs integration design; it is recorded here as a requirement with examples, not as a finished rule.

## The representative slice

Nine full records: **France, Britain, Russia, the Ottoman Empire, the Qing, the Maratha Confederacy, the United States, Haiti, Sokoto.** Each has identity, geography, relationships, starting forces and commanders, distinctive units, development ratings, one national trait with its cost, difficulty, objectives, three plausible strategies, AI priorities with concrete examples, visual identity, and evidence with stated adjustments.

Asymmetry at a glance (relative 1-5):

| Participant | Treasury | Manpower | Industry | Naval | Technology | Stability | Difficulty | Trait and its cost |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| France | 3 | 5 | 4 | 3 | 4 | 4 | commanding | Corps d'armée: faster concentration, worse supply abroad |
| Britain | 5 | 2 | 5 | 5 | 4 | 4 | balanced | Paymaster: subsidies an ally may pocket |
| Russia | 2 | 5 | 3 | 2 | 3 | 4 | balanced | Depth: invaders starve, so do its own reinforcements |
| Ottoman Empire | 3 | 4 | 2 | 3 | 2 | 2 | hard | The New Order: reform steps that risk revolt |
| Qing | 4 | 5 | 3 | 2 | 2 | 3 | balanced | All under Heaven: income and peace, rebellion when pressed |
| Marathas | 2 | 4 | 2 | 1 | 3 | 1 | desperate | Five houses: separate armies that may defect |
| United States | 3 | 3 | 3 | 2 | 3 | 4 | balanced | Neutral carrier: trade income that builds toward war |
| Haiti | 1 | 3 | 1 | 1 | 3 | 2 | hard | Never again: burn the coast, hold the mountains |
| Sokoto | 1 | 3 | 1 | 1 | 1 | 3 | hard | The flags: risings it starts and does not control |

Representative openings: France must beat Austria before Russia arrives or gamble at sea; Britain cannot win on land and cannot lose at sea, so it buys allies; the Ottomans start at peace and must decide what to reform before Russia is free; Haiti has the best army it will ever have and no money; Sokoto owns one camp.

## Units

`units.json` separates **shared families** (line and light infantry, light and heavy cavalry, foot artillery, ship of the line, frigate, transport, militia) from **distinctive units**. A nation's version of a shared family is a look, not a new unit: French chasseurs à cheval are the light-cavalry family in green and are rated identically on purpose. A distinctive unit earns its record by doing something the family does not: rifles that outrange muskets and load slowly, Cossacks that cost nothing and cannot hold ground, Janissaries whose upkeep cannot be refused, Pindaris that destroy income instead of fighting.

Not every country gets an elite regiment. Sokoto's distinction is how it recruits; the United States' is a frigate and a cap set by Congress.

Three records propose **new mechanics** and say so: the Pindari *raid* (removes income, deals no damage), the rifle's *reduced close fire*, and Haiti's *mountain fort* as a recruitable defensive unit.

## Events and diplomacy

The starting relations are history and live in the nation records. Events are rules: each has start conditions, a **trigger on game state** (never a date alone), affected entities, effects, presentation, interactions and the counterfactual it allows. The six written so far: the Confederation of the Rhine, Prussia's decision, the Spanish crisis (which starts the American independence chains), the court's flight to Brazil, Haiti's division, and the founding of the Sokoto Caliphate.

## Art links

Each nation record lists its flag, map colour, portraits, units, buildings and architectural family by asset id. Only France is delivered (`campaign-atlas-01`); `validate_design.py` fails if a record claims delivered art that no batch contains. Planned ids follow `units.<entity>.<unit>`, `identity.<entity>.flag`, `portraits.<person>.bust`, `buildings.<region>.<kind>.l<level>`.

## Open decisions for the Owner

1. **Dates.** Approve the five, or name the cut. 1810-09 versus 1808-05 is the real choice.
2. **Roster size.** 34 playable is a proposal. The tiers make a cut easy: majors and mediums alone give 22.
3. **Portraits where depiction is sensitive or undocumented.** Usman dan Fodio should not be drawn as a likeness; I recommend an emblematic panel. Several rulers (Osei Bonsu, Karađorđe's contemporaries in Africa and Asia) have no reliable portrait; these need a stated convention.
4. **The Qing 'flag'.** No national flag existed in 1805. Use the dragon standard as an identity mark, or a neutral device?
5. **The Maratha Confederacy as one participant.** Historically five houses. One participant with five armies is the proposal.

## Open questions for integration

1. **Gameplay vocabulary.** The handoff refers to a supplied vocabulary; none is in this repository. `vocabulary.json` is a stand-in with relative ratings. Please supply the real terms and scales and I will map every record.
2. **Regional system and event triggers** need engine support that may not exist. Tell me which conditions are observable and I will rewrite triggers to fit.
3. **Entity ids.** The runtime theme uses `entity.france` in `global_visual.entities`; the sample used `historical.france`. The records here use `entity.*` throughout.

## What is not done

- Rosters and records for the other four scenarios.
- Full records for the 25 playable entities outside the slice.
- Starting forces as counts and positions: the slice gives them in words.
- Territory geometry. Political geography will be dated overlay records over the painted map. Europe now has a hex grid and terrain table to key them to (`design/maps/europe-hexes.json`); the other regions wait on their maps.
- Verification of every 'recalled' source against the text.
