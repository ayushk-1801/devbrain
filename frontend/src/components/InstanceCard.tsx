import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Copy, Check, Trash2, AlertTriangle, ExternalLink, Clock, FolderGit2, Settings2, MoreVertical } from 'lucide-react';

export interface Instance {
  id: string;
  repo: string;
  api_url: string;
  status: 'running' | 'pending' | 'error' | 'stopped';
  created_at: string;
  mcp_command: string;
}

interface InstanceCardProps {
  instance: Instance;
  onDelete: (id: string) => void;
}

const AGENTS = [
  {
    id: 'claude',
    name: 'Claude Code',
    icon: '/claude-ai.svg',
    description: 'Run this in your project terminal to register DevBrain in Claude Code:',
    copyText: (url: string) => `claude mcp add devbrain -s project -e DEVBRAIN_API_URL="${url}" -- python -m backend.mcp_server`,
    mode: 'shell',
  },
  {
    id: 'codex',
    name: 'Codex',
    icon: '/codex-color-removebg-preview.png',
    description: 'Add this to your ~/.codex/config.toml under [mcp_servers.devbrain]:',
    copyText: (url: string) => `[mcp_servers.devbrain]\ncommand = "python"\nargs = ["-m", "backend.mcp_server"]\nenv = { "DEVBRAIN_API_URL" = "${url}" }`,
    mode: 'toml',
  },
  {
    id: 'cursor',
    name: 'Cursor',
    icon: '/cursor.png',
    description: 'Add as a Command type in Cursor Settings > Features > MCP:',
    copyText: (url: string) => `python -m backend.mcp_server --api-url "${url}"`,
    mode: 'command',
  },
  {
    id: 'zed',
    name: 'Zed Editor',
    icon: '/Zed_Editor_Logo.png',
    description: 'Paste this into your Zed settings.json under "context_servers":',
    copyText: (url: string) => JSON.stringify({
      "devbrain": {
        "command": {
          "path": "python",
          "args": ["-m", "backend.mcp_server"],
          "env": {
            "DEVBRAIN_API_URL": url
          }
        }
      }
    }, null, 2),
    mode: 'json',
  },
  {
    id: 'antigravity',
    name: 'Antigravity',
    icon: '/google-antigravity.png',
    description: 'Run this to connect DevBrain to your Google Antigravity CLI:',
    copyText: (url: string) => `agy mcp add devbrain -e DEVBRAIN_API_URL="${url}" -- python -m backend.mcp_server`,
    mode: 'shell',
  },
  {
    id: 'opencode',
    name: 'OpenCode',
    icon: '/opencode-logo-removebg-preview.png',
    description: 'Add this to your global or project opencode.jsonc config file under the "mcp" key:',
    copyText: (url: string) => JSON.stringify({
      "devbrain": {
        "type": "local",
        "command": ["python", "-m", "backend.mcp_server"],
        "enabled": true,
        "environment": {
          "DEVBRAIN_API_URL": url
        }
      }
    }, null, 2),
    mode: 'json',
  }
];

function StatusBadge({ status }: { status: Instance['status'] }) {
  const config = {
    running: {
      label: 'Running',
      bg: 'var(--color-accent-mint)',
      textColor: 'oklch(0.3 0.12 150)',
      dot: '#10b981',
      pulse: true,
    },
    pending: {
      label: 'Pending',
      bg: 'var(--color-accent-yellow)',
      textColor: 'oklch(0.4 0.12 85)',
      dot: '#eab308',
      pulse: true,
    },
    error: {
      label: 'Error',
      bg: 'var(--color-accent-peach)',
      textColor: 'oklch(0.4 0.15 30)',
      dot: '#ef4444',
      pulse: false,
    },
    stopped: {
      label: 'Stopped',
      bg: 'var(--color-bg-secondary)',
      textColor: 'var(--color-text-muted)',
      dot: 'var(--color-text-inactive)',
      pulse: false,
    },
  };

  const { label, bg, textColor, dot, pulse } = config[status];

  return (
    <div
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wide border border-black/5"
      style={{ background: bg, color: textColor }}
    >
      <span className="relative flex h-1.5 w-1.5">
        {pulse && (
          <span
            className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
            style={{ background: dot }}
          />
        )}
        <span
          className="relative inline-flex rounded-full h-1.5 w-1.5"
          style={{ background: dot }}
        />
      </span>
      {label}
    </div>
  );
}

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
    <button
      onClick={handleCopy}
      className={`flex items-center justify-center transition-all rounded-lg cursor-pointer text-[10px] ${
        iconOnly
          ? 'p-1 border border-border-soft bg-bg-card text-text-muted hover:text-text-primary hover:bg-bg-secondary hover:shadow-xs'
          : compact
            ? 'px-1 py-0.5 text-text-muted hover:text-text-primary text-[9.5px]'
            : 'px-2 py-1 text-text-muted hover:text-text-primary hover:bg-bg-secondary border border-border-soft/60'
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
            className="flex items-center gap-0.5 font-bold text-text-primary"
          >
            <Check size={10} />
            {!iconOnly && 'Copied'}
          </motion.span>
        ) : (
          <motion.span
            key="copy"
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.8, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="flex items-center gap-0.5"
          >
            <Copy size={10} />
            {!iconOnly && label}
          </motion.span>
        )}
      </AnimatePresence>
    </button>
  );
}

function formatDate(dateStr: string) {
  try {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(dateStr));
  } catch {
    return dateStr;
  }
}

function HighlightedCode({ code, mode }: { code: string; mode: string }) {
  if (mode === 'json') {
    const tokens = code.split(/(".*?"|[{}[\]:,]|\d+|true|false)/g);
    return (
      <>
        {tokens.map((token, i) => {
          if (token.startsWith('"') && token.endsWith('"')) {
            const nextToken = tokens[i + 1] || '';
            const isKey = nextToken.trim() === ':';
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

export default function InstanceCard({ instance, onDelete }: InstanceCardProps) {
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [showConfig, setShowConfig] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState(AGENTS[0]);

  const { id, repo, api_url, status, created_at } = instance;
  const repoName = repo.split('/').pop() ?? repo;
  const repoOwner = repo.split('/')[0] ?? '';

  return (
    <div className="h-full">
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -15, scale: 0.98 }}
        transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
        className="h-full flex flex-col bg-bg-card border border-border-soft rounded-xl overflow-hidden hover:shadow-[0_8px_24px_rgba(0,0,0,0.04)] dark:hover:shadow-[0_8px_24px_rgba(0,0,0,0.3)] transition-all duration-200 relative group"
      >
        {/* Absolute Deletion Overlay */}
        <AnimatePresence>
          {confirmDelete && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-bg-card/95 backdrop-blur-xs flex flex-col justify-center p-5 z-20"
            >
              <div className="flex items-start gap-2.5 text-[11px] font-semibold text-red-600 dark:text-red-400 mb-3.5">
                <AlertTriangle size={14} className="shrink-0 mt-0.5" />
                <div>
                  <p className="font-bold">Are you absolutely sure?</p>
                  <p className="font-medium text-text-muted text-[10px] mt-0.5 leading-normal">
                    This stops all containers and permanently deletes all Kuzu graph data.
                  </p>
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setConfirmDelete(false)}
                  className="flex-1 py-1.5 text-[11px] font-bold rounded-lg border border-border-soft bg-bg text-text-primary hover:bg-bg-secondary transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    setConfirmDelete(false);
                    onDelete(id);
                  }}
                  className="flex-1 py-1.5 text-[11px] font-bold rounded-lg text-white transition-colors cursor-pointer bg-red-600 hover:bg-red-700 shadow-xs"
                >
                  Delete
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Card header */}
        <div className="p-4 pb-3 border-b border-border-soft/60">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex items-start gap-2.5">
              <div className="p-2 bg-bg-secondary rounded-lg text-text-muted shrink-0 mt-0.5 border border-border-soft/40">
                <FolderGit2 size={15} />
              </div>
              <div className="min-w-0">
                <div className="flex items-baseline flex-wrap gap-x-0.5">
                  <span className="text-text-inactive text-[11.5px] font-medium">
                    {repoOwner}
                  </span>
                  <span className="text-text-inactive text-[11.5px] font-light">/</span>
                  <h3 className="font-display font-black text-[15px] text-text-primary truncate">
                    {repoName}
                  </h3>
                </div>
                <div className="flex items-center gap-1 text-text-muted text-[10px] mt-0.5">
                  <Clock size={10} className="text-text-inactive" />
                  <span>Created {formatDate(created_at)}</span>
                </div>
              </div>
            </div>
            
            {/* Header Right Actions */}
            <div className="flex items-center gap-1.5 shrink-0 mt-0.5">
              <StatusBadge status={status} />
              
              {/* Three Dot Dropdown Menu */}
              <div className="relative">
                <button
                  onClick={() => setShowMenu(!showMenu)}
                  className="p-1 hover:bg-bg-secondary rounded-md text-text-muted hover:text-text-primary transition-colors cursor-pointer"
                >
                  <MoreVertical size={14} />
                </button>
                <AnimatePresence>
                  {showMenu && (
                    <>
                      <div className="fixed inset-0 z-20" onClick={() => setShowMenu(false)} />
                      <motion.div
                        initial={{ opacity: 0, scale: 0.95, y: -4 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: -4 }}
                        transition={{ duration: 0.12 }}
                        className="absolute right-0 mt-1 w-max min-w-[110px] bg-bg-card border border-border-soft rounded-lg shadow-lg py-1 z-30 font-mono text-[10px]"
                      >
                        <button
                          onClick={() => {
                            setShowMenu(false);
                            setConfirmDelete(true);
                          }}
                          className="w-full flex items-center gap-1.5 px-2.5 py-1.5 text-red-500 hover:bg-red-500/10 transition-colors text-left font-bold cursor-pointer whitespace-nowrap"
                        >
                          <Trash2 size={11} />
                          Delete Instance
                        </button>
                      </motion.div>
                    </>
                  )}
                </AnimatePresence>
              </div>
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="p-4 space-y-4 flex-1 flex flex-col justify-between">
          <div className="space-y-4">
            {/* API URL */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <p className="text-[9px] font-bold text-text-inactive uppercase tracking-wider font-mono">
                  API INSTANCE URL
                </p>
                <button
                  onClick={() => setShowConfig(!showConfig)}
                  className={`flex items-center gap-1 text-[9px] font-bold uppercase tracking-wider px-2 py-1 rounded-md border transition-all cursor-pointer ${
                    showConfig
                      ? 'bg-text-primary border-text-primary text-bg-card'
                      : 'border-border-soft text-text-muted hover:text-text-primary hover:bg-bg-secondary'
                  }`}
                >
                  <Settings2 size={10} />
                  <span>Config</span>
                </button>
              </div>
              <div className="flex items-center justify-between gap-2 bg-bg-secondary border border-border-soft rounded-lg px-2 py-0.5 hover:border-text-muted/30 transition-colors duration-150">
                <a
                  href={api_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[10px] font-mono text-text-muted hover:text-text-primary truncate flex items-center gap-1 transition-colors py-0.5"
                >
                  <ExternalLink size={10} className="shrink-0 text-text-inactive" />
                  <span className="truncate underline underline-offset-4 decoration-border-soft/60 group-hover:decoration-text-muted transition-colors">{api_url}</span>
                </a>
                <CopyButton text={api_url} label="Copy" compact={true} />
              </div>
            </div>

            {/* Expandable Agent Configuration Block */}
            <AnimatePresence>
              {showConfig && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                  className="overflow-hidden space-y-3"
                >
                  <div className="border-t border-border-soft/60 pt-3">
                    <p className="text-[9px] font-bold text-text-inactive uppercase tracking-wider mb-2 font-mono">
                      Select Agent
                    </p>
                    
                    {/* Horizontal Agents Grid */}
                    <div className="grid grid-cols-6 gap-1.5 bg-bg-secondary p-1.5 rounded-lg border border-border-soft/40">
                      {AGENTS.map((agent) => {
                        const isSelected = selectedAgent.id === agent.id;
                        return (
                          <button
                            key={agent.id}
                            onClick={() => setSelectedAgent(agent)}
                            className={`flex flex-col items-center justify-center p-1 rounded-md border transition-all cursor-pointer aspect-square ${
                              isSelected
                                ? 'bg-bg-card border-border-soft shadow-xs scale-102 font-bold'
                                : 'border-transparent hover:bg-bg-card/45 hover:border-border-soft'
                            }`}
                            title={agent.name}
                          >
                            <img
                              src={agent.icon}
                              alt={agent.name}
                              className="w-7 h-7 object-contain opacity-90 transition-all duration-150"
                            />
                            <span className="text-[8px] font-bold text-text-muted mt-1 truncate max-w-full text-center lowercase">
                              {agent.name.split(' ')[0]}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Config Code Block */}
                  <motion.div
                    key={selectedAgent.id}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.15 }}
                    className="space-y-1.5"
                  >
                    <p className="text-[10px] font-semibold text-text-muted leading-snug">
                      {selectedAgent.description}
                    </p>
                    
                    <div className="relative rounded-lg border border-border-soft bg-bg p-3 group/code">
                      <div className="absolute right-2 top-2 opacity-0 group-hover/code:opacity-100 transition-opacity duration-200">
                        <CopyButton text={selectedAgent.copyText(api_url)} label="Copy" iconOnly={true} />
                      </div>
                      <pre className="text-[10px] font-mono text-text-primary whitespace-pre-wrap break-all leading-relaxed pr-10">
                        <code className="font-mono">
                          <HighlightedCode code={selectedAgent.copyText(api_url)} mode={selectedAgent.mode} />
                        </code>
                      </pre>
                    </div>
                  </motion.div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
