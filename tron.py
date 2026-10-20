#!/usr/bin/env python3
"""Tron lightcycle contribution graph -> animated SVG.

Two lightcycles race along the gutters of your GitHub contribution grid,
lighting up the squares they pass, until one of them derezzes.

    python tron.py <github-user> <out.svg> [--seed N] [--demo]
"""
import argparse
import random
import re
import urllib.request
from collections import deque

CELL, GAP = 10, 3
STEP = CELL + GAP          # lattice spacing (gutter to gutter)
PAD_X, PAD_TOP, PAD_BOT = 18, 34, 16
DT = 0.075                 # seconds per lattice step
MIN_STEPS = 60             # reroll games shorter than this

BG = "#02060d"
LEVELS = ["#0a1622", "#0c3550", "#105f86", "#1690bd", "#2cc6ee"]
BIKES = [
    {"name": "cyan", "color": "#00eaff", "lit": ["#0d3b4a", "#0f5a6e", "#138297", "#1aaec2", "#5ff2ff"]},
    {"name": "orange", "color": "#ff8c1a", "lit": ["#3d220c", "#5e3210", "#8a4714", "#bd5f18", "#ffaa4d"]},
]
DIRS = [(1, 0), (0, 1), (-1, 0), (0, -1)]


def fetch_levels(user):
    """Return grid[col][row] of levels 0-4 (None for days not shown)."""
    req = urllib.request.Request(
        f"https://github.com/users/{user}/contributions",
        headers={"User-Agent": "tron-contrib"})
    html = urllib.request.urlopen(req, timeout=30).read().decode()
    cells = {}
    for tag in re.findall(r"<td[^>]*ContributionCalendar-day[^>]*>", html):
        m_id = re.search(r'id="contribution-day-component-(\d+)-(\d+)"', tag)
        m_lv = re.search(r'data-level="(\d)"', tag)
        if m_id and m_lv:
            cells[(int(m_id.group(2)), int(m_id.group(1)))] = int(m_lv.group(1))
    if not cells:
        raise SystemExit("no contribution cells found")
    cols = max(c for c, _ in cells) + 1
    return [[cells.get((c, r)) for r in range(7)] for c in range(cols)]


def demo_levels(rng, cols=53):
    return [[rng.choice([0, 0, 0, 1, 1, 2, 3, 4]) for _ in range(7)] for _ in range(cols)]


def simulate(W, H, rng):
    """Two bikes on a (W+1)x(H+1) vertex lattice. Returns paths and crash info."""
    occupied = set()
    bikes = [
        {"pos": (0, 2), "dir": 0},
        {"pos": (W, H - 2), "dir": 2},
    ]
    for b in bikes:
        b["path"] = [b["pos"]]
        b["crashed"] = False
        occupied.add(b["pos"])

    def inside(p):
        return 0 <= p[0] <= W and 0 <= p[1] <= H

    def area(start, blocked):
        seen, q = {start}, deque([start])
        while q:
            x, y = q.popleft()
            for dx, dy in DIRS:
                n = (x + dx, y + dy)
                if inside(n) and n not in occupied and n not in blocked and n not in seen:
                    seen.add(n)
                    q.append(n)
        return len(seen)

    while True:
        moves = []
        for i, b in enumerate(bikes):
            other = bikes[1 - i]["pos"]
            rival_next = {(other[0] + dx, other[1] + dy) for dx, dy in DIRS}
            options = []
            for turn in (0, 1, -1):
                d = (b["dir"] + turn) % 4
                n = (b["pos"][0] + DIRS[d][0], b["pos"][1] + DIRS[d][1])
                if inside(n) and n not in occupied:
                    options.append((area(n, rival_next), turn, d, n))
            if not options:
                d = b["dir"]
                moves.append((d, (b["pos"][0] + DIRS[d][0], b["pos"][1] + DIRS[d][1])))
                continue
            best = max(o[0] for o in options)
            good = [o for o in options if o[0] >= best * 0.97]
            straight = [o for o in good if o[1] == 0]
            roll = rng.random()
            if roll < 0.35:       # hunt: close in on the rival
                pick = min(good, key=lambda o: abs(o[3][0] - other[0]) + abs(o[3][1] - other[1]))
            elif straight and roll < 0.85:
                pick = straight[0]
            else:
                pick = rng.choice(good)
            moves.append((pick[2], pick[3]))

        targets = [m[1] for m in moves]
        for i, b in enumerate(bikes):
            t = targets[i]
            if not inside(t) or t in occupied or t == targets[1 - i]:
                b["crashed"] = True
                b["crash_at"] = t
        if any(b["crashed"] for b in bikes):
            break
        for b, (d, t) in zip(bikes, moves):
            b["dir"], b["pos"] = d, t
            b["path"].append(t)
            occupied.add(t)
    return bikes


def vx(x):
    return PAD_X - GAP / 2 + x * STEP


def vy(y):
    return PAD_TOP - GAP / 2 + y * STEP


def path_d(points):
    """SVG path through lattice points, keeping only the corners."""
    keep = [points[0]]
    for a, b, c in zip(points, points[1:], points[2:]):
        if (b[0] - a[0], b[1] - a[1]) != (c[0] - b[0], c[1] - b[1]):
            keep.append(b)
    if len(points) > 1:
        keep.append(points[-1])
    return "M" + " L".join(f"{vx(x):.1f} {vy(y):.1f}" for x, y in keep)


def fmt(v):
    return f"{v:.4f}".rstrip("0").rstrip(".")


def render(user, grid, bikes):
    W, H = len(grid), 7
    steps = len(bikes[0]["path"]) - 1
    t_play = steps * DT
    t_boom = t_play + 0.7
    t_fade0 = t_boom + 1.8
    t_fade1 = t_fade0 + 0.9
    D = t_fade1 + 0.5
    k = lambda t: fmt(min(max(t / D, 0), 1))  # noqa: E731

    width = PAD_X * 2 + W * STEP - GAP
    height = PAD_TOP + H * STEP - GAP + PAD_BOT
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        "<defs>",
        '<filter id="glow" x="-50%" y="-50%" width="200%" height="200%">'
        '<feGaussianBlur stdDeviation="2.2" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>'
        "</filter>",
        "</defs>",
        f'<rect width="{width}" height="{height}" rx="10" fill="{BG}"/>',
        f'<text x="{PAD_X}" y="21" fill="#5ff2ff" font-family="Consolas,Menlo,monospace" '
        f'font-size="12" letter-spacing="3" filter="url(#glow)">{user.upper()} // THE GRID</text>',
    ]

    # Which bike first lights each cell, and when.
    lit = {}
    for bi, b in enumerate(bikes):
        p = b["path"]
        for s, (a, c) in enumerate(zip(p, p[1:]), start=1):
            if a[1] == c[1]:      # horizontal edge
                x = min(a[0], c[0])
                touched = [(x, a[1] - 1), (x, a[1])]
            else:                 # vertical edge
                y = min(a[1], c[1])
                touched = [(a[0] - 1, y), (a[0], y)]
            for cell in touched:
                if cell not in lit or lit[cell][0] > s:
                    lit[cell] = (s, bi)

    # Contribution squares.
    out.append("<g>")
    for c in range(W):
        for r in range(H):
            lv = grid[c][r]
            if lv is None:
                continue
            base = LEVELS[lv]
            x, y = PAD_X + c * STEP, PAD_TOP + r * STEP
            rect = f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{base}"'
            if (c, r) in lit:
                s, bi = lit[(c, r)]
                on = BIKES[bi]["lit"][lv]
                t0 = s * DT
                out.append(
                    rect + f'><animate attributeName="fill" dur="{fmt(D)}s" repeatCount="indefinite" '
                    f'values="{base};{base};{on};{on};{base};{base}" '
                    f'keyTimes="0;{k(t0)};{k(t0 + 0.25)};{k(t_fade0)};{k(t_fade1)};1"/></rect>')
            else:
                out.append(rect + "/>")
    out.append("</g>")

    # Trails, bikes, explosions.
    fade = (f'<animate attributeName="opacity" dur="{fmt(D)}s" repeatCount="indefinite" '
            f'values="1;1;0;0" keyTimes="0;{k(t_fade0)};{k(t_fade1)};1"/>')
    out.append("<g>" + fade)
    for bi, b in enumerate(bikes):
        color = BIKES[bi]["color"]
        d = path_d(b["path"])
        length = steps * STEP
        out.append(
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2.4" stroke-linejoin="round" '
            f'stroke-linecap="round" filter="url(#glow)" stroke-dasharray="{fmt(length)} {fmt(length + 10)}">'
            f'<animate attributeName="stroke-dashoffset" dur="{fmt(D)}s" repeatCount="indefinite" '
            f'values="{fmt(length)};0;0" keyTimes="0;{k(t_play)};1"/></path>')

        # The bike itself: a small glowing capsule riding the head of the trail.
        hide = ""
        if b["crashed"]:
            hide = (f'<animate attributeName="opacity" dur="{fmt(D)}s" repeatCount="indefinite" '
                    f'values="1;1;0;0" keyTimes="0;{k(t_play)};{k(t_play + 0.05)};1" calcMode="discrete"/>')
        out.append(
            f'<g filter="url(#glow)">{hide}'
            f'<rect x="-7" y="-2.6" width="11" height="5.2" rx="2.6" fill="{color}"/>'
            f'<rect x="-2" y="-1.3" width="6" height="2.6" rx="1.3" fill="#ffffff"/>'
            f'<animateMotion dur="{fmt(D)}s" repeatCount="indefinite" rotate="auto" '
            f'path="{d}" keyPoints="0;1;1" keyTimes="0;{k(t_play)};1" calcMode="linear"/></g>')

        if b["crashed"]:
            last, hit = b["path"][-1], b["crash_at"]
            cx = (vx(last[0]) + vx(hit[0])) / 2
            cy = (vy(last[1]) + vy(hit[1])) / 2
            kt = f'keyTimes="0;{k(t_play)};{k(t_play + 0.15)};{k(t_boom)};1"'
            anim = f'dur="{fmt(D)}s" repeatCount="indefinite"'
            out.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="0" fill="none" stroke="{color}" '
                f'stroke-width="2" filter="url(#glow)" opacity="0">'
                f'<animate attributeName="r" {anim} values="0;0;8;22;22" {kt}/>'
                f'<animate attributeName="opacity" {anim} values="0;0;1;0;0" {kt}/></circle>')
            rng = random.Random(len(b["path"]))
            for j in range(10):
                ang = j * 36 + rng.uniform(-12, 12)
                dist = rng.uniform(14, 30)
                out.append(
                    f'<g transform="translate({cx:.1f} {cy:.1f}) rotate({ang:.0f})">'
                    f'<rect x="0" y="-0.8" width="3" height="1.6" fill="{color}" filter="url(#glow)" opacity="0">'
                    f'<animate attributeName="x" {anim} values="0;0;{dist * 0.5:.1f};{dist:.1f};{dist:.1f}" {kt}/>'
                    f'<animate attributeName="opacity" {anim} values="0;0;1;0;0" {kt}/></rect></g>')
    out.append("</g>")

    # Result banner.
    crashed = [b["crashed"] for b in bikes]
    if all(crashed):
        msg, col = "DOUBLE DEREZZ", "#ffffff"
    else:
        win = crashed.index(False)
        msg, col = f"{BIKES[win]['name'].upper()} WINS // END OF LINE", BIKES[win]["color"]
    out.append(
        f'<text x="{width - PAD_X}" y="21" text-anchor="end" fill="{col}" '
        f'font-family="Consolas,Menlo,monospace" font-size="12" letter-spacing="3" '
        f'filter="url(#glow)" opacity="0">{msg}'
        f'<animate attributeName="opacity" dur="{fmt(D)}s" repeatCount="indefinite" '
        f'values="0;0;1;1;0;0" keyTimes="0;{k(t_play + 0.3)};{k(t_play + 0.6)};{k(t_fade0)};{k(t_fade1)};1"/>'
        "</text>")
    out.append("</svg>")
    return "\n".join(out), steps, D


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("user")
    ap.add_argument("out")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--demo", action="store_true", help="use random data instead of fetching")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    grid = demo_levels(rng) if args.demo else fetch_levels(args.user)
    for _ in range(50):
        bikes = simulate(len(grid), 7, rng)
        if len(bikes[0]["path"]) - 1 >= MIN_STEPS:
            break
    svg, steps, D = render(args.user, grid, bikes)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(svg)
    result = ["crashed" if b["crashed"] else "survived" for b in bikes]
    print(f"{args.out}: {steps} steps, loop {D:.1f}s, {len(svg) // 1024} KB, cyan {result[0]}, orange {result[1]}")


if __name__ == "__main__":
    main()
