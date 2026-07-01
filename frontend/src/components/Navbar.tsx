import { Github } from 'lucide-react';
import { motion, useScroll, useTransform } from 'motion/react';

export function Navbar() {
  const { scrollY } = useScroll();

  // Morph values continuously based on scrollY (0px to 200px scroll range)
  const height = useTransform(scrollY, [0, 200], [70, 54]);
  const width = useTransform(scrollY, [0, 200], ["100%", "90%"]);
  const maxWidth = useTransform(scrollY, [0, 200], [2560, 1024]); // increased to 1024 to prevent squishing
  const top = useTransform(scrollY, [0, 200], [0, 16]);
  const borderRadius = useTransform(scrollY, [0, 200], [0, 27]); // half of height 54 is 27px (perfect pill shape)

  const backgroundColor = useTransform(
    scrollY,
    [0, 200],
    ["rgba(254, 254, 243, 1)", "rgba(254, 254, 243, 0.85)"]
  );

  const borderColor = useTransform(
    scrollY,
    [0, 200],
    ["rgba(34, 34, 34, 0)", "rgba(34, 34, 34, 0.08)"]
  );

  const boxShadow = useTransform(
    scrollY,
    [0, 200],
    ["0px 0px 0px rgba(4, 2, 0, 0)", "0px 12px 32px rgba(4, 2, 0, 0.04)"]
  );

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 flex justify-center pointer-events-none">
      <motion.div 
        style={{
          height,
          width,
          maxWidth,
          top,
          borderRadius,
          backgroundColor,
          borderColor,
          boxShadow
        }}
        className="w-full pointer-events-auto flex items-center justify-between relative backdrop-blur-md border px-6 md:px-7"
      >
        {/* Left */}
        <div className="flex items-center gap-3">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-text-primary">
            <circle cx="8" cy="12" r="4" />
            <circle cx="16" cy="12" r="4" />
            <line x1="12" y1="12" x2="16" y2="12" />
          </svg>
          <span className="font-mono text-[18px] font-bold text-text-primary">devbrain</span>
        </div>

        {/* Center - desktop only */}
        <div className="hidden md:flex items-center gap-6">
          {['About', 'Features', 'How It Works', 'Use Cases', 'Docs'].map(item => (
            <a key={item} href={`#${item.toLowerCase().replace(/ /g, '-')}`} className="font-mono text-[14px] md:text-[15px] font-medium text-text-primary hover:underline underline-offset-4 decoration-1">
              {item}
            </a>
          ))}
        </div>

        {/* Right */}
        <div className="flex items-center gap-5">
          <a href="https://github.com" target="_blank" rel="noopener noreferrer" aria-label="GitHub Repository" className="flex items-center gap-2 text-text-muted hover:text-text-primary transition-colors">
            <Github size={20} />
          </a>
          <button className="hidden md:block bg-bg-secondary border-[1.5px] border-border text-text-primary font-mono text-[14px] font-medium px-4 py-1.5 rounded-full cursor-pointer hover:bg-[#E8E8DC] transition-colors duration-200">
            Get Started
          </button>
        </div>
      </motion.div>
    </nav>
  );
}
