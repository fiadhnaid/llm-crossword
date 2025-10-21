# Quick Start Guide

## Run the Demo

```bash
source venv/bin/activate

# Solve easy puzzle (default - includes API demo)
python main.py

# Solve specific difficulty
python main.py easy
python main.py medium
python main.py hard
python main.py cryptic
```

## Solve Specific Puzzles

```bash
python solve_crossword.py data/easy.json
python solve_crossword.py data/medium.json
python solve_crossword.py data/hard.json
```

## Files Overview

- **`SOLUTION_README.md`** - Complete technical documentation
- **`main.py`** - Demo showing basic API + AI solver
- **`solve_crossword.py`** - CLI to solve specific puzzles
- **`test_solver.py`** - Test suite
- **`src/solver/agent.py`** - Main agentic solver (350+ lines)
- **`src/solver/ui.py`** - PM-themed UI wrapper (200+ lines)

## Key Features

- ✅ Solves easy/medium puzzles 100%
- 🤖 Uses tool calling for self-correction
- 🎭 Humorous PM-themed commentary
- 🔧 7 LLM-accessible tools
- 🚫 No code duplication - uses existing puzzle methods

## Results

| Puzzle | Success |
|--------|---------|
| Easy   | ✅ 100% |
| Medium | ✅ 100% |
| Hard   | ⚠️ 13% |
| Cryptic| ❌ 0% |

See **SOLUTION_README.md** for complete documentation.
