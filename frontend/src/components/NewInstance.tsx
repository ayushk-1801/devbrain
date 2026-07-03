import { useState, useEffect, type Dispatch, type SetStateAction } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  ChevronRight,
  ChevronLeft,
  Eye,
  EyeOff,
  Copy,
  Check,
  ExternalLink,
  Github,
  Key,
  Webhook,
  Loader2,
  CheckCircle2,
  ArrowRight,
  Sparkles,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth, PLATFORM_API } from '../context/AuthContext';
import { Navbar } from './Navbar';

// ─── Types ────────────────────────────────────────────────────────────────────

interface FormData {
  repo: string;
  githubToken: string;
  cogneeKey: string;
  geminiKey: string;
  llmProvider: 'cognee' | 'gemini';
  webhookSecret: string;
}

interface CreatedInstance {
  id: string;
  api_url: string;
  mcp_command: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function maskSecret(val: string) {
  if (!val) return '—';
  return val.slice(0, 4) + '•'.repeat(Math.max(0, val.length - 4));
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  };
  return (
    <button
      onClick={copy}
      className="flex items-center gap-1.5 text-[12px] font-medium text-text-muted hover:text-text-primary transition-colors px-2.5 py-1.5 rounded-lg hover:bg-white/10 cursor-pointer"
    >
      <AnimatePresence mode="wait" initial={false}>
        {copied ? (
          <motion.span
            key="c"
            initial={{ scale: 0.7, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.7, opacity: 0 }}
            className="flex items-center gap-1 text-green-400"
          >
            <Check size={12} /> Copied!
          </motion.span>
        ) : (
          <motion.span
            key="u"
            initial={{ scale: 0.7, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.7, opacity: 0 }}
            className="flex items-center gap-1"
          >
            <Copy size={12} /> Copy
          </motion.span>
        )}
      </AnimatePresence>
    </button>
  );
}

function PasswordInput({
  value,
  onChange,
  placeholder,
  id,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  id: string;
}) {
  const [show, setShow] = useState(false);
  return (
    <div className="relative">
      <input
        id={id}
        type={show ? 'text' : 'password'}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full bg-bg border border-border-soft rounded-xl px-4 py-3 text-[14px] text-text-primary placeholder:text-text-inactive focus:outline-none focus:border-border transition-colors font-mono pr-11"
      />
      <button
        type="button"
        onClick={() => setShow((s) => !s)}
        className="absolute right-3 top-1/2 -translate-y-1/2 text-text-inactive hover:text-text-muted transition-colors cursor-pointer"
      >
        {show ? <EyeOff size={16} /> : <Eye size={16} />}
      </button>
    </div>
  );
}

// ─── Step indicators ──────────────────────────────────────────────────────────

const STEPS = ['Repository', 'API Keys', 'Review', 'Done'];

function StepIndicator({ current }: { current: number }) {
  return (
    <div className="flex items-center justify-center gap-2 mb-8">
      {STEPS.map((label, idx) => {
        const done = idx < current;
        const active = idx === current;
        return (
          <div key={label} className="flex items-center gap-2">
            <div className="flex flex-col items-center gap-1">
              <motion.div
                animate={{
                  background: done
                    ? 'var(--color-btn-dark)'
                    : active
                    ? 'var(--accent-mint)'
                    : 'var(--color-bg-secondary)',
                  borderColor: active ? 'var(--color-border)' : 'var(--color-border-soft)',
                  scale: active ? 1.15 : 1,
                }}
                transition={{ duration: 0.25 }}
                className="w-7 h-7 rounded-full border-2 flex items-center justify-center text-[11px] font-bold"
                style={{
                  color: done
                    ? 'var(--color-btn-dark-text)'
                    : active
                    ? '#040200'
                    : 'var(--color-text-primary)'
                }}
              >
                {done ? <Check size={12} /> : idx + 1}
              </motion.div>
              <span
                className="text-[10px] font-medium hidden sm:block"
                style={{
                  color: active ? 'var(--color-text-primary)' : 'var(--color-text-inactive)',
                }}
              >
                {label}
              </span>
            </div>
            {idx < STEPS.length - 1 && (
              <div
                className="w-10 h-[2px] rounded-full mb-3 sm:mb-0"
                style={{
                  background: done ? 'var(--color-btn-dark)' : 'var(--color-border-soft)',
                }}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── Step 1: Repository ───────────────────────────────────────────────────────

function StepRepo({
  form,
  setForm,
  onNext,
}: {
  form: FormData;
  setForm: Dispatch<SetStateAction<FormData>>;
  onNext: () => void;
}) {
  const [touched, setTouched] = useState(false);
  const valid = form.repo.includes('/') && form.repo.split('/').length === 2 && form.repo.split('/').every(Boolean);
  const error = touched && !valid ? 'Enter a valid repo in owner/repo format' : '';

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display font-black text-[24px] text-text-primary mb-1">
          Which repository?
        </h2>
        <p className="text-text-muted text-[14px]">
          DevBrain will index the full history of this repo.
        </p>
      </div>

      <div>
        <label htmlFor="repo" className="block text-[13px] font-semibold text-text-primary mb-2">
          Repository <span className="text-red-400">*</span>
        </label>
        <div className="relative">
          <Github
            size={16}
            className="absolute left-3.5 top-1/2 -translate-y-1/2 text-text-inactive"
          />
          <input
            id="repo"
            type="text"
            value={form.repo}
            onChange={(e) => setForm((f) => ({ ...f, repo: e.target.value }))}
            onBlur={() => setTouched(true)}
            placeholder="owner/repository"
            className="w-full bg-bg border border-border-soft rounded-xl pl-10 pr-4 py-3 text-[14px] text-text-primary placeholder:text-text-inactive focus:outline-none focus:border-border transition-colors font-mono"
          />
        </div>
        {error && (
          <p className="text-red-500 text-[12px] mt-1.5">{error}</p>
        )}
        <p className="text-text-inactive text-[12px] mt-2">
          e.g. <code className="font-mono text-text-muted">vercel/next.js</code> or{' '}
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-text-muted hover:text-text-primary underline underline-offset-2 inline-flex items-center gap-1"
          >
            browse GitHub <ExternalLink size={10} />
          </a>
        </p>
      </div>

      <button
        onClick={() => {
          setTouched(true);
          if (valid) onNext();
        }}
        className="w-full flex items-center justify-center gap-2 bg-btn-dark hover:bg-btn-dark-hover text-btn-dark-text font-display font-semibold text-[15px] py-3.5 rounded-2xl transition-colors cursor-pointer"
      >
        Next <ChevronRight size={16} />
      </button>
    </div>
  );
}

// ─── Step 2: API Keys ─────────────────────────────────────────────────────────

function StepKeys({
  form,
  setForm,
  onBack,
  onNext,
}: {
  form: FormData;
  setForm: Dispatch<SetStateAction<FormData>>;
  onBack: () => void;
  onNext: () => void;
}) {
  const llmKey = form.llmProvider === 'cognee' ? form.cogneeKey : form.geminiKey;
  const canNext = form.githubToken && llmKey;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display font-black text-[24px] text-text-primary mb-1">
          API Keys
        </h2>
        <p className="text-text-muted text-[14px]">
          These are stored securely and never shared.
        </p>
      </div>

      {/* GitHub Token */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label htmlFor="gh-token" className="text-[13px] font-semibold text-text-primary flex items-center gap-1.5">
            <Key size={13} />
            GitHub Personal Access Token <span className="text-red-400">*</span>
          </label>
          <a
            href="https://github.com/settings/tokens/new?scopes=repo"
            target="_blank"
            rel="noopener noreferrer"
            className="text-[11px] text-text-muted hover:text-text-primary underline underline-offset-2 inline-flex items-center gap-1"
          >
            Generate token <ExternalLink size={10} />
          </a>
        </div>
        <PasswordInput
          id="gh-token"
          value={form.githubToken}
          onChange={(v) => setForm((f) => ({ ...f, githubToken: v }))}
          placeholder="ghp_••••••••••••••••••••"
        />
      </div>

      {/* LLM Key selector */}
      <div>
        <label className="block text-[13px] font-semibold text-text-primary mb-2 flex items-center gap-1.5">
          <Sparkles size={13} />
          LLM Provider Key <span className="text-red-400">*</span>
        </label>

        {/* Toggle tabs */}
        <div className="flex gap-2 mb-3 p-1 bg-bg-secondary border border-border-soft rounded-xl">
          {(['cognee', 'gemini'] as const).map((provider) => (
            <button
              key={provider}
              onClick={() => setForm((f) => ({ ...f, llmProvider: provider }))}
              className={`flex-1 py-2 text-[13px] font-semibold rounded-lg transition-all cursor-pointer ${
                form.llmProvider === provider
                  ? 'bg-bg-card border border-border-soft text-text-primary shadow-sm'
                  : 'text-text-muted hover:text-text-primary'
              }`}
            >
              {provider === 'cognee' ? 'Cognee' : 'Google Gemini'}
            </button>
          ))}
        </div>

        {form.llmProvider === 'cognee' ? (
          <PasswordInput
            id="cognee-key"
            value={form.cogneeKey}
            onChange={(v) => setForm((f) => ({ ...f, cogneeKey: v }))}
            placeholder="cognee_••••••••••••••••"
          />
        ) : (
          <PasswordInput
            id="gemini-key"
            value={form.geminiKey}
            onChange={(v) => setForm((f) => ({ ...f, geminiKey: v }))}
            placeholder="AIza••••••••••••••••••"
          />
        )}
      </div>

      {/* Webhook Secret */}
      <div>
        <label htmlFor="webhook" className="block text-[13px] font-semibold text-text-primary mb-2 flex items-center gap-1.5">
          <Webhook size={13} />
          Webhook Secret{' '}
          <span className="text-text-inactive font-normal ml-1">(optional — auto-generated if blank)</span>
        </label>
        <PasswordInput
          id="webhook"
          value={form.webhookSecret}
          onChange={(v) => setForm((f) => ({ ...f, webhookSecret: v }))}
          placeholder="Leave blank to auto-generate"
        />
      </div>

      <div className="flex gap-3">
        <button
          onClick={onBack}
          className="flex items-center gap-2 px-5 py-3 rounded-2xl border border-border-soft bg-bg-card hover:bg-bg-secondary text-text-primary text-[14px] font-semibold transition-colors cursor-pointer"
        >
          <ChevronLeft size={16} /> Back
        </button>
        <button
          onClick={() => { if (canNext) onNext(); }}
          disabled={!canNext}
          className="flex-1 flex items-center justify-center gap-2 bg-btn-dark hover:bg-btn-dark-hover text-btn-dark-text font-display font-semibold text-[15px] py-3.5 rounded-2xl transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Next <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );
}

// ─── Step 3: Review & Create ─────────────────────────────────────────────────

const PROGRESS_STEPS = [
  'Provisioning container…',
  'Configuring Redis…',
  'Starting API server…',
  'Starting worker…',
  'Instance ready!',
];

function StepReview({
  form,
  onBack,
  onSuccess,
}: {
  form: FormData;
  onBack: () => void;
  onSuccess: (instance: CreatedInstance) => void;
}) {
  const { token } = useAuth();
  const [loading, setLoading] = useState(false);
  const [progressIdx, setProgressIdx] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    setProgressIdx(0);

    // Animated progress steps while waiting
    const interval = setInterval(() => {
      setProgressIdx((i) => (i < PROGRESS_STEPS.length - 2 ? i + 1 : i));
    }, 5000);

    try {
      const body: Record<string, string> = {
        repo: form.repo,
        github_token: form.githubToken,
        llm_provider: form.llmProvider,
        ...(form.llmProvider === 'cognee'
          ? { cognee_api_key: form.cogneeKey }
          : { gemini_api_key: form.geminiKey }),
        ...(form.webhookSecret ? { webhook_secret: form.webhookSecret } : {}),
      };

      const res = await fetch(
        `${PLATFORM_API}/instances?authorization=Bearer ${token}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        }
      );

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail ?? `HTTP ${res.status}`);
      }

      const data = await res.json();
      setProgressIdx(PROGRESS_STEPS.length - 1);
      setTimeout(() => onSuccess(data), 600);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create instance');
    } finally {
      clearInterval(interval);
      if (error) setLoading(false);
    }
  };

  const llmLabel = form.llmProvider === 'cognee' ? 'Cognee' : 'Google Gemini';
  const llmKey = form.llmProvider === 'cognee' ? form.cogneeKey : form.geminiKey;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display font-black text-[24px] text-text-primary mb-1">
          Review & Create
        </h2>
        <p className="text-text-muted text-[14px]">
          Estimated startup time: ~30 seconds
        </p>
      </div>

      {/* Summary card */}
      <div className="bg-bg-secondary border border-border-soft rounded-2xl divide-y divide-border-soft overflow-hidden">
        {[
          { label: 'Repository', value: form.repo, mono: true },
          { label: 'LLM Provider', value: llmLabel },
          { label: `${llmLabel} API Key`, value: maskSecret(llmKey), mono: true },
          { label: 'GitHub Token', value: maskSecret(form.githubToken), mono: true },
          {
            label: 'Webhook Secret',
            value: form.webhookSecret ? maskSecret(form.webhookSecret) : 'Auto-generated',
            mono: true,
          },
        ].map(({ label, value, mono }) => (
          <div key={label} className="flex items-center justify-between px-4 py-3 gap-4">
            <span className="text-[13px] text-text-muted shrink-0">{label}</span>
            <span
              className={`text-[13px] font-medium text-text-primary text-right truncate ${
                mono ? 'font-mono' : ''
              }`}
            >
              {value}
            </span>
          </div>
        ))}
      </div>

      {/* Loading progress */}
      <AnimatePresence>
        {loading && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="bg-bg-secondary border border-border-soft rounded-2xl p-4 space-y-2">
              {PROGRESS_STEPS.map((step, idx) => {
                const done = idx < progressIdx;
                const active = idx === progressIdx;
                return (
                  <motion.div
                    key={step}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: idx <= progressIdx ? 1 : 0.3, x: 0 }}
                    className="flex items-center gap-3 text-[13px]"
                  >
                    {done ? (
                      <Check size={14} className="text-green-500 shrink-0" />
                    ) : active ? (
                      <Loader2 size={14} className="animate-spin text-text-muted shrink-0" />
                    ) : (
                      <div className="w-3.5 h-3.5 rounded-full border border-border-soft shrink-0" />
                    )}
                    <span
                      className={
                        done
                          ? 'text-text-muted line-through'
                          : active
                          ? 'text-text-primary font-medium'
                          : 'text-text-inactive'
                      }
                    >
                      {step}
                    </span>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Error */}
      {error && (
        <div
          className="px-4 py-3 rounded-xl border text-[13px] font-medium"
          style={{
            background: 'oklch(0.97 0.03 30 / 0.6)',
            borderColor: 'oklch(0.8 0.1 30)',
            color: 'oklch(0.4 0.14 30)',
          }}
        >
          ⚠️ {error}
        </div>
      )}

      <div className="flex gap-3">
        <button
          onClick={onBack}
          disabled={loading}
          className="flex items-center gap-2 px-5 py-3 rounded-2xl border border-border-soft bg-bg-card hover:bg-bg-secondary text-text-primary text-[14px] font-semibold transition-colors cursor-pointer disabled:opacity-40"
        >
          <ChevronLeft size={16} /> Back
        </button>
        <button
          onClick={handleCreate}
          disabled={loading}
          className="flex-1 flex items-center justify-center gap-2 bg-btn-dark hover:bg-btn-dark-hover text-btn-dark-text font-display font-semibold text-[15px] py-3.5 rounded-2xl transition-colors cursor-pointer disabled:opacity-60"
        >
          {loading ? (
            <>
              <Loader2 size={16} className="animate-spin" /> Creating…
            </>
          ) : (
            <>
              <Sparkles size={16} /> Create DevBrain Instance
            </>
          )}
        </button>
      </div>
    </div>
  );
}

// ─── Step 4: Success ──────────────────────────────────────────────────────────

function StepSuccess({ instance }: { instance: CreatedInstance }) {
  const navigate = useNavigate();
  const [apiCopied, setApiCopied] = useState(false);
  const [mcpCopied, setMcpCopied] = useState(false);

  const copyText = async (text: string, setter: (v: boolean) => void) => {
    try {
      await navigator.clipboard.writeText(text);
      setter(true);
      setTimeout(() => setter(false), 2000);
    } catch {}
  };

  // Confetti-style particles
  const particles = Array.from({ length: 18 }, (_, i) => ({
    id: i,
    x: Math.random() * 100,
    delay: Math.random() * 0.6,
    size: 6 + Math.random() * 8,
    color: ['var(--accent-mint)', 'var(--accent-yellow)', 'var(--accent-peach)', 'var(--accent-orchid)'][
      Math.floor(Math.random() * 4)
    ],
  }));

  return (
    <div className="space-y-6 relative">
      {/* Confetti */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {particles.map((p) => (
          <motion.div
            key={p.id}
            className="absolute rounded-sm"
            style={{
              left: `${p.x}%`,
              top: -p.size,
              width: p.size,
              height: p.size,
              background: p.color,
            }}
            animate={{
              y: [0, 280 + Math.random() * 100],
              rotate: [0, 360 * (Math.random() > 0.5 ? 1 : -1)],
              opacity: [1, 0],
            }}
            transition={{
              duration: 1.8 + Math.random() * 0.8,
              delay: p.delay,
              ease: 'easeIn',
            }}
          />
        ))}
      </div>

      {/* Checkmark */}
      <div className="flex flex-col items-center py-4">
        <motion.div
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: 'spring', stiffness: 260, damping: 20 }}
          className="w-20 h-20 rounded-full flex items-center justify-center mb-4"
          style={{ background: 'var(--accent-mint)' }}
        >
          <CheckCircle2 size={40} className="text-green-700" />
        </motion.div>
        <motion.h2
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="font-display font-black text-[26px] text-text-primary"
        >
          Instance Created! 🎉
        </motion.h2>
        <motion.p
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="text-text-muted text-[14px] mt-1"
        >
          Your DevBrain instance is spinning up.
        </motion.p>
      </div>

      {/* API URL */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.35 }}
      >
        <p className="text-[11px] font-semibold text-text-inactive uppercase tracking-wider mb-2">
          API URL
        </p>
        <div
          className="flex items-center justify-between gap-2 border border-border-soft rounded-xl px-3 py-2.5"
          style={{ background: 'var(--color-bg-secondary)' }}
        >
          <code className="text-[13px] font-mono text-text-muted truncate">
            {instance.api_url}
          </code>
          <button
            onClick={() => copyText(instance.api_url, setApiCopied)}
            className="shrink-0 flex items-center gap-1 text-[12px] text-text-muted hover:text-text-primary cursor-pointer px-2 py-1 rounded-lg hover:bg-bg-card transition-colors"
          >
            {apiCopied ? <Check size={12} className="text-green-500" /> : <Copy size={12} />}
            {apiCopied ? 'Copied!' : 'Copy'}
          </button>
        </div>
      </motion.div>

      {/* MCP Command */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.42 }}
      >
        <p className="text-[11px] font-semibold text-text-inactive uppercase tracking-wider mb-2">
          MCP CLI Command
        </p>
        <div
          className="rounded-xl border border-border-soft overflow-hidden"
          style={{ background: 'var(--color-btn-dark)' }}
        >
          <div className="flex items-center justify-between px-3 py-2 border-b border-white/10">
            <span className="text-[10px] font-mono text-white/40">bash</span>
            <button
              onClick={() => copyText(instance.mcp_command, setMcpCopied)}
              className="flex items-center gap-1 text-[12px] text-white/50 hover:text-white/80 cursor-pointer transition-colors"
            >
              {mcpCopied ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
              {mcpCopied ? 'Copied!' : 'Copy'}
            </button>
          </div>
          <div className="px-3 py-3 overflow-x-auto">
            <pre className="text-[12px] font-mono text-white/80 whitespace-pre-wrap break-all leading-relaxed">
              {instance.mcp_command}
            </pre>
          </div>
        </div>
      </motion.div>

      {/* CTA buttons */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="flex flex-col sm:flex-row gap-3 pt-2"
      >
        <button
          onClick={() => navigate('/dashboard')}
          className="flex-1 flex items-center justify-center gap-2 bg-btn-dark hover:bg-btn-dark-hover text-btn-dark-text font-display font-semibold text-[14px] py-3.5 rounded-2xl transition-colors cursor-pointer"
        >
          Go to Dashboard <ArrowRight size={16} />
        </button>
        <a
          href="/docs"
          className="flex-1 flex items-center justify-center gap-2 border border-border-soft bg-bg-card hover:bg-bg-secondary text-text-primary text-[14px] font-semibold py-3.5 rounded-2xl transition-colors cursor-pointer"
        >
          Ingest your first repo <ExternalLink size={14} />
        </a>
      </motion.div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function NewInstance() {
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<FormData>({
    repo: '',
    githubToken: '',
    cogneeKey: '',
    geminiKey: '',
    llmProvider: 'gemini',
    webhookSecret: '',
  });
  const [createdInstance, setCreatedInstance] = useState<CreatedInstance | null>(null);

  const handleSuccess = (instance: CreatedInstance) => {
    setCreatedInstance(instance);
    setStep(3);
  };

  return (
    <div className="min-h-screen bg-bg">
      <Navbar />

      <main className="pt-24 pb-20 px-4 flex flex-col items-center">
        {/* Page header */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="text-center mb-8 max-w-xl"
        >
          <h1 className="font-display font-black text-[30px] md:text-[36px] leading-tight tracking-tight">
            <span className="text-text-primary">Create a </span>
            <span
              className="bg-clip-text text-transparent"
              style={{
                backgroundImage:
                  'linear-gradient(135deg, oklch(0.7 0.15 150), oklch(0.75 0.12 200))',
              }}
            >
              DevBrain Instance
            </span>
          </h1>
          <p className="text-text-muted text-[15px] mt-2">
            Connect your repo and start querying its entire history.
          </p>
        </motion.div>

        {/* Wizard card */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
          className="w-full max-w-2xl bg-bg-card border border-border-soft rounded-3xl p-7 md:p-9 shadow-[0_16px_64px_rgba(0,0,0,0.07)]"
        >
          <StepIndicator current={step} />

          <AnimatePresence mode="wait">
            <motion.div
              key={step}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.25, ease: 'easeInOut' }}
            >
              {step === 0 && (
                <StepRepo form={form} setForm={setForm} onNext={() => setStep(1)} />
              )}
              {step === 1 && (
                <StepKeys
                  form={form}
                  setForm={setForm}
                  onBack={() => setStep(0)}
                  onNext={() => setStep(2)}
                />
              )}
              {step === 2 && (
                <StepReview
                  form={form}
                  onBack={() => setStep(1)}
                  onSuccess={handleSuccess}
                />
              )}
              {step === 3 && createdInstance && (
                <StepSuccess instance={createdInstance} />
              )}
            </motion.div>
          </AnimatePresence>
        </motion.div>
      </main>
    </div>
  );
}
