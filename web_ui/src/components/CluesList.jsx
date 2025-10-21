import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'

function ClueSection({ title, clues, direction }) {
  return (
    <div className="glass rounded-xl p-6">
      <h3 className="text-lg font-semibold mb-4 text-violet-400">{title}</h3>
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {clues.length === 0 ? (
          <p className="text-slate-400 text-sm text-center py-4">No clues yet</p>
        ) : (
          <AnimatePresence>
            {clues.map((clue) => (
              <motion.div
                key={`${clue.number}-${direction}`}
                className={`p-3 rounded-lg transition-all ${
                  clue.answered
                    ? 'bg-green-500/20 border-l-4 border-green-500'
                    : 'bg-slate-800/50'
                }`}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                layout
              >
                <span className="font-bold text-violet-400 mr-2">{clue.number}.</span>
                <span className="text-slate-200">{clue.text}</span>
                <span className="text-slate-400 text-sm ml-2">({clue.length})</span>
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>
    </div>
  )
}

export default function CluesList({ clues }) {
  return (
    <div className="space-y-6">
      <ClueSection title="Across" clues={clues.across} direction="across" />
      <ClueSection title="Down" clues={clues.down} direction="down" />
    </div>
  )
}
