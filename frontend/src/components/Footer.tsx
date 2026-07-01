import { useState } from 'react';
import { Copy, Check } from 'lucide-react';
import { motion } from 'motion/react';

export function Footer() {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText("docker-compose up");
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <footer 
      style={{
        background: 'radial-gradient(circle at 10% 20%, rgba(216, 240, 228, 0.25) 0%, transparent 60%), radial-gradient(circle at 90% 80%, rgba(255, 221, 248, 0.25) 0%, transparent 60%)'
      }}
      className="w-full flex flex-col mt-20 relative bg-bg"
    >
      {/* Top Wave */}
      <div className="w-full overflow-hidden h-[120px] absolute top-0 left-0 right-0 transform -translate-y-[119px] pointer-events-none">
        <svg viewBox="0 0 1440 120" preserveAspectRatio="none" className="w-full h-full">
          <defs>
            <linearGradient id="wave-top" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="var(--color-accent-mint)" />
              <stop offset="35%" stopColor="var(--color-accent-mint)" stopOpacity="0" />
              <stop offset="65%" stopColor="var(--color-accent-peach)" stopOpacity="0" />
              <stop offset="100%" stopColor="var(--color-accent-peach)" />
            </linearGradient>
          </defs>
          <path d="M0,60 C360,120 360,0 720,60 C1080,120 1080,0 1440,60 L1440,120 L0,120 Z" fill="url(#wave-top)" fillOpacity="0.5" />
          <path d="M0,60 C360,120 360,0 720,60 C1080,120 1080,0 1440,60" fill="none" stroke="var(--color-text-primary)" strokeWidth="1" />
        </svg>
      </div>

      {/* CTA Content */}
      <div className="w-full flex flex-col items-center justify-center pt-8 pb-16 px-6 z-10 bg-transparent">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-text-primary mb-8">
          <circle cx="8" cy="12" r="4" />
          <circle cx="16" cy="12" r="4" />
          <line x1="12" y1="12" x2="16" y2="12" />
        </svg>

        <h2 className="font-display text-[40px] md:text-[56px] font-black text-text-primary leading-[1.1] max-w-[720px] text-center tracking-tight">
          Build AI agents that actually<br />understand your codebase.
        </h2>

        <p className="font-display text-[16px] md:text-[17px] text-text-muted max-w-[520px] mt-6 text-center leading-[1.6]">
          One Docker command. Any GitHub repo.<br />Connects to Claude Code in under 5 minutes.
        </p>

        <button className="bg-btn-dark text-btn-dark-text font-mono text-[14px] md:text-[15px] font-medium px-[32px] py-[16px] rounded-full transition-[background-color,box-shadow] duration-200 cursor-pointer mt-10 hover:bg-[#3a3836]">
          Deploy with Docker
        </button>

        <div className="mt-8 bg-bg-card border-[1.5px] border-[rgba(4,2,0,0.12)] rounded-[16px] px-[32px] py-[20px] inline-flex items-center gap-4 hover:border-[rgba(4,2,0,0.24)] transition-colors group">
          <span className="font-mono text-[15px] text-text-primary">docker-compose up</span>
          <button 
            onClick={handleCopy} 
            className="text-text-muted group-hover:text-text-primary transition-colors cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-border rounded"
            aria-label="Copy docker command"
          >
            {copied ? <Check size={16} /> : <Copy size={16} />}
          </button>
        </div>
      </div>

      {/* Bottom Wave */}
      <div className="w-full overflow-hidden h-[120px] pointer-events-none">
        <svg viewBox="0 0 1440 120" preserveAspectRatio="none" className="w-full h-full">
          <defs>
            <linearGradient id="wave-bot" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="var(--color-accent-sage)" />
              <stop offset="35%" stopColor="var(--color-accent-sage)" stopOpacity="0" />
              <stop offset="65%" stopColor="var(--color-accent-orchid)" stopOpacity="0" />
              <stop offset="100%" stopColor="var(--color-accent-orchid)" />
            </linearGradient>
          </defs>
          <path d="M0,60 C360,0 360,120 720,60 C1080,0 1080,120 1440,60 L1440,0 L0,0 Z" fill="url(#wave-bot)" fillOpacity="0.5" />
          <path d="M0,60 C360,0 360,120 720,60 C1080,0 1080,120 1440,60" fill="none" stroke="var(--color-text-primary)" strokeWidth="1" />
        </svg>
      </div>

      {/* Footer Bar */}
      <div className="w-full border-t border-[rgba(4,2,0,0.1)] px-[24px] md:px-[48px] py-[24px] flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="font-mono text-[13px] text-text-muted">
          © 2026 DevBrain
        </div>
        <div className="flex items-center gap-[24px]">
          <a href="#" className="font-mono text-[13px] text-text-muted hover:text-text-primary hover:underline underline-offset-4 decoration-1">Terms</a>
          <a href="#" className="font-mono text-[13px] text-text-muted hover:text-text-primary hover:underline underline-offset-4 decoration-1">GitHub</a>
          <a href="#" className="font-mono text-[13px] text-text-muted hover:text-text-primary hover:underline underline-offset-4 decoration-1">Docs</a>
        </div>
      </div>
    </footer>
  );
}
