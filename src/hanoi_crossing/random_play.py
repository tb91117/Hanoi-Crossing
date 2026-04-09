from __future__ import annotations

import argparse
import itertools
import random as _random
import sys

from hanoi_crossing.engine import GameState, apply, initial_state, valid_actions
from hanoi_crossing.replay import LogEntry, _action_str, print_final_state


def run_random(
    n: int,
    max_turns: int = 10_000,
    seed: int | None = None,
    turns: list[str] | None = None,
    quiet: bool = False,
) -> GameState:
    """Run a random game and print the final state.  Returns the final GameState."""
    rng = _random.Random(seed)
    state = initial_state(n)
    turn_cycle = itertools.cycle(turns if turns else ["A", "B"])
    log: list[LogEntry] = []

    for step in range(1, max_turns + 1):
        if state.winner:
            break
        player = next(turn_cycle)
        options = valid_actions(state, player)
        if not options:
            break  # game over, no actions possible
        action = rng.choice(options)
        state, was_legal = apply(state, player, action)
        log.append((step, player, action, was_legal))

        if not quiet:
            tag = "ok  " if was_legal else "ILLEGAL"
            print(f"  {step:4}. {player} {_action_str(action):<20} [{tag}]")

    print_final_state(state, log)
    return state


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="hanoi-random",
        description="Play Hanoi Crossing with random moves",
    )
    parser.add_argument("n", type=int, help="Number of disks per player")
    parser.add_argument(
        "--max-turns", type=int, default=10_000, metavar="N",
        help="Maximum number of turns before stopping (default: 10000)",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="RNG seed for reproducible games",
    )
    parser.add_argument(
        "--turns", type=str, default=None,
        help="Comma-separated turn order, cycled (e.g. A,B,A,B)",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress per-step output",
    )
    args = parser.parse_args()

    turns = args.turns.split(",") if args.turns else None
    if turns:
        for t in turns:
            if t.strip() not in ("A", "B"):
                print(f"Error: unknown player in --turns: {t!r}", file=sys.stderr)
                sys.exit(1)
        turns = [t.strip() for t in turns]

    run_random(n=args.n, max_turns=args.max_turns, seed=args.seed, turns=turns, quiet=args.quiet)
