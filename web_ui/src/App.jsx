import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { io } from 'socket.io-client'
import './index.css'

const API_URL = 'http://localhost:5001'

// PM Commentary
const PM_COMMENTARY = {
  CORRECT: [
    "The PM's brilliant mind strikes again! '{}' was obvious to someone of such intellect.",
    "Elementary, my dear Prime Minister! '{}' fits perfectly - as expected.",
    "Ah yes, '{}' - a word befitting someone of the PM's vast intellectual prowess.",
    "The PM's legendary wordplay skills shine through with '{}'! Magnificent!",
    "How does the PM do it? '{}' was a masterstroke of cognitive excellence!",
    "Superb! '{}' - clearly the work of a crossword virtuoso of the highest caliber.",
    "The PM's unparalleled deductive reasoning produces '{}' with effortless grace.",
    "'{}'! The PM's razor-sharp wit cuts through this clue like butter.",
    "Extraordinary! The PM divines '{}' as if reading the very fabric of language itself.",
    "Bravo! '{}' - proof positive of the PM's towering intellectual superiority.",
  ],
  INCORRECT: [
    "Even the PM's genius requires a moment's reflection on this one.",
    "A strategic pause - the PM's brilliant mind is exploring alternative pathways.",
    "The PM graciously allows the universe a chance to recalibrate.",
    "A tactical retreat - Sun Tzu would approve of the PM's wisdom here.",
    "The PM demonstrates the humility of true genius by reconsidering.",
    "Ah, a teaching moment! The PM illustrates that even brilliance must verify.",
    "The PM's keen intellect detects a need for recalibration - admirable!",
    "A minor course correction - the hallmark of a truly flexible mind.",
  ],
  START: [
    "🧠 The Prime Minister's formidable intellect engages with today's crossword...",
    "📰 The PM approaches this puzzle with characteristic brilliance...",
    "✨ Witness the power of the PM's magnificent cognitive abilities...",
    "🎯 The PM's laser-focused mind prepares to conquer this challenge...",
  ],
  COMPLETE: [
    "🏆 The Prime Minister's unparalleled intellect prevails once more!",
    "👑 Another puzzle vanquished by the PM's superior brainpower!",
    "🎉 The PM's cognitive supremacy is once again demonstrated beyond doubt!",
    "⚡ No crossword can withstand the PM's formidable mental prowess!",
    "🌟 The PM adds another victory to an already legendary record!",
  ]
}

const getRandomCommentary = (type, answer = '') => {
  const comments = PM_COMMENTARY[type]
  const comment = comments[Math.floor(Math.random() * comments.length)]
  return comment.replace('{}', answer)
}

// Simple inline components to avoid import issues
function CrosswordGrid({ grid }) {
  if (!grid || grid.length === 0) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '4rem', color: '#94a3b8' }}>
        <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>🎯</div>
        <p>Select a puzzle and click "Start Solving" to begin</p>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', justifyContent: 'center' }}>
      <div style={{
        display: 'grid',
        gap: '2px',
        background: '#475569',
        padding: '2px',
        borderRadius: '4px',
        gridTemplateColumns: `repeat(${grid[0]?.length || 0}, minmax(0, 1fr))`
      }}>
        {grid.map((row, rowIdx) =>
          row.map((cell, colIdx) => (
            <div
              key={`${rowIdx}-${colIdx}`}
              className={`cell ${cell.active ? 'cell-active' : 'cell-inactive'}`}
            >
              {cell.value || ''}
            </div>
          ))
        )}
      </div>
    </div>
  )
}

function App() {
  const [socket, setSocket] = useState(null)
  const [puzzles, setPuzzles] = useState([])
  const [selectedPuzzle, setSelectedPuzzle] = useState('')
  const [status, setStatus] = useState('idle')
  const [grid, setGrid] = useState([])
  const [clues, setClues] = useState({ across: [], down: [] })
  const [progress, setProgress] = useState({ filled: 0, total: 0 })
  const [stats, setStats] = useState({ iterations: 0, time: 0, toolCalls: 0 })
  const [activities, setActivities] = useState([])

  // Initialize WebSocket
  useEffect(() => {
    const newSocket = io(API_URL)
    setSocket(newSocket)

    newSocket.on('connection_established', (data) => {
      console.log('Connected:', data)
    })

    newSocket.on('solver_event', (event) => {
      handleSolverEvent(event)
    })

    return () => newSocket.close()
  }, [])

  // Load puzzles
  useEffect(() => {
    fetch(`${API_URL}/api/puzzles`)
      .then(res => res.json())
      .then(data => setPuzzles(data))
      .catch(err => console.error('Failed to load puzzles:', err))
  }, [])

  const handleSolverEvent = (event) => {
    const { type, data } = event

    switch (type) {
      case 'solving_started':
        setStatus('solving')
        setProgress({ filled: 0, total: data.total_clues })
        setStats({ iterations: 0, time: 0, toolCalls: 0 })
        addActivity(getRandomCommentary('START'), 'info')
        break

      case 'grid_updated':
        setGrid(data.grid)
        setClues(data.clues)
        break

      case 'clue_solved':
        addActivity(`✓ ${data.clue_number}-${data.direction}: ${data.answer}`, 'success')
        addActivity(`💬 ${getRandomCommentary('CORRECT', data.answer)}`, 'pm-comment')
        break

      case 'tool_called':
        setStats(prev => ({ ...prev, toolCalls: prev.toolCalls + 1 }))
        break

      case 'progress_updated':
        setProgress({ filled: data.filled, total: data.total })
        break

      case 'solving_completed':
        setStatus('completed')
        setGrid(data.grid)
        setClues(data.clues)
        setStats({
          iterations: data.iterations,
          time: data.time_elapsed,
          toolCalls: data.tool_calls
        })
        addActivity(getRandomCommentary('COMPLETE'), 'success')
        addActivity(`💭 Solved in ${data.iterations} iterations, ${data.time_elapsed.toFixed(1)}s, ${data.tool_calls} tool calls`, 'info')
        break

      case 'solving_failed':
        setStatus('failed')
        addActivity('Solving failed or timed out', 'error')
        break

      case 'error':
        addActivity(`Error: ${data.message}`, 'error')
        break

      default:
        break
    }
  }

  const addActivity = (message, level = 'info') => {
    const activity = {
      id: Date.now(),
      message,
      level,
      time: new Date().toLocaleTimeString()
    }
    setActivities(prev => [activity, ...prev].slice(0, 100))
  }

  const handleStart = async () => {
    if (!selectedPuzzle) {
      alert('Please select a puzzle first')
      return
    }

    try {
      const res = await fetch(`${API_URL}/api/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ puzzle_path: selectedPuzzle })
      })

      if (!res.ok) {
        const error = await res.json()
        addActivity(`Failed to start: ${error.error}`, 'error')
      }
    } catch (err) {
      addActivity(`Network error: ${err.message}`, 'error')
    }
  }

  const statusStyles = {
    idle: 'Idle',
    solving: 'Solving...',
    completed: 'Completed ✓',
    failed: 'Failed ✗'
  }

  return (
    <div style={{ minHeight: '100vh', padding: '2rem' }}>
      <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
        {/* Header */}
        <motion.header
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          style={{ textAlign: 'center', marginBottom: '2rem' }}
        >
          <h1 style={{
            fontSize: '3rem',
            fontWeight: 'bold',
            marginBottom: '0.5rem',
            background: 'linear-gradient(90deg, #c084fc, #f472b6)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent'
          }}>
            🧩 Crossword Solver
          </h1>
          <p style={{ color: '#cbd5e1' }}>Watch AI solve crosswords in real-time</p>
        </motion.header>

        {/* Controls */}
        <div className="glass" style={{ borderRadius: '12px', padding: '1.5rem', marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '1rem' }}>
            <div style={{ flex: '1', minWidth: '200px' }}>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.5rem' }}>
                Select Puzzle
              </label>
              <select
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  background: '#1e293b',
                  color: 'white',
                  border: '1px solid #475569',
                  borderRadius: '8px',
                  fontSize: '1rem'
                }}
                value={selectedPuzzle}
                onChange={(e) => setSelectedPuzzle(e.target.value)}
                disabled={status === 'solving'}
              >
                <option value="">Choose a puzzle...</option>
                {puzzles.map((puzzle) => (
                  <option key={puzzle.path} value={puzzle.path}>
                    {puzzle.name}
                  </option>
                ))}
              </select>
            </div>

            <button
              className="btn-primary"
              onClick={handleStart}
              disabled={!selectedPuzzle || status === 'solving'}
            >
              {status === 'solving' ? 'Solving...' : 'Start Solving'}
            </button>

            <div style={{
              padding: '0.5rem 1rem',
              borderRadius: '20px',
              fontSize: '0.875rem',
              fontWeight: 600,
              background: status === 'solving' ? 'rgba(139, 92, 246, 0.2)' : 'rgba(71, 85, 105, 0.5)',
              color: status === 'solving' ? '#a78bfa' : '#cbd5e1'
            }}>
              {statusStyles[status]}
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>
          {/* Grid */}
          <div className="glass" style={{ borderRadius: '12px', padding: '1.5rem' }}>
            {/* Progress */}
            <div style={{ marginBottom: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.875rem', color: '#cbd5e1' }}>Progress</span>
                <span style={{ fontSize: '0.875rem', color: '#cbd5e1' }}>
                  {progress.filled} / {progress.total} clues
                </span>
              </div>
              <div style={{ height: '8px', background: '#1e293b', borderRadius: '9999px', overflow: 'hidden' }}>
                <motion.div
                  style={{ height: '100%', background: 'linear-gradient(90deg, #8b5cf6, #ec4899)' }}
                  initial={{ width: 0 }}
                  animate={{
                    width: `${progress.total > 0 ? (progress.filled / progress.total * 100) : 0}%`
                  }}
                  transition={{ duration: 0.5 }}
                />
              </div>
            </div>

            <CrosswordGrid grid={grid} />

            {/* Stats */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginTop: '1.5rem' }}>
              {[
                { label: 'Iterations', value: stats.iterations, icon: '⚡' },
                { label: 'Time', value: `${stats.time.toFixed(1)}s`, icon: '⏱️' },
                { label: 'Tool Calls', value: stats.toolCalls, icon: '🔧' }
              ].map((stat) => (
                <div key={stat.label} style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '2rem', marginBottom: '0.25rem' }}>{stat.icon}</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#a78bfa', marginBottom: '0.25rem' }}>
                    {stat.value}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{stat.label}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Clues */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {['across', 'down'].map((direction) => (
              <div key={direction} className="glass" style={{ borderRadius: '12px', padding: '1.5rem' }}>
                <h3 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '1rem', color: '#a78bfa', textTransform: 'capitalize' }}>
                  {direction}
                </h3>
                <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                  {clues[direction]?.length > 0 ? (
                    clues[direction].map((clue) => (
                      <div
                        key={`${clue.number}-${direction}`}
                        style={{
                          padding: '0.75rem',
                          marginBottom: '0.5rem',
                          background: clue.answered ? 'rgba(16, 185, 129, 0.1)' : '#1e293b',
                          borderRadius: '6px',
                          borderLeft: clue.answered ? '3px solid #10b981' : '3px solid transparent'
                        }}
                      >
                        <span style={{ fontWeight: 700, color: '#a78bfa', marginRight: '0.5rem' }}>
                          {clue.number}.
                        </span>
                        <span style={{ color: '#e2e8f0' }}>{clue.text}</span>
                        <span style={{ color: '#94a3b8', fontSize: '0.875rem', marginLeft: '0.5rem' }}>
                          ({clue.length})
                        </span>
                      </div>
                    ))
                  ) : (
                    <p style={{ textAlign: 'center', padding: '1rem', color: '#64748b', fontSize: '0.875rem' }}>
                      No clues yet
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Activity Log */}
        <div className="glass" style={{ borderRadius: '12px', padding: '1.5rem' }}>
          <h3 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '1rem' }}>Activity Log</h3>
          <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
            {activities.length > 0 ? (
              activities.map((activity) => (
                <div
                  key={activity.id}
                  style={{
                    padding: '0.75rem',
                    marginBottom: '0.5rem',
                    background: activity.level === 'pm-comment' ? 'rgba(139, 92, 246, 0.1)' : '#1e293b',
                    borderRadius: '6px',
                    borderLeft: `3px solid ${
                      activity.level === 'success' ? '#10b981' :
                      activity.level === 'error' ? '#ef4444' :
                      activity.level === 'pm-comment' ? '#f59e0b' : '#8b5cf6'
                    }`,
                    fontStyle: activity.level === 'pm-comment' ? 'italic' : 'normal'
                  }}
                >
                  <span style={{ fontSize: '0.75rem', color: '#94a3b8', marginRight: '0.5rem' }}>
                    {activity.time}
                  </span>
                  <span style={{
                    fontSize: '0.875rem',
                    color: activity.level === 'pm-comment' ? '#fbbf24' : '#e2e8f0'
                  }}>
                    {activity.message}
                  </span>
                </div>
              ))
            ) : (
              <p style={{ textAlign: 'center', padding: '1rem', color: '#64748b', fontSize: '0.875rem' }}>
                No activity yet
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
