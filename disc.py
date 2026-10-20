#!/usr/bin/env python3
"""Spinning red identity disc -> looping GIF (original design, Ares-inspired).

    python disc.py disc.gif [--size 200]
"""
import argparse
import math

from PIL import Image, ImageChops, ImageDraw, ImageFilter

S = 640                    # working resolution, downscaled at the end
BG = (13, 17, 23)          # GitHub dark page background
RED = (255, 36, 36)
HOT = (255, 214, 214)
BODY = (34, 6, 8)
FRAMES = 48
FRAME_MS = 40


def arc(d, r, start, end, width, color):
    c = S / 2
    d.arc([c - r, c - r, c + r, c + r], start, end, fill=color, width=width)


def face(theta, color, scale):
    """One layer of the disc face; scale thins the strokes for the hot core."""
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = lambda px: max(1, round(px * scale))  # noqa: E731
    arc(d, 282, 0, 360, w(16), color)
    for k in range(3):                         # three long blades
        a = theta + k * 120
        arc(d, 238, a, a + 96, w(14), color)
    for k in range(12):                        # counter-rotating ticks
        a = -1.6 * theta + k * 30
        arc(d, 196, a, a + 9, w(14), color)
    arc(d, 160, 0, 360, w(5), color)
    c = S / 2
    hexagon = [(c + 72 * math.cos(math.radians(theta * 0.5 + 60 * k + 30)),
                c + 72 * math.sin(math.radians(theta * 0.5 + 60 * k + 30))) for k in range(6)]
    d.line(hexagon + hexagon[:1], fill=color, width=w(10), joint="curve")
    r = 26 * scale + 6
    d.ellipse([c - r, c - r, c + r, c + r], fill=color)
    return img


def disc_face(theta):
    body = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(body).ellipse([S / 2 - 290, S / 2 - 290, S / 2 + 290, S / 2 + 290], fill=BODY + (255,))
    lines = face(theta, RED + (255,), 1.0)
    glow = lines.filter(ImageFilter.GaussianBlur(16))
    out = Image.alpha_composite(body, glow)
    out = Image.alpha_composite(out, glow)
    out = Image.alpha_composite(out, lines)
    return Image.alpha_composite(out, face(theta, HOT + (255,), 0.35))


def frame(i):
    t = i / FRAMES
    phi = 2 * math.pi * t                      # one full turn around the vertical axis
    theta = 360 * 2 * t                        # blades spin twice per loop
    squash = abs(math.cos(phi))
    canvas = Image.new("RGBA", (S, S), BG + (255,))

    # Rim: a glowing edge that widens as the disc turns side-on.
    rim_w = round(34 * abs(math.sin(phi)))
    if rim_w > 1:
        rim = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        x0 = S / 2 - rim_w / 2
        ImageDraw.Draw(rim).rounded_rectangle([x0, S / 2 - 290, x0 + rim_w, S / 2 + 290],
                                              radius=rim_w / 2, fill=RED + (255,))
        canvas = Image.alpha_composite(canvas, rim.filter(ImageFilter.GaussianBlur(10)))
        canvas = Image.alpha_composite(canvas, rim)

    width = max(4, round(S * squash))
    f = disc_face(theta).resize((width, S), Image.LANCZOS)
    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    layer.paste(f, ((S - width) // 2, 0))
    canvas = Image.alpha_composite(canvas, layer)

    bg = Image.new("RGB", (S, S), BG)
    halo = ImageChops.subtract(canvas.convert("RGB"), bg).filter(ImageFilter.GaussianBlur(28))
    return ImageChops.add(canvas.convert("RGB"), ImageChops.multiply(halo, Image.new("RGB", (S, S), (110, 60, 60))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--size", type=int, default=200)
    args = ap.parse_args()

    frames = [frame(i).resize((args.size, args.size), Image.LANCZOS) for i in range(FRAMES)]
    # One shared palette so the glow doesn't flicker between frames.
    sheet = Image.new("RGB", (args.size * 8, args.size))
    for k in range(8):
        sheet.paste(frames[k * FRAMES // 8], (k * args.size, 0))
    palette = sheet.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    gif = [fr.quantize(palette=palette, dither=Image.Dither.NONE) for fr in frames]
    gif[0].save(args.out, save_all=True, append_images=gif[1:], duration=FRAME_MS, loop=0,
                optimize=False, disposal=1)
    print(f"{args.out}: {FRAMES} frames, {args.size}px")


if __name__ == "__main__":
    main()
