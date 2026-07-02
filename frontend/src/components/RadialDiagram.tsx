export function RadialDiagram() {
  const cx = 400;
  const cy = 300;
  const r = 130;
  const nodes = ['Commit', 'Pull Request', 'ADR', 'File', 'Developer', 'Module', 'Function', 'Decision'];
  
  const nodePositions = nodes.map((name, i) => {
    const angle = (i * 45 - 90) * (Math.PI / 180);
    return {
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
      name,
      angle
    };
  });

  return (
    <div className="w-full relative overflow-hidden flex justify-center">
      <svg viewBox="0 110 800 390" className="w-full h-auto max-w-[1200px]" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <filter id="blur-arc" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" />
          </filter>
          
          <linearGradient id="arc-left" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="var(--color-accent-yellow)" stopOpacity="1" />
            <stop offset="100%" stopColor="var(--color-accent-sage)" stopOpacity="1" />
          </linearGradient>

          <linearGradient id="arc-right" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="var(--color-accent-peach)" stopOpacity="1" />
            <stop offset="100%" stopColor="var(--color-accent-orchid)" stopOpacity="1" />
          </linearGradient>

          <linearGradient id="grad-mint-left" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="var(--color-accent-mint)" stopOpacity="0" />
            <stop offset="100%" stopColor="var(--color-accent-mint)" stopOpacity="1" />
          </linearGradient>

          <linearGradient id="grad-peach-right" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="var(--color-accent-peach)" stopOpacity="1" />
            <stop offset="100%" stopColor="var(--color-accent-peach)" stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* Outer Arcs Background Glow */}
        {/* Left arc path: from ~210 to ~150 degrees */}
        <path d="M 210 190 A 220 220 0 0 0 210 410" stroke="url(#arc-left)" strokeWidth="10" fill="none" opacity="0.8" filter="url(#blur-arc)" />
        {/* Right arc path: from ~-30 to ~30 degrees */}
        <path d="M 590 190 A 220 220 0 0 1 590 410" stroke="url(#arc-right)" strokeWidth="10" fill="none" opacity="0.8" filter="url(#blur-arc)" />

        {/* Outer Arcs Spines */}
        <path d="M 210 190 A 220 220 0 0 0 210 410" stroke="var(--color-border)" strokeWidth="1" fill="none" />
        <path d="M 590 190 A 220 220 0 0 1 590 410" stroke="var(--color-border)" strokeWidth="1" fill="none" />

        {/* Ribbon Connections to Outer Nodes */}
        <g opacity="0.35" filter="url(#blur-arc)">
          <path d="M 80 300 L 260 300" stroke="url(#grad-mint-left)" strokeWidth="40" fill="none" />
          <path d="M 540 300 L 720 300" stroke="url(#grad-peach-right)" strokeWidth="40" fill="none" />
        </g>
        
        <path d="M 120 300 L 270 300" stroke="var(--color-border)" strokeWidth="1.2" strokeDasharray="4 4" fill="none" />
        <path d="M 530 300 L 680 300" stroke="var(--color-border)" strokeWidth="1.2" strokeDasharray="4 4" fill="none" />

        <circle cx="270" cy="300" r="4" fill="var(--color-border)" />
        <circle cx="530" cy="300" r="4" fill="var(--color-border)" />

        {/* Arc Labels */}
        <g transform="translate(100, 200)" className="font-display text-[11px]" textAnchor="middle" dominantBaseline="middle">
          <rect x="-55" y="-12" width="110" height="24" rx="12" fill="var(--color-accent-sage)" fillOpacity="0.25" stroke="var(--color-border)" strokeWidth="1" strokeDasharray="3 3" />
          <text y="1.5" fill="var(--color-text-primary)">Ingestion Layer</text>
        </g>

        <g transform="translate(700, 200)" className="font-display text-[11px]" textAnchor="middle" dominantBaseline="middle">
          <rect x="-50" y="-12" width="100" height="24" rx="12" fill="var(--color-accent-peach)" fillOpacity="0.25" stroke="var(--color-border)" strokeWidth="1" strokeDasharray="3 3" />
          <text y="1.5" fill="var(--color-text-primary)">Recall Layer</text>
        </g>

        {/* Inner Mesh Edges */}
        <g stroke="var(--color-text-primary)" strokeWidth="0.8" opacity="0.25">
          {nodePositions.map((n1, i) => 
            nodePositions.map((n2, j) => {
              if (i < j) {
                return <line key={`edge-${i}-${j}`} x1={n1.x} y1={n1.y} x2={n2.x} y2={n2.y} />
              }
              return null;
            })
          )}
        </g>

        {/* Inner Mesh Nodes */}
        {nodePositions.map((n, i) => (
          <g key={`node-${i}`}>
            <circle cx={n.x} cy={n.y} r="8" style={{ fill: 'var(--color-bg)' }} stroke="var(--color-border)" strokeWidth="1.5" />
            {/* Short leader line & Label */}
            <line 
              x1={n.x + Math.cos(n.angle) * 12} 
              y1={n.y + Math.sin(n.angle) * 12 + (n.name === 'Function' || n.name === 'ADR' ? -8 : 0)} 
              x2={n.x + Math.cos(n.angle) * 24} 
              y2={n.y + Math.sin(n.angle) * 24 + (n.name === 'Function' || n.name === 'ADR' ? -18 : 0)} 
              stroke="var(--color-border)" strokeWidth="1" opacity="0.5" 
            />
            <text 
              x={n.x + Math.cos(n.angle) * 32} 
              y={n.y + Math.sin(n.angle) * 32 + (n.name === 'Function' || n.name === 'ADR' ? -22 : 0)} 
              fill="var(--color-text-primary)" 
              className="font-display text-[12px]" 
              textAnchor={Math.cos(n.angle) > 0.1 ? "start" : Math.cos(n.angle) < -0.1 ? "end" : "middle"}
              dominantBaseline={Math.sin(n.angle) > 0.1 ? "hanging" : Math.sin(n.angle) < -0.1 ? "baseline" : "middle"}
            >
              {n.name}
            </text>
          </g>
        ))}

        {/* Flanking Terminal Nodes */}
        <g transform="translate(80, 300)" className="font-display text-[13px]" textAnchor="middle" dominantBaseline="middle">
          <rect x="-45" y="-16" width="90" height="32" rx="16" style={{ fill: 'var(--color-bg)' }} stroke="var(--color-border)" strokeWidth="1.5" />
          <text y="1" fill="var(--color-text-primary)">Your Repo</text>
        </g>

        <g transform="translate(720, 300)" className="font-display text-[13px]" textAnchor="middle" dominantBaseline="middle">
          <rect x="-60" y="-18" width="120" height="36" rx="18" fill="var(--color-btn-dark)" />
          <text y="1" fill="var(--color-btn-dark-text)">Your Question</text>
        </g>

      </svg>
    </div>
  );
}
