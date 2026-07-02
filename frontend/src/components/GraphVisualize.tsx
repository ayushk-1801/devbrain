import React, { useRef, useState, useEffect, useCallback } from 'react';
import * as d3 from 'd3';
import { motion, AnimatePresence } from 'motion/react';
import {
  Network, Search, Loader2, AlertCircle, X, ZoomIn, ZoomOut,
  Maximize2, Link as LinkIcon, GitCommit, GitPullRequest, User,
  FileText, BookOpen, Box, Code, Layers, AlertTriangle, Tag,
  ArrowLeft, Info, BarChart3, ChevronDown
} from 'lucide-react';

// ─── Types ─────────────────────────────────────────────────────────────────────

interface GraphNode {
  id: string;
  type: string;
  name: string;
  description?: string;
  [key: string]: unknown;
}

interface GraphEdge {
  source: string;
  target: string;
  relationship_name?: string;
  relationship?: string;
  [key: string]: unknown;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

interface SimNode extends d3.SimulationNodeDatum, GraphNode {
  x: number;
  y: number;
  fx?: number | null;
  fy?: number | null;
  connectionCount: number;
}

interface SimLink extends d3.SimulationLinkDatum<SimNode> {
  relationship_name: string;
  [key: string]: unknown;
}

// ─── Node Color Palette ────────────────────────────────────────────────────────

const NODE_COLORS: Record<string, string> = {
  Commit: '#F3FE7A', // yellow
  PullRequest: '#FFD3BA', // peach
  Developer: '#D8F0E4', // mint
  File: '#CFE3EA', // powder
  ADR: '#D9E7C9', // sage
  Module: '#D9E7C9', // sage
  Function: '#CFE3EA', // powder
  Class: '#D9E7C9', // sage
  Issue: '#F3FE7A', // yellow
  Entity: '#D8F0E4', // mint
  EntityType: '#B8D4C4', // darker mint
  DefaultDocument: '#CFE3EA', // powder
  DocumentChunk: '#A9C7D0', // darker powder
  TextSummary: '#FFD3BA', // peach
  TextDocument: '#CFE3EA', // powder
  default: '#E0E0D0',
};

const NODE_ICONS: Record<string, typeof GitCommit> = {
  Commit: GitCommit,
  PullRequest: GitPullRequest,
  Developer: User,
  File: FileText,
  ADR: BookOpen,
  Module: Box,
  Function: Code,
  Class: Layers,
  Issue: AlertTriangle,
};

function getNodeColor(type: string): string {
  return NODE_COLORS[type] || NODE_COLORS.default;
}

function getNodeRadius(connectionCount: number): number {
  return Math.max(6, Math.min(24, 6 + connectionCount * 2));
}

// ─── Component ─────────────────────────────────────────────────────────────────

export default function GraphVisualize() {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const simulationRef = useRef<d3.Simulation<SimNode, SimLink> | null>(null);
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null);

  const [url, setUrl] = useState('http://localhost:8000');
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<SimNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<SimNode | null>(null);
  const [tooltipPos, setTooltipPos] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [showLegend, setShowLegend] = useState(true);
  const [showStats, setShowStats] = useState(true);
  const [graphRendered, setGraphRendered] = useState(false);

  // ─── Fetch Graph Data ──────────────────────────────────────────────────────

  const fetchGraph = useCallback(async () => {
    if (!url.trim()) return;
    setLoading(true);
    setError(null);
    setSelectedNode(null);
    setGraphRendered(false);

    try {
      const cleanUrl = url.replace(/\/+$/, '');
      const res = await fetch(`${cleanUrl}/graph`);
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      const data: GraphData = await res.json();

      if (!data.nodes || !data.edges) {
        throw new Error('Invalid graph data: missing nodes or edges');
      }
      if (data.nodes.length === 0) {
        throw new Error('Graph is empty — no nodes found. Try ingesting some data first.');
      }

      setGraphData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch graph data');
    } finally {
      setLoading(false);
    }
  }, [url]);

  // ─── Stats Computation ────────────────────────────────────────────────────

  const stats = graphData ? {
    totalNodes: graphData.nodes.length,
    totalEdges: graphData.edges.length,
    byType: graphData.nodes.reduce((acc, n) => {
      acc[n.type] = (acc[n.type] || 0) + 1;
      return acc;
    }, {} as Record<string, number>),
    edgeTypes: graphData.edges.reduce((acc, e) => {
      const rel = e.relationship_name || e.relationship || 'unknown';
      acc[rel] = (acc[rel] || 0) + 1;
      return acc;
    }, {} as Record<string, number>),
  } : null;

  // ─── D3 Graph Rendering ───────────────────────────────────────────────────

  useEffect(() => {
    if (!graphData || !svgRef.current || !containerRef.current) return;

    const svg = d3.select(svgRef.current);
    const container = containerRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight;

    // Clear previous render
    svg.selectAll('*').remove();

    // ─── Build node map with connection counts ────────────────────────
    const connectionCounts = new Map<string, number>();
    graphData.edges.forEach(e => {
      connectionCounts.set(e.source, (connectionCounts.get(e.source) || 0) + 1);
      connectionCounts.set(e.target, (connectionCounts.get(e.target) || 0) + 1);
    });

    const simNodes: SimNode[] = graphData.nodes.map(n => ({
      ...n,
      x: width / 2 + (Math.random() - 0.5) * width * 0.6,
      y: height / 2 + (Math.random() - 0.5) * height * 0.6,
      connectionCount: connectionCounts.get(n.id) || 0,
    }));

    const nodeById = new Map(simNodes.map(n => [n.id, n]));

    const simLinks: SimLink[] = graphData.edges
      .filter(e => nodeById.has(e.source) && nodeById.has(e.target))
      .map(e => ({
        ...e,
        source: e.source,
        target: e.target,
        relationship_name: e.relationship_name || e.relationship || 'RELATED_TO',
      }));

    // ─── SVG setup ────────────────────────────────────────────────────
    svg.attr('width', width).attr('height', height);

    // Defs for markers, filters and gradients
    const defs = svg.append('defs');

    // Arrow markers
    defs.append('marker')
      .attr('id', 'arrowhead')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 20)
      .attr('refY', 0)
      .attr('markerWidth', 8)
      .attr('markerHeight', 8)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', 'var(--color-text-muted)')
      .attr('opacity', 0.5);

    defs.append('marker')
      .attr('id', 'arrowhead-highlight')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 20)
      .attr('refY', 0)
      .attr('markerWidth', 8)
      .attr('markerHeight', 8)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', 'var(--color-accent-mint)')
      .attr('opacity', 0.9);

    // Glow filter
    const glowFilter = defs.append('filter')
      .attr('id', 'glow')
      .attr('x', '-50%').attr('y', '-50%')
      .attr('width', '200%').attr('height', '200%');
    glowFilter.append('feGaussianBlur')
      .attr('stdDeviation', '4')
      .attr('result', 'coloredBlur');
    const glowMerge = glowFilter.append('feMerge');
    glowMerge.append('feMergeNode').attr('in', 'coloredBlur');
    glowMerge.append('feMergeNode').attr('in', 'SourceGraphic');

    // Highlight glow filter
    const highlightFilter = defs.append('filter')
      .attr('id', 'highlight-glow')
      .attr('x', '-80%').attr('y', '-80%')
      .attr('width', '260%').attr('height', '260%');
    highlightFilter.append('feGaussianBlur')
      .attr('stdDeviation', '8')
      .attr('result', 'coloredBlur');
    const highlightMerge = highlightFilter.append('feMerge');
    highlightMerge.append('feMergeNode').attr('in', 'coloredBlur');
    highlightMerge.append('feMergeNode').attr('in', 'SourceGraphic');

    // Main group for zoom/pan
    const g = svg.append('g').attr('class', 'graph-container');

    // ─── Links ────────────────────────────────────────────────────────
    const linkGroup = g.append('g').attr('class', 'links');

    const linkLines = linkGroup.selectAll<SVGLineElement, SimLink>('line')
      .data(simLinks)
      .join('line')
      .attr('stroke', 'var(--color-text-muted)')
      .attr('stroke-opacity', 0.15)
      .attr('stroke-width', 1)
      .attr('marker-end', 'url(#arrowhead)');

    const linkLabels = linkGroup.selectAll<SVGTextElement, SimLink>('text')
      .data(simLinks)
      .join('text')
      .text(d => (d as SimLink).relationship_name)
      .attr('font-size', '8px')
      .attr('font-family', 'var(--font-mono)')
      .attr('fill', 'var(--color-text-muted)')
      .attr('opacity', 0)
      .attr('text-anchor', 'middle')
      .attr('dy', '-4');

    // ─── Nodes ────────────────────────────────────────────────────────
    const nodeGroup = g.append('g').attr('class', 'nodes');

    const nodeGs = nodeGroup.selectAll<SVGGElement, SimNode>('g')
      .data(simNodes)
      .join('g')
      .attr('class', 'node-group')
      .style('cursor', 'pointer');

    // Outer glow ring
    nodeGs.append('circle')
      .attr('class', 'node-glow')
      .attr('r', d => getNodeRadius(d.connectionCount) + 4)
      .attr('fill', d => getNodeColor(d.type))
      .attr('opacity', 0.15)
      .attr('filter', 'url(#glow)');

    // Main node circle
    nodeGs.append('circle')
      .attr('class', 'node-circle')
      .attr('r', d => getNodeRadius(d.connectionCount))
      .attr('fill', d => getNodeColor(d.type))
      .attr('stroke', d => d3.color(getNodeColor(d.type))?.darker(0.4)?.toString() || '#888')
      .attr('stroke-width', 1.5)
      .attr('opacity', 0.9);

    // Node labels
    nodeGs.append('text')
      .text(d => {
        const label = d.name || d.id;
        return label.length > 16 ? label.slice(0, 14) + '…' : label;
      })
      .attr('font-size', d => Math.max(8, Math.min(12, getNodeRadius(d.connectionCount) * 0.8)) + 'px')
      .attr('font-family', 'var(--font-mono)')
      .attr('fill', 'var(--color-text-primary)')
      .attr('text-anchor', 'middle')
      .attr('dy', d => getNodeRadius(d.connectionCount) + 14)
      .attr('opacity', 0.7)
      .attr('pointer-events', 'none');

    // ─── Interactions ─────────────────────────────────────────────────

    // Hover
    nodeGs
      .on('mouseenter', function (event: MouseEvent, d: SimNode) {
        setHoveredNode(d);
        setTooltipPos({ x: event.clientX, y: event.clientY });

        // Enlarge hovered node
        d3.select(this).select('.node-circle')
          .transition().duration(200)
          .attr('r', getNodeRadius(d.connectionCount) * 1.3)
          .attr('filter', 'url(#highlight-glow)');
        d3.select(this).select('.node-glow')
          .transition().duration(200)
          .attr('r', getNodeRadius(d.connectionCount) * 1.3 + 6)
          .attr('opacity', 0.35);

        // Show connected edge labels
        linkLabels
          .filter((l: SimLink) => {
            const src = typeof l.source === 'object' ? (l.source as SimNode).id : l.source;
            const tgt = typeof l.target === 'object' ? (l.target as SimNode).id : l.target;
            return src === d.id || tgt === d.id;
          })
          .transition().duration(200)
          .attr('opacity', 0.8);

        // Highlight connected edges
        linkLines
          .filter((l: SimLink) => {
            const src = typeof l.source === 'object' ? (l.source as SimNode).id : l.source;
            const tgt = typeof l.target === 'object' ? (l.target as SimNode).id : l.target;
            return src === d.id || tgt === d.id;
          })
          .transition().duration(200)
          .attr('stroke-opacity', 0.6)
          .attr('stroke-width', 2)
          .attr('marker-end', 'url(#arrowhead-highlight)');
      })
      .on('mousemove', (event: MouseEvent) => {
        setTooltipPos({ x: event.clientX, y: event.clientY });
      })
      .on('mouseleave', function (_event: MouseEvent, d: SimNode) {
        setHoveredNode(null);

        d3.select(this).select('.node-circle')
          .transition().duration(300)
          .attr('r', getNodeRadius(d.connectionCount))
          .attr('filter', null);
        d3.select(this).select('.node-glow')
          .transition().duration(300)
          .attr('r', getNodeRadius(d.connectionCount) + 4)
          .attr('opacity', 0.15);

        // Reset edges if no selected node
        if (!selectedNode) {
          linkLabels.transition().duration(300).attr('opacity', 0);
          linkLines.transition().duration(300)
            .attr('stroke-opacity', 0.15)
            .attr('stroke-width', 1)
            .attr('marker-end', 'url(#arrowhead)');
        }
      });

    // Click to select/highlight connections
    nodeGs.on('click', (_event: MouseEvent, d: SimNode) => {
      setSelectedNode(prev => prev?.id === d.id ? null : d);

      const isDeselecting = selectedNode?.id === d.id;

      if (isDeselecting) {
        // Reset all
        nodeGs.select('.node-circle').transition().duration(300).attr('opacity', 0.9);
        nodeGs.select('.node-glow').transition().duration(300).attr('opacity', 0.15);
        linkLines.transition().duration(300)
          .attr('stroke-opacity', 0.15).attr('stroke-width', 1).attr('marker-end', 'url(#arrowhead)');
        linkLabels.transition().duration(300).attr('opacity', 0);
      } else {
        // Dim non-connected
        const connectedIds = new Set<string>([d.id]);
        simLinks.forEach(l => {
          const src = typeof l.source === 'object' ? (l.source as SimNode).id : l.source as string;
          const tgt = typeof l.target === 'object' ? (l.target as SimNode).id : l.target as string;
          if (src === d.id) connectedIds.add(tgt);
          if (tgt === d.id) connectedIds.add(src);
        });

        nodeGs.select('.node-circle')
          .transition().duration(300)
          .attr('opacity', (n: SimNode) => connectedIds.has(n.id) ? 1 : 0.15);
        nodeGs.select('.node-glow')
          .transition().duration(300)
          .attr('opacity', (n: SimNode) => connectedIds.has(n.id) ? 0.35 : 0.03);

        linkLines
          .transition().duration(300)
          .attr('stroke-opacity', (l: SimLink) => {
            const src = typeof l.source === 'object' ? (l.source as SimNode).id : l.source as string;
            const tgt = typeof l.target === 'object' ? (l.target as SimNode).id : l.target as string;
            return (src === d.id || tgt === d.id) ? 0.7 : 0.03;
          })
          .attr('stroke-width', (l: SimLink) => {
            const src = typeof l.source === 'object' ? (l.source as SimNode).id : l.source as string;
            const tgt = typeof l.target === 'object' ? (l.target as SimNode).id : l.target as string;
            return (src === d.id || tgt === d.id) ? 2.5 : 0.5;
          })
          .attr('marker-end', (l: SimLink) => {
            const src = typeof l.source === 'object' ? (l.source as SimNode).id : l.source as string;
            const tgt = typeof l.target === 'object' ? (l.target as SimNode).id : l.target as string;
            return (src === d.id || tgt === d.id) ? 'url(#arrowhead-highlight)' : 'url(#arrowhead)';
          });

        linkLabels
          .transition().duration(300)
          .attr('opacity', (l: SimLink) => {
            const src = typeof l.source === 'object' ? (l.source as SimNode).id : l.source as string;
            const tgt = typeof l.target === 'object' ? (l.target as SimNode).id : l.target as string;
            return (src === d.id || tgt === d.id) ? 0.9 : 0;
          });
      }
    });

    // ─── Drag behavior ────────────────────────────────────────────────
    const drag = d3.drag<SVGGElement, SimNode>()
      .on('start', (event, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on('drag', (event, d) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on('end', (event, d) => {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      });

    nodeGs.call(drag);

    // ─── Zoom behavior ────────────────────────────────────────────────
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 8])
      .on('zoom', (event) => {
        g.attr('transform', event.transform.toString());
      });

    svg.call(zoom);
    zoomRef.current = zoom;

    // ─── Force simulation ─────────────────────────────────────────────
    const simulation = d3.forceSimulation<SimNode>(simNodes)
      .force('link', d3.forceLink<SimNode, SimLink>(simLinks)
        .id(d => d.id)
        .distance(d => {
          const srcNode = typeof d.source === 'object' ? d.source : nodeById.get(d.source as string);
          const tgtNode = typeof d.target === 'object' ? d.target : nodeById.get(d.target as string);
          const maxConnections = Math.max(srcNode?.connectionCount || 0, tgtNode?.connectionCount || 0);
          return 180 + maxConnections * 12;
        })
        .strength(0.4))
      .force('charge', d3.forceManyBody<SimNode>().strength(-800).distanceMax(1000))
      .force('center', d3.forceCenter(width / 2, height / 2).strength(0.02))
      .force('collision', d3.forceCollide<SimNode>().radius(d => getNodeRadius(d.connectionCount) + 45))
      .force('x', d3.forceX(width / 2).strength(0.015))
      .force('y', d3.forceY(height / 2).strength(0.015))
      .alpha(1)
      .alphaDecay(0.015);

    simulation.on('tick', () => {
      linkLines
        .attr('x1', d => (d.source as SimNode).x)
        .attr('y1', d => (d.source as SimNode).y)
        .attr('x2', d => (d.target as SimNode).x)
        .attr('y2', d => (d.target as SimNode).y);

      linkLabels
        .attr('x', d => ((d.source as SimNode).x + (d.target as SimNode).x) / 2)
        .attr('y', d => ((d.source as SimNode).y + (d.target as SimNode).y) / 2);

      nodeGs.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    simulationRef.current = simulation;

    // Fit to view after simulation settles a bit
    setTimeout(() => {
      const bounds = (g.node() as SVGGElement)?.getBBox();
      if (bounds) {
        const dx = bounds.width;
        const dy = bounds.height;
        const x = bounds.x;
        const y = bounds.y;
        const padding = 80;
        const scale = Math.min(
          0.9,
          Math.min(width / (dx + padding * 2), height / (dy + padding * 2))
        );
        const tx = width / 2 - scale * (x + dx / 2);
        const ty = height / 2 - scale * (y + dy / 2);

        svg.transition().duration(1000)
          .call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(scale));
      }
      setGraphRendered(true);
    }, 2000);

    // Subtle pulse animation via CSS
    const style = document.createElement('style');
    style.textContent = `
      @keyframes nodeGlowPulse {
        0%, 100% { opacity: 0.15; }
        50% { opacity: 0.25; }
      }
      .node-glow {
        animation: nodeGlowPulse 3s ease-in-out infinite;
      }
    `;
    document.head.appendChild(style);

    return () => {
      simulation.stop();
      style.remove();
    };
  }, [graphData]); // eslint-disable-line react-hooks/exhaustive-deps

  // ─── Zoom Controls ─────────────────────────────────────────────────────────

  const handleZoom = useCallback((direction: 'in' | 'out' | 'fit') => {
    if (!svgRef.current || !zoomRef.current) return;
    const svg = d3.select(svgRef.current);
    const zoom = zoomRef.current;

    if (direction === 'fit') {
      svg.transition().duration(750)
        .call(zoom.transform, d3.zoomIdentity);
    } else {
      const factor = direction === 'in' ? 1.5 : 0.67;
      svg.transition().duration(300)
        .call(zoom.scaleBy, factor);
    }
  }, []);

  // ─── Keyboard shortcut for Enter ──────────────────────────────────────────

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') fetchGraph();
  }, [fetchGraph]);

  // ─── Unique node types from current data ──────────────────────────────────

  const nodeTypes = graphData
    ? [...new Set(graphData.nodes.map(n => n.type))].sort()
    : Object.keys(NODE_COLORS).filter(k => k !== 'default');

  // ─── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="relative w-screen h-screen overflow-hidden bg-bg" ref={containerRef}>
      {/* ─── SVG Canvas ──────────────────────────────────────────────── */}
      <svg
        ref={svgRef}
        className="absolute inset-0 w-full h-full"
        style={{ background: 'var(--color-bg)' }}
      />

      {/* ─── Grid overlay for empty state ───────────────────────────── */}
      {!graphData && !loading && (
        <div className="absolute inset-0 pointer-events-none" style={{
          backgroundImage: `radial-gradient(circle, var(--color-text-inactive) 1px, transparent 1px)`,
          backgroundSize: '40px 40px',
          opacity: 0.3,
        }} />
      )}

      {/* ─── Top Control Bar ─────────────────────────────────────────── */}
      <motion.div
        initial={{ y: -60, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        className="absolute top-4 left-4 right-4 z-30"
      >
        <div className="mx-auto max-w-3xl">
          <div
            className="flex items-center gap-3 px-4 py-2.5 rounded-2xl border backdrop-blur-xl"
            style={{
              background: 'color-mix(in srgb, var(--color-bg-card) 75%, transparent)',
              borderColor: 'color-mix(in srgb, var(--color-border) 30%, transparent)',
              boxShadow: '0 8px 32px rgba(0,0,0,0.08), 0 0 0 1px rgba(255,255,255,0.05) inset',
            }}
          >
            {/* Back button */}
            <a
              href="/"
              className="flex items-center gap-1.5 text-text-muted hover:text-text-primary transition-colors shrink-0"
            >
              <ArrowLeft size={16} />
              <span className="font-mono text-xs hidden sm:inline">Home</span>
            </a>

            <div className="w-px h-6 bg-border/30 shrink-0" />

            {/* Logo */}
            <div className="flex items-center gap-2 shrink-0">
              <Network size={18} className="text-text-primary" />
              <span className="font-mono text-sm font-bold text-text-primary hidden sm:inline">Graph</span>
            </div>

            <div className="w-px h-6 bg-border/30 shrink-0" />

            {/* URL Input */}
            <div className="flex-1 flex items-center gap-2 min-w-0">
              <LinkIcon size={14} className="text-text-muted shrink-0" />
              <input
                type="text"
                value={url}
                onChange={e => setUrl(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Backend URL (e.g. http://localhost:8000)"
                className="flex-1 bg-transparent text-text-primary font-mono text-sm outline-none placeholder:text-text-inactive min-w-0"
              />
            </div>

            {/* Fetch Button */}
            <button
              onClick={fetchGraph}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-1.5 rounded-xl font-mono text-xs font-semibold transition-all duration-200 shrink-0 cursor-pointer disabled:cursor-not-allowed"
              style={{
                background: loading ? 'var(--color-bg-secondary)' : 'var(--color-btn-dark)',
                color: loading ? 'var(--color-text-muted)' : 'var(--color-btn-dark-text)',
              }}
            >
              {loading ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Search size={14} />
              )}
              <span className="hidden sm:inline">{loading ? 'Loading…' : 'Fetch'}</span>
            </button>
          </div>
        </div>
      </motion.div>

      {/* ─── Empty State ─────────────────────────────────────────────── */}
      <AnimatePresence>
        {!graphData && !loading && !error && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.4 }}
            className="absolute inset-0 flex items-center justify-center z-10"
          >
            <div className="text-center max-w-md px-6">
              <motion.div
                animate={{
                  rotate: [0, 5, -5, 0],
                  scale: [1, 1.05, 1],
                }}
                transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
                className="inline-block mb-6"
              >
                <div
                  className="w-24 h-24 rounded-3xl flex items-center justify-center border"
                  style={{
                    background: 'color-mix(in srgb, var(--color-accent-yellow) 15%, var(--color-bg-card))',
                    borderColor: 'color-mix(in srgb, var(--color-accent-yellow) 30%, transparent)',
                  }}
                >
                  <Network size={40} className="text-accent-yellow" />
                </div>
              </motion.div>
              <h2 className="font-display text-2xl font-bold text-text-primary mb-3">
                Visualize Your Knowledge Graph
              </h2>
              <p className="font-mono text-sm text-text-muted leading-relaxed mb-6">
                Enter your DevBrain backend URL above and click <strong>Fetch</strong> to explore
                your codebase's knowledge graph — commits, PRs, ADRs, modules, and how they all connect.
              </p>
              <div className="flex flex-wrap gap-2 justify-center">
                {['Commits', 'Pull Requests', 'ADRs', 'Modules', 'Functions'].map((tag, i) => (
                  <span
                    key={tag}
                    className="px-3 py-1 rounded-full font-mono text-xs font-medium border"
                    style={{
                      background: `color-mix(in srgb, ${Object.values(NODE_COLORS)[i]} 20%, var(--color-bg))`,
                      borderColor: `color-mix(in srgb, ${Object.values(NODE_COLORS)[i]} 40%, transparent)`,
                      color: 'var(--color-text-primary)',
                    }}
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ─── Loading State ───────────────────────────────────────────── */}
      <AnimatePresence>
        {loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 flex items-center justify-center z-20"
          >
            <div className="text-center">
              <div className="relative w-20 h-20 mx-auto mb-6">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                  className="absolute inset-0 rounded-full border-2 border-transparent"
                  style={{ borderTopColor: 'var(--color-accent-yellow)', borderRightColor: 'var(--color-accent-mint)' }}
                />
                <motion.div
                  animate={{ rotate: -360 }}
                  transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
                  className="absolute inset-2 rounded-full border-2 border-transparent"
                  style={{ borderTopColor: 'var(--color-accent-yellow)', borderLeftColor: 'var(--color-accent-peach)' }}
                />
                <div className="absolute inset-0 flex items-center justify-center">
                  <Network size={20} className="text-text-muted" />
                </div>
              </div>
              <p className="font-mono text-sm text-text-muted">Fetching knowledge graph…</p>
              <div className="flex gap-1 justify-center mt-3">
                {[0, 1, 2].map(i => (
                  <motion.div
                    key={i}
                    animate={{ opacity: [0.3, 1, 0.3] }}
                    transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }}
                    className="w-1.5 h-1.5 rounded-full bg-accent-yellow"
                  />
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ─── Error State ─────────────────────────────────────────────── */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className="absolute bottom-6 left-1/2 -translate-x-1/2 z-30"
          >
            <div
              className="flex items-center gap-3 px-5 py-3 rounded-2xl border backdrop-blur-xl max-w-lg"
              style={{
                background: 'color-mix(in srgb, #FF4444 10%, var(--color-bg-card) 80%)',
                borderColor: 'color-mix(in srgb, #FF4444 30%, transparent)',
              }}
            >
              <AlertCircle size={18} className="text-red-400 shrink-0" />
              <p className="font-mono text-xs text-text-primary flex-1">{error}</p>
              <button
                onClick={() => setError(null)}
                className="text-text-muted hover:text-text-primary transition-colors cursor-pointer"
              >
                <X size={14} />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ─── Zoom Controls ───────────────────────────────────────────── */}
      {graphData && (
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: graphRendered ? 1 : 0, x: graphRendered ? 0 : 20 }}
          transition={{ duration: 0.4, delay: 0.3 }}
          className="absolute bottom-6 right-6 z-20 flex flex-col gap-1"
        >
          {[
            { icon: ZoomIn, action: () => handleZoom('in'), label: 'Zoom In' },
            { icon: ZoomOut, action: () => handleZoom('out'), label: 'Zoom Out' },
            { icon: Maximize2, action: () => handleZoom('fit'), label: 'Fit View' },
          ].map(({ icon: Icon, action, label }) => (
            <button
              key={label}
              onClick={action}
              title={label}
              className="w-10 h-10 rounded-xl flex items-center justify-center border backdrop-blur-xl transition-all duration-200 hover:scale-105 cursor-pointer"
              style={{
                background: 'color-mix(in srgb, var(--color-bg-card) 80%, transparent)',
                borderColor: 'color-mix(in srgb, var(--color-border) 30%, transparent)',
              }}
            >
              <Icon size={16} className="text-text-muted" />
            </button>
          ))}
        </motion.div>
      )}

      {/* ─── Legend Panel ────────────────────────────────────────────── */}
      {graphData && (
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: graphRendered ? 1 : 0, x: graphRendered ? 0 : -20 }}
          transition={{ duration: 0.4, delay: 0.2 }}
          className="absolute bottom-6 left-6 z-20"
        >
          <div
            className="rounded-2xl border backdrop-blur-xl overflow-hidden"
            style={{
              background: 'color-mix(in srgb, var(--color-bg-card) 80%, transparent)',
              borderColor: 'color-mix(in srgb, var(--color-border) 30%, transparent)',
              boxShadow: '0 8px 32px rgba(0,0,0,0.08)',
            }}
          >
            <button
              onClick={() => setShowLegend(!showLegend)}
              className="flex items-center gap-2 px-4 py-2.5 w-full text-left cursor-pointer hover:bg-bg-secondary/30 transition-colors"
            >
              <Info size={14} className="text-text-muted" />
              <span className="font-mono text-xs font-semibold text-text-primary">Legend</span>
              <motion.span
                animate={{ rotate: showLegend ? 180 : 0 }}
                className="ml-auto text-text-muted shrink-0"
              >
                <ChevronDown size={14} />
              </motion.span>
            </button>
            <AnimatePresence>
              {showLegend && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  <div className="px-4 pb-3 grid grid-cols-2 gap-x-4 gap-y-1.5">
                    {nodeTypes.map((rawType: any) => {
                      const type = rawType as string;
                      const Icon = NODE_ICONS[type];
                      return (
                        <div key={type} className="flex items-center gap-2">
                          <div
                            className="w-3 h-3 rounded-full shrink-0"
                            style={{
                              background: getNodeColor(type),
                              boxShadow: `0 0 6px ${getNodeColor(type)}40`,
                            }}
                          />
                          {Icon && <Icon size={11} className="text-text-muted shrink-0" />}
                          <span className="font-mono text-[10px] text-text-muted truncate">{type}</span>
                        </div>
                      );
                    })}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </motion.div>
      )}

      {/* ─── Stats Panel ─────────────────────────────────────────────── */}
      {stats && (
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: graphRendered ? 1 : 0, x: graphRendered ? 0 : 20 }}
          transition={{ duration: 0.4, delay: 0.4 }}
          className="absolute top-20 right-6 z-20"
        >
          <div
            className="rounded-2xl border backdrop-blur-xl overflow-hidden"
            style={{
              background: 'color-mix(in srgb, var(--color-bg-card) 80%, transparent)',
              borderColor: 'color-mix(in srgb, var(--color-border) 30%, transparent)',
              boxShadow: '0 8px 32px rgba(0,0,0,0.08)',
            }}
          >
            <button
              onClick={() => setShowStats(!showStats)}
              className="flex items-center gap-2 px-4 py-2.5 w-full text-left cursor-pointer hover:bg-bg-secondary/30 transition-colors"
            >
              <BarChart3 size={14} className="text-text-muted" />
              <span className="font-mono text-xs font-semibold text-text-primary">Stats</span>
              <motion.span
                animate={{ rotate: showStats ? 180 : 0 }}
                className="ml-auto text-text-muted shrink-0"
              >
                <ChevronDown size={14} />
              </motion.span>
            </button>
            <AnimatePresence>
              {showStats && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  <div className="px-4 pb-3 space-y-3 min-w-[200px]">
                    {/* Summary */}
                    <div className="flex gap-4">
                      <div>
                        <div className="font-mono text-xl font-bold text-text-primary">{stats.totalNodes}</div>
                        <div className="font-mono text-[10px] text-text-muted uppercase tracking-wider">Nodes</div>
                      </div>
                      <div>
                        <div className="font-mono text-xl font-bold text-text-primary">{stats.totalEdges}</div>
                        <div className="font-mono text-[10px] text-text-muted uppercase tracking-wider">Edges</div>
                      </div>
                    </div>

                    {/* Breakdown by type */}
                    <div className="space-y-1">
                      <div className="font-mono text-[10px] text-text-muted uppercase tracking-wider">By Type</div>
                      {Object.entries(stats.byType)
                        .sort(([, a], [, b]) => (b as number) - (a as number))
                        .slice(0, 8)
                        .map(([type, count]) => (
                          <div key={type} className="flex items-center gap-2">
                            <div
                              className="w-2 h-2 rounded-full shrink-0"
                              style={{ background: getNodeColor(type) }}
                            />
                            <span className="font-mono text-[10px] text-text-muted flex-1 truncate">{type}</span>
                            <span className="font-mono text-[10px] font-semibold text-text-primary">{count}</span>
                          </div>
                        ))}
                    </div>

                    {/* Edge types */}
                    <div className="space-y-1">
                      <div className="font-mono text-[10px] text-text-muted uppercase tracking-wider">Relationships</div>
                      {Object.entries(stats.edgeTypes)
                        .sort(([, a], [, b]) => (b as number) - (a as number))
                        .slice(0, 5)
                        .map(([type, count]) => (
                          <div key={type} className="flex items-center gap-2">
                            <span className="font-mono text-[10px] text-text-muted flex-1 truncate">{type}</span>
                            <span className="font-mono text-[10px] font-semibold text-text-primary">{count}</span>
                          </div>
                        ))}
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </motion.div>
      )}

      {/* ─── Selected Node Detail Panel ──────────────────────────────── */}
      <AnimatePresence>
        {selectedNode && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            transition={{ duration: 0.3 }}
            className="absolute bottom-6 left-1/2 -translate-x-1/2 z-30 w-full max-w-md px-4"
          >
            <div
              className="rounded-2xl border backdrop-blur-xl p-4"
              style={{
                background: 'color-mix(in srgb, var(--color-bg-card) 85%, transparent)',
                borderColor: `color-mix(in srgb, ${getNodeColor(selectedNode.type)} 40%, transparent)`,
                boxShadow: `0 8px 32px rgba(0,0,0,0.1), 0 0 0 1px ${getNodeColor(selectedNode.type)}15 inset`,
              }}
            >
              <div className="flex items-start gap-3">
                {NODE_ICONS[selectedNode.type] && (
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                    style={{
                      background: `color-mix(in srgb, ${getNodeColor(selectedNode.type)} 25%, var(--color-bg))`,
                    }}
                  >
                    {(() => {
                      const Icon = NODE_ICONS[selectedNode.type];
                      return Icon ? <Icon size={18} style={{ color: getNodeColor(selectedNode.type) }} /> : null;
                    })()}
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className="px-2 py-0.5 rounded-md font-mono text-[10px] font-semibold uppercase tracking-wider"
                      style={{
                        background: `color-mix(in srgb, ${getNodeColor(selectedNode.type)} 20%, transparent)`,
                        color: 'var(--color-text-primary)',
                      }}
                    >
                      {selectedNode.type}
                    </span>
                    <span className="font-mono text-[10px] text-text-muted">
                      {selectedNode.connectionCount} connections
                    </span>
                  </div>
                  <h3 className="font-display text-sm font-bold text-text-primary truncate">
                    {selectedNode.name || selectedNode.id}
                  </h3>
                  {selectedNode.description && (
                    <p className="font-mono text-[11px] text-text-muted mt-1 line-clamp-2">
                      {selectedNode.description}
                    </p>
                  )}
                </div>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="text-text-muted hover:text-text-primary transition-colors cursor-pointer shrink-0"
                >
                  <X size={14} />
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ─── Hover Tooltip ───────────────────────────────────────────── */}
      <AnimatePresence>
        {hoveredNode && !selectedNode && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className="fixed z-50 pointer-events-none"
            style={{
              left: tooltipPos.x + 16,
              top: tooltipPos.y - 8,
            }}
          >
            <div
              className="px-3 py-2 rounded-xl border max-w-xs"
              style={{
                background: 'color-mix(in srgb, var(--color-bg-card) 95%, transparent)',
                borderColor: `color-mix(in srgb, ${getNodeColor(hoveredNode.type)} 40%, transparent)`,
                backdropFilter: 'blur(16px)',
                boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
              }}
            >
              <div className="flex items-center gap-2 mb-1">
                <div
                  className="w-2.5 h-2.5 rounded-full"
                  style={{
                    background: getNodeColor(hoveredNode.type),
                    boxShadow: `0 0 6px ${getNodeColor(hoveredNode.type)}60`,
                  }}
                />
                <span className="font-mono text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                  {hoveredNode.type}
                </span>
              </div>
              <div className="font-display text-xs font-bold text-text-primary truncate">
                {hoveredNode.name || hoveredNode.id}
              </div>
              {hoveredNode.description && (
                <div className="font-mono text-[10px] text-text-muted mt-0.5 line-clamp-2">
                  {hoveredNode.description}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
