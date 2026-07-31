#!/usr/bin/env python3
"""
Regenerates the cloud-on-a-dusk-sky command banners in assets/.

Run with: uv run --with pillow --with numpy python3 tools/generate_banners.py
"""

import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS = REPO_ROOT / "assets"
FONT_PATH = str(ASSETS / "font.ttf")
SS = 3  # supersample factor

SKY_TOP = (13, 10, 28)
SKY_MID = (32, 20, 56)
SKY_BOTTOM = (56, 27, 58)

CLOUD_HILITE = (240, 231, 255)
CLOUD_MID = (176, 150, 232)
CLOUD_SHADOW = (72, 48, 132)
CLOUD_GLOW = (150, 116, 220)

TEXT_COLOR = (228, 224, 245)
TEXT_GLOW = (150, 116, 220)


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def sky_gradient(size):
    w, h = size
    img = Image.new("RGB", size)
    px = img.load()
    for y in range(h):
        t = y / (h - 1)
        if t < 0.55:
            c = lerp(SKY_TOP, SKY_MID, t / 0.55)
        else:
            c = lerp(SKY_MID, SKY_BOTTOM, (t - 0.55) / 0.45)
        for x in range(0, w, 4):
            px[x, y] = c
            for dx in range(1, min(4, w - x)):
                px[x + dx, y] = c
    return img


def draw_sparkle(draw, cx, cy, size, color, alpha=255):
    long_ = size
    short_ = size * 0.28
    pts = [
        (cx, cy - long_), (cx + short_, cy - short_ * 0.6),
        (cx + long_, cy), (cx + short_, cy + short_ * 0.6),
        (cx, cy + long_), (cx - short_, cy + short_ * 0.6),
        (cx - long_, cy), (cx - short_, cy - short_ * 0.6),
    ]
    draw.polygon(pts, fill=(*color, alpha))


def sparkles_layer(size, sparkles):
    w, h = size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dg = ImageDraw.Draw(glow)
    d = ImageDraw.Draw(overlay)
    for (cx, cy, s, a) in sparkles:
        dg.ellipse([cx - s * 0.9, cy - s * 0.9, cx + s * 0.9, cy + s * 0.9],
                   fill=(210, 190, 255, min(120, a)))
    glow = glow.filter(ImageFilter.GaussianBlur(6 * SS))
    for (cx, cy, s, a) in sparkles:
        draw_sparkle(d, cx, cy, s, (255, 255, 255), a)
    return Image.alpha_composite(glow, overlay)


def moon(size, cx, cy, r):
    w, h = size
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dg = ImageDraw.Draw(glow)
    dg.ellipse([cx - r * 2.6, cy - r * 2.6, cx + r * 2.6, cy + r * 2.6],
               fill=(210, 200, 255, 70))
    glow = glow.filter(ImageFilter.GaussianBlur(r * 0.6))

    bite_r = r * 1.05
    bite_cx = cx + r * 0.55
    mask = Image.new("L", (w, h), 0)
    dm = ImageDraw.Draw(mask)
    dm.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    dm.ellipse([bite_cx - bite_r, cy - bite_r, bite_cx + bite_r, cy + bite_r], fill=0)
    moon_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    moon_img.paste((248, 244, 255, 235), (0, 0, w, h), mask)
    return Image.alpha_composite(glow, moon_img)


def cloud_lobes(cx, cy, scale):
    return [
        (cx - 0.62 * scale, cy + 0.05 * scale, 0.40 * scale),
        (cx - 0.30 * scale, cy - 0.28 * scale, 0.50 * scale),
        (cx + 0.10 * scale, cy - 0.38 * scale, 0.56 * scale),
        (cx + 0.48 * scale, cy - 0.18 * scale, 0.48 * scale),
        (cx + 0.66 * scale, cy + 0.12 * scale, 0.36 * scale),
        (cx + 0.30 * scale, cy + 0.30 * scale, 0.42 * scale),
        (cx - 0.15 * scale, cy + 0.32 * scale, 0.44 * scale),
        (cx - 0.50 * scale, cy + 0.28 * scale, 0.34 * scale),
    ]


def cloud_silhouette_mask(size, lobes):
    mask = Image.new("L", size, 0)
    d = ImageDraw.Draw(mask)
    for (x, y, r) in lobes:
        d.ellipse([x - r, y - r, x + r, y + r], fill=255)
    return mask


def smooth_radial_gradient(size, center, near_color, far_color, max_r, ease=1.3):
    w, h = size
    ys, xs = np.mgrid[0:h, 0:w]
    dist = np.sqrt((xs - center[0]) ** 2 + (ys - center[1]) ** 2)
    t = np.clip(dist / max_r, 0, 1) ** ease
    near = np.array(near_color, dtype=np.float32)
    far = np.array(far_color, dtype=np.float32)
    grad = near[None, None, :] + (far - near)[None, None, :] * t[:, :, None]
    return Image.fromarray(grad.astype(np.uint8), mode="RGB")


def draw_cloud(size, cx, cy, scale):
    w, h = size
    lobes = cloud_lobes(cx, cy, scale)
    silhouette = cloud_silhouette_mask(size, lobes)

    glow = Image.new("RGBA", size, (0, 0, 0, 0))
    glow.paste((*CLOUD_GLOW, 110), (0, 0, w, h), silhouette)
    glow = glow.filter(ImageFilter.GaussianBlur(scale * 0.16))

    hl_cx, hl_cy = cx - 0.30 * scale, cy - 0.34 * scale
    shade = smooth_radial_gradient(
        size, (hl_cx, hl_cy), CLOUD_HILITE, CLOUD_SHADOW, scale * 1.75, ease=1.15
    )

    cloud_rgba = Image.new("RGBA", size, (0, 0, 0, 0))
    cloud_rgba.paste(shade, (0, 0), silhouette)

    # Rim light: erode the silhouette to get a thin edge band, then keep
    # only the part of that band facing the (upper-left) light source.
    erode_px = max(2, int(scale * 0.05))
    eroded = silhouette.filter(ImageFilter.MinFilter(2 * erode_px + 1))
    rim_band = Image.fromarray(
        np.maximum(
            np.array(silhouette, dtype=np.int16) - np.array(eroded, dtype=np.int16), 0
        ).astype(np.uint8)
    )
    rim_band = rim_band.filter(ImageFilter.GaussianBlur(scale * 0.012))

    ys, xs = np.mgrid[0:h, 0:w]
    light_dir = np.array([-0.55, -0.75])
    light_dir = light_dir / np.linalg.norm(light_dir)
    nx = (xs - cx).astype(np.float32)
    ny = (ys - cy).astype(np.float32)
    norm = np.sqrt(nx ** 2 + ny ** 2) + 1e-6
    dot = (nx / norm) * light_dir[0] + (ny / norm) * light_dir[1]
    facing = np.clip(dot, 0, 1) ** 0.8
    rim_arr = np.array(rim_band, dtype=np.float32) / 255.0 * facing
    rim_alpha = Image.fromarray((rim_arr * 255).astype(np.uint8))

    rim_final = Image.new("RGBA", size, (0, 0, 0, 0))
    rim_final.paste((255, 252, 255, 255), (0, 0, w, h), rim_alpha)

    out = Image.alpha_composite(glow, cloud_rgba)
    out = Image.alpha_composite(out, rim_final)

    streak_layer = Image.new("RGBA", size, (0, 0, 0, 0))
    dstreak = ImageDraw.Draw(streak_layer)
    base_y = cy + scale * 0.42
    for i, dx in enumerate([-0.32, -0.12, 0.10, 0.30]):
        x0 = cx + dx * scale
        length = scale * (0.22 + 0.05 * (i % 2))
        dstreak.line([(x0, base_y), (x0 - scale * 0.03, base_y + length)],
                     fill=(190, 175, 235, 130), width=max(2, int(scale * 0.01)))
    out = Image.alpha_composite(out, streak_layer)

    return out


def load_font(px):
    return ImageFont.truetype(FONT_PATH, px)


def draw_text_block(canvas_rgba, anchor_x, cy, title, subtitle, align):
    w, h = canvas_rgba.size
    title_font = load_font(int(76 * SS))
    sub_font = load_font(int(46 * SS))

    tmp = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)

    tb = d.textbbox((0, 0), title, font=title_font)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    sb = d.textbbox((0, 0), subtitle, font=sub_font)
    sw, sh = sb[2] - sb[0], sb[3] - sb[1]

    gap = 18 * SS
    block_h = th + gap + sh
    top = cy - block_h / 2

    if align == "left":
        tx = anchor_x
        sx = anchor_x
    else:
        tx = anchor_x - tw
        sx = anchor_x - sw

    ty = top - tb[1]
    sy = top + th + gap - sb[1]

    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dg = ImageDraw.Draw(glow)
    dg.text((tx, ty), title, font=title_font, fill=(*TEXT_GLOW, 235))
    dg.text((sx, sy), subtitle, font=sub_font, fill=(*TEXT_GLOW, 200))
    glow = glow.filter(ImageFilter.GaussianBlur(6 * SS))

    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ds = ImageDraw.Draw(shadow)
    off = 3 * SS
    ds.text((tx + off, ty + off), title, font=title_font, fill=(0, 0, 0, 140))
    ds.text((sx + off, sy + off), subtitle, font=sub_font, fill=(0, 0, 0, 140))
    shadow = shadow.filter(ImageFilter.GaussianBlur(2 * SS))

    d.text((tx, ty), title, font=title_font, fill=(*TEXT_COLOR, 255))
    d.text((sx, sy), subtitle, font=sub_font, fill=(*TEXT_COLOR, 255))

    out = Image.alpha_composite(canvas_rgba, glow)
    out = Image.alpha_composite(out, shadow)
    out = Image.alpha_composite(out, tmp)
    return out


def _starfield(size, count, seed, max_h_frac=0.7):
    w, h = size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    rnd = random.Random(seed)
    ds = ImageDraw.Draw(overlay)
    for _ in range(count):
        x = rnd.uniform(0, w)
        y = rnd.uniform(0, h * max_h_frac)
        r = rnd.uniform(0.8, 2.2) * SS
        a = rnd.randint(60, 190)
        ds.ellipse([x - r, y - r, x + r, y + r], fill=(230, 225, 255, a))
    return overlay.filter(ImageFilter.GaussianBlur(0.5 * SS))


def _cloud_sparkles(cx, cy, scale, seed, count=5):
    rnd = random.Random(seed)
    sparkles = []
    for _ in range(count):
        ang = rnd.uniform(0, math.tau)
        dist = rnd.uniform(scale * 0.55, scale * 1.05)
        sx = cx + math.cos(ang) * dist
        sy = cy - abs(math.sin(ang)) * dist * 0.9 - scale * 0.15
        s = rnd.uniform(6, 15) * SS
        a = rnd.randint(160, 255)
        sparkles.append((sx, sy, s, a))
    return sparkles


def render_banner(subtitle, cloud_side, out_path, size=(1150, 500)):
    w, h = size[0] * SS, size[1] * SS
    bg_rgba = sky_gradient((w, h)).convert("RGBA")
    bg_rgba = Image.alpha_composite(
        bg_rgba, _starfield((w, h), int(70 * SS), hash(subtitle) & 0xFFFF)
    )

    moon_cx = (w * 0.14) if cloud_side == "right" else (w * 0.86)
    bg_rgba = Image.alpha_composite(bg_rgba, moon((w, h), moon_cx, h * 0.22, 34 * SS))

    scale = h * 0.62
    cloud_cx = w * (0.82 if cloud_side == "right" else 0.18)
    cloud_cy = h * 0.56
    canvas = Image.alpha_composite(bg_rgba, draw_cloud((w, h), cloud_cx, cloud_cy, scale))

    sparkles = _cloud_sparkles(cloud_cx, cloud_cy, scale, (hash(subtitle) >> 8) & 0xFFFF)
    canvas = Image.alpha_composite(canvas, sparkles_layer((w, h), sparkles))

    text_anchor_x = w * 0.12 if cloud_side == "right" else w * 0.88
    align = "left" if cloud_side == "right" else "right"
    canvas = draw_text_block(canvas, text_anchor_x, h * 0.52, "NIMBUS", subtitle, align)

    final = canvas.convert("RGB").resize(size, Image.LANCZOS)
    final.save(out_path, optimize=True)
    print("wrote", out_path)


def render_square(out_path, size=(1000, 1000)):
    w, h = size[0] * SS, size[1] * SS
    bg = sky_gradient((w, h)).convert("RGBA")
    bg = Image.alpha_composite(bg, _starfield((w, h), int(90 * SS), 42, max_h_frac=0.55))
    bg = Image.alpha_composite(bg, moon((w, h), w * 0.80, h * 0.16, 34 * SS))

    scale = h * 0.30
    cloud_cx, cloud_cy = w * 0.5, h * 0.40
    canvas = Image.alpha_composite(bg, draw_cloud((w, h), cloud_cx, cloud_cy, scale))

    sparkles = _cloud_sparkles(cloud_cx, cloud_cy, scale, 99)
    canvas = Image.alpha_composite(canvas, sparkles_layer((w, h), sparkles))

    tmp = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    title_font = load_font(int(92 * SS))
    title = "NIMBUS"
    tb = d.textbbox((0, 0), title, font=title_font)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    tx = (w - tw) / 2
    ty = h * 0.72 - tb[1]

    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dg = ImageDraw.Draw(glow)
    dg.text((tx, ty), title, font=title_font, fill=(*TEXT_GLOW, 235))
    glow = glow.filter(ImageFilter.GaussianBlur(6 * SS))

    d.text((tx, ty), title, font=title_font, fill=(*TEXT_COLOR, 255))

    canvas = Image.alpha_composite(canvas, glow)
    canvas = Image.alpha_composite(canvas, tmp)

    final = canvas.convert("RGB").resize(size, Image.LANCZOS)
    final.save(out_path, optimize=True)
    print("wrote", out_path)


BANNERS = [
    ("ABOUT USERBOT", "right", "nimbus_cmd.png"),
    ("INFO", "left", "nimbus_info.png"),
    ("IT'S USERBOT", "right", "start_cmd.png"),
    ("PRESETS", "right", "presets_cmd.png"),
    ("STARTED", "left", "nimbus_started.png"),
    ("INSTALLATION", "left", "nimbus_installation.png"),
    ("UPDATED", "left", "updated.png"),
    ("JOINED", "right", "joined_jr.png"),
    ("DECLINED JOIN", "right", "declined_jr.png"),
    ("JOIN REQUEST", "left", "join_request.png"),
    ("UNIT ALPHA", "left", "unit_alpha.png"),
]


if __name__ == "__main__":
    for subtitle, side, filename in BANNERS:
        render_banner(subtitle, side, str(ASSETS / filename))
    render_square(str(ASSETS / "nimbus.png"))
