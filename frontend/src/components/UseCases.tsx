import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { UserPlus, Map, MessageSquare, BookOpen, Search, GitBranch, History, CheckCircle, Users, Box, TrendingUp, AlertCircle, Bot, Code2, ShieldAlert, PenTool, Lock, Navigation, Bell } from 'lucide-react';

const tabs = [
  { id: 'onboarding', label: 'Onboarding' },
  { id: 'review', label: 'Code Review' },
  { id: 'agents', label: 'AI Agents' }
];

const useCaseContent: Record<string, any[]> = {
  onboarding: [
    { icon: UserPlus, title: "New Engineer Ramp-Up", body: "A new hire asks 'why does this service exist?' DevBrain surfaces the original ADR, the founding PRs, and the first author - in seconds, not days." },
    { icon: Map, title: "Codebase Orientation", body: "Ask 'what does the payment module do and what depends on it?' Get a sourced walkthrough of the architecture from the actual history." },
    { icon: MessageSquare, title: "Silent Knowledge Transfer", body: "When a senior engineer leaves, their institutional knowledge stays in the graph. DevBrain makes offboarding a non-event." },
    { icon: BookOpen, title: "Self-Serve Documentation", body: "Junior engineers answer their own questions without interrupting seniors. Slack messages asking 'why does this exist' drop dramatically." },
    { icon: GitBranch, title: "Cross-Team Visibility", body: "Frontend asks 'did the API team change the auth interface?' DevBrain answers with exact commits and PR links - no cross-team Slack threads." },
    { icon: Bell, title: "Personal Update Digest", body: "Every @mention of you, every file you touched that changed, and every issue assigned to you - delivered as a digest. No more 'did you see my comment on issue #42?'" }
  ],
  review: [
    { icon: History, title: "Prior Art Check", body: "Before merging, reviewers ask DevBrain if this approach has been tried before. Avoid re-solving solved problems." },
    { icon: ShieldAlert, title: "Regression Context", body: "Surface every past bug fix touching the files in a PR. Reviewers catch regressions before they ship." },
    { icon: CheckCircle, title: "Decision Alignment", body: "Check if a PR conflicts with an existing ADR. DevBrain flags architectural drift automatically." },
    { icon: Users, title: "Reviewer Suggestion", body: "DevBrain surfaces who last touched each changed file - built-in CODEOWNERS intelligence." },
    { icon: Box, title: "Scope Analysis", body: "Understand the blast radius of a change: which modules are downstream of the files this PR touches?" },
    { icon: TrendingUp, title: "Historical Velocity", body: "See how many PRs this file has had in the last 90 days. Hot files warrant extra scrutiny." }
  ],
  agents: [
    { icon: Bot, title: "MCP Native", body: "Connect Claude Code or Cursor to DevBrain via the Cognee MCP server. Agents query the graph automatically on every task." },
    { icon: Code2, title: "Grounded Code Gen", body: "AI agents generate code with full context of past decisions, not just the current file. No hallucinated solutions." },
    { icon: AlertCircle, title: "Agentic Refactors", body: "Before an agent refactors a module, it queries what decisions govern it. Safe, compliant changes - automatically." },
    { icon: PenTool, title: "PR Drafting", body: "Agents write PR descriptions that reference the ADRs and prior commits their changes relate to. Automatic context." },
    { icon: Lock, title: "Regression Prevention", body: "Agents check the graph before changing a function: 'has this been reverted before and why?' Ghost bugs stay buried." },
    { icon: Navigation, title: "Multi-hop Reasoning", body: "Agents traverse: function → module → PR → ADR → decision. Answer 'why does this code exist' in a single graph walk." }
  ]
};

const tabColors: Record<string, string> = {
  onboarding: 'var(--color-accent-mint)',
  review: 'var(--color-accent-powder)',
  agents: 'var(--color-accent-blush)'
};

export function UseCases() {
  const [activeTab, setActiveTab] = useState(tabs[0].id);

  return (
    <section id="use-cases" className="section-padding content-container flex flex-col items-center">
      <motion.div 
        initial={{ opacity: 0, y: 24 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-100px" }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="flex flex-col items-center text-center w-full"
      >
        <h2 className="font-display text-[32px] sm:text-[36px] md:text-[56px] lg:text-[60px] font-extrabold text-text-primary leading-[1.1] max-w-[800px] tracking-tight">
          Where DevBrain helps
        </h2>
      </motion.div>

      {/* Pill Switcher */}
      <div className="flex flex-row flex-wrap justify-center gap-3 mt-12 mb-16 w-full px-4">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`font-display text-[14px] px-[24px] py-[10px] rounded-full border-[1.5px] transition-colors cursor-pointer ${
                isActive 
                  ? 'font-bold border-border text-[#040200] ' + (
                      tab.id === 'onboarding' 
                        ? 'bg-accent-mint dark:bg-bg-secondary dark:text-accent-mint dark:border-accent-mint/30'
                        : tab.id === 'review' 
                          ? 'bg-accent-powder dark:bg-bg-secondary dark:text-accent-powder dark:border-accent-powder/30'
                          : 'bg-accent-blush dark:bg-bg-secondary dark:text-accent-blush dark:border-accent-blush/30'
                    )
                  : 'border-text-muted bg-transparent text-text-muted hover:bg-bg-secondary'
              }`}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Card Grid */}
      <div className="w-full relative min-h-[600px] mb-12 md:mb-20">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -16 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8"
          >
            {useCaseContent[activeTab].map((card, idx) => {
              const Icon = card.icon;
              return (
                <div 
                  key={idx}
                  className={`rounded-[24px] p-[40px] md:p-[48px] flex flex-col transition-all duration-300 border ${
                    activeTab === 'onboarding' 
                      ? 'bg-accent-mint border-border/10 dark:bg-bg-secondary dark:border-accent-mint/20'
                      : activeTab === 'review' 
                        ? 'bg-accent-powder border-border/10 dark:bg-bg-secondary dark:border-accent-powder/20'
                        : 'bg-accent-blush border-border/10 dark:bg-bg-secondary dark:border-accent-blush/20'
                  }`}
                >
                  <Icon size={32} className={`mb-6 ${
                    activeTab === 'onboarding' ? 'text-[#040200] dark:text-accent-mint'
                      : activeTab === 'review' ? 'text-[#040200] dark:text-accent-powder'
                      : 'text-[#040200] dark:text-accent-blush'
                  }`} />
                  <h3 className="font-display text-[20px] md:text-[22px] font-bold text-[#040200] dark:text-text-primary mb-3 leading-tight tracking-tight">
                    {card.title}
                  </h3>
                  <p className="font-display text-[15px] md:text-[16px] text-[#6B6A5E] dark:text-text-muted leading-[1.6]">
                    {card.body}
                  </p>
                </div>
              );
            })}
          </motion.div>
        </AnimatePresence>
      </div>
    </section>
  );
}
