import { Github, Sun, Moon, Menu, X } from 'lucide-react';
import { motion, useScroll, useTransform, AnimatePresence } from 'motion/react';
import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Logo } from './ui/Logo';

export function Navbar() {
  const { scrollY } = useScroll();
  const location = useLocation();
  const isVisualizePage = location.pathname === '/visualize';

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

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
    <nav className="fixed top-0 left-0 right-0 z-50 flex flex-col items-center justify-center pointer-events-none">
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
        className={`w-full pointer-events-auto flex items-center justify-between relative border px-6 md:px-7 transition-[background-color,border-color,box-shadow] duration-300 ${
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
            <Link to="/" className="text-[14px] md:text-[15px] font-medium text-text-primary hover:underline underline-offset-4 decoration-1">
              ← Home
            </Link>
          </div>
        ) : (
          <div className="hidden md:flex items-center gap-6">
            {['About', 'Features', 'Use Cases'].map(item => (
              <a key={item} href={`#${item.toLowerCase().replace(/ /g, '-')}`} className="text-[14px] md:text-[15px] font-medium text-text-primary hover:underline underline-offset-4 decoration-1">
                {item}
              </a>
            ))}
            <Link to="/visualize" className="text-[14px] md:text-[15px] font-medium text-text-primary hover:underline underline-offset-4 decoration-1">
              Visualize
            </Link>
            <Link to="/docs" className="text-[14px] md:text-[15px] font-medium text-text-primary hover:underline underline-offset-4 decoration-1">
              Docs
            </Link>
          </div>
        )}

        {/* Right */}
        <div className="flex items-center gap-4">
          <button 
            onClick={() => setTheme(t => t === 'light' ? 'dark' : 'light')}
            className="text-text-muted hover:text-text-primary transition-colors cursor-pointer outline-none p-1.5 rounded-full"
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
          </button>
          <a href="https://github.com/ayushk-1801/devbrain" target="_blank" rel="noopener noreferrer" aria-label="GitHub Repository" className="flex items-center gap-2 text-text-muted hover:text-text-primary transition-colors">
            <Github size={20} />
          </a>
          <button className="hidden md:block bg-bg-secondary border-[1.5px] border-border text-text-primary text-[14px] font-medium px-4 py-1.5 rounded-full cursor-pointer hover:bg-text-primary hover:text-bg hover:border-text-primary transition-colors duration-200">
            Get Started
          </button>
          {/* Mobile menu toggle */}
          <button 
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden text-text-primary p-1.5 focus:outline-none hover:bg-bg-secondary rounded-full cursor-pointer"
            aria-label="Toggle mobile menu"
          >
            {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </motion.div>

      {/* Mobile Menu Dropdown */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
            className="w-[90%] md:hidden bg-bg-card border border-border-soft rounded-[20px] p-5 flex flex-col gap-3.5 shadow-[0_12px_32px_rgba(0,0,0,0.08)] pointer-events-auto z-40 mt-3.5 backdrop-blur-md"
          >
            {isVisualizePage ? (
              <Link 
                to="/" 
                onClick={() => setMobileMenuOpen(false)}
                className="text-[15px] font-medium text-text-primary py-1.5 border-b border-border-soft/60"
              >
                ← Home
              </Link>
            ) : (
              <>
                {['About', 'Features', 'Use Cases'].map(item => (
                  <a 
                    key={item} 
                    href={`#${item.toLowerCase().replace(/ /g, '-')}`}
                    onClick={() => setMobileMenuOpen(false)}
                    className="text-[15px] font-medium text-text-primary py-1.5 border-b border-border-soft/60"
                  >
                    {item}
                  </a>
                ))}
                <Link 
                  to="/visualize" 
                  onClick={() => setMobileMenuOpen(false)}
                  className="text-[15px] font-medium text-text-primary py-1.5 border-b border-border-soft/60"
                >
                  Visualize
                </Link>
                <Link 
                  to="/docs" 
                  onClick={() => setMobileMenuOpen(false)}
                  className="text-[15px] font-medium text-text-primary py-1.5 border-b border-border-soft/60"
                >
                  Docs
                </Link>
              </>
            )}
            <button className="w-full bg-btn-dark text-btn-dark-text text-[14px] font-medium py-3 rounded-full mt-2 cursor-pointer hover:bg-btn-dark-hover">
              Get Started
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
}
