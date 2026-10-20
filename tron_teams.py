#!/usr/bin/env python3
"""Team Tron lightcycles (NvN) on the contribution grid -> animated SVG.

    python tron_teams.py <github-user> <out.svg> [--team-size 3] [--seed N]
"""
import argparse
import random
from collections import deque

from tron import (BG, CELL, DIRS, DT, LEVELS, PAD_X, STEP, fetch_levels,
                  fmt, path_d, vx, vy)

PAD_TOP, PAD_BOT = 34, 16
TEAMS = [
    {"name": "CYAN", "colors": ["#00eaff", "#4f8dff", "#5fffc8"]},
    {"name": "ORANGE", "colors": ["#ff8c1a", "#ff4040", "#ffd23d"]},
]


def mix(a, b, t):
    pa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    pb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(pa, pb))


def simulate(W, H, rng, size, teamwork=False):
    occupied = set()
    bikes = []
    rows_a = [round(H * (i + 0.5) / size) for i in range(size)]
    rows_b = [min(H, r + 1) for r in rows_a]
    for team, (x, d, rows) in enumerate([(0, 0, rows_a), (W, 2, rows_b)]):
        for i, y in enumerate(rows):
            bikes.append({"team": team, "color": TEAMS[team]["colors"][i % 3], "pos": (x, y),
                          "dir": d, "path": [(x, y)], "crashed": False})
            occupied.add((x, y))

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

    def alive(team=None):
        return [b for b in bikes if not b["crashed"] and (team is None or b["team"] == team)]

    while alive(0) and alive(1):
        moves = {}
        for b in alive():
            enemies = alive(1 - b["team"])
            danger = {(e["pos"][0] + dx, e["pos"][1] + dy) for e in enemies for dx, dy in DIRS}
            options = []
            for turn in (0, 1, -1):
                d = (b["dir"] + turn) % 4
                n = (b["pos"][0] + DIRS[d][0], b["pos"][1] + DIRS[d][1])
                if inside(n) and n not in occupied:
                    options.append((area(n, danger), turn, d, n))
            if not options:
                d = b["dir"]
                moves[id(b)] = (d, (b["pos"][0] + DIRS[d][0], b["pos"][1] + DIRS[d][1]))
                continue
            best = max(o[0] for o in options)
            good = [o for o in options if o[0] >= best * 0.97]
            straight = [o for o in good if o[1] == 0]
            dist = lambda p, q: abs(p[0] - q[0]) + abs(p[1] - q[1])  # noqa: E731
            closest = min(enemies, key=lambda e: dist(e["pos"], b["pos"]))
            target = closest["pos"]
            toward = lambda t: min(good, key=lambda o: dist(o[3], t))  # noqa: E731
            mates = [m for m in alive(b["team"]) if m is not b]
            leader = alive(b["team"])[0]
            roll = rng.random()
            pick = None
            if teamwork and dist(target, b["pos"]) > 14:
                # Formation: the wingman copies the leader's heading.
                if b is not leader and id(leader) in moves:
                    same = [o for o in good if o[2] == moves[id(leader)][0]]
                    if same:
                        pick = same[0]
                elif roll < 0.25:
                    pick = toward(target)
            elif teamwork and roll < 0.65:
                ex, ey = DIRS[closest["dir"]]
                if b is leader or not mates:
                    # Cut-off: race for the spot just ahead of the enemy.
                    pick = toward((target[0] + 5 * ex, target[1] + 5 * ey))
                else:
                    # Pincer: close in on the flank away from the leader.
                    flanks = [(target[0] - 3 * ey, target[1] + 3 * ex), (target[0] + 3 * ey, target[1] - 3 * ex)]
                    pick = toward(max(flanks, key=lambda f: dist(f, leader["pos"])))
            elif not teamwork and roll < 0.35:
                pick = toward(target)     # hunt the nearest enemy
            if pick is None:
                if straight and rng.random() < 0.75:
                    pick = straight[0]
                else:
                    pick = rng.choice(good)
            moves[id(b)] = (pick[2], pick[3])

        live = alive()
        targets = [moves[id(b)][1] for b in live]
        for b, t in zip(live, targets):
            if not inside(t) or t in occupied or targets.count(t) > 1:
                b["crashed"] = True
                b["crash_at"] = t
        for b in live:
            if not b["crashed"]:
                b["dir"], b["pos"] = moves[id(b)]
                b["path"].append(b["pos"])
                occupied.add(b["pos"])
    return bikes


def render(user, grid, bikes, tag=""):
    W, H = len(grid), 7
    end = max(len(b["path"]) - 1 for b in bikes)
    t_play = end * DT
    t_boom = t_play + 0.7
    t_fade0 = t_boom + 1.8
    t_fade1 = t_fade0 + 0.9
    D = t_fade1 + 0.5
    k = lambda t: fmt(min(max(t / D, 0), 1))  # noqa: E731
    anim = f'dur="{fmt(D)}s" repeatCount="indefinite"'

    width = PAD_X * 2 + W * STEP - 3
    height = PAD_TOP + H * STEP - 3 + PAD_BOT
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<defs><filter id="glow" x="-50%" y="-50%" width="200%" height="200%">'
        '<feGaussianBlur stdDeviation="2.2" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>'
        "</filter></defs>",
        f'<rect width="{width}" height="{height}" rx="10" fill="{BG}"/>',
        f'<text x="{PAD_X}" y="21" fill="#5ff2ff" font-family="Consolas,Menlo,monospace" '
        f'font-size="12" letter-spacing="3" filter="url(#glow)">{user.upper()} // THE GRID // '
        f'{len(bikes) // 2}V{len(bikes) // 2}{tag}</text>',
    ]

    lit = {}
    for bi, b in enumerate(bikes):
        p = b["path"]
        for s, (a, c) in enumerate(zip(p, p[1:]), start=1):
            if a[1] == c[1]:
                x = min(a[0], c[0])
                touched = [(x, a[1] - 1), (x, a[1])]
            else:
                y = min(a[1], c[1])
                touched = [(a[0] - 1, y), (a[0], y)]
            for cell in touched:
                if cell not in lit or lit[cell][0] > s:
                    lit[cell] = (s, bi)

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
                on = mix(BG, bikes[bi]["color"], 0.18 + 0.17 * lv)
                t0 = s * DT
                out.append(
                    rect + f'><animate attributeName="fill" {anim} '
                    f'values="{base};{base};{on};{on};{base};{base}" '
                    f'keyTimes="0;{k(t0)};{k(t0 + 0.25)};{k(t_fade0)};{k(t_fade1)};1"/></rect>')
            else:
                out.append(rect + "/>")
    out.append("</g>")

    out.append(f'<g><animate attributeName="opacity" {anim} values="1;1;0;0" '
               f'keyTimes="0;{k(t_fade0)};{k(t_fade1)};1"/>')
    for b in bikes:
        color = b["color"]
        steps = len(b["path"]) - 1
        t_end = steps * DT
        if steps == 0:
            d = f"M{vx(b['path'][0][0]):.1f} {vy(b['path'][0][1]):.1f} l0.01 0"
        else:
            d = path_d(b["path"])
        length = max(steps * STEP, 0.01)
        out.append(
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2.4" stroke-linejoin="round" '
            f'stroke-linecap="round" filter="url(#glow)" stroke-dasharray="{fmt(length)} {fmt(length + 10)}">'
            f'<animate attributeName="stroke-dashoffset" {anim} '
            f'values="{fmt(length)};0;0" keyTimes="0;{k(t_end)};1"/></path>')
        hide = ""
        if b["crashed"]:
            hide = (f'<animate attributeName="opacity" {anim} values="1;1;0;0" '
                    f'keyTimes="0;{k(t_end)};{k(t_end + 0.05)};1" calcMode="discrete"/>')
        out.append(
            f'<g filter="url(#glow)">{hide}'
            f'<rect x="-7" y="-2.6" width="11" height="5.2" rx="2.6" fill="{color}"/>'
            f'<rect x="-2" y="-1.3" width="6" height="2.6" rx="1.3" fill="#ffffff"/>'
            f'<animateMotion {anim} rotate="auto" path="{d}" keyPoints="0;1;1" '
            f'keyTimes="0;{k(t_end)};1" calcMode="linear"/></g>')
        if b["crashed"]:
            last, hit = b["path"][-1], b["crash_at"]
            cx = (vx(last[0]) + vx(hit[0])) / 2
            cy = (vy(last[1]) + vy(hit[1])) / 2
            kt = f'keyTimes="0;{k(t_end)};{k(t_end + 0.15)};{k(t_end + 0.7)};1"'
            out.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="0" fill="none" stroke="{color}" '
                f'stroke-width="2" filter="url(#glow)" opacity="0">'
                f'<animate attributeName="r" {anim} values="0;0;8;22;22" {kt}/>'
                f'<animate attributeName="opacity" {anim} values="0;0;1;0;0" {kt}/></circle>')
            rng = random.Random(len(b["path"]) * 31 + int(cx))
            for j in range(10):
                ang = j * 36 + rng.uniform(-12, 12)
                dist = rng.uniform(14, 30)
                out.append(
                    f'<g transform="translate({cx:.1f} {cy:.1f}) rotate({ang:.0f})">'
                    f'<rect x="0" y="-0.8" width="3" height="1.6" fill="{color}" filter="url(#glow)" opacity="0">'
                    f'<animate attributeName="x" {anim} values="0;0;{dist * 0.5:.1f};{dist:.1f};{dist:.1f}" {kt}/>'
                    f'<animate attributeName="opacity" {anim} values="0;0;1;0;0" {kt}/></rect></g>')
    out.append("</g>")

    alive_teams = {b["team"] for b in bikes if not b["crashed"]}
    if not alive_teams:
        msg, col = "TOTAL DEREZZ", "#ffffff"
    else:
        win = alive_teams.pop()
        msg, col = f"{TEAMS[win]['name']} TEAM WINS // END OF LINE", TEAMS[win]["colors"][0]
    out.append(
        f'<text x="{width - PAD_X}" y="21" text-anchor="end" fill="{col}" '
        f'font-family="Consolas,Menlo,monospace" font-size="12" letter-spacing="3" '
        f'filter="url(#glow)" opacity="0">{msg}'
        f'<animate attributeName="opacity" {anim} values="0;0;1;1;0;0" '
        f'keyTimes="0;{k(t_play + 0.3)};{k(t_play + 0.6)};{k(t_fade0)};{k(t_fade1)};1"/></text>')
    out.append("</svg>")
    return "\n".join(out), end, D, msg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("user")
    ap.add_argument("out")
    ap.add_argument("--team-size", type=int, default=3)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--min-steps", type=int, default=45)
    ap.add_argument("--teamwork", action="store_true")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    grid = fetch_levels(args.user)
    for _ in range(100):
        bikes = simulate(len(grid), 7, rng, args.team_size, args.teamwork)
        if max(len(b["path"]) for b in bikes) - 1 >= args.min_steps:
            break
    svg, steps, D, msg = render(args.user, grid, bikes, " // SQUADS" if args.teamwork else "")
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"{args.out}: {steps} steps, loop {D:.1f}s, {len(svg) // 1024} KB, {msg}")


if __name__ == "__main__":
    main()
