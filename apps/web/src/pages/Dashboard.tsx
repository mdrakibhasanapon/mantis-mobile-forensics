import React from 'react';
import { DeviceHeader } from '../components/DeviceHeader';
import { AccountCards } from '../components/AccountCards';
import { StatsBar } from '../components/StatsBar';
import { Charts } from '../components/Charts';
import { Case, Evidence, CaseStatistics } from '../types';
import { ShieldAlert, AlertTriangle, ArrowRight } from 'lucide-react';

interface DashboardProps {
  activeCase: Case | null;
  evidenceList: Evidence[];
  stats: CaseStatistics | null;
  onNavigateTab: (tab: string) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({
  activeCase,
  evidenceList,
  stats,
  onNavigateTab,
}) => {
  return (
    <div className="flex-1 h-full min-h-0 overflow-y-auto p-4 space-y-3 bg-[#0c0f14]">
      {/* Device Information Header */}
      <DeviceHeader evidenceList={evidenceList} />

      {/* Discovered Accounts Grid */}
      <AccountCards />

      {/* 10-Metric Statistics Pills */}
      <StatsBar stats={stats} onSelectCategory={(cat) => onNavigateTab(cat === 'recovered' ? 'recovery' : 'artifacts')} />

      {/* Interactive Charts: Donut + Bar */}
      <Charts />

      {/* Quick Security / Triage Alerts Banner */}
      {stats && stats.triage_findings_count > 0 && (
        <div className="bg-gradient-to-r from-rose-950/30 via-[#161a24] to-[#121722] border border-rose-800/40 rounded-md p-3 flex items-center justify-between shadow-sm">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded bg-rose-500/20 border border-rose-500/40 flex items-center justify-center text-rose-400">
              <ShieldAlert size={18} />
            </div>
            <div>
              <div className="text-xs font-bold text-rose-300">
                Security Triage: {stats.triage_findings_count} Suspicious Indicators Identified
              </div>
              <div className="text-[11px] text-slate-400">
                High-risk Android permissions (SMS reading/sending) and suspicious C2 domain references detected in extracted files.
              </div>
            </div>
          </div>
          <button
            onClick={() => onNavigateTab('triage')}
            className="px-3 py-1.5 rounded text-xs font-semibold bg-rose-600/30 text-rose-200 border border-rose-500/40 hover:bg-rose-600/50 transition-colors flex items-center space-x-1"
          >
            <span>Review Findings</span>
            <ArrowRight size={13} />
          </button>
        </div>
      )}
    </div>
  );
};
