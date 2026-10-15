import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { CorrelationLink } from '../types';
import { Share2, Phone, Mail, Link, Hash } from 'lucide-react';

interface CorrelationsPageProps {
  caseId: string;
}

export const CorrelationsPage: React.FC<CorrelationsPageProps> = ({ caseId }) => {
  const [correlations, setCorrelations] = useState<CorrelationLink[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!caseId) return;
    setIsLoading(true);
    api.getCorrelations(caseId)
      .then(setCorrelations)
      .catch(console.error)
      .finally(() => setIsLoading(false));
  }, [caseId]);

  return (
    <div className="flex-1 h-full min-h-0 overflow-y-auto p-4 bg-[#0c0f14] space-y-4 select-none">
      <div className="pb-3 border-b border-[#1c2738]">
        <h2 className="text-lg font-bold text-slate-100 tracking-wide">Cross-Source Deterministic Correlation</h2>
        <p className="text-xs text-slate-400">
          Deterministic correlation engine mapping phone numbers, email identifiers, and usernames across distinct forensic sources.
        </p>
      </div>

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
    </div>
  );
};
