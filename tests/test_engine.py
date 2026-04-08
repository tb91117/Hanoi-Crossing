"""Tests for the Hanoi Crossing engine.

All tests exercise the engine directly (no CLI).
"""

import pytest

from hanoi_crossing.engine import (
    GameState,
    Lift,
    Place,
    Skip,
    apply,
    initial_state,
    valid_actions,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def poles(state: GameState) -> dict[str, tuple[int, ...]]:
    return state.poles

def hand(state: GameState, player: str) -> int | None:
    return state.hands[player]


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------

class TestInitialState:
    def test_n1_pole_contents(self):
        s = initial_state(1)
        assert s.poles["1a"] == (1,)
        assert s.poles["1b"] == (2,)
        assert s.poles["2"] == ()
        assert s.poles["3a"] == ()
        assert s.poles["3b"] == ()

    def test_n1_hands_empty(self):
        s = initial_state(1)
        assert s.hands["A"] is None
        assert s.hands["B"] is None

    def test_n1_no_winner(self):
        assert initial_state(1).winner is None

    def test_n3_a_disks(self):
        s = initial_state(3)
        # A gets odd disks 1,3,5 — largest at bottom → (5, 3, 1)
        assert s.poles["1a"] == (5, 3, 1)

    def test_n3_b_disks(self):
        s = initial_state(3)
        # B gets even disks 2,4,6 — largest at bottom → (6, 4, 2)
        assert s.poles["1b"] == (6, 4, 2)

    def test_n_must_be_positive(self):
        with pytest.raises(ValueError):
            initial_state(0)


# ---------------------------------------------------------------------------
# Lift
# ---------------------------------------------------------------------------

class TestLift:
    def test_lift_own_pole(self):
        # n=2 → A's pole 1a = (3, 1); top disk is 1.
        s = initial_state(2)
        ns, legal = apply(s, "A", Lift("1a"))
        assert legal
        assert ns.hands["A"] == 1
        assert ns.poles["1a"] == (3,)

    def test_lift_shared_pole_by_a(self):
        s = initial_state(1)
        # First, place a disk on the shared pole manually by applying actions.
        s, _ = apply(s, "A", Lift("1a"))   # A picks up disk 1
        s, _ = apply(s, "A", Place("2"))   # A puts it on shared pole
        assert s.poles["2"] == (1,)
        ns, legal = apply(s, "A", Lift("2"))
        assert legal
        assert ns.hands["A"] == 1

    def test_lift_shared_pole_by_b(self):
        s = initial_state(1)
        s, _ = apply(s, "A", Lift("1a"))
        s, _ = apply(s, "A", Place("2"))
        ns, legal = apply(s, "B", Lift("2"))
        assert legal
        assert ns.hands["B"] == 1

    def test_lift_invisible_pole_a_cannot_see_1b(self):
        s = initial_state(1)
        ns, legal = apply(s, "A", Lift("1b"))
        assert not legal
        assert ns is s  # same object returned

    def test_lift_invisible_pole_b_cannot_see_3a(self):
        s = initial_state(1)
        ns, legal = apply(s, "B", Lift("3a"))
        assert not legal

    def test_lift_already_holding(self):
        s = initial_state(2)
        s, _ = apply(s, "A", Lift("1a"))  # A now holds disk 1
        ns, legal = apply(s, "A", Lift("1a"))  # try to lift again
        assert not legal

    def test_lift_empty_pole(self):
        s = initial_state(1)
        ns, legal = apply(s, "A", Lift("3a"))  # 3a is empty at start
        assert not legal

    def test_lift_removes_top_disk(self):
        s = initial_state(3)  # pole 1a = (5, 3, 1)
        ns, _ = apply(s, "A", Lift("1a"))
        assert ns.poles["1a"] == (5, 3)
        assert ns.hands["A"] == 1


# ---------------------------------------------------------------------------
# Place
# ---------------------------------------------------------------------------

class TestPlace:
    def test_place_on_empty_pole(self):
        s = initial_state(1)
        s, _ = apply(s, "A", Lift("1a"))
        ns, legal = apply(s, "A", Place("3a"))
        assert legal
        assert ns.poles["3a"] == (1,)
        assert ns.hands["A"] is None

    def test_place_smaller_on_larger(self):
        s = initial_state(2)           # 1a=(3,1), 1b=(4,2)
        s, _ = apply(s, "B", Lift("1b"))  # B picks up disk 2
        s, _ = apply(s, "A", Lift("1a"))  # A picks up disk 1; 1a=(3,)
        # A places disk 1 on top of disk 3 → legal
        ns, legal = apply(s, "A", Place("1a"))
        assert legal

    def test_place_larger_on_smaller_illegal(self):
        s = initial_state(2)
        # Put disk 1 on shared pole first, then try to put disk 3 on it.
        s, _ = apply(s, "A", Lift("1a"))   # picks up 1
        s, _ = apply(s, "A", Place("2"))   # 2 has disk 1
        s, _ = apply(s, "A", Lift("1a"))   # picks up 3
        ns, legal = apply(s, "A", Place("2"))  # try to put 3 on top of 1
        assert not legal

    def test_place_no_disk_in_hand(self):
        s = initial_state(1)
        ns, legal = apply(s, "A", Place("3a"))
        assert not legal

    def test_place_on_invisible_pole(self):
        s = initial_state(1)
        s, _ = apply(s, "A", Lift("1a"))
        ns, legal = apply(s, "A", Place("3b"))  # 3b not visible to A
        assert not legal

    def test_place_on_shared_pole(self):
        s = initial_state(1)
        s, _ = apply(s, "A", Lift("1a"))
        ns, legal = apply(s, "A", Place("2"))
        assert legal
        assert ns.poles["2"] == (1,)


# ---------------------------------------------------------------------------
# Skip
# ---------------------------------------------------------------------------

class TestSkip:
    def test_skip_always_legal(self):
        s = initial_state(2)
        ns, legal = apply(s, "A", Skip())
        assert legal

    def test_skip_leaves_state_unchanged(self):
        s = initial_state(2)
        ns, _ = apply(s, "A", Skip())
        assert ns == s

    def test_skip_when_holding(self):
        s = initial_state(1)
        s, _ = apply(s, "A", Lift("1a"))
        ns, legal = apply(s, "A", Skip())
        assert legal
        assert ns.hands["A"] == 1


# ---------------------------------------------------------------------------
# Illegal action has no effect
# ---------------------------------------------------------------------------

class TestIllegalActionImmutability:
    def test_illegal_action_returns_same_state(self):
        s = initial_state(2)
        ns, legal = apply(s, "A", Lift("1b"))  # invisible
        assert not legal
        assert ns == s

    def test_original_state_not_modified_after_legal_action(self):
        s = initial_state(2)
        original_poles = dict(s.poles)
        ns, _ = apply(s, "A", Lift("1a"))
        # s should be untouched
        assert s.poles == original_poles
        # ns is different
        assert ns.poles != s.poles


# ---------------------------------------------------------------------------
# Win condition
# ---------------------------------------------------------------------------

class TestWinCondition:
    def test_spec_example_n1_a_wins(self):
        """Reproduce the N=1 example from the spec."""
        s = initial_state(1)
        s, _ = apply(s, "A", Lift("1a"))   # step 1: A lifts disk 1
        s, _ = apply(s, "B", Lift("1b"))   # step 2: B lifts disk 2
        s, _ = apply(s, "A", Place("3a"))  # step 3: A places disk 1 on 3a
        assert s.winner == "A"

    def test_b_wins(self):
        s = initial_state(1)
        s, _ = apply(s, "B", Lift("1b"))
        s, _ = apply(s, "B", Place("3b"))
        assert s.winner == "B"

    def test_no_win_disk_in_hand(self):
        s = initial_state(1)
        s, _ = apply(s, "A", Lift("1a"))  # A holds disk 1, 1a empty, 2 empty, 3a empty
        assert s.winner is None  # can't win while holding

    def test_no_win_disk_on_start_pole(self):
        s = initial_state(2)
        # Move only the top disk (1) to 3a; disk 3 is still on 1a.
        s, _ = apply(s, "A", Lift("1a"))   # picks up 1
        s, _ = apply(s, "A", Place("3a"))  # puts 1 on 3a
        assert s.winner is None  # disk 3 still on 1a

    def test_no_win_disk_on_shared_pole(self):
        s = initial_state(1)
        s, _ = apply(s, "A", Lift("1a"))
        s, _ = apply(s, "A", Place("2"))   # disk on shared pole
        # Now A's hand is empty, 1a is empty, but 2 is not empty → no win
        assert s.winner is None

    def test_b_wins_does_not_require_a_poles_empty(self):
        s = initial_state(1)
        # B can win independently of A's private poles.
        s, _ = apply(s, "B", Lift("1b"))
        s, _ = apply(s, "B", Place("3b"))
        assert s.winner == "B"
        # A's disk is still on 1a.
        assert s.poles["1a"] == (1,)

    def test_no_actions_after_win(self):
        s = initial_state(1)
        s, _ = apply(s, "B", Lift("1b"))
        s, _ = apply(s, "B", Place("3b"))
        assert s.winner == "B"
        # Further actions return (state, False)
        ns, legal = apply(s, "A", Skip())
        assert not legal
        assert ns is s


# ---------------------------------------------------------------------------
# valid_actions
# ---------------------------------------------------------------------------

class TestValidActions:
    def test_includes_skip_always(self):
        s = initial_state(2)
        actions = valid_actions(s, "A")
        assert Skip() in actions

    def test_empty_hand_includes_lifts_no_places(self):
        s = initial_state(2)
        actions = valid_actions(s, "A")
        kinds = {type(a) for a in actions}
        assert Lift in kinds
        assert Place not in kinds

    def test_holding_includes_places_no_lifts(self):
        s = initial_state(2)
        s, _ = apply(s, "A", Lift("1a"))
        actions = valid_actions(s, "A")
        kinds = {type(a) for a in actions}
        assert Place in kinds
        assert Lift not in kinds

    def test_cannot_lift_invisible_poles(self):
        s = initial_state(1)
        actions = valid_actions(s, "A")
        lift_poles = {a.pole for a in actions if isinstance(a, Lift)}
        assert "1b" not in lift_poles
        assert "3b" not in lift_poles

    def test_cannot_place_on_smaller_disk(self):
        s = initial_state(2)
        # Put disk 1 on shared pole.
        s, _ = apply(s, "A", Lift("1a"))  # picks up 1
        s, _ = apply(s, "A", Place("2"))  # 2 has disk 1 on top
        # A picks up disk 3 from 1a.
        s, _ = apply(s, "A", Lift("1a"))
        actions = valid_actions(s, "A")
        place_poles = {a.pole for a in actions if isinstance(a, Place)}
        assert "2" not in place_poles  # can't put 3 on 1

    def test_no_valid_actions_after_win(self):
        s = initial_state(1)
        s, _ = apply(s, "B", Lift("1b"))
        s, _ = apply(s, "B", Place("3b"))
        assert valid_actions(s, "A") == []
        assert valid_actions(s, "B") == []


# ---------------------------------------------------------------------------
# Cross-player shared pole interaction
# ---------------------------------------------------------------------------

class TestSharedPole:
    def test_b_can_lift_disk_a_placed_on_shared(self):
        s = initial_state(1)
        s, _ = apply(s, "A", Lift("1a"))
        s, _ = apply(s, "A", Place("2"))
        ns, legal = apply(s, "B", Lift("2"))
        assert legal
        assert ns.hands["B"] == 1

    def test_a_can_lift_disk_b_placed_on_shared(self):
        s = initial_state(1)
        s, _ = apply(s, "B", Lift("1b"))
        s, _ = apply(s, "B", Place("2"))
        ns, legal = apply(s, "A", Lift("2"))
        assert legal
        assert ns.hands["A"] == 2


# ---------------------------------------------------------------------------
# n=2 multi-step sequence
# ---------------------------------------------------------------------------

class TestN2Sequence:
    def test_a_wins_n2(self):
        """A can win a 2-disk game by moving disks 1 and 3 to pole 3a."""
        s = initial_state(2)
        # Move disk 1 out of the way to the shared pole.
        s, ok = apply(s, "A", Lift("1a"))
        assert ok and s.hands["A"] == 1
        s, ok = apply(s, "A", Place("2"))
        assert ok
        # Move disk 3 to 3a.
        s, ok = apply(s, "A", Lift("1a"))
        assert ok and s.hands["A"] == 3
        s, ok = apply(s, "A", Place("3a"))
        assert ok
        # Move disk 1 from shared pole to 3a on top of disk 3.
        s, ok = apply(s, "A", Lift("2"))
        assert ok and s.hands["A"] == 1
        s, ok = apply(s, "A", Place("3a"))
        assert ok
        assert s.winner == "A"
        assert s.poles["3a"] == (3, 1)
