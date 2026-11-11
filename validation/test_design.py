"""The content-design checker must catch broken links between records, and name the record."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from validate_design import DESIGN, DesignError, validate_design  # noqa: E402


class DesignRecords(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='meishu-design-')
        self.directory = Path(self.temp.name) / 'global-conquest'
        shutil.copytree(DESIGN, self.directory)

    def tearDown(self):
        self.temp.cleanup()

    def edit(self, name, change):
        path = self.directory / name
        data = json.loads(path.read_text(encoding='utf-8'))
        change(data)
        path.write_text(json.dumps(data), encoding='utf-8')

    def rejected(self, message):
        with self.assertRaisesRegex(DesignError, message):
            validate_design(self.directory)

    def test_committed_records_are_consistent(self):
        report = validate_design()
        self.assertGreaterEqual(report['playable'], 30)
        self.assertGreaterEqual(report['detailed_nations'], 8)

    def test_unknown_overlord(self):
        self.edit('roster-1805-09.json', lambda data: data['entities'][1].update(overlord='entity.atlantis'))
        self.rejected('entity.italy: overlord entity.atlantis is not in the roster')

    def test_playable_without_tier(self):
        self.edit('roster-1805-09.json', lambda data: data['entities'][0].pop('tier'))
        self.rejected('entity.france: a playable entity needs a tier')

    def test_relationship_with_unknown_entity(self):
        self.edit('nations-1805-09.json', lambda data: data['nations'][0]['relationships'].append({'with': 'entity.nowhere', 'relation': 'war'}))
        self.rejected('entity.france: relationship with unknown entity')

    def test_distinctive_unit_without_definition(self):
        self.edit('nations-1805-09.json', lambda data: data['nations'][0]['military']['distinctive_units'].append('unit.france.balloon-corps'))
        self.rejected('entity.france: distinctive unit unit.france.balloon-corps has no definition')

    def test_art_claimed_but_not_delivered(self):
        self.edit('nations-1805-09.json', lambda data: data['nations'][1]['visual'].update(art_status='delivered'))
        self.rejected('entity.britain: art is marked delivered but these assets are in no batch')

    def test_rating_outside_scale(self):
        self.edit('units.json', lambda data: data['units'][0]['ratings'].update(fire=9))
        self.rejected('unit.shared.line-infantry: ratings are integers 1..5')

    def test_event_on_unknown_entity(self):
        self.edit('events-1805-09.json', lambda data: data['events'][0]['affected'].append('entity.nowhere'))
        self.rejected('event.confederation-of-the-rhine: affects unknown entity')

    def test_scenario_outside_window(self):
        self.edit('scenarios.json', lambda data: data['scenarios'][0].update(date='1821-05-05'))
        self.rejected('outside the historical window')


if __name__ == '__main__':
    unittest.main()
