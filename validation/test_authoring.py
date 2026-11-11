"""Checks for the authoring kit: the parts where a silent mistake would ship wrong art.

Run with the rest: python -m unittest discover -s validation -v
Needs numpy and pycairo in addition to requirements.txt (see authoring/README.md).
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'authoring'))

import build as builder  # noqa: E402


def mean_difference(first, second):
    """Average per-channel difference of two equally sized RGB images, 0..255."""
    return sum(ImageStat.Stat(ImageChops.difference(first, second)).mean) / 3

from shared.kit import anim, compose, hexgrid, maplayout, rig, sheet  # noqa: E402
from shared.kit.palette import Palette  # noqa: E402
from shared.painters import find_painter, illustration  # noqa: E402
from validate import validate  # noqa: E402

BATCH = ROOT / 'submissions/campaign-atlas-01/manifest.json'
AUTHORING = ROOT / 'authoring/campaign-atlas-01'


class FrameIndexing(unittest.TestCase):
    clip = {'frames': [4, 5, 6], 'fps': 10, 'loop': True}

    def test_looping_clip_wraps(self):
        self.assertEqual([compose.frame_at(self.clip, ms) for ms in (0, 99, 100, 250, 300, 1000)], [4, 4, 5, 6, 4, 5])

    def test_one_shot_holds_last_frame(self):
        clip = dict(self.clip, loop=False)
        self.assertEqual([compose.frame_at(clip, ms) for ms in (0, 250, 300, 9000)], [4, 6, 6, 6])

    def test_frame_box_is_row_major_and_names_the_asset_when_out_of_range(self):
        asset = {'id': 'units.test.case', 'frame_size': [128, 128], 'size': [1024, 640]}
        self.assertEqual(compose.frame_box(asset, 9), (128, 128, 256, 256))
        with self.assertRaisesRegex(IndexError, 'units.test.case: frame 40'):
            compose.frame_box(asset, 40)

    def test_clip_table_packs_clips_in_order(self):
        table, total = anim.clip_table({'idle': {'frames': 3, 'fps': 8, 'loop': True}, 'attack': {'frames': 2, 'fps': 12, 'loop': False}})
        self.assertEqual((table['idle']['frames'], table['attack']['frames'], total), ([0, 1, 2], [3, 4], 5))


class AnchorsAndMirroring(unittest.TestCase):
    asset = {'display_size': [64, 64], 'anchor': [0.25, 0.875], 'directions': 'mirror-x'}

    def test_rect_puts_the_anchor_on_the_world_point(self):
        left, top, width, height = compose.screen_rect(self.asset, (100, 200), scale=2.0)
        self.assertEqual((left + 0.25 * width, top + 0.875 * height), (100, 200))

    def test_mirroring_keeps_the_ground_point(self):
        left, top, width, height = compose.screen_rect(self.asset, (100, 200), mirror=True)
        self.assertEqual((left + (1 - 0.25) * width, top + 0.875 * height), (100, 200))

    def test_fixed_assets_ignore_mirror(self):
        fixed = dict(self.asset, directions='fixed')
        self.assertEqual(compose.screen_rect(fixed, (10, 10), mirror=True), compose.screen_rect(fixed, (10, 10)))


class AnimationSampling(unittest.TestCase):
    poses = {'a': {'x': 0.0, 'hand': [0.0, 0.0]}, 'b': {'x': 10.0, 'hand': [4.0, 8.0]}}

    def test_one_shot_lands_on_its_last_key(self):
        clip = {'frames': 3, 'loop': False, 'keys': [{'t': 0, 'pose': 'a'}, {'t': 1, 'pose': 'b', 'ease': 'linear'}]}
        self.assertEqual([frame['x'] for frame in anim.sample_keys(clip, self.poses)], [0.0, 5.0, 10.0])

    def test_loop_stops_short_of_repeating_frame_zero(self):
        clip = {'frames': 4, 'loop': True, 'keys': [{'t': 0, 'pose': 'a'}, {'t': 0.5, 'pose': 'b', 'ease': 'linear'},
                                                    {'t': 1, 'pose': 'a', 'ease': 'linear'}]}
        self.assertEqual([frame['x'] for frame in anim.sample_keys(clip, self.poses)], [0.0, 5.0, 10.0, 5.0])

    def test_pose_overrides_merge_and_unknown_poses_are_named(self):
        merged = anim.resolve({'pose': 'b', 'x': 3.0}, self.poses)
        self.assertEqual((merged['x'], merged['hand']), (3.0, [4.0, 8.0]))
        with self.assertRaisesRegex(KeyError, "Unknown pose 'missing'"):
            anim.resolve('missing', self.poses)


class Skeleton(unittest.TestCase):
    def test_limb_reaches_a_reachable_target(self):
        joint, end = rig.two_bone((0, 0), (6, 8), 6, 6, rig.ARM_BEND)
        self.assertAlmostEqual(end[0], 6, places=5)
        self.assertAlmostEqual(end[1], 8, places=5)
        for a, b in (((0, 0), joint), (joint, end)):
            self.assertAlmostEqual(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5, 6, places=5)

    def test_limb_never_stretches(self):
        _, end = rig.two_bone((0, 0), (100, 0), 6, 6, rig.ARM_BEND)
        self.assertLess(end[0], 12.0)

    def test_walk_plants_the_foot_through_stance(self):
        for phase in (0.0, 0.2, 0.45):
            (_, height), _ = rig.walk_feet(phase, 19, 6)
            self.assertEqual(height, 0.0)
        (_, height), _ = rig.walk_feet(0.75, 19, 6)
        self.assertLess(height, -4.0)


class CropConsistency(unittest.TestCase):
    def test_crop_maps_box_onto_frame(self):
        scale, offset = illustration.crop_transform([66, 40, 380, 380], (192, 192))
        self.assertAlmostEqual(scale, 192 / 380)
        self.assertEqual(offset, (-66, -40))

    def test_bad_boxes_are_refused(self):
        with self.assertRaisesRegex(ValueError, 'aspect'):
            illustration.crop_transform([0, 0, 200, 100], (192, 192))
        with self.assertRaisesRegex(ValueError, 'inside'):
            illustration.crop_transform([400, 0, 200, 200], (192, 192))

    def test_avatar_is_the_same_drawing_as_the_bust(self):
        batch = compose.Batch(BATCH)
        box = json.loads((AUTHORING / 'portraits/napoleon/character.json').read_text(encoding='utf-8'))['crops']['avatar']
        bust = batch.frame('portraits.napoleon.bust', 0).crop((box[0], box[1], box[0] + box[2], box[1] + box[3]))
        expected = compose.resize_rgba(bust, (192, 192)).convert('RGB')
        actual = batch.frame('portraits.napoleon.avatar', 0).convert('RGB')
        self.assertLess(mean_difference(expected, actual), 9.0, 'avatar no longer matches its crop of the bust')


class MissingReferences(unittest.TestCase):
    def test_unknown_painter_lists_the_known_ones(self):
        with self.assertRaisesRegex(KeyError, "Unknown painter 'watercolour'.*terrain"):
            find_painter('watercolour')

    def test_unknown_colour_names_the_palette_file(self):
        palette = Palette({'ink': '#000000', 'paper': '#ffffff'}, 'demo/palette.json')
        with self.assertRaisesRegex(KeyError, "demo/palette.json: palette has no colour 'mauve'"):
            palette('mauve')

    def test_unknown_format_names_the_asset(self):
        with self.assertRaisesRegex(builder.BuildError, 'ui.demo: unknown format'):
            builder.resolve_format({'id': 'ui.demo', 'format': 'poster'}, {})

    def test_layout_reports_the_cell_with_an_unknown_code(self):
        layout = {'rows': ['g?'], 'legend': {'g': 'maps.terrain.plain'}}
        with self.assertRaisesRegex(KeyError, 'row 0 column 1'):
            list(maplayout.cells(layout))


class BuiltBatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.batch = compose.Batch(BATCH)

    def test_committed_batch_validates(self):
        self.assertEqual(validate(BATCH)['asset_count'], len(self.batch.assets))

    def test_every_sheet_frame_is_reachable_from_a_clip(self):
        for identifier, asset in self.batch.assets.items():
            count = (asset['size'][0] // asset['frame_size'][0]) * (asset['size'][1] // asset['frame_size'][1])
            used = {index for clip in asset['clips'].values() for index in clip['frames']}
            columns = asset['size'][0] // asset['frame_size'][0]
            self.assertLessEqual(count - len(used), columns - 1, f'{identifier}: more than a row of unused frames')

    def test_units_keep_the_safe_margin_in_every_frame(self):
        for identifier, asset in self.batch.assets.items():
            if asset['category'] != 'units':
                continue
            width, height = asset['frame_size']
            for name, clip in asset['clips'].items():
                for index in clip['frames']:
                    solid = self.batch.frame(identifier, index).getchannel('A').point(lambda value: 255 if value > 60 else 0)
                    left, top, right, bottom = solid.getbbox()
                    self.assertTrue(left >= 8 and top >= 8 and right <= width - 8 and bottom <= height - 8,
                                    f'{identifier}/{name} frame {index} leaves the 8 px safe margin: {(left, top, right, bottom)}')

    def test_unit_clips_end_where_idle_begins(self):
        for identifier, asset in self.batch.assets.items():
            if asset['category'] != 'units':
                continue
            first = self.batch.frame(identifier, asset['clips']['idle']['frames'][0]).convert('RGB')
            last = self.batch.frame(identifier, asset['clips']['finish']['frames'][-1]).convert('RGB')
            self.assertLess(mean_difference(first, last), 4.0, f'{identifier}: finish does not settle into idle')

    def test_sea_repeats_across_the_hex_lattice(self):
        tile = self.batch.frame('maps.terrain.water', 0).convert('RGB')
        seam = [sum(abs(a - b) for a, b in zip(tile.getpixel((0, y)), tile.getpixel((127, y)))) / 3 for y in range(40, 104)]
        inner = [sum(abs(a - b) for a, b in zip(tile.getpixel((60, y)), tile.getpixel((61, y)))) / 3 for y in range(40, 104)]
        self.assertLess(sum(seam) / len(seam), sum(inner) / len(inner) + 6.0, 'left and right edges of the sea tile do not meet')

    def test_land_pieces_feather_out_before_the_frame_edge(self):
        for identifier in ('maps.terrain.plain', 'maps.terrain.forest', 'maps.coast.sand', 'maps.coast.shallows'):
            alpha = self.batch.frame(identifier, 0).getchannel('A')
            width, height = alpha.size
            border = [alpha.getpixel((x, y)) for x in range(width) for y in (0, height - 1)] + \
                     [alpha.getpixel((x, y)) for y in range(height) for x in (0, width - 1)]
            self.assertLess(max(border), 24, f'{identifier}: artwork is cut by the frame edge')


class BatchSwitching(unittest.TestCase):
    def test_two_unrelated_batches_render_through_the_same_code(self):
        for manifest in (ROOT / 'samples/manifest.json', BATCH):
            batch = compose.Batch(manifest)
            scene = json.loads((manifest.parent / batch.manifest['preview']).read_text(encoding='utf-8'))
            image = compose.render_scene(batch, scene, pixels_per_unit=1.0)
            self.assertEqual(image.size, tuple(scene['canvas_size']))
            self.assertGreater(len(image.convert('RGB').getcolors(maxcolors=1 << 24)), 50)

    def test_scene_draws_coast_layers_before_any_land(self):
        layout = json.loads((AUTHORING / 'scenes/channel-coast.json').read_text(encoding='utf-8'))
        order = [item['asset'] for item in maplayout.scene_from_layout(layout)['items']]
        last_coast = max(index for index, asset in enumerate(order) if asset.startswith('maps.coast.'))
        first_land = min(index for index, asset in enumerate(order) if asset.startswith('maps.terrain.'))
        self.assertLess(last_coast, first_land)


class ExportMetadata(unittest.TestCase):
    def test_rebuilding_one_asset_keeps_the_rest_and_records_true_facts(self):
        with tempfile.TemporaryDirectory(prefix='meishu-build-') as temp:
            work = Path(temp) / 'batch'
            shutil.copytree(AUTHORING, work)
            config = json.loads((work / 'batch.json').read_text(encoding='utf-8'))
            output = ROOT / 'submissions' / '_test-build'
            config['output'] = 'submissions/_test-build'
            config['assets'] = [asset for asset in config['assets'] if asset['id'] in ('identity.france.flag', 'maps.grid.hex')]
            config.pop('preview', None)
            (work / 'batch.json').write_text(json.dumps(config), encoding='utf-8')
            try:
                builder.build(work)
                manifest = builder.build(work, only=('identity.',))
                self.assertEqual([entry['id'] for entry in manifest['assets']], ['maps.grid.hex', 'identity.france.flag'])
                for entry in manifest['assets']:
                    with Image.open(output / entry['file']) as image:
                        self.assertEqual(list(image.size), entry['size'])
                        self.assertEqual(image.mode, 'RGBA')
            finally:
                shutil.rmtree(output, ignore_errors=True)

    def test_sheet_packing_rejects_mixed_frames(self):
        frames = [Image.new('RGBA', (8, 8)), Image.new('RGBA', (8, 9))]
        with self.assertRaisesRegex(ValueError, 'Frame 1'):
            sheet.pack(frames)

    def test_hex_geometry_matches_the_contract(self):
        self.assertEqual(hexgrid.corners()[0], (64.0, 0.0))
        self.assertEqual(hexgrid.NEIGHBOURS['se'], (64, 108))
        self.assertTrue(hexgrid.inside((64, 72)) and not hexgrid.inside((2, 2)))


if __name__ == '__main__':
    unittest.main()
