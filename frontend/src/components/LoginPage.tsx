import { useEffect } from 'react';
import { motion } from 'motion/react';
import { Github, GitBranch, Zap, Network } from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Logo } from './ui/Logo';

const ERROR_MESSAGES: Record<string, string> = {
  state_mismatch: 'Security check failed. Please try again.',
  token_exchange_failed: 'Could not complete GitHub login. Please try again.',
  user_fetch_failed: 'Could not fetch your GitHub profile. Please try again.',
};

const FEATURE_PILLS = [
  { icon: GitBranch, label: 'Git History', color: 'var(--accent-mint)' },
  { icon: Zap, label: 'PR Decisions', color: 'var(--accent-yellow)' },
  { icon: Network, label: 'AST Graph', color: 'var(--accent-peach)' },
];

const ORB_CONFIGS = [
  {
    size: 600,
    x: '-15%',
    y: '-20%',
    color: 'radial-gradient(circle, oklch(0.82 0.09 300 / 0.35) 0%, transparent 70%)',
    duration: 18,
  },
  {
    size: 500,
    x: '55%',
    y: '30%',
    color: 'radial-gradient(circle, oklch(0.88 0.12 150 / 0.3) 0%, transparent 70%)',
    duration: 22,
  },
  {
    size: 400,
    x: '20%',
    y: '60%',
    color: 'radial-gradient(circle, oklch(0.85 0.1 40 / 0.28) 0%, transparent 70%)',
    duration: 26,
  },
];

export default function LoginPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user, isLoading, login } = useAuth();
  const errorKey = searchParams.get('error') ?? '';
  const errorMessage = ERROR_MESSAGES[errorKey] ?? (errorKey ? 'An error occurred. Please try again.' : null);

  // Redirect if already authenticated
  useEffect(() => {
    if (!isLoading && user) {
      navigate('/dashboard', { replace: true });
    }
  }, [user, isLoading, navigate]);

  return (
    <div className="min-h-screen bg-bg relative overflow-hidden flex items-center justify-center px-4">
      {/* Animated background orbs */}
      {ORB_CONFIGS.map((orb, i) => (
        <motion.div
          key={i}
          className="absolute pointer-events-none"
          style={{
            width: orb.size,
            height: orb.size,
            left: orb.x,
            top: orb.y,
            background: orb.color,
            borderRadius: '50%',
            filter: 'blur(1px)',
          }}
          animate={{
            x: [0, 30, -20, 15, 0],
            y: [0, -25, 20, -10, 0],
            scale: [1, 1.08, 0.95, 1.04, 1],
          }}
          transition={{
            duration: orb.duration,
            repeat: Infinity,
            ease: 'easeInOut',
            delay: i * 3,
          }}
        />
      ))}

      {/* Subtle grid overlay */}
      <div
        className="absolute inset-0 pointer-events-none opacity-[0.03]"
        style={{
          backgroundImage: `
            linear-gradient(var(--color-text-primary) 1px, transparent 1px),
            linear-gradient(90deg, var(--color-text-primary) 1px, transparent 1px)
          `,
          backgroundSize: '48px 48px',
        }}
      />

      <motion.div
        initial={{ opacity: 0, y: 32 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
        className="relative z-10 w-full max-w-md"
      >
        {/* Glass card */}
        <div
          className="rounded-3xl border border-border-soft p-8 md:p-10 shadow-2xl"
          style={{
            background: 'color-mix(in srgb, var(--color-bg-card) 85%, transparent)',
            backdropFilter: 'blur(24px)',
            WebkitBackdropFilter: 'blur(24px)',
          }}
        >
          {/* Logo */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="flex justify-center mb-6"
          >
            <Logo />
          </motion.div>

          {/* Heading */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.18 }}
            className="text-center mb-8"
          >
            <h1 className="font-display text-[28px] md:text-[32px] font-black text-text-primary leading-tight tracking-tight">
              Welcome to DevBrain
            </h1>
            <p className="text-text-muted text-[15px] mt-2 leading-relaxed font-display">
              Your codebase's living memory
            </p>
          </motion.div>

          {/* Feature pills */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.26 }}
            className="flex items-center justify-center gap-2 flex-wrap mb-8"
          >
            {FEATURE_PILLS.map(({ icon: Icon, label, color }) => (
              <div
                key={label}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[12px] font-medium text-text-primary border border-border-soft"
                style={{ background: color, borderColor: 'transparent' }}
              >
                <Icon size={12} />
                {label}
              </div>
            ))}
          </motion.div>

          {/* Error message */}
          {errorMessage && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-5 px-4 py-3 rounded-xl border text-[13px] font-medium"
              style={{
                background: 'oklch(0.95 0.05 30 / 0.5)',
                borderColor: 'oklch(0.75 0.12 30)',
                color: 'oklch(0.35 0.12 30)',
              }}
            >
              ⚠️ {errorMessage}
            </motion.div>
          )}

          {/* GitHub Sign In button */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.34 }}
          >
            <button
              onClick={login}
              className="w-full flex items-center justify-center gap-3 bg-btn-dark hover:bg-btn-dark-hover text-btn-dark-text font-display font-semibold text-[15px] px-6 py-4 rounded-2xl transition-all duration-200 cursor-pointer group"
              style={{
                boxShadow: '0 4px 24px rgba(0,0,0,0.12)',
              }}
            >
              <Github
                size={20}
                className="transition-transform duration-200 group-hover:rotate-12"
              />
              Continue with GitHub
            </button>
          </motion.div>

          {/* Footer note */}
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4, delay: 0.44 }}
            className="text-center text-text-inactive text-[12px] mt-6 leading-relaxed"
          >
            By signing in, you agree to our Terms of Service.
            <br />
            We only request the permissions we need.
          </motion.p>
        </div>

        {/* Back to home */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4, delay: 0.5 }}
          className="text-center mt-5"
        >
          <a
            href="/"
            className="text-text-muted text-[13px] hover:text-text-primary transition-colors font-display"
          >
            ← Back to home
          </a>
        </motion.div>
      </motion.div>
    </div>
  );
}
