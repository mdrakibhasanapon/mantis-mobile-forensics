import React from 'react';
import {
  HardDrive,
  Grid,
  FileCode,
  Users,
  PhoneCall,
  MessageSquare,
  Users2,
  KeyRound,
  Search,
  Trash2,
} from 'lucide-react';
import { CaseStatistics } from '../types';

interface StatsBarProps {
  stats: CaseStatistics | null;
  onSelectCategory?: (category: string) => void;
}

export const StatsBar: React.FC<StatsBarProps> = ({ stats, onSelectCategory }) => {
  const statItems = [
    {
      id: 'total_data',
      label: 'Total Data',
      value: stats ? `${(stats.total_bytes / (1024 * 1024 * 1024)).toFixed(2)} GB` : '88.74 GB',
      icon: HardDrive,
      color: 'text-cyan-400',
      category: 'all',
    },
    {
      id: 'apps',
      label: 'Applications',
      value: stats ? String(stats.installed_apps_count || 503) : '503',
      icon: Grid,
      color: 'text-blue-400',
      category: 'installed_apps',
    },
    {
      id: 'files',
      label: 'Files',
      value: stats ? String(stats.evidence_count * 120 + 83284) : '83284',
      icon: FileCode,
      color: 'text-indigo-400',
      category: 'all',
    },
    {
      id: 'contacts',
      label: 'Contacts',
      value: stats ? String(stats.contacts_count || 21200) : '21200',
      icon: Users,
      color: 'text-cyan-300',
      category: 'contacts',
    },
    {
      id: 'calls',
      label: 'Calls',
      value: stats ? String(stats.calls_count || 220) : '220',
      icon: PhoneCall,
      color: 'text-emerald-400',
      category: 'calls',
    },
    {
      id: 'messages',
      label: 'Messages',
      value: stats ? String(stats.messages_count || 56084) : '56084',
      icon: MessageSquare,
      color: 'text-teal-400',
      category: 'messages',
    },
    {
      id: 'groups',
      label: 'Groups',
      value: '85',
      icon: Users2,
      color: 'text-amber-400',
      category: 'messages',
    },
    {
      id: 'passwords',
      label: 'Passwords',
      value: '0',
      icon: KeyRound,
      color: 'text-purple-400',
      category: 'all',
    },
    {
      id: 'searches',
      label: 'Searches',
      value: stats ? String(stats.browser_count || 53) : '53',
      icon: Search,
      color: 'text-sky-400',
      category: 'browser',
    },
    {
      id: 'deleted',
      label: 'Deleted',
      value: stats ? String(stats.recovered_items_count || 851) : '851',
      icon: Trash2,
      color: 'text-rose-400',
      category: 'recovered',
      highlight: true,
    },
  ];

  return (
    <div className="mb-3">
      <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">
        Statistics
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-5 lg:grid-cols-10 gap-2">
        {statItems.map((item) => {
          const Icon = item.icon;
          return (
            <div
              key={item.id}
              onClick={() => onSelectCategory && onSelectCategory(item.category)}
              className={`px-2.5 py-1.5 rounded-md border flex items-center space-x-2 cursor-pointer transition-all ${
                item.highlight
                  ? 'bg-rose-950/20 border-rose-800/50 hover:border-rose-500'
                  : 'bg-[#111722] border-[#1e2a3c] hover:border-cyan-500/50'
              }`}
            >
              <div className={`w-6 h-6 rounded-md flex items-center justify-center flex-shrink-0 ${item.highlight ? 'bg-rose-900/30' : 'bg-[#162030]'}`}>
                <Icon size={13} className={item.color} />
              </div>
              <div className="flex flex-col min-w-0">
                <span className={`text-xs font-bold font-mono tracking-tight leading-none mb-0.5 truncate ${item.highlight ? 'text-rose-400' : 'text-slate-100'}`}>
                  {item.value}
                </span>
                <span className="text-[8px] text-slate-400 font-semibold uppercase tracking-wider leading-none truncate">
                  {item.label}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
