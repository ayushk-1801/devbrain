import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Copy, Check, Trash2, AlertTriangle, ExternalLink, Clock, FolderGit2, Settings2, MoreVertical, BookOpen, Link2 } from 'lucide-react';

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
  onConfigClick: (instance: Instance) => void;
}



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



export default function InstanceCard({ instance, onDelete, onConfigClick }: InstanceCardProps) {
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [showMenu, setShowMenu] = useState(false);

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
                        className="absolute right-0 mt-1 w-max min-w-[110px] bg-bg-card border border-border-soft rounded-lg shadow-lg py-1 z-30 text-[10px]"
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
                  onClick={() => onConfigClick(instance)}
                  className="flex items-center gap-1 text-[9px] font-bold uppercase tracking-wider px-2 py-1 rounded-md border border-border-soft text-text-muted hover:text-text-primary hover:bg-bg-secondary transition-all cursor-pointer"
                >
                  <BookOpen size={10} />
                  <span>Instructions</span>
                </button>
              </div>
              <div className="flex items-center justify-between gap-2 bg-bg-secondary border border-border-soft rounded-lg px-2 py-0.5 hover:border-text-muted/30 transition-colors duration-150">
                <a
                  href={api_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[10px] font-mono text-text-muted hover:text-text-primary truncate flex items-center gap-1 transition-colors py-0.5"
                >
                  <Link2 size={10} className="shrink-0 text-text-inactive" />
                  <span className="truncate underline underline-offset-4 decoration-border-soft/60 group-hover:decoration-text-muted transition-colors">{api_url}</span>
                </a>
                <CopyButton text={api_url} label="Copy" compact={true} />
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
