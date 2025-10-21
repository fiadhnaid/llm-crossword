import React from 'react'
import { motion } from 'framer-motion'

const statusConfig = {
  idle: { label: 'Idle', class: 'bg-slate-600' },
  solving: { label: 'Solving...', class: 'bg-violet-600 animate-pulse-slow' },
  completed: { label: 'Completed', class: 'bg-green-600' },
  failed: { label: 'Failed', class: 'bg-red-600' }
}

export default function Controls({ puzzles, selectedPuzzle, setSelectedPuzzle, status, onStart }) {
  const statusInfo = statusConfig[status] || statusConfig.idle

  return (
    <motion.div
      className="glass rounded-xl p-6 mb-6"
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="flex flex-col md:flex-row items-center gap-4">
        <div className="flex-1 w-full">
          <label className="block text-sm font-medium mb-2">Select Puzzle</label>
          <select
            className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500 transition-all"
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

        <div className="flex items-center gap-4">
          <button
            className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:transform-none"
            onClick={onStart}
            disabled={!selectedPuzzle || status === 'solving'}
          >
            {status === 'solving' ? 'Solving...' : 'Start Solving'}
          </button>

          <div className={`px-4 py-2 rounded-full text-sm font-semibold ${statusInfo.class}`}>
            {statusInfo.label}
          </div>
        </div>
      </div>
    </motion.div>
  )
}
