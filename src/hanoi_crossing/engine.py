"""
Hanoi Crossing — core game engine.

Board layout
------------
        1a
        |
 1b -- [2] -- 3b
        |
        3a

Player A sees: 1a – 2 – 3a   (poles numbered 1, 2, 3 from A's perspective)
Player B sees: 1b – 2 – 3b   (poles numbered 1, 2, 3 from B's perspective)

Pole stacks are stored bottom-to-top: index 0 is the largest (bottom) disk,
last element is the smallest (top) disk that can be lifted.

Design decisions
----------------
- GameState is a frozen dataclass; poles are stored as tuples for immutability.
- Actions are plain frozen dataclasses (Lift, Place, Skip).
- `apply` never raises on invalid input; it returns (state, False) so callers
  can log illegal moves without try/except.
- Win check runs after every legal action for BOTH players.  A player's visible
  set includes the shared pole, so pole 2 must be empty for either player to win.
- Turn order is entirely external; the engine does not track whose turn it is.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PLAYERS: tuple[str, str] = ("A", "B")

# Pole ids visible to each player, in order 1 → 2 → 3.
VISIBLE: dict[str, tuple[str, str, str]] = {
    "A": ("1a", "2", "3a"),
    "B": ("1b", "2", "3b"),
}

# The pole a player must fill to win.
WIN_POLE: dict[str, str] = {"A": "3a", "B": "3b"}

# Shared pole id.
SHARED_POLE = "2"

ALL_POLES: tuple[str, ...] = ("1a", "2", "3a", "1b", "3b")

# ---------------------------------------------------------------------------
# Action types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Lift:
    """Lift the top disk from `pole` into the player's hand."""

    pole: str  # internal pole id, e.g. "1a", "2"


@dataclass(frozen=True)
class Place:
    """Place the held disk onto `pole`."""

    pole: str  # internal pole id


@dataclass(frozen=True)
class Skip:
    """Do nothing; pass the turn."""


Action = Lift | Place | Skip


# ---------------------------------------------------------------------------
# Game state
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GameState:
    """Immutable snapshot of the game.

    poles : dict mapping each pole id to a tuple of ints.
            Tuple is ordered bottom-to-top; last element is the top disk.
    hands : dict mapping each player ("A" / "B") to the disk they hold,
            or None if their hand is empty.
    n     : number of disks per player (A has n odd disks, B has n even disks).
    winner: None while the game is in progress; "A" or "B" once decided.
    """

    n: int
    poles: dict[str, tuple[int, ...]]
    hands: dict[str, Optional[int]]
    winner: Optional[str]

    def top(self, pole: str) -> Optional[int]:
        """Return the top disk of *pole*, or None if the pole is empty."""
        stack = self.poles[pole]
        return stack[-1] if stack else None

    def __str__(self) -> str:  # pragma: no cover
        lines = []
        for pole in ALL_POLES:
            lines.append(f"  {pole}: {list(self.poles[pole])}")
        for p in PLAYERS:
            h = self.hands[p]
            lines.append(f"  hand[{p}]: {h if h is not None else '-'}")
        if self.winner:
            lines.append(f"  winner: {self.winner}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def initial_state(n: int) -> GameState:
    """Return the starting state for an n-disk game.

    Player A receives odd disks 1, 3, 5, …, 2n-1 stacked on pole 1a
    (largest at bottom, so stored as (2n-1, …, 3, 1)).
    Player B receives even disks 2, 4, 6, …, 2n stacked on pole 1b.
    """
    if n < 1:
        raise ValueError(f"n must be >= 1, got {n}")

    a_disks: tuple[int, ...] = tuple(range(2 * n - 1, 0, -2))  # (2n-1, …, 1)
    b_disks: tuple[int, ...] = tuple(range(2 * n, 0, -2))       # (2n, …, 2)

    poles: dict[str, tuple[int, ...]] = {
        "1a": a_disks,
        "2":  (),
        "3a": (),
        "1b": b_disks,
        "3b": (),
    }
    hands: dict[str, Optional[int]] = {"A": None, "B": None}
    return GameState(n=n, poles=poles, hands=hands, winner=None)


# ---------------------------------------------------------------------------
# Legality check
# ---------------------------------------------------------------------------


def _can_place(disk: int, top: Optional[int]) -> bool:
    """True if *disk* may be placed on a stack whose current top is *top*."""
    return top is None or disk < top


def _is_legal(state: GameState, player: str, action: Action) -> bool:
    """Return True iff *action* is legal for *player* in *state*."""
    visible = VISIBLE[player]

    if isinstance(action, Skip):
        return True

    if isinstance(action, Lift):
        if action.pole not in visible:
            return False
        if state.hands[player] is not None:
            return False  # already holding a disk
        return state.top(action.pole) is not None  # pole must be non-empty

    if isinstance(action, Place):
        if action.pole not in visible:
            return False
        disk = state.hands[player]
        if disk is None:
            return False  # nothing to place
        return _can_place(disk, state.top(action.pole))

    return False  # unknown action type


# ---------------------------------------------------------------------------
# Win detection
# ---------------------------------------------------------------------------


def _check_winner(
    poles: dict[str, tuple[int, ...]],
    hands: dict[str, Optional[int]],
) -> Optional[str]:
    """Return the winning player if any, else None.

    Check both players so we catch the edge case where one player's action
    clears the shared pole and satisfies the other player's win condition.
    We prefer to report the player who just moved first; caller controls order.
    """
    for player in PLAYERS:
        if hands[player] is not None:
            continue  # can't win while holding a disk
        visible = VISIBLE[player]
        win_pole = WIN_POLE[player]
        # All visible poles except the win pole must be empty.
        if all(not poles[p] for p in visible if p != win_pole):
            return player
    return None


# ---------------------------------------------------------------------------
# State transition
# ---------------------------------------------------------------------------


def apply(state: GameState, player: str, action: Action) -> tuple[GameState, bool]:
    """Apply *action* for *player*.

    Returns
    -------
    (new_state, was_legal)
        If *was_legal* is False the returned state is identical to *state*
        (the turn is wasted; no mutation occurred).
    """
    if state.winner is not None:
        # Game already over; no further actions change the state.
        return state, False

    if not _is_legal(state, player, action):
        return state, False

    # Build mutable copies.
    new_poles: dict[str, list[int]] = {k: list(v) for k, v in state.poles.items()}
    new_hands: dict[str, Optional[int]] = dict(state.hands)

    if isinstance(action, Lift):
        new_hands[player] = new_poles[action.pole].pop()

    elif isinstance(action, Place):
        disk = new_hands[player]
        assert disk is not None
        new_poles[action.pole].append(disk)
        new_hands[player] = None

    # Freeze back to tuples.
    frozen_poles: dict[str, tuple[int, ...]] = {k: tuple(v) for k, v in new_poles.items()}

    # Check win — prefer to credit the acting player first.
    ordered = [player] + [p for p in PLAYERS if p != player]
    winner: Optional[str] = None
    for p in ordered:
        if new_hands[p] is not None:
            continue
        vp = VISIBLE[p]
        wp = WIN_POLE[p]
        if all(not frozen_poles[pole] for pole in vp if pole != wp):
            winner = p
            break

    return (
        GameState(n=state.n, poles=frozen_poles, hands=new_hands, winner=winner),
        True,
    )


# ---------------------------------------------------------------------------
# Valid action enumeration
# ---------------------------------------------------------------------------


def valid_actions(state: GameState, player: str) -> list[Action]:
    """Return every currently legal action for *player*.

    Always includes Skip.  If the player has an empty hand, includes Lift
    actions for every non-empty visible pole.  If the player is holding a
    disk, includes Place actions for every visible pole where placement is
    legal.
    """
    if state.winner is not None:
        return []

    actions: list[Action] = [Skip()]
    visible = VISIBLE[player]

    if state.hands[player] is None:
        for pole in visible:
            if state.poles[pole]:
                actions.append(Lift(pole))
    else:
        disk = state.hands[player]
        assert disk is not None
        for pole in visible:
            if _can_place(disk, state.top(pole)):
                actions.append(Place(pole))

    return actions
