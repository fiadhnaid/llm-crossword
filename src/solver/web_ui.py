"""
Web-based UI for crossword solving with live updates.
Runs independently without modifying the agent code.
"""
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from flask import Flask, jsonify, request, send_from_directory, send_file
from flask_socketio import SocketIO, emit
from flask_cors import CORS

from src.crossword.utils import load_puzzle
from src.solver.agent import CrosswordAgent


# Get absolute paths
BASE_DIR = Path(__file__).parent.parent.parent  # llm-crossword root
WEB_UI_DIST = BASE_DIR / "web_ui" / "dist"

app = Flask(__name__)
app.config['SECRET_KEY'] = 'crossword-solver-secret'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
current_session: Optional[Dict[str, Any]] = None
solving_thread: Optional[threading.Thread] = None


class WebUIAgent:
    """Wrapper around CrosswordAgent that emits progress via SocketIO."""

    def __init__(self, agent: CrosswordAgent, puzzle_name: str):
        self.agent = agent
        self.puzzle_name = puzzle_name
        self.start_time = None
        self.events: List[Dict[str, Any]] = []

    def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit an event to all connected clients."""
        event = {
            'type': event_type,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        self.events.append(event)
        socketio.emit('solver_event', event)

    def _get_grid_state(self) -> List[List[Dict[str, Any]]]:
        """Convert puzzle grid to JSON-serializable format."""
        grid = []
        for row_idx, row in enumerate(self.agent.puzzle.current_grid.cells):
            grid_row = []
            for col_idx, cell in enumerate(row):
                # Check if this cell is part of any clue
                is_active = any(
                    (row_idx, col_idx) in clue.cells()
                    for clue in self.agent.puzzle.clues
                )
                grid_row.append({
                    'value': cell.value,
                    'row': row_idx,
                    'col': col_idx,
                    'active': is_active
                })
            grid.append(grid_row)
        return grid

    def _get_clues_state(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get current state of all clues."""
        across = []
        down = []

        for clue in self.agent.puzzle.clues:
            clue_data = {
                'number': clue.number,
                'text': clue.text,
                'length': clue.length,
                'answered': clue.answered,
                'direction': clue.direction.value
            }

            if clue.direction.value == 'across':
                across.append(clue_data)
            else:
                down.append(clue_data)

        return {'across': across, 'down': down}

    def solve(self) -> bool:
        """Solve the puzzle with UI updates."""
        self.start_time = time.time()

        # Emit start event
        self._emit_event('solving_started', {
            'puzzle_name': self.puzzle_name,
            'width': self.agent.puzzle.width,
            'height': self.agent.puzzle.height,
            'total_clues': len(self.agent.puzzle.clues)
        })

        # Monkey-patch the agent's tool execution to emit events
        original_execute = self.agent._execute_tool

        def execute_with_events(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
            result = original_execute(tool_name, arguments)

            # Emit tool call event
            self._emit_event('tool_called', {
                'tool': tool_name,
                'arguments': arguments,
                'result': result
            })

            # Emit grid update for relevant tools
            if tool_name in ['set_answer', 'undo_last']:
                self._emit_event('grid_updated', {
                    'grid': self._get_grid_state(),
                    'clues': self._get_clues_state()
                })

            # Special handling for validation
            if tool_name == 'validate_clue':
                clue = self.agent._find_clue(arguments['clue_number'], arguments['direction'])
                if clue and result.get('valid'):
                    self._emit_event('clue_solved', {
                        'clue_number': arguments['clue_number'],
                        'direction': arguments['direction'],
                        'answer': result.get('current_answer'),
                        'text': clue.text
                    })

            # Update progress
            filled = sum(1 for c in self.agent.puzzle.clues if c.answered)
            total = len(self.agent.puzzle.clues)
            self._emit_event('progress_updated', {
                'filled': filled,
                'total': total,
                'percentage': (filled / total * 100) if total > 0 else 0
            })

            return result

        self.agent._execute_tool = execute_with_events

        # Run the solver
        success = self.agent.solve(verbose=False)

        # Emit completion event
        elapsed = time.time() - self.start_time
        self._emit_event('solving_completed' if success else 'solving_failed', {
            'success': success,
            'iterations': self.agent.iterations,
            'time_elapsed': elapsed,
            'tool_calls': self.agent.tool_call_count,
            'grid': self._get_grid_state(),
            'clues': self._get_clues_state()
        })

        return success


def solve_puzzle_background(puzzle_path: str, client, model: str):
    """Background thread to solve puzzle."""
    global current_session

    try:
        # Load puzzle
        puzzle = load_puzzle(puzzle_path)
        puzzle_name = Path(puzzle_path).stem

        # Create agent
        agent = CrosswordAgent(puzzle, client, model)
        web_agent = WebUIAgent(agent, puzzle_name)

        # Update session
        current_session['status'] = 'solving'
        current_session['agent'] = web_agent

        # Solve
        success = web_agent.solve()

        current_session['status'] = 'completed' if success else 'failed'

    except Exception as e:
        socketio.emit('solver_event', {
            'type': 'error',
            'timestamp': datetime.now().isoformat(),
            'data': {'message': str(e)}
        })
        current_session['status'] = 'error'


@app.route('/')
def index():
    """Serve the React app."""
    index_path = WEB_UI_DIST / 'index.html'
    if not index_path.exists():
        return jsonify({
            'error': 'Frontend not built',
            'message': 'Run: cd web_ui && npm run build'
        }), 500
    return send_file(str(index_path))


@app.route('/assets/<path:path>')
def serve_assets(path):
    """Serve React static assets."""
    return send_from_directory(str(WEB_UI_DIST / 'assets'), path)


@app.route('/api/puzzles')
def list_puzzles():
    """List available puzzle files."""
    data_dir = BASE_DIR / 'data'
    puzzles = []

    if data_dir.exists():
        for puzzle_file in data_dir.glob('*.json'):
            puzzles.append({
                'name': puzzle_file.stem,
                'path': str(puzzle_file)
            })

    return jsonify(puzzles)


@app.route('/api/start', methods=['POST'])
def start_solving():
    """Start solving a puzzle."""
    global current_session, solving_thread

    data = request.json
    puzzle_path = data.get('puzzle_path')

    if not puzzle_path:
        return jsonify({'error': 'No puzzle path provided'}), 400

    if current_session and current_session.get('status') == 'solving':
        return jsonify({'error': 'Already solving a puzzle'}), 400

    # Initialize session
    current_session = {
        'status': 'starting',
        'puzzle_path': puzzle_path,
        'start_time': datetime.now().isoformat()
    }

    # Import OpenAI client (assumes env vars are set)
    import os
    from dotenv import load_dotenv
    from openai import AzureOpenAI

    load_dotenv()

    client = AzureOpenAI(
        api_version=os.getenv("OPENAI_API_VERSION"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY")
    )
    model = data.get('model', 'gpt-4o')

    # Start solving in background thread
    solving_thread = threading.Thread(
        target=solve_puzzle_background,
        args=(puzzle_path, client, model),
        daemon=True
    )
    solving_thread.start()

    return jsonify({'status': 'started'})


@app.route('/api/status')
def get_status():
    """Get current solving status."""
    if not current_session:
        return jsonify({'status': 'idle'})

    status_data = {
        'status': current_session.get('status'),
        'puzzle_path': current_session.get('puzzle_path'),
        'start_time': current_session.get('start_time')
    }

    if 'agent' in current_session:
        agent = current_session['agent']
        status_data['iterations'] = agent.agent.iterations
        status_data['tool_calls'] = agent.agent.tool_call_count

    return jsonify(status_data)


@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    emit('connection_established', {'message': 'Connected to solver'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    pass


def run_ui(host='127.0.0.1', port=5001, debug=False):
    """Run the web UI server."""
    print(f"""
╔════════════════════════════════════════════════════════════╗
║  🧩 CROSSWORD SOLVER WEB UI                                ║
╟────────────────────────────────────────────────────────────╢
║  Server starting at: http://{host}:{port}                  ║
║  Open this URL in your browser to use the UI              ║
╚════════════════════════════════════════════════════════════╝
    """)
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    run_ui(debug=True)
