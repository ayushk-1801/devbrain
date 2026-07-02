import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { GitCommit, GitPullRequest, FileText, Code2 } from 'lucide-react';

const tabs = [
  { id: 'commits', label: 'Commits', icon: GitCommit, desc: 'Analyze diffs, messages, and authors' },
  { id: 'prs', label: 'Pull Requests', icon: GitPullRequest, desc: 'Review comments and merge lineage' },
  { id: 'adrs', label: 'ADRs', icon: FileText, desc: 'Auto-discover and link decisions' },
  { id: 'ast', label: 'Code AST', icon: Code2, desc: 'Traverse live call graphs' }
];

const tabContent: Record<string, {title: string, body: string, illustration: React.ReactNode}[]> = {
  commits: [
    { 
      title: "Commit Intelligence", 
      body: "Every git push is analyzed - message, diff, author, timestamp, and changed files become traversable graph nodes with full provenance.",
      illustration: (
        <svg viewBox="0 0 160 160" className="w-full h-full">
          <circle cx="80" cy="80" r="4" fill="var(--color-text-primary)" />
          <path d="M 80 80 L 120 40 M 80 80 L 130 80 M 80 80 L 110 130" stroke="var(--color-text-primary)" strokeWidth="1.2" fill="none" />
          <circle cx="120" cy="40" r="24" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1.5" />
          <circle cx="130" cy="80" r="20" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1.5" />
          <circle cx="110" cy="130" r="28" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1.5" />
          <rect x="30" y="70" width="40" height="20" rx="10" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1.5" />
        </svg>
      )
    },
    { 
      title: "Diff-Level Context", 
      body: "DevBrain stores which files changed in every commit, not just the message. Ask 'what touched this file in the last 6 months' and get an exact answer.",
      illustration: (
        <svg viewBox="0 0 160 160" className="w-full h-full">
          <path d="M 20 80 L 140 80" stroke="var(--color-text-primary)" strokeWidth="1.2" strokeDasharray="4 4" />
          <circle cx="50" cy="80" r="4" fill="var(--color-text-primary)" />
          <circle cx="90" cy="80" r="4" fill="var(--color-text-primary)" />
          <circle cx="130" cy="80" r="4" fill="var(--color-text-primary)" />
          <path d="M 90 80 C 110 50, 130 50, 140 50" stroke="var(--color-text-primary)" strokeWidth="1.2" fill="none" />
          <circle cx="140" cy="50" r="4" fill="var(--color-text-primary)" />
        </svg>
      )
    },
    { 
      title: "Author Graph", 
      body: "Commits link to developer nodes, building a map of who knows what. Surface the right engineer before asking a question in Slack.",
      illustration: (
        <svg viewBox="0 0 160 160" className="w-full h-full">
          <path d="M 50 60 L 80 100 L 110 60" stroke="var(--color-text-primary)" strokeWidth="1.2" fill="none" />
          <rect x="30" y="40" width="40" height="20" rx="10" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1.5" />
          <rect x="90" y="40" width="40" height="20" rx="10" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1.5" />
          <circle cx="80" cy="100" r="4" fill="var(--color-text-primary)" />
          <circle cx="80" cy="120" r="12" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1.5" />
        </svg>
      )
    },
  ],
  prs: [
    { title: "Review Comment Memory", body: "Every review comment, approval, and change-request is stored. The debate that shaped the code is permanently accessible.", illustration: null },
    { title: "Decision Provenance", body: "PR descriptions and linked issues are parsed and connected to the modules they touched. Ask 'why was this function written this way' - get the PR.", illustration: null },
    { title: "Merge Lineage", body: "Know exactly which PRs affected any file or module, in chronological order. Full audit trail, zero manual tracking.", illustration: null },
  ],
  adrs: [
    { title: "Auto-Discovery", body: "DevBrain scans /docs/decisions, /adr, /docs/adr, and /.decisions automatically. No config needed.", illustration: null },
    { title: "Module Linkage", body: "ADRs are linked to the code modules they govern via Cognee's entity extraction. Ask 'what decisions apply to the auth module' - get them all.", illustration: null },
    { title: "Supersession Tracking", body: "When ADR-12 supersedes ADR-07, the graph records the edge. You always know the current governing decision, not an outdated one.", illustration: null },
  ],
  ast: [
    { title: "Dependency Graph", body: "Functions, classes, and modules form a live call graph. See what depends on what across the entire codebase, in any language.", illustration: null },
    { title: "Impact Analysis", body: "Before changing a function, ask which modules call it. DevBrain traverses the AST graph and lists every affected path.", illustration: null },
    { title: "Cross-Source Traversal", body: "The AST graph connects to the commit and PR graphs. Find which pull requests modified a function and why - in a single query.", illustration: null },
  ]
};

export function Features() {
  const [activeTab, setActiveTab] = useState(tabs[0].id);

  React.useEffect(() => {
    const interval = setInterval(() => {
      setActiveTab((prev) => {
        const currentIndex = tabs.findIndex((tab) => tab.id === prev);
        const nextIndex = (currentIndex + 1) % tabs.length;
        return tabs[nextIndex].id;
      });
    }, 8000);

    return () => clearInterval(interval);
  }, [activeTab]);

  return (
    <section id="features" className="section-padding content-container flex flex-col items-center">
      <motion.div 
        initial={{ opacity: 0, y: 24 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-100px" }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="flex flex-col items-center text-center w-full"
      >
        <h2 className="font-display text-[32px] sm:text-[36px] md:text-[56px] lg:text-[60px] font-extrabold text-text-primary leading-[1.1] max-w-[800px] tracking-tight">
          What's inside DevBrain
        </h2>
      </motion.div>

      {/* Tabs Row */}
      <div className="flex flex-row overflow-x-auto md:overflow-visible flex-nowrap md:flex-wrap justify-start md:justify-center gap-6 md:gap-[48px] mt-[60px] w-full px-4 no-scrollbar pb-3 md:pb-0">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className="group flex flex-col items-center gap-3 relative min-w-[120px] snap-center cursor-pointer pb-3"
            >
              <Icon size={24} className={isActive ? 'text-text-primary' : 'text-text-inactive group-hover:text-text-muted transition-colors'} />
              <div className="flex flex-col items-center">
                <span className={`text-[14px] ${isActive ? 'text-text-primary font-bold' : 'text-text-inactive group-hover:text-text-muted transition-colors'}`}>
                  {tab.label}
                </span>
                
                {/* Active Underline with Loading Animation */}
                {isActive && (
                  <motion.div 
                    className="absolute bottom-0 left-0 h-[2px] bg-text-primary"
                    initial={{ width: "0%" }}
                    animate={{ width: "100%" }}
                    transition={{ duration: 8, ease: "linear" }}
                  />
                )}
              </div>
            </button>
          );
        })}
      </div>

      {/* Card Grid */}
      <div className="w-full mt-[48px] md:mt-[80px] mb-12 md:mb-20">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -16 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="grid grid-cols-1 md:grid-cols-3 gap-8 md:min-h-[480px]"
          >
            {tabContent[activeTab].map((card, idx) => (
              <div 
                key={idx}
                className="bg-bg-card rounded-[24px] p-[40px] md:p-[56px] flex flex-col h-full transition-all duration-300"
              >
                <div className="w-full h-[160px] bg-bg rounded-[16px] mb-8 overflow-hidden flex items-center justify-center shrink-0">
                  {card.illustration || (
                    <div className="opacity-20 flex flex-col gap-2 items-center">
                      <div className="w-12 h-12 rounded-full border-2 border-border flex items-center justify-center">
                        <div className="w-2 h-2 rounded-full bg-border"></div>
                      </div>
                    </div>
                  )}
                </div>
                <h3 className="font-display text-[24px] md:text-[28px] font-bold text-text-primary mb-4 leading-tight tracking-tight shrink-0">
                  {card.title}
                </h3>
                <p className="font-display text-[16px] text-text-muted leading-[1.6] grow">
                  {card.body}
                </p>
              </div>
            ))}
          </motion.div>
        </AnimatePresence>
      </div>
    </section>
  );
}
