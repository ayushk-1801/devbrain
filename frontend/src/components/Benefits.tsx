import { motion, useScroll, useTransform } from 'motion/react';
import { Cpu, Database, Code2, GitBranch, Sparkles } from 'lucide-react';
import React from 'react';

const benefits = [
  {
    icon: Cpu,
    title: "Surgical Memory Pruning",
    body: "Cleanly dissolve deprecated modules or legacy refactors using the forget() API. Removes subgraphs in real-time while keeping the rest of the memory intact.",
    bg: "var(--color-accent-peach)",
    zIndex: 5
  },
  {
    icon: Database,
    title: "Hybrid Memory Engine",
    body: "Combines vector databases for semantic concepts and graph databases for multi-hop relationship traversal. Answer complex 'why was this changed' queries instantly.",
    bg: "var(--color-accent-yellow)",
    zIndex: 4
  },
  {
    icon: Code2,
    title: "AST & Dependency Parsing",
    body: "Parses your codebases down to abstract syntax trees using cognee[codegraph]. Maps function calls, class inheritances, and modules directly into the memory graph.",
    bg: "var(--color-accent-sage)",
    zIndex: 3
  },
  {
    icon: GitBranch,
    title: "Automated GitHub Sync",
    body: "Real-time webhook sync captures commits, pull requests, issues, and ADRs. Ingests raw repository events and automatically turns them into structured semantic memory.",
    bg: "var(--color-accent-powder)",
    zIndex: 2
  },
  {
    icon: Sparkles,
    title: "Self-Improving Memory",
    body: "Runs weekly background consolidation to prune stale nodes, strengthen frequently-queried paths, and surgically delete deprecated subgraphs on command.",
    bg: "var(--color-accent-mint)",
    zIndex: 1
  }
];

export function Benefits() {
  const containerRef = React.useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end end"]
  });

  // Statically defined scroll transforms for each card to satisfy React Hooks rules
  // Card 4 (New Hires) - idx 4
  const opacity4 = useTransform(scrollYProgress, [0.00, 0.15], [0, 1]);
  const y4 = useTransform(scrollYProgress, [0.00, 0.15], [400, 0]);

  // Card 3 (Engineering Managers) - idx 3
  const opacity3 = useTransform(scrollYProgress, [0.15, 0.30], [0, 1]);
  const y3 = useTransform(scrollYProgress, [0.15, 0.30], [400, 0]);

  // Card 2 (Senior Engineers) - idx 2
  const opacity2 = useTransform(scrollYProgress, [0.30, 0.45], [0, 1]);
  const y2 = useTransform(scrollYProgress, [0.30, 0.45], [400, 0]);

  // Card 1 (Developer Tooling Teams) - idx 1
  const opacity1 = useTransform(scrollYProgress, [0.45, 0.60], [0, 1]);
  const y1 = useTransform(scrollYProgress, [0.45, 0.60], [400, 0]);

  // Card 0 (AI Coding Agents) - idx 0
  const opacity0 = useTransform(scrollYProgress, [0.60, 0.75], [0, 1]);
  const y0 = useTransform(scrollYProgress, [0.60, 0.75], [400, 0]);

  // Color transitions for each card (active highlight when they are the top card)
  // Card 4 (New Hires) color transition (active during 0.00 - 0.15)
  const bg4 = useTransform(
    scrollYProgress,
    [0.00, 0.13, 0.15, 1.00],
    ["#D8F0E4", "#D8F0E4", "#F3F3E8", "#F3F3E8"]
  );

  // Card 3 (Engineering Managers) color transition (active during 0.15 - 0.30)
  const bg3 = useTransform(
    scrollYProgress,
    [0.00, 0.15, 0.17, 0.28, 0.30, 1.00],
    ["#F3F3E8", "#F3F3E8", "#CFE3EA", "#CFE3EA", "#F3F3E8", "#F3F3E8"]
  );

  // Card 2 (Senior Engineers) color transition (active during 0.30 - 0.45)
  const bg2 = useTransform(
    scrollYProgress,
    [0.00, 0.30, 0.32, 0.43, 0.45, 1.00],
    ["#F3F3E8", "#F3F3E8", "#D9E7C9", "#D9E7C9", "#F3F3E8", "#F3F3E8"]
  );

  // Card 1 (Developer Tooling Teams) color transition (active during 0.45 - 0.60)
  const bg1 = useTransform(
    scrollYProgress,
    [0.00, 0.45, 0.47, 0.58, 0.60, 1.00],
    ["#F3F3E8", "#F3F3E8", "#F3FE7A", "#F3FE7A", "#F3F3E8", "#F3F3E8"]
  );

  // Card 0 (AI Coding Agents) color transition (active during 0.60 - 1.00)
  const bg0 = useTransform(
    scrollYProgress,
    [0.00, 0.60, 0.62, 1.00],
    ["#F3F3E8", "#F3F3E8", "#FFD3BA", "#FFD3BA"]
  );

  const opacities = [opacity0, opacity1, opacity2, opacity3, opacity4];
  const yTransforms = [y0, y1, y2, y3, y4];
  const bgs = [bg0, bg1, bg2, bg3, bg4];

  return (
    <section ref={containerRef} className="relative w-full h-auto lg:h-[250vh] overflow-visible">
      {/* Sticky container that stays in the viewport on desktop */}
      <div className="relative lg:sticky lg:top-0 lg:left-0 w-full h-auto lg:h-screen overflow-visible lg:overflow-hidden flex flex-col items-center justify-center pt-[80px] md:pt-[100px] pb-[80px] px-6">
        
        <motion.div 
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="flex flex-col items-center text-center w-full max-w-[800px] z-10 lg:-mt-16"
        >
          <h2 className="font-display text-[36px] md:text-[56px] lg:text-[60px] font-extrabold text-text-primary leading-[1.1] tracking-tight">
            Engineered for Complete Codebase Intelligence
          </h2>
          <p className="font-display text-[16px] md:text-[18px] text-text-muted max-w-[640px] mt-6 leading-[1.7]">
            A hybrid memory layer mapping commits, pull requests, ADRs, and code AST into a single queryable knowledge graph.
          </p>
        </motion.div>

        {/* Stacked Cards Container */}
        <div className="w-full relative min-h-[580px] md:min-h-[520px] mt-[40px] max-w-[1000px] mx-auto hidden lg:block">
          {benefits.map((card, idx) => {
            const Icon = card.icon;
            
            // Calculate diagonal offsets
            const xOffset = (4 - idx) * 160;
            const yOffset = (4 - idx) * 48;

            return (
              <motion.div
                key={idx}
                style={{
                  position: 'absolute',
                  top: yOffset,
                  left: `calc(50% - 240px + ${xOffset - 320}px)`,
                  zIndex: card.zIndex,
                  backgroundColor: bgs[idx],
                  opacity: opacities[idx],
                  y: yTransforms[idx]
                }}
                className="w-[480px] rounded-[24px] p-8 md:p-10 border-[12px] border-[var(--color-bg)] shadow-none"
              >
                <Icon size={28} className="text-text-primary mb-6" />
                <h3 className="font-display text-[22px] font-bold text-text-primary mb-3 leading-tight tracking-tight">
                  {card.title}
                </h3>
                <p className="font-display text-[16px] text-text-muted leading-[1.6]">
                  {card.body}
                </p>
              </motion.div>
            );
          })}

          {/* Desktop View Docs Button (placed absolutely below Card 0 and left-aligned) */}
          <motion.div
            style={{
              position: 'absolute',
              top: 490, // 192 (yOffset of Card 0) + 274 (card height estimate) + 24 (gap)
              left: 'calc(50% - 240px + 320px)', // matches left calculation of Card 0 (xOffset = 640)
              opacity: opacity0,
              y: y0,
              zIndex: 10
            }}
            className="hidden lg:flex w-[480px] justify-start"
          >
            <button className="bg-btn-dark text-btn-dark-text font-mono text-[14px] md:text-[15px] font-medium px-8 py-[16px] rounded-full transition-[background-color,box-shadow] duration-200 cursor-pointer hover:bg-[#3a3836]">
              View Docs
            </button>
          </motion.div>
        </div>

        {/* Mobile/Tablet View (Flat vertical list) */}
        <div className="w-full flex flex-col gap-6 mt-16 lg:hidden max-w-[600px] mx-auto">
          {benefits.map((card, idx) => {
            const Icon = card.icon;
            return (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-100px" }}
                transition={{ duration: 0.4, ease: "easeOut", delay: idx * 0.1 }}
                style={{ backgroundColor: card.bg }}
                className="w-full rounded-[24px] p-6 border-[8px] border-[var(--color-bg)] shadow-none"
              >
                <Icon size={28} className="text-text-primary mb-6" />
                <h3 className="font-display text-[22px] font-bold text-text-primary mb-3 leading-tight tracking-tight">
                  {card.title}
                </h3>
                <p className="font-display text-[16px] text-text-muted leading-[1.6]">
                  {card.body}
                </p>
              </motion.div>
            );
          })}
        </div>

        {/* Mobile View Docs Button */}
        <motion.div 
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-50px" }}
          transition={{ duration: 0.5, ease: "easeOut", delay: 0.3 }}
          className="mt-16 md:mt-12 lg:hidden relative z-10 flex justify-center w-full"
        >
          <button className="bg-btn-dark text-btn-dark-text font-mono text-[14px] md:text-[15px] font-medium px-8 py-[16px] rounded-full transition-[background-color,box-shadow] duration-200 cursor-pointer hover:bg-[#3a3836]">
            view docs
          </button>
        </motion.div>
      </div>
    </section>
  );
}
