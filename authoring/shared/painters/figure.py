"""Drawing a soldier from solved joints and a look record.

Geometry lives here; every colour and every optional item (headgear type,
shoulder ornaments, moustache, second crossbelt) comes from the look, so a new
regiment or nation is a look entry, not a code branch. Coordinates are frame
pixels relative to the ground anchor, facing +x.
"""
import math

from ..kit import draw
from ..kit.rig import along

INK = 1.2
FAR_TONE = 0.80                                   # far-side limbs sit back in value

# A campaigner's proportions, about five and a half heads: sturdy enough to read at map
# scale without tipping into a toy soldier.
DEFAULT_BUILD = {'spine': 24.0, 'near_shoulder': (-5.4, 22.0), 'far_shoulder': (5.0, 22.6),
                 'near_hip': (-2.0, 0.0), 'far_hip': (2.6, 0.3), 'neck': 9.6, 'head_forward': 1.0, 'head_scale': 0.93,
                 'thigh': 20.0, 'shin': 19.0, 'ankle': 3.0, 'upper_arm': 12.5, 'forearm': 12.0, 'scale': 1.06}


class Painter:
    def __init__(self, ctx, pal, look):
        self.ctx, self.pal, self.look = ctx, pal, look

    def colour(self, role, far=False):
        name = self.look[role]
        return self.pal.tone(name, FAR_TONE) if far else self.pal(name)

    def inked(self, role, far=False, width=INK):
        draw.inked(self.ctx, self.colour(role, far), self.pal('ink'), width)

    def fill(self, role, alpha=1.0, far=False):
        draw.wash(self.ctx, self.colour(role, far), alpha)


def contact_shadow(ctx, pal, half_width=17.0, half_height=4.6):
    draw.shadow_blob(ctx, 0.5, 0.6, half_width, half_height, pal('ink'), 0.40)


# ------------------------------------------------------------------ limbs

def leg(p, joints, side):
    far = side == 'far'
    hip, knee, ankle = joints[side + '_hip'], joints[side + '_knee'], joints[side + '_ankle']
    pitch = math.radians(joints[side + '_foot_pitch'])
    shoe = [(-3.9, -0.6), (-4.1, 3.0), (7.4, 3.0), (8.0, 1.3), (2.9, -2.0)]
    points = [(ankle[0] + x * math.cos(pitch) - y * math.sin(pitch), ankle[1] + x * math.sin(pitch) + y * math.cos(pitch))
              for x, y in shoe]
    draw.polygon(p.ctx, points)
    p.inked('shoes', far)
    draw.capsule(p.ctx, hip, knee, 5.5, 4.4)
    p.inked('breeches', far)
    gaiter_top = draw.lerp_point(knee, hip, p.look.get('gaiter_height', 0.10))
    draw.capsule(p.ctx, gaiter_top, knee, 4.6, 4.4)
    p.inked('gaiters', far)
    draw.capsule(p.ctx, knee, ankle, 4.4, 3.3)
    p.inked('gaiters', far)


def arm(p, joints, side):
    far = side == 'far'
    shoulder, elbow, hand = joints[side + '_shoulder'], joints[side + '_elbow'], joints[side + '_hand']
    draw.capsule(p.ctx, shoulder, elbow, 4.5, 3.8)
    p.inked('coat', far)
    draw.capsule(p.ctx, elbow, hand, 3.8, 3.2)
    p.inked('coat', far)
    draw.capsule(p.ctx, draw.lerp_point(elbow, hand, 0.52), draw.lerp_point(elbow, hand, 0.86), 3.85, 3.5)
    p.inked('cuff', far)
    draw.ellipse(p.ctx, hand[0], hand[1], 3.0, 3.0)
    p.inked('skin', far, width=1.0)
    if not far:
        shoulder_ornament(p, joints)


def shoulder_ornament(p, joints):
    ornament = p.look.get('shoulder', {'type': 'none'})
    shoulder, elbow = joints['near_shoulder'], joints['near_elbow']
    torso = joints['torso']
    top = (shoulder[0] + torso.up[0] * 3.0, shoulder[1] + torso.up[1] * 3.0)
    if ornament['type'] == 'strap':
        inner = (top[0] + torso.forward[0] * 4.0, top[1] + torso.forward[1] * 4.0)
        p.ctx.move_to(*top)
        p.ctx.line_to(*inner)
        draw.line(p.ctx, p.pal(ornament['piping']), 2.4)
        p.ctx.move_to(*top)
        p.ctx.line_to(*inner)
        draw.line(p.ctx, p.pal(ornament['colour']), 1.3)
    elif ornament['type'] == 'epaulette':
        down = draw.lerp_point(shoulder, elbow, 0.34)
        for offset in (-2.6, -0.9, 0.9, 2.6):                 # fringe
            p.ctx.move_to(top[0] + torso.forward[0] * (offset - 1.5), top[1] + torso.forward[1] * (offset - 1.5) + 1.5)
            p.ctx.line_to(down[0] + torso.forward[0] * (offset * 1.25 - 1.2), down[1] + 1.2)
        draw.line(p.ctx, p.pal('ink'), 2.3)
        for offset in (-2.6, -0.9, 0.9, 2.6):
            p.ctx.move_to(top[0] + torso.forward[0] * (offset - 1.5), top[1] + torso.forward[1] * (offset - 1.5) + 1.5)
            p.ctx.line_to(down[0] + torso.forward[0] * (offset * 1.25 - 1.2), down[1] + 1.2)
        draw.line(p.ctx, p.pal(ornament['colour']), 1.3)
        angle = math.atan2(torso.forward[1], torso.forward[0])
        draw.ellipse(p.ctx, top[0] - torso.forward[0] * 1.0, top[1] + 0.4, 5.0, 2.5, angle)
        draw.inked(p.ctx, p.pal(ornament['colour']), p.pal('ink'), 1.0)


# ------------------------------------------------------------------ trunk

def pack(p, joints):
    if not p.look.get('pack'):
        return
    torso = joints['torso']
    corners = [torso.at(-16.4, 7.0), torso.at(-16.0, 20.4), torso.at(-7.0, 21.2), torso.at(-6.6, 7.6)]
    draw.smooth(p.ctx, corners, tension=0.25)
    p.inked('pack')
    draw.source(p.ctx, p.pal('ink'), 0.5)                       # calfskin hair
    p.ctx.set_line_width(0.7)
    for forward, up in ((-14.4, 11.0), (-11.2, 13.0), (-13.4, 16.4), (-9.8, 17.8), (-12.0, 9.4)):
        a, b = torso.at(forward, up), torso.at(forward - 0.6, up - 2.0)
        p.ctx.move_to(*a)
        p.ctx.line_to(*b)
    p.ctx.stroke()
    if p.look.get('roll'):
        draw.capsule(p.ctx, torso.at(-16.0, 23.4), torso.at(-7.8, 24.2), 3.1, 3.1)
        p.inked('roll')
        for forward in (-13.8, -10.0):
            p.ctx.move_to(*torso.at(forward, 20.6))
            p.ctx.line_to(*torso.at(forward + 0.2, 27.0))
        draw.line(p.ctx, p.colour('belts'), 1.3)


def tails(p, joints):
    torso = joints['torso']
    sway = joints.get('tail_sway', 0.0)
    if not p.look.get('tails', True):
        return
    outline = [torso.at(-6.6, 9.5), torso.at(-10.2 - sway * 0.4, -3.0), torso.at(-11.6 - sway, -17.5),
               torso.at(-6.2 - sway, -18.6), torso.at(-3.0, -4.5), torso.at(-0.6, 3.0)]
    draw.polygon(p.ctx, outline)
    p.inked('coat')
    draw.polygon(p.ctx, [torso.at(-11.3 - sway, -17.0), torso.at(-6.3 - sway, -18.2), torso.at(-5.0 - sway * 0.6, -9.5)])
    p.inked('turnback', width=0.9)


def crossbelt(p, start, end):
    for colour, width in ((p.pal('ink'), 4.9), (p.colour('belts'), 3.4)):
        p.ctx.move_to(*start)
        p.ctx.line_to(*end)
        draw.line(p.ctx, colour, width)


def chest_lapels(p, t):
    """Coat cut away over a contrasting plastron and waistcoat (French habit, most line coats)."""
    ctx = p.ctx
    draw.polygon(ctx, [t.at(1.6, 9.2), t.at(10.8, 8.0), t.at(8.8, -4.0), t.at(-1.6, -4.0)])
    p.fill('waistcoat')
    lapel = [t.at(0.9, 25.6), t.at(9.8, 23.0), t.at(10.6, 14.5), t.at(8.8, 7.4), t.at(2.2, 8.6), t.at(0.2, 16.0)]
    draw.polygon(ctx, lapel)
    p.fill('lapel')
    draw.polygon(ctx, [lapel[0], lapel[5], lapel[4], lapel[3]], closed=False)
    draw.line(ctx, p.colour('piping'), 1.1)
    for up in (20.6, 16.4, 12.2):
        point = t.at(2.2 + (20.6 - up) * 0.06, up)
        draw.ellipse(ctx, point[0], point[1], 0.85, 0.85)
    draw.wash(ctx, p.pal(p.look.get('buttons', 'brass')))


def chest_braid(p, t):
    """Light-cavalry dolman: rows of cord across the breast between button lines."""
    ctx = p.ctx
    for up in (21.5, 18.2, 14.9, 11.6, 8.3, 5.0):
        ctx.move_to(*t.at(1.0, up + 0.5))
        ctx.curve_to(*t.at(4.0, up - 0.3), *t.at(7.0, up - 0.3), *t.at(10.6, up + 0.2))
    draw.line(ctx, p.colour('braid'), 1.25)
    for forward in (1.6, 5.6, 9.4):
        for up in (21.5, 18.2, 14.9, 11.6, 8.3, 5.0):
            point = t.at(forward, up)
            draw.ellipse(ctx, point[0], point[1], 0.7, 0.7)
    draw.wash(ctx, p.pal(p.look.get('buttons', 'brass')))
    if 'sash' in p.look:                                       # barrel sash at the waist
        draw.polygon(ctx, [t.at(-8.0, 4.4), t.at(11.0, 3.6), t.at(10.0, -0.4), t.at(-8.0, 0.4)])
        p.fill('sash')
        for forward in (-3.5, 1.0, 5.5):
            ctx.move_to(*t.at(forward, 4.2))
            ctx.line_to(*t.at(forward, -0.2))
        draw.line(ctx, p.pal(p.look.get('sash_bars', 'cloth_white')), 1.2)


def chest_single(p, t):
    """Single-breasted coat: one button line down a closed front."""
    for up in (21.0, 17.0, 13.0, 9.0, 5.0):
        point = t.at(7.6 - (21.0 - up) * 0.05, up)
        draw.ellipse(p.ctx, point[0], point[1], 0.9, 0.9)
    draw.wash(p.ctx, p.pal(p.look.get('buttons', 'brass')))


CHESTS = {'lapels': chest_lapels, 'braid': chest_braid, 'single': chest_single}


def torso(p, joints):
    ctx, t = p.ctx, joints['torso']
    body = [t.at(-6.8, 0.0), t.at(-6.4, 9.0), t.at(-8.8, 20.2), t.at(-3.6, 24.8), t.at(3.2, 25.0), t.at(8.0, 21.2),
            t.at(9.4, 14.5), t.at(7.8, 6.0), t.at(6.6, -1.0), t.at(0.0, -3.0)]
    draw.smooth(ctx, body, tension=0.45)
    outline = ctx.copy_path()
    p.fill('coat')
    ctx.save()
    ctx.append_path(outline)
    ctx.clip()
    CHESTS[p.look.get('chest', 'lapels')](p, t)
    if p.look.get('crossbelts', 1) >= 1:
        crossbelt(p, t.at(6.2, 24.2), t.at(-7.6, 4.0))          # cartridge-box belt, far shoulder to near hip
    if p.look.get('crossbelts', 1) >= 2:
        crossbelt(p, t.at(-6.6, 23.2), t.at(7.8, 4.5))          # sabre belt crossing it
    if p.look.get('pack'):
        ctx.move_to(*t.at(-6.4, 22.8))                           # knapsack strap round the near shoulder
        ctx.curve_to(*t.at(-3.8, 19.0), *t.at(-4.0, 15.0), *t.at(-6.8, 12.2))
        draw.line(ctx, p.pal('ink'), 2.6, 0.9)
        ctx.move_to(*t.at(-6.4, 22.8))
        ctx.curve_to(*t.at(-3.8, 19.0), *t.at(-4.0, 15.0), *t.at(-6.8, 12.2))
        draw.line(ctx, p.colour('belts'), 1.5)
    draw.shadow_blob(ctx, *t.at(-1.0, 2.0), 10.0, 5.0, p.pal('ink'), 0.26)      # weight gathers at the waist
    draw.shadow_blob(ctx, *t.at(-7.5, 13.0), 4.0, 9.0, p.pal('ink'), 0.20)      # and under the near arm
    ctx.restore()
    ctx.append_path(outline)
    draw.line(ctx, p.pal('ink'), INK)
    draw.polygon(ctx, [t.at(-4.2, 23.0), t.at(4.0, 23.2), t.at(4.5, 27.4), t.at(-3.9, 27.2)])
    p.inked('collar', width=1.0)


def cartridge_box(p, joints):
    if not p.look.get('cartridge_box'):
        return
    t = joints['torso']
    draw.smooth(p.ctx, [t.at(-11.4, -5.0), t.at(-11.0, 2.8), t.at(-4.4, 3.2), t.at(-4.2, -4.6)], tension=0.2)
    p.inked('cartridge_box')
    centre = t.at(-7.7, -0.8)
    draw.ellipse(p.ctx, centre[0], centre[1], 1.1, 1.1)
    draw.wash(p.ctx, p.pal(p.look.get('buttons', 'brass')))
    if p.look.get('sidearm') == 'briquet':                    # grenadier's short sabre at the hip
        p.ctx.move_to(*t.at(-4.0, 1.5))
        p.ctx.line_to(*t.at(-12.5, -11.0))
        draw.line(p.ctx, p.pal('ink'), 2.6)
        p.ctx.move_to(*t.at(-4.0, 1.5))
        p.ctx.line_to(*t.at(-12.5, -11.0))
        draw.line(p.ctx, p.pal('scabbard'), 1.4)
        hilt = t.at(-3.6, 2.2)
        draw.ellipse(p.ctx, hilt[0], hilt[1], 1.6, 1.6)
        draw.inked(p.ctx, p.pal('brass'), p.pal('ink'), 0.8)


# ------------------------------------------------------------------ head and headgear

def head(p, joints):
    ctx, h, t = p.ctx, joints['head_frame'], joints['torso']
    draw.capsule(ctx, t.at(0.2, 24.6), h.at(0.4, -5.6), 3.6, 3.4)                               # neck stock
    p.inked('stock', width=1.0)
    tilt = math.atan2(h.forward[1], h.forward[0])
    draw.ellipse(ctx, h.origin[0], h.origin[1], 7.6 * h.scale, 8.4 * h.scale, tilt)
    skull = ctx.copy_path()
    p.fill('skin')
    ctx.save()
    ctx.append_path(skull)
    ctx.clip()
    hair = [h.at(2.6, 9.4), h.at(-4.0, 9.6), h.at(-9.0, 3.0), h.at(-7.6, -6.5), h.at(-3.2, -6.2), h.at(-1.6, -3.4),
            h.at(-2.2, 1.0), h.at(-0.4, 5.0)]
    draw.smooth(ctx, hair, tension=0.4)
    p.fill('hair')
    jaw = h.at(-1.0, -5.5)                                      # weathered jaw, no rouge
    draw.shadow_blob(ctx, jaw[0], jaw[1], 6.5, 3.6, p.pal('skin_shade'), 0.55)
    brim = h.at(1.0, 9.0)                                       # hard shade thrown by the hat
    draw.shadow_blob(ctx, brim[0], brim[1], 10.5, 7.4, p.pal('skin_shade'), 0.95)
    ctx.restore()
    ctx.append_path(skull)
    draw.line(ctx, p.pal('ink'), INK)
    nose = [h.at(6.9, 1.4), h.at(9.5, -1.2), h.at(7.0, -2.5)]
    draw.polygon(ctx, nose)
    p.fill('skin')
    draw.polygon(ctx, nose, closed=False)
    draw.line(ctx, p.pal('ink'), 1.0)
    ear = h.at(-1.9, -0.6)
    ctx.new_sub_path()
    ctx.arc(ear[0], ear[1], 1.5, tilt + 0.9, tilt + 4.4)
    draw.line(ctx, p.pal('ink'), 0.8, 0.8)
    eye = h.at(3.5, 0.6)
    draw.ellipse(ctx, eye[0], eye[1], 0.95, 1.1, tilt)
    draw.wash(ctx, p.pal('ink'))
    ctx.move_to(*h.at(1.9, 2.7))
    ctx.line_to(*h.at(5.2, 3.0))
    draw.line(ctx, p.pal('ink'), 1.0)
    ctx.move_to(*h.at(4.6, -4.4))
    ctx.line_to(*h.at(6.9, -4.2))
    draw.line(ctx, p.pal('ink'), 0.9, 0.85)
    if p.look.get('moustache'):
        ctx.move_to(*h.at(3.6, -3.4))
        ctx.curve_to(*h.at(5.4, -2.2), *h.at(7.0, -2.6), *h.at(8.2, -4.0))
        draw.line(ctx, p.colour('hair'), 1.9)
    HEADGEAR[p.look['headgear']['type']](p, h, tilt)


def roundel(p, centre, colours, radius):
    for colour, scale in zip(colours, (1.0, 0.68, 0.36)):
        draw.ellipse(p.ctx, centre[0], centre[1], radius * scale, radius * scale)
        draw.wash(p.ctx, p.pal(colour))
    draw.ellipse(p.ctx, centre[0], centre[1], radius, radius)
    draw.line(p.ctx, p.pal('ink'), 0.6, 0.8)


def bicorne(p, h, tilt):
    """Cocked hat worn athwart, seen three-quarters on."""
    ctx, gear = p.ctx, p.look['headgear']
    outline = [h.at(-15.0, 3.2), h.at(-11.4, 8.6), h.at(-5.6, 14.4), h.at(0.8, 17.4), h.at(6.6, 14.6), h.at(11.6, 9.0),
               h.at(15.4, 3.4), h.at(10.2, 5.0), h.at(1.5, 6.6), h.at(-7.5, 5.4)]
    draw.smooth(ctx, outline, tension=0.42)
    path = ctx.copy_path()
    draw.wash(ctx, p.pal(gear['felt']))
    ctx.save()
    ctx.append_path(path)
    ctx.clip()
    draw.smooth(ctx, [h.at(-13.5, 4.2), h.at(-9.4, 8.8), h.at(-4.2, 13.6), h.at(0.6, 15.6)], closed=False)
    draw.line(ctx, p.pal(gear.get('sheen', 'hat_sheen')), 1.5, 0.6)
    ctx.restore()
    ctx.append_path(path)
    draw.line(ctx, p.pal('ink'), INK)
    if 'lace' in gear:
        ctx.move_to(*h.at(3.4, 11.4))
        ctx.line_to(*h.at(3.0, 6.6))
        draw.line(ctx, p.pal(gear['lace']), 1.3)
    if 'cockade' in gear:
        roundel(p, h.at(3.4, 11.6), gear['cockade'], 2.7)
    if 'pompon' in gear:
        ball = h.at(3.2, 17.4)
        draw.ellipse(ctx, ball[0], ball[1], 2.5, 2.3)
        draw.inked(ctx, p.pal(gear['pompon']), p.pal('ink'), 0.9)


def bearskin(p, h, tilt):
    """Grenadier's fur cap with front plate, cords and side plume. gear.height scales the crown."""
    ctx, gear = p.ctx, p.look['headgear']
    k = gear.get('height', 22.0) / 25.4

    def at(forward, up):
        return h.at(forward, 3.0 + (up - 3.0) * k)

    if 'plume' in gear:
        feather = [at(-7.4, 12.0), at(-9.8, 18.0), at(-9.4, 23.5), at(-6.8, 26.4), at(-4.6, 23.0), at(-4.4, 17.0)]
        draw.smooth(ctx, feather, tension=0.5)
        draw.inked(ctx, p.pal(gear['plume']), p.pal('ink'), 1.0)
    outline = [at(-8.4, 2.6), at(-9.8, 9.5), at(-9.0, 17.5), at(-4.8, 23.6), at(1.6, 25.4), at(7.0, 22.2),
               at(9.4, 14.5), at(9.2, 7.0), at(8.4, 3.6), at(0.0, 5.0)]
    draw.smooth(ctx, outline, tension=0.42)
    path = ctx.copy_path()
    draw.wash(ctx, p.pal(gear['fur']))
    ctx.save()
    ctx.append_path(path)
    ctx.clip()
    draw.source(ctx, p.pal(gear.get('sheen', 'hat_sheen')), 0.55)
    ctx.set_line_width(0.9)
    for forward, up in ((-6.5, 9), (-4.0, 13), (-6.8, 16), (-2.5, 19), (1.5, 21.5), (-1.0, 10), (1.5, 15), (4.6, 19)):
        a, b = at(forward, up), at(forward - 0.7, up - 2.6)
        ctx.move_to(*a)
        ctx.line_to(*b)
    ctx.stroke()
    ctx.restore()
    ctx.append_path(path)
    draw.line(ctx, p.pal('ink'), INK)
    if 'plate' in gear:
        draw.polygon(ctx, [at(4.4, 5.2), at(8.8, 4.4), at(9.2, 11.0), at(6.8, 13.6), at(4.4, 11.4)])
        draw.inked(ctx, p.pal(gear['plate']), p.pal('ink'), 0.8)
    if 'cords' in gear:
        ctx.move_to(*at(-9.0, 12.0))
        ctx.curve_to(*at(-3.0, 9.0), *at(3.5, 12.5), *at(9.0, 16.5))
        draw.line(ctx, p.pal(gear['cords']), 1.4)
        tassel = at(-8.6, 8.4)
        draw.ellipse(ctx, tassel[0], tassel[1], 1.5, 2.2)
        draw.inked(ctx, p.pal(gear['cords']), p.pal('ink'), 0.7)


def shako(p, h, tilt):
    """Felt shako: plate, cockade, pompon or plume, optional cords. Proportions from the look."""
    ctx, gear = p.ctx, p.look['headgear']
    height, flare = gear.get('height', 13.0), gear.get('flare', 0.8)
    if 'plume' in gear:
        feather = [h.at(2.0, 6 + height), h.at(0.6, 12 + height), h.at(1.4, 18 + height), h.at(3.6, 20.5 + height),
                   h.at(5.4, 17 + height), h.at(5.0, 10 + height)]
        draw.smooth(ctx, feather, tension=0.5)
        draw.inked(ctx, p.pal(gear['plume']), p.pal('ink'), 1.0)
    body = [h.at(-7.6, 4.4), h.at(-7.6 - flare, 5.0 + height), h.at(8.0 + flare, 5.6 + height), h.at(8.2, 4.8)]
    draw.polygon(ctx, body)
    draw.inked(ctx, p.pal(gear['felt']), p.pal('ink'), INK)
    draw.polygon(ctx, [h.at(-7.6 - flare, 3.6 + height), h.at(-7.6 - flare, 5.4 + height), h.at(8.0 + flare, 6.0 + height),
                       h.at(8.0 + flare, 4.2 + height)])
    draw.inked(ctx, p.pal(gear.get('top_band', gear['felt'])), p.pal('ink'), 0.8)
    peak = [h.at(4.0, 4.6), h.at(11.8, 2.6), h.at(11.4, 1.6), h.at(3.6, 3.4)]
    draw.polygon(ctx, peak)
    draw.inked(ctx, p.pal(gear.get('peak', 'leather_black')), p.pal('ink'), 0.9)
    if 'plate' in gear:
        draw.polygon(ctx, [h.at(3.0, 6.6), h.at(5.6, 5.4), h.at(8.0, 6.8), h.at(5.6, 10.6)])
        draw.inked(ctx, p.pal(gear['plate']), p.pal('ink'), 0.7)
    if 'cockade' in gear:
        roundel(p, h.at(4.6, 2.2 + height), gear['cockade'], 2.3)
    if 'pompon' in gear:
        ball = h.at(4.2, 7.6 + height)
        draw.ellipse(ctx, ball[0], ball[1], 2.4, 2.2)
        draw.inked(ctx, p.pal(gear['pompon']), p.pal('ink'), 0.9)
    if 'cords' in gear:
        ctx.move_to(*h.at(-8.0, 3.0 + height))
        ctx.curve_to(*h.at(-3.0, height - 3.0), *h.at(3.0, height - 2.0), *h.at(8.4, 4.0 + height))
        draw.line(ctx, p.pal(gear['cords']), 1.3)


HEADGEAR = {'bicorne': bicorne, 'bearskin': bearskin, 'shako': shako}


# ------------------------------------------------------------------ musket

def musket(p, gun, near_hand=None, ramrod=0.0):
    ctx, spec = p.ctx, p.look['musket']
    length, blade = spec['length'], spec.get('bayonet', 0.0)

    def g(distance, offset=0.0):
        return along(gun['butt'], gun['angle'], distance, offset)

    ctx.move_to(*g(13, -1.9))                                   # sling
    ctx.curve_to(*g(20, -5.4), *g(32, -5.0), *g(40, -1.4))
    draw.line(ctx, p.pal('ink'), 2.0, 0.85)
    ctx.move_to(*g(13, -1.9))
    ctx.curve_to(*g(20, -5.4), *g(32, -5.0), *g(40, -1.4))
    draw.line(ctx, p.colour('belts'), 1.1)
    if blade:
        draw.polygon(ctx, [g(length - 1.0, 1.4), g(length + 1.4, 3.1), g(length + blade, 2.3), g(length + 1.4, 1.5)])
        draw.inked(ctx, p.pal('steel_light'), p.pal('ink'), 0.75)
    ctx.move_to(*g(12.5, 1.9))                                  # barrel
    ctx.line_to(*g(length, 1.6))
    draw.line(ctx, p.pal('ink'), 3.0)
    stock = [g(0, 2.3), g(11, 1.3), g(15.5, 1.7), g(length - 9, 1.0), g(length - 9, -1.2), g(16, -1.6), g(11, -1.9),
             g(1.6, -3.7), g(0, -3.4)]
    draw.polygon(ctx, stock)
    draw.inked(ctx, p.pal(spec.get('wood', 'gunstock')), p.pal('ink'), 1.0)
    ctx.move_to(*g(12.5, 1.9))
    ctx.line_to(*g(length, 1.6))
    draw.line(ctx, p.pal('steel'), 1.5)
    for distance in spec.get('bands', []):                      # barrel bands
        ctx.move_to(*g(distance, 2.5))
        ctx.line_to(*g(distance, -1.3))
        draw.line(ctx, p.pal(spec.get('furniture', 'brass')), 1.3)
    draw.polygon(ctx, [g(12.4, 2.0), g(17.0, 2.0), g(15.6, 4.6), g(13.4, 3.6)])                 # lock and cock
    draw.inked(ctx, p.pal('steel_dark'), p.pal('ink'), 0.7)
    ctx.move_to(*g(11.4, -1.9))
    ctx.curve_to(*g(12.4, -4.0), *g(15.4, -4.0), *g(16.4, -1.7))
    draw.line(ctx, p.pal(spec.get('furniture', 'brass')), 1.0)
    if ramrod > 0 and near_hand is not None:
        ctx.move_to(*near_hand)
        ctx.line_to(*g(length - 7 * ramrod, 1.6))
        draw.line(ctx, p.pal('ink'), 1.9)
        ctx.move_to(*near_hand)
        ctx.line_to(*g(length - 7 * ramrod, 1.6))
        draw.line(ctx, p.pal('steel_light'), 0.9)


def muzzle_point(look, gun, beyond=0.0):
    return along(gun['butt'], gun['angle'], look['musket']['length'] + beyond, 1.6)


def muzzle_flash(p, gun, strength):
    """Tongue of fire along the bore plus the priming flash at the lock."""
    if strength <= 0:
        return
    ctx, length = p.ctx, p.look['musket']['length']

    def g(distance, offset=0.0):
        return along(gun['butt'], gun['angle'], distance, 1.6 + offset)

    def tongue(reach, breadth, colour, alpha):
        reach, breadth = reach * strength, breadth * strength
        points = [g(length - 1.0, breadth * 0.30), g(length + reach * 0.18, breadth * 0.95), g(length + reach * 0.30, breadth * 0.42),
                  g(length + reach * 0.52, breadth * 0.80), g(length + reach * 0.62, breadth * 0.26), g(length + reach, 0.0),
                  g(length + reach * 0.62, -breadth * 0.26), g(length + reach * 0.52, -breadth * 0.80),
                  g(length + reach * 0.30, -breadth * 0.42), g(length + reach * 0.18, -breadth * 0.95), g(length - 1.0, -breadth * 0.30)]
        draw.polygon(ctx, points)
        draw.wash(ctx, p.pal(colour), alpha)

    tongue(10.5, 12.0, 'flash_edge', 0.96)
    tongue(8.0, 8.0, 'flash_core', 1.0)
    tongue(5.0, 4.2, 'flash_white', 1.0)
    pan = along(gun['butt'], gun['angle'], 14.5, 5.4)
    for radius, colour in ((3.4, 'flash_edge'), (2.0, 'flash_core')):
        draw.ellipse(ctx, pan[0], pan[1] - 0.8, radius * strength, radius * strength * 1.25)
        draw.wash(ctx, p.pal(colour), 0.92)


def powder_smoke(p, centre, strength, age, seed=3):
    """Engraved powder smoke: scalloped puffs that swell with age (0..1) and thin with strength (1..0)."""
    if strength <= 0.02:
        return
    ctx = p.ctx
    spread = 3.5 + age * 9.5
    puffs = [(-0.2, 0.1, 1.0), (0.9, -0.5, 0.82), (0.3, -1.15, 0.74), (1.6, 0.25, 0.6), (-0.9, -0.7, 0.62)]
    placed = [(centre[0] + dx * spread, centre[1] + dy * spread - age * 6.0, (3.4 + age * 5.6) * scale) for dx, dy, scale in puffs]
    for x, y, radius in placed:
        draw.ellipse(ctx, x, y, radius + 0.9, radius + 0.9)
    draw.wash(ctx, p.pal('ink'), 0.55 * strength)
    for x, y, radius in placed:
        draw.ellipse(ctx, x, y, radius, radius)
    draw.wash(ctx, p.pal('powder_smoke'), 0.95 * strength)
    for x, y, radius in placed[:3]:
        ctx.new_sub_path()
        ctx.arc(x + radius * 0.15, y + radius * 0.1, radius * 0.55, 0.3, 2.2)
    draw.line(ctx, p.pal('ink'), 0.75, 0.36 * strength)


def sabre(p, hand, angle_degrees, length=30.0):
    """Curved light-cavalry sabre held at `hand`; angle is the blade's direction (0 = facing, 90 = up)."""
    ctx = p.ctx

    def b(distance, offset=0.0):
        return along(hand, angle_degrees, distance, offset)

    blade = [b(1.5, 0.9), b(length * 0.45, 2.6), b(length * 0.8, 3.0), b(length, 1.2), b(length * 0.8, 1.3), b(length * 0.45, 0.8), b(1.5, -0.7)]
    draw.smooth(ctx, blade, tension=0.4)
    draw.inked(ctx, p.pal('steel_light'), p.pal('ink'), 0.9)
    ctx.move_to(*b(-2.6, 1.0))                                  # stirrup guard
    ctx.curve_to(*b(-2.8, -3.6), *b(1.4, -3.8), *b(2.0, -0.6))
    draw.line(ctx, p.pal('ink'), 2.4)
    ctx.move_to(*b(-2.6, 1.0))
    ctx.curve_to(*b(-2.8, -3.6), *b(1.4, -3.8), *b(2.0, -0.6))
    draw.line(ctx, p.pal(p.look.get('buttons', 'brass')), 1.2)


# ------------------------------------------------------------------ assembly

def foot_soldier(ctx, pal, look, joints, extras):
    """Full figure in painter's order. extras: flash, smoke (strength), smoke_age, smoke_at, ramrod."""
    p = Painter(ctx, pal, look)
    contact_shadow(ctx, pal)
    arm(p, joints, 'far')
    leg(p, joints, 'far')
    pack(p, joints)
    tails(p, joints)
    torso(p, joints)
    leg(p, joints, 'near')
    cartridge_box(p, joints)
    head(p, joints)
    gun = joints['gun']
    if gun is not None:
        musket(p, gun, joints['near_hand'], extras.get('ramrod', 0.0))
    arm(p, joints, 'near')
    powder_smoke(p, extras.get('smoke_at', (0.0, 0.0)), extras.get('smoke', 0.0), extras.get('smoke_age', 0.0))
    if gun is not None:
        muzzle_flash(p, gun, extras.get('flash', 0.0))
