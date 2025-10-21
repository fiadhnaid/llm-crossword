import React from 'react'
import { motion } from 'framer-motion'

export default function CrosswordGrid({ grid }) {
  if (!grid || grid.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-slate-400">
        <div className="text-6xl mb-4">🎯</div>
        <p>Select a puzzle and click "Start Solving" to begin</p>
      </div>
    )
  }

  return (
    <div className="flex justify-center">
      <div
        className="inline-grid gap-0.5 bg-slate-700 p-0.5 rounded"
        style={{
          gridTemplateColumns: `repeat(${grid[0]?.length || 0}, minmax(0, 1fr))`
        }}
      >
        {grid.map((row, rowIdx) =>
          row.map((cell, colIdx) => (
            <motion.div
              key={`${rowIdx}-${colIdx}`}
              className={`cell ${cell.active ? 'cell-active' : 'cell-inactive'}`}
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{
                delay: (rowIdx * row.length + colIdx) * 0.01,
                type: 'spring',
                stiffness: 300
              }}
              whileHover={cell.active ? { scale: 1.1 } : {}}
            >
              {cell.value && (
                <motion.span
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: 'spring', stiffness: 500 }}
                >
                  {cell.value}
                </motion.span>
              )}
            </motion.div>
          ))
        )}
      </div>
    </div>
  )
}
