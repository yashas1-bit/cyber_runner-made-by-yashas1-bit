

import os
import sys
import time
import math
import random
import msvcrt

# CYBER RUNNER
# Windows + standard Python only. No Pygame or Tkinter.

WIDTH = 64
HEIGHT = 22
PLAYER_X = 10
GROUND_Y = HEIGHT - 5
FPS = 30

CYAN = "\033[96m"
PURPLE = "\033[95m"
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
WHITE = "\033[97m"
DIM = "\033[90m"
RESET = "\033[0m"

HIGH_SCORE_FILE = "cyber_runner_highscore.txt"


def load_high_score():
    try:
        with open(HIGH_SCORE_FILE, "r", encoding="utf-8") as f:
            return max(0, int(f.read().strip()))
    except (OSError, ValueError):
        return 0


def save_high_score(score):
    try:
        with open(HIGH_SCORE_FILE, "w", encoding="utf-8") as f:
            f.write(str(score))
    except OSError:
        pass


def read_keys():
    keys = []

    while msvcrt.kbhit():
        key = msvcrt.getch()

        if key in (b"\x00", b"\xe0"):
            if msvcrt.kbhit():
                keys.append(("arrow", msvcrt.getch()))
        else:
            keys.append(("key", key.lower()))

    return keys


def make_game():
    return {
        "objects": [],
        "height": 0.0,
        "jump_velocity": 0.0,
        "grounded": True,
        "distance": 0.0,
        "score": 0,
        "speed": 15.0,
        "spawn_distance": 25.0,
        "alive": True,
        "message": "",
        "shard_flash": 0,
    }


def spawn_object(game):
    objects = game["objects"]

    # Avoid spawning a new hazard too close to another one.
    rightmost = max(
        (o["x"] for o in objects if o["kind"] != "shard"),
        default=-100
    )

    if rightmost > WIDTH - 13:
        return

    choice = random.random()

    if choice < 0.28:
        objects.append({
            "kind": "gap",
            "x": float(WIDTH),
            "width": random.randint(4, 5)
        })
    elif choice < 0.63:
        objects.append({
            "kind": "block",
            "x": float(WIDTH),
            "width": 1
        })
    else:
        # Energy shards reward precise jumps.
        base_x = float(WIDTH)
        for i in range(5):
            objects.append({
                "kind": "shard",
                "x": base_x + i * 2.0,
                "width": 1,
                "height": 2.5
            })


def draw(game, high_score):
    # Build a complete frame in memory, then print it at once.
    grid = [[" " for _ in range(WIDTH)] for _ in range(HEIGHT)]
    colors = {}

    def put(x, y, char, color):
        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
            grid[y][x] = char
            colors[(x, y)] = color

    # Distant skyline.
    random.seed(11)
    for bx in range(0, WIDTH, 7):
        building_height = 3 + (bx * 3 % 6)
        for y in range(GROUND_Y - building_height, GROUND_Y):
            for x in range(bx, min(bx + 5, WIDTH)):
                put(x, y, ".", DIM)

        if bx + 2 < WIDTH:
            put(bx + 2, GROUND_Y - building_height, "^", PURPLE)

    random.seed()

    # Rooftop surface, interrupted by gaps.
    for x in range(WIDTH):
        in_gap = any(
            o["kind"] == "gap"
            and o["x"] <= x < o["x"] + o["width"]
            for o in game["objects"]
        )

        if not in_gap:
            put(x, GROUND_Y, "=", CYAN)
            put(x, GROUND_Y + 1, "#", DIM)
            put(x, GROUND_Y + 2, "#", DIM)

    # Rooftop obstacles and energy shards.
    for obj in game["objects"]:
        x = round(obj["x"])

        if obj["kind"] == "block":
            for yy in range(GROUND_Y - 1, GROUND_Y):
                put(x, yy, "X", RED)

        elif obj["kind"] == "shard":
            sy = GROUND_Y - round(obj["height"])
            put(x, sy, "*", YELLOW)

    # Player. Height is measured upward from the rooftop.
    player_y = GROUND_Y - round(game["height"])
    put(PLAYER_X, player_y - 1, "O", WHITE)
    put(PLAYER_X, player_y, "A", CYAN)
    put(PLAYER_X - 1, player_y, "/", PURPLE)
    put(PLAYER_X + 1, player_y, "\\", PURPLE)

    # HUD.
    header = (
        f" CYBER RUNNER  |  SCORE {game['score']:05d}"
        f"  |  BEST {high_score:05d}"
    )
    header = header[:WIDTH].ljust(WIDTH)
    lines = [CYAN + header + RESET]

    for y, row in enumerate(grid):
        line = ""
        for x, char in enumerate(row):
            color = colors.get((x, y), RESET)
            line += color + char
        lines.append(line + RESET)

    lines.append(
        DIM + " SPACE/W/UP: JUMP   Q: QUIT   "
        "Jump over X and gaps; collect * " + RESET
    )

    if game["message"]:
        lines.append(YELLOW + game["message"] + RESET)

    sys.stdout.write("\033[H" + "\n".join(lines) + "\033[J")
    sys.stdout.flush()


def game_over_screen(score, high_score):
    sys.stdout.write("\033[2J\033[H")
    print(RED + r"""
   ____   _    __  __ _____
  / ___| / \  |  \/  | ____|
 | |  _ / _ \ | |\/| |  _|
 | |_| / ___ \| |  | | |___
  \____/_/   \_\_|  |_|_____|
""" + RESET)
    print()
    print(CYAN + "       C Y B E R   R U N N E R" + RESET)
    print()
    print(f"       Score:      {score}")
    print(f"       Best score: {high_score}")
    print()
    print("       [R] Run again")
    print("       [Q] Quit")
    print()
    sys.stdout.flush()


def play():
    game = make_game()
    high_score = load_high_score()
    last_time = time.monotonic()
    last_draw = 0.0
    game["message"] = "Ready! Jump with SPACE, W, or UP."

    # Give the player time to read the controls.
    start_time = time.monotonic()

    while game["alive"]:
        now = time.monotonic()
        dt = min(now - last_time, 0.05)
        last_time = now

        for kind, key in read_keys():
            if kind == "key":
                if key in (b"q", b"\x1b"):
                    return False

                if key in (b" ", b"w"):
                    if game["grounded"]:
                        game["jump_velocity"] = 13.5
                        game["grounded"] = False

            elif kind == "arrow" and key == b"H":
                if game["grounded"]:
                    game["jump_velocity"] = 13.5
                    game["grounded"] = False

        if now - start_time < 0.8:
            draw(game, high_score)
            time.sleep(0.01)
            continue

        # Physics: gravity and jumping.
        if not game["grounded"]:
            game["height"] += game["jump_velocity"] * dt
            game["jump_velocity"] -= 30.0 * dt

            if game["height"] <= 0:
                game["height"] = 0.0
                game["jump_velocity"] = 0.0
                game["grounded"] = True

        # Progressively increase the running speed.
        game["speed"] = min(28.0, 15.0 + game["distance"] / 100.0)
        game["distance"] += game["speed"] * dt
        game["score"] = int(game["distance"]) + game["shard_flash"]

        # Spawn objects at intervals.
        game["spawn_distance"] -= game["speed"] * dt
        if game["spawn_distance"] <= 0:
            spawn_object(game)
            game["spawn_distance"] = random.uniform(15.0, 23.0)

        # Scroll the world.
        for obj in game["objects"]:
            obj["x"] -= game["speed"] * dt

        # Collect shards and detect collisions.
        for obj in game["objects"][:]:
            x = obj["x"]

            if obj["kind"] == "shard":
                if (
                    abs(x - PLAYER_X) < 1.0
                    and abs(game["height"] - obj["height"]) < 2.0
                ):
                    game["shard_flash"] += 25
                    game["objects"].remove(obj)
                    continue

            elif obj["kind"] == "block":
                if abs(x - PLAYER_X) < 0.65:
                    if game["height"] < 1.5:
                        game["alive"] = False

            elif obj["kind"] == "gap":
                if x <= PLAYER_X < x + obj["width"]:
                    if game["height"] < 1.0:
                        game["alive"] = False

            if obj in game["objects"] and x < -6:
                game["objects"].remove(obj)

        if not game["alive"]:
            break

        if now - last_draw >= 1.0 / FPS:
            draw(game, high_score)
            last_draw = now

        time.sleep(0.005)

    score = game["score"]
    high_score = max(high_score, score)
    save_high_score(high_score)
    game_over_screen(score, high_score)

    while True:
        for kind, key in read_keys():
            if kind == "key":
                if key == b"r":
                    return True
                if key in (b"q", b"\x1b"):
                    return False
        time.sleep(0.03)


def main():
    if os.name != "nt":
        print("This version uses Windows keyboard input (msvcrt).")
        print("Run it on Windows in VS Code.")
        return

    os.system("")
    sys.stdout.write("\033[2J\033[H\033[?25l")
    sys.stdout.flush()

    try:
        while True:
            if not play():
                break
    finally:
        sys.stdout.write("\033[0m\033[?25h\n")
        sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.stdout.write("\033[0m\033[?25h\n")
        print("Game closed.")
