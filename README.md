# Hanoi Crossing

A two-player Tower of Hanoi variant with a shared middle pole.

## Rules

Two players (A and B) each have three poles arranged around a central shared
pole (pole 2):

```
        1a
        |
 1b -- [2] -- 3b
        |
        3a
```

- Player A sees poles **1a, 2, 3a**. Player B sees poles **1b, 2, 3b**.
- A starts with odd-sized disks (1, 3, 5, …) stacked on pole 1 (largest at bottom).
- B starts with even-sized disks (2, 4, 6, …) stacked on pole 1.
- Standard Hanoi rule: a disk may only be placed on an empty pole or on a strictly larger disk.
- Each turn a player does exactly one of: **Lift** the top disk from any visible pole into their hand, **Place** the held disk onto any visible pole, or **Skip**.
- A player holds at most one disk at a time. Either player may lift from the shared pole.
- An illegal action wastes the turn; the game state is unchanged.
- **Win**: hand empty and, among the player's visible poles, only pole 3 has disks.

## Installation

```bash
uv sync
```

## Usage

### Replay mode

Reads a pre-recorded move file and prints the final state.

```bash
uv run hanoi-replay <n> <replay-file>
```

**Example** (N=1, from the spec):

```bash
uv run hanoi-replay 1 examples/n1_a_wins.txt
```

### Random-play mode

Both players choose uniformly at random from their legal actions each turn.

```bash
uv run hanoi-random <n> [--max-turns N] [--seed S] [--turns A,B,...] [--quiet]
```

**Examples:**

```bash
uv run hanoi-random 2 --seed 42 --quiet   # reproducible, suppress per-step log
uv run hanoi-random 3 --turns A,A,B       # A gets two turns for every one of B's
```

## Replay file format

Lines starting with `#` and blank lines are ignored.

```
# First non-comment line: declare the turn order.
turns: A B A

# One action per line, in the same order as the turn list.
# Syntax: <PLAYER> <verb> [<pole>]
# Pole numbers are player-relative: 1 = start pole, 2 = shared, 3 = goal pole.

A lift 1        # A lifts from 1a
B lift 1        # B lifts from 1b
A place 3       # A places onto 3a
```

See `examples/` for complete files.

## Tests

```bash
uv run pytest -v
```

41 tests covering:

- Initial state construction
- Lift / Place / Skip legality (own poles, shared pole, invisible poles, Hanoi rule)
- Illegal actions leave state unchanged (immutability)
- Win-condition detection for A and B
- `valid_actions` enumeration
- Cross-player shared-pole interactions
- Multi-step n=2 win sequence

## Design decisions

### State representation

`GameState` is a **frozen dataclass** with pole stacks stored as **immutable
tuples** (bottom to top). This makes the state hashable and safely shareable;
a single application of an action always produces a new object without
touching the original. Internal pole ids are short strings (`"1a"`, `"2"`,
`"3a"`, `"1b"`, `"3b"`).

### Action types

Actions are frozen dataclasses (`Lift(pole)`, `Place(pole)`, `Skip()`). Using
typed objects instead of strings makes the engine code explicit and keeps
`valid_actions` straightforward to iterate.

### `apply` returns `(state, was_legal)` instead of raising

Frontends need to log illegal moves without crashing. Returning `(state, False)`
lets callers handle them uniformly without try/except.

### Win condition and the shared pole

The win condition is: *hand empty, and among the player's visible poles only
pole 3 has disks*. Because the shared pole (2) is in **both** players' visible
sets, a player can only win if pole 2 is empty. This is a natural consequence
of the rules and adds strategic depth — a player may need to clear the shared
pole (possibly by letting the opponent take disks off it) before winning.

### Win check after every action

Both players are checked for a win after each legal action. The acting player
is checked first so they get credit for moves that simultaneously satisfy both
win conditions (a degenerate edge case for n=1).

### Turn order is fully external

The engine does not track whose turn it is. `apply(state, player, action)`
accepts any player on any call. The caller supplies the turn sequence.

### Random-play turn order

Defaults to strict alternation (A, B, A, B, …) via `itertools.cycle`. Any
custom sequence can be supplied with `--turns`, and it is also cycled.

## AI disclosure

This project was built with the assistance of **Claude Sonnet 4.6** via the
Claude Code CLI. The AI was used for:

- Generating the initial implementation plan and architecture
- Writing all source files (engine, CLIs, tests) from the plan
- Debugging the one test assertion error caught by the test run

All code was reviewed and the design decisions are the author's own.
