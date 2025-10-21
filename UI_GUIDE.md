# 🧩 Crossword Solver Web UI Guide

A modern, delightful web interface for watching your AI agent solve crossword puzzles in real-time!

## ✨ Features

- **🎨 Modern Design**: Beautiful React UI with Tailwind CSS and dark mode
- **⚡ Real-time Updates**: WebSocket-powered live progress tracking
- **🎭 Smooth Animations**: Delightful Framer Motion animations as clues are solved
- **📊 Live Stats**: Track iterations, time, and tool calls
- **🎯 Interactive Grid**: Watch the crossword fill in as the agent works
- **📝 Activity Log**: See every tool call and decision the agent makes

## 🚀 Quick Start

### First Time Setup

```bash
# 1. Install Python dependencies (if not already installed)
pip install -r requirements.txt

# 2. Install Node.js dependencies for the UI
cd web_ui
npm install
cd ..
```

### Running the UI

Simply run from the project root:

```bash
python run_ui.py
```

Then open your browser to **http://localhost:5000**

That's it! The launcher handles everything:
- Checks dependencies
- Builds the frontend (first time only)
- Starts the Flask server
- Serves the React app

## 🎮 How to Use

1. **Select a Puzzle**: Choose from available puzzles in the `data/` directory
2. **Click "Start Solving"**: Watch the AI agent work in real-time
3. **Observe**:
   - Grid fills in with answers
   - Progress bar shows completion
   - Stats update live
   - Activity log shows agent's thinking

## 🏗️ Architecture

### Frontend (Modern React Stack)
- **React 19** - Latest React features
- **Vite** - Lightning-fast build tool
- **Tailwind CSS v4** - Utility-first styling
- **Framer Motion** - Smooth animations
- **Socket.IO Client** - Real-time communication

### Backend (Python)
- **Flask** - Lightweight web framework
- **Flask-SocketIO** - WebSocket support
- **Flask-CORS** - Cross-origin requests

### Integration
- Wraps your `CrosswordAgent` without modifying it
- Runs in a separate thread
- Emits events for UI updates

## 📁 Project Structure

```
llm-crossword/
├── web_ui/                     # React frontend
│   ├── src/
│   │   ├── App.jsx            # Main app component
│   │   ├── components/        # React components
│   │   │   ├── CrosswordGrid.jsx
│   │   │   ├── CluesList.jsx
│   │   │   ├── Stats.jsx
│   │   │   ├── Controls.jsx
│   │   │   └── ActivityLog.jsx
│   │   ├── index.css          # Tailwind styles
│   │   └── main.jsx           # Entry point
│   ├── dist/                  # Built files (auto-generated)
│   └── package.json
│
├── src/solver/
│   ├── agent.py               # Your agent (unchanged!)
│   ├── ui.py                  # Terminal UI (unchanged!)
│   └── web_ui.py              # Web UI backend (separate)
│
└── run_ui.py                  # Convenient launcher script
```

## 🔧 Development Mode

### Frontend Development (with hot reload)

```bash
cd web_ui
npm run dev  # Starts Vite dev server on http://localhost:5173
```

Then update the `API_URL` in `App.jsx` to point to your backend:
```javascript
const API_URL = 'http://localhost:5000'
```

And run the backend separately:
```bash
python -c "from src.solver.web_ui import run_ui; run_ui(debug=True)"
```

### Backend Development

The backend code is in `src/solver/web_ui.py`. It:
- Serves the built React app
- Provides REST API endpoints
- Handles WebSocket connections
- Wraps your agent with event emission

## 🎨 Customization

### Styling
Edit `web_ui/src/index.css` and `web_ui/tailwind.config.js`

### Components
All React components are in `web_ui/src/components/`

### Backend Events
Modify event emission in `src/solver/web_ui.py` → `WebUIAgent` class

## 🚫 What This Doesn't Affect

The Web UI is **completely separate** from your agent development:

✅ Your `agent.py` is **untouched**
✅ Your terminal `ui.py` still works
✅ All your existing code runs normally
✅ The Web UI is an **optional** alternative interface

You can continue developing your agent while the Web UI runs independently!

## 🐛 Troubleshooting

### "Module not found" errors
```bash
pip install flask flask-socketio flask-cors python-socketio
```

### Frontend not building
```bash
cd web_ui
npm install
npm run build
```

### Port 5000 already in use
Edit `run_ui.py` and change the port:
```python
run_ui(host='127.0.0.1', port=5001, debug=False)
```

### WebSocket connection fails
- Check that both frontend and backend are running
- Verify CORS is enabled in `web_ui.py`
- Check browser console for errors

## 📝 Notes

- The UI updates in real-time via WebSocket
- Solving runs in a background thread
- Multiple clients can connect and watch simultaneously
- Progress is maintained server-side

## 🎉 Enjoy!

This UI makes it delightful to watch your AI agent solve crosswords. No more staring at terminal output - now you have a beautiful, animated interface!

Happy solving! 🧩
