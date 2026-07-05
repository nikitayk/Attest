import { useEffect, useRef, useState } from 'react'

export default function PipelineDiagram() {
  const svgRef = useRef(null)
  const [pulsePath, setPulsePath] = useState('main')
  const [showGlow, setShowGlow] = useState(null) // 'certify' or 'quarantine'

  useEffect(() => {
    const animate = () => {
      // 70% chance to take certify path, 30% to take quarantine path
      const takeCertifyPath = Math.random() < 0.7
      setPulsePath(takeCertifyPath ? 'certify' : 'quarantine')

      // Trigger glow at the end of the animation (after ~3.5s)
      setTimeout(() => {
        setShowGlow(takeCertifyPath ? 'certify' : 'quarantine')
        // Clear glow after 500ms
        setTimeout(() => setShowGlow(null), 500)
      }, 3200)

      // Loop every 3.5 seconds
      setTimeout(animate, 3500)
    }

    animate()
  }, [])

  return (
    <div className="w-full overflow-x-auto">
      <svg
        ref={svgRef}
        viewBox="0 0 900 200"
        className="w-full h-auto"
        style={{ minHeight: '200px' }}
      >
        <defs>
          {/* Arrow marker */}
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="7"
            refX="9"
            refY="3.5"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="#D4AF37" />
          </marker>

          {/* Glow filter */}
          <filter id="glow-green" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          <filter id="glow-red" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Main pipeline path */}
        <path
          d="M 50 100 L 750 100"
          stroke="#D4AF37"
          strokeWidth="2"
          fill="none"
          opacity="0.3"
        />

        {/* Fork paths */}
        <path
          d="M 750 100 L 750 140 L 800 140"
          stroke="#22c55e"
          strokeWidth="2"
          fill="none"
          opacity="0.3"
          markerEnd="url(#arrowhead)"
        />
        <path
          d="M 750 100 L 750 60 L 800 60"
          stroke="#ef4444"
          strokeWidth="2"
          fill="none"
          opacity="0.3"
          markerEnd="url(#arrowhead)"
        />

        {/* Animated pulse path */}
        {pulsePath === 'main' && (
          <>
            <circle r="6" fill="#D4AF37">
              <animateMotion
                dur="3.5s"
                repeatCount="1"
                path="M 50 100 L 750 100"
                rotate="auto"
              />
            </circle>
          </>
        )}

        {pulsePath === 'certify' && (
          <>
            <circle r="6" fill="#22c55e">
              <animateMotion
                dur="3.5s"
                repeatCount="1"
                path="M 50 100 L 750 100 L 750 140 L 800 140"
                rotate="auto"
              />
            </circle>
          </>
        )}

        {pulsePath === 'quarantine' && (
          <>
            <circle r="6" fill="#ef4444">
              <animateMotion
                dur="3.5s"
                repeatCount="1"
                path="M 50 100 L 750 100 L 750 60 L 800 60"
                rotate="auto"
              />
            </circle>
          </>
        )}

        {/* Nodes */}
        <g transform="translate(50, 75)">
          <foreignObject width="100" height="50">
            <div className="bg-slate-800 border border-gray-600 rounded-md p-3 text-center">
              <p className="text-xs font-medium text-white">Documents</p>
            </div>
          </foreignObject>
        </g>

        <g transform="translate(170, 75)">
          <foreignObject width="100" height="50">
            <div className="bg-slate-800 border border-gray-600 rounded-md p-3 text-center">
              <p className="text-xs font-medium text-white">Chunk+Hash</p>
            </div>
          </foreignObject>
        </g>

        <g transform="translate(290, 75)">
          <foreignObject width="100" height="50">
            <div className="bg-slate-800 border border-gray-600 rounded-md p-3 text-center">
              <p className="text-xs font-medium text-white">Merkle Tree</p>
            </div>
          </foreignObject>
        </g>

        <g transform="translate(410, 75)">
          <foreignObject width="100" height="50">
            <div className="bg-slate-800 border border-gray-600 rounded-md p-3 text-center">
              <p className="text-xs font-medium text-white">Ed25519 Sign</p>
            </div>
          </foreignObject>
        </g>

        <g transform="translate(530, 75)">
          <foreignObject width="100" height="50">
            <div className="bg-slate-800 border border-gray-600 rounded-md p-3 text-center">
              <p className="text-xs font-medium text-white">Query</p>
            </div>
          </foreignObject>
        </g>

        <g transform="translate(650, 75)">
          <foreignObject width="100" height="50">
            <div className="bg-slate-800 border border-gray-600 rounded-md p-3 text-center">
              <p className="text-xs font-medium text-white">Re-hash Check</p>
            </div>
          </foreignObject>
        </g>

        {/* Certify node */}
        <g transform="translate(800, 115)">
          <foreignObject width="100" height="50">
            <div
              className={`bg-slate-800 border rounded-md p-3 text-center transition-all duration-300 ${
                showGlow === 'certify'
                  ? 'border-green-500 shadow-lg shadow-green-500/50'
                  : 'border-green-600/50'
              }`}
            >
              <p className="text-xs font-medium text-green-400">✓ Generate+Certify</p>
            </div>
          </foreignObject>
        </g>

        {/* Quarantine node */}
        <g transform="translate(800, 35)">
          <foreignObject width="100" height="50">
            <div
              className={`bg-slate-800 border rounded-md p-3 text-center transition-all duration-300 ${
                showGlow === 'quarantine'
                  ? 'border-red-500 shadow-lg shadow-red-500/50'
                  : 'border-red-600/50'
              }`}
            >
              <p className="text-xs font-medium text-red-400">✗ Quarantine</p>
            </div>
          </foreignObject>
        </g>
      </svg>
    </div>
  )
}
