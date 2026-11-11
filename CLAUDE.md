# 任务入口 · Task entry

This repository is the art-production workspace for the Napoleonic strategy game. Claude owns the complete visual system and the Global Conquest content design; Codex owns game implementation, bindings, Android and merging; the Owner approves direction, scope and results. (Handoff v0.7, 2026-11-11, supersedes the earlier art-only brief: content design is now in scope as design proposals, kept apart from the runtime image manifest.)

## Start here

1. `design/COVERAGE.md` — what is delivered and what is left. Update it with every batch.
2. `design/ART-DECISIONS.md` — the art direction and every decision taken, including the Owner's standing directions: **maps are continuous and hexes never show; the tone is iron and blood.**
3. `authoring/README.md` — how to build, review and change the art.
4. `design/global-conquest/README.md` — scenarios, roster, nation records, open decisions.

Contracts, unchanged: `ASSET-SPEC.md`, `DELIVERY-CONTRACT.md`, `schemas/`. Samples are technical fixtures, not a style.

## Working rules

- Art is drawn by code under `authoring/` and built into `submissions/<batch>/`. Shared code never names an asset, nation or person; variation is data.
- Every batch: build, seal, validate, run the tests, look at the result at display size and close up, then open a PR from `art/<batch>` with ids, method, checks, screenshots and what remains.
- Every PNG in the tree must be declared in a manifest. Review images go on the PR, not in the repository.
- Downloads need the Owner's yes. Raw downloads stay out of the tree; derived layers go under `authoring/geodata/` with the source pinned by commit and hash.
- Regional maps are painted for a record in `design/maps/`; the hex grid, frontiers, towns and names are never painted in.
- Record what is documented and what is interpreted for anything historical. Do not present recalled facts as checked ones.
- Content design uses stable ids and keeps history, proposal and art status apart. `python tools/validate_design.py` must pass.
- Bring the Owner decisions with alternatives and a recommendation; make routine ones yourself and write them down.

## Checks

```sh
python tools/validate.py submissions/<batch>/manifest.json
python tools/validate_design.py
python -m unittest discover -s validation
python tools/check_isolation.py
```
