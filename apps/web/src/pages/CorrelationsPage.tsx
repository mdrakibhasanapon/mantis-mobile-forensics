import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { CorrelationLink } from '../types';
import {
  Share2,
  Phone,
  Mail,
  Network,
  Users,
  MessageSquare,
  Clock,
  ArrowUpRight,
  TrendingUp,
  Activity,
} from 'lucide-react';

interface CorrelationsPageProps {
  caseId: string;
}

export const CorrelationsPage: React.FC<CorrelationsPageProps> = ({ caseId }) => {
  const [activeTab, setActiveTab] = useState<'graph' | 'links'>('graph');
  const [correlations, setCorrelations] = useState<CorrelationLink[]>([]);
  const [graphData, setGraphData] = useState<any>(null);
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!caseId) return;
    setIsLoading(true);
    Promise.all([
      api.getCorrelations(caseId).catch(() => []),
      api.getLinkAnalysis(caseId).catch(() => null),
    ])
      .then(([corrs, graph]) => {
        setCorrelations(corrs || []);
        setGraphData(graph);
        if (graph?.top_contacts && graph.top_contacts.length > 0) {
          setSelectedNode(graph.top_contacts[0]);
        }
      })
      .finally(() => setIsLoading(false));
  }, [caseId]);

  return (
    <div className="flex-1 h-full min-h-0 flex flex-col p-4 bg-[#0c0f14] space-y-3 overflow-y-auto">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between pb-3 border-b border-[#1c2738] gap-3">
        <div>
          <div className="flex items-center space-x-2">
            <Network size={20} className="text-cyan-400" />
            <h2 className="text-lg font-bold text-slate-100 tracking-wide">
              Communication Link Analysis & Correlation Network
            </h2>
          </div>
          <p className="text-xs text-slate-400">
            Nodal network mapping between target suspect and frequent contacts across messaging and voice telephony.
          </p>
        </div>

        {/* View Tabs */}
        <div className="flex bg-[#101724] p-1 rounded-lg border border-[#1e2a3c]">
          <button
            onClick={() => setActiveTab('graph')}
            className={`px-3 py-1 text-xs font-semibold rounded-md transition-colors flex items-center space-x-1.5 ${
              activeTab === 'graph'
                ? 'bg-cyan-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Network size={13} />
            <span>Link Analysis Graph</span>
          </button>
          <button
            onClick={() => setActiveTab('links')}
            className={`px-3 py-1 text-xs font-semibold rounded-md transition-colors flex items-center space-x-1.5 ${
              activeTab === 'links'
                ? 'bg-cyan-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Share2 size={13} />
            <span>Deterministic Identifiers ({correlations.length})</span>
          </button>
        </div>
      </div>

      {activeTab === 'graph' ? (
        <div className="space-y-4">
          {/* Top Metric Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-[#10151f] border border-[#1c2738] rounded-lg p-3">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Identified Entities</span>
              <div className="text-xl font-bold text-cyan-400 mt-1 font-mono">
                {graphData?.metrics?.total_entities || 0}
              </div>
            </div>
            <div className="bg-[#10151f] border border-[#1c2738] rounded-lg p-3">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Total Interactions</span>
              <div className="text-xl font-bold text-emerald-400 mt-1 font-mono">
                {graphData?.metrics?.total_interactions || 0}
              </div>
            </div>
            <div className="bg-[#10151f] border border-[#1c2738] rounded-lg p-3">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Active Channels</span>
              <div className="text-xl font-bold text-amber-400 mt-1 font-mono">
                {Object.keys(graphData?.metrics?.channel_distribution || {}).length}
              </div>
            </div>
            <div className="bg-[#10151f] border border-[#1c2738] rounded-lg p-3">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Top Subject</span>
              <div className="text-sm font-bold text-purple-400 mt-1 truncate">
                {graphData?.top_contacts?.[0]?.label || 'None'}
              </div>
            </div>
          </div>

          {/* Main Visual Nodal Network & Subject Inspector */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Interactive SVG Network Canvas */}
            <div className="lg:col-span-2 bg-[#090d13] border border-[#1c2738] rounded-lg p-4 min-h-[380px] flex flex-col justify-between relative overflow-hidden">
              <div className="flex items-center justify-between pb-2 border-b border-[#16202e] text-xs font-semibold text-slate-400">
                <span>VISUAL RELATIONSHIP NETWORK (NODE TOPOLOGY)</span>
                <span className="text-[10px] text-cyan-400">Click a node to inspect entity</span>
              </div>

              {/* Render Nodes in Orbit */}
              <div className="relative w-full h-[320px] flex items-center justify-center my-2">
                {/* Central Suspect Node */}
                <div className="z-10 flex flex-col items-center justify-center w-24 h-24 rounded-full bg-cyan-950/80 border-2 border-cyan-400 text-center shadow-lg shadow-cyan-950/60 p-1 cursor-default">
                  <Users size={20} className="text-cyan-300 mb-1" />
                  <span className="text-[10px] font-bold text-slate-100 leading-tight">DEVICE</span>
                  <span className="text-[9px] text-cyan-400 font-mono">SUSPECT</span>
                </div>

                {/* Orbiting Contact Nodes */}
                {graphData?.top_contacts?.slice(0, 8).map((node: any, idx: number) => {
                  const total = Math.min(graphData.top_contacts.length, 8);
                  const angle = (idx / total) * (2 * Math.PI) - Math.PI / 2;
                  const radius = 125; // Orbit radius in pixels
                  const x = Math.cos(angle) * radius;
                  const y = Math.sin(angle) * radius;
                  const isSelected = selectedNode?.id === node.id;

                  return (
                    <React.Fragment key={node.id}>
                      {/* Connection Line */}
                      <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ left: 0, top: 0 }}>
                        <line
                          x1="50%"
                          y1="50%"
                          x2={`calc(50% + ${x}px)`}
                          y2={`calc(50% + ${y}px)`}
                          stroke={isSelected ? '#38bdf8' : '#223249'}
                          strokeWidth={isSelected ? 2 : Math.min(node.total_interactions, 6)}
                          strokeDasharray={isSelected ? 'none' : '4 2'}
                        />
                      </svg>

                      {/* Node Element */}
                      <div
                        onClick={() => setSelectedNode(node)}
                        style={{
                          transform: `translate(${x}px, ${y}px)`,
                        }}
                        className={`absolute z-20 flex flex-col items-center justify-center p-2 rounded-lg border cursor-pointer transition-all ${
                          isSelected
                            ? 'bg-[#18283f] border-cyan-400 shadow-md shadow-cyan-900/50 scale-110'
                            : 'bg-[#101724] border-[#1e2b3c] hover:border-slate-500 hover:scale-105'
                        }`}
                      >
                        <div className="flex items-center space-x-1">
                          <Phone size={10} className="text-emerald-400" />
                          <span className="text-[10px] font-bold text-slate-200 truncate max-w-[90px]">
                            {node.label}
                          </span>
                        </div>
                        <span className="text-[9px] font-mono text-cyan-300 font-semibold">
                          {node.total_interactions} acts
                        </span>
                      </div>
                    </React.Fragment>
                  );
                })}
              </div>

              {/* Bottom Channel Breakdown Legend */}
              <div className="pt-2 border-t border-[#16202e] flex flex-wrap items-center gap-2 text-[10px]">
                <span className="text-slate-500 font-semibold">CHANNELS:</span>
                {Object.entries(graphData?.metrics?.channel_distribution || {}).map(([ch, cnt]: any) => (
                  <span key={ch} className="px-2 py-0.5 rounded bg-[#131b26] border border-[#223146] text-slate-300 font-mono">
                    {ch}: <strong className="text-cyan-400">{cnt}</strong>
                  </span>
                ))}
              </div>
            </div>

            {/* Right: Selected Node Detail Inspector */}
            <div className="bg-[#10151f] border border-[#1c2738] rounded-lg p-4 flex flex-col justify-between">
              <div>
                <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Contact Entity Profile
                </div>
                {selectedNode ? (
                  <div className="space-y-3">
                    <div className="bg-[#090d13] p-3 rounded-lg border border-[#1a2536]">
                      <div className="text-base font-bold text-slate-100">{selectedNode.label}</div>
                      {selectedNode.phone && (
                        <div className="text-xs font-mono text-cyan-400 mt-0.5">{selectedNode.phone}</div>
                      )}
                      <div className="mt-2 flex items-center space-x-2">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-950 text-cyan-300 border border-cyan-800">
                          {selectedNode.total_interactions} Total Interactions
                        </span>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="bg-[#090d13] p-2.5 rounded border border-[#1a2536]">
                        <span className="text-[10px] text-slate-500 uppercase">Voice Calls</span>
                        <div className="text-sm font-bold text-emerald-400 font-mono mt-0.5">
                          {selectedNode.call_count || 0}
                        </div>
                      </div>
                      <div className="bg-[#090d13] p-2.5 rounded border border-[#1a2536]">
                        <span className="text-[10px] text-slate-500 uppercase">Chat Messages</span>
                        <div className="text-sm font-bold text-cyan-400 font-mono mt-0.5">
                          {selectedNode.msg_count || 0}
                        </div>
                      </div>
                    </div>

                    {selectedNode.channels && (
                      <div className="text-xs">
                        <span className="text-[10px] text-slate-500 uppercase font-semibold">Utilized Apps / Channels</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {selectedNode.channels.map((ch: string) => (
                            <span key={ch} className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-200 border border-slate-700">
                              {ch}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {selectedNode.first_seen && (
                      <div className="text-[11px] font-mono text-slate-400 space-y-1 bg-[#090d13] p-2 rounded border border-[#1a2536]">
                        <div><strong className="text-slate-500">First Interaction:</strong> {selectedNode.first_seen}</div>
                        <div><strong className="text-slate-500">Last Interaction:</strong> {selectedNode.last_seen}</div>
                      </div>
                    )}

                    {selectedNode.recent_snippet && (
                      <div className="text-xs bg-[#0a0f17] p-2 rounded border border-[#182333] text-slate-300">
                        <span className="text-[10px] text-slate-500 block mb-1 uppercase font-semibold">Sample Communication</span>
                        <div className="italic text-slate-400">"{selectedNode.recent_snippet}"</div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-slate-500 text-xs py-8 text-center">
                    Click any node or contact to inspect relationship metrics.
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* 24-Hour Activity Heatmap */}
          {graphData?.metrics?.hourly_activity && (
            <div className="bg-[#10151f] border border-[#1c2738] rounded-lg p-4">
              <div className="flex items-center space-x-2 mb-3">
                <Activity size={15} className="text-cyan-400" />
                <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wide">
                  24-Hour Communication Activity Distribution (Pattern of Life)
                </h3>
              </div>
              <div className="grid grid-cols-12 md:grid-cols-24 gap-1 items-end h-24 pt-2">
                {Object.entries(graphData.metrics.hourly_activity).map(([hour, count]: any) => {
                  const maxCount = Math.max(...Object.values(graphData.metrics.hourly_activity).map((v: any) => v || 0), 1);
                  const heightPct = Math.max(Math.round((count / maxCount) * 100), 8);
                  return (
                    <div key={hour} className="flex flex-col items-center h-full justify-end group">
                      <div
                        style={{ height: `${heightPct}%` }}
                        className={`w-full rounded-t transition-all ${
                          count > 0 ? 'bg-cyan-500 hover:bg-cyan-400' : 'bg-[#182333]'
                        }`}
                        title={`${hour}:00 - ${count} events`}
                      />
                      <span className="text-[9px] text-slate-500 mt-1 font-mono">{hour}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Deterministic Correlation Identifiers */
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {isLoading ? (
            <div className="col-span-2 text-center py-16 text-slate-500 font-mono text-xs">
              Evaluating multi-source entity relationships...
            </div>
          ) : correlations.length > 0 ? (
            correlations.map((c) => (
              <div
                key={c.id}
                className="bg-[#10151f] border border-[#1e2a3c] hover:border-cyan-500/40 rounded-lg p-3.5 transition-all text-xs font-mono"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <div className="p-1.5 rounded bg-cyan-950/60 border border-cyan-800 text-cyan-400">
                      {c.entity_type === 'phone_number' ? <Phone size={14} /> : <Mail size={14} />}
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-500 uppercase font-sans font-bold">
                        {c.entity_type.replace('_', ' ')}
                      </span>
                      <div className="text-sm font-bold text-slate-100">{c.value}</div>
                    </div>
                  </div>
                  <span className="px-2 py-0.5 rounded bg-amber-950/40 border border-amber-800/40 text-amber-400 text-[11px] font-semibold">
                    {c.occurrences} Linkages
                  </span>
                </div>

                <p className="text-slate-300 font-sans text-xs mb-3 bg-[#090d13] p-2 rounded border border-[#17212f]">
                  {c.description}
                </p>

                <div className="text-[10px] text-slate-500 flex items-center justify-between pt-2 border-t border-[#182333]">
                  <span>Evidence Sources: {c.linked_evidence_ids.length}</span>
                  <span>Linked Artefacts: {c.linked_artifact_ids.length}</span>
                </div>
              </div>
            ))
          ) : (
            <div className="col-span-2 text-center py-16 text-slate-500 text-xs">
              No cross-source correlations discovered. Import multiple extractions or run synthetic generation.
            </div>
          )}
        </div>
      )}
    </div>
  );
};
