import React from 'react'
import { motion } from 'framer-motion'

export default function Stats({ stats, status }) {
  const statItems = [
    { label: 'Iterations', value: stats.iterations, icon: '⚡' },
    { label: 'Time', value: `${stats.time.toFixed(1)}s`, icon: '⏱️' },
    { label: 'Tool Calls', value: stats.toolCalls, icon: '🔧' }
  ]

  return (
    <motion.div
      className="glass rounded-xl p-6"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
    >
      <div className="grid grid-cols-3 gap-4">
        {statItems.map((stat, idx) => (
          <motion.div
            key={stat.label}
            className="text-center"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.3 + idx * 0.1 }}
          >
            <div className="text-3xl mb-1">{stat.icon}</div>
            <div className="text-2xl font-bold text-violet-400 mb-1">
              {stat.value}
            </div>
            <div className="text-xs text-slate-400">{stat.label}</div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  )
}
