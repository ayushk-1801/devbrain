import { motion, useScroll, useTransform } from 'motion/react';
import { Bell, Database, Code2, GitBranch, Sparkles } from 'lucide-react';
import React from 'react';
import { Link } from 'react-router-dom';

const benefits = [
  {
    icon: Bell,
    title: "Personalized Changelogs",
    body: "Never miss an @mention or file change that matters to you. DevBrain tracks who touched what and generates per-user digests - zero extra GitHub API calls needed.",
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
    body: "Real-time webhook sync captures commits, pull requests, issues, releases, and ADRs. Ingests raw repository events and automatically turns them into structured semantic memory.",
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

  const [activeIndex, setActiveIndex] = React.useState(4);
  React.useEffect(() => {
    return scrollYProgress.onChange((latest) => {
      if (latest < 0.15) setActiveIndex(4);
      else if (latest < 0.30) setActiveIndex(3);
      else if (latest < 0.45) setActiveIndex(2);
      else if (latest < 0.60) setActiveIndex(1);
      else setActiveIndex(0);
    });
  }, [scrollYProgress]);

  const opacities = [opacity0, opacity1, opacity2, opacity3, opacity4];
  const yTransforms = [y0, y1, y2, y3, y4];

  return (
    <section ref={containerRef} id="how-it-works" className="relative w-full h-auto lg:h-[250vh] overflow-visible">
      {/* Sticky container that stays in the viewport on desktop */}
      <div className="benefits-sticky-container relative lg:sticky lg:top-0 lg:left-0 w-full h-auto lg:h-screen overflow-visible lg:overflow-hidden flex flex-col items-center justify-center pt-[80px] md:pt-[100px] lg:pt-[6vh] lg:pb-[4vh] px-6">
        
        <motion.div 
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="flex flex-col items-center text-center w-full max-w-[800px] z-10 lg:-mt-2 xl:-mt-10"
        >
          <h2 className="benefits-heading font-display text-[32px] sm:text-[36px] md:text-[56px] lg:text-[48px] xl:text-[60px] font-extrabold text-text-primary leading-[1.1] tracking-tight">
            Engineered for Complete Codebase Intelligence
          </h2>
          <p className="benefits-paragraph font-display text-[16px] md:text-[18px] text-text-muted max-w-[640px] mt-4 lg:mt-5 leading-[1.7]">
            A hybrid memory layer mapping commits, pull requests, ADRs, and code AST into a single queryable knowledge graph.
          </p>
        </motion.div>

        {/* Stacked Cards Container */}
        <div className="w-full relative min-h-[540px] md:min-h-[500px] mt-[30px] lg:mt-[4vh] xl:mt-10 max-w-[1000px] mx-auto hidden lg:block">
          {benefits.map((card, idx) => {
            const Icon = card.icon;
            
            // Calculate diagonal offsets
            const xOffset = (4 - idx) * 160;
            const yOffset = (4 - idx) * 40;

            return (
              <motion.div
                key={idx}
                style={{
                  position: 'absolute',
                  top: yOffset,
                  left: `calc(50% - 240px + ${xOffset - 320}px)`,
                  zIndex: card.zIndex,
                  opacity: opacities[idx],
                  y: yTransforms[idx]
                }}
                className={`w-[480px] rounded-[24px] p-6 lg:p-6 xl:p-8 border-[12px] border-bg shadow-none transition-colors duration-300 ${
                  activeIndex === idx
                    ? idx === 4 ? 'bg-accent-mint text-[#040200]'
                      : idx === 3 ? 'bg-accent-powder text-[#040200]'
                      : idx === 2 ? 'bg-accent-sage text-[#040200]'
                      : idx === 1 ? 'bg-accent-yellow text-[#040200]'
                      : 'bg-accent-peach text-[#040200]'
                    : 'bg-bg-secondary text-text-muted'
                }`}
              >
                <Icon size={28} className={`${activeIndex === idx ? 'text-[#040200]' : 'text-text-primary'} mb-6`} />
                <h3 className={`font-display text-[22px] font-bold mb-3 leading-tight tracking-tight ${activeIndex === idx ? 'text-[#040200]' : 'text-text-primary'}`}>
                  {card.title}
                </h3>
                <p className={`font-display text-[16px] leading-[1.6] ${activeIndex === idx ? 'text-[#6B6A5E]' : 'text-text-muted'}`}>
                  {card.body}
                </p>
              </motion.div>
            );
          })}

          {/* Desktop View Docs Button (placed absolutely below Card 0 and left-aligned) */}
          <motion.div 
            style={{
              position: 'absolute',
              top: 480, // 160 (yOffset of Card 0) + 296 (card height estimate) + 24 (gap)
              left: 'calc(50% - 240px + 320px)', // matches left calculation of Card 0 (xOffset = 640)
              opacity: opacity0,
              y: y0,
              zIndex: 10
            }}
            className="hidden lg:flex w-[480px] justify-start"
          >
            <Link to="/docs" className="bg-btn-dark text-btn-dark-text text-[14px] md:text-[15px] font-medium px-8 py-[16px] rounded-full transition-[background-color,box-shadow] duration-200 cursor-pointer hover:bg-btn-dark-hover inline-block text-center">
              View Docs
            </Link>
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
                className={`w-full rounded-[24px] p-6 border-[8px] border-bg shadow-none ${
                  idx === 4 ? 'bg-accent-mint'
                    : idx === 3 ? 'bg-accent-powder'
                    : idx === 2 ? 'bg-accent-sage'
                    : idx === 1 ? 'bg-accent-yellow'
                    : 'bg-accent-peach'
                }`}
              >
                <Icon size={28} className="text-[#040200] mb-6" />
                <h3 className="font-display text-[22px] font-bold text-[#040200] mb-3 leading-tight tracking-tight">
                  {card.title}
                </h3>
                <p className="font-display text-[16px] text-[#6B6A5E] leading-[1.6]">
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
          <Link to="/docs" className="bg-btn-dark text-btn-dark-text text-[14px] md:text-[15px] font-medium px-8 py-[16px] rounded-full transition-[background-color,box-shadow] duration-200 cursor-pointer hover:bg-btn-dark-hover inline-block text-center">
            view docs
          </Link>
        </motion.div>
      </div>
    </section>
  );
}
