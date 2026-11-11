"""Check the Global Conquest content-design records for shape and cross-references.

    python tools/validate_design.py

These records are design inputs, not runtime data: this checker is separate from
validate.py and never touches the image contract. It reads design/global-conquest
and the delivered manifests, and reports the first problem with the record it is in.
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / 'design' / 'global-conquest'
ID = re.compile(r'^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)+$')
REPRESENTATIONS = {'playable', 'independent', 'dependent', 'associated', 'regional-system'}
TIERS = {'major', 'medium', 'minor'}
NATION_AREAS = ('identity', 'geography', 'relationships', 'military', 'proposal', 'ai', 'visual', 'history')


class DesignError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise DesignError(message)


def load(name, directory=DESIGN):
    path = directory / name
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as error:
        raise DesignError(f'{path}: {error}') from error


def delivered_assets(root=ROOT):
    """Asset ids in every submitted batch (samples are fixtures and do not count as delivered art)."""
    identifiers = set()
    for manifest in sorted((root / 'submissions').glob('*/manifest.json')):
        identifiers.update(asset['id'] for asset in json.loads(manifest.read_text(encoding='utf-8'))['assets'])
    return identifiers


def check_scenarios(scenarios):
    identifiers = set()
    for scenario in scenarios['scenarios']:
        require(ID.match(scenario['id']), f'scenarios: bad id {scenario["id"]!r}')
        require(scenario['id'] not in identifiers, f'scenarios: duplicate {scenario["id"]}')
        identifiers.add(scenario['id'])
        require(re.fullmatch(r'\d{4}-\d{2}-\d{2}', scenario['date']), f'{scenario["id"]}: date must be YYYY-MM-DD')
        require(scenarios['window']['from'] <= scenario['date'] <= scenarios['window']['to'],
                f'{scenario["id"]}: {scenario["date"]} is outside the historical window')
        require(scenario['world_state'] and scenario['why_this_day'], f'{scenario["id"]}: needs why_this_day and world_state')
    require(sum(1 for scenario in scenarios['scenarios'] if scenario.get('first_complete')) == 1,
            'scenarios: exactly one scenario must be marked first_complete')
    return identifiers


def check_roster(roster, scenario_ids):
    require(roster['scenario'] in scenario_ids, f'roster: unknown scenario {roster["scenario"]}')
    entities = {}
    for entity in roster['entities']:
        identifier = entity['id']
        require(ID.match(identifier), f'roster: bad id {identifier!r}')
        require(identifier not in entities, f'roster: duplicate {identifier}')
        entities[identifier] = entity
        require(entity['representation'] in REPRESENTATIONS, f'{identifier}: unknown representation {entity["representation"]!r}')
        if entity['representation'] == 'playable':
            require(entity.get('tier') in TIERS, f'{identifier}: a playable entity needs a tier')
        if entity['representation'] in ('dependent', 'associated'):
            require('overlord' in entity, f'{identifier}: {entity["representation"]} needs an overlord')
        for field in ('name', 'region', 'form', 'capital', 'note'):
            require(entity.get(field), f'{identifier}: missing {field}')
    for identifier, entity in entities.items():
        if 'overlord' in entity:
            require(entity['overlord'] in entities, f'{identifier}: overlord {entity["overlord"]} is not in the roster')
            require(entity['overlord'] != identifier, f'{identifier}: cannot be its own overlord')
    return entities


def check_units(units, entities, sources, vocabulary):
    known = {}
    ratings, tags, families = set(vocabulary['unit_ratings']), set(vocabulary['unit_tags']), set(vocabulary['families'])
    for unit in units['units']:
        identifier = unit['id']
        require(ID.match(identifier) and identifier not in known, f'units: bad or duplicate id {identifier!r}')
        known[identifier] = unit
        require(unit['affiliation'] == 'shared' or unit['affiliation'] in entities, f'{identifier}: unknown affiliation {unit["affiliation"]}')
        require(unit['family'] in families, f'{identifier}: unknown family {unit["family"]}')
        require(set(unit['ratings']) == ratings, f'{identifier}: ratings must be exactly {sorted(ratings)}')
        require(all(isinstance(value, int) and 1 <= value <= 5 for value in unit['ratings'].values()), f'{identifier}: ratings are integers 1..5')
        require(set(unit['tags']) <= tags, f'{identifier}: unknown tags {sorted(set(unit["tags"]) - tags)}')
        for field in ('historical_basis', 'period', 'equipment', 'role', 'recruitment', 'ai_use'):
            require(unit.get(field), f'{identifier}: missing {field}')
        require(ID.match(unit['art']['asset']), f'{identifier}: art.asset is not an asset id')
        for source in unit['sources']:
            require(source in sources, f'{identifier}: unknown source {source}')
    return known


def check_nations(nations, entities, units, sources, vocabulary, assets):
    seen = set()
    for nation in nations['nations']:
        identifier = nation['id']
        require(identifier in entities, f'nations: {identifier} is not in the roster')
        require(entities[identifier].get('detail'), f'{identifier}: roster entry is not marked detail')
        require(identifier not in seen, f'nations: duplicate {identifier}')
        seen.add(identifier)
        missing = [area for area in NATION_AREAS if area not in nation]
        require(not missing, f'{identifier}: missing design areas {missing}')
        for relation in nation['relationships']:
            require(relation['with'] in entities, f'{identifier}: relationship with unknown entity {relation["with"]}')
            require(relation['relation'] in vocabulary['relations'], f'{identifier}: unknown relation {relation["relation"]!r}')
        for unit in nation['military']['distinctive_units']:
            require(unit in units, f'{identifier}: distinctive unit {unit} has no definition')
            require(units[unit]['affiliation'] == identifier, f'{identifier}: {unit} belongs to {units[unit]["affiliation"]}')
        proposal = nation['proposal']
        require(set(proposal['ratings']) == set(vocabulary['nation_ratings']), f'{identifier}: proposal.ratings keys do not match the vocabulary')
        require(proposal['difficulty'] in vocabulary['difficulty'], f'{identifier}: unknown difficulty {proposal["difficulty"]!r}')
        require({'name', 'effect', 'tradeoff'} <= set(proposal['trait']), f'{identifier}: a trait needs name, effect and tradeoff')
        require(nation['ai']['priorities'] and nation['ai']['examples'], f'{identifier}: AI needs priorities and concrete examples')
        for source in nation['history']['sources']:
            require(source in sources, f'{identifier}: unknown source {source}')
        visual = nation['visual']
        require(re.fullmatch(r'#[0-9A-Fa-f]{6}', visual['map_colour']), f'{identifier}: map_colour must be #RRGGBB')
        linked = [visual['flag'], *visual['portraits'], *visual['units'], *visual['buildings']]
        if visual['art_status'].startswith('delivered'):
            absent = [asset for asset in linked if asset not in assets]
            require(not absent, f'{identifier}: art is marked delivered but these assets are in no batch: {absent}')
    marked = {identifier for identifier, entity in entities.items() if entity.get('detail')}
    require(marked == seen, f'nations: roster marks detail for {sorted(marked - seen)} without records')
    colours = {}
    for nation in nations['nations']:
        colour = nation['visual']['map_colour'].lower()
        require(colour not in colours, f'{nation["id"]}: map colour {colour} is already used by {colours.get(colour)}')
        colours[colour] = nation['id']


def check_unit_art(units, assets):
    for identifier, unit in units.items():
        if unit['art']['status'].startswith('delivered'):
            require(unit['art']['asset'] in assets, f'{identifier}: art marked delivered but {unit["art"]["asset"]} is in no batch')


def check_events(events, entities, scenario_ids):
    require(events['scenario'] in scenario_ids, f'events: unknown scenario {events["scenario"]}')
    identifiers = set()
    for event in events['events']:
        identifier = event['id']
        require(ID.match(identifier) and identifier not in identifiers, f'events: bad or duplicate id {identifier!r}')
        identifiers.add(identifier)
        for field in ('title', 'historical', 'start_conditions', 'trigger', 'affected', 'effects', 'presentation', 'interactions'):
            require(event.get(field), f'{identifier}: missing {field}')
        for entity in event['affected']:
            require(entity in entities, f'{identifier}: affects unknown entity {entity}')


def validate_design(directory=DESIGN, root=ROOT):
    vocabulary = load('vocabulary.json', directory)
    sources = {source['id'] for source in load('sources.json', directory)['sources']}
    scenario_ids = check_scenarios(load('scenarios.json', directory))
    entities = check_roster(load('roster-1805-09.json', directory), scenario_ids)
    assets = delivered_assets(root)
    units = check_units(load('units.json', directory), entities, sources, vocabulary)
    check_unit_art(units, assets)
    check_nations(load('nations-1805-09.json', directory), entities, units, sources, vocabulary, assets)
    check_events(load('events-1805-09.json', directory), entities, scenario_ids)
    playable = [entity for entity in entities.values() if entity['representation'] == 'playable']
    return {'scenarios': len(scenario_ids), 'entities': len(entities), 'playable': len(playable),
            'detailed_nations': sum(1 for entity in entities.values() if entity.get('detail')), 'units': len(units)}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.parse_args()
    try:
        report = validate_design()
    except (DesignError, KeyError) as error:
        parser.exit(1, f'FAIL: {error}\n')
    print('PASS: ' + ', '.join(f'{value} {name.replace("_", " ")}' for name, value in report.items()))


if __name__ == '__main__':
    main()
