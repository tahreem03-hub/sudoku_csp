# Sudoku CSP Solver — Report

## Implementation Overview

The solver models Sudoku as a **Constraint Satisfaction Problem (CSP)**:

- **Variables**: 81 cells, each identified by `(row, col)`.
- **Domains**: Each cell starts with domain `{1..9}`; pre-filled cells get a singleton domain `{digit}`.
- **Constraints**: All-Different across each row, column, and 3×3 box (enforced via peer arc-consistency).

Three techniques are combined:

| Technique | Role |
|---|---|
| **AC-3** | Preprocessing — prunes domains before search begins |
| **MRV heuristic** | Variable ordering — picks the most-constrained unassigned cell first |
| **Forward Checking + AC-3** | After each assignment, fully propagates constraints (AC-3 re-run) |
| **Backtracking** | Systematic search with undo on failure |

---

## Solutions

### Board 1 — Easy (`easy.txt`)

**Input:**
```
. . 4 | . 3 . | . 5 .
6 . 9 | 4 . . | . . .
. . 5 | 1 . . | 4 8 9
------+-------+------
. . . | . 6 . | 9 3 .
3 . . | 8 . 7 | . . 2
. 2 6 | . 4 . | . . .
------+-------+------
4 5 3 | . . 9 | 6 . .
. . . | . . 4 | 7 . 5
. 9 . | . 5 . | 2 . .
```

**Solution:**
```
7 8 4 | 9 3 2 | 1 5 6
6 1 9 | 4 8 5 | 3 2 7
2 3 5 | 1 7 6 | 4 8 9
------+-------+------
5 7 8 | 2 6 1 | 9 3 4
3 4 1 | 8 9 7 | 5 6 2
9 2 6 | 5 4 3 | 8 7 1
------+-------+------
4 5 3 | 7 2 9 | 6 1 8
8 6 2 | 3 1 4 | 7 9 5
1 9 7 | 6 5 8 | 2 4 3
```

| Metric | Value |
|---|---|
| BACKTRACK calls | **1** |
| BACKTRACK failures | **0** |

**Comment:** AC-3 alone resolves every cell — backtracking is called exactly once (the initial call) and never fails. The high density of clues leaves no ambiguity.

---

### Board 2 — Medium (`medium.txt`)

**Solution:**
```
2 4 5 | 9 8 1 | 3 7 6
1 6 9 | 2 7 3 | 5 8 4
8 3 7 | 5 6 4 | 2 1 9
------+-------+------
9 7 6 | 1 2 5 | 4 3 8
5 1 3 | 4 9 8 | 6 2 7
4 8 2 | 7 3 6 | 9 5 1
------+-------+------
3 9 1 | 6 5 7 | 8 4 2
7 2 8 | 3 4 9 | 1 6 5
6 5 4 | 8 1 2 | 7 9 3
```

| Metric | Value |
|---|---|
| BACKTRACK calls | **3** |
| BACKTRACK failures | **0** |

**Comment:** AC-3 reduces most domains to singletons. Only 2 additional recursive calls are needed, and no branch ever fails — the MRV heuristic guided the search directly to the solution.

---

### Board 3 — Hard (`hard.txt`)

**Solution:**
```
4 6 2 | 8 3 1 | 9 5 7
7 9 5 | 4 2 6 | 1 8 3
3 8 1 | 7 9 5 | 4 2 6
------+-------+------
1 7 3 | 9 8 4 | 2 6 5
6 5 9 | 3 1 2 | 7 4 8
2 4 8 | 5 6 7 | 3 1 9
------+-------+------
9 2 6 | 1 7 8 | 5 3 4
8 3 4 | 2 5 9 | 6 7 1
5 1 7 | 6 4 3 | 8 9 2
```

| Metric | Value |
|---|---|
| BACKTRACK calls | **10** |
| BACKTRACK failures | **3** |

**Comment:** AC-3 reduces the search space significantly, but three cells remain ambiguous after preprocessing. The solver explores 3 dead-end branches before finding the solution. The relatively low failure count shows that forward checking + MRV prunes bad branches very early.

---

### Board 4 — Very Hard (`veryhard.txt`)

**Solution:**
```
9 8 7 | 6 5 4 | 3 2 1
2 4 6 | 1 7 3 | 9 8 5
3 5 1 | 9 2 8 | 7 4 6
------+-------+------
1 2 8 | 5 3 7 | 6 9 4
6 3 4 | 8 9 2 | 1 5 7
7 9 5 | 4 6 1 | 8 3 2
------+-------+------
5 1 9 | 2 8 6 | 4 7 3
4 7 2 | 3 1 9 | 5 6 8
8 6 3 | 7 4 5 | 2 1 9
```

| Metric | Value |
|---|---|
| BACKTRACK calls | **6,050** |
| BACKTRACK failures | **6,037** |

**Comment:** This is a near-minimal-clue puzzle. AC-3 preprocessing alone leaves many cells with 2–4 candidates. With so little initial structure, the solver must explore thousands of branches. The high ratio of failures to calls (6037/6050 ≈ 99.8%) confirms that almost every branch ends in a contradiction — but forward checking catches these contradictions quickly (shallow backtracking) rather than letting them cascade deeply.

---

## Algorithm Summary

```
SOLVE(filename):
    board   ← READ(filename)
    domains ← INIT_DOMAINS(board)       # singletons for clues, {1..9} for blanks
    if not AC3(domains): return FAIL    # preprocessing
    return BACKTRACK(domains)

BACKTRACK(domains):
    calls++
    if COMPLETE(domains): return domains
    cell ← SELECT_MRV(domains)          # most constrained variable
    for value in domains[cell]:
        new_domains ← FORWARD_CHECK(domains, cell, value)
        # forward check = assign + AC-3 propagation
        if new_domains ≠ FAIL:
            result ← BACKTRACK(new_domains)
            if result ≠ FAIL: return result
    failures++
    return FAIL                         # trigger backtrack
```

