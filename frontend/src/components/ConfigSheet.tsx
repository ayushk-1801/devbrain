import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Copy, Check, X, ExternalLink, Info, BookOpen, Link2 } from 'lucide-react';
import { type Instance } from './InstanceCard';

interface ConfigSheetProps {
  instance: Instance;
  onClose: () => void;
}

const AGENTS = [
  {
    id: 'claude',
    name: 'Claude Code',
    icon: '/claude-ai.svg',
    description: {
      python: '1. Ensure Claude Code is installed globally (npm install -g @anthropic-ai/claude-code).\n2. Open your project folder in your terminal.\n3. Run the command below to register DevBrain as a local Python MCP server:',
      docker: '1. Ensure Claude Code is installed globally (npm install -g @anthropic-ai/claude-code).\n2. Make sure Docker is running on your machine.\n3. Run the command below to register DevBrain as a containerized Docker MCP server:'
    },
    copyText: (url: string, runMode: 'python' | 'docker') => 
      runMode === 'python'
        ? `claude mcp add devbrain -s project -e DEVBRAIN_API_URL="${url}" -- python -m backend.mcp_server`
        : `claude mcp add devbrain -s project -- docker run -i --rm -e DEVBRAIN_API_URL="${url}" devbrain-mcp`,
    mode: 'shell',
  },
  {
    id: 'codex',
    name: 'Codex',
    icon: '/codex-color-removebg-preview.png',
    description: {
      python: '1. Open or create your Codex configuration file at ~/.codex/config.toml.\n2. Locate the [mcp_servers] parent section.\n3. Append the following TOML configuration block to enable DevBrain via local Python:',
      docker: '1. Make sure Docker is running on your machine.\n2. Open your Codex config at ~/.codex/config.toml.\n3. Append the following TOML block to run DevBrain containerized via Docker:'
    },
    copyText: (url: string, runMode: 'python' | 'docker') => 
      runMode === 'python'
        ? `[mcp_servers.devbrain]\ncommand = "python"\nargs = ["-m", "backend.mcp_server"]\nenv = { "DEVBRAIN_API_URL" = "${url}" }`
        : `[mcp_servers.devbrain]\ncommand = "docker"\nargs = ["run", "-i", "--rm", "-e", "DEVBRAIN_API_URL=${url}", "devbrain-mcp"]`,
    mode: 'toml',
  },
  {
    id: 'cursor',
    name: 'Cursor',
    icon: '/cursor.png',
    description: {
      python: '1. Open Cursor Settings (click the gear icon in the top right or use shortcut).\n2. Navigate to Features > MCP in the sidebar.\n3. Click "+ Add New MCP Server".\n4. Set Name: "devbrain", Type: "command", and paste the following Python command:',
      docker: '1. Make sure Docker is running on your machine.\n2. Open Cursor Settings and navigate to Features > MCP in the sidebar.\n3. Click "+ Add New MCP Server".\n4. Set Name: "devbrain", Type: "command", and paste the following Docker run command:'
    },
    copyText: (url: string, runMode: 'python' | 'docker') => 
      runMode === 'python'
        ? `python -m backend.mcp_server --api-url "${url}"`
        : `docker run -i --rm -e DEVBRAIN_API_URL="${url}" devbrain-mcp`,
    mode: 'command',
  },
  {
    id: 'zed',
    name: 'Zed Editor',
    icon: '/Zed_Editor_Logo.png',
    description: {
      python: '1. Open your Zed configuration file (Command Palette > "zed: open settings" or Ctrl/Cmd + ,).\n2. Locate the "context_servers" block.\n3. Paste the following JSON server definition inside the context_servers section:',
      docker: '1. Make sure Docker is running on your machine.\n2. Open your Zed settings configuration file.\n3. Locate the "context_servers" block.\n4. Paste the following JSON block to run the server inside Docker:'
    },
    copyText: (url: string, runMode: 'python' | 'docker') => 
      runMode === 'python'
        ? JSON.stringify({
            "devbrain": {
              "command": {
                "path": "python",
                "args": ["-m", "backend.mcp_server"],
                "env": {
                  "DEVBRAIN_API_URL": url
                }
              }
            }
          }, null, 2)
        : JSON.stringify({
            "devbrain": {
              "command": {
                "path": "docker",
                "args": [
                  "run",
                  "-i",
                  "--rm",
                  "-e",
                  `DEVBRAIN_API_URL=${url}`,
                  "devbrain-mcp"
                ]
              }
            }
          }, null, 2),
    mode: 'json',
  },
  {
    id: 'antigravity',
    name: 'Antigravity',
    icon: '/google-antigravity.png',
    description: {
      python: '1. Ensure the Antigravity CLI is installed locally.\n2. Open your project directory in the terminal.\n3. Run the following command to register DevBrain as an MCP server:',
      docker: '1. Ensure the Antigravity CLI is installed and Docker is running.\n2. Open your project directory in the terminal.\n3. Run the command below to connect DevBrain containerized via Docker:'
    },
    copyText: (url: string, runMode: 'python' | 'docker') => 
      runMode === 'python'
        ? `agy mcp add devbrain -e DEVBRAIN_API_URL="${url}" -- python -m backend.mcp_server`
        : `agy mcp add devbrain -- docker run -i --rm -e DEVBRAIN_API_URL="${url}" devbrain-mcp`,
    mode: 'shell',
  },
  {
    id: 'opencode',
    name: 'OpenCode',
    icon: '/opencode-logo-removebg-preview.png',
    description: {
      python: '1. Open your global or project-level opencode.jsonc file.\n2. Locate the "mcp" config key.\n3. Paste the following JSON block under the mcp definition:',
      docker: '1. Make sure Docker is running on your machine.\n2. Open your global or project-level opencode.jsonc file.\n3. Paste the following JSON block under the mcp definition to connect DevBrain via Docker:'
    },
    copyText: (url: string, runMode: 'python' | 'docker') => 
      runMode === 'python'
        ? JSON.stringify({
            "devbrain": {
              "type": "local",
              "command": ["python", "-m", "backend.mcp_server"],
              "enabled": true,
              "environment": {
                "DEVBRAIN_API_URL": url
              }
            }
          }, null, 2)
        : JSON.stringify({
            "devbrain": {
              "type": "local",
              "command": [
                "docker",
                "run",
                "-i",
                "--rm",
                "-e",
                `DEVBRAIN_API_URL=${url}`,
                "devbrain-mcp"
              ],
              "enabled": true
            }
          }, null, 2),
    mode: 'json',
  }
];

const RUN_MODES = [
  {
    id: 'python',
    name: 'Python',
    icon: 'https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg',
    description: 'Local Python execution'
  },
  {
    id: 'docker',
    name: 'Docker',
    icon: 'https://cdn.simpleicons.org/docker/2496ED',
    description: 'Containerized execution'
  }
] as const;

function CopyButton({ text, label = 'Copy', compact = false, iconOnly = false }: { text: string; label?: string; compact?: boolean; iconOnly?: boolean }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
    }
  };

  return (
    <motion.button
      whileHover={{ scale: 1.04 }}
      whileTap={{ scale: 0.96 }}
      onClick={handleCopy}
      className={`flex items-center justify-center transition-all rounded-lg cursor-pointer text-[10px] ${
        iconOnly
          ? 'p-2 border border-border-soft bg-bg text-text-muted hover:text-text-primary hover:bg-bg-secondary hover:shadow-xs'
          : compact
            ? 'px-2 py-0.5 text-text-muted hover:text-text-primary text-[9.5px]'
            : 'px-3 py-1 text-text-muted hover:text-text-primary hover:bg-bg-secondary border border-border-soft/60'
      }`}
      title={label}
    >
      <AnimatePresence mode="wait" initial={false}>
        {copied ? (
          <motion.span
            key="check"
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.8, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="flex items-center gap-1 font-bold text-text-primary"
          >
            <Check size={11} />
            {!iconOnly && 'Copied'}
          </motion.span>
        ) : (
          <motion.span
            key="copy"
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.8, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="flex items-center gap-1"
          >
            <Copy size={11} />
            {!iconOnly && label}
          </motion.span>
        )}
      </AnimatePresence>
    </motion.button>
  );
}

function HighlightedCode({ code, mode }: { code: string; mode: string }) {
  if (mode === 'json') {
    const tokens = code.split(/(".*?"|[{}[\]:,]|\d+|true|false)/g);
    return (
      <>
        {tokens.map((token, i) => {
          if (token.startsWith('"') && token.endsWith('"')) {
            let isKey = false;
            for (let j = i + 1; j < tokens.length; j++) {
              const nextT = tokens[j];
              if (nextT === '') continue;
              if (nextT.trim() === '') continue;
              if (nextT === ':') {
                isKey = true;
              }
              break;
            }
            if (isKey) {
              return <span key={i} className="text-[#3b82f6] dark:text-[#60a5fa] font-semibold">{token}</span>;
            }
            return <span key={i} className="text-[#ea580c] dark:text-[#f97316]">{token}</span>;
          }
          if (token === 'true' || token === 'false') {
            return <span key={i} className="text-[#8b5cf6] dark:text-[#a78bfa] font-semibold">{token}</span>;
          }
          if (['{', '}', '[', ']', ':', ','].includes(token)) {
            return <span key={i} className="text-text-muted opacity-80">{token}</span>;
          }
          return <span key={i}>{token}</span>;
        })}
      </>
    );
  }

  if (mode === 'toml') {
    const lines = code.split('\n');
    return (
      <>
        {lines.map((line, i) => {
          if (line.trim().startsWith('[') && line.trim().endsWith(']')) {
            return <div key={i} className="text-[#8b5cf6] dark:text-[#a78bfa] font-semibold">{line}</div>;
          }
          const parts = line.split(/(=)/);
          if (parts.length >= 3) {
            const key = parts[0];
            const eq = parts[1];
            const val = parts.slice(2).join('');
            
            const highlightedKey = <span className="text-[#3b82f6] dark:text-[#60a5fa] font-semibold">{key}</span>;
            
            const valTokens = val.split(/(".*?"|[{}[\]]|\d+|true|false)/g);
            const highlightedVal = valTokens.map((token, j) => {
              if (token.startsWith('"') && token.endsWith('"')) {
                return <span key={j} className="text-[#ea580c] dark:text-[#f97316]">{token}</span>;
              }
              if (['{', '}', '[', ']'].includes(token)) {
                return <span key={j} className="text-text-muted opacity-80">{token}</span>;
              }
              return <span key={j}>{token}</span>;
            });

            return (
              <div key={i}>
                {highlightedKey}
                <span className="text-text-muted mx-1">{eq}</span>
                {highlightedVal}
              </div>
            );
          }
          return <div key={i}>{line}</div>;
        })}
      </>
    );
  }

  if (mode === 'shell') {
    const tokens = code.split(/(claude|agy|python|pip|-s|-e|--|DEVBRAIN_API_URL=|\".*?\")/g);
    return (
      <>
        {tokens.map((token, i) => {
          if (['claude', 'agy', 'python', 'pip'].includes(token)) {
            return <span key={i} className="text-[#3b82f6] dark:text-[#60a5fa] font-semibold">{token}</span>;
          }
          if (['-s', '-e', '--'].includes(token)) {
            return <span key={i} className="text-[#0891b2] dark:text-[#22d3ee] font-semibold">{token}</span>;
          }
          if (token === 'DEVBRAIN_API_URL=') {
            return <span key={i} className="text-[#8b5cf6] dark:text-[#a78bfa] font-semibold">{token}</span>;
          }
          if (token.startsWith('"') && token.endsWith('"')) {
            return <span key={i} className="text-[#ea580c] dark:text-[#f97316]">{token}</span>;
          }
          return <span key={i}>{token}</span>;
        })}
      </>
    );
  }

  return <>{code}</>;
}

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.06,
      delayChildren: 0.04,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 12 },
  show: {
    opacity: 1,
    y: 0,
    transition: {
      type: 'spring',
      damping: 24,
      stiffness: 240,
    },
  },
};

export default function ConfigSheet({ instance, onClose }: ConfigSheetProps) {
  const [selectedAgent, setSelectedAgent] = useState(AGENTS[0]);
  const [runMode, setRunMode] = useState<'python' | 'docker'>('python');
  
  const repoName = instance.repo.split('/').pop() ?? instance.repo;

  return (
    <>
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.25, ease: 'easeOut' }}
        onClick={onClose}
        className="fixed inset-0 bg-[#0c0b08]/40 dark:bg-black/60 backdrop-blur-sm z-50 cursor-pointer"
      />

      {/* Slide-out Panel */}
      <motion.div
        initial={{ x: '100%' }}
        animate={{ x: 0 }}
        exit={{ x: '100%' }}
        transition={{ type: 'spring', damping: 32, stiffness: 280, mass: 0.95 }}
        className="fixed right-0 top-0 bottom-0 w-full max-w-[520px] bg-bg-card border-l border-border-soft z-50 shadow-2xl flex flex-col h-screen text-text-primary"
      >
        {/* Header */}
        <div className="p-6 border-b border-border-soft/60 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-bg-secondary rounded-xl text-text-muted border border-border-soft/60">
              <BookOpen size={18} />
            </div>
            <div>
              <h2 className="font-display font-black text-lg leading-tight">Setup Instructions</h2>
              <p className="text-text-muted text-[11px] mt-0.5">Connect DevBrain to your AI coding agents</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-bg-secondary rounded-lg text-text-muted hover:text-text-primary transition-all duration-150 cursor-pointer"
          >
            <X size={18} />
          </button>
        </div>

        {/* Scrollable Body */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="show"
          className="flex-1 overflow-y-auto p-6 space-y-6"
        >
          {/* Repository/Instance Summary card */}
          <motion.div
            variants={itemVariants}
            className="bg-bg-secondary rounded-xl border border-border-soft/80 p-4 space-y-3"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[12px] font-bold text-text-inactive">Current Instance</p>
                <h3 className="font-display font-bold text-base mt-0.5 text-text-primary">{repoName}</h3>
              </div>
              {(() => {
                const status = instance.status;
                const badgeConfig = {
                  running: {
                    label: 'Running',
                    bg: 'bg-[#D8F0E4]',
                    textColor: 'text-[#065f46]',
                    dot: 'bg-[#10b981]',
                    pulse: true,
                  },
                  pending: {
                    label: 'Pending',
                    bg: 'bg-[#FEF9C3]',
                    textColor: 'text-[#713f12]',
                    dot: 'bg-[#eab308]',
                    pulse: true,
                  },
                  error: {
                    label: 'Error',
                    bg: 'bg-[#FEE2E2]',
                    textColor: 'text-[#991b1b]',
                    dot: 'bg-[#ef4444]',
                    pulse: false,
                  },
                  stopped: {
                    label: 'Stopped',
                    bg: 'bg-bg-secondary',
                    textColor: 'text-text-muted',
                    dot: 'bg-text-inactive',
                    pulse: false,
                  }
                }[status] || {
                  label: 'Running',
                  bg: 'bg-[#D8F0E4]',
                  textColor: 'text-[#065f46]',
                  dot: 'bg-[#10b981]',
                  pulse: true,
                };

                return (
                  <div className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold tracking-wide border border-black/5 ${badgeConfig.bg} ${badgeConfig.textColor}`}>
                    <span className={`h-1.5 w-1.5 rounded-full ${badgeConfig.dot} ${badgeConfig.pulse ? 'animate-pulse' : ''}`} />
                    {badgeConfig.label}
                  </div>
                );
              })()}
            </div>

            <div className="pt-2 border-t border-border-soft/40">
              <p className="text-[12px] font-bold text-text-inactive mb-1">API URL</p>
              <div className="flex items-center justify-between gap-2 bg-bg-card border border-border-soft rounded-lg px-2.5 py-1">
                <a
                  href={instance.api_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[10px] font-mono text-text-muted hover:text-text-primary truncate flex items-center gap-1 transition-colors"
                >
                  <Link2 size={10} className="shrink-0 text-text-inactive" />
                  <span className="truncate underline underline-offset-4 decoration-border-soft">{instance.api_url}</span>
                </a>
                <CopyButton text={instance.api_url} label="Copy" compact={true} />
              </div>
            </div>
          </motion.div>

          {/* Select Agent grid */}
          <motion.div variants={itemVariants} className="space-y-2">
            <p className="text-[13px] font-bold text-text-muted">1. Select Coding Agent</p>
            <div className="grid grid-cols-4 gap-2">
              {AGENTS.map((agent) => {
                const isSelected = selectedAgent.id === agent.id;
                return (
                  <motion.button
                    key={agent.id}
                    onClick={() => setSelectedAgent(agent)}
                    whileTap={{ scale: 0.98 }}
                    className={`relative flex flex-col items-center justify-center pt-[18px] pb-[18px] px-2 rounded-xl border transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-bg border-border-soft shadow-xs'
                        : 'bg-bg-card border-border-soft/40 hover:bg-bg/40 hover:border-border-soft/80'
                    }`}
                  >
                    <img
                      src={agent.icon}
                      alt={agent.name}
                      className="w-8 h-8 object-contain opacity-90 transition-all duration-150 mb-1.5"
                    />
                    <span className={`text-[12.5px] text-text-primary text-center truncate w-full z-20 transition-all duration-100 ${
                      isSelected ? 'font-bold' : 'font-medium opacity-80'
                    }`}>
                      {agent.name}
                    </span>
                  </motion.button>
                );
              })}
            </div>
          </motion.div>

          {/* Select Run Mode (Python / Docker) */}
          <motion.div variants={itemVariants} className="space-y-2">
            <p className="text-[13px] font-bold text-text-muted">2. Select Connection Environment</p>
            <div className="grid grid-cols-2 gap-2">
              {RUN_MODES.map((modeOption) => {
                const isSelected = runMode === modeOption.id;
                return (
                  <motion.button
                    key={modeOption.id}
                    onClick={() => setRunMode(modeOption.id)}
                    whileTap={{ scale: 0.98 }}
                    className={`relative flex flex-row items-center justify-start p-3 pl-6 gap-4 rounded-xl border transition-all cursor-pointer h-18 ${
                      isSelected
                        ? 'bg-bg border-border-soft shadow-xs'
                        : 'bg-bg-card border-border-soft/40 hover:bg-bg/40 hover:border-border-soft/80'
                    }`}
                  >
                    <img
                      src={modeOption.icon}
                      alt={modeOption.name}
                      className="w-8 h-8 object-contain opacity-90 transition-all duration-150 shrink-0"
                    />
                    <div className="flex flex-col items-start min-w-0">
                      <span className={`text-[12.5px] text-text-primary text-left truncate w-full z-20 transition-all duration-100 ${
                        isSelected ? 'font-bold' : 'font-medium opacity-80'
                      }`}>
                        {modeOption.name}
                      </span>
                      <span className="text-[10px] text-text-muted text-left truncate w-full z-20 lowercase mt-0.5 leading-normal">
                        {modeOption.description}
                      </span>
                    </div>
                  </motion.button>
                );
              })}
            </div>
          </motion.div>

          {/* Configuration instructions block */}
          <motion.div
            variants={itemVariants}
            className="border-t border-border-soft/60 pt-4"
          >
            <div className="space-y-3">
              <p className="text-[13px] font-bold text-text-muted">3. Setup Instructions</p>
              <pre className="text-[11.5px] font-display font-medium text-text-muted leading-relaxed whitespace-pre-wrap break-words">
                {selectedAgent.description[runMode]}
              </pre>

              <div className="relative rounded-xl border border-border-soft bg-bg p-4 group/code shadow-xs">
                <div className="absolute right-3 top-3">
                  <CopyButton text={selectedAgent.copyText(instance.api_url, runMode)} label="Copy" iconOnly={true} />
                </div>
                <pre className="text-[11px] font-mono text-text-primary whitespace-pre-wrap break-all leading-relaxed pr-10">
                  <code className="font-mono">
                    <HighlightedCode code={selectedAgent.copyText(instance.api_url, runMode)} mode={selectedAgent.mode} />
                  </code>
                </pre>
              </div>
            </div>
          </motion.div>
        </motion.div>
      </motion.div>
    </>
  );
}
