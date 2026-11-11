"""Cairo drawing surface -> contract-compliant straight-alpha RGBA images.

Painters draw in frame pixel units on a supersampled cairo surface. This module
owns the conversion to the runtime format: box downsample in premultiplied
space, un-premultiply, and zero the RGB of fully transparent pixels.
"""
import cairo
import numpy as np
from PIL import Image

SUPERSAMPLE = 4


class Canvas:
    """A frame-sized drawing surface. `ctx` works in frame pixels."""

    def __init__(self, width, height, supersample=SUPERSAMPLE):
        self.width, self.height, self.supersample = int(width), int(height), int(supersample)
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.width * self.supersample,
                                          self.height * self.supersample)
        self.ctx = cairo.Context(self.surface)
        self.ctx.scale(self.supersample, self.supersample)
        self.ctx.set_antialias(cairo.ANTIALIAS_BEST)
        self.ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        self.ctx.set_line_cap(cairo.LINE_CAP_ROUND)

    def array(self):
        """Premultiplied float RGBA in 0..255 at frame resolution."""
        self.surface.flush()
        s = self.supersample
        raw = np.frombuffer(self.surface.get_data(), dtype=np.uint8)
        raw = raw.reshape(self.height * s, self.surface.get_stride() // 4, 4)[:, :self.width * s]
        box = raw.astype(np.float32).reshape(self.height, s, self.width, s, 4).mean(axis=(1, 3))
        return box[..., [2, 1, 0, 3]]  # cairo stores BGRA on little-endian hosts

    def image(self):
        return premultiplied_to_image(self.array())


def premultiplied_to_image(premultiplied):
    """Premultiplied float RGBA (0..255) -> straight-alpha 8-bit RGBA image."""
    alpha = premultiplied[..., 3:4]
    safe = np.where(alpha > 0, alpha, 1.0)
    rgb = np.clip(premultiplied[..., :3] * 255.0 / safe, 0, 255)
    out = np.concatenate([rgb, alpha], axis=2)
    out = np.rint(out).astype(np.uint8)
    out[out[..., 3] == 0] = 0
    return Image.fromarray(out, 'RGBA')


def image_to_array(image):
    return np.asarray(image.convert('RGBA'), dtype=np.float32).copy()


def array_to_image(array):
    out = np.rint(np.clip(array, 0, 255)).astype(np.uint8)
    out[out[..., 3] == 0] = 0
    return Image.fromarray(out, 'RGBA')


def paper_grain(image, seed, fine=0.035, mottle=0.03, mottle_cell=24):
    """Laid-paper tooth: per-pixel grain plus slow tonal drift. Alpha is untouched.

    Not lattice-periodic; use fine-only grain (mottle=0) on tiling artwork.
    """
    rng = np.random.default_rng(seed)
    array = image_to_array(image)
    height, width = array.shape[:2]
    factor = 1.0 + (rng.random((height, width), dtype=np.float32) - 0.5) * 2 * fine
    if mottle:
        cells = (max(2, height // mottle_cell + 2), max(2, width // mottle_cell + 2))
        coarse = Image.fromarray((rng.random(cells, dtype=np.float32) * 255).astype(np.uint8), 'L')
        coarse = np.asarray(coarse.resize((width, height), Image.BICUBIC), dtype=np.float32) / 255.0
        factor *= 1.0 + (coarse - 0.5) * 2 * mottle
    array[..., :3] *= factor[..., None]
    return array_to_image(array)


def composite(base, overlay):
    """Straight-alpha source-over of two equally sized RGBA images."""
    out = base.copy()
    out.alpha_composite(overlay)
    return array_to_image(image_to_array(out))


def glow(image, radius, strength=1.0, tint=None):
    """Soft bloom under the artwork, used by effects and selected UI states."""
    from PIL import ImageFilter
    array = image_to_array(image)
    halo = image.filter(ImageFilter.GaussianBlur(radius))
    halo_array = image_to_array(halo)
    if tint is not None:
        halo_array[..., :3] = np.array(tint, dtype=np.float32)
    halo_array[..., 3] = np.clip(halo_array[..., 3] * strength, 0, 255)
    return composite(array_to_image(halo_array), array_to_image(array))


def desaturate(image, amount, lift=0.0):
    """Blend toward luminance; used for disabled UI states."""
    array = image_to_array(image)
    luminance = (array[..., 0] * 0.3 + array[..., 1] * 0.59 + array[..., 2] * 0.11)[..., None]
    array[..., :3] = array[..., :3] * (1 - amount) + luminance * amount
    array[..., :3] = array[..., :3] * (1 - lift) + 255.0 * lift
    return array_to_image(array)


def scale_tone(image, factor):
    array = image_to_array(image)
    array[..., :3] *= factor
    return array_to_image(array)
