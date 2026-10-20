#!/usr/bin/env python3
"""Render every saved race in races.json; the active one becomes tron-lightcycles.svg.

    python render.py <github-user> <out-dir>
"""
import json
import os
import random
import shutil
import sys

import tron
import tron_teams


def build(user, grid, race):
    rng = random.Random(race["seed"])
    if race["mode"] == "duel":
        for _ in range(50):
            bikes = tron.simulate(len(grid), 7, rng)
            if len(bikes[0]["path"]) - 1 >= tron.MIN_STEPS:
                break
        return tron.render(user, grid, bikes)[0]
    teamwork = race.get("teamwork", False)
    for _ in range(100):
        bikes = tron_teams.simulate(len(grid), 7, rng, race["team_size"], teamwork)
        if max(len(b["path"]) for b in bikes) - 1 >= race.get("min_steps", 45):
            break
    return tron_teams.render(user, grid, bikes, " // SQUADS" if teamwork else "")[0]


def main():
    user, out = sys.argv[1], sys.argv[2]
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "races.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    grid = tron.fetch_levels(user)
    os.makedirs(os.path.join(out, "races"), exist_ok=True)
    for name, race in cfg["races"].items():
        path = os.path.join(out, "races", f"{name}.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(build(user, grid, race))
        print(f"rendered {path}")
    shutil.copy(os.path.join(out, "races", f"{cfg['active']}.svg"), os.path.join(out, "tron-lightcycles.svg"))
    print(f"active: {cfg['active']}")


if __name__ == "__main__":
    main()
