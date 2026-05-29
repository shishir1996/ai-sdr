"use client"

import { useState, useEffect, useRef, useCallback } from "react"

interface CursorProps {
  color?: string
  hoverScale?: number
}

export default function CustomCursor({ color = "168, 85, 247", hoverScale = 0.5 }: CursorProps) {
  const [pos, setPos] = useState({ x: 0, y: 0 })
  const [hovering, setHovering] = useState(false)
  const [visible, setVisible] = useState(false)
  const [clicking, setClicking] = useState(false)
  const trailRef = useRef<HTMLDivElement>(null)
  const glowRef = useRef<HTMLDivElement>(null)
  const rafRef = useRef<number>(0)

  const updatePosition = useCallback((x: number, y: number) => {
    setPos({ x, y })
    if (trailRef.current) {
      trailRef.current.style.transform = `translate(${x - 16}px, ${y - 16}px)`
    }
    if (glowRef.current) {
      glowRef.current.style.transform = `translate(${x - 128}px, ${y - 128}px)`
    }
  }, [])

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      rafRef.current = requestAnimationFrame(() => updatePosition(e.clientX, e.clientY))
      if (!visible) setVisible(true)
    }
    const onLeave = () => setVisible(false)
    const onEnter = () => setVisible(true)
    const onDown = () => setClicking(true)
    const onUp = () => setClicking(false)

    const onHover = (e: MouseEvent) => {
      const target = (e.target as HTMLElement).closest(
        "a, button, input, textarea, select, [data-cursor-hover]"
      )
      setHovering(!!target)
    }

    window.addEventListener("mousemove", onMove, { passive: true })
    window.addEventListener("mousemove", onHover, { passive: true })
    window.addEventListener("mousedown", onDown, { passive: true })
    window.addEventListener("mouseup", onUp, { passive: true })
    document.addEventListener("mouseleave", onLeave, { passive: true })
    document.addEventListener("mouseenter", onEnter, { passive: true })

    return () => {
      window.removeEventListener("mousemove", onMove)
      window.removeEventListener("mousemove", onHover)
      window.removeEventListener("mousedown", onDown)
      window.removeEventListener("mouseup", onUp)
      document.removeEventListener("mouseleave", onLeave)
      document.removeEventListener("mouseenter", onEnter)
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
    }
  }, [visible, updatePosition])

  if (typeof window === "undefined") return null

  return (
    <>
      <div
        className="fixed top-0 left-0 w-1 h-1 rounded-full pointer-events-none z-[9999]"
        style={{
          background: `rgb(${color})`,
          boxShadow: `0 0 6px rgba(${color}, 0.8), 0 0 20px rgba(${color}, 0.4)`,
          transform: `translate(${pos.x}px, ${pos.y}px)`,
          opacity: visible ? 1 : 0,
          transition: "opacity 0.15s ease",
          willChange: "transform",
        }}
      />
      <div
        ref={trailRef}
        className="fixed top-0 left-0 w-8 h-8 rounded-full pointer-events-none z-[9998]"
        style={{
          border: `1px solid rgba(${color}, 0.5)`,
          transform: `translate(${pos.x - 16}px, ${pos.y - 16}px) scale(${hovering ? hoverScale : 1})`,
          opacity: visible ? 1 : 0,
          transition: "opacity 0.15s ease, transform 0.2s ease-out, border-color 0.2s ease",
          willChange: "transform",
          scale: clicking ? 0.7 : hovering ? hoverScale : 1,
          boxShadow: hovering ? `0 0 30px rgba(${color}, 0.25)` : "none",
        }}
      />
      <div
        ref={glowRef}
        className="fixed top-0 left-0 w-64 h-64 rounded-full pointer-events-none z-[9990]"
        style={{
          background: `radial-gradient(circle, rgba(${color}, 0.08) 0%, transparent 70%)`,
          transform: `translate(${pos.x - 128}px, ${pos.y - 128}px)`,
          opacity: visible ? 1 : 0,
          transition: "opacity 0.3s ease",
          willChange: "transform",
        }}
      />
    </>
  )
}
