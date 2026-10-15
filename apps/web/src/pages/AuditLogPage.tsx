import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { AuditRecord } from '../types';
import { History, ShieldCheck, ShieldAlert, CheckCircle2, Lock } from 'lucide-react';

interface AuditLogPageProps {
  caseId: string;
}

export const AuditLogPage: React.FC<AuditLogPageProps> = ({ caseId }) => {
  const [records, setRecords] = useState<AuditRecord[]>([]);
  const [verification, setVerification] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!caseId) return;
    setIsLoading(true);
    api.getCaseAudit(caseId)
      .then((data) => {
        setRecords(data.records);
        setVerification(data.verification);
      })
      .catch(console.error)
      .finally(() => setIsLoading(false));
  }, [caseId]);

  const formatTimestamp = (ts: string) => {
    try {
      const d = new Date(ts);
      if (isNaN(d.getTime())) return ts || 'N/A';
      return d.toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
    } catch {
      return ts || 'N/A';
    }
  };

  return (
    <div className="flex-1 h-full min-h-0 overflow-y-auto p-4 bg-[#0c0f14] space-y-4 select-none">
      <div className="pb-3 border-b border-[#1c2738] flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-slate-100 tracking-wide">Append-Only Chain of Custody & Audit Trail</h2>
          <p className="text-xs text-slate-400">
            Immutable, cryptographically chained SHA-256 ledger recording every forensic intake, hash verification, and analysis step.
          </p>
        </div>

        {verification && (
          <div
            className={`px-3 py-1.5 rounded text-xs font-semibold flex items-center space-x-2 ${
              verification.valid
                ? 'bg-emerald-950/70 text-emerald-400 border border-emerald-800'
                : 'bg-rose-950/70 text-rose-400 border border-rose-800'
            }`}
          >
            {verification.valid ? <ShieldCheck size={16} /> : <ShieldAlert size={16} />}
            <span>
              {verification.valid
                ? `LEDGER VERIFIED (${verification.count} RECORDS INTACT)`
                : `CHAIN TAMPERED: ${verification.errors.length} INTEGRITY ANOMALIES`}
            </span>
          </div>
        )}
      </div>

      <div className="space-y-2 font-mono text-xs">
        {isLoading ? (
          <div className="text-center py-16 text-slate-500">Verifying SHA-256 audit block signatures...</div>
        ) : records.length > 0 ? (
          records.map((r, idx) => (
            <div
              key={r.id}
              className="bg-[#10151f] border border-[#1e2a3c] rounded p-3 hover:border-cyan-500/40 transition-colors"
            >
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center space-x-2">
                  <span className="w-5 h-5 rounded-full bg-[#182333] border border-[#26374f] text-[10px] text-cyan-400 flex items-center justify-center font-bold">
                    {idx + 1}
                  </span>
                  <span className="font-bold text-slate-100 font-sans text-xs uppercase">{r.action}</span>
                  <span className="text-[11px] text-slate-400 font-mono">by {r.actor}</span>
                </div>
                <span className="text-slate-400 text-[11px]">
                  {formatTimestamp(r.timestamp)}
                </span>
              </div>

              <div className="bg-[#090d13] p-2 rounded border border-[#16202e] text-[11px] mb-2 text-slate-300">
                <span className="text-slate-500 block mb-0.5">EVENT PAYLOAD:</span>
                <pre className="whitespace-pre-wrap">{JSON.stringify(r.details, null, 2)}</pre>
              </div>

              <div className="text-[10px] text-slate-500 flex items-center justify-between border-t border-[#172230] pt-1.5">
                <span className="truncate max-w-md">
                  Signature: <code className="text-amber-400/90">{r.hash_signature}</code>
                </span>
                <span className="text-emerald-400 font-sans flex items-center space-x-1">
                  <Lock size={10} />
                  <span>Chained</span>
                </span>
              </div>
            </div>
          ))
        ) : (
          <div className="text-center py-16 text-slate-500 text-xs">No audit records recorded yet.</div>
        )}
      </div>
    </div>
  );
};
