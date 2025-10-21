# Crossword Solver Web UI

A modern, delightful React-based interface for watching AI solve crossword puzzles in real-time.

## Features

- 🎨 **Modern UI**: Built with React, Vite, and Tailwind CSS
- ⚡ **Real-time Updates**: WebSocket connection for live solving progress
- 🎭 **Beautiful Animations**: Smooth transitions using Framer Motion
- 📊 **Live Stats**: Track iterations, time, and tool calls as the agent works
- 🎯 **Interactive Grid**: Watch cells fill in as clues are solved

## Quick Start

From the project root:

```bash
# Install dependencies (first time only)
cd web_ui
npm install
cd ..

# Run the UI
python run_ui.py
```

Then open http://localhost:5000 in your browser.

## Development

### Frontend Development

```bash
cd web_ui
npm run dev  # Run Vite dev server on port 5173
```

### Backend Development

The backend (Flask + SocketIO) is in `src/solver/web_ui.py`.

To run backend only:
```bash
python -c "from src.solver.web_ui import run_ui; run_ui(debug=True)"
```

## Architecture

- **Frontend**: React + Vite + Tailwind CSS + Framer Motion
- **Backend**: Flask + Flask-SocketIO
- **Communication**: WebSocket for real-time events
- **Agent Integration**: Wraps `CrosswordAgent` without modifying core code

## How It Works

1. Select a puzzle from the dropdown (loads from `data/` folder)
2. Click "Start Solving"
3. Watch the agent work in real-time:
   - Grid updates as answers are filled
   - Progress bar shows completion
   - Activity log shows tool calls
   - Stats track performance

The UI runs completely independently from your agent development work!

## Building for Production

```bash
cd web_ui
npm run build
```

The built files will be in `web_ui/dist/` and served by Flask.
