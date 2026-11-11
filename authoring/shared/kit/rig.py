"""Skeleton maths for figures: two-bone IK and the foot soldier's joint solve.

Screen coordinates throughout: +x is the facing direction, +y is down, and the
origin is the frame's ground anchor. Poses give intent (where the pelvis, feet,
musket and hands are); this module turns that into joint positions.
"""
import math

ARM_BEND, LEG_BEND = 1, -1          # elbows trail behind and below; knees lead


def two_bone(root, target, first, second, bend):
    """Middle joint and reachable end for a two-segment limb."""
    dx, dy = target[0] - root[0], target[1] - root[1]
    distance = math.hypot(dx, dy)
    reach = min(max(distance, abs(first - second) + 1e-3), first + second - 1e-3)
    base = math.atan2(dy, dx) if distance > 1e-6 else math.pi / 2
    inner = math.acos(max(-1.0, min(1.0, (first * first + reach * reach - second * second) / (2 * first * reach))))
    joint = (root[0] + first * math.cos(base + bend * inner), root[1] + first * math.sin(base + bend * inner))
    end = (root[0] + reach * math.cos(base), root[1] + reach * math.sin(base))
    return joint, end


def along(origin, angle_degrees, distance, offset=0.0):
    """Point on a line leaving origin at angle (0° = facing, 90° = up); offset is to its upper side."""
    radians = math.radians(angle_degrees)
    return (origin[0] + math.cos(radians) * distance + math.sin(radians) * -offset,
            origin[1] - math.sin(radians) * distance - math.cos(radians) * offset)


class Frame2D:
    """A local axis pair: `forward` and `up` unit vectors at an origin."""

    def __init__(self, origin, lean_degrees, scale=1.0):
        lean = math.radians(lean_degrees)
        self.origin, self.scale = origin, scale
        self.forward = (math.cos(lean), math.sin(lean))
        self.up = (math.sin(lean), -math.cos(lean))

    def at(self, forward, up):
        forward, up = forward * self.scale, up * self.scale
        return (self.origin[0] + self.forward[0] * forward + self.up[0] * up,
                self.origin[1] + self.forward[1] * forward + self.up[1] * up)


def hand_target(spec, gun, shoulder):
    """A hand follows the musket ('grip': distance from the butt), a point ('at'), or hangs ('hang': degrees)."""
    if spec.get('grip') is not None:
        return along(gun['butt'], gun['angle'], spec['grip'], spec.get('offset', 0.0))
    if spec.get('at') is not None:
        return tuple(spec['at'])
    swing = math.radians(spec.get('hang', 0.0))
    reach = spec.get('reach', 21.0)
    return (shoulder[0] + math.sin(swing) * reach, shoulder[1] + math.cos(swing) * reach)


def solve_figure(pose, build):
    """Pose + body measurements -> named joints."""
    torso = Frame2D(tuple(pose['pelvis']), pose.get('lean', 0.0))
    joints = {'torso': torso, 'hip': torso.origin, 'chest': torso.at(0, build['spine']),
              'near_shoulder': torso.at(*build['near_shoulder']), 'far_shoulder': torso.at(*build['far_shoulder']),
              'near_hip': torso.at(*build['near_hip']), 'far_hip': torso.at(*build['far_hip'])}
    head = Frame2D(joints['chest'], pose.get('lean', 0.0) + pose.get('head', 0.0))
    joints['head_frame'] = Frame2D(head.at(build['head_forward'], build['neck']),
                                   pose.get('lean', 0.0) + pose.get('head', 0.0), build.get('head_scale', 1.0))
    joints['head'] = joints['head_frame'].origin
    for side in ('near', 'far'):
        foot = pose.get(side + '_foot')
        if foot is not None:                          # planted or stepping: solve from the sole
            ankle = (foot[0], foot[1] - build['ankle'])
            knee, ankle = two_bone(joints[side + '_hip'], ankle, build['thigh'], build['shin'], LEG_BEND)
        else:                                         # seated or free: explicit thigh and knee angles
            thigh_angle, knee_bend = pose[side + '_leg']
            knee = _swing(joints[side + '_hip'], thigh_angle, build['thigh'])
            ankle = _swing(knee, thigh_angle - knee_bend, build['shin'])
        joints[side + '_knee'], joints[side + '_ankle'] = knee, ankle
        joints[side + '_foot_pitch'] = pose.get(side + '_pitch', 0.0)
    gun = pose.get('gun')
    joints['gun'] = gun
    for side in ('near', 'far'):
        shoulder = joints[side + '_shoulder']
        target = hand_target(pose.get(side + '_hand', {}), gun, shoulder)
        elbow, hand = two_bone(shoulder, target, build['upper_arm'], build['forearm'],
                               pose.get(side + '_hand', {}).get('bend', ARM_BEND))
        joints[side + '_elbow'], joints[side + '_hand'] = elbow, hand
    return joints


def _swing(origin, angle_degrees, length):
    """0° hangs straight down; positive swings toward the facing direction."""
    radians = math.radians(angle_degrees)
    return (origin[0] + math.sin(radians) * length, origin[1] + math.cos(radians) * length)


def walk_feet(phase, stride, lift):
    """Sole position and pitch for one foot of an in-place walk; phase 0 = heel strike in front."""
    phase %= 1.0
    if phase < 0.5:                                    # stance: the ground carries the foot back
        t = phase / 0.5
        pitch = -14 * max(0.0, 1 - t * 5) + 22 * max(0.0, t - 0.72) / 0.28      # heel strike, then toe-off
        return (stride / 2 - stride * t, 0.0), pitch
    t = (phase - 0.5) / 0.5                            # swing: lifted and carried forward
    eased = 0.5 - math.cos(math.pi * t) / 2
    return (-stride / 2 + stride * eased, -lift * math.sin(math.pi * t) ** 0.8), 22 - 36 * t
