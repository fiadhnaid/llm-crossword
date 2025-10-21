#!/usr/bin/env python3
"""
Launcher script for the Crossword Solver Web UI.
This script runs independently and doesn't interfere with your agent development.
"""
import os
import sys
import subprocess
from pathlib import Path

def check_dependencies():
    """Check if required Python packages are installed."""
    try:
        import flask
        import flask_socketio
        import flask_cors
        return True
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("\nInstall required packages:")
        print("  pip install flask flask-socketio flask-cors python-socketio")
        return False

def build_frontend():
    """Build the React frontend if needed."""
    web_ui_dir = Path(__file__).parent / "web_ui"
    dist_dir = web_ui_dir / "dist"

    print(f"📁 Web UI directory: {web_ui_dir}")
    print(f"📦 Dist directory: {dist_dir}")

    if not dist_dir.exists():
        print("🔨 Building React frontend...")
        try:
            subprocess.run(["npm", "run", "build"], cwd=web_ui_dir, check=True)
            print("✅ Frontend built successfully!\n")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to build frontend: {e}")
            print("   Make sure you have run 'npm install' in web_ui/")
            return False
    else:
        print(f"✅ Frontend already built (found {len(list(dist_dir.glob('*')))} files)\n")

    return True

def main():
    """Main entry point."""
    print("""
╔════════════════════════════════════════════════════════════╗
║  🧩 CROSSWORD SOLVER WEB UI                                ║
║  Modern React Interface with Real-time Updates            ║
╚════════════════════════════════════════════════════════════╝
    """)

    # Check Python dependencies
    print("🔍 Checking dependencies...")
    if not check_dependencies():
        sys.exit(1)

    # Build frontend if needed
    if not build_frontend():
        sys.exit(1)

    # Import and run the server
    try:
        from src.solver.web_ui import run_ui, BASE_DIR, WEB_UI_DIST

        print(f"📂 Project root: {BASE_DIR}")
        print(f"📦 Serving from: {WEB_UI_DIST}")
        print(f"   (exists: {WEB_UI_DIST.exists()})")
        print("\n🚀 Starting server...")
        print("\n📍 Open your browser to: http://127.0.0.1:5001")
        print("   (Press Ctrl+C to stop)\n")
        print("💡 Tip: Port 5000 is often used by macOS AirPlay. Using 5001 instead.\n")

        run_ui(host='127.0.0.1', port=5001, debug=True)

    except KeyboardInterrupt:
        print("\n\n👋 Server stopped. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
