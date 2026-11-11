# Units

How units are built, what the delivered ones are based on, and where legibility overrode the drill book.

## Build

A unit is a **drill** performed by a **look**.

- Drill: `authoring/<batch>/units/*-drill.json` and `sabre-charge.json`. Named poses, clips, frames and fps. Clip timing in the manifest is derived from this file.
- Look: `authoring/<batch>/units/<nation>-<year>.json`. Colours as palette roles, headgear type, chest style, shoulder ornament, belts, pack, weapon, horse and saddlery.
- Formation: in `batch.json`. Which members stand where, how far each rank lags (the rippling volley), how far it recedes in value.

Painters: `authoring/shared/painters/figure.py` (the man), `infantry.py` (foot drill), `cavalry.py` (horse rig and mounted drill). Skeleton maths: `authoring/shared/kit/rig.py`.

Adding a regiment of an existing arm is a look record. Adding headgear or a chest style is one function in `figure.py`. Adding an arm (artillery, a ship) is a new painter.

## Clips

| | idle | move | attack | recover | finish |
| --- | --- | --- | --- | --- | --- |
| Infantry | 8 f, 8 fps, loop: shouldered arms, breathing | 8 f, 12 fps, loop: march in step | 6 f, 12 fps: present, aim, fire, recoil | 10 f, 12 fps: cartridge, prime, ram twice, return | 5 f, 12 fps: settle to shouldered arms |
| Cavalry | 8 f, 8 fps, loop: standing, horse breathing | 8 f, 12 fps, loop: gallop | 7 f, 12 fps: gallop, raise, cut, follow through | 6 f, 12 fps: rein in, sabre to the carry | 5 f, 12 fps: halt and settle |

`finish` ends on `idle` frame 0 (tested). Hooves and feet are solved from ground targets, so a planted foot does not slide. The rear rank acts one frame late.

Every frame keeps head, feet and weapons 8 px inside the frame (tested).

## Delivered looks, September 1805

**Line fusilier** (`units.infantry.line`). Dark blue coat, white lapels piped scarlet, scarlet collar and cuffs, white waistcoat and breeches, black campaign gaiters, white crossbelt, calfskin pack with rolled greatcoat, cocked hat with cockade. Basis: blue coat decreed 1793 with white lapels, turnbacks and waistcoat and red collar and cuffs; white breeches and black gaiters regulation; bicorne until the shako of 1806.

**Grenadier of the Old Guard** (`units.france.grenadier`). As above with scarlet fringed epaulettes, scarlet turnbacks, two crossbelts, short sabre, moustache, bearskin with brass plate, white cords and scarlet plume. Basis: Guard grenadier coat lined scarlet with scarlet turnbacks and scarlet epaulettes on both shoulders.

**Chasseur à cheval** (`units.cavalry.light`). Green braided dolman, scarlet collar and cuffs, green breeches, black boots, shako with pompon and cords, white sheepskin with scarlet wolf-tooth edging, green portmanteau, bay horse. Basis: line chasseurs in green with facings by regiment; shako adopted from 1805; dolman with white braid before the 1806 coat.

## Where the art departs from the record

- **Musket on the visible shoulder** in both facings. Drill carried it on the left. Forced by `mirror-x`.
- **Musket shortened** to about two thirds of true length so that the levelled piece and bayonet stay inside a 128 px frame.
- **Bearskin and plume lowered** for the same reason.
- **Cocked hat worn athwart** with a sky-blue company pompon: the athwart wear is attested; the pompon colour follows the 1811 company scheme and is an assumption for 1805.
- **Cockade** painted blue centre, red, white outer: the order is my recollection of Empire practice and was not confirmed in the pages read.
- **Rolled greatcoat on the pack:** general issue came after 1805.
- **Chasseur facings scarlet** as for the 1st regiment; the dolman is kept although several regiments had moved to the coat.
- **Rider smaller than the foot soldier** (0.85) so horse and man fit one frame.
- **Three men stand for a battalion, two troopers for a squadron.**

Sources read for this batch are listed in `submissions/campaign-atlas-01/sources.json`. Guard foot grenadier bearskin detail and the Guard chasseur colour table could not be retrieved and rest on general knowledge.

## Not done

Artillery, naval and transport units; light infantry, heavy cavalry; every nation other than France; separate left-facing sheets for asymmetric kit; battle-worn variants.
