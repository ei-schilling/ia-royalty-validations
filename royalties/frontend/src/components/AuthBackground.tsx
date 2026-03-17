/** Animated mesh-gradient background for auth pages. */

import { motion } from 'motion/react'

const orbs = [
  { cx: '-5%', cy: '-10%', r: 600, color: 'oklch(0.75 0.22 55)', dur: 8, dx: 180, dy: 120 },
  { cx: '60%', cy: '-15%', r: 500, color: 'oklch(0.60 0.28 25)', dur: 10, dx: -140, dy: 200 },
  { cx: '40%', cy: '50%', r: 650, color: 'oklch(0.50 0.22 280)', dur: 9, dx: 160, dy: -150 },
  { cx: '0%', cy: '70%', r: 450, color: 'oklch(0.60 0.24 160)', dur: 11, dx: -120, dy: -180 },
  { cx: '75%', cy: '40%', r: 550, color: 'oklch(0.75 0.22 55)', dur: 12, dx: -180, dy: 100 },
]

export default function AuthBackground() {
  return (
    <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none" aria-hidden="true">
      {/* Floating orbs */}
      {orbs.map((o, i) => (
        <motion.div
          key={i}
          className="absolute rounded-full"
          style={{
            left: o.cx,
            top: o.cy,
            width: o.r,
            height: o.r,
            background: `radial-gradient(circle, ${o.color} 0%, transparent 65%)`,
            opacity: 0.35,
            filter: 'blur(60px)',
          }}
          animate={{
            x: [0, o.dx, -o.dx * 0.7, o.dx * 0.4, 0],
            y: [0, o.dy, -o.dy * 0.6, o.dy * 0.3, 0],
            scale: [1, 1.25, 0.85, 1.1, 1],
          }}
          transition={{
            duration: o.dur,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      ))}

      {/* Dot grid */}
      <div
        className="absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage: 'radial-gradient(circle, oklch(0.9 0 0) 1px, transparent 1px)',
          backgroundSize: '32px 32px',
        }}
      />

      {/* Bottom edge fade */}
      <div className="absolute bottom-0 left-0 right-0 h-48 bg-gradient-to-t from-background to-transparent" />
    </div>
  )
}
