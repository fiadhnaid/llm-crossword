# 🚀 Web UI Quick Start

## Simple 2-Step Setup

### 1. Install Dependencies (First Time Only)

```bash
# Python dependencies
pip install -r requirements.txt

# Frontend dependencies
cd web_ui
npm install
cd ..
```

### 2. Run the UI

```bash
python run_ui.py
```

Then open: **http://127.0.0.1:5001**

---

## ⚠️ Troubleshooting

### "Port 5000 is in use"

**Solution**: The UI now uses port **5001** by default (macOS AirPlay uses 5000).

If 5001 is also in use, edit `run_ui.py`:
```python
run_ui(host='127.0.0.1', port=5002, debug=True)  # Change to any free port
```

Also update `web_ui/src/App.jsx`:
```javascript
const API_URL = 'http://localhost:5002'  // Match the port
```

Then rebuild:
```bash
cd web_ui && npm run build && cd ..
```

### "Module not found: flask"

```bash
pip install flask flask-socketio flask-cors python-socketio
```

### "Frontend not built" Error

```bash
cd web_ui
npm install
npm run build
cd ..
```

### Cannot Access Localhost

1. **Check the server started**: Look for "Server starting at: http://127.0.0.1:5001"
2. **Use 127.0.0.1 instead of localhost**: http://127.0.0.1:5001
3. **Check firewall**: Make sure localhost connections are allowed
4. **Try a different browser**: Some browsers have strict localhost policies

### WebSocket Connection Issues

If the UI loads but shows "connection failed":
- Make sure you're accessing the **same port** the server is running on
- Check browser console (F12) for errors
- Try refreshing the page

---

## 📱 Usage

1. **Select a puzzle** from the dropdown (loads from `data/` folder)
2. **Click "Start Solving"**
3. **Watch** the agent solve in real-time!

---

## 🎯 Features

- ✨ Real-time grid updates
- 📊 Live statistics (iterations, time, tool calls)
- 📝 Activity log of all agent actions
- 🎨 Beautiful animations
- 📱 Responsive design

---

## 🔧 For Developers

### Run in Development Mode

**Frontend** (with hot reload):
```bash
cd web_ui
npm run dev  # Runs on http://localhost:5173
```

**Backend** (separate terminal):
```bash
python -c "from src.solver.web_ui import run_ui; run_ui(debug=True)"
```

Update `web_ui/src/App.jsx` to use dev server:
```javascript
const API_URL = 'http://localhost:5001'  // Backend URL
```

### Build for Production

```bash
cd web_ui
npm run build
```

The built files go to `web_ui/dist/` and are served by Flask.

---

## 💡 Tips

- **Port conflict?** Use ports 5001-5010 to avoid conflicts
- **Slow loading?** Make sure `npm run build` completed successfully
- **Can't find puzzles?** Check that `.json` files exist in `data/` folder

---

Need more help? See `UI_GUIDE.md` for complete documentation!
