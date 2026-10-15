import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { TriageFinding } from '../types';
import { ShieldAlert, AlertTriangle, AlertCircle, Info, ShieldCheck } from 'lucide-react';

interface TriagePageProps {
  caseId: string;
}

export const TriagePage: React.FC<TriagePageProps> = ({ caseId }) => {
  const [findings, setFindings] = useState<TriageFinding[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!caseId) return;
    setIsLoading(true);
    api.getTriageFindings(caseId)
      .then(setFindings)
      .catch(console.error)
      .finally(() => setIsLoading(false));
  }, [caseId]);

  const getSeverityBadge = (sev: string) => {
    switch (sev) {
      case 'critical':
        return <span className="px-2 py-0.5 rounded bg-rose-950/70 border border-rose-800 text-rose-400 font-bold text-[10px]">CRITICAL</span>;
      case 'high':
        return <span className="px-2 py-0.5 rounded bg-orange-950/70 border border-orange-800 text-orange-400 font-bold text-[10px]">HIGH</span>;
      case 'medium':
        return <span className="px-2 py-0.5 rounded bg-amber-950/70 border border-amber-800 text-amber-400 font-bold text-[10px]">MEDIUM</span>;
      default:
        return <span className="px-2 py-0.5 rounded bg-blue-950/70 border border-blue-800 text-blue-400 font-bold text-[10px]">LOW</span>;
    }
  };

  return (
    <div className="flex-1 h-full min-h-0 overflow-y-auto p-4 bg-[#0c0f14] space-y-4 select-none">
      <div className="pb-3 border-b border-[#1c2738]">
        <h2 className="text-lg font-bold text-slate-100 tracking-wide">Local Malware & Security Triage</h2>
        <p className="text-xs text-slate-400">
          Offline heuristic and signature analysis of APK permissions, suspicious C2 domains, and suspicious persistence indicators.
        </p>
      </div>

      <div className="space-y-2.5">
        {isLoading ? (
          <div className="text-center py-16 text-slate-500 font-mono text-xs">Scanning evidence items...</div>
        ) : findings.length > 0 ? (
          findings.map((f) => (
            <div
              key={f.id}
              className="bg-[#111622] border border-[#1e2a3c] hover:border-cyan-500/40 rounded-lg p-3.5 transition-all text-xs flex items-start space-x-3.5"
            >
              <div className="p-2 rounded bg-[#0b0e14] border border-[#1d2737] flex-shrink-0 mt-0.5">
                <ShieldAlert size={18} className={f.severity === 'critical' ? 'text-rose-400' : 'text-amber-400'} />
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-semibold text-slate-100 text-sm font-sans">{f.title}</span>
                    <span className="text-[10px] text-slate-500 font-mono">[{f.rule_id}]</span>
                  </div>
                  {getSeverityBadge(f.severity)}
                </div>

                <p className="text-slate-300 font-sans text-xs mb-2 select-text">{f.description}</p>

                <div className="text-[11px] font-mono text-slate-500 flex items-center space-x-4 bg-[#090d13] p-1.5 rounded border border-[#16202e]">
                  <span>Target: <code className="text-cyan-400">{f.target_file}</code></span>
                  <span>Category: <strong className="text-slate-300">{f.category}</strong></span>
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="text-center py-16 text-slate-500 text-xs">
            No malware or suspicious indicators identified in current evidence.
          </div>
        )}
      </div>
    </div>
  );
};
