import React, { useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import { Copy, Check } from 'lucide-react';
import { motion, useMotionValue, useReducedMotion, useSpring, useTransform, useScroll } from 'motion/react';
import { Logo } from './ui/Logo';

const VIEWBOX_WIDTH = 1410;

function SiteFooterInteractiveLogotype() {
  const shouldReduceMotion = useReducedMotion();

  const gradientX1Raw = useMotionValue(0.5);
  const gradientX1 = useSpring(
    useTransform(gradientX1Raw, [0, 1], [0, VIEWBOX_WIDTH]),
    {
      stiffness: 150,
      damping: 25,
    }
  );

  const handleMouseMove = (event: React.MouseEvent<HTMLDivElement>) => {
    if (shouldReduceMotion) return;

    const containerRect = event.currentTarget.getBoundingClientRect();
    gradientX1Raw.set(
      (event.clientX - containerRect.left) / containerRect.width
    );
  };

  const handleMouseLeave = () => {
    if (shouldReduceMotion) return;
    gradientX1Raw.set(0.5);
  };

  return (
    <div className="relative w-full">
      <div
        className="overflow-hidden"
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
      >
        <div className="flex w-full translate-y-[20%] items-center justify-center">
          <svg
            className="w-full max-w-[1410px] h-auto"
            viewBox="0 0 1410 258"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              fillRule="evenodd"
              clipRule="evenodd"
              d="M1 1H97V33H33V225H97V257H1V1ZM129 193V225H97V193H129ZM129 65H161V193H129V65ZM129 65V33H97V65H129ZM193 65H353V161H225V225H353V257H193V65ZM225 97H321V129H225V97ZM385 65H417V193H449V225H481V193H513V65H545V193H513V225H481V257H449V225H417V193H385V65ZM577 1H705V33H737V113H705V145H737V225H705V257H577V1ZM609 33H705V113H609V33ZM609 145H705V225H609V145ZM769 65H929V129H897V97H801V257H769V65ZM993 65H1121V257H1089V225H1057V193H1089V97H993V65ZM993 225H961V97H993V225ZM993 225V257H1057V225H993ZM1185 1H1217V33H1185V1ZM1249 65H1377V97H1281V257H1249V65ZM1377 97H1409V257H1377V97Z"
              fill="url(#paint0_linear_1145_73)"
            />
            <path
              d="M1153 65V97H1185V257H1217V65H1153Z"
              fill="url(#paint0_linear_1145_73)"
            />
            <path
              stroke="var(--color-text-primary)"
              strokeOpacity={0.1}
              d="M97 33V1H1V257H97V225M97 33H33V225H97M97 33H129V65M97 33V65H129M97 225H129V193M97 225V193H129M129 193H161V65H129M129 193V65M193 65H353V161H225V225H353V257H193V65ZM225 97H321V129H225V97ZM385 65H417V193H449V225H481V193H513V65H545V193H513V225H481V257H449V225H417V193H385V65ZM577 1H705V33H737V113H705V145H737V225H705V257H577V1ZM609 33H705V113H609V33ZM609 145H705V225H609V145ZM769 65H929V129H897V97H801V257H769V65ZM1057 225H1089V257H1121V65H993V97M1057 225V193H1089V97H993M1057 225V257H993V225M1057 225H993M993 97H961V225H993M993 97V225M1185 1H1217V33H1185V1ZM1153 65V97H1185V257H1217V65H1153ZM1377 97V65H1249V257H1281V97H1377ZM1377 97H1409V257H1377V97Z"
              strokeWidth="2"
            />
            <defs>
              <motion.linearGradient
                id="paint0_linear_1145_73"
                x1={gradientX1}
                y1="1"
                x2="705"
                y2="350"
                gradientUnits="userSpaceOnUse"
              >
                <stop
                  offset="0.625"
                  stopColor="var(--color-text-primary)"
                  stopOpacity="0"
                />
                <stop offset="1" stopColor="var(--color-text-primary)" />
              </motion.linearGradient>
            </defs>
          </svg>
        </div>
      </div>
    </div>
  );
}

const agents = [
  {
    name: "Claude Code",
    bg: "bg-white",
    borderColor: "border-[rgba(4,2,0,0.08)]",
    shadowColor: "hover:shadow-[0_12px_28px_rgba(4,2,0,0.08)]",
    position: "top-[6%] left-[12%] lg:left-[25%]",
    dx: -60,
    dy: -40,
    logo: (
      <img src="/claude-ai.svg" alt="Claude Code" className="w-7 h-7 sm:w-9 sm:h-9 lg:w-11 lg:h-11 object-contain select-none" />
    )
  },
  {
    name: "Cursor",
    bg: "bg-white",
    borderColor: "border-[rgba(4,2,0,0.08)]",
    shadowColor: "hover:shadow-[0_12px_28px_rgba(4,2,0,0.08)]",
    position: "top-[12%] right-[10%] lg:right-[20%]",
    dx: 60,
    dy: -30,
    logo: (
      <img src="/cursor.png" alt="Cursor" className="w-7 h-7 sm:w-9 sm:h-9 lg:w-11 lg:h-11 object-contain select-none" />
    )
  },
  {
    name: "GitHub Copilot",
    bg: "bg-white",
    borderColor: "border-[rgba(4,2,0,0.08)]",
    shadowColor: "hover:shadow-[0_12px_28px_rgba(4,2,0,0.08)]",
    position: "top-[22%] left-[6%] lg:left-[16%]",
    dx: -80,
    dy: -10,
    logo: (
      <img src="/github-copilot-removebg-preview.png" alt="GitHub Copilot" className="w-7 h-7 sm:w-9 sm:h-9 lg:w-11 lg:h-11 object-contain select-none" />
    )
  },
  {
    name: "Antigravity",
    bg: "bg-white",
    borderColor: "border-[rgba(4,2,0,0.08)]",
    shadowColor: "hover:shadow-[0_12px_28px_rgba(4,2,0,0.08)]",
    position: "top-[44%] left-[10%] lg:left-[22%]",
    dx: -60,
    dy: 10,
    logo: (
      <img src="/google-antigravity.png" alt="Antigravity" className="w-7 h-7 sm:w-9 sm:h-9 lg:w-11 lg:h-11 object-contain select-none" />
    )
  },
  {
    name: "Zed",
    bg: "bg-white",
    borderColor: "border-[rgba(4,2,0,0.08)]",
    shadowColor: "hover:shadow-[0_12px_28px_rgba(4,2,0,0.08)]",
    position: "top-[34%] right-[6%] lg:right-[15%]",
    dx: 70,
    dy: -10,
    logo: (
      <img src="/Zed_Editor_Logo.png" alt="Zed" className="w-7 h-7 sm:w-9 sm:h-9 lg:w-11 lg:h-11 object-contain select-none" />
    )
  },
  {
    name: "OpenAI Codex",
    bg: "bg-white",
    borderColor: "border-[rgba(4,2,0,0.08)]",
    shadowColor: "hover:shadow-[0_12px_28px_rgba(4,2,0,0.08)]",
    position: "top-[56%] right-[12%] lg:right-[22%]",
    dx: 50,
    dy: 20,
    logo: (
      <img src="/codex-color-removebg-preview.png" alt="OpenAI Codex" className="w-7 h-7 sm:w-9 sm:h-9 lg:w-11 lg:h-11 object-contain select-none" />
    )
  },
  {
    name: "n8n",
    bg: "bg-white",
    borderColor: "border-[rgba(4,2,0,0.08)]",
    shadowColor: "hover:shadow-[0_12px_28px_rgba(4,2,0,0.08)]",
    position: "top-[68%] left-[6%] lg:left-[14%]",
    dx: -70,
    dy: 40,
    logo: (
      <img src="/n8n-icon.webp" alt="n8n" className="w-7 h-7 sm:w-9 sm:h-9 lg:w-11 lg:h-11 object-contain select-none" />
    )
  },
  {
    name: "OpenCode",
    bg: "bg-white",
    borderColor: "border-[rgba(4,2,0,0.08)]",
    shadowColor: "hover:shadow-[0_12px_28px_rgba(4,2,0,0.08)]",
    position: "top-[80%] left-[15%] lg:left-[25%]",
    dx: -50,
    dy: 60,
    logo: (
      <img src="/opencode-logo-removebg-preview.png" alt="OpenCode" className="w-7 h-7 sm:w-9 sm:h-9 lg:w-11 lg:h-11 object-contain select-none" />
    )
  },

  {
    name: "Windsurf",
    bg: "bg-white",
    borderColor: "border-[rgba(4,2,0,0.08)]",
    shadowColor: "hover:shadow-[0_12px_28px_rgba(4,2,0,0.08)]",
    position: "top-[74%] right-[8%] lg:right-[16%]",
    dx: 70,
    dy: 40,
    logo: (
      <img src="/images-removebg-preview.png" alt="Windsurf" className="w-7 h-7 sm:w-9 sm:h-9 lg:w-11 lg:h-11 object-contain select-none" />
    )
  },
  {
    name: "Aider",
    bg: "bg-white",
    borderColor: "border-[rgba(4,2,0,0.08)]",
    shadowColor: "hover:shadow-[0_12px_28px_rgba(4,2,0,0.08)]",
    position: "top-[72%] right-[24%] lg:right-[32%]",
    dx: 50,
    dy: 60,
    logo: (
      <img src="/images12-removebg-preview.png" alt="Aider" className="w-7 h-7 sm:w-9 sm:h-9 lg:w-11 lg:h-11 object-contain select-none" />
    )
  }
];

function AgentIcon({ agent, progress }: { agent: typeof agents[0]; progress: any; key?: any }) {
  const x = useTransform(progress, [0, 1], [0, agent.dx * (typeof window !== 'undefined' && window.innerWidth < 1024 ? 0.35 : 1)]);
  const y = useTransform(progress, [0, 1], [0, agent.dy * (typeof window !== 'undefined' && window.innerWidth < 1024 ? 0.35 : 1)]);

  return (
    <motion.div
      style={{ x, y }}
      whileHover={{ scale: 1.1, rotate: Math.random() > 0.5 ? 3 : -3 }}
      className={`absolute pointer-events-auto ${agent.position} w-12 h-12 sm:w-16 sm:h-16 lg:w-20 lg:h-20 rounded-[14px] sm:rounded-[18px] lg:rounded-[24px] ${agent.bg} border border-border-soft flex items-center justify-center cursor-pointer transition-[box-shadow,border-color] duration-300 shadow-sm ${agent.shadowColor}`}
      title={agent.name}
    >
      {agent.logo}
    </motion.div>
  );
}

export function Footer() {
  const [copied, setCopied] = useState(false);
  const footerRef = useRef<HTMLElement>(null);
  const ctaRef = useRef<HTMLDivElement>(null);

  const { scrollYProgress } = useScroll({
    target: ctaRef,
    offset: ["start end", "center center"]
  });

  const handleCopy = () => {
    navigator.clipboard.writeText("docker-compose up");
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <footer 
      ref={footerRef}
      className="w-screen flex flex-col mt-20 relative bg-bg left-1/2 -translate-x-1/2"
    >
      {/* Top Ribbon Wave */}
      <div className="w-full h-[160px] absolute top-0 left-0 right-0 transform -translate-y-[159px] pointer-events-none">
        <svg viewBox="0 0 1440 160" preserveAspectRatio="none" className="w-full h-full">
          <defs>
            <linearGradient id="wave-top" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="var(--color-accent-mint)" />
              <stop offset="50%" stopColor="var(--color-accent-yellow)" />
              <stop offset="100%" stopColor="var(--color-accent-sage)" />
            </linearGradient>
            <filter id="glow-filter" filterUnits="userSpaceOnUse" x="0" y="0" width="1440" height="160">
              <feGaussianBlur stdDeviation="3" />
            </filter>
          </defs>
          {/* Blurred Glowing Ribbon */}
          <path 
            d="M 0 50 L 300 50 C 380 50, 420 120, 500 120 L 940 120 C 1020 120, 1060 50, 1140 50 L 1440 50" 
            fill="none" 
            stroke="url(#wave-top)" 
            strokeWidth="40" 
            strokeOpacity="0.85" 
            filter="url(#glow-filter)" 
          />
          {/* Crisp 1px Overlay Line */}
          <path 
            d="M 0 50 L 300 50 C 380 50, 420 120, 500 120 L 940 120 C 1020 120, 1060 50, 1140 50 L 1440 50" 
            fill="none" 
            stroke="#040200" 
            strokeWidth="1.2" 
            strokeOpacity="0.8"
          />
        </svg>
      </div>

      {/* CTA Content */}
      <div ref={ctaRef} className="w-full relative flex flex-col items-center justify-center pt-24 pb-28 px-6 z-10 bg-transparent max-w-[1200px] mx-auto overflow-visible min-h-[520px]">
        {/* Scattered Agent Logos (Mobile & Desktop) - Constrained between ribbons vertically, but spans full viewport width */}
        <div className="absolute inset-y-0 w-screen left-1/2 -translate-x-1/2 pointer-events-none z-0 overflow-hidden">
          {agents.map((agent, index) => (
            <AgentIcon key={index} agent={agent} progress={scrollYProgress} />
          ))}
        </div>

        <Logo className="h-6 w-auto text-text-primary mb-8" />

        <h2 className="font-display text-[32px] sm:text-[40px] md:text-[56px] font-black text-text-primary leading-[1.1] max-w-[720px] text-center tracking-tight">
          Build AI agents that actually<br className="hidden sm:inline" /> understand your codebase.
        </h2>

        <p className="font-display text-[16px] md:text-[17px] text-text-muted max-w-[520px] mt-6 text-center leading-[1.6]">
          One Docker command. Any GitHub repo.<br />Connects to Claude Code in under 5 minutes.
        </p>

        <button className="bg-btn-dark text-btn-dark-text text-[14px] md:text-[15px] font-medium px-[32px] py-[16px] rounded-full transition-[background-color,box-shadow] duration-200 cursor-pointer mt-10 hover:bg-btn-dark-hover">
          Deploy with Docker
        </button>

        <div className="mt-8 bg-bg-card border-[1.5px] border-[rgba(4,2,0,0.12)] rounded-[16px] px-[32px] py-[20px] inline-flex items-center gap-4 hover:border-[rgba(4,2,0,0.24)] transition-colors group">
          <span className="font-code text-[15px] text-text-primary">docker-compose up</span>
          <button 
            onClick={handleCopy} 
            className="text-text-muted group-hover:text-text-primary transition-colors cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-border rounded"
            aria-label="Copy docker command"
          >
            {copied ? <Check size={16} /> : <Copy size={16} />}
          </button>
        </div>


      </div>

      {/* Bottom Ribbon Wave */}
      <div className="w-full h-[160px] pointer-events-none">
        <svg viewBox="0 0 1440 160" preserveAspectRatio="none" className="w-full h-full">
          <defs>
            <linearGradient id="wave-bot" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="var(--color-accent-blush)" />
              <stop offset="50%" stopColor="var(--color-accent-peach)" />
              <stop offset="100%" stopColor="var(--color-accent-orchid)" />
            </linearGradient>
            <filter id="glow-filter-bot" filterUnits="userSpaceOnUse" x="0" y="0" width="1440" height="160">
              <feGaussianBlur stdDeviation="3" />
            </filter>
          </defs>
          {/* Blurred Glowing Ribbon */}
          <path 
            d="M 0 110 L 300 110 C 380 110, 420 40, 500 40 L 940 40 C 1020 40, 1060 110, 1140 110 L 1440 110" 
            fill="none" 
            stroke="url(#wave-bot)" 
            strokeWidth="40" 
            strokeOpacity="0.85" 
            filter="url(#glow-filter-bot)" 
          />
          {/* Crisp 1px Overlay Line */}
          <path 
            d="M 0 110 L 300 110 C 380 110, 420 40, 500 40 L 940 40 C 1020 40, 1060 110, 1140 110 L 1440 110" 
            fill="none" 
            stroke="#040200" 
            strokeWidth="1.2" 
            strokeOpacity="0.8"
          />
        </svg>
      </div>

      {/* Interactive Logotype */}
      <SiteFooterInteractiveLogotype />

      {/* Footer Bar */}
      <div className="w-full border-t border-[rgba(4,2,0,0.1)] px-[24px] md:px-[48px] py-[24px] flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center justify-center md:justify-start gap-3 flex-1">
          <div className="inline-flex items-center gap-1.5 bg-accent-mint/20 border border-accent-mint/30 px-2 py-0.5 rounded text-[10px] font-bold uppercase font-mono text-text-primary leading-none">
            Open Source
            <span className="text-text-muted font-normal normal-case">MIT</span>
          </div>
        </div>
        <span className="text-[13px] text-text-muted">
          © 2026 DevBrain
        </span>
        <div className="flex items-center justify-center md:justify-end gap-[24px] flex-1">
          <a href="https://github.com/ayushk-1801/devbrain" className="text-[13px] text-text-muted hover:text-text-primary hover:underline underline-offset-4 decoration-1">GitHub</a>
          <Link to="/docs" className="text-[13px] text-text-muted hover:text-text-primary hover:underline underline-offset-4 decoration-1">Docs</Link>
        </div>
      </div>
    </footer>
  );
}
