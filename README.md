# ♟ 8by8 AI CHESS LAB

> A complete chess engine and AI bot built entirely from scratch — no Stockfish, no `python-chess`, no prebuilt engines. Every algorithm, every rule, every evaluation metric was implemented by hand.

---

## Table of Contents

1. [What Is This?](#1-what-is-this)
2. [Why This Project Exists](#2-why-this-project-exists)
3. [Key Features](#3-key-features)
4. [Screenshots](#4-screenshots)
5. [Installation](#5-installation)
6. [How To Run](#6-how-to-run)
7. [Controls & UI Guide](#7-controls--ui-guide)
8. [Folder Structure](#8-folder-structure)
9. [Architecture Overview](#9-architecture-overview)
10. [Chess Engine — Simple Explanation](#10-chess-engine--simple-explanation)
11. [Chess Engine — Technical Deep Dive](#11-chess-engine--technical-deep-dive)
12. [AI Search — Simple Explanation](#12-ai-search--simple-explanation)
13. [AI Search — Technical Deep Dive](#13-ai-search--technical-deep-dive)
14. [Evaluation Function](#14-evaluation-function)
15. [Visualization System](#15-visualization-system)
16. [GUI Architecture](#16-gui-architecture)
17. [File-by-File Reference](#17-file-by-file-reference)
18. [Full Application Flow](#18-full-application-flow)
19. [Performance Analysis](#19-performance-analysis)
20. [Limitations](#20-limitations)
21. [Future Improvements](#21-future-improvements)
22. [Learning Outcomes](#22-learning-outcomes)
23. [Contribution Guide](#23-contribution-guide)
24. [Debugging Guide](#24-debugging-guide)
25. [FAQ](#25-faq)
26. [Glossary](#26-glossary)

---

## 1. What Is This?

**8by8 AI CHESS LAB** is a complete, self-contained chess application with a built-from-scratch AI opponent. It is simultaneously:

- **A fully playable chess game** — with all rules, special moves, and end conditions
- **An AI engineering showcase** — featuring Minimax, Alpha-Beta Pruning, Iterative Deepening, and Quiescence Search
- **An algorithm visualization platform** — watch the AI think in real time
- **An analytics dashboard** — track evaluation scores, move quality, and search statistics
- **An educational tool** — understand how chess engines actually work

The entire project is written in Python with zero external chess libraries. Every board representation, move generation algorithm, evaluation function, and search algorithm was written from scratch.

---

## 2. Why This Project Exists

Most chess programs are either:
- Simple GUI wrappers around Stockfish (a prebuilt engine)
- Academic code that's impossible to run or understand

This project takes a different approach: **build everything from scratch, make it beautiful, make it explainable.**

The goal is to demonstrate that you can:
1. Understand and implement the full theory of chess programming
2. Build production-quality software architecture
3. Create a polished, usable product — not just a proof of concept

---

## 3. Key Features

### Chess Engine (from scratch)
- ✅ Complete 8×8 board representation
- ✅ Legal move generation for all 6 piece types
- ✅ All special moves: castling, en passant, pawn promotion
- ✅ Check, checkmate, and stalemate detection
- ✅ Draw conditions: 50-move rule, threefold repetition, insufficient material
- ✅ Move undo/redo with full state restoration
- ✅ FEN import/export and PGN export
- ✅ Zobrist hashing for position identification

### AI Engine (from scratch)
- ✅ Minimax search algorithm
- ✅ Alpha-beta pruning (cuts search tree by ~50%)
- ✅ Iterative deepening (searches depth 1→2→3→N)
- ✅ Quiescence search (prevents horizon effect)
- ✅ Transposition table (avoids re-searching positions)
- ✅ Move ordering: MVV-LVA, killer heuristic, history heuristic
- ✅ Opening book (common first moves)
- ✅ 4 difficulty levels: Easy / Medium / Hard / Expert
- ✅ Runs in a background thread (GUI never freezes)

### Evaluation Function
- ✅ Material counting (piece values)
- ✅ Piece-square tables (positional bonuses)
- ✅ Mobility (number of available moves)
- ✅ King safety (shelter, open files, attack pressure)
- ✅ Center control (occupation and influence)
- ✅ Pawn structure (doubled, isolated, backward, passed pawns)
- ✅ Piece activity (rook files, bishop pair, knight outposts)
- ✅ Endgame adjustments (king centralization)

### Game Modes
- ✅ Human vs AI
- ✅ Human vs Human (local multiplayer)
- ✅ AI vs AI (watch two engines play)

### Visualization & Analytics
- ✅ Live AI thinking panel (depth, nodes, NPS, best move)
- ✅ Top candidate moves with scores
- ✅ Evaluation breakdown by component
- ✅ Board evaluation bar (advantage indicator)
- ✅ Attack heatmap overlay
- ✅ Natural-language AI move explanations
- ✅ Evaluation graph over time (matplotlib)
- ✅ Search depth / node count charts
- ✅ Move quality classification (Blunder/Mistake/Good/Great/Brilliant)
- ✅ Per-player accuracy estimates

---

## 4. Screenshots

```
┌─────────────────────────────────────────────────────────────────┐
│  ♟ 8by8 AI CHESS LAB    ⊕ New Game  ↩ Undo  ⇌ Flip   Difficulty: Hard │
├──────────────────────────────────┬──────────────────────────────┤
│ White to move                    │ EVALUATION                    │
│                                  │ Material:      +0.00         │
│  8 │ ♜ ♞ ♝ ♛ ♚ ♝ ♞ ♜           │ Position:      +0.18         │
│  7 │ ♟ ♟ ♟ ♟ · ♟ ♟ ♟           │ Mobility:      +0.08         │
│  6 │ · · · · · · · ·            │ King Safety:   +0.12         │
│  5 │ · · · · ♟ · · ·           ├──────────────────────────────┤
│  4 │ · · · · ♙ · · ·           │ AI ENGINE                     │
│  3 │ · · · · · ♘ · ·           │ Best move:   Nf3              │
│  2 │ ♙ ♙ ♙ ♙ · ♙ ♙ ♙          │ Evaluation:  +0.31           │
│  1 │ ♖ ♘ ♗ ♕ ♔ ♗ · ♖          │ Depth:       5               │
│     a b c d e f g h             │ Nodes:       14,944          │
│                                  │ Nodes/sec:   1,867           │
│  White captured: —               ├──────────────────────────────┤
│  Black captured: —               │ TOP CANDIDATES               │
│                                  │ ① Nf3      +0.31            │
│                                  │ ② d4       +0.28            │
│                                  │ ③ Bc4      +0.22            │
├──────────────────────────────────┴──────────────────────────────┤
│  [Evaluation Chart]  [Search Depth Chart]  [Move Quality Chart]  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Installation

### Requirements
- Python 3.11 or newer
- pip

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/ai-chess-lab.git
cd ai-chess-lab

# 2. (Optional but recommended) Create a virtual environment
python -m venv venv
source venv/bin/activate          # Linux/macOS
venv\Scripts\activate             # Windows

# 3. Install dependencies
pip install -r requirements.txt
```

### Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| PySide6 | ≥ 6.5.0 | GUI framework (Qt6 for Python) |
| matplotlib | ≥ 3.7.0 | Analytics charts embedded in Qt |
| numpy | ≥ 1.24.0 | Numerical utilities |
| pandas | ≥ 2.0.0 | Data export |

---

## 6. How To Run

```bash
python main.py
```

That's it. No configuration needed.

---

## 7. Controls & UI Guide

### Board Interaction
| Action | How |
|--------|-----|
| Select a piece | Click it |
| Move a piece | Click piece → click destination |
| Drag and drop | Click and drag to destination |
| Pawn promotion | Automatically prompts piece selection |

### Toolbar Buttons
| Button | Function |
|--------|----------|
| ⊕ New Game | Opens game configuration dialog |
| ↩ Undo | Undoes the last 2 moves (your move + AI's response) |
| ⇌ Flip | Flips the board orientation |
| 🔥 Heatmap | Toggles attack heatmap overlay |
| 📊 Export | Saves PGN + analysis JSON |
| ⚙ Settings | Opens theme / animation settings |
| ☀ Light | Toggles dark/light theme |

### Difficulty Levels
| Level | Depth | Time | Style |
|-------|-------|------|-------|
| Easy | 2 ply | 0.5s | Random top-4 moves |
| Medium | 3 ply | 1.0s | Slight randomness |
| Hard | 5 ply | 3.0s | Near optimal |
| Expert | 7 ply | 10s | Full strength |

### Sidebar Panels
- **EVALUATION** — component breakdown of current position score
- **AI ENGINE** — live search statistics while AI is thinking
- **TOP CANDIDATES** — ranked list of moves the AI is considering
- **MOVES** — full game move history in algebraic notation
- **AI REASONING** — natural-language explanation of the AI's last move

### Bottom Charts (tabs)
- **Evaluation** — score over time (positive = White winning)
- **Search Depth** — depth reached per AI move
- **Move Quality** — distribution of Brilliant/Good/Mistake/Blunder moves

---

## 8. Folder Structure

```
ai_chess_lab/
│
├── main.py                  # Application entry point
├── requirements.txt         # Python dependencies
├── README.md                # This file
│
├── engine/                  # Chess rules engine (zero external libs)
│   ├── __init__.py
│   ├── pieces.py            # Piece types, values, piece-square tables
│   ├── moves.py             # Move dataclass, square helpers
│   ├── zobrist.py           # Zobrist hashing for positions
│   ├── board.py             # Board state, make/undo moves
│   ├── move_generator.py    # Legal move generation for all pieces
│   └── game.py              # Game manager, rules, PGN export
│
├── ai/                      # AI search engine (zero external libs)
│   ├── __init__.py
│   ├── evaluator.py         # Board evaluation function
│   ├── search.py            # Minimax + alpha-beta + optimizations
│   └── player.py            # AI player controller, difficulty levels
│
├── gui/                     # PySide6 graphical interface
│   ├── __init__.py
│   ├── theme.py             # Color system and stylesheet
│   ├── board_widget.py      # Interactive chessboard widget
│   ├── panels.py            # Sidebar panels (eval, AI stats, history)
│   ├── charts.py            # Matplotlib analytics charts
│   ├── dialogs.py           # Promotion, new game, settings dialogs
│   └── main_window.py       # Main window and application orchestrator
│
├── analytics/               # Data collection and reporting
│   ├── __init__.py
│   └── collector.py         # Move quality, accuracy, stats collection
│
├── assets/                  # Static assets (icons, fonts if needed)
├── docs/                    # Additional documentation
└── logs/                    # Game logs and exports
```

---

## 9. Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                    MainWindow                        │
│  ┌───────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │BoardWidget│  │  Panels  │  │  Charts (MPL)    │  │
│  └─────┬─────┘  └────┬─────┘  └──────────────────┘  │
│        │ move_req    │ stats                          │
│        ▼             ▼                               │
│  ┌─────────────────────────────┐                     │
│  │         Game (engine)       │                     │
│  │  Board + MoveGenerator      │                     │
│  │  Rules + History            │                     │
│  └──────────────┬──────────────┘                     │
│                 │ board.clone()                      │
│  ┌──────────────▼──────────────┐                     │
│  │      AIWorker (QThread)     │                     │
│  │   AIPlayer → SearchEngine   │                     │
│  │   Evaluator (leaf nodes)    │                     │
│  │   TranspositionTable        │                     │
│  └──────────────┬──────────────┘                     │
│                 │ move_selected signal               │
│  ┌──────────────▼──────────────┐                     │
│  │   AnalyticsCollector        │                     │
│  │   MoveQuality + Charts      │                     │
│  └─────────────────────────────┘                     │
└─────────────────────────────────────────────────────┘
```

**Data flow:**
1. User clicks on the board → `BoardWidget` emits `move_requested`
2. `MainWindow` validates the move via `Game.push_move()`
3. After the human move, `MainWindow` spawns `AIWorker` in a `QThread`
4. `SearchEngine` runs iterative deepening, emitting progress via signals
5. `AIWorker` emits `move_selected` when done
6. `MainWindow` applies the AI move, updates all panels and charts

---

## 10. Chess Engine — Simple Explanation

Think of a chess engine as having three main jobs:

### Job 1: Knowing the Rules
The engine needs to know exactly what moves are legal at any position. For example:
- A pawn on e2 can move to e3 or e4
- A knight on g1 can jump to f3 or h3
- A king cannot move into check

This sounds simple but there are many edge cases — pinned pieces, en passant, castling through attacked squares.

### Job 2: Remembering Everything
After every move, the engine needs to remember exactly what the board looked like so it can undo moves (for searching future possibilities) and detect repetitions (same position 3 times = draw).

### Job 3: Understanding the Position
The engine assigns a numerical "score" to every position — positive means White is winning, negative means Black is winning. A score of +100 means White is about one pawn ahead.

---

## 11. Chess Engine — Technical Deep Dive

### Board Representation

The board is a **flat list of 64 elements** (not a 2D array), indexed by:
```
square_index = rank * 8 + file
```
Where `rank 0 = a1–h1` (White's back rank) and `rank 7 = a8–h8`.

This is called "mailbox" representation. Alternatives like bitboards (64-bit integers with one bit per square) are faster but harder to implement and read.

```python
# Square indexing
# a1=0, b1=1, ..., h1=7
# a2=8, b2=9, ..., h2=15
# ...
# a8=56, ..., h8=63

def sq(rank: int, file: int) -> int:
    return rank * 8 + file
```

### Move Generation

For each piece type, we generate **pseudo-legal moves** (moves ignoring whether they leave the king in check), then **filter** to legal moves:

```python
def generate_legal_moves(board):
    pseudo = generate_pseudo_legal(board)
    legal  = []
    for move in pseudo:
        board.push(move)                           # make the move
        if not board.is_in_check(our_color):      # check if king exposed
            legal.append(move)
        board.pop()                                # undo
    return legal
```

**Sliding pieces** (bishop, rook, queen) use ray casting — iterate in each direction until blocked:
```python
for dr, df in directions:
    r, f = start_rank + dr, start_file + df
    while in_bounds(r, f):
        if board[sq(r,f)] is None:
            add_move(sq(r,f))
        elif enemy_piece(sq(r,f)):
            add_capture(sq(r,f)); break
        else:
            break   # own piece blocks
        r += dr; f += df
```

**Special moves:**

*Castling* — King has not moved, rook has not moved, no pieces between them, king does not pass through check:
```python
if castling_rights["WK"] and is_empty(f1) and is_empty(g1):
    if not attacked(e1) and not attacked(f1) and not attacked(g1):
        add_castle(KINGSIDE)
```

*En passant* — Pawn captures diagonally to the en-passant target square (set when opponent double-pushed):
```python
if ep_square == capture_diagonal:
    remove pawn at (ep_rank, capture_file)  # the captured pawn isn't on ep_square
    move pawn to ep_square
```

### Zobrist Hashing

We assign a random 64-bit number to every (piece, square, color) combination, then XOR them all together to get a position key:

```python
key = 0
for square, piece in board:
    key ^= PIECE_KEYS[piece.color][piece.type][square]
if side_to_move == BLACK:
    key ^= SIDE_KEY
key ^= CASTLING_KEYS[castling_rights]
key ^= EP_FILE_KEYS[ep_file]
```

XOR is its own inverse, so updating the hash after a move is O(1):
```python
key ^= PIECE_KEYS[color][type][from_sq]   # remove piece from source
key ^= PIECE_KEYS[color][type][to_sq]     # place piece at destination
```

### State Undo

Every move saves an `HistoryEntry` before execution:
```python
@dataclass
class HistoryEntry:
    move:            Move
    castling_rights: dict
    en_passant_sq:   Optional[int]
    halfmove_clock:  int
    fullmove_number: int
    position_key:    int   # Zobrist key before move
```

`board.pop()` restores all these fields exactly.

### End Condition Detection

| Condition | Detection |
|-----------|-----------|
| Checkmate | No legal moves AND king in check |
| Stalemate | No legal moves AND king NOT in check |
| 50-move rule | `halfmove_clock >= 100` (counts half-moves) |
| Repetition | Zobrist key appears 3× in `position_counts` dict |
| Insufficient material | Only kings left, or K+B vs K, etc. |

---

## 12. AI Search — Simple Explanation

The AI looks ahead into the future — it imagines "what if I play this move? What would my opponent do? Then what would I do?" — building a tree of possibilities.

### Minimax

Think of it like a game of chess between two rational players:
- **Maximizer (White):** always picks the move with the highest score
- **Minimizer (Black):** always picks the move with the lowest score

Analogy: *"Minimax is like planning a road trip while assuming every traffic light will be red unless you take the optimal route."*

```
Starting position (depth 3)
├── Move A (score: +0.5)
│   ├── Opponent responds X → depth 2
│   │   ├── I play 1 → depth 1 → score: +0.3
│   │   └── I play 2 → depth 1 → score: +0.7   ← I pick this (max)
│   └── Opponent responds Y → depth 2
│       ├── I play 1 → score: +0.1
│       └── I play 2 → score: +0.4              ← I pick this (max)
│   Opponent picks min(+0.7, +0.4) = +0.4       ← Opponent picks Y
└── Move B (score: +0.2)
    ...
AI picks max(+0.4, ...) = +0.4 → plays Move A
```

### Alpha-Beta Pruning

Alpha-beta notices that we can **skip entire branches** when we already know a better option exists:

*"If I already have a move scoring +0.5, and I find a branch where my opponent can force -0.1, I don't need to keep looking at that branch."*

Alpha-beta typically reduces the search tree from **O(b^d)** to **O(b^(d/2))**, effectively doubling the searchable depth.

### Iterative Deepening

Instead of searching directly to depth 5, we search depth 1, then 2, then 3, etc.:
- We can stop at any time and still have a valid answer (from the previous depth)
- Results from shallower searches help **order moves** at deeper searches, making alpha-beta more effective

### Quiescence Search

At the end of the main search, positions aren't "quiet" — there might be a hanging piece about to be captured. We extend the search with **captures only** until the position stabilizes:

*"Never evaluate a position where the queen is about to be taken — look one more move ahead first."*

---

## 13. AI Search — Technical Deep Dive

### Negamax Formulation

Instead of separate maximizer/minimizer logic, negamax uses the identity:
```
max(a, b) = -min(-a, -b)
```

```python
def negamax(board, depth, alpha, beta):
    if depth == 0:
        return quiescence(board, alpha, beta)

    moves = generate_and_order(board)
    if not moves:
        if in_check():
            return -CHECKMATE + (MAX_DEPTH - depth)  # prefer faster mate
        return 0  # stalemate

    for move in moves:
        board.push(move)
        score = -negamax(board, depth-1, -beta, -alpha)
        board.pop()

        alpha = max(alpha, score)
        if alpha >= beta:
            update_killers(move, depth)
            break  # beta cutoff — this branch is "too good", opponent avoids it

    return alpha
```

### Transposition Table

Positions are cached by Zobrist key:
```python
class TTEntry:
    key:   int          # full Zobrist key (to detect hash collisions)
    depth: int          # how deep we searched
    score: int          # score found
    flag:  int          # EXACT | LOWER_BOUND | UPPER_BOUND
    move:  Move         # best move found (for move ordering)
```

Flag types:
- **EXACT**: score is exact — we searched all moves
- **LOWER_BOUND** (beta cutoff): actual score is at least this
- **UPPER_BOUND** (alpha, no improvement): actual score is at most this

### Move Ordering

Good move ordering is critical for alpha-beta efficiency. We score moves before searching:

| Priority | Move Type | Score |
|----------|-----------|-------|
| 1st | TT move (best from previous search) | +10,000 |
| 2nd | Captures (MVV-LVA) | +1,000 + table |
| 3rd | Pawn promotions | +1,500 |
| 4th | Killer moves (caused cutoff at this depth) | +80 |
| 5th | History heuristic (caused cutoffs anywhere) | 0–400 |
| 6th | Other quiet moves | 0 |

**MVV-LVA (Most Valuable Victim, Least Valuable Attacker):**
Prefer capturing a queen with a pawn over capturing a pawn with a queen.
```
score = 1000 + victim_value - attacker_value / 100
```

**Killer Heuristic:**
Moves that caused a beta cutoff at the same depth in sibling nodes are likely good elsewhere too. Store 2 killers per depth level.

**History Heuristic:**
Track `history[color][from][to] += depth²` whenever a quiet move causes a cutoff. Moves that historically cause cutoffs get higher priority.

### Quiescence Search

```python
def quiescence(board, alpha, beta, max_depth=6):
    stand_pat = evaluate(board)   # "do nothing" score

    if stand_pat >= beta:
        return beta           # opponent won't allow this
    alpha = max(alpha, stand_pat)

    if max_depth == 0:
        return stand_pat

    captures = [m for m in legal_moves() if m.is_capture]
    order(captures)

    for capture in captures:
        board.push(capture)
        score = -quiescence(board, -beta, -alpha, max_depth-1)
        board.pop()
        alpha = max(alpha, score)
        if alpha >= beta:
            return beta
    return alpha
```

### Complexity Analysis

| Method | Branching Factor | Depth 5 Nodes |
|--------|-----------------|---------------|
| Pure minimax | ~35 | 35^5 = 52M |
| Alpha-beta (worst case) | ~35 | 35^5 = 52M |
| Alpha-beta (average) | ~6 | 6^5 = 7,776 |
| Alpha-beta (best case) | ~35^0.5≈6 | 35^2.5 = 7,200 |

Good move ordering brings us close to the best case, making depth-5 search real-time feasible even in Python.

---

## 14. Evaluation Function

The evaluation returns a score in **centipawns** (1 pawn = 100 cp) from White's perspective.

### Material Values
| Piece | Value |
|-------|-------|
| Pawn | 100 |
| Knight | 320 |
| Bishop | 330 |
| Rook | 500 |
| Queen | 900 |
| King | 20,000 (effectively infinite) |

### Piece-Square Tables (PST)
Each piece gets a bonus/penalty based on which square it occupies. For example, the pawn PST rewards advanced, central pawns:

```
Pawn PST (White, rank 0=back rank):
 0,  0,  0,  0,  0,  0,  0,  0   ← rank 1 (never here)
 5, 10, 10,-20,-20, 10, 10,  5   ← rank 2
 ...
50, 50, 50, 50, 50, 50, 50, 50   ← rank 7 (about to promote!)
```

Black mirrors the table vertically via `square XOR 56`.

### King Safety
In the middlegame, the king should be castled and sheltered:
- Penalty for each attacker near the king zone
- Penalty for open files adjacent to the king
- Penalty if the king has not castled

In endgames, the king should be active and central (opposite PST).

### Pawn Structure
- **Doubled pawns**: two pawns on the same file (-20 cp each extra)
- **Isolated pawns**: no friendly pawns on adjacent files (-15 cp)
- **Backward pawns**: pawn behind all friendly pawns, can't advance safely (-12 cp)
- **Passed pawns**: no enemy pawns ahead on same/adjacent files (bonus by rank: 0/10/20/35/55/80/120 cp)

### Mobility
The difference in pseudo-legal move count, weighted at 4 cp per move. A side with more available moves is more flexible.

### Piece Activity
- **Bishop pair**: +30 cp (two bishops are stronger than bishop+knight or two knights in open positions)
- **Rook on open file**: +20 cp (file has no pawns)
- **Rook on semi-open file**: +10 cp (file has no friendly pawns)
- **Knight outpost**: +18 cp (knight on a square no enemy pawn can attack)

---

## 15. Visualization System

### Live AI Thinking Panel
Updated every search iteration (each completed depth level):
- Current best move (updated progressively)
- Evaluation score
- Depth reached
- Total nodes searched
- Nodes per second
- Time elapsed
- Transposition table hits

### Top Candidate Moves
The 5 best moves found at root, ranked by score. Shows the AI's "shortlist" and by how much the top choice beats alternatives.

### Evaluation Bar
A vertical bar split between white (light) and dark (black), with the boundary position encoding advantage. Clamps at ±15 pawns for display.

### Board Heatmaps
Toggled by the 🔥 button. Highlights squares attacked by the side to move:
- Blue tones for the current player's attacks
- Intensity proportional to attack count

### AI Explanation
After each AI move, a natural-language explanation is generated by comparing evaluation components before and after the move:

```
"AI played Nf3 because it improves piece placement, increases mobility, 
and gains center control. Evaluated at +0.31 pawns after searching 
14,944 nodes to depth 5."
```

### Analytics Charts
Three embedded matplotlib figures:
1. **Evaluation over time** — line chart with colored fill (positive = white, negative = black)
2. **Search depth + nodes** — dual-axis bar/line chart per AI move
3. **Move quality** — grouped bar chart (White vs Black, 6 quality categories)

---

## 16. GUI Architecture

The GUI uses **PySide6 (Qt6 for Python)** with custom `QPainter`-based rendering.

```
QMainWindow (MainWindow)
├── QFrame (Toolbar)
│   └── QPushButton × N + QComboBox (Difficulty)
├── QSplitter (Vertical: main | charts)
│   ├── QSplitter (Horizontal: board | sidebar)
│   │   ├── QWidget (Board area)
│   │   │   ├── EvalBar (QWidget, custom QPainter)
│   │   │   ├── GameStatusPanel (QFrame)
│   │   │   ├── BoardWidget (QWidget, custom QPainter)  ← board rendering
│   │   │   └── CapturedPiecesPanel (QFrame)
│   │   └── QScrollArea (Sidebar)
│   │       ├── EvalBreakdownPanel (QFrame + QGridLayout)
│   │       ├── AIThinkingPanel (QFrame + QGridLayout)
│   │       ├── TopMovesPanel (QFrame + QLabel × 5)
│   │       ├── MoveHistoryPanel (QFrame + QListWidget)
│   │       └── AIExplanationPanel (QFrame + QLabel)
│   └── AnalyticsChartsWidget (QFrame + QTabWidget)
│       ├── EvalChart (FigureCanvas)
│       ├── DepthNodesChart (FigureCanvas)
│       └── MoveQualityChart (FigureCanvas)
```

### Threading Model
The AI search runs in a dedicated `QThread` to prevent GUI freezing:

```
Main Thread                    AI Thread
──────────────────────         ──────────────────────
User clicks                    AIWorker.run()
  → move_requested signal        → SearchEngine.search()
  → MainWindow._on_player_move()    (iterative deepening)
  → AIWorker.request()           → emit thinking_update (progress)
                              → emit move_selected (done)
                                 ↓
                          Main Thread (signal handler)
                            → _on_ai_move()
                            → board update, panel refresh
```

Signals cross thread boundaries safely in Qt's signal-slot system.

### Board Rendering (QPainter)

The `BoardWidget` overrides `paintEvent()` and draws everything manually:

1. **Board squares** — alternating `board_light` / `board_dark` colored rectangles
2. **Highlights** — semi-transparent fills for last move, selected square, legal destinations
3. **Check** — radial gradient from king square
4. **Pieces** — Unicode chess symbols (`♔♕♖♗♘♙♚♛♜♝♞♟`) rendered with `QPainter.drawText()`
5. **Heatmap** — semi-transparent colored fills overlaid on squares
6. **Coordinates** — rank numbers and file letters in square corners
7. **Animation** — piece movement interpolated over ~12 frames at 60fps using `QTimer`

---

## 17. File-by-File Reference

### `main.py`
**Purpose:** Application entry point. Initializes Qt, applies theme, creates and shows `MainWindow`.

**Key responsibilities:**
- Configure high-DPI scaling
- Set global font
- Apply initial stylesheet
- Start Qt event loop

---

### `engine/pieces.py`
**Purpose:** Piece type definitions, material values, Unicode symbols, and piece-square tables.

**Key classes:**
- `Color(IntEnum)` — WHITE=1, BLACK=-1; has `.opponent()` method
- `PieceType(IntEnum)` — PAWN=1 through KING=6
- `Piece(dataclass)` — frozen dataclass with `color` + `piece_type`

**Key constants:**
- `PIECE_VALUES` — material values in centipawns
- `PAWN_PST`, `KNIGHT_PST`, etc. — 64-element positional tables
- `get_pst_value(piece_type, color, square, is_endgame)` — looks up PST with color mirroring

---

### `engine/moves.py`
**Purpose:** Move representation and algebraic notation utilities.

**Key classes:**
- `MoveFlag` — constants (NORMAL, DOUBLE_PUSH, EN_PASSANT, CASTLE_*, PROMOTION)
- `Move(dataclass)` — from_sq, to_sq, piece, captured, promotion, flag, score
- `HistoryEntry(dataclass)` — pre-move board state snapshot for undo

**Key functions:**
- `sq(rank, file)` — packs rank/file into 0-63
- `sq_to_alg(square)` — converts 28 → "e4"
- `alg_to_sq(notation)` — converts "e4" → 28

---

### `engine/zobrist.py`
**Purpose:** Zobrist hash tables and incremental hashing helpers.

**Key data:**
- `PIECE_KEYS[color][piece_type][square]` — random 64-bit integers
- `SIDE_KEY` — XORed when it's Black's turn
- `CASTLING_KEYS[4-bit int]` — 16 entries for all castling right combinations
- `EP_FILE_KEYS[file]` — 8 entries for en-passant file

---

### `engine/board.py`
**Purpose:** Core board state, move execution, undo, attack detection.

**Key class: `Board`**
- `squares: list[Optional[Piece]]` — 64-element flat board
- `push(move)` — executes a move, saves history entry
- `pop()` — restores previous state
- `is_square_attacked(square, by_color)` — checks all attacker types
- `is_in_check(color)` — checks if color's king is attacked
- `clone()` — fast shallow copy for search
- `to_fen()` / `from_fen(fen)` — FEN serialization

---

### `engine/move_generator.py`
**Purpose:** All pseudo-legal and legal move generation.

**Key class: `MoveGenerator`** (all static methods)
- `generate_legal_moves(board)` — complete legal move list
- `generate_legal_moves_from(board, square)` — moves from one square
- `has_any_legal_move(board)` — quick check (stops at first legal move)
- `attacked_squares(board, color)` — all squares attacked by a color (for heatmaps)

**Internal generators:**
- `_pawn_moves()` — forward, double, captures, en passant, promotion
- `_knight_moves()` — 8 L-shaped jumps
- `_sliding_moves()` — ray-casting for bishop/rook/queen
- `_king_moves()` — 8 adjacent squares + castling

---

### `engine/game.py`
**Purpose:** High-level game state manager.

**Key class: `Game`**
- `push_move(move)` — validates and executes; updates result
- `push_uci(uci)` — convenience method from UCI string
- `undo()` — undoes last move
- `legal_moves()` — cached legal move list
- `_update_result()` — checks all draw/win conditions after each move
- `_to_san(move)` — generates SAN with check/checkmate suffixes
- `to_pgn(...)` — full PGN export with headers and moves

---

### `ai/evaluator.py`
**Purpose:** Static position evaluation function.

**Key class: `Evaluator`** (all static methods)
- `evaluate(board, detail=False)` → `(score_cp, EvalBreakdown | None)`
- `_count_moves(board, color)` — fast pseudo-legal mobility count
- `_center_control(board)` — occupation bonus for center squares
- `_pawn_structure(board)` — doubled/isolated/backward/passed evaluation
- `_king_safety(board, phase)` — attacker count + shelter (middlegame weighted)
- `_piece_activity(board)` — bishop pair, open rook files, knight outposts
- `_endgame_bonus(board)` — king centralization bonus

**Key dataclass: `EvalBreakdown`**
- All component scores as floats
- `.to_dict()` — for panel display
- `.summary()` — formatted text table

---

### `ai/search.py`
**Purpose:** Complete AI search engine.

**Key classes:**
- `TranspositionTable` — fixed-size hash table; `get(key)`, `store(key, depth, score, flag, move)`
- `SearchStats(dataclass)` — nodes, depth, NPS, best move, PV, top moves
- `SearchEngine` — main search class
  - `search(board, max_depth, time_limit, progress_cb)` → `SearchStats`
  - `_root_search()` — root-level search that collects top moves
  - `_negamax()` — recursive alpha-beta with TT
  - `_quiescence()` — capture-only extension search
  - `_order_moves()` — scores moves for ordering
  - `_update_killers()` — killer heuristic update
- `OpeningBook` — static `get_book_move(board)` returning a book move or None

---

### `ai/player.py`
**Purpose:** AI player controller with difficulty presets and threading.

**Key classes:**
- `DifficultyConfig(dataclass)` — depth, time limit, randomness, top-N moves
- `AIPlayer` — wraps `SearchEngine`; `request_move(board, callback)` runs in background thread
- `generate_explanation(board, move, stats)` — builds natural-language explanation

**Difficulty configs:**

| Level | Depth | Time | Randomness |
|-------|-------|------|------------|
| Easy | 2 | 0.5s | Picks from top 4 (70% of the time) |
| Medium | 3 | 1.0s | Picks from top 2 (30% of the time) |
| Hard | 5 | 3.0s | Near-deterministic |
| Expert | 7 | 10s | Always best move |

---

### `analytics/collector.py`
**Purpose:** Collects game statistics for charts and export.

**Key classes:**
- `MoveQuality` — classifies moves by eval delta (Brilliant/Great/Good/Inaccuracy/Mistake/Blunder)
- `MoveDataPoint(dataclass)` — per-move stats record
- `GameAnalytics` — collection of all move data; accuracy/blunders stats
- `AnalyticsCollector` — `record_move()` and `set_result()` interface

---

### `gui/theme.py`
**Purpose:** Color palette, stylesheet generation, theme switching.

**Key classes:**
- `ColorPalette(dataclass)` — ~30 semantic color slots
- `DARK_THEME`, `LIGHT_THEME` — color presets
- `Theme` — class-level state; `set_dark()`, `set_light()`, `stylesheet()`

---

### `gui/board_widget.py`
**Purpose:** Interactive chessboard widget with QPainter rendering.

**Key class: `BoardWidget(QWidget)`**
- `paintEvent()` — draws board, highlights, pieces, coordinates
- `mousePressEvent()` — click-to-move with selection logic
- `mouseMoveEvent()` — drag-and-drop support
- `animate_move(move, piece)` — smooth piece movement over 12 frames
- `set_heatmap(color, data)` — overlay attack visualization

---

### `gui/panels.py`
**Purpose:** All sidebar panel widgets.

**Widgets:**
- `EvalBar` — custom QPainter vertical advantage indicator
- `MoveHistoryPanel` — QListWidget with move pairs formatted in mono font
- `AIThinkingPanel` — grid of stat labels updated during search
- `TopMovesPanel` — ranked move list with score indicators
- `EvalBreakdownPanel` — component-by-component score grid
- `AIExplanationPanel` — word-wrapped explanation text
- `GameStatusPanel` — turn indicator and check/result display

---

### `gui/charts.py`
**Purpose:** Matplotlib figures embedded in Qt via `FigureCanvasQTAgg`.

**Widgets:**
- `EvalChart` — evaluation history line chart with fill
- `DepthNodesChart` — dual-axis depth bar + nodes line chart
- `MoveQualityChart` — grouped bar chart for quality distributions
- `AnalyticsChartsWidget` — `QTabWidget` containing all three charts

---

### `gui/dialogs.py`
**Purpose:** Modal dialogs.

**Dialogs:**
- `PromotionDialog` — 4-button promotion piece selection
- `NewGameDialog` — mode, color, difficulty configuration
- `SettingsDialog` — theme, coords, animation toggles

---

### `gui/main_window.py`
**Purpose:** Main application window and orchestrator.

**Key class: `MainWindow(QMainWindow)`**
- `_build_ui()` — assembles all widgets and layouts
- `_start_new_game(...)` — resets all state for a fresh game
- `_on_player_move(move)` — validates human move, triggers AI
- `_on_ai_move(move, stats, explanation)` — applies AI move, updates all panels
- `_post_move_update(...)` — refreshes board, charts, history, status

---

## 18. Full Application Flow

```
STARTUP
  main.py → QApplication + MainWindow()
  MainWindow._build_ui()
  AI QThreads started (waiting for work)
  Board initialized to starting position

HUMAN MOVE
  User clicks piece → BoardWidget.mousePressEvent()
    → _selected_sq set, legal destinations computed
  User clicks destination → move_requested signal emitted
    → MainWindow._on_player_move(move)
    → Game.push_move(move) — validates + executes
    → AnalyticsCollector.record_move(eval_before, eval_after, ...)
    → _post_move_update(): board/history/charts/status refreshed
    → if game ongoing: _trigger_ai_move()

AI MOVE
  AIWorker.request(game)
    → game.board.clone() (thread-safe copy)
    → AIPlayer.request_move(board, callbacks)
      → SearchEngine.search(board, max_depth, time_limit)
        → OpeningBook.get_book_move() — check book first
        → Iterative deepening loop (depth 1 → max_depth):
          → _root_search():
            → MoveGenerator.generate_legal_moves()
            → _order_moves() (TT move first, then MVV-LVA, killers, history)
            → for each move:
              → board.push(move)
              → _negamax(board, depth-1, -beta, -alpha)
                → check TT (return cached if deep enough)
                → depth==0: _quiescence() → Evaluator.evaluate()
                → for each move: recurse, alpha-beta cutoffs
                → store in TT
                → update killers/history on cutoff
              → board.pop()
            → collect top_moves for display
          → emit thinking_update signal (every depth)
        → apply randomness (for lower difficulties)
      → generate_explanation(board, move, stats)
      → emit move_selected signal
  MainWindow._on_ai_move(move, stats, explanation)
    → Game.push_move(move)
    → update all panels, charts, eval bar
    → re-enable board interaction

GAME END
  After every move, Game._update_result() checks:
    Checkmate → CHECKMATE (no legal moves + in check)
    Stalemate → STALEMATE (no legal moves + not in check)
    50-move → DRAW_50_MOVE (halfmove_clock >= 100)
    Repetition → DRAW_REPETITION (position_counts[key] >= 3)
    Insufficient → DRAW_INSUFFICIENT (only kings + ≤1 minor piece)
  If result != ONGOING:
    Board set non-interactive
    Result displayed in status bar
    Analytics finalized
```

---

## 19. Performance Analysis

### Engine Speed (Python, no compilation)
| Operation | Speed |
|-----------|-------|
| `generate_legal_moves()` | ~500 µs / call |
| `evaluate()` | ~350 µs / call |
| `board.push()` / `board.pop()` | ~5 µs / call |
| `is_square_attacked()` | ~10 µs / call |
| Search NPS (depth 5) | ~2,000–5,000 nodes/sec |

### Why Python Is Slow For Chess
- No bitboard operations (Python integers aren't machine-native 64-bit)
- Object overhead (each Piece is a dataclass instance)
- Dynamic dispatch (no static types at runtime)

### How We Compensate
- **Alpha-beta** cuts branching factor from ~35 to ~6 (effective)
- **Transposition table** avoids re-searching transpositions
- **Move ordering** makes alpha-beta near-optimal
- **Quiescence search** at leaf only (not full expansion)

### Comparison To Stockfish
Stockfish searches millions of nodes per second in C++ with bitboards. Our engine searches thousands. For a Python portfolio project this is normal and expected.

---

## 20. Limitations

1. **Speed** — Pure Python is ~100-1000× slower than C++ engines. Depth 7 is Expert mode's ceiling.
2. **No endgame tablebases** — The evaluator uses heuristics, not perfect endgame knowledge.
3. **No null-move pruning** — Implemented in the architecture but not enabled (risk of zugzwang bugs in endgame).
4. **No multi-threading for search** — The search is single-threaded; Lazy SMP would require more complex shared TT.
5. **Opening book is minimal** — A full production opening book has thousands of positions.
6. **No pondering** — The AI doesn't think during the human's turn.

---

## 21. Future Improvements

### Short Term
- [ ] Full opening book (Polyglot format)
- [ ] Endgame tablebases (Syzygy)
- [ ] Aspiration windows (search around expected score)
- [ ] Late move reductions (LMR)
- [ ] Null-move pruning (with zugzwang detection)

### Medium Term
- [ ] Bitboard board representation (massive speed improvement)
- [ ] PyPy support for 5-10× speed boost
- [ ] Cython compilation of hot paths
- [ ] Pondering (thinking during opponent's turn)
- [ ] FEN import dialog

### Long Term
- [ ] Neural network evaluation (NNUE-style)
- [ ] Online play support (via lichess API)
- [ ] Game database with search
- [ ] Computer vision board input (webcam → FEN)

---

## 22. Learning Outcomes

By studying and extending this project, you will demonstrate:

### Algorithms & Data Structures
- **Recursion** — minimax and quiescence search
- **Search trees** — game tree exploration and pruning
- **Hash tables** — transposition table with collision handling
- **Heuristics** — move ordering, killer moves, history heuristic
- **Graph theory** — game tree as a directed acyclic graph

### Software Engineering
- **OOP design** — clean separation between engine / AI / GUI / analytics
- **Observer pattern** — Qt signals/slots for decoupled communication
- **Threading** — background search with thread-safe GUI updates
- **Strategy pattern** — interchangeable difficulty configurations

### Game Theory
- **Minimax theorem** — optimal play in zero-sum games
- **Alpha-beta pruning** — proof that pruned branches don't affect result
- **Iterative deepening** — why depth-first + time budgets beats fixed-depth

### GUI Development
- **Custom rendering** — QPainter for non-standard visual components
- **Responsive design** — QSplitter, QScrollArea, proper layouts
- **Embedded charts** — matplotlib inside Qt windows
- **Threading models** — worker threads with signal-based results

---

## 23. Contribution Guide

### Setup
```bash
git clone https://github.com/yourusername/ai-chess-lab.git
cd ai-chess-lab
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### Running Tests
```bash
python -c "
from engine.game import Game, GameResult
from ai.search import SearchEngine

# Quick smoke test
g = Game()
assert len(g.legal_moves()) == 20
g.push_uci('e2e4'); g.push_uci('e7e5')
eng = SearchEngine()
stats = eng.search(g.board, max_depth=3, time_limit=5.0)
assert stats.best_move is not None
print('All tests passed')
"
```

### Code Style
- Follow PEP 8
- Type hints everywhere
- Docstrings on all public classes and methods
- No magic numbers — define named constants

### Adding a New Evaluation Feature
1. Add the evaluation logic as a static method in `ai/evaluator.py`
2. Add a field to `EvalBreakdown`
3. Call the method in `Evaluator.evaluate()` and add to `total`
4. Update `EvalBreakdownPanel` in `gui/panels.py` to display it

### Adding a New Panel
1. Create a `QFrame` subclass in `gui/panels.py`
2. Add an instance to `MainWindow._build_sidebar()`
3. Connect it to the relevant signal in `MainWindow`

---

## 24. Debugging Guide

### "No legal moves" immediately
```python
from engine.board import Board
from engine.move_generator import MoveGenerator
b = Board()
moves = MoveGenerator.generate_legal_moves(b)
print(len(moves))   # should be 20
```

### AI returns wrong move
Enable detailed logging in `SearchEngine._negamax()`:
```python
# Add temporarily:
print(f"  depth={depth} score={score} move={move.uci()}")
```

### GUI freezes when AI thinks
Ensure `AIWorker` is moved to its own `QThread` before calling `request()`.
Check that `result_callback` only emits signals, never updates Qt widgets directly.

### Evaluation seems wrong
```python
from ai.evaluator import Evaluator
from engine.game import Game
g = Game()
score, bd = Evaluator.evaluate(g.board, detail=True)
print(bd.summary())   # should be all zeros at start
```

### FEN doesn't load correctly
```python
from engine.board import Board
fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
b = Board.from_fen(fen)
print(b)
print(b.to_fen() == fen)   # should be True
```

---

## 25. FAQ

**Q: Why not use Stockfish?**  
A: The entire point is demonstrating that you can build a chess engine from scratch. Wrapping Stockfish would be a GUI project, not an AI project.

**Q: Why Python instead of C++?**  
A: Python is more readable, more widely known, and more appropriate for a portfolio/educational project. The tradeoff in speed is acceptable at this scale.

**Q: How strong is the AI?**  
A: At Expert difficulty (~depth 7), roughly 1400-1700 Elo for a human player. Much weaker than Stockfish (3500+ Elo) but competitive against casual players.

**Q: Can I use this as a library (without the GUI)?**  
A: Yes. The `engine/` and `ai/` packages have zero GUI dependencies. You can import `Game`, `SearchEngine`, and `Evaluator` independently.

**Q: How do I make the AI stronger?**  
A: Increase `max_depth` in `DIFFICULTY_CONFIGS`, add null-move pruning, add aspiration windows, or port hot paths to Cython/C extensions.

**Q: Is there a way to analyze a specific position?**  
A: Yes — use `Board.from_fen(fen)` and pass it to `SearchEngine.search()` directly:
```python
from engine.board import Board
from ai.search import SearchEngine
b = Board.from_fen("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
eng = SearchEngine()
stats = eng.search(b, max_depth=6, time_limit=10.0)
print(stats.summary())
```

---

## 26. Glossary

| Term | Definition |
|------|------------|
| **Alpha** | In alpha-beta: the best score the maximizing player is guaranteed so far |
| **Alpha-beta pruning** | Optimization that skips branches which can't affect the final result |
| **Beta** | In alpha-beta: the best score the minimizing player is guaranteed so far |
| **Beta cutoff** | When alpha ≥ beta — the current branch is too good for the opponent to allow |
| **Bitboard** | Board representation using 64-bit integers (one bit per square) — very fast |
| **Centipawn** | 1/100th of a pawn — the unit of evaluation (100 cp = 1 pawn advantage) |
| **En passant** | Special pawn capture: a pawn on its 5th rank can capture a neighbor pawn that just double-pushed |
| **Horizon effect** | AI blindly stops search at a fixed depth, missing tactics just beyond — quiescence search fixes this |
| **Heuristic** | A rule of thumb that gives good results in practice without being provably optimal |
| **Iterative deepening** | Searching depth 1, then 2, then 3... to use time efficiently and improve move ordering |
| **Killer heuristic** | Remembering moves that caused beta cutoffs and trying them first in sibling nodes |
| **Legal move** | A move that doesn't leave the moving side's king in check |
| **Mobility** | Number of available moves — more moves = more flexibility = positional advantage |
| **MVV-LVA** | Most Valuable Victim, Least Valuable Attacker — move ordering for captures |
| **Negamax** | A cleaner minimax formulation where both sides maximize (score negated when switching sides) |
| **NPS** | Nodes Per Second — how fast the search explores the game tree |
| **Opening book** | Pre-stored optimal first moves, avoiding the need to search early game positions |
| **Passed pawn** | A pawn with no opposing pawns ahead of it on its file or adjacent files — very strong |
| **Piece-square table (PST)** | A 64-entry table of bonuses/penalties per square for each piece type |
| **Ply** | One half-move (one side's move); depth-5 means 5 plies, not 5 full moves |
| **Principal variation (PV)** | The sequence of best moves found by the search |
| **Pruning** | Cutting off search branches that can't improve the result |
| **Pseudo-legal move** | A move that follows piece movement rules but may leave the king in check |
| **Quiescence search** | Extension of main search that only considers captures, until the position is "quiet" |
| **Transposition** | Reaching the same position via different move orders |
| **Transposition table (TT)** | Hash map caching previously searched positions to avoid redundant work |
| **Zobrist hash** | A technique for hashing board positions using XOR of random numbers |

---

*Built with ♟ from scratch — no engines, no shortcuts.*
