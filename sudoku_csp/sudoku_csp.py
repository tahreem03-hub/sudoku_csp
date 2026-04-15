"""
Sudoku CSP Solver
=================
Solves Sudoku puzzles using Constraint Satisfaction Problem (CSP) techniques:
  - Backtracking Search
  - Forward Checking (domain pruning after each assignment)
  - AC-3 (Arc Consistency Algorithm 3) as preprocessing

Author: CSP Assignment
"""

import sys
import copy
from collections import deque


# ─────────────────────────────────────────────
# 1. Board Representation & Helpers
# ─────────────────────────────────────────────

def read_board(filename):
    """Read a 9x9 Sudoku board from a text file. 0 = empty cell."""
    board = []
    with open(filename) as f:
        for line in f:
            row = [int(ch) for ch in line.strip() if ch.isdigit()]
            if len(row) == 9:
                board.append(row)
    assert len(board) == 9, f"Expected 9 rows, got {len(board)}"
    return board


def print_board(board):
    """Pretty-print a Sudoku board with box dividers."""
    lines = []
    for i, row in enumerate(board):
        if i % 3 == 0 and i != 0:
            lines.append("------+-------+------")
        cells = []
        for j, val in enumerate(row):
            if j % 3 == 0 and j != 0:
                cells.append("|")
            cells.append(str(val) if val != 0 else ".")
        lines.append(" ".join(cells))
    print("\n".join(lines))


def board_to_domains(board):
    """
    Convert a raw 9x9 board into a CSP domain dict.
    Key: (row, col)  →  Value: set of possible digits {1..9}
    Pre-filled cells get a singleton domain; empty cells get {1..9}.
    """
    domains = {}
    for r in range(9):
        for c in range(9):
            if board[r][c] != 0:
                domains[(r, c)] = {board[r][c]}      # Fixed cell
            else:
                domains[(r, c)] = set(range(1, 10))  # All digits possible
    return domains


# ─────────────────────────────────────────────
# 2. Constraint Definitions
# ─────────────────────────────────────────────

def get_peers(r, c):
    """
    Return the set of all cells that share a row, column, or 3×3 box
    with cell (r, c) — excluding (r, c) itself.
    These are exactly the cells that cannot share the same digit.
    """
    peers = set()

    # Same row
    for cc in range(9):
        if cc != c:
            peers.add((r, cc))

    # Same column
    for rr in range(9):
        if rr != r:
            peers.add((rr, c))

    # Same 3×3 box
    box_r, box_c = 3 * (r // 3), 3 * (c // 3)
    for rr in range(box_r, box_r + 3):
        for cc in range(box_c, box_c + 3):
            if (rr, cc) != (r, c):
                peers.add((rr, cc))

    return peers


# Build a global peer lookup table (computed once for speed)
PEERS = {(r, c): get_peers(r, c) for r in range(9) for c in range(9)}


def get_arcs():
    """
    Return all directed arcs (Xi, Xj) where Xi and Xj are peers.
    Used to initialise the AC-3 queue.
    """
    arcs = []
    for cell, peers in PEERS.items():
        for peer in peers:
            arcs.append((cell, peer))
    return arcs


# ─────────────────────────────────────────────
# 3. AC-3 (Arc Consistency)
# ─────────────────────────────────────────────

def revise(domains, xi, xj):
    """
    Make arc Xi → Xj consistent by removing values from domain(Xi)
    that have no support in domain(Xj).

    For Sudoku the constraint is AllDiff, so a value v in domain(Xi)
    is unsupported only when domain(Xj) = {v} (the single remaining
    value equals v, leaving no other choice for Xj).

    Returns True if domain(Xi) was changed (at least one value removed).
    """
    revised = False
    for v in set(domains[xi]):           # iterate over a copy
        # v is unsupported if every value in Xj's domain equals v
        if domains[xj] == {v}:
            domains[xi].discard(v)
            revised = True
    return revised


def ac3(domains):
    """
    Run AC-3 on the given domains dict (modified in place).

    Returns False if any domain becomes empty (problem is unsolvable
    from this state), True otherwise.
    """
    queue = deque(get_arcs())

    while queue:
        xi, xj = queue.popleft()
        if revise(domains, xi, xj):
            if len(domains[xi]) == 0:
                return False            # Contradiction — prune this branch
            # Domain of Xi shrank: re-check all arcs pointing INTO Xi
            for xk in PEERS[xi]:
                if xk != xj:
                    queue.append((xk, xi))

    return True


# ─────────────────────────────────────────────
# 4. Backtracking Search with Forward Checking
# ─────────────────────────────────────────────

# Global counters (reset per puzzle)
backtrack_calls = 0
backtrack_failures = 0


def select_unassigned_variable(domains):
    """
    Minimum Remaining Values (MRV) heuristic:
    Choose the unassigned variable with the smallest domain.
    Ties are broken by the Degree heuristic (most peers).
    """
    unassigned = [cell for cell, dom in domains.items() if len(dom) > 1]
    # Also include cells that are technically "assigned" by AC-3 propagation
    # A cell is unassigned if it has more than one possible value
    if not unassigned:
        return None
    return min(unassigned, key=lambda cell: (len(domains[cell]), -len(PEERS[cell])))


def is_complete(domains):
    """Assignment is complete when every cell has exactly one value in its domain."""
    return all(len(dom) == 1 for dom in domains.values())


def forward_check(domains, cell, value):
    """
    After assigning `value` to `cell`, assign it and then run AC-3 to
    propagate all consequences (not just immediate peers).

    Running AC-3 handles chains of forced assignments: when removing a
    value from a peer's domain reduces it to a singleton, that in turn
    must be propagated to *its* peers, and so on.

    Returns a new domains dict with the assignment + full propagation
    applied, or None if a contradiction is detected.
    """
    new_domains = {k: set(v) for k, v in domains.items()}
    new_domains[cell] = {value}

    # Remove value from each peer immediately (seed the propagation)
    for peer in PEERS[cell]:
        new_domains[peer].discard(value)
        if len(new_domains[peer]) == 0:
            return None     # Contradiction before AC-3

    # Run AC-3 to propagate any newly forced singletons throughout the grid
    if not ac3(new_domains):
        return None         # AC-3 detected a contradiction

    return new_domains


def backtrack(domains):
    """
    Recursive backtracking search.

    - Selects the next unassigned variable (MRV heuristic).
    - Tries each value in its domain (Least Constraining Value ordering
      is approximated by iterating sorted values for determinism).
    - After each assignment, runs forward checking to prune peer domains.
    - Returns the solved domains dict, or None on failure.
    """
    global backtrack_calls, backtrack_failures
    backtrack_calls += 1

    # Base case: all cells assigned
    if is_complete(domains):
        return domains

    # Choose the most constrained unassigned variable
    cell = select_unassigned_variable(domains)
    if cell is None:
        # Shouldn't happen if is_complete is correct, but guard anyway
        return domains

    for value in sorted(domains[cell]):  # Try each candidate value
        new_domains = forward_check(domains, cell, value)
        if new_domains is None:
            continue        # Forward check failed — skip this value

        result = backtrack(new_domains)
        if result is not None:
            return result   # Solution found

    # No value worked — backtrack
    backtrack_failures += 1
    return None


# ─────────────────────────────────────────────
# 5. Main Solver Entry Point
# ─────────────────────────────────────────────

def solve(filename):
    """
    Full pipeline:
      1. Read board
      2. Convert to CSP domains
      3. Run AC-3 for initial propagation
      4. Run backtracking search
      5. Return solution board and statistics
    """
    global backtrack_calls, backtrack_failures
    backtrack_calls = 0
    backtrack_failures = 0

    board = read_board(filename)
    domains = board_to_domains(board)

    # AC-3 preprocessing: enforce arc consistency before search begins
    if not ac3(domains):
        print(f"AC-3 found no solution for {filename}")
        return None, 0, 0

    # Backtracking search with forward checking
    result = backtrack(domains)

    if result is None:
        print(f"No solution found for {filename}")
        return None, backtrack_calls, backtrack_failures

    # Convert domain dict back to a 9x9 board
    solution = [[list(result[(r, c)])[0] for c in range(9)] for r in range(9)]
    return solution, backtrack_calls, backtrack_failures


def validate_solution(board):
    """Verify every row, column, and box contains digits 1–9 exactly once."""
    digits = set(range(1, 10))

    # Rows
    for r in range(9):
        if set(board[r]) != digits:
            return False

    # Columns
    for c in range(9):
        if {board[r][c] for r in range(9)} != digits:
            return False

    # 3×3 boxes
    for br in range(3):
        for bc in range(3):
            box = {board[br*3+r][bc*3+c] for r in range(3) for c in range(3)}
            if box != digits:
                return False

    return True


# ─────────────────────────────────────────────
# 6. Run All Four Boards
# ─────────────────────────────────────────────

if __name__ == "__main__":
    puzzles = [
        ("easy.txt",     "Easy"),
        ("medium.txt",   "Medium"),
        ("hard.txt",     "Hard"),
        ("veryhard.txt", "Very Hard"),
    ]

    for filename, label in puzzles:
        print("=" * 55)
        print(f"  {label} Board  ({filename})")
        print("=" * 55)

        solution, calls, failures = solve(filename)

        if solution:
            print_board(solution)
            valid = validate_solution(solution)
            print(f"\n  Valid solution : {valid}")
        else:
            print("  No solution found.")

        print(f"  BACKTRACK calls   : {calls}")
        print(f"  BACKTRACK failures: {failures}")
        print()
