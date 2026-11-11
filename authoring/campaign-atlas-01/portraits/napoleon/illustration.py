"""Napoléon, autumn 1805: half-length in the green chasseur coat and plain cocked hat.

An original drawing on the 512x640 bust canvas. The head is turned a little to
the viewer's left with the eyes brought back to the viewer; light falls from the
upper left and the brim throws the eyes into shade. What is documented and what
is interpretation is recorded in character.json.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from shared.kit import draw as pen  # noqa: E402

INK = 2.2
HEAD_SCALE = 1.08


def hatch_in(ctx, pal, path, bounds, angle, gap, alpha, width=0.9):
    """Engraver's shading: parallel lines confined to a shape."""
    ctx.save()
    ctx.append_path(path)
    ctx.clip()
    pen.hatch(ctx, bounds, angle, gap, pal('ink'), width, alpha)
    ctx.restore()


def shape(ctx, points, tension=0.5):
    pen.smooth(ctx, points, tension=tension)
    return ctx.copy_path()


def coat(ctx, pal):
    body = [(246, 372), (176, 352), (120, 384), (60, 424), (36, 520), (22, 640), (490, 640), (478, 520), (456, 424), (392, 384), (318, 352)]
    path = shape(ctx, body, 0.32)
    pen.wash(ctx, pal('np_coat'))
    ctx.save()
    ctx.append_path(path)
    ctx.clip()
    pen.shadow_blob(ctx, 420, 560, 130, 190, pal('np_coat_deep'), 0.95)             # the side away from the light
    pen.shadow_blob(ctx, 250, 660, 240, 90, pal('np_coat_deep'), 0.8)
    pen.shadow_blob(ctx, 110, 450, 70, 70, pal('np_coat_light'), 0.75)              # lit shoulder
    ctx.restore()
    hatch_in(ctx, pal, path, (300, 380, 500, 640), -0.9, 6.0, 0.22)
    # Waistcoat in the opening of the coat, the Legion's red sash across it.
    vest = [(246, 392), (214, 470), (196, 560), (190, 640), (318, 640), (306, 560), (284, 470)]
    pen.polygon(ctx, vest)
    vest_path = ctx.copy_path()
    pen.wash(ctx, pal('np_white'))
    ctx.save()
    ctx.append_path(vest_path)
    ctx.clip()
    pen.shadow_blob(ctx, 300, 560, 40, 120, pal('np_white_shade'), 0.9)
    pen.polygon(ctx, [(196, 470), (226, 452), (322, 600), (300, 640), (268, 640)])
    pen.wash(ctx, pal('np_sash'))
    pen.polygon(ctx, [(226, 452), (322, 600), (316, 612), (220, 462)])
    pen.wash(ctx, pal('np_sash_deep'), 0.7)
    for y in (486, 524, 562, 600):                                                    # waistcoat buttons
        pen.ellipse(ctx, 251, y, 4.2, 4.2)
        pen.inked(ctx, pal('np_gold'), pal('ink'), 1.2)
    ctx.move_to(250, 400)
    ctx.line_to(252, 640)
    pen.line(ctx, pal('ink'), 1.2, 0.55)
    ctx.restore()
    for lapel, fold in (([(246, 376), (190, 372), (150, 420), (176, 520), (196, 560), (214, 470)], [(190, 372), (176, 520)]),
                        ([(246, 376), (306, 372), (350, 420), (326, 520), (306, 560), (284, 470)], [(306, 372), (326, 520)])):
        pen.polygon(ctx, lapel)                                                      # lapels, piped scarlet
        pen.inked(ctx, pal('np_coat'), pal('ink'), 1.4, ink_alpha=0.7)
        pen.polygon(ctx, [lapel[0], lapel[5], lapel[4]], closed=False)
        pen.line(ctx, pal('np_red'), 4.0)
        pen.polygon(ctx, [lapel[0], lapel[5], lapel[4]], closed=False)
        pen.line(ctx, pal('ink'), 1.2, 0.8)
    for x, y in ((318, 440), (322, 478), (318, 516)):                                 # coat buttons on the wearer's left
        pen.ellipse(ctx, x, y, 5.4, 5.4)
        pen.inked(ctx, pal('np_gold'), pal('ink'), 1.3)
        pen.ellipse(ctx, x - 1.5, y - 1.5, 1.8, 1.8)
        pen.wash(ctx, pal('np_gold_light'))
    ctx.append_path(path)
    pen.line(ctx, pal('ink'), INK)


def decorations(ctx, pal):
    """Star of the Grand Eagle embroidered on the breast; cross of the Legion and the Iron Crown at the lapel."""
    cx, cy = 378, 520
    for index in range(10):
        angle = index * math.tau / 10 - math.pi / 2
        long = 30 if index % 2 == 0 else 18
        tip = (cx + math.cos(angle) * long, cy + math.sin(angle) * long)
        left = (cx + math.cos(angle + 0.32) * 9, cy + math.sin(angle + 0.32) * 9)
        right = (cx + math.cos(angle - 0.32) * 9, cy + math.sin(angle - 0.32) * 9)
        pen.polygon(ctx, [left, tip, right])
        pen.inked(ctx, pal('np_silver'), pal('ink'), 1.0)
    pen.ellipse(ctx, cx, cy, 11, 11)
    pen.inked(ctx, pal('np_gold'), pal('ink'), 1.2)
    pen.ellipse(ctx, cx, cy, 6, 6)
    pen.inked(ctx, pal('np_coat_light'), pal('ink'), 0.9)
    for (x, y), ribbon, medal in (((352, 446), 'np_sash', 'np_white'), ((378, 450), 'np_gold', 'np_gold_light')):
        pen.polygon(ctx, [(x - 6, y - 16), (x + 6, y - 16), (x + 5, y), (x - 5, y)])
        pen.inked(ctx, pal(ribbon), pal('ink'), 1.0)
        pen.ellipse(ctx, x, y + 6, 6.5, 6.5)
        pen.inked(ctx, pal(medal), pal('ink'), 1.1)
        pen.ellipse(ctx, x, y + 6, 2.4, 2.4)
        pen.wash(ctx, pal('np_gold'))


def epaulette(ctx, pal, x, y, turn, lit):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(turn)
    for index in range(13):                                                           # bullion fringe
        fx = -46 + index * 7.6
        ctx.move_to(fx, 4)
        ctx.curve_to(fx - 1, 22, fx + 2, 36, fx + 0.5, 50 - abs(index - 6) * 1.6)
    pen.line(ctx, pal('ink'), 6.4)
    for index in range(13):
        fx = -46 + index * 7.6
        ctx.move_to(fx, 4)
        ctx.curve_to(fx - 1, 22, fx + 2, 36, fx + 0.5, 50 - abs(index - 6) * 1.6)
    pen.line(ctx, pal('np_gold' if lit else 'np_gold_deep'), 4.2)
    pen.ellipse(ctx, 0, 0, 56, 17)
    path = ctx.copy_path()
    pen.wash(ctx, pal('np_gold'))
    ctx.save()
    ctx.append_path(path)
    ctx.clip()
    pen.shadow_blob(ctx, -18 if lit else 20, -6, 30, 9, pal('np_gold_light'), 0.9 if lit else 0.4)
    pen.shadow_blob(ctx, 22, 10, 40, 9, pal('np_gold_deep'), 0.8)
    ctx.restore()
    ctx.append_path(path)
    pen.line(ctx, pal('ink'), 1.8)
    pen.ellipse(ctx, 0, 0, 44, 10.5)
    pen.line(ctx, pal('np_gold_deep'), 1.3, 0.8)
    ctx.restore()


def arm_in_waistcoat(ctx, pal):
    """The right forearm carried across, hand slipped inside the waistcoat."""
    sleeve = [(72, 436), (46, 504), (40, 584), (58, 640), (172, 640), (228, 604), (238, 568), (216, 546), (150, 574), (120, 540), (112, 470)]
    path = shape(ctx, sleeve, 0.32)
    pen.wash(ctx, pal('np_coat'))
    ctx.save()
    ctx.append_path(path)
    ctx.clip()
    pen.shadow_blob(ctx, 150, 640, 130, 40, pal('np_coat_deep'), 0.95)
    pen.shadow_blob(ctx, 190, 590, 50, 30, pal('np_coat_deep'), 0.6)
    pen.shadow_blob(ctx, 78, 500, 30, 64, pal('np_coat_light'), 0.75)
    for start in ((108, 556), (128, 572), (92, 590)):                                 # folds gathered at the elbow
        ctx.move_to(*start)
        ctx.curve_to(start[0] + 12, start[1] + 16, start[0] + 8, start[1] + 36, start[0] - 6, start[1] + 50)
    pen.line(ctx, pal('ink'), 1.4, 0.5)
    ctx.restore()
    ctx.append_path(path)
    pen.line(ctx, pal('ink'), INK)
    cuff = [(192, 556), (230, 542), (246, 566), (238, 600), (204, 610)]
    pen.smooth(ctx, cuff, tension=0.3)
    pen.inked(ctx, pal('np_red'), pal('ink'), 1.8)
    for x, y in ((204, 572), (212, 592)):                                             # cuff buttons
        pen.ellipse(ctx, x, y, 3.4, 3.4)
        pen.inked(ctx, pal('np_gold'), pal('ink'), 1.0)
    pen.polygon(ctx, [(236, 546), (250, 550), (252, 592), (240, 598)])                # shirt cuff, then the hand is gone
    pen.inked(ctx, pal('np_white'), pal('ink'), 1.3)


def collar(ctx, pal):
    pen.polygon(ctx, [(226, 322), (266, 322), (260, 384), (246, 394), (232, 384)])   # cravat
    pen.inked(ctx, pal('np_white'), pal('ink'), 1.5)
    for y in (344, 362):
        ctx.move_to(236, y)
        ctx.curve_to(244, y + 8, 250, y + 8, 258, y)
    pen.line(ctx, pal('ink'), 1.1, 0.5)
    for points, shade in (([(172, 316), (226, 332), (241, 378), (196, 370), (168, 350)], False),
                          ([(330, 312), (264, 332), (251, 378), (300, 370), (334, 346)], True)):
        path = shape(ctx, points, 0.22)
        pen.wash(ctx, pal('np_red'))
        ctx.save()
        ctx.append_path(path)
        ctx.clip()
        pen.shadow_blob(ctx, 250, 318, 110, 22, pal('np_red_deep'), 0.9)             # the head's shadow lies on the collar
        if shade:
            pen.shadow_blob(ctx, 322, 344, 36, 36, pal('np_red_deep'), 0.9)
        ctx.restore()
        ctx.append_path(path)
        pen.line(ctx, pal('ink'), 1.9)


def head(ctx, pal):
    skull = [(184, 150), (170, 196), (168, 240), (176, 276), (194, 304), (218, 322), (242, 328), (270, 320),
             (300, 300), (320, 264), (328, 214), (322, 150)]
    path = shape(ctx, skull, 0.5)
    pen.wash(ctx, pal('np_skin'))
    ctx.save()
    ctx.append_path(path)
    ctx.clip()
    # Form: the far cheek takes the light; the near side turns into shadow.
    side = [(276, 150), (272, 204), (290, 236), (284, 272), (264, 300), (252, 332), (336, 332), (340, 150)]
    pen.smooth(ctx, side, tension=0.5)
    side_path = ctx.copy_path()
    pen.wash(ctx, pal('np_skin_shade'), 0.72)
    hatch_in(ctx, pal, side_path, (240, 150, 340, 340), -0.95, 5.0, 0.20)
    pen.shadow_blob(ctx, 318, 252, 24, 70, pal('np_skin_deep'), 0.55)
    pen.shadow_blob(ctx, 194, 246, 24, 30, pal('np_skin_light'), 0.85)                # light on the cheekbone
    pen.shadow_blob(ctx, 234, 310, 24, 12, pal('np_skin_light'), 0.7)                 # and on the chin
    pen.shadow_blob(ctx, 186, 292, 16, 20, pal('np_skin_shade'), 0.5)                 # weight of the jaw
    pen.shadow_blob(ctx, 242, 338, 64, 13, pal('np_skin_deep'), 0.8)                  # under the jaw
    for cx in (207, 270):                                                             # the eye sockets
        pen.shadow_blob(ctx, cx, 213, 24, 15, pal('np_skin_deep'), 0.5)
    # The brim's shadow: a hard band across brow and eyes.
    brim = [(166, 150), (166, 190), (200, 201), (236, 199), (270, 203), (302, 199), (334, 190), (334, 150)]
    pen.smooth(ctx, brim, tension=0.4)
    brim_path = ctx.copy_path()
    pen.wash(ctx, pal('np_skin_deep'), 0.6)
    hatch_in(ctx, pal, brim_path, (166, 150, 334, 206), 0.0, 4.2, 0.15)
    # Hair brushed forward in pointed locks, the longest falling at the centre; then the sideburn.
    for x0, length, lean in ((188, 20, -3), (200, 30, -2), (213, 24, 1), (226, 41, 2), (240, 29, 3), (253, 21, 4), (264, 15, 4)):
        lock = [(x0 - 2, 146), (x0 - 4 + lean * 0.4, 150 + length * 0.55), (x0 + 2 + lean, 150 + length),
                (x0 + 9 + lean * 0.6, 150 + length * 0.5), (x0 + 13, 146)]
        pen.smooth(ctx, lock, tension=0.5)
        pen.wash(ctx, pal('np_hair'))
    sideburn = [(300, 150), (302, 196), (306, 232), (314, 250), (322, 244), (328, 212), (326, 150)]
    pen.smooth(ctx, sideburn, tension=0.4)
    pen.wash(ctx, pal('np_hair'))
    ctx.restore()
    ear = [(322, 214), (334, 208), (342, 228), (336, 256), (322, 264)]                # ear, half lost in hair and shadow
    pen.smooth(ctx, ear, tension=0.5)
    pen.inked(ctx, pal('np_skin_shade'), pal('ink'), 1.6)
    ctx.move_to(328, 222)
    ctx.curve_to(336, 228, 334, 246, 326, 252)
    pen.line(ctx, pal('ink'), 1.1, 0.6)
    ctx.append_path(path)
    pen.line(ctx, pal('ink'), INK)
    features(ctx, pal)


def eye(ctx, pal, cx, cy, half, far):
    lids = [(cx - half, cy + 1.0), (cx - half * 0.45, cy - 6.0), (cx + half * 0.45, cy - 6.2), (cx + half, cy + 0.2),
            (cx + half * 0.4, cy + 5.4), (cx - half * 0.45, cy + 5.6)]
    pen.smooth(ctx, lids, tension=0.5)
    path = ctx.copy_path()
    pen.wash(ctx, pal('np_eye_white'))
    ctx.save()
    ctx.append_path(path)
    ctx.clip()
    iris_x = cx + (2.5 if far else -1.5)                                              # both eyes turned back to the viewer
    pen.ellipse(ctx, iris_x, cy - 0.4, 7.6, 7.8)
    pen.inked(ctx, pal('np_eye'), pal('ink'), 1.3)
    pen.ellipse(ctx, iris_x, cy - 0.4, 3.4, 3.5)
    pen.wash(ctx, pal('ink'))
    pen.ellipse(ctx, iris_x - 2.6, cy - 2.8, 1.6, 1.6)
    pen.wash(ctx, pal('np_eye_white'))
    ctx.rectangle(cx - half, cy - 8, half * 2, 5.4)                                   # the lid's shadow on the eye
    pen.wash(ctx, pal('ink'), 0.38)
    ctx.restore()
    pen.smooth(ctx, lids[:4], closed=False, tension=0.5)                              # heavy upper lid
    pen.line(ctx, pal('ink'), 2.8)
    pen.smooth(ctx, [lids[3], lids[4], lids[5], lids[0]], closed=False, tension=0.5)
    pen.line(ctx, pal('ink'), 1.0, 0.7)
    ctx.move_to(cx - half * 0.7, cy + 9.5)                                            # tiredness under the eye
    ctx.curve_to(cx - half * 0.2, cy + 12.5, cx + half * 0.4, cy + 12.5, cx + half * 0.8, cy + 8.5)
    pen.line(ctx, pal('ink'), 0.9, 0.32)


def features(ctx, pal):
    eye(ctx, pal, 207, 214, 15.0, far=True)
    eye(ctx, pal, 270, 215, 17.5, far=False)
    for brow in ([(186, 204), (198, 200), (214, 200), (228, 206), (214, 205.5), (198, 205)],
                 [(246, 206), (260, 200), (280, 200), (298, 205), (280, 205), (260, 205.5)]):
        pen.smooth(ctx, brow, tension=0.4)                                            # low, level brows, drawn together
        pen.wash(ctx, pal('np_hair'))
    ctx.move_to(235, 200)                                                             # the frown between them
    ctx.line_to(234, 210)
    ctx.move_to(241, 201)
    ctx.line_to(242, 209)
    pen.line(ctx, pal('ink'), 1.1, 0.5)
    # Nose: straight and fine, modelled by its shaded side rather than outlined.
    plane = [(240, 212), (247, 232), (250, 250), (246, 259), (236, 258), (236, 236)]
    pen.smooth(ctx, plane, tension=0.4)
    pen.wash(ctx, pal('np_skin_shade'), 0.85)
    pen.shadow_blob(ctx, 229, 240, 5.5, 16, pal('np_skin_light'), 0.9)                # light down the ridge
    ctx.move_to(241, 214)
    ctx.curve_to(243, 230, 246, 242, 247, 251)
    pen.line(ctx, pal('ink'), 1.3, 0.55)
    tip = [(218, 252), (224, 245), (234, 246), (241, 252), (247, 252), (249, 258), (242, 261), (234, 258), (224, 260), (217, 258)]
    pen.smooth(ctx, tip, closed=False, tension=0.5)
    pen.line(ctx, pal('ink'), 1.5, 0.85)
    pen.ellipse(ctx, 223, 257.5, 3.2, 1.9)
    pen.wash(ctx, pal('ink'), 0.72)
    pen.ellipse(ctx, 242, 258.5, 3.4, 1.9)
    pen.wash(ctx, pal('ink'), 0.72)
    pen.shadow_blob(ctx, 234, 266, 16, 5, pal('np_skin_deep'), 0.55)                  # shadow under the nose
    ctx.move_to(212, 260)                                                             # folds from nostril to mouth
    ctx.curve_to(205, 268, 204, 276, 207, 283)
    ctx.move_to(252, 261)
    ctx.curve_to(260, 268, 262, 276, 259, 284)
    pen.line(ctx, pal('ink'), 1.0, 0.4)
    # Mouth: small, finely cut, firmly closed, the corners held down.
    upper = [(212, 279.5), (222, 275), (229, 277), (233, 275.5), (237, 277), (245, 275.5), (255, 280), (245, 281.5), (233, 281), (222, 281.5)]
    pen.smooth(ctx, upper, tension=0.4)
    pen.wash(ctx, pal('np_lip_deep'))
    lower = [(216, 281), (233, 281.5), (251, 281), (246, 289), (233, 291.5), (221, 289)]
    pen.smooth(ctx, lower, tension=0.5)
    pen.wash(ctx, pal('np_lip'))
    pen.shadow_blob(ctx, 228, 285, 8, 2.6, pal('np_skin_light'), 0.5)
    ctx.move_to(210, 279.5)
    ctx.curve_to(222, 283, 245, 283, 257, 280)
    pen.line(ctx, pal('ink'), 1.8)
    ctx.move_to(209, 279)
    ctx.line_to(206, 283.5)
    ctx.move_to(258, 280)
    ctx.line_to(261, 284.5)
    pen.line(ctx, pal('ink'), 1.3, 0.75)
    pen.shadow_blob(ctx, 233, 297, 14, 4.0, pal('np_skin_deep'), 0.75)                # hollow under the lip
    ctx.move_to(222, 314)                                                             # the set of a heavy chin
    ctx.curve_to(230, 319, 240, 319, 248, 313)
    pen.line(ctx, pal('ink'), 1.0, 0.32)
    ctx.move_to(234, 303)
    ctx.line_to(234, 309)
    pen.line(ctx, pal('ink'), 0.9, 0.3)


def hat(ctx, pal):
    outline = [(88, 152), (112, 116), (158, 76), (214, 54), (256, 49), (300, 54), (356, 76), (402, 116), (426, 154),
               (392, 152), (336, 158), (256, 162), (176, 158), (120, 152)]
    path = shape(ctx, outline, 0.42)
    pen.wash(ctx, pal('np_hat'))
    ctx.save()
    ctx.append_path(path)
    ctx.clip()
    pen.shadow_blob(ctx, 190, 96, 110, 34, pal('np_hat_sheen'), 0.55)                # nap of the felt catching light
    pen.shadow_blob(ctx, 256, 168, 190, 22, pal('ink'), 0.75)
    ctx.move_to(104, 142)
    ctx.curve_to(170, 96, 250, 74, 256, 60)
    ctx.move_to(408, 142)
    ctx.curve_to(346, 98, 268, 76, 256, 60)
    pen.line(ctx, pal('np_hat_sheen'), 1.6, 0.55)
    ctx.restore()
    hatch_in(ctx, pal, path, (256, 40, 430, 170), -0.6, 5.5, 0.30)
    ctx.append_path(path)
    pen.line(ctx, pal('ink'), INK + 0.4)
    ctx.move_to(302, 74)                                                              # cockade loop
    ctx.line_to(296, 150)
    pen.line(ctx, pal('ink'), 5.0)
    ctx.move_to(302, 74)
    ctx.line_to(296, 150)
    pen.line(ctx, pal('np_hat_sheen'), 2.6)
    for colour, radius in (('np_cockade_white', 17), ('np_red', 11.5), ('np_cockade_blue', 6)):
        pen.ellipse(ctx, 304, 96, radius, radius)
        pen.wash(ctx, pal(colour))
    pen.ellipse(ctx, 304, 96, 17, 17)
    pen.line(ctx, pal('ink'), 1.6)
    pen.ellipse(ctx, 296, 150, 4.2, 4.2)
    pen.inked(ctx, pal('np_gold'), pal('ink'), 1.2)


def draw(ctx, pal, character):
    """Entry point used by the shared illustration painter."""
    coat(ctx, pal)
    decorations(ctx, pal)
    epaulette(ctx, pal, 98, 408, -0.3, lit=True)
    epaulette(ctx, pal, 420, 408, 0.3, lit=False)
    arm_in_waistcoat(ctx, pal)
    collar(ctx, pal)
    ctx.save()                              # the head is drawn a little over life against the body, as portraits of state were
    ctx.translate(250, 332)
    ctx.scale(HEAD_SCALE, HEAD_SCALE)
    ctx.translate(-250, -332)
    head(ctx, pal)
    hat(ctx, pal)
    ctx.restore()
