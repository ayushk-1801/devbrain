import { Github, Sun, Moon } from 'lucide-react';
import { motion, useScroll, useTransform } from 'motion/react';
import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Logo } from './ui/Logo';

export function Navbar() {
  const { scrollY } = useScroll();
  const location = useLocation();
  const isVisualizePage = location.pathname === '/visualize';

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
  const borderRadius = useTransform(scrollY, [0, 200], [0, 16]); // Matches visualize page's rounded-2xl (16px)

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 flex justify-center pointer-events-none">
      <motion.div 
        style={{
          height,
          width,
          maxWidth,
          top,
          borderRadius,
          background: scrolled 
            ? 'color-mix(in srgb, var(--color-bg-card) 80%, transparent)' 
            : 'var(--color-bg)',
          borderColor: scrolled 
            ? 'color-mix(in srgb, var(--color-border) 30%, transparent)' 
            : 'transparent',
          boxShadow: scrolled 
            ? '0 8px 32px rgba(0,0,0,0.06)' 
            : 'none',
        }}
        className={`w-full pointer-events-auto flex items-center justify-between relative border px-6 md:px-7 transition-all duration-300 ${
          scrolled ? 'backdrop-blur-xl' : 'backdrop-blur-none'
        }`}
      >
        {/* Left */}
        <Link to="/" className="flex items-center shrink-0 cursor-pointer">
          <Logo />
        </Link>

        {/* Center - desktop only */}
        {isVisualizePage ? (
          <div className="hidden md:flex items-center gap-6">
            <Link to="/" className="font-mono text-[14px] md:text-[15px] font-medium text-text-primary hover:underline underline-offset-4 decoration-1">
              ← Home
            </Link>
          </div>
        ) : (
          <div className="hidden md:flex items-center gap-6">
            {['About', 'Features', 'Use Cases'].map(item => (
              <a key={item} href={`#${item.toLowerCase().replace(/ /g, '-')}`} className="font-mono text-[14px] md:text-[15px] font-medium text-text-primary hover:underline underline-offset-4 decoration-1">
                {item}
              </a>
            ))}
            <Link to="/visualize" className="font-mono text-[14px] md:text-[15px] font-medium text-text-primary hover:underline underline-offset-4 decoration-1">
              Visualize
            </Link>
          </div>
        )}

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
          <button className="hidden md:block bg-bg-secondary border-[1.5px] border-border text-text-primary font-mono text-[14px] font-medium px-4 py-1.5 rounded-full cursor-pointer hover:bg-text-primary hover:text-bg hover:border-text-primary transition-colors duration-200">
            Get Started
          </button>
        </div>
      </motion.div>
    </nav>
  );
}
