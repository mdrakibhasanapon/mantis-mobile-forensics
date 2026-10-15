import React from 'react';
import { Home, FolderPlus, Download, FileCheck, RefreshCw, ShieldCheck } from 'lucide-react';
import { Case } from '../types';

interface TopBarProps {
  activeCase: Case | null;
  onOpenCaseModal: () => void;
  onQuickGenerate: () => void;
  onViewReport: () => void;
  onRefresh: () => void;
  isRefreshing?: boolean;
}

export const TopBar: React.FC<TopBarProps> = ({
  activeCase,
  onOpenCaseModal,
  onQuickGenerate,
  onViewReport,
  onRefresh,
  isRefreshing,
}) => {
  return (
    <header className="h-13 bg-[#0d121a] border-b border-[#1c2738] px-4 flex items-center justify-between select-none">
      {/* Left: Case Info */}
      <div className="flex items-center space-x-3">
        <div className="w-8 h-8 rounded bg-[#162030] border border-[#233247] p-0.5 flex items-center justify-center shadow-sm">
          <img src="./logo.png" alt="Mantis" className="w-full h-full object-contain rounded" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-sm font-bold text-slate-100 tracking-wide">
              {activeCase ? `Case: ${activeCase.case_number}` : 'No Case Loaded'}
            </span>
            {activeCase && (
              <span className="text-xs px-2 py-0.5 rounded bg-cyan-950/70 border border-cyan-800/60 text-cyan-400 font-mono">
                {activeCase.title}
              </span>
            )}
          </div>
          <div className="text-[11px] text-slate-400">
            {activeCase ? `Examiner: ${activeCase.investigator} | Agency: ${activeCase.agency || 'DFIR Lab'}` : 'Select or create a forensic case to begin analysis'}
          </div>
        </div>
      </div>

      {/* Center: Extraction Timestamps */}
      {activeCase && (
        <div className="hidden lg:flex items-center space-x-6 text-xs text-slate-400 font-mono">
          <div className="flex flex-col">
            <span className="text-[10px] text-slate-500 uppercase font-sans font-semibold tracking-wider leading-none mb-1">Decoded</span>
            <span className="text-xs text-slate-300 font-mono leading-none">{new Date(activeCase.updated_at).toLocaleString()}</span>
          </div>
          <div className="border-l border-[#222f42] pl-6 flex flex-col">
            <span className="text-[10px] text-slate-500 uppercase font-sans font-semibold tracking-wider leading-none mb-1">Extraction Time</span>
            <span className="text-xs text-slate-300 font-mono leading-none">{new Date(activeCase.created_at).toLocaleString()}</span>
          </div>
        </div>
      )}

      {/* Right: Actions */}
      <div className="flex items-center space-x-2">
        <button
          onClick={onRefresh}
          title="Refresh Case Data"
          className="p-1.5 rounded bg-[#162030] border border-[#233247] text-slate-300 hover:text-cyan-400 hover:border-cyan-500/50 transition-colors"
        >
          <RefreshCw size={15} className={isRefreshing ? 'animate-spin text-cyan-400' : ''} />
        </button>

        <button
          onClick={onQuickGenerate}
          className="px-2.5 py-1.5 rounded text-xs font-medium bg-gradient-to-r from-cyan-600/30 to-blue-600/30 border border-cyan-500/50 text-cyan-300 hover:bg-cyan-600/40 transition-all flex items-center space-x-1.5 shadow-sm"
          title="Generate and auto-parse synthetic mobile extraction for demonstration/testing"
        >
          <Download size={13} />
          <span>Quick Synthetic Extraction</span>
        </button>

        <button
          onClick={onViewReport}
          disabled={!activeCase}
          className="px-2.5 py-1.5 rounded text-xs font-medium bg-[#162030] border border-[#26374f] text-slate-200 hover:border-cyan-500/60 hover:text-cyan-300 disabled:opacity-40 transition-colors flex items-center space-x-1.5"
        >
          <FileCheck size={13} />
          <span>View Report</span>
        </button>

        <button
          onClick={onOpenCaseModal}
          className="px-3 py-1.5 rounded text-xs font-semibold bg-cyan-500 text-slate-950 hover:bg-cyan-400 transition-colors flex items-center space-x-1.5 shadow-sm shadow-cyan-900/50"
        >
          <FolderPlus size={14} />
          <span>Create / Open Case</span>
        </button>
      </div>
    </header>
  );
};
