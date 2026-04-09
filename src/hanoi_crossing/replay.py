from __future__ import annotations

import sys
from pathlib import Path

from hanoi_crossing.engine import (
    Action,
    GameState,
    Lift,
    Place,
    Skip,
    VISIBLE,
    apply,
    initial_state,
)

# Player-relative pole number → internal pole id.
_POLE_MAP: dict[str, dict[int, str]] = {
    "A": {1: "1a", 2: "2", 3: "3a"},
    "B": {1: "1b", 2: "2", 3: "3b"},
}


def _resolve_pole(player: str, pole_num: int) -> str:
    mapping = _POLE_MAP.get(player)
    if mapping is None:
        raise ValueError(f"Unknown player '{player}'")
    pole_id = mapping.get(pole_num)
    if pole_id is None:
        raise ValueError(f"Invalid pole number {pole_num} for player {player}")
    return pole_id


def parse_replay_file(path: str) -> tuple[list[str], list[tuple[str, Action]]]:
    """Parse a replay file.

    Returns
    -------
    (turn_order, moves)
        turn_order : list of player ids, one per step.
        moves      : list of (player, Action) pairs, same length as turn_order.
    """
    raw_lines = Path(path).read_text(encoding="utf-8").splitlines()
    lines = [ln.strip() for ln in raw_lines if ln.strip() and not ln.strip().startswith("#")]

    if not lines:
        raise ValueError("Replay file is empty")

    # First line must be the turn order.
    first = lines[0]
    if not first.lower().startswith("turns:"):
        raise ValueError(f"First non-comment line must start with 'turns:', got: {first!r}")
    turn_order = first.split(":", 1)[1].split()
    for t in turn_order:
        if t not in ("A", "B"):
            raise ValueError(f"Unknown player in turn order: {t!r}")

    move_lines = lines[1:]
    if len(move_lines) != len(turn_order):
        raise ValueError(
            f"Turn order has {len(turn_order)} entries but {len(move_lines)} action lines found"
        )

    moves: list[tuple[str, Action]] = []
    for i, (player, line) in enumerate(zip(turn_order, move_lines)):
        parts = line.split()
        if len(parts) < 2:
            raise ValueError(f"Line {i + 2}: too few tokens: {line!r}")
        file_player, verb, *rest = parts
        if file_player != player:
            raise ValueError(
                f"Line {i + 2}: expected player {player!r} but got {file_player!r}"
            )
        verb = verb.lower()
        if verb == "skip":
            moves.append((player, Skip()))
        elif verb == "lift":
            if not rest:
                raise ValueError(f"Line {i + 2}: 'lift' requires a pole number")
            pole_id = _resolve_pole(player, int(rest[0]))
            moves.append((player, Lift(pole_id)))
        elif verb == "place":
            if not rest:
                raise ValueError(f"Line {i + 2}: 'place' requires a pole number")
            pole_id = _resolve_pole(player, int(rest[0]))
            moves.append((player, Place(pole_id)))
        else:
            raise ValueError(f"Line {i + 2}: unknown action {verb!r}")

    return turn_order, moves


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

LogEntry = tuple[int, str, Action, bool]  # (step, player, action, was_legal)


def _action_str(action: Action) -> str:
    if isinstance(action, Skip):
        return "skip"
    if isinstance(action, Lift):
        return f"lift {action.pole}"
    if isinstance(action, Place):
        return f"place {action.pole}"
    return str(action)


def print_final_state(state: GameState, log: list[LogEntry]) -> None:
    print("=" * 40)
    print("FINAL STATE")
    print("=" * 40)

    print("\nPoles (bottom to top):")
    for pole_id in ("1a", "2", "3a", "1b", "3b"):
        label = f"  {pole_id}"
        disks = list(state.poles[pole_id])
        print(f"{label:6}: {disks}")

    print("\nHands:")
    for p in ("A", "B"):
        h = state.hands[p]
        print(f"  {p}: {h if h is not None else '-'}")

    if state.winner:
        print(f"\nWinner: {state.winner}")
    else:
        print("\nNo winner yet")

    print(f"\nMove log ({len(log)} turns):")
    for step, player, action, legal in log:
        tag = "ok  " if legal else "ILLEGAL"
        print(f"  {step:3}. {player} {_action_str(action):<20} [{tag}]")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_replay(n: int, path: str) -> GameState:
    """Execute a replay and print the final state.  Returns the final GameState."""
    turn_order, moves = parse_replay_file(path)
    state = initial_state(n)
    log: list[LogEntry] = []

    for step, (player, action) in enumerate(moves, start=1):
        state, was_legal = apply(state, player, action)
        log.append((step, player, action, was_legal))
        if state.winner:
            break  # stop processing once someone has won

    print_final_state(state, log)
    return state


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: hanoi-replay <n> <replay-file>", file=sys.stderr)
        sys.exit(1)

    try:
        n = int(sys.argv[1])
    except ValueError:
        print(f"Error: n must be an integer, got {sys.argv[1]!r}", file=sys.stderr)
        sys.exit(1)

    run_replay(n, sys.argv[2])
