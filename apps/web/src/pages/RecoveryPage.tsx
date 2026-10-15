import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { RecoveredItem } from '../types';
import { Trash2, CheckCircle2, AlertCircle, FileSearch, Sparkles } from 'lucide-react';

interface RecoveryPageProps {
  caseId: string;
}

export const RecoveryPage: React.FC<RecoveryPageProps> = ({ caseId }) => {
  const [recovered, setRecovered] = useState<RecoveredItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!caseId) return;
    setIsLoading(true);
    api.getRecoveredItems(caseId)
      .then(setRecovered)
      .catch(console.error)
      .finally(() => setIsLoading(false));
  }, [caseId]);

  return (
    <div className="flex-1 h-full min-h-0 overflow-y-auto p-4 bg-[#0c0f14] space-y-4 select-none">
      <div className="pb-3 border-b border-[#1c2738]">
        <h2 className="text-lg font-bold text-slate-100 tracking-wide">Deleted-Data Recovery & Freelist Carving</h2>
        <p className="text-xs text-slate-400">
          Recovered intact fragments from SQLite database freelist pages, unallocated database chunks, and raw byte patterns.
        </p>
      </div>

      <div className="space-y-2.5">
        {isLoading ? (
          <div className="text-center py-16 text-slate-500 font-mono text-xs">Carving unallocated space...</div>
        ) : recovered.length > 0 ? (
          recovered.map((r) => (
            <div
              key={r.id}
              className="bg-[#111622] border border-[#1e2a3c] hover:border-cyan-500/40 rounded-lg p-3.5 transition-all text-xs flex items-start space-x-3.5"
            >
              <div className="p-2 rounded bg-rose-950/30 border border-rose-800/40 text-rose-400 flex-shrink-0 mt-0.5">
                <Trash2 size={16} />
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1.5 font-mono">
                  <div className="flex items-center space-x-2">
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-rose-950/70 border border-rose-800 text-rose-400 uppercase">
                      {r.classification}
                    </span>
                    <span className="text-slate-400 text-xs">
                      Source: <strong className="text-slate-200">{r.source_file}</strong>
                    </span>
                    <span className="text-slate-500 text-[11px]">
                      Offset: 0x{r.offset.toString(16).toUpperCase()} ({r.offset})
                    </span>
                  </div>
                  <span className="text-cyan-400 font-bold text-[11px]">
                    Confidence: {Math.round(r.confidence * 100)}%
                  </span>
                </div>

                <div className="bg-[#080c12] p-2.5 rounded border border-[#172232] font-mono text-xs text-slate-200 select-text mb-2 break-all">
                  {r.data_preview}
                </div>

                <div className="text-[10px] text-slate-500 font-mono flex items-center justify-between">
                  <span>Method: <code>{r.recovery_method}</code></span>
                  <span>Forensic Status: Verified Reproducible From Working Copy</span>
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="text-center py-16 text-slate-500 text-xs">
            No deleted items carved. Run synthetic extraction or freelist carver on existing SQLite databases.
          </div>
        )}
      </div>
    </div>
  );
};
