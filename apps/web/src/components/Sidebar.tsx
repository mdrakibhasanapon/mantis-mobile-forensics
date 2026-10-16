import React from 'react';
import {
  Home,
  Briefcase,
  Smartphone,
  DownloadCloud,
  FolderArchive,
  Layers,
  MessageSquare,
  Database,
  Clock,
  Share2,
  Image,
  Search,
  ShieldAlert,
  Cpu,
  FileText,
  History,
  Settings,
  MapPin,
} from 'lucide-react';

interface SidebarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  activeCaseNumber?: string;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onSelectTab, activeCaseNumber }) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: Home },
    { id: 'cases', label: 'Case Management', icon: Briefcase },
    { id: 'devices', label: 'Connected Devices', icon: Smartphone },
    { id: 'acquisition', label: 'Acquisition & Import', icon: DownloadCloud },
    { id: 'evidence', label: 'Evidence Explorer', icon: FolderArchive },
    { id: 'artifacts', label: 'Artefact Analysis', icon: Layers },
    { id: 'apps', label: 'Application Parsers', icon: MessageSquare },
    { id: 'sqlite', label: 'SQLite Forensic Explorer', icon: Database },
    { id: 'timeline', label: 'Unified Timeline', icon: Clock },
    { id: 'correlation', label: 'Correlation Graph', icon: Share2 },
    { id: 'geomap', label: 'Geo-Map & EXIF', icon: MapPin },
    { id: 'media', label: 'Media Gallery', icon: Image },
    { id: 'search', label: 'Global Search', icon: Search },
    { id: 'triage', label: 'Malware & IOC Triage', icon: ShieldAlert },
    { id: 'ai', label: 'Forensic Assistant', icon: Cpu },
    { id: 'reports', label: 'Forensic Reports', icon: FileText },
    { id: 'audit', label: 'Audit Trail', icon: History },
    { id: 'settings', label: 'System Settings', icon: Settings },
  ];

  return (
    <aside className="w-16 bg-[#090d13] border-r border-[#1a2332] flex flex-col items-center py-3 select-none z-20">
      {/* App Logo / Shield */}
      <div className="mb-4 flex flex-col items-center group cursor-pointer" onClick={() => onSelectTab('dashboard')}>
        <div className="w-10 h-10 rounded-lg p-0.5 bg-[#0e141f] border border-cyan-500/50 flex items-center justify-center shadow-lg shadow-cyan-950/60 group-hover:border-cyan-400 transition-colors">
          <img src="./logo.png" alt="Mantis" className="w-full h-full object-contain rounded-md" />
        </div>
        <span className="text-[9px] text-cyan-400/90 font-mono mt-1 font-semibold">1.0.0</span>
      </div>

      {/* Nav icons list */}
      <nav className="flex-1 w-full flex flex-col items-center space-y-1 overflow-y-auto no-scrollbar">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              title={item.label}
              className={`w-10 h-10 rounded-md flex items-center justify-center transition-all duration-150 relative ${
                isActive
                  ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/40 shadow-sm shadow-cyan-900/30'
                  : 'text-slate-400 hover:text-slate-100 hover:bg-[#151c28]'
              }`}
            >
              <Icon size={19} strokeWidth={isActive ? 2.2 : 1.7} />
              {isActive && (
                <div className="absolute left-0 w-1 h-5 bg-cyan-400 rounded-r-full" />
              )}
            </button>
          );
        })}
      </nav>

      {/* Bottom Status Indicator */}
      <div className="mt-2 pt-2 border-t border-[#1a2332] flex flex-col items-center" title="Localhost Encrypted IPC Active">
        <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
      </div>
    </aside>
  );
};
