import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Plus, RefreshCw, Brain, Layers, AlertCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth, PLATFORM_API } from '../context/AuthContext';
import { Navbar } from './Navbar';
import InstanceCard, { type Instance } from './InstanceCard';

// Skeleton loader for cards
function CardSkeleton() {
  return (
    <div className="bg-bg-card border border-border-soft rounded-2xl overflow-hidden animate-pulse">
      <div className="p-5 pb-4 border-b border-border-soft">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <div className="h-4 bg-bg-secondary rounded-lg w-36" />
            <div className="h-3 bg-bg-secondary rounded-lg w-24" />
          </div>
          <div className="h-6 bg-bg-secondary rounded-full w-20" />
        </div>
      </div>
      <div className="p-5 space-y-4">
        <div className="space-y-2">
          <div className="h-3 bg-bg-secondary rounded w-16" />
          <div className="h-10 bg-bg-secondary rounded-xl" />
        </div>
        <div className="space-y-2">
          <div className="h-3 bg-bg-secondary rounded w-24" />
          <div className="h-20 bg-bg-secondary rounded-xl" />
        </div>
      </div>
    </div>
  );
}

// Empty state
function EmptyState({ onCreateClick }: { onCreateClick: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="col-span-full flex flex-col items-center justify-center py-20 px-6"
    >
      <div
        className="w-20 h-20 rounded-3xl border border-border-soft flex items-center justify-center mb-6"
        style={{ background: 'var(--accent-mint)' }}
      >
        <Brain size={36} className="text-text-primary opacity-60" />
      </div>
      <h3 className="font-display font-bold text-[22px] text-text-primary mb-2">
        No instances yet
      </h3>
      <p className="text-text-muted text-[15px] text-center max-w-sm leading-relaxed mb-8">
        Create your first DevBrain instance to start querying your codebase's history and decisions.
      </p>
      <button
        onClick={onCreateClick}
        className="flex items-center gap-2 bg-btn-dark hover:bg-btn-dark-hover text-btn-dark-text font-display font-semibold text-[14px] px-6 py-3 rounded-full transition-colors duration-200 cursor-pointer"
      >
        <Plus size={16} />
        Create First Instance
      </button>
    </motion.div>
  );
}

export default function Dashboard() {
  const { user, token } = useAuth();
  const navigate = useNavigate();

  const [instances, setInstances] = useState<Instance[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchInstances = useCallback(
    async (silent = false) => {
      if (!token) return;
      if (!silent) setIsLoading(true);
      else setIsRefreshing(true);
      setError(null);

      try {
        const res = await fetch(
          `${PLATFORM_API}/instances?authorization=Bearer ${token}`
        );
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setInstances(Array.isArray(data) ? data : data.instances ?? []);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load instances');
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [token]
  );

  useEffect(() => {
    fetchInstances();
  }, [fetchInstances]);

  // Auto-refresh every 30s
  useEffect(() => {
    const interval = setInterval(() => fetchInstances(true), 30_000);
    return () => clearInterval(interval);
  }, [fetchInstances]);

  const handleDelete = useCallback(
    async (id: string) => {
      if (!token) return;
      // Optimistic remove
      setInstances((prev) => prev.filter((i) => i.id !== id));
      try {
        await fetch(`${PLATFORM_API}/instances/${id}?authorization=Bearer ${token}`, {
          method: 'DELETE',
        });
      } catch {
        // Re-fetch if delete failed
        fetchInstances(true);
      }
    },
    [token, fetchInstances]
  );

  return (
    <div className="min-h-screen bg-bg">
      <Navbar />

      <main className="pt-24 pb-20 px-4 sm:px-6 md:px-10 max-w-[1200px] mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
          className="flex flex-col sm:flex-row sm:items-center justify-between gap-5 mb-10"
        >
          <div className="flex items-center gap-4">
            {user?.avatar_url && (
              <motion.img
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.1 }}
                src={user.avatar_url}
                alt={user.login}
                className="w-12 h-12 rounded-full border-2 border-border-soft object-cover"
              />
            )}
            <div>
              <h1 className="font-display font-black text-[26px] md:text-[30px] text-text-primary leading-tight">
                Welcome back,{' '}
                <span
                  className="bg-clip-text text-transparent"
                  style={{
                    backgroundImage: 'linear-gradient(135deg, var(--color-text-primary), var(--color-text-muted))',
                  }}
                >
                  @{user?.login}
                </span>
              </h1>
              <p className="text-text-muted text-[14px] mt-0.5">
                {instances.length === 0 && !isLoading
                  ? 'Create your first DevBrain instance below'
                  : `${instances.length} instance${instances.length !== 1 ? 's' : ''} running`}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Refresh button */}
            <button
              onClick={() => fetchInstances(true)}
              disabled={isRefreshing}
              className="flex items-center gap-2 px-4 py-2.5 rounded-full border border-border-soft bg-bg-card hover:bg-bg-secondary text-text-muted hover:text-text-primary text-[13px] font-medium transition-colors cursor-pointer disabled:opacity-50"
            >
              <RefreshCw size={13} className={isRefreshing ? 'animate-spin' : ''} />
              Refresh
            </button>

            {/* Create new instance */}
            <button
              onClick={() => navigate('/new-instance')}
              className="flex items-center gap-2 bg-btn-dark hover:bg-btn-dark-hover text-btn-dark-text font-display font-semibold text-[14px] px-5 py-2.5 rounded-full transition-colors duration-200 cursor-pointer"
            >
              <Plus size={16} />
              New Instance
            </button>
          </div>
        </motion.div>

        {/* Stats strip */}
        {!isLoading && instances.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="flex gap-3 mb-8 flex-wrap"
          >
            {[
              {
                label: 'Total',
                value: instances.length,
                color: 'var(--color-bg-secondary)',
                isDarkText: false,
              },
              {
                label: 'Running',
                value: instances.filter((i) => i.status === 'running').length,
                color: 'var(--accent-mint)',
                isDarkText: true,
              },
              {
                label: 'Pending',
                value: instances.filter((i) => i.status === 'pending').length,
                color: 'var(--accent-yellow)',
                isDarkText: true,
              },
              {
                label: 'Error',
                value: instances.filter((i) => i.status === 'error' || i.status === 'stopped').length,
                color: 'var(--accent-peach)',
                isDarkText: true,
              },
            ].map(({ label, value, color, isDarkText }) => (
              <div
                key={label}
                className={`flex items-center gap-2 px-4 py-2 rounded-full border border-border-soft text-[13px] font-medium transition-colors ${
                  isDarkText ? 'text-[#040200]' : 'text-text-primary'
                }`}
                style={{ background: color }}
              >
                <Layers size={12} className={isDarkText ? 'text-[#6B6A5E]' : 'text-text-muted'} />
                <span className="font-bold">{value}</span>
                <span className={isDarkText ? 'text-[#6B6A5E]' : 'text-text-muted'}>{label}</span>
              </div>
            ))}
          </motion.div>
        )}

        {/* Error banner */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              className="mb-6 flex items-center gap-3 px-4 py-3.5 rounded-2xl border"
              style={{
                background: 'oklch(0.97 0.03 30 / 0.6)',
                borderColor: 'oklch(0.8 0.1 30)',
                color: 'oklch(0.4 0.14 30)',
              }}
            >
              <AlertCircle size={16} />
              <span className="text-[13px] font-medium">{error}</span>
              <button
                onClick={() => fetchInstances()}
                className="ml-auto text-[12px] font-semibold underline cursor-pointer"
              >
                Retry
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {isLoading ? (
            <>
              <CardSkeleton />
              <CardSkeleton />
              <CardSkeleton />
              <CardSkeleton />
            </>
          ) : instances.length === 0 ? (
            <EmptyState onCreateClick={() => navigate('/new-instance')} />
          ) : (
            instances.map((instance) => (
              <div key={instance.id}>
                <InstanceCard instance={instance} onDelete={handleDelete} />
              </div>
            ))
          )}
        </div>
      </main>
    </div>
  );
}
