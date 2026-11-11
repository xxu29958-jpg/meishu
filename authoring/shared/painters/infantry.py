"""Foot soldiers: a drill (poses and clip timing) performed by a look (uniform).

Both are data. The drill file defines named poses, keyed clips and the walk
cycle; the look file defines colours and kit. This module samples the drill
into one pose per frame, solves the skeleton and asks figure.py to draw it.
"""
import math

import cairo

from ..kit import anim, rig, sheet
from ..kit.raster import paper_grain
from . import figure

ANCHOR = (64.0, 112.0)                 # unit format: 128 px frame, anchor (0.5, 0.875)
POSE_DEFAULTS = {'lean': 0.0, 'head': 0.0, 'near_pitch': 0.0, 'far_pitch': 0.0, 'flash': 0.0, 'smoke': 0.0,
                 'smoke_age': 0.0, 'smoke_at': [0.0, 0.0], 'ramrod': 0.0, 'tail_sway': 0.0}
HAND_NUMBERS = ('grip', 'offset', 'hang', 'reach')


def load_look(spec):
    looks = spec.data(spec.params['looks'])
    name = spec.params['look']
    if name not in looks['looks']:
        raise KeyError(f'{spec.id}: look {name!r} not in {spec.params["looks"]}; has {sorted(looks["looks"])}')
    look = dict(looks.get('defaults', {}))
    look.update(looks['looks'][name])
    return look


def build_for(drill, look):
    build = dict(figure.DEFAULT_BUILD)
    build.update(drill.get('build', {}))
    build.update(look.get('build', {}))
    return build


def make_mixer(build):
    """Pose interpolation that keeps hands on the musket when both keys grip it."""

    def mix(a, b, t):
        result = {}
        for key in a:
            if key in ('near_hand', 'far_hand'):
                continue
            result[key] = anim.blend(a[key], b.get(key, a[key]), t)
        joints_a = joints_b = None
        for side in ('near_hand', 'far_hand'):
            ha, hb = a.get(side, {}), b.get(side, {})
            if ha.get('grip') is not None and hb.get('grip') is not None:
                result[side] = {'grip': anim.blend(ha['grip'], hb['grip'], t),
                                'offset': anim.blend(ha.get('offset', 0.0), hb.get('offset', 0.0), t)}
            elif ha.get('hang') is not None and hb.get('hang') is not None:
                result[side] = {'hang': anim.blend(ha['hang'], hb['hang'], t),
                                'reach': anim.blend(ha.get('reach', 21.0), hb.get('reach', 21.0), t)}
            else:                                      # different kinds of hold: travel in a straight line
                joints_a = joints_a or rig.solve_figure(a, build)
                joints_b = joints_b or rig.solve_figure(b, build)
                joint = side.replace('_hand', '') + '_hand'
                result[side] = {'at': anim.blend(list(joints_a[joint]), list(joints_b[joint]), t)}
        return result
    return mix


def walk_pose(base, cycle, phase):
    """One frame of the in-place march built on the drill's carrying pose."""
    pose = dict(base)
    near, near_pitch = rig.walk_feet(phase, cycle['stride'], cycle['lift'])
    far, far_pitch = rig.walk_feet(phase + 0.5, cycle['stride'], cycle['lift'])
    bob = cycle.get('bob', 1.0) * math.cos(4 * math.pi * phase)
    pose.update(near_foot=list(near), far_foot=list(far), near_pitch=near_pitch, far_pitch=far_pitch)
    pose['pelvis'] = [base['pelvis'][0], base['pelvis'][1] + bob]
    pose['lean'] = base.get('lean', 0.0) + cycle.get('sway', 0.6) * math.sin(4 * math.pi * phase)
    pose['head'] = base.get('head', 0.0) - cycle.get('sway', 0.6) * math.sin(4 * math.pi * phase)
    gun = dict(base['gun'])
    gun['butt'] = [gun['butt'][0], gun['butt'][1] + bob]
    gun['angle'] = gun['angle'] + cycle.get('gun_sway', 1.2) * math.sin(2 * math.pi * phase)
    pose['gun'] = gun
    pose['far_hand'] = {'hang': cycle.get('arm_swing', 18.0) * math.sin(2 * math.pi * phase), 'reach': 21.5}
    pose['tail_sway'] = 1.4 * math.sin(2 * math.pi * phase + 0.6)
    return pose


def frame_poses(drill, build):
    """clip name -> list of full poses, in the drill's clip order."""
    poses = drill['poses']
    mix = make_mixer(build)
    result = {}
    for name, clip in drill['clips'].items():
        if clip['type'] == 'keys':
            result[name] = anim.sample_keys(clip, poses, POSE_DEFAULTS, mix)
        elif clip['type'] == 'walk':
            base = anim.resolve(clip['pose'], poses, POSE_DEFAULTS)
            result[name] = [walk_pose(base, clip, index / clip['frames']) for index in range(clip['frames'])]
        else:
            raise ValueError(f'Clip {name!r} has unknown type {clip["type"]!r}')
    return result


def paint(spec):
    """params: looks + look (uniform), drill (poses and clips)."""
    look = load_look(spec)
    drill = spec.data(spec.params['drill'])
    build = build_for(drill, look)
    by_clip = frame_poses(drill, build)
    clips, total = anim.clip_table(drill['clips'])
    poses = [pose for name in drill['clips'] for pose in by_clip[name]]
    if len(poses) != total:
        raise ValueError(f'{spec.id}: drill produced {len(poses)} frames but its clips declare {total}')
    pal = spec.palette

    formation = spec.params.get('formation', [{'offset': [0, 0]}])
    spans = {name: record['frames'] for name, record in clips.items()}
    frame_clip = {index: name for name, indices in spans.items() for index in indices}

    def member_pose(index, delay):
        """A rank that acts `delay` frames late stays inside the same clip."""
        indices = spans[frame_clip[index]]
        position = indices.index(index) - delay
        if clips[frame_clip[index]]['loop']:
            return poses[indices[position % len(indices)]]
        return poses[indices[max(0, position)]]

    def draw_frame(ctx, index):
        for member in sorted(formation, key=lambda member: member['offset'][1]):       # rear rank first
            pose = member_pose(index, member.get('delay', 0))
            joints = rig.solve_figure(pose, build)
            joints['tail_sway'] = pose.get('tail_sway', 0.0)
            scale = build.get('scale', 1.0) * member.get('scale', 1.0)
            ctx.save()
            ctx.translate(ANCHOR[0] + member['offset'][0], ANCHOR[1] + member['offset'][1])
            ctx.scale(scale, scale)
            ctx.push_group()
            figure.foot_soldier(ctx, pal, look, joints, pose)
            if member.get('recede', 0.0) > 0:                  # rear ranks sink back in value
                ctx.set_operator(cairo.OPERATOR_ATOP)
                ctx.set_source_rgba(*pal('ink', member['recede']))
                ctx.paint()
                ctx.set_operator(cairo.OPERATOR_OVER)
            ctx.pop_group_to_source()
            ctx.paint()
            ctx.restore()

    frames = sheet.render(spec.frame, draw_frame, total, lambda image, index: paper_grain(image, spec.seed, fine=0.025, mottle=0))
    return sheet.Work(frames=frames, clips=clips, vector=draw_frame)
