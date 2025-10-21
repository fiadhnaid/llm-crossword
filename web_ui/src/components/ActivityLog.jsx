import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'

export default function ActivityLog({ activities }) {
  const levelStyles = {
    info: 'border-l-violet-500 bg-violet-500/10',
    success: 'border-l-green-500 bg-green-500/10',
    error: 'border-l-red-500 bg-red-500/10'
  }

  return (
    <motion.div
      className="glass rounded-xl p-6"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
    >
      <h3 className="text-lg font-semibold mb-4">Activity Log</h3>
      <div className="max-h-64 overflow-y-auto space-y-2">
        {activities.length === 0 ? (
          <p className="text-slate-400 text-sm text-center py-4">No activity yet</p>
        ) : (
          <AnimatePresence mode="popLayout">
            {activities.map((activity) => (
              <motion.div
                key={activity.id}
                className={`p-3 rounded-lg border-l-4 ${levelStyles[activity.level]}`}
                initial={{ opacity: 0, height: 0, marginBottom: 0 }}
                animate={{ opacity: 1, height: 'auto', marginBottom: '0.5rem' }}
                exit={{ opacity: 0, height: 0, marginBottom: 0 }}
                layout
              >
                <span className="text-xs text-slate-400 mr-2">{activity.time}</span>
                <span className="text-sm text-slate-200">{activity.message}</span>
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>
    </motion.div>
  )
}
