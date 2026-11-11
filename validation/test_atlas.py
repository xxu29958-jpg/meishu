"""Checks for painted regional maps: projection, fields, recipe names, seamless windows, delivered chunks.

Run with the rest: python -m unittest discover -s validation -v
"""
import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'authoring'))

import build as builder  # noqa: E402
from shared.kit import field, geo, maplayout  # noqa: E402
from shared.kit.palette import Palette  # noqa: E402
from shared.painters import atlas  # noqa: E402
from validate import validate  # noqa: E402

AUTHORING = ROOT / 'authoring/atlas-europe-01'
BATCH = ROOT / 'submissions/atlas-europe-01'
REGION = json.loads((ROOT / 'design/maps/europe.json').read_text(encoding='utf-8'))
RECIPE = json.loads((AUTHORING / 'europe.json').read_text(encoding='utf-8'))


class Projection(unittest.TestCase):
    projection = geo.projection_from(REGION['projection'])

    def test_centre_maps_to_the_origin_and_points_come_back(self):
        x, y = self.projection.forward(20.0, 50.0)
        self.assertAlmostEqual(float(x), 0.0, places=6)
        self.assertAlmostEqual(float(y), 0.0, places=6)
        lon = np.array([-22.0, -9.1, 2.35, 31.2, 49.9, 25.8])
        lat = np.array([64.1, 38.7, 48.86, 30.0, 40.4, 71.2])
        back_lon, back_lat = self.projection.inverse(*self.projection.forward(lon, lat))
        np.testing.assert_allclose(back_lon, lon, atol=1e-9)
        np.testing.assert_allclose(back_lat, lat, atol=1e-9)

    def test_equal_ground_gets_equal_map_area(self):
        def map_area(lon, lat, size=0.5):
            corners = [(lon, lat), (lon + size, lat), (lon + size, lat + size), (lon, lat + size)]
            x, y = self.projection.forward(*zip(*corners))
            return 0.5 * abs(sum(x[i] * y[(i + 1) % 4] - x[(i + 1) % 4] * y[i] for i in range(4)))

        def ground_area(lat, size=0.5):
            radius = REGION['projection']['sphere_radius_km']
            return radius ** 2 * math.radians(size) * (math.sin(math.radians(lat + size)) - math.sin(math.radians(lat)))

        ratios = [map_area(lon, lat) / ground_area(lat) for lon, lat in ((-9, 38), (2, 48), (37, 55), (31, 30), (25, 70), (49, 40))]
        self.assertLess(max(ratios) - min(ratios), 0.002)

    def test_record_check_points_match_the_projection(self):
        frame = geo.frame_for(REGION, 0)
        for point in REGION['check_points']:
            px, py = frame.to_pixels(point['lon'], point['lat'])
            self.assertAlmostEqual(float(px), point['level0_pixel'][0], delta=0.01, msg=point['name'])
            self.assertAlmostEqual(float(py), point['level0_pixel'][1], delta=0.01, msg=point['name'])

    def test_level_size_must_agree_with_the_window(self):
        broken = json.loads(json.dumps(REGION))
        broken['levels'][0]['size'] = [3000, 2560]
        with self.assertRaisesRegex(ValueError, 'does not match the window'):
            geo.frame_for(broken, 0)
        with self.assertRaisesRegex(KeyError, 'no level 7'):
            geo.frame_for(REGION, 7)


class Fields(unittest.TestCase):
    def test_distance_matches_brute_force(self):
        seeds = np.random.default_rng(3).random((70, 90)) > 0.99
        rows, columns = np.nonzero(seeds)
        gy, gx = np.mgrid[0:70, 0:90]
        brute = np.sqrt(((gy[..., None] - rows) ** 2 + (gx[..., None] - columns) ** 2).min(axis=2))
        np.testing.assert_allclose(field.distance(seeds, 40), np.minimum(brute, 40), atol=1e-3)

    def test_noise_depends_on_position_not_on_the_window(self):
        x, y = np.meshgrid(np.linspace(-40, 55, 120, dtype=np.float32), np.linspace(10, 90, 100, dtype=np.float32))
        whole = field.fbm(x, y, 7, 4)
        np.testing.assert_array_equal(field.fbm(x[30:60, 50:90], y[30:60, 50:90], 7, 4), whole[30:60, 50:90])
        self.assertLess(abs(float(whole.mean())), 0.05)
        self.assertGreater(float(whole.std()), 0.1)

    def test_chaikin_keeps_ends_of_open_lines(self):
        line = np.array([[0.0, 0.0], [4.0, 0.0], [4.0, 4.0]])
        smooth = geo.chaikin(line, 2, closed=False)
        np.testing.assert_array_equal(smooth[0], line[0])
        np.testing.assert_array_equal(smooth[-1], line[-1])
        self.assertGreater(len(smooth), len(line))


class Recipe(unittest.TestCase):
    def test_committed_recipe_names_only_geography_that_exists(self):
        atlas.check_recipe(RECIPE)

    def test_a_misspelt_range_is_named(self):
        broken = json.loads(json.dumps(RECIPE))
        broken['relief']['ranges'][0]['region'] = 'ALPES'
        with self.assertRaisesRegex(atlas.RecipeError, "range outline 'ALPES'"):
            atlas.check_recipe(broken)

    def test_an_unknown_ground_is_named(self):
        broken = json.loads(json.dumps(RECIPE))
        broken['cover']['samples'].append([10, 50, 'jungle'])
        with self.assertRaisesRegex(atlas.RecipeError, "unknown ground 'jungle'"):
            atlas.check_recipe(broken)

    def test_palette_inherits_and_overrides(self):
        palette = Palette.load(AUTHORING / 'palette.json')
        base = Palette.load(ROOT / 'authoring/campaign-atlas-01/palette.json')
        self.assertEqual(palette('ink'), base('ink'))
        self.assertTrue(palette.has('map_sea') and not base.has('map_sea'))

    def test_parts_belong_to_their_batch_entry_only(self):
        entries = [{'id': 'maps.region.x.z0.r0c0'}, {'id': 'maps.region.x.z0.r0c1'}, {'id': 'maps.region.x.z01.r0c0'}, {'id': 'maps.terrain.plain'}]
        self.assertEqual(len(builder.entry_ids({'id': 'maps.region.x.z0', 'parts': True}, entries)), 2)
        self.assertEqual(len(builder.entry_ids({'id': 'maps.terrain.plain'}, entries)), 1)


class SeamlessWindows(unittest.TestCase):
    """The same ground must paint the same whichever window it falls in."""

    def test_overlapping_windows_agree(self):
        palette = Palette.load(AUTHORING / 'palette.json')
        frame = geo.frame_for(REGION, 0)
        px, py = frame.to_pixels(9.0, 44.6)                      # Ligurian coast: sea lining, relief, woods, a river
        area = frame.window(int(px) - 110, int(py) - 80, 220, 160)
        margin = math.ceil(atlas.near_reach(RECIPE) / frame.units_per_pixel) + 10
        survey = atlas.Survey(area, RECIPE, palette, margin)
        first = atlas.paint_window(area.window(0, 0, 150, 120), RECIPE, palette, survey, margin)
        second = atlas.paint_window(area.window(60, 30, 160, 130), RECIPE, palette, survey, margin)
        difference = np.abs(first[30:120, 60:150] - second[0:90, 0:90])
        self.assertLess(float(difference.mean()), 0.01)          # colour levels out of 255
        self.assertLess(float(difference.max()), 2.0)


class DeliveredMap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((BATCH / 'manifest.json').read_text(encoding='utf-8'))
        cls.level = REGION['levels'][0]
        cls.chunks = {}
        for row in range(cls.level['rows']):
            for column in range(cls.level['columns']):
                identifier = cls.level['id_pattern'].format(row=row, column=column)
                asset = next(item for item in cls.manifest['assets'] if item['id'] == identifier)
                cls.chunks[(row, column)] = np.asarray(Image.open(BATCH / asset['file']).convert('RGBA'))

    def test_batch_validates_and_holds_exactly_the_chunks_the_record_names(self):
        self.assertEqual(validate(BATCH / 'manifest.json')['asset_count'], self.level['rows'] * self.level['columns'])
        self.assertEqual(len(self.manifest['assets']), len(self.chunks))
        for asset in self.manifest['assets']:
            self.assertEqual(asset['frame_size'], [self.level['chunk'] + 2 * self.level['skirt']] * 2)
            self.assertEqual(asset['anchor'], [0.5, 0.5])

    def test_chunks_are_opaque(self):
        for position, pixels in self.chunks.items():
            self.assertEqual(int(pixels[..., 3].min()), 255, f'chunk {position} has transparent pixels')

    def test_skirts_repeat_the_neighbouring_chunk_exactly(self):
        size, skirt = self.level['chunk'], self.level['skirt']
        for (row, column), pixels in self.chunks.items():
            right, below = self.chunks.get((row, column + 1)), self.chunks.get((row + 1, column))
            if right is not None:
                np.testing.assert_array_equal(pixels[:, size:], right[:, :2 * skirt], f'{row},{column} against its right neighbour')
            if below is not None:
                np.testing.assert_array_equal(pixels[size:, :], below[:2 * skirt, :], f'{row},{column} against the chunk below')

    def test_known_places_fall_on_land_and_known_waters_on_sea(self):
        size, skirt = self.level['chunk'], self.level['skirt']
        for point in REGION['check_points']:
            px, py = point['level0_pixel']
            row, column = int(py // size), int(px // size)
            x, y = int(px - column * size) + skirt, int(py - row * size) + skirt
            patch = self.chunks[(row, column)][y - 2:y + 3, x - 2:x + 3, :3].astype(float).mean(axis=(0, 1))
            blueness = patch[2] - patch[0]
            if point['is'] == 'sea':
                self.assertGreater(blueness, 20, f'{point["name"]} should be water, got {patch.round()}')
            else:
                self.assertLess(blueness, 12, f'{point["name"]} should be land, got {patch.round()}')

    def test_preview_scene_places_every_chunk_on_its_centre(self):
        scene = maplayout.scene_from_region(REGION, 0)
        self.assertEqual(scene, json.loads((BATCH / 'preview.json').read_text(encoding='utf-8')))
        self.assertEqual(scene['items'][7]['asset'], 'maps.region.europe.z0.r1c1')
        self.assertEqual(scene['items'][7]['position'], [768.0, 768.0])


if __name__ == '__main__':
    unittest.main()
