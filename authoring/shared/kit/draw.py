"""Path and ink helpers shared by every painter.

The house style is a hand-coloured engraving: flat gouache washes, a sepia ink
line of slightly uneven weight, and hatching instead of gradients for form.
"""
import math
import cairo


def rgba(value, alpha=1.0):
    """'#rrggbb' or (r,g,b[,a]) in 0..1 -> (r,g,b,a)."""
    if isinstance(value, str):
        value = value.lstrip('#')
        r, g, b = (int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
        return (r, g, b, alpha)
    if len(value) == 3:
        return (*value, alpha)
    return (value[0], value[1], value[2], value[3] * alpha)


def mix(a, b, t):
    a, b = rgba(a), rgba(b)
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(4))


def source(ctx, color, alpha=1.0):
    ctx.set_source_rgba(*rgba(color, alpha))


def clockwise(points):
    """Points ordered clockwise on screen (y down), the direction cairo arcs run.

    Sub-paths that overlap must wind the same way or the fill punches holes.
    """
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1]))
    return list(points) if area >= 0 else list(reversed(points))


def polygon(ctx, points, closed=True):
    ctx.new_sub_path()
    ctx.move_to(*points[0])
    for point in points[1:]:
        ctx.line_to(*point)
    if closed:
        ctx.close_path()


def smooth(ctx, points, closed=True, tension=0.5):
    """Catmull-Rom spline through the points, emitted as cubic Béziers."""
    count = len(points)
    if count < 3:
        return polygon(ctx, points, closed)

    def at(index):
        if closed:
            return points[index % count]
        return points[min(max(index, 0), count - 1)]

    ctx.new_sub_path()
    ctx.move_to(*points[0])
    for i in range(count if closed else count - 1):
        p0, p1, p2, p3 = at(i - 1), at(i), at(i + 1), at(i + 2)
        k = tension / 3.0 * 2.0
        c1 = (p1[0] + (p2[0] - p0[0]) * k / 2, p1[1] + (p2[1] - p0[1]) * k / 2)
        c2 = (p2[0] - (p3[0] - p1[0]) * k / 2, p2[1] - (p3[1] - p1[1]) * k / 2)
        ctx.curve_to(c1[0], c1[1], c2[0], c2[1], p2[0], p2[1])
    if closed:
        ctx.close_path()


def ellipse(ctx, cx, cy, rx, ry, rotation=0.0):
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(rotation)
    ctx.scale(rx, ry)
    ctx.new_sub_path()
    ctx.arc(0, 0, 1, 0, math.tau)
    ctx.restore()


def rounded_rect(ctx, x, y, width, height, radius):
    radius = min(radius, width / 2, height / 2)
    ctx.new_sub_path()
    ctx.arc(x + width - radius, y + radius, radius, -math.pi / 2, 0)
    ctx.arc(x + width - radius, y + height - radius, radius, 0, math.pi / 2)
    ctx.arc(x + radius, y + height - radius, radius, math.pi / 2, math.pi)
    ctx.arc(x + radius, y + radius, radius, math.pi, math.pi * 1.5)
    ctx.close_path()


def capsule(ctx, start, end, start_radius, end_radius):
    """Tapered limb between two joints, round at both ends."""
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dy)
    if length < 1e-6:
        return ellipse(ctx, start[0], start[1], start_radius, start_radius)
    angle = math.atan2(dy, dx)
    # Tangent offset so the sides meet both circles cleanly.
    offset = math.asin(max(-1.0, min(1.0, (start_radius - end_radius) / length)))
    ctx.new_sub_path()
    ctx.arc(start[0], start[1], start_radius, angle + math.pi / 2 - offset, angle - math.pi / 2 + offset)
    ctx.arc(end[0], end[1], end_radius, angle - math.pi / 2 + offset, angle + math.pi / 2 - offset)
    ctx.close_path()


def wash(ctx, color, alpha=1.0, preserve=False):
    source(ctx, color, alpha)
    ctx.fill_preserve() if preserve else ctx.fill()


def line(ctx, color, width, alpha=1.0, preserve=False):
    source(ctx, color, alpha)
    ctx.set_line_width(width)
    ctx.stroke_preserve() if preserve else ctx.stroke()


def inked(ctx, fill, ink, width, fill_alpha=1.0, ink_alpha=1.0):
    """Fill the current path, then draw its ink contour."""
    wash(ctx, fill, fill_alpha, preserve=True)
    line(ctx, ink, width, ink_alpha)


def hatch(ctx, bounds, angle, gap, color, width, alpha=1.0, jitter=None):
    """Parallel engraved lines across `bounds`; call inside a clip."""
    x0, y0, x1, y1 = bounds
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    reach = math.hypot(x1 - x0, y1 - y0) / 2 + gap
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(angle)
    source(ctx, color, alpha)
    ctx.set_line_width(width)
    position, index = -reach, 0
    while position <= reach:
        shift = jitter(index) if jitter else 0.0
        ctx.move_to(-reach, position + shift)
        ctx.line_to(reach, position + shift)
        position += gap
        index += 1
    ctx.stroke()
    ctx.restore()


def shadow_blob(ctx, cx, cy, rx, ry, color, alpha):
    """Soft contact shadow; a radial fade keeps it from reading as a hard disc."""
    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(rx, ry)
    pattern = cairo.RadialGradient(0, 0, 0, 0, 0, 1)
    r, g, b, _ = rgba(color)
    pattern.add_color_stop_rgba(0.0, r, g, b, alpha)
    pattern.add_color_stop_rgba(0.65, r, g, b, alpha * 0.55)
    pattern.add_color_stop_rgba(1.0, r, g, b, 0.0)
    ctx.set_source(pattern)
    ctx.new_sub_path()
    ctx.arc(0, 0, 1, 0, math.tau)
    ctx.fill()
    ctx.restore()


def polar(origin, angle_degrees, length):
    """Point at `length` from origin; 0° points down the screen, positive swings forward (+x)."""
    radians = math.radians(angle_degrees)
    return (origin[0] + math.sin(radians) * length, origin[1] + math.cos(radians) * length)


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_point(a, b, t):
    return (lerp(a[0], b[0], t), lerp(a[1], b[1], t))
