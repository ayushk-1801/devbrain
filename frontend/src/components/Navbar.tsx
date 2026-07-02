import { Github, Sun, Moon } from 'lucide-react';
import { motion, useScroll, useTransform } from 'motion/react';
import { useState, useEffect } from 'react';

export function Navbar() {
  const { scrollY } = useScroll();

  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('theme');
      if (saved === 'light' || saved === 'dark') return saved;
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return 'light';
  });

  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    localStorage.setItem('theme', theme);
  }, [theme]);

  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    return scrollY.onChange((latest) => {
      setScrolled(latest > 50);
    });
  }, [scrollY]);

  // Morph values continuously based on scrollY (0px to 200px scroll range)
  const height = useTransform(scrollY, [0, 200], [70, 54]);
  const width = useTransform(scrollY, [0, 200], ["100%", "90%"]);
  const maxWidth = useTransform(scrollY, [0, 200], [2560, 1024]); // increased to 1024 to prevent squishing
  const top = useTransform(scrollY, [0, 200], [0, 16]);
  const borderRadius = useTransform(scrollY, [0, 200], [0, 27]); // half of height 54 is 27px (perfect pill shape)

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 flex justify-center pointer-events-none">
      <motion.div 
        style={{
          height,
          width,
          maxWidth,
          top,
          borderRadius
        }}
        className={`w-full pointer-events-auto flex items-center justify-between relative backdrop-blur-md border px-6 md:px-7 transition-all duration-300 ${
          scrolled 
            ? 'bg-bg/85 border-border/8 shadow-[0_4px_16px_rgba(4,2,0,0.02)] dark:shadow-[0_4px_16px_rgba(0,0,0,0.1)]' 
            : 'bg-bg border-transparent shadow-none'
        }`}
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
          <button 
            onClick={() => setTheme(t => t === 'light' ? 'dark' : 'light')}
            className="text-text-muted hover:text-text-primary transition-colors cursor-pointer outline-none p-1.5 rounded-full hover:bg-bg-secondary"
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
          </button>
          <a href="https://github.com/ayushk-1801/devbrain" target="_blank" rel="noopener noreferrer" aria-label="GitHub Repository" className="flex items-center gap-2 text-text-muted hover:text-text-primary transition-colors">
            <Github size={20} />
          </a>
          <button className="hidden md:block bg-bg-secondary border-[1.5px] border-border text-text-primary font-mono text-[14px] font-medium px-4 py-1.5 rounded-full cursor-pointer hover:bg-[#000000] hover:text-white hover:border-[#000000] transition-colors duration-200 dark:hover:bg-[#FFFFFF] dark:hover:text-black dark:hover:border-[#FFFFFF]">
            Get Started
          </button>
        </div>
      </motion.div>
    </nav>
  );
}
