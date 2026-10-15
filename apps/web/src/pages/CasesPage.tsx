import React, { useState } from 'react';
import { api } from '../api/client';
import { Case } from '../types';
import { FolderPlus, FolderOpen, CheckCircle, Shield, FileCheck, ArrowRight } from 'lucide-react';

interface CasesPageProps {
  cases: Case[];
  activeCase: Case | null;
  onSelectCase: (caseId: string) => void;
  onRefreshCases: () => void;
}

export const CasesPage: React.FC<CasesPageProps> = ({
  cases,
  activeCase,
  onSelectCase,
  onRefreshCases,
}) => {
  const [isCreating, setIsCreating] = useState(false);
  const [caseNumber, setCaseNumber] = useState('');
  const [title, setTitle] = useState('');
  const [investigator, setInvestigator] = useState('Special Agent Kali');
  const [agency, setAgency] = useState('Digital Forensics & Incident Response Unit');
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!caseNumber || !title || !investigator) return;
    setIsSubmitting(true);
    try {
      const created = await api.createCase({
        case_number: caseNumber,
        title,
        investigator,
        agency,
        description,
      });
      await api.setActiveCase(created.id);
      onRefreshCases();
      setIsCreating(false);
      setCaseNumber('');
      setTitle('');
    } catch (err) {
      console.error(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex-1 h-full min-h-0 overflow-y-auto p-4 bg-[#0c0f14] space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-[#1c2738]">
        <div>
          <h2 className="text-lg font-bold text-slate-100 tracking-wide">Case Management</h2>
          <p className="text-xs text-slate-400">
            Create, switch, or inspect isolated forensic case boundaries and chain-of-custody logs.
          </p>
        </div>
        <button
          onClick={() => setIsCreating(true)}
          className="px-3 py-1.5 rounded text-xs font-semibold bg-cyan-500 text-slate-950 hover:bg-cyan-400 transition-colors flex items-center space-x-1.5 shadow-sm shadow-cyan-900/50"
        >
          <FolderPlus size={14} />
          <span>New Forensic Case</span>
        </button>
      </div>

      {/* Creation Modal / Inline Box */}
      {isCreating && (
        <form onSubmit={handleCreate} className="bg-[#111722] border border-cyan-500/40 rounded-lg p-4 shadow-xl space-y-3 max-w-xl">
          <div className="text-xs font-bold text-cyan-400 uppercase tracking-wider">Create New Investigation Case</div>
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <label className="block text-slate-400 mb-1 font-semibold">Case Number *</label>
              <input
                type="text"
                required
                placeholder="e.g. MMF-2026-0047"
                value={caseNumber}
                onChange={(e) => setCaseNumber(e.target.value)}
                className="w-full bg-[#16202e] border border-[#24344a] rounded px-3 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
              />
            </div>
            <div>
              <label className="block text-slate-400 mb-1 font-semibold">Case Title *</label>
              <input
                type="text"
                required
                placeholder="e.g. Mobile Extraction Analysis"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full bg-[#16202e] border border-[#24344a] rounded px-3 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>
            <div>
              <label className="block text-slate-400 mb-1 font-semibold">Lead Investigator *</label>
              <input
                type="text"
                required
                value={investigator}
                onChange={(e) => setInvestigator(e.target.value)}
                className="w-full bg-[#16202e] border border-[#24344a] rounded px-3 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>
            <div>
              <label className="block text-slate-400 mb-1 font-semibold">Agency / Organization</label>
              <input
                type="text"
                value={agency}
                onChange={(e) => setAgency(e.target.value)}
                className="w-full bg-[#16202e] border border-[#24344a] rounded px-3 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-slate-400 mb-1 font-semibold">Description / Authorization Reference</label>
              <input
                type="text"
                placeholder="Search warrant reference, authorization scope, evidence notes"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full bg-[#16202e] border border-[#24344a] rounded px-3 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>
          </div>
          <div className="flex justify-end space-x-2 pt-2">
            <button
              type="button"
              onClick={() => setIsCreating(false)}
              className="px-3 py-1.5 rounded text-xs text-slate-400 hover:text-slate-200 bg-[#16202e] border border-[#24344a]"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-1.5 rounded text-xs font-semibold bg-cyan-500 hover:bg-cyan-400 text-slate-950 transition-colors"
            >
              {isSubmitting ? 'Creating Case...' : 'Initialize Case'}
            </button>
          </div>
        </form>
      )}

      {/* Case Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {cases.map((c) => {
          const isActive = activeCase?.id === c.id;
          return (
            <div
              key={c.id}
              className={`p-3.5 rounded-lg border transition-all flex flex-col justify-between ${
                isActive
                  ? 'bg-[#131b27] border-cyan-500/50 shadow-md shadow-cyan-950/40'
                  : 'bg-[#10151f] border-[#1c2738] hover:border-[#2b3c54]'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold font-mono text-cyan-400">{c.case_number}</span>
                  {isActive && (
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-cyan-950/70 border border-cyan-800 text-cyan-300">
                      ACTIVE CASE
                    </span>
                  )}
                </div>
                <h3 className="text-sm font-semibold text-slate-100 mb-1">{c.title}</h3>
                <p className="text-xs text-slate-400 line-clamp-2 mb-3">
                  {c.description || 'No description provided.'}
                </p>
                <div className="text-[11px] font-mono text-slate-400 space-y-0.5 mb-3">
                  <div>Investigator: <span className="text-slate-200">{c.investigator}</span></div>
                  <div>Agency: <span className="text-slate-300">{c.agency || 'N/A'}</span></div>
                  <div>Storage: <code className="text-[10px] text-slate-500">{c.storage_path}</code></div>
                </div>
              </div>

              <div className="pt-2.5 border-t border-[#1a2536] flex items-center justify-between text-xs font-mono">
                <span className="text-slate-400 text-[11px]">
                  Evidence: <strong className="text-slate-200">{c.evidence_count}</strong> | Artefacts: <strong className="text-slate-200">{c.artifact_count}</strong>
                </span>
                {!isActive ? (
                  <button
                    onClick={() => onSelectCase(c.id)}
                    className="px-2.5 py-1 rounded bg-[#172333] hover:bg-cyan-500/20 text-cyan-300 border border-[#23354d] hover:border-cyan-500/40 transition-colors flex items-center space-x-1"
                  >
                    <span>Switch</span>
                    <ArrowRight size={12} />
                  </button>
                ) : (
                  <span className="text-emerald-400 flex items-center space-x-1 text-[11px]">
                    <CheckCircle size={13} />
                    <span>Selected</span>
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
