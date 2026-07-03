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
        <svg viewBox="0 0 240 160" className="w-full h-full">
          <style>{`
            .spin-ring { animation: spin 20s infinite linear; transform-origin: 120px 80px; }
            .pulse-commit { animation: pulse-core 3s infinite ease-in-out; transform-origin: 120px 80px; }
            .flow-path { stroke-dasharray: 6 6; animation: flow-data 2s infinite linear; }
            @keyframes spin {
              from { transform: rotate(0deg); }
              to { transform: rotate(360deg); }
            }
            @keyframes pulse-core {
              0%, 100% { transform: scale(1); }
              50% { transform: scale(1.08); }
            }
            @keyframes flow-data {
              to { stroke-dashoffset: -12; }
            }
          `}</style>

          {/* Curved connecting lines */}
          <path d="M 120 80 Q 90 50 60 45" stroke="var(--color-border)" strokeWidth="1.5" fill="none" />
          <path d="M 120 80 Q 90 50 60 45" stroke="var(--color-accent-yellow, #F3FE7A)" strokeWidth="2.5" fill="none" className="flow-path" opacity="0.6" strokeLinecap="round" />

          <path d="M 120 80 Q 150 50 180 45" stroke="var(--color-border)" strokeWidth="1.5" fill="none" />
          <path d="M 120 80 Q 150 50 180 45" stroke="var(--color-accent-mint, #D8F0E4)" strokeWidth="2.5" fill="none" className="flow-path" opacity="0.6" strokeLinecap="round" />

          <path d="M 120 80 Q 90 110 60 115" stroke="var(--color-border)" strokeWidth="1.5" fill="none" />
          <path d="M 120 80 Q 90 110 60 115" stroke="var(--color-accent-peach, #FFD3BA)" strokeWidth="2.5" fill="none" className="flow-path" opacity="0.6" strokeLinecap="round" />

          <path d="M 120 80 Q 150 110 180 115" stroke="var(--color-border)" strokeWidth="1.5" fill="none" />
          <path d="M 120 80 Q 150 110 180 115" stroke="var(--color-accent-orchid, #FFBCFD)" strokeWidth="2.5" fill="none" className="flow-path" opacity="0.6" strokeLinecap="round" />

          {/* Central Commit Hub */}
          <g>
            <circle cx="120" cy="80" r="22" fill="none" stroke="var(--color-border)" strokeWidth="1.5" strokeDasharray="4 3" className="spin-ring" />
            <g className="pulse-commit">
              <circle cx="120" cy="80" r="14" fill="var(--color-accent-yellow, #F3FE7A)" stroke="var(--color-border)" strokeWidth="2" />
              <circle cx="120" cy="80" r="5" fill="var(--color-text-primary)" />
            </g>
          </g>

          {/* Metadata Nodes */}
          {/* Top-Left: Author */}
          <g transform="translate(60, 45)">
            <g>
              <circle cx="0" cy="0" r="18" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1.5" />
              <circle cx="0" cy="-3" r="4" fill="none" stroke="var(--color-text-primary)" strokeWidth="1.5" />
              <path d="M -7 6 C -7 2, -4 1, 0 1 C 4 1, 7 2, 7 6" fill="none" stroke="var(--color-text-primary)" strokeWidth="1.5" />
              <g transform="translate(0, 24)">
                <rect x="-24" y="-6" width="48" height="12" rx="4" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1" />
                <text x="0" y="2" textAnchor="middle" fontSize="7" fontWeight="bold" fill="var(--color-text-muted)">@author</text>
              </g>
            </g>
          </g>

          {/* Top-Right: Files */}
          <g transform="translate(180, 45)">
            <g>
              <rect x="-16" y="-18" width="32" height="36" rx="6" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1.5" />
              <rect x="-8" y="-10" width="16" height="20" rx="2" fill="none" stroke="var(--color-text-primary)" strokeWidth="1.5" />
              <line x1="-4" y1="-5" x2="4" y2="-5" stroke="var(--color-text-primary)" strokeWidth="1" />
              <line x1="-4" y1="0" x2="4" y2="0" stroke="var(--color-text-primary)" strokeWidth="1" />
              <line x1="-4" y1="5" x2="1" y2="5" stroke="var(--color-text-primary)" strokeWidth="1" />
              <g transform="translate(0, 24)">
                <rect x="-24" y="-6" width="48" height="12" rx="4" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1" />
                <text x="0" y="2" textAnchor="middle" fontSize="7" fontWeight="bold" fill="var(--color-text-muted)">2 files</text>
              </g>
            </g>
          </g>

          {/* Bottom-Left: Timestamp */}
          <g transform="translate(60, 115)">
            <g>
              <rect x="-18" y="-18" width="36" height="36" rx="8" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1.5" />
              <circle cx="0" cy="0" r="10" fill="none" stroke="var(--color-text-primary)" strokeWidth="1.5" />
              <polyline points="0,-5 0,0 4,2" fill="none" stroke="var(--color-text-primary)" strokeWidth="1.5" strokeLinecap="round" />
              <g transform="translate(0, 24)">
                <rect x="-24" y="-6" width="48" height="12" rx="4" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1" />
                <text x="0" y="2" textAnchor="middle" fontSize="7" fontWeight="bold" fill="var(--color-text-muted)">12m ago</text>
              </g>
            </g>
          </g>

          {/* Bottom-Right: Commit Message */}
          <g transform="translate(180, 115)">
            <g>
              <rect x="-18" y="-18" width="36" height="36" rx="8" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1.5" />
              <rect x="-10" y="-8" width="20" height="14" rx="3" fill="none" stroke="var(--color-text-primary)" strokeWidth="1.5" />
              <path d="M -5 6 L -8 10 L -8 6" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1.5" />
              <line x1="-6" y1="-3" x2="6" y2="-3" stroke="var(--color-text-primary)" strokeWidth="1" />
              <line x1="-6" y1="2" x2="3" y2="2" stroke="var(--color-text-primary)" strokeWidth="1" />
              <g transform="translate(0, 24)">
                <rect x="-24" y="-6" width="48" height="12" rx="4" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1" />
                <text x="0" y="2" textAnchor="middle" fontSize="7" fontWeight="bold" fill="var(--color-text-muted)">feat: auth</text>
              </g>
            </g>
          </g>
        </svg>
      )
    },
    { 
      title: "Diff-Level Context", 
      body: "DevBrain stores which files changed in every commit, not just the message. Ask 'what touched this file in the last 6 months' and get an exact answer.",
      illustration: (
        <svg viewBox="0 0 240 160" className="w-full h-full">
          <style>{`
            .diff-added-overlay { fill: #22c55e; fill-opacity: 0.08; animation: pulse-green 3s infinite ease-in-out; }
            .diff-removed-overlay { fill: #ef4444; fill-opacity: 0.08; animation: pulse-red 3s infinite ease-in-out; }
            .code-line { stroke-linecap: round; }
            @keyframes pulse-green {
              0%, 100% { fill-opacity: 0.06; }
              50% { fill-opacity: 0.16; }
            }
            @keyframes pulse-red {
              0%, 100% { fill-opacity: 0.06; }
              50% { fill-opacity: 0.16; }
            }
          `}</style>
          
          {/* Main IDE Window Background */}
          <rect x="20" y="15" width="200" height="130" rx="8" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1.5" />
          
          {/* Header Bar Background (slightly darker/offset with rounded top corners) */}
          <path d="M 20.75 23 C 20.75 19, 24 15.75, 28 15.75 L 212 15.75 C 216 15.75, 219.25 19, 219.25 23 L 219.25 40 L 20.75 40 Z" fill="var(--color-bg-card)" opacity="0.5" />
          
          {/* Header bottom separator line */}
          <line x1="20" y1="40" x2="220" y2="40" stroke="var(--color-border)" strokeWidth="1" />
          
          {/* Tab 1: utils.ts (Active) */}
          {/* Folder-style Tab shape: rounded top corners, flat bottom */}
          <path d="M 30 40 L 30 24 A 4 4 0 0 1 34 20 L 96 20 A 4 4 0 0 1 100 24 L 100 40 Z" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1" />
          {/* Erase the bottom border of the active tab to connect it to the editor area */}
          <line x1="30.5" y1="40" x2="99.5" y2="40" stroke="var(--color-bg)" strokeWidth="1.5" />
          {/* Mini File Icon (Dog-eared page) */}
          <path d="M 37 34 L 37 26 L 41 26 L 43 28 L 43 34 Z" fill="none" stroke="var(--color-text-primary)" strokeWidth="1" strokeLinejoin="round" />
          <path d="M 41 26 L 41 28 L 43 28" fill="none" stroke="var(--color-text-primary)" strokeWidth="1" strokeLinejoin="round" />
          {/* Text */}
          <text x="69" y="33" textAnchor="middle" fontSize="7.5" fontWeight="bold" fill="var(--color-text-primary)">utils.ts</text>
          
          {/* Tab 2: main.py (Inactive) */}
          <path d="M 106 40 L 106 24 A 4 4 0 0 1 110 20 L 172 20 A 4 4 0 0 1 176 24 L 176 40 Z" fill="none" />
          {/* Mini File Icon (Dog-eared page) */}
          <path d="M 113 34 L 113 26 L 117 26 L 119 28 L 119 34 Z" fill="none" stroke="var(--color-text-inactive)" strokeWidth="1" strokeLinejoin="round" />
          <path d="M 117 26 L 117 28 L 119 28" fill="none" stroke="var(--color-text-inactive)" strokeWidth="1" strokeLinejoin="round" />
          {/* Text */}
          <text x="145" y="33" textAnchor="middle" fontSize="7.5" fill="var(--color-text-inactive)">main.py</text>
          
          {/* Left Gutter separator */}
          <line x1="48" y1="40" x2="48" y2="145" stroke="var(--color-border)" strokeWidth="1" opacity="0.6" />
          
          {/* Scrollbar on right */}
          <rect x="212" y="46" width="3" height="92" rx="1.5" fill="var(--color-bg-card)" opacity="0.5" />
          <rect x="212" y="55" width="3" height="30" rx="1.5" fill="var(--color-text-inactive)" opacity="0.3" />

          {/* Line Gutter numbers */}
          <text x="34" y="56" textAnchor="middle" fontSize="7" fill="var(--color-text-inactive)">14</text>
          <text x="34" y="68" textAnchor="middle" fontSize="7" fill="var(--color-text-inactive)">15</text>
          
          <text x="34" y="86" textAnchor="middle" fontSize="7" fill="var(--color-text-inactive)">16</text>
          
          <text x="34" y="99" textAnchor="middle" fontSize="7" fill="var(--color-text-inactive)">17</text>
          <text x="34" y="112" textAnchor="middle" fontSize="7" fill="var(--color-text-inactive)">18</text>
          <text x="34" y="125" textAnchor="middle" fontSize="7" fill="var(--color-text-inactive)">19</text>

          {/* Removed Overlay Block (Red) */}
          <rect x="21" y="45" width="190" height="28" className="diff-removed-overlay" />
          <text x="44" y="56" textAnchor="middle" fontSize="7" fill="#ef4444" fontWeight="bold" opacity="0.75">-</text>
          <text x="44" y="68" textAnchor="middle" fontSize="7" fill="#ef4444" fontWeight="bold" opacity="0.75">-</text>
          
          <line x1="56" y1="53" x2="100" y2="53" stroke="#ef4444" strokeWidth="2.5" className="code-line" />
          <line x1="106" y1="53" x2="150" y2="53" stroke="var(--color-text-inactive)" strokeWidth="2.5" className="code-line" opacity="0.5" />
          <line x1="56" y1="65" x2="120" y2="65" stroke="#ef4444" strokeWidth="2.5" className="code-line" />

          {/* Neutral line */}
          <line x1="56" y1="83" x2="170" y2="83" stroke="var(--color-text-inactive)" strokeWidth="2.5" className="code-line" opacity="0.6" />

          {/* Added Overlay Block (Green) */}
          <rect x="21" y="89" width="190" height="42" className="diff-added-overlay" />
          <text x="44" y="99" textAnchor="middle" fontSize="7" fill="#22c55e" fontWeight="bold" opacity="0.75">+</text>
          <text x="44" y="112" textAnchor="middle" fontSize="7" fill="#22c55e" fontWeight="bold" opacity="0.75">+</text>
          <text x="44" y="125" textAnchor="middle" fontSize="7" fill="#22c55e" fontWeight="bold" opacity="0.75">+</text>
          
          <line x1="56" y1="96" x2="115" y2="96" stroke="#22c55e" strokeWidth="2.5" className="code-line" />
          <line x1="121" y1="96" x2="185" y2="96" stroke="var(--color-text-muted)" strokeWidth="2.5" className="code-line" />
          <line x1="56" y1="109" x2="160" y2="109" stroke="#22c55e" strokeWidth="2.5" className="code-line" />
          <line x1="56" y1="122" x2="95" y2="122" stroke="#22c55e" strokeWidth="2.5" className="code-line" />
        </svg>
      )
    },
    { 
      title: "Author Graph", 
      body: "Commits link to developer nodes, building a map of who knows what. Surface the right engineer before asking a question in Slack.",
      illustration: (
        <svg viewBox="0 0 240 160" className="w-full h-full svg-theme">
          <style>{`
            .svg-theme {
              --svg-mint: #2EA44F;
              --svg-peach: #F05032;
              --svg-orchid: #8250DF;
              --svg-powder: #0288d1;
              --svg-sage: #558b2f;
            }
            .pulse-dev-1 { animation: pulse-dev 4s infinite ease-in-out; transform-origin: center; }
            .pulse-dev-2 { animation: pulse-dev 4s infinite ease-in-out; animation-delay: 2s; transform-origin: center; }
            .flow-line-a { stroke-dasharray: 5 5; animation: flow-a 2.5s infinite linear; }
            .flow-line-b { stroke-dasharray: 5 5; animation: flow-b 2.5s infinite linear; }
            @keyframes pulse-dev {
              0%, 100% { transform: scale(1); }
              50% { transform: scale(1.08); }
            }
            @keyframes flow-a {
              to { stroke-dashoffset: -10; }
            }
            @keyframes flow-b {
              to { stroke-dashoffset: 10; }
            }
          `}</style>

          {/* Connection Curves */}
          {/* Dev A to Shared File */}
          <path d="M 70 80 Q 95 40 120 40" stroke="var(--color-border)" strokeWidth="1.5" fill="none" />
          <path d="M 70 80 Q 95 40 120 40" stroke="var(--svg-mint)" strokeWidth="2.5" fill="none" strokeLinecap="round" className="flow-line-a" opacity="0.75" />

          {/* Dev B to Shared File */}
          <path d="M 170 80 Q 145 40 120 40" stroke="var(--color-border)" strokeWidth="1.5" fill="none" />
          <path d="M 170 80 Q 145 40 120 40" stroke="var(--svg-peach)" strokeWidth="2.5" fill="none" strokeLinecap="round" className="flow-line-b" opacity="0.75" />

          {/* Dev A to File A */}
          <path d="M 70 80 Q 60 105 50 125" stroke="var(--color-border)" strokeWidth="1.5" fill="none" />
          <path d="M 70 80 Q 60 105 50 125" stroke="var(--svg-mint)" strokeWidth="2.5" fill="none" strokeLinecap="round" className="flow-line-a" opacity="0.75" />

          {/* Dev B to File B */}
          <path d="M 170 80 Q 180 105 190 125" stroke="var(--color-border)" strokeWidth="1.5" fill="none" />
          <path d="M 170 80 Q 180 105 190 125" stroke="var(--svg-peach)" strokeWidth="2.5" fill="none" strokeLinecap="round" className="flow-line-b" opacity="0.75" />

          {/* Developers Nodes */}
          {/* Dev A (Alice) */}
          <g transform="translate(70, 80)">
            <g className="pulse-dev-1">
              <circle cx="0" cy="0" r="16" fill="var(--color-bg)" stroke="var(--svg-mint)" strokeWidth="2.5" />
              <circle cx="0" cy="-3" r="4" fill="none" stroke="var(--color-text-primary)" strokeWidth="1.5" />
              <path d="M -6 5 C -6 2, -3 1, 0 1 C 3 1, 6 2, 6 5" fill="none" stroke="var(--color-text-primary)" strokeWidth="1.5" />
              <text x="0" y="24" textAnchor="middle" fontSize="8" fontWeight="bold" fill="var(--color-text-primary)">Alice</text>
            </g>
          </g>

          {/* Dev B (Bob) */}
          <g transform="translate(170, 80)">
            <g className="pulse-dev-2">
              <circle cx="0" cy="0" r="16" fill="var(--color-bg)" stroke="var(--svg-peach)" strokeWidth="2.5" />
              <circle cx="0" cy="-3" r="4" fill="none" stroke="var(--color-text-primary)" strokeWidth="1.5" />
              <path d="M -6 5 C -6 2, -3 1, 0 1 C 3 1, 6 2, 6 5" fill="none" stroke="var(--color-text-primary)" strokeWidth="1.5" />
              <text x="0" y="24" textAnchor="middle" fontSize="8" fontWeight="bold" fill="var(--color-text-primary)">Bob</text>
            </g>
          </g>

          {/* File Nodes */}
          {/* Shared File: auth.ts */}
          <g transform="translate(120, 40)">
            <g>
              <rect x="-14" y="-12" width="28" height="24" rx="4" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1.5" />
              <text x="0" y="3" textAnchor="middle" fontSize="7" fontWeight="bold" fill="var(--color-text-primary)" fontFamily="var(--font-mono)">auth</text>
              <rect x="-18" y="-19" width="36" height="10" rx="3" fill="var(--color-bg)" stroke="var(--svg-powder)" strokeWidth="1.5" />
              <text x="0" y="-12" textAnchor="middle" fontSize="6" fontWeight="bold" fill="var(--color-text-primary)">SHARED</text>
            </g>
          </g>

          {/* Alice's File: router.py */}
          <g transform="translate(50, 125)">
            <g>
              <rect x="-14" y="-10" width="28" height="20" rx="4" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1.5" />
              <text x="0" y="3" textAnchor="middle" fontSize="7" fontWeight="bold" fill="var(--color-text-primary)" fontFamily="var(--font-mono)">route</text>
              <rect x="-10" y="-16" width="20" height="8" rx="2" fill="var(--color-bg)" stroke="var(--svg-orchid)" strokeWidth="1.5" />
              <text x="0" y="-10" textAnchor="middle" fontSize="5" fontWeight="bold" fill="var(--color-text-primary)">PY</text>
            </g>
          </g>

          {/* Bob's File: db.sql */}
          <g transform="translate(190, 125)">
            <g>
              <rect x="-14" y="-10" width="28" height="20" rx="4" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1.5" />
              <text x="0" y="3" textAnchor="middle" fontSize="7" fontWeight="bold" fill="var(--color-text-primary)" fontFamily="var(--font-mono)">db</text>
              <rect x="-10" y="-16" width="20" height="8" rx="2" fill="var(--color-bg)" stroke="var(--svg-sage)" strokeWidth="1.5" />
              <text x="0" y="-10" textAnchor="middle" fontSize="5" fontWeight="bold" fill="var(--color-text-primary)">SQL</text>
            </g>
          </g>
        </svg>
      )
    },
  ],
  prs: [
    { 
      title: "Review Comment Memory", 
      body: "Every review comment, approval, and change-request is stored. The debate that shaped the code is permanently accessible.", 
      illustration: (
        <svg viewBox="0 0 240 160" className="w-full h-full svg-theme">
          <style>{`
            .svg-theme {
              --svg-mint: #2EA44F;
              --svg-peach: #F05032;
              --svg-yellow: #F7DF1E;
            }
          `}</style>
          
          {/* Code Editor Panel on the left */}
          <rect x="15" y="20" width="105" height="120" rx="6" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1" />
          {/* Gutter divider */}
          <line x1="38" y1="20" x2="38" y2="140" stroke="var(--color-border)" strokeWidth="1" opacity="0.4" />
          
          {/* Gutter Line Numbers */}
          <text x="26" y="44" textAnchor="middle" fontSize="6.5" fill="var(--color-text-inactive)">24</text>
          <text x="26" y="58" textAnchor="middle" fontSize="6.5" fill="var(--color-text-inactive)">25</text>
          <text x="26" y="72" textAnchor="middle" fontSize="6.5" fill="var(--color-text-inactive)">26</text>
          <text x="26" y="86" textAnchor="middle" fontSize="6.5" fill="var(--color-text-inactive)">27</text>
          <text x="26" y="100" textAnchor="middle" fontSize="6.5" fill="var(--color-text-inactive)">28</text>
          <text x="26" y="114" textAnchor="middle" fontSize="6.5" fill="var(--color-text-inactive)">29</text>

          {/* Commented Code Line Highlight (Line 25) */}
          <rect x="39" y="48" width="80" height="14" fill="var(--svg-yellow)" opacity="0.15" />
          
          {/* Code lines representation */}
          <line x1="44" y1="41" x2="105" y2="41" stroke="var(--color-text-inactive)" strokeWidth="2.5" strokeLinecap="round" opacity="0.6" />
          <line x1="44" y1="55" x2="85" y2="55" stroke="var(--color-text-primary)" strokeWidth="2.5" strokeLinecap="round" />
          <line x1="44" y1="69" x2="112" y2="69" stroke="var(--color-text-inactive)" strokeWidth="2.5" strokeLinecap="round" opacity="0.6" />
          <line x1="44" y1="83" x2="95" y2="83" stroke="var(--color-text-inactive)" strokeWidth="2.5" strokeLinecap="round" opacity="0.6" />
          <line x1="44" y1="97" x2="110" y2="97" stroke="var(--color-text-inactive)" strokeWidth="2.5" strokeLinecap="round" opacity="0.6" />
          <line x1="44" y1="111" x2="75" y2="111" stroke="var(--color-text-inactive)" strokeWidth="2.5" strokeLinecap="round" opacity="0.6" />

          {/* Dotted link indicator from code to bubble thread */}
          <circle cx="89" cy="55" r="2" fill="var(--svg-peach)" stroke="var(--color-border)" strokeWidth="0.8" />
          <path d="M 91 55 Q 112 55 135 45" stroke="var(--color-border)" strokeWidth="1" strokeDasharray="3 2" fill="none" opacity="0.8" />

          {/* thread alignment indicator between Alice and Bob */}
          <path d="M 140 67 L 140 77 M 140 77 L 142 77" stroke="var(--color-border)" strokeWidth="1" strokeDasharray="2 1" fill="none" opacity="0.6" />

          {/* Bubble 1 (Alice - Reviewer) */}
          <g transform="translate(135, 25)">
            <rect x="0" y="0" width="85" height="42" rx="6" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1.2" />
            <circle cx="11" cy="11" r="5" fill="var(--svg-mint)" stroke="var(--color-border)" strokeWidth="1" />
            <text x="11" y="13.5" textAnchor="middle" fontSize="6.5" fontWeight="bold" fill="#FEFEF3">A</text>
            <text x="21" y="13" fontSize="6.5" fontWeight="bold" fill="var(--color-text-primary)">@alice</text>
            <text x="48" y="13" fontSize="5.5" fill="var(--color-text-inactive)">2h ago</text>
            <rect x="68" y="7" width="13" height="7" rx="1.5" fill="var(--svg-mint)" opacity="0.2" />
            <text x="74.5" y="12.5" textAnchor="middle" fontSize="4.5" fontWeight="bold" fill="var(--svg-mint)">REV</text>
            
            <line x1="8" y1="24" x2="77" y2="24" stroke="var(--color-text-muted)" strokeWidth="2.5" strokeLinecap="round" />
            <line x1="8" y1="32" x2="55" y2="32" stroke="var(--color-text-inactive)" strokeWidth="2.5" strokeLinecap="round" />
          </g>

          {/* Bubble 2 (Bob - Author - Reply) */}
          <g transform="translate(142, 77)">
            <rect x="0" y="0" width="78" height="42" rx="6" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1.2" />
            <circle cx="11" cy="11" r="5" fill="var(--svg-peach)" stroke="var(--color-border)" strokeWidth="1" />
            <text x="11" y="13.5" textAnchor="middle" fontSize="6.5" fontWeight="bold" fill="#FEFEF3">B</text>
            <text x="21" y="13" fontSize="6.5" fontWeight="bold" fill="var(--color-text-primary)">@bob</text>
            <text x="45" y="13" fontSize="5.5" fill="var(--color-text-inactive)">1h ago</text>
            
            <line x1="8" y1="24" x2="70" y2="24" stroke="var(--color-text-muted)" strokeWidth="2.5" strokeLinecap="round" />
            <line x1="8" y1="32" x2="45" y2="32" stroke="var(--color-text-inactive)" strokeWidth="2.5" strokeLinecap="round" />
          </g>
        </svg>
      )
    },
    { 
      title: "Decision Provenance", 
      body: "PR descriptions and linked issues are parsed and connected to the modules they touched. Ask 'why was this function written this way' - get the PR.", 
      illustration: (
        <svg viewBox="0 0 240 160" className="w-full h-full svg-theme">
          <style>{`
            .svg-theme {
              --svg-mint: #2EA44F;
              --svg-peach: #F05032;
              --svg-orchid: #8250DF;
              --svg-yellow: #F7DF1E;
            }
            .trail-dot { animation: travel 3s infinite linear; }
            @keyframes travel {
              0% { offset-distance: 0%; }
              100% { offset-distance: 100%; }
            }
          `}</style>
          
          <path id="provenance-path" d="M 45 80 Q 82.5 30 120 80 T 195 80" fill="none" stroke="none" />
          <path d="M 45 80 Q 82.5 30 120 80 T 195 80" fill="none" stroke="var(--color-border)" strokeWidth="1.5" strokeDasharray="4 4" />
 
          <circle r="4" fill="var(--color-text-primary)" className="trail-dot">
            <animateMotion dur="3s" repeatCount="indefinite">
              <mpath href="#provenance-path" />
            </animateMotion>
          </circle>
 
          <g transform="translate(45, 80)">
            <circle cx="0" cy="0" r="22" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="2" />
            <path d="M 0 -9 L 9 7 L -9 7 Z" fill="var(--svg-peach)" stroke="var(--color-border)" strokeWidth="1.5" strokeLinejoin="round" />
            <line x1="0" y1="-2" x2="0" y2="2" stroke="var(--color-text-primary)" strokeWidth="1.5" strokeLinecap="round" />
            <circle cx="0" cy="4.5" r="0.8" fill="var(--color-text-primary)" />
            <text x="0" y="32" textAnchor="middle" fontSize="10" fontWeight="bold" fill="var(--color-text-muted)">Issue</text>
          </g>
 
          <g transform="translate(120, 80)">
            <circle cx="0" cy="0" r="22" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="2" />
            <circle cx="-4" cy="5" r="2.2" fill="none" stroke="var(--svg-orchid)" strokeWidth="1.5" />
            <circle cx="-4" cy="-5" r="2.2" fill="none" stroke="var(--svg-orchid)" strokeWidth="1.5" />
            <circle cx="4" cy="-5" r="2.2" fill="none" stroke="var(--svg-orchid)" strokeWidth="1.5" />
            <line x1="-4" y1="2.8" x2="-4" y2="-2.8" stroke="var(--svg-orchid)" strokeWidth="1.5" />
            <path d="M -4 1 Q 2 1 4 -2.8" fill="none" stroke="var(--svg-orchid)" strokeWidth="1.5" />
            <text x="0" y="32" textAnchor="middle" fontSize="10" fontWeight="bold" fill="var(--color-text-muted)">PR #42</text>
          </g>
 
          <g transform="translate(195, 80)">
            <circle cx="0" cy="0" r="22" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="2" />
            <rect x="-8" y="-8" width="16" height="16" rx="3" fill="var(--svg-yellow)" stroke="var(--color-border)" strokeWidth="1.5" />
            <text x="0" y="3" textAnchor="middle" fontSize="9" fontWeight="bold" fill="var(--color-text-primary)" fontFamily="var(--font-mono)">JS</text>
            <text x="0" y="32" textAnchor="middle" fontSize="10" fontWeight="bold" fill="var(--color-text-muted)">Module</text>
          </g>
        </svg>
      )
    },
    { 
      title: "Merge Lineage", 
      body: "Know exactly which PRs affected any file or module, in chronological order. Full audit trail, zero manual tracking.", 
      illustration: (
        <svg viewBox="0 0 240 160" className="w-full h-full svg-theme">
          <style>{`
            .svg-theme {
              --svg-mint: #2EA44F;
              --svg-orchid: #8250DF;
              --svg-peach: #F05032;
            }
            .pulse-merge {
              animation: merge-glow 3s infinite ease-in-out;
            }
            @keyframes merge-glow {
              0%, 100% { opacity: 0.7; }
              50% { opacity: 1; }
            }
          `}</style>

          {/* Branch Track Labels */}
          <text x="15" y="74" fontSize="7" fontWeight="bold" fill="var(--color-text-inactive)">main</text>
          <text x="75" y="108" textAnchor="middle" fontSize="6.5" fontWeight="bold" fill="var(--svg-mint)">feat/pay</text>
          <text x="175" y="28" textAnchor="middle" fontSize="6.5" fontWeight="bold" fill="var(--svg-orchid)">feat/auth</text>

          {/* Dotted lines mapping Merge Commits to PR Tags */}
          <line x1="120" y1="80" x2="120" y2="40" stroke="var(--color-border)" strokeWidth="1" strokeDasharray="2 2" />
          <line x1="220" y1="80" x2="220" y2="120" stroke="var(--color-border)" strokeWidth="1" strokeDasharray="2 2" />

          {/* Main trunk line */}
          <line x1="20" y1="80" x2="225" y2="80" stroke="var(--color-text-inactive)" strokeWidth="2.5" strokeLinecap="round" opacity="0.4" />

          {/* feat/pay branch lines (smooth S-curves) */}
          <path d="M 30 80 C 42 80, 50 120, 62 120" fill="none" stroke="var(--svg-mint)" strokeWidth="2.5" strokeLinecap="round" />
          <line x1="62" y1="120" x2="88" y2="120" stroke="var(--svg-mint)" strokeWidth="2.5" strokeLinecap="round" />
          <path d="M 88 120 C 100 120, 108 80, 120 80" fill="none" stroke="var(--svg-mint)" strokeWidth="2.5" strokeLinecap="round" />

          {/* feat/auth branch lines (smooth S-curves) */}
          <path d="M 130 80 C 142 80, 150 40, 162 40" fill="none" stroke="var(--svg-orchid)" strokeWidth="2.5" strokeLinecap="round" />
          <line x1="162" y1="40" x2="188" y2="40" stroke="var(--svg-orchid)" strokeWidth="2.5" strokeLinecap="round" />
          <path d="M 188 40 C 200 40, 208 80, 220 80" fill="none" stroke="var(--svg-orchid)" strokeWidth="2.5" strokeLinecap="round" />

          {/* Commit Nodes */}
          {/* Parent commit (main) */}
          <circle cx="30" cy="80" r="4.5" fill="var(--color-bg)" stroke="var(--color-text-inactive)" strokeWidth="2" />
          <text x="30" y="93" textAnchor="middle" fontSize="5.5" fontFamily="var(--font-mono)" fill="var(--color-text-inactive)">f2b8d0</text>

          {/* Feature commit E (feat/pay) */}
          <circle cx="75" cy="120" r="4.5" fill="var(--color-bg)" stroke="var(--svg-mint)" strokeWidth="2" />
          <text x="75" y="133" textAnchor="middle" fontSize="5.5" fontFamily="var(--font-mono)" fill="var(--color-text-inactive)">a4c7e9</text>

          {/* Merge Commit 1 (PR #32) */}
          <g className="pulse-merge">
            <circle cx="120" cy="80" r="6" fill="var(--color-bg)" stroke="var(--svg-mint)" strokeWidth="2" />
            <circle cx="120" cy="80" r="2.2" fill="var(--svg-mint)" />
          </g>
          <text x="120" y="93" textAnchor="middle" fontSize="5.5" fontFamily="var(--font-mono)" fill="var(--color-text-inactive)">8f9d0c</text>

          {/* Intermediate commit (main) */}
          <circle cx="130" cy="80" r="4.5" fill="var(--color-bg)" stroke="var(--color-text-inactive)" strokeWidth="2" />

          {/* Feature commit F (feat/auth) */}
          <circle cx="175" cy="40" r="4.5" fill="var(--color-bg)" stroke="var(--svg-orchid)" strokeWidth="2" />
          <text x="175" y="53" textAnchor="middle" fontSize="5.5" fontFamily="var(--font-mono)" fill="var(--color-text-inactive)">c5e6f1</text>

          {/* Merge Commit 2 (PR #42) */}
          <g className="pulse-merge">
            <circle cx="220" cy="80" r="6" fill="var(--color-bg)" stroke="var(--svg-orchid)" strokeWidth="2" />
            <circle cx="220" cy="80" r="2.2" fill="var(--svg-orchid)" />
          </g>
          <text x="220" y="93" textAnchor="middle" fontSize="5.5" fontFamily="var(--font-mono)" fill="var(--color-text-inactive)">b2d4f5</text>

          {/* Metadata Tags */}
          {/* PR #32 Tag */}
          <g transform="translate(120, 26)">
            <rect x="-20" y="-7" width="40" height="14" rx="3" fill="var(--color-bg)" stroke="none" />
            <rect x="-20" y="-7" width="3" height="14" rx="1" fill="var(--svg-mint)" stroke="none" />
            <text x="1" y="2.5" textAnchor="middle" fontSize="6.5" fontWeight="bold" fill="var(--color-text-primary)">PR #32</text>
            <rect x="-20" y="-7" width="40" height="14" rx="3" fill="none" stroke="var(--color-border)" strokeWidth="1" />
          </g>

          {/* PR #42 Tag */}
          <g transform="translate(220, 134)">
            <rect x="-20" y="-7" width="40" height="14" rx="3" fill="var(--color-bg)" stroke="none" />
            <rect x="-20" y="-7" width="3" height="14" rx="1" fill="var(--svg-orchid)" stroke="none" />
            <text x="1" y="2.5" textAnchor="middle" fontSize="6.5" fontWeight="bold" fill="var(--color-text-primary)">PR #42</text>
            <rect x="-20" y="-7" width="40" height="14" rx="3" fill="none" stroke="var(--color-border)" strokeWidth="1" />
          </g>
        </svg>)
    },
  ],
  adrs: [
    { 
      title: "Auto-Discovery", 
      body: "DevBrain scans /docs/decisions, /adr, /docs/adr, and /.decisions automatically. No config needed.", 
      illustration: (
        <svg viewBox="0 0 240 160" className="w-full h-full svg-theme">
          <style>{`
            .svg-theme {
              --svg-mint: #2EA44F;
              --svg-peach: #F05032;
              --svg-orchid: #8250DF;
              --svg-yellow: #F7DF1E;
            }
            .scan-line { animation: sweep 3s infinite linear; }
            .found-node { animation: glow-node 3s infinite ease-in-out; }
            .found-text { animation: glow-text 3s infinite ease-in-out; }
            @keyframes sweep {
              0% { transform: translateY(-10px); opacity: 0; }
              15% { opacity: 0.8; }
              85% { opacity: 0.8; }
              100% { transform: translateY(145px); opacity: 0; }
            }
            @keyframes glow-node {
              0%, 100% { stroke: var(--color-border); }
              50% { stroke: var(--svg-mint); filter: drop-shadow(0 0 3px var(--svg-mint)); }
            }
            @keyframes glow-text {
              0%, 100% { fill: var(--color-text-inactive); }
              50% { fill: var(--svg-mint); }
            }
          `}</style>

          {/* Directory Tree Structure */}
          {/* Tree branch connections */}
          <line x1="80" y1="36" x2="80" y2="130" stroke="var(--color-border)" strokeWidth="1.2" strokeDasharray="2 2" />
          <line x1="80" y1="55" x2="92" y2="55" stroke="var(--color-border)" strokeWidth="1.2" strokeDasharray="2 2" />
          <line x1="80" y1="105" x2="92" y2="105" stroke="var(--color-border)" strokeWidth="1.2" strokeDasharray="2 2" />
          <line x1="80" y1="130" x2="92" y2="130" stroke="var(--color-border)" strokeWidth="1.2" strokeDasharray="2 2" />
          
          <line x1="100" y1="61" x2="100" y2="80" stroke="var(--color-border)" strokeWidth="1.2" strokeDasharray="2 2" />
          <line x1="100" y1="80" x2="112" y2="80" stroke="var(--color-border)" strokeWidth="1.2" strokeDasharray="2 2" />
          
          <line x1="120" y1="86" x2="120" y2="105" stroke="var(--color-border)" strokeWidth="1.2" strokeDasharray="2 2" />
          <line x1="120" y1="105" x2="134" y2="105" stroke="var(--color-border)" strokeWidth="1.2" strokeDasharray="2 2" />

          {/* Root Folder: devbrain */}
          <g transform="translate(80, 30)">
            <path d="M -8 -6 L -3 -6 L -1 -4 L 8 -4 L 8 6 L -8 6 Z" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1.2" />
          </g>
          <text x="92" y="33" fontSize="6.5" fontWeight="bold" fill="var(--color-text-primary)">devbrain</text>

          {/* Subfolder: docs */}
          <g transform="translate(100, 55)">
            <path d="M -8 -6 L -3 -6 L -1 -4 L 8 -4 L 8 6 L -8 6 Z" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1.2" />
          </g>
          <text x="112" y="58" fontSize="6" fill="var(--color-text-primary)">docs</text>

          {/* Subfolder: adr */}
          <g transform="translate(120, 80)">
            <path d="M -8 -6 L -3 -6 L -1 -4 L 8 -4 L 8 6 L -8 6 Z" fill="var(--color-bg)" stroke="var(--svg-orchid)" strokeWidth="1.2" />
          </g>
          <text x="132" y="83" fontSize="6" fontWeight="bold" fill="var(--svg-orchid)">adr</text>

          {/* ADR File: 0001-auth.md (glowing file) */}
          <g transform="translate(140, 105)">
            <path d="M -5 -7 L 1 -7 L 5 -3 L 5 7 L -5 7 Z" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1.2" className="found-node" />
            <path d="M 1 -7 L 1 -3 L 5 -3 Z" fill="none" stroke="var(--color-border)" strokeWidth="0.8" />
          </g>
          <text x="150" y="108" fontSize="6" fontWeight="bold" fill="var(--color-text-inactive)" className="found-text">0001-auth.md</text>

          {/* Subfolder: backend */}
          <g transform="translate(100, 105)">
            <path d="M -8 -6 L -3 -6 L -1 -4 L 8 -4 L 8 6 L -8 6 Z" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1.2" opacity="0.6" />
          </g>
          <text x="112" y="108" fontSize="6" fill="var(--color-text-inactive)">backend</text>

          {/* Subfolder: frontend */}
          <g transform="translate(100, 130)">
            <path d="M -8 -6 L -3 -6 L -1 -4 L 8 -4 L 8 6 L -8 6 Z" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1.2" opacity="0.6" />
          </g>
          <text x="112" y="133" fontSize="6" fill="var(--color-text-inactive)">frontend</text>

          {/* Sweeping Laser Line */}
          <g className="scan-line" style={{ transformOrigin: "center" }}>
            <line x1="20" y1="20" x2="220" y2="20" stroke="var(--svg-mint)" strokeWidth="2.5" opacity="0.85" style={{ filter: "drop-shadow(0 0 4px var(--svg-mint))" }} />
            <rect x="20" y="20" width="200" height="8" fill="var(--svg-mint)" opacity="0.08" />
          </g>
        </svg>
      )
    },
    { 
      title: "Module Linkage", 
      body: "ADRs are linked to the code modules they govern via Cognee's entity extraction. Ask 'what decisions apply to the auth module' - get them all.", 
      illustration: (
        <svg viewBox="0 0 240 160" className="w-full h-full svg-theme">
          <style>{`
            .svg-theme {
              --svg-mint: #2EA44F;
              --svg-peach: #F05032;
            }
            .pulse-link { stroke-dasharray: 6 3; animation: line-flow 1.5s infinite linear; }
            @keyframes line-flow {
              to { stroke-dashoffset: -9; }
            }
          `}</style>
          
          <path d="M 70 80 C 110 50, 130 110, 170 80" stroke="var(--color-border)" strokeWidth="2" fill="none" className="pulse-link" />
          <path d="M 70 80 C 110 50, 130 110, 170 80" stroke="var(--svg-peach)" strokeWidth="2.5" fill="none" strokeLinecap="round" className="pulse-link" opacity="0.8" />

          <g transform="translate(70, 80)">
            <rect x="-24" y="-30" width="48" height="60" rx="6" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="2" />
            <rect x="-16" y="-20" width="32" height="6" fill="var(--svg-peach)" rx="1" />
            <line x1="-16" y1="-5" x2="16" y2="-5" stroke="var(--color-text-muted)" strokeWidth="1.5" />
            <line x1="-16" y1="5" x2="10" y2="5" stroke="var(--color-text-muted)" strokeWidth="1.5" />
            <line x1="-16" y1="15" x2="4" y2="15" stroke="var(--color-text-muted)" strokeWidth="1.5" />
            <text x="0" y="44" textAnchor="middle" fontSize="10" fontWeight="bold" fill="var(--color-text-muted)">ADR-10</text>
          </g>

          <g transform="translate(170, 80)">
            <rect x="-24" y="-24" width="48" height="48" rx="8" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="2" />
            <path d="M -12 -6 L 0 -12 L 12 -6 L 12 6 L 0 12 L -12 6 Z" fill="var(--svg-mint)" stroke="var(--color-border)" strokeWidth="1.2" />
            <line x1="0" y1="-12" x2="0" y2="12" stroke="var(--color-border)" strokeWidth="1.2" />
            <line x1="-12" y1="-6" x2="0" y2="0" stroke="var(--color-border)" strokeWidth="1.2" />
            <line x1="12" y1="-6" x2="0" y2="0" stroke="var(--color-border)" strokeWidth="1.2" />
            <text x="0" y="38" textAnchor="middle" fontSize="10" fontWeight="bold" fill="var(--color-text-muted)">auth.ts</text>
          </g>
        </svg>
      )
    },
    { 
      title: "Supersession Tracking", 
      body: "When ADR-12 supersedes ADR-07, the graph records the edge. You always know the current governing decision, not an outdated one.", 
      illustration: (
        <svg viewBox="0 0 240 160" className="w-full h-full svg-theme">
          <style>{`
            .svg-theme {
              --svg-mint: #2EA44F;
              --svg-peach: #F05032;
              --svg-yellow: #F7DF1E;
            }
            .deprecate-cross { stroke-dasharray: 100; stroke-dashoffset: 100; animation: strike 2.5s infinite ease-in-out; }
            @keyframes strike {
              0%, 15% { stroke-dashoffset: 100; opacity: 0; }
              50%, 100% { stroke-dashoffset: 0; opacity: 1; }
            }
          `}</style>
          
          <g transform="translate(60, 80)">
            <rect x="-20" y="-28" width="40" height="56" rx="4" fill="var(--color-bg)" stroke="var(--color-text-inactive)" strokeWidth="1.5" strokeDasharray="3 3" opacity="0.6" />
            <line x1="-12" y1="-16" x2="12" y2="-16" stroke="var(--color-text-inactive)" strokeWidth="1.5" opacity="0.6" />
            <line x1="-12" y1="-8" x2="6" y2="-8" stroke="var(--color-text-inactive)" strokeWidth="1.5" opacity="0.6" />
            <text x="0" y="42" textAnchor="middle" fontSize="9" fontWeight="bold" fill="var(--color-text-inactive)">ADR-07</text>
            
            <line x1="-24" y1="-32" x2="24" y2="32" stroke="#ef4444" strokeWidth="2.5" className="deprecate-cross" />
            <line x1="24" y1="-32" x2="-24" y2="32" stroke="#ef4444" strokeWidth="2.5" className="deprecate-cross" />
          </g>

          <g>
            <path d="M 150 80 L 105 80" stroke="var(--color-border)" strokeWidth="1.5" strokeDasharray="4 4" />
            <path d="M 105 80 L 112 75 M 105 80 L 112 85" stroke="var(--color-border)" strokeWidth="1.5" />
            <rect x="105" y="58" width="45" height="13" rx="3" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1" />
            <text x="127.5" y="67" textAnchor="middle" fontSize="6" fontWeight="bold" fill="var(--color-text-primary)">SUPERSEDES</text>
          </g>

          <g transform="translate(180, 80)">
            <rect x="-20" y="-28" width="40" height="56" rx="4" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="2" />
            <rect x="-12" y="-18" width="24" height="5" fill="var(--svg-yellow)" rx="1" />
            <line x1="-12" y1="-6" x2="12" y2="-6" stroke="var(--color-text-muted)" strokeWidth="1.5" />
            <line x1="-12" y1="2" x2="8" y2="2" stroke="var(--color-text-muted)" strokeWidth="1.5" />
            <line x1="-12" y1="10" x2="0" y2="10" stroke="var(--color-text-muted)" strokeWidth="1.5" />
            <text x="0" y="42" textAnchor="middle" fontSize="9" fontWeight="bold" fill="var(--color-text-primary)">ADR-12</text>
          </g>
        </svg>
      )
    },
  ],
  ast: [
    { 
      title: "Dependency Graph", 
      body: "Functions, classes, and modules form a live call graph. See what depends on what across the entire codebase, in any language.", 
      illustration: (
        <svg viewBox="0 0 240 160" className="w-full h-full svg-theme">
          <style>{`
            .svg-theme {
              --svg-mint: #2EA44F;
              --svg-peach: #F05032;
              --svg-orchid: #8250DF;
              --svg-yellow: #F7DF1E;
            }
            .flow-dep { stroke-dasharray: 4 4; animation: flow 2s infinite linear; }
            .pulse-app { animation: breathe 3s infinite ease-in-out; transform-origin: 50px 80px; }
            @keyframes flow {
              to { stroke-dashoffset: -8; }
            }
            @keyframes breathe {
              0%, 100% { transform: scale(1); }
              50% { transform: scale(1.05); }
            }
          `}</style>
          
          <line x1="50" y1="80" x2="110" y2="40" stroke="var(--color-border)" strokeWidth="1.5" />
          <line x1="50" y1="80" x2="110" y2="40" stroke="var(--svg-orchid)" strokeWidth="2.5" className="flow-dep" opacity="0.75" />

          <line x1="50" y1="80" x2="110" y2="120" stroke="var(--color-border)" strokeWidth="1.5" />
          <line x1="50" y1="80" x2="110" y2="120" stroke="var(--svg-orchid)" strokeWidth="2.5" className="flow-dep" opacity="0.75" />

          <line x1="110" y1="40" x2="180" y2="40" stroke="var(--color-border)" strokeWidth="1.5" />
          <line x1="110" y1="40" x2="180" y2="40" stroke="var(--svg-mint)" strokeWidth="2.5" className="flow-dep" opacity="0.75" />

          <line x1="110" y1="120" x2="180" y2="120" stroke="var(--color-border)" strokeWidth="1.5" />
          <line x1="110" y1="120" x2="180" y2="120" stroke="var(--svg-yellow)" strokeWidth="2.5" className="flow-dep" opacity="0.75" />

          <line x1="180" y1="40" x2="180" y2="120" stroke="var(--color-border)" strokeWidth="1.5" strokeDasharray="3 3" />
          <line x1="110" y1="40" x2="110" y2="120" stroke="var(--color-border)" strokeWidth="1.5" />

          <g transform="translate(50, 80)" className="pulse-app">
            <circle cx="0" cy="0" r="16" fill="var(--svg-orchid)" stroke="var(--color-border)" strokeWidth="2.5" />
            <text x="0" y="3" textAnchor="middle" fontSize="9" fontWeight="bold" fill="#FEFEF3" fontFamily="var(--font-mono)">App</text>
          </g>

          <g transform="translate(110, 40)">
            <circle cx="0" cy="0" r="14" fill="var(--color-bg)" stroke="var(--svg-orchid)" strokeWidth="2" />
            <text x="0" y="3" textAnchor="middle" fontSize="7.5" fontWeight="bold" fill="var(--color-text-primary)" fontFamily="var(--font-mono)">Router</text>
          </g>

          <g transform="translate(110, 120)">
            <circle cx="0" cy="0" r="14" fill="var(--color-bg)" stroke="var(--svg-orchid)" strokeWidth="2" />
            <text x="0" y="3" textAnchor="middle" fontSize="7.5" fontWeight="bold" fill="var(--color-text-primary)" fontFamily="var(--font-mono)">Store</text>
          </g>

          <g transform="translate(180, 40)">
            <circle cx="0" cy="0" r="12" fill="var(--color-bg)" stroke="var(--svg-mint)" strokeWidth="1.8" />
            <text x="0" y="3" textAnchor="middle" fontSize="7" fill="var(--color-text-muted)" fontFamily="var(--font-mono)">Auth</text>
          </g>

          <g transform="translate(180, 120)">
            <circle cx="0" cy="0" r="12" fill="var(--color-bg)" stroke="var(--svg-yellow)" strokeWidth="1.8" />
            <text x="0" y="3" textAnchor="middle" fontSize="7" fill="var(--color-text-muted)" fontFamily="var(--font-mono)">Db</text>
          </g>
        </svg>
      )
    },
    { 
      title: "Impact Analysis", 
      body: "Before changing a function, ask which modules call it. DevBrain traverses the AST graph and lists every affected path.", 
      illustration: (
        <svg viewBox="0 0 240 160" className="w-full h-full svg-theme">
          <style>{`
            .svg-theme {
              --svg-mint: #2EA44F;
              --svg-peach: #F05032;
              --svg-orchid: #8250DF;
            }
            .impact-pulse { animation: pulse-impact 3s infinite ease-in-out; }
            .impact-path { stroke-dasharray: 8 4; animation: path-flow 2s infinite linear; }
            @keyframes pulse-impact {
              0%, 100% { filter: none; }
              50% { filter: drop-shadow(0 0 4px var(--svg-peach)); }
            }
            @keyframes path-flow {
              to { stroke-dashoffset: -12; }
            }
          `}</style>
          
          <path d="M 60 80 Q 110 40 160 40" stroke="var(--color-border)" strokeWidth="1.5" fill="none" />
          <path d="M 60 80 Q 110 120 160 120" stroke="var(--color-border)" strokeWidth="1.5" fill="none" />
          <path d="M 60 80 L 160 80" stroke="var(--color-border)" strokeWidth="1.5" fill="none" />
          
          <path d="M 60 80 Q 110 40 160 40" stroke="var(--svg-peach)" strokeWidth="2.5" fill="none" opacity="0.8" className="impact-path" />
          <path d="M 60 80 L 160 80" stroke="var(--svg-peach)" strokeWidth="2.5" fill="none" opacity="0.8" className="impact-path" />

          <g transform="translate(60, 80)">
            <circle cx="0" cy="0" r="18" fill="var(--svg-peach)" stroke="var(--color-border)" strokeWidth="2" />
            <text x="0" y="3" textAnchor="middle" fontSize="8" fontWeight="bold" fill="#FEFEF3" fontFamily="var(--font-mono)">EDIT</text>
          </g>

          <g transform="translate(160, 40)" className="impact-pulse">
            <circle cx="0" cy="0" r="14" fill="var(--color-bg)" stroke="var(--svg-orchid)" strokeWidth="2" />
            <text x="0" y="3" textAnchor="middle" fontSize="7" fontWeight="bold" fill="var(--color-text-primary)" fontFamily="var(--font-mono)">api.ts</text>
          </g>

          <g transform="translate(160, 80)" className="impact-pulse">
            <circle cx="0" cy="0" r="14" fill="var(--color-bg)" stroke="var(--svg-orchid)" strokeWidth="2" />
            <text x="0" y="3" textAnchor="middle" fontSize="7" fontWeight="bold" fill="var(--color-text-primary)" fontFamily="var(--font-mono)">web.ts</text>
          </g>

          <g transform="translate(160, 120)">
            <circle cx="0" cy="0" r="14" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1.5" opacity="0.4" />
            <text x="0" y="3" textAnchor="middle" fontSize="7" fill="var(--color-text-inactive)" fontFamily="var(--font-mono)">db.ts</text>
          </g>
        </svg>
      )
    },
    { 
      title: "Cross-Source Traversal", 
      body: "The AST graph connects to the commit and PR graphs. Find which pull requests modified a function and why - in a single query.", 
      illustration: (
        <svg viewBox="0 0 240 160" className="w-full h-full svg-theme">
          <style>{`
            .svg-theme {
              --svg-mint: #2EA44F;
              --svg-peach: #F05032;
              --svg-orchid: #8250DF;
              --svg-yellow: #F7DF1E;
            }
            .orbiting-group { animation: rotate-orbit 6s infinite linear; transform-origin: 0px 0px; }
            @keyframes rotate-orbit {
              from { transform: rotate(0deg); }
              to { transform: rotate(360deg); }
            }
          `}</style>
          
          <polygon points="120,40 65,115 175,115" fill="none" stroke="var(--color-border)" strokeWidth="1.5" strokeDasharray="4 4" />
          
          <circle cx="120" cy="90" r="50" fill="none" stroke="var(--color-border)" strokeWidth="1.5" opacity="0.3" />

          <circle cx="120" cy="90" r="18" fill="var(--color-bg)" stroke="var(--color-border)" strokeWidth="1.5" />
          <text x="120" y="93" textAnchor="middle" fontSize="8" fontWeight="bold" fill="var(--color-text-primary)" fontFamily="var(--font-mono)">TRAVERSE</text>

          <g transform="translate(120, 40)">
            <circle cx="0" cy="0" r="18" fill="var(--svg-mint)" stroke="var(--color-border)" strokeWidth="2.5" />
            <text x="0" y="3.5" textAnchor="middle" fontSize="10" fontWeight="bold" fill="#FEFEF3">{"{ }"}</text>
            <text x="0" y="-22" textAnchor="middle" fontSize="8" fontWeight="bold" fill="var(--color-text-muted)">AST</text>
          </g>

          <g transform="translate(65, 115)">
            <circle cx="0" cy="0" r="18" fill="var(--svg-yellow)" stroke="var(--color-border)" strokeWidth="2.5" />
            <circle cx="0" cy="0" r="4" fill="none" stroke="var(--color-text-primary)" strokeWidth="2" />
            <line x1="-9" y1="0" x2="-4" y2="0" stroke="var(--color-text-primary)" strokeWidth="2" />
            <line x1="4" y1="0" x2="9" y2="0" stroke="var(--color-text-primary)" strokeWidth="2" />
            <text x="0" y="28" textAnchor="middle" fontSize="8" fontWeight="bold" fill="var(--color-text-muted)">Commit</text>
          </g>

          <g transform="translate(175, 115)">
            <circle cx="0" cy="0" r="18" fill="var(--svg-orchid)" stroke="var(--color-border)" strokeWidth="2.5" />
            <circle cx="-4" cy="4" r="2.5" fill="none" stroke="#FEFEF3" strokeWidth="1.5" />
            <circle cx="4" cy="-4" r="2.5" fill="none" stroke="#FEFEF3" strokeWidth="1.5" />
            <line x1="-4" y1="1.5" x2="-4" y2="-4" stroke="#FEFEF3" strokeWidth="1.5" />
            <path d="M -4 -4 Q 4 -4 4 -1.5" fill="none" stroke="#FEFEF3" strokeWidth="1.5" />
            <text x="0" y="28" textAnchor="middle" fontSize="8" fontWeight="bold" fill="var(--color-text-muted)">PR</text>
          </g>

          <g transform="translate(120, 90)">
            <g className="orbiting-group">
              <circle cx="50" cy="0" r="4.5" fill="var(--svg-peach)" />
              <circle cx="50" cy="0" r="8" fill="none" stroke="var(--svg-peach)" strokeWidth="1.2" opacity="0.5" />
            </g>
          </g>
        </svg>
      )
    }
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
              className="group flex flex-col items-center gap-2 sm:gap-3 relative min-w-[80px] sm:min-w-[120px] snap-center cursor-pointer pb-2 sm:pb-3"
            >
              <Icon className={`w-5 h-5 sm:w-6 sm:h-6 ${isActive ? 'text-text-primary' : 'text-text-inactive group-hover:text-text-muted transition-colors'}`} />
              <div className="relative pb-1 flex flex-col items-center">
                <span className={`text-[12px] sm:text-[14px] ${isActive ? 'text-text-primary font-bold' : 'text-text-inactive group-hover:text-text-muted transition-colors'}`}>
                  {tab.label}
                </span>
                
                {/* Active Underline with Loading Animation */}
                {isActive && (
                  <motion.div 
                    className="absolute bottom-0 left-0 right-0 h-[2px] bg-text-primary"
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
                <div className="w-full h-[200px] mb-8 overflow-hidden flex items-center justify-center shrink-0">
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
