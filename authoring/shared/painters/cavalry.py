"""Mounted troops: a horse rig, a seated rider from figure.py, and a sabre drill.

The horse's legs are solved from hoof targets, so one pair of numbers (gait
phase and gait amount) carries it from standing to full gallop and back. The
rider, tack and coat colours come from the look; timing comes from the drill.
"""
import math

import cairo

from ..kit import anim, draw, rig, sheet
from ..kit.raster import paper_grain
from . import figure
from .infantry import load_look

ANCHOR = (64.0, 112.0)
FAR = figure.FAR_TONE

# Horse measurements in frame pixels, body-local, facing +x, ground at y = 0.
BODY = [(-19, -55.5), (-27, -51.5), (-29.5, -43), (-24, -35), (-10, -33.5), (4, -34.5), (13, -36), (21, -40.5),
        (23.5, -47.5), (17, -54.5), (11, -56.5), (-3, -53.8)]
PIVOT = (-2.0, -44.0)
WITHERS, BREAST, NECK_BASE, TAIL_BASE = (11.0, -56.5), (23.5, -47.0), (17.0, -50.0), (-27.0, -51.0)
SEAT = (-2.5, -55.0)
LEGS = {   # root joint, standing hoof x, gallop reach and lift, phase offset in the stride, which way the middle joint folds
    'far_hind': {'root': (-16.0, -37.5), 'home': -18.0, 'reach': 14.0, 'lift': 9.0, 'offset': 0.00, 'bend': rig.ARM_BEND},
    'near_hind': {'root': (-20.0, -37.0), 'home': -23.0, 'reach': 14.0, 'lift': 9.0, 'offset': 0.12, 'bend': rig.ARM_BEND},
    'far_fore': {'root': (18.5, -38.5), 'home': 21.0, 'reach': 15.0, 'lift': 12.0, 'offset': 0.42, 'bend': rig.LEG_BEND},
    'near_fore': {'root': (14.5, -38.0), 'home': 16.0, 'reach': 15.0, 'lift': 12.0, 'offset': 0.55, 'bend': rig.LEG_BEND},
}
UPPER, LOWER, PASTERN = 19.0, 15.5, 4.6
POSE_DEFAULTS = {'horse': {'phase': 0.0, 'amount': 0.0, 'neck': 40.0, 'head': 58.0, 'tail': 0.0, 'bob': 0.0},
                 'sabre': 80.0, 'swoosh': [0.0, 0.0, 0.0]}


def gallop_hoof(phase, leg, stance=0.34):
    """Hoof position and tilt through one stride of the gallop."""
    p = (phase + leg['offset']) % 1.0
    if p < stance:
        t = p / stance
        return (leg['home'] + 4.0 + leg['reach'] * (1 - 2 * t), 0.0), 0.0
    t = (p - stance) / (1 - stance)
    eased = 0.5 - math.cos(math.pi * t) / 2
    lift = math.sin(math.pi * t) ** 0.85
    return (leg['home'] + 4.0 - leg['reach'] + 2 * leg['reach'] * eased, -leg['lift'] * lift), 55.0 * lift * (1 - t)


def body_motion(horse):
    """Vertical bob and pitch of the trunk for the gait phase."""
    amount, phase = horse['amount'], horse['phase']
    bob = horse.get('bob', 0.0) - 2.6 * amount * math.sin(math.tau * (phase + 0.2))
    pitch = 4.0 * amount * math.sin(math.tau * (phase + 0.45))
    return bob, pitch


def to_local(point, bob, pitch):
    """World (frame) point -> body-local point under the trunk's bob and pitch."""
    angle = math.radians(-pitch)
    x, y = point[0] - PIVOT[0], point[1] - bob - PIVOT[1]
    return (PIVOT[0] + x * math.cos(angle) - y * math.sin(angle), PIVOT[1] + x * math.sin(angle) + y * math.cos(angle))


class Horse:
    def __init__(self, ctx, pal, look):
        self.ctx, self.pal, self.coat = ctx, pal, look['horse']

    def colour(self, role, far=False):
        return self.pal.tone(self.coat[role], FAR) if far else self.pal(self.coat[role])

    def leg(self, name, horse, bob, pitch):
        ctx, leg, far = self.ctx, LEGS[name], name.startswith('far')
        (gx, gy), tilt = gallop_hoof(horse['phase'], leg)
        amount = horse['amount']
        hoof_world = (draw.lerp(leg['home'], gx, amount), gy * amount)
        hoof = to_local(hoof_world, bob, pitch)
        tilt *= amount
        toe = math.radians(tilt)
        fetlock = (hoof[0] - 1.2 - math.sin(toe) * PASTERN, hoof[1] - math.cos(toe) * PASTERN)
        joint, fetlock = rig.two_bone(leg['root'], fetlock, UPPER, LOWER, leg['bend'])
        hind = 'hind' in name
        draw.capsule(ctx, leg['root'], joint, 6.6 if hind else 5.4, 3.3)        # gaskin or forearm, muscled above
        draw.inked(ctx, self.colour('body', far), self.pal('ink'), 1.1)
        draw.capsule(ctx, joint, fetlock, 3.0, 2.3)                             # cannon bone
        draw.inked(ctx, self.colour('points', far), self.pal('ink'), 1.0)
        draw.ellipse(ctx, joint[0], joint[1], 3.0, 3.0)                         # knee or hock, no hard outline
        draw.wash(ctx, self.colour('points' if hind else 'body', far))
        end = (fetlock[0] + 1.2 + math.sin(toe) * PASTERN, fetlock[1] + math.cos(toe) * PASTERN)
        draw.capsule(ctx, fetlock, (end[0], end[1] - 1.6), 2.1, 2.3)
        draw.inked(ctx, self.colour('points', far), self.pal('ink'), 1.0)
        shape = [(-2.6, 0.0), (3.3, 0.0), (2.5, -3.2), (-1.8, -3.2)]
        points = [(end[0] + x * math.cos(toe) - y * math.sin(toe), end[1] + x * math.sin(toe) + y * math.cos(toe)) for x, y in shape]
        draw.polygon(ctx, points)
        draw.inked(ctx, self.colour('hoof', far), self.pal('ink'), 0.9)

    def tail(self, horse):
        ctx = self.ctx
        stream = horse['amount'] * 0.85 + horse.get('tail', 0.0)
        tip = (TAIL_BASE[0] - 6 - 15 * stream, TAIL_BASE[1] + 30 - 22 * stream)
        mid = (TAIL_BASE[0] - 8 - 5 * stream, TAIL_BASE[1] + 12 - 10 * stream)
        outline = [(TAIL_BASE[0] + 1, TAIL_BASE[1] - 2), (mid[0] - 3.5, mid[1] - 2), (tip[0] - 2, tip[1]), (tip[0] + 2.5, tip[1] + 1.5),
                   (mid[0] + 4.5, mid[1] + 3), (TAIL_BASE[0] + 3, TAIL_BASE[1] + 5)]
        draw.smooth(ctx, outline, tension=0.5)
        draw.inked(ctx, self.colour('mane'), self.pal('ink'), 1.1)
        ctx.move_to(mid[0] - 0.5, mid[1])
        ctx.line_to(tip[0] + 0.5, tip[1] - 1)
        draw.line(ctx, self.pal(self.coat.get('mane_sheen', 'hat_sheen')), 0.8, 0.5)

    def body(self):
        ctx = self.ctx
        draw.smooth(ctx, BODY, tension=0.5)
        path = ctx.copy_path()
        draw.wash(ctx, self.colour('body'))
        ctx.save()
        ctx.append_path(path)
        ctx.clip()
        draw.shadow_blob(ctx, -2, -33, 30, 8, self.pal(self.coat['shade']), 0.95)          # belly in shadow
        draw.shadow_blob(ctx, -22, -40, 9, 12, self.pal(self.coat['shade']), 0.5)
        draw.shadow_blob(ctx, -16, -53, 12, 5, self.pal(self.coat['light']), 0.75)          # light along the croup
        draw.shadow_blob(ctx, 14, -52, 8, 5, self.pal(self.coat['light']), 0.6)
        ctx.new_sub_path()                                                                   # haunch and shoulder muscle
        ctx.arc(-18, -44, 10, -0.4, 1.5)
        ctx.new_sub_path()
        ctx.arc(11, -45, 9.5, 0.6, 2.4)
        draw.line(ctx, self.pal('ink'), 0.9, 0.4)
        ctx.restore()
        ctx.append_path(path)
        draw.line(ctx, self.pal('ink'), 1.25)

    def neck_and_head(self, horse):
        ctx = self.ctx
        neck, head = math.radians(horse['neck']), math.radians(horse['head'])
        n = (math.sin(neck), -math.cos(neck))
        m = (math.cos(neck), math.sin(neck))
        poll = (NECK_BASE[0] + n[0] * 23, NECK_BASE[1] + n[1] * 23)
        top, throat = (poll[0] - m[0] * 5.0, poll[1] - m[1] * 5.0), (poll[0] + m[0] * 5.4, poll[1] + m[1] * 5.4)
        crest = (draw.lerp(WITHERS[0], top[0], 0.55) - m[0] * 1.6, draw.lerp(WITHERS[1], top[1], 0.55) - m[1] * 1.6)
        gullet = (draw.lerp(BREAST[0], throat[0], 0.55) - m[0] * 1.0, draw.lerp(BREAST[1], throat[1], 0.55) - m[1] * 1.0)
        outline = [(WITHERS[0] - 3, WITHERS[1] + 2.5), crest, top, throat, gullet, (BREAST[0] - 1, BREAST[1] + 4), (10, -44)]
        draw.smooth(ctx, outline, tension=0.42)
        draw.inked(ctx, self.colour('body'), self.pal('ink'), 1.25)
        flow = horse['amount']
        mane = [(WITHERS[0] - 2, WITHERS[1] + 1), (crest[0] - m[0] * (3 + 3 * flow) - 3 * flow, crest[1] - m[1] * 3 - 1.5 * flow),
                (top[0] - m[0] * (2.5 + 2 * flow) - 2 * flow, top[1] - m[1] * 2.5), (top[0] + n[0] * 2, top[1] + n[1] * 2),
                (top[0] + m[0] * 1.5, top[1] + m[1] * 1.5), (crest[0] + m[0] * 2.0, crest[1] + m[1] * 2.0), (WITHERS[0] + 2.5, WITHERS[1] + 3)]
        draw.smooth(ctx, mane, tension=0.4)
        draw.inked(ctx, self.colour('mane'), self.pal('ink'), 1.0)
        d = (math.cos(head), math.sin(head))
        up = (d[1], -d[0])

        def h(u, v):
            return (poll[0] + d[0] * u + up[0] * v, poll[1] + d[1] * u + up[1] * v)

        for forward in (-0.6, 1.6):                                                          # ears
            draw.polygon(ctx, [h(forward - 1.6, 3.6), h(forward - 2.2, 9.6), h(forward + 1.8, 4.6)])
            draw.inked(ctx, self.colour('body'), self.pal('ink'), 0.9)
        skull = [h(-2.5, 4.4), h(8, 4.3), h(16.5, 2.7), h(21.0, 1.4), h(21.8, -2.6), h(17.5, -4.2), h(10, -4.6), h(2.5, -7.2), h(-3.4, -3.0)]
        draw.smooth(ctx, skull, tension=0.42)
        path = ctx.copy_path()
        draw.wash(ctx, self.colour('body'))
        ctx.save()
        ctx.append_path(path)
        ctx.clip()
        muzzle = h(21, -1)
        draw.shadow_blob(ctx, muzzle[0], muzzle[1], 6.5, 6.0, self.pal(self.coat['points']), 0.9)
        jaw = h(6, -6)
        draw.shadow_blob(ctx, jaw[0], jaw[1], 8, 4, self.pal(self.coat['shade']), 0.7)
        if 'blaze' in self.coat:
            draw.polygon(ctx, [h(3, 4.6), h(17, 2.9), h(17, 1.4), h(3.6, 2.6)])
            draw.wash(ctx, self.pal(self.coat['blaze']), 0.9)
        ctx.restore()
        ctx.append_path(path)
        draw.line(ctx, self.pal('ink'), 1.15)
        eye, nostril = h(6.6, 1.9), h(19.8, -0.3)
        draw.ellipse(ctx, eye[0], eye[1], 1.15, 1.15)
        draw.wash(ctx, self.pal('ink'))
        draw.ellipse(ctx, nostril[0], nostril[1], 0.9, 0.7)
        draw.wash(ctx, self.pal('ink'), 0.9)
        for a, b in ((h(14.8, 3.2), h(15.2, -4.5)), (h(15.2, -3.4), h(1.0, -1.6))):                                # bridle
            ctx.move_to(*a)
            ctx.line_to(*b)
        draw.line(ctx, self.pal(self.coat.get('tack', 'leather_black')), 1.3)
        bit = h(16.8, -3.6)
        draw.ellipse(ctx, bit[0], bit[1], 1.3, 1.3)
        draw.inked(ctx, self.pal('brass'), self.pal('ink'), 0.6)
        forelock = [h(-1.5, 4.5), h(4.5, 5.2), h(6.5, 2.4), h(1.5, 3.0)]
        draw.smooth(ctx, forelock, tension=0.4)
        draw.inked(ctx, self.colour('mane'), self.pal('ink'), 0.8)
        return bit

    def saddlery(self, look):
        ctx, tack = self.ctx, look['saddlery']
        if 'valise' in tack:                                                                 # portmanteau behind the saddle
            draw.capsule(ctx, (-17.5, -57.0), (-11.0, -57.6), 3.2, 3.2)
            draw.inked(ctx, self.pal(tack['valise']), self.pal('ink'), 1.0)
            draw.ellipse(ctx, -17.8, -57.0, 1.5, 2.4)
            draw.wash(ctx, self.pal(tack.get('valise_end', tack['edge'])))
        cloth = [(-15, -56.5), (9.5, -57.5), (11.5, -47), (9, -39), (-3, -37.5), (-15, -39.5), (-17.5, -48)]
        draw.smooth(ctx, cloth, tension=0.35)
        draw.inked(ctx, self.pal(tack['cloth']), self.pal('ink'), 1.1)
        teeth = []                                                                           # wolf-tooth edging
        edge = [(-16.6, -44), (-14.6, -40.2), (-9, -38.4), (-3, -37.9), (3, -38.4), (8.6, -39.6), (10.8, -44)]
        for a, b in zip(edge, edge[1:]):
            mid = draw.lerp_point(a, b, 0.5)
            teeth.append([a, b, (mid[0] + (0 - mid[0]) * 0.12, mid[1] - 3.6)])
        for triangle in teeth:
            draw.polygon(ctx, triangle)
        draw.wash(ctx, self.pal(tack['edge']))
        ctx.move_to(1.5, -39)                                                                # girth and stirrup leather
        ctx.line_to(2.5, -34.6)
        draw.line(ctx, self.pal(self.coat.get('tack', 'leather_black')), 2.0)


def reins(ctx, pal, bit, hand):
    ctx.move_to(*bit)
    ctx.curve_to(bit[0] - 6, bit[1] + 7, hand[0] + 9, hand[1] + 5, hand[0], hand[1])
    draw.line(ctx, pal('ink'), 0.95, 0.9)


def swoosh(ctx, pal, hand, sweep):
    """The blade's path through the cut, as a pale crescent."""
    start, end, alpha = sweep
    if alpha <= 0.02 or abs(end - start) < 1:
        return
    steps = 10
    outer = [rig.along(hand, draw.lerp(start, end, i / steps), 31.0) for i in range(steps + 1)]
    inner = [rig.along(hand, draw.lerp(start, end, i / steps), 31.0 - 9.0 * (i / steps) ** 0.7) for i in range(steps + 1)]
    draw.polygon(ctx, outer + inner[::-1])
    draw.wash(ctx, pal('flash_white'), 0.78 * alpha)


def trooper(ctx, pal, look, pose, build):
    """One horse and rider at the origin, drawn in the trunk's moving frame."""
    horse = pose['horse']
    bob, pitch = body_motion(horse)
    mount = Horse(ctx, pal, look)
    draw.shadow_blob(ctx, 0.0, 1.0, 34.0, 5.6, pal('ink'), 0.42)
    ctx.save()
    ctx.translate(PIVOT[0], PIVOT[1] + bob)
    ctx.rotate(math.radians(pitch))
    ctx.translate(-PIVOT[0], -PIVOT[1])
    mount.leg('far_hind', horse, bob, pitch)
    mount.leg('far_fore', horse, bob, pitch)
    mount.tail(horse)
    mount.body()
    bit = mount.neck_and_head(horse)
    mount.leg('near_hind', horse, bob, pitch)
    mount.leg('near_fore', horse, bob, pitch)
    scale = build.get('rider_scale', 0.85)
    joints = rig.solve_figure(pose['rider'], build)
    rein_hand = (SEAT[0] + joints['far_hand'][0] * scale, SEAT[1] + joints['far_hand'][1] * scale)
    reins(ctx, pal, bit, rein_hand)
    ctx.save()
    ctx.translate(*SEAT)
    ctx.scale(scale, scale)
    p = figure.Painter(ctx, pal, look)
    figure.arm(p, joints, 'far')
    ctx.restore()
    mount.saddlery(look)
    ctx.save()
    ctx.translate(*SEAT)
    ctx.scale(scale, scale)
    figure.torso(p, joints)
    figure.leg(p, joints, 'near')
    figure.head(p, joints)
    swoosh(ctx, pal, joints['near_hand'], pose['swoosh'])
    figure.sabre(p, joints['near_hand'], pose['sabre'], look.get('sabre_length', 30.0))
    figure.arm(p, joints, 'near')
    ctx.restore()
    ctx.restore()


def gallop_pose(base, clip, phase):
    pose = anim.blend(base, base, 0.0)
    pose['horse'] = dict(base['horse'], phase=phase, amount=1.0)
    rise = math.sin(math.tau * (phase + 0.2))
    rider = dict(pose['rider'])
    rider['lean'] = base['rider'].get('lean', 0.0) + clip.get('rider_rock', 3.0) * rise
    rider['pelvis'] = [base['rider']['pelvis'][0], base['rider']['pelvis'][1] - 1.2 * max(0.0, rise)]
    pose['rider'] = rider
    pose['sabre'] = base['sabre'] + 4.0 * rise
    return pose


def frame_poses(drill):
    poses, result = drill['poses'], {}
    for name, clip in drill['clips'].items():
        if clip['type'] == 'keys':
            result[name] = anim.sample_keys(clip, poses, POSE_DEFAULTS)
        elif clip['type'] == 'gallop':
            base = anim.resolve(clip['pose'], poses, POSE_DEFAULTS)
            result[name] = [gallop_pose(base, clip, index / clip['frames']) for index in range(clip['frames'])]
        else:
            raise ValueError(f'Clip {name!r} has unknown type {clip["type"]!r}')
    return result


def paint(spec):
    """params: looks + look (rider, horse and saddlery), drill (poses and clips), optional formation."""
    look = load_look(spec)
    drill = spec.data(spec.params['drill'])
    build = dict(figure.DEFAULT_BUILD)
    build.update(drill.get('build', {}))
    build.update(look.get('build', {}))
    by_clip = frame_poses(drill)
    clips, total = anim.clip_table(drill['clips'])
    poses = [pose for name in drill['clips'] for pose in by_clip[name]]
    pal = spec.palette
    formation = spec.params.get('formation', [{'offset': [0, 0]}])
    spans = {name: record['frames'] for name, record in clips.items()}
    frame_clip = {index: name for name, indices in spans.items() for index in indices}

    def member_pose(index, delay):
        indices = spans[frame_clip[index]]
        position = indices.index(index) - delay
        if clips[frame_clip[index]]['loop']:
            return poses[indices[position % len(indices)]]
        return poses[indices[max(0, position)]]

    def draw_frame(ctx, index):
        for member in sorted(formation, key=lambda member: member['offset'][1]):
            scale = build.get('scale', 1.0) * member.get('scale', 1.0)
            ctx.save()
            ctx.translate(ANCHOR[0] + member['offset'][0], ANCHOR[1] + member['offset'][1])
            ctx.scale(scale, scale)
            ctx.push_group()
            trooper(ctx, pal, look, member_pose(index, member.get('delay', 0)), build)
            if member.get('recede', 0.0) > 0:
                ctx.set_operator(cairo.OPERATOR_ATOP)
                ctx.set_source_rgba(*pal('ink', member['recede']))
                ctx.paint()
                ctx.set_operator(cairo.OPERATOR_OVER)
            ctx.pop_group_to_source()
            ctx.paint()
            ctx.restore()

    frames = sheet.render(spec.frame, draw_frame, total, lambda image, index: paper_grain(image, spec.seed, fine=0.025, mottle=0))
    return sheet.Work(frames=frames, clips=clips, vector=draw_frame)
