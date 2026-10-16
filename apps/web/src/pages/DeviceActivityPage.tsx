import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Artifact, Case } from '../types';
import {
  Bell,
  Download,
  Package,
  Search,
  RefreshCw,
  ExternalLink,
  ShieldAlert,
  ShieldCheck,
  FileCode,
  HardDrive,
  Copy,
  Check,
  AlertTriangle,
  Clock,
  Filter,
} from 'lucide-react';

interface DeviceActivityPageProps {
  activeCase: Case | null;
}

export const DeviceActivityPage: React.FC<DeviceActivityPageProps> = ({ activeCase }) => {
  const [activeTab, setActiveTab] = useState<'notifications' | 'downloads' | 'apps'>('notifications');
  const [notifications, setNotifications] = useState<Artifact[]>([]);
  const [downloads, setDownloads] = useState<Artifact[]>([]);
  const [apps, setApps] = useState<Artifact[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [filterRiskOnly, setFilterRiskOnly] = useState(false);

  const fetchData = () => {
    if (!activeCase) return;
    setIsLoading(true);
    Promise.all([
      api.listArtifacts(activeCase.id, 'notifications').catch(() => []),
      api.listArtifacts(activeCase.id, 'downloads').catch(() => []),
      api.listArtifacts(activeCase.id, 'installed_apps').catch(() => []),
    ])
      .then(([notifs, dls, appList]) => {
        setNotifications(notifs || []);
        setDownloads(dls || []);
        setApps(appList || []);
      })
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    fetchData();
  }, [activeCase?.id]);

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  if (!activeCase) {
    return (
      <div className="flex-1 h-full flex items-center justify-center bg-[#0c0f14] text-slate-500 text-sm">
        Select or activate a forensic case to inspect device traces.
      </div>
    );
  }

  // Filter logic
  const filteredNotifs = notifications.filter((n) => {
    const q = searchQuery.toLowerCase();
    const norm = n.normalized_data || {};
    return (
      !q ||
      (norm.title && norm.title.toLowerCase().includes(q)) ||
      (norm.message_preview && norm.message_preview.toLowerCase().includes(q)) ||
      (norm.package_name && norm.package_name.toLowerCase().includes(q))
    );
  });

  const filteredDownloads = downloads.filter((d) => {
    const q = searchQuery.toLowerCase();
    const norm = d.normalized_data || {};
    return (
      !q ||
      (norm.filename && norm.filename.toLowerCase().includes(q)) ||
      (norm.source_url && norm.source_url.toLowerCase().includes(q)) ||
      (norm.destination_path && norm.destination_path.toLowerCase().includes(q))
    );
  });

  const filteredApps = apps.filter((a) => {
    const q = searchQuery.toLowerCase();
    const norm = a.normalized_data || {};
    const matchesSearch =
      !q ||
      (norm.package_name && norm.package_name.toLowerCase().includes(q)) ||
      (norm.code_path && norm.code_path.toLowerCase().includes(q));
    const matchesRisk = !filterRiskOnly || norm.high_risk_surveillance;
    return matchesSearch && matchesRisk;
  });

  return (
    <div className="flex-1 h-full min-h-0 flex flex-col p-4 bg-[#0c0f14] space-y-3 overflow-hidden">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between pb-3 border-b border-[#1c2738] gap-3">
        <div>
          <h2 className="text-lg font-bold text-slate-100 tracking-wide flex items-center space-x-2">
            <span>Device Activity & System Traces Hub</span>
          </h2>
          <p className="text-xs text-slate-400">
            Dedicated triage sections for Push Notification logs, Download Manager history, and Installed Applications audit.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          {/* Sub-Tab Switcher */}
          <div className="flex bg-[#101724] p-1 rounded-lg border border-[#1e2a3c]">
            <button
              onClick={() => setActiveTab('notifications')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors flex items-center space-x-1.5 ${
                activeTab === 'notifications'
                  ? 'bg-cyan-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Bell size={13} />
              <span>Notifications ({notifications.length})</span>
            </button>
            <button
              onClick={() => setActiveTab('downloads')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors flex items-center space-x-1.5 ${
                activeTab === 'downloads'
                  ? 'bg-cyan-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Download size={13} />
              <span>Downloads ({downloads.length})</span>
            </button>
            <button
              onClick={() => setActiveTab('apps')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors flex items-center space-x-1.5 ${
                activeTab === 'apps'
                  ? 'bg-cyan-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Package size={13} />
              <span>Installed Apps ({apps.length})</span>
            </button>
          </div>

          <button
            onClick={fetchData}
            disabled={isLoading}
            className="p-2 rounded bg-[#16202e] border border-[#24344a] text-slate-300 hover:text-cyan-400 transition-colors"
            title="Refresh Activity"
          >
            <RefreshCw size={13} className={isLoading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* Search & Filter Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-[#10151f] p-2.5 rounded-lg border border-[#1a2536]">
        <div className="relative flex-1 max-w-md">
          <Search size={14} className="absolute left-3 top-2.5 text-slate-500" />
          <input
            type="text"
            placeholder={
              activeTab === 'notifications'
                ? 'Search notifications preview, sender, or package...'
                : activeTab === 'downloads'
                ? 'Search download filename, destination path, or URL...'
                : 'Search package name, permissions, or code path...'
            }
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 bg-[#090d14] border border-[#1e2a3c] rounded text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-sans"
          />
        </div>

        {activeTab === 'apps' && (
          <button
            onClick={() => setFilterRiskOnly(!filterRiskOnly)}
            className={`px-3 py-1.5 rounded text-xs font-semibold border flex items-center space-x-1.5 transition-colors ${
              filterRiskOnly
                ? 'bg-rose-950/80 text-rose-300 border-rose-700'
                : 'bg-[#151e2c] text-slate-400 border-[#223146] hover:text-slate-200'
            }`}
          >
            <ShieldAlert size={13} />
            <span>High-Risk Surveillance Apps Only</span>
          </button>
        )}
      </div>

      {/* Content Area */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        {/* ================= 1. NOTIFICATIONS TAB ================= */}
        {activeTab === 'notifications' && (
          <div className="space-y-2.5">
            {filteredNotifs.length > 0 ? (
              filteredNotifs.map((art) => {
                const norm = art.normalized_data || {};
                return (
                  <div
                    key={art.id}
                    className="p-3 rounded-lg bg-[#111622] border border-[#1c2738] hover:border-cyan-500/40 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-2 mb-1.5">
                      <div className="flex items-center space-x-2">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-950 text-cyan-300 border border-cyan-800">
                          {norm.app_label || 'App'}
                        </span>
                        <span className="text-xs font-bold text-slate-200">{norm.title || 'System Alert'}</span>
                        <span className="text-[10px] font-mono text-slate-500">[{norm.package_name}]</span>
                      </div>
                      <span className="text-[10px] font-mono text-slate-400 whitespace-nowrap">
                        {norm.timestamp_utc || art.timestamp_utc || 'N/A'}
                      </span>
                    </div>

                    <p className="text-xs text-slate-300 font-sans bg-[#090d13] p-2 rounded border border-[#17212f] select-text">
                      {norm.message_preview || '(No preview content)'}
                    </p>

                    <div className="mt-2 flex items-center justify-between text-[10px] font-mono text-slate-500">
                      <span>Source: <code>{art.source_file}</code> ({art.source_table})</span>
                      <button
                        onClick={() => handleCopy(norm.message_preview || '', art.id)}
                        className="hover:text-cyan-400 flex items-center space-x-1"
                      >
                        {copiedId === art.id ? <Check size={11} className="text-emerald-400" /> : <Copy size={11} />}
                        <span>{copiedId === art.id ? 'Copied' : 'Copy Text'}</span>
                      </button>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="text-center py-16 text-slate-500 text-xs">
                No notification records match query. Ingest notification databases (e.g. notification_log.db, wpndatabase.db).
              </div>
            )}
          </div>
        )}

        {/* ================= 2. DOWNLOADS TAB ================= */}
        {activeTab === 'downloads' && (
          <div className="space-y-2.5">
            {filteredDownloads.length > 0 ? (
              filteredDownloads.map((art) => {
                const norm = art.normalized_data || {};
                return (
                  <div
                    key={art.id}
                    className="p-3.5 rounded-lg bg-[#111622] border border-[#1c2738] hover:border-cyan-500/40 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <div className="flex items-center space-x-2.5">
                        <div className="p-2 rounded bg-cyan-950/60 border border-cyan-800 text-cyan-400">
                          <Download size={16} />
                        </div>
                        <div>
                          <div className="text-sm font-bold text-slate-100">{norm.filename}</div>
                          <span className="text-[10px] text-slate-500 font-mono">{norm.mime_type}</span>
                        </div>
                      </div>

                      <div className="flex flex-col items-end">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-800">
                          {norm.download_status || 'Completed'}
                        </span>
                        <span className="text-[10px] font-mono text-slate-400 mt-1">
                          {norm.file_size_bytes ? `${(norm.file_size_bytes / 1024).toFixed(1)} KB` : '0 KB'}
                        </span>
                      </div>
                    </div>

                    {norm.source_url && (
                      <div className="text-xs bg-[#090d13] p-2 rounded border border-[#17212f] font-mono text-slate-300 flex items-center justify-between mb-2 select-text">
                        <div className="truncate max-w-[85%]">
                          <span className="text-[10px] text-slate-500 block uppercase font-sans font-bold">Source URL:</span>
                          <span className="text-cyan-300">{norm.source_url}</span>
                        </div>
                        <button
                          onClick={() => handleCopy(norm.source_url, art.id)}
                          className="p-1 hover:text-cyan-400"
                          title="Copy Source URL"
                        >
                          {copiedId === art.id ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                        </button>
                      </div>
                    )}

                    <div className="flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono text-slate-500 pt-1 border-t border-[#182333]">
                      <span>Path: <code>{norm.destination_path || 'N/A'}</code></span>
                      <span>Downloaded: {norm.timestamp_utc || art.timestamp_utc || 'N/A'}</span>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="text-center py-16 text-slate-500 text-xs">
                No download records found. Ingest Android DownloadManager (downloads.db) or browser databases.
              </div>
            )}
          </div>
        )}

        {/* ================= 3. INSTALLED APPS TAB ================= */}
        {activeTab === 'apps' && (
          <div className="space-y-3">
            {filteredApps.length > 0 ? (
              filteredApps.map((art) => {
                const norm = art.normalized_data || {};
                const isRisky = norm.high_risk_surveillance;
                const permissions: string[] = norm.permissions || [];
                return (
                  <div
                    key={art.id}
                    className={`p-3.5 rounded-lg border transition-all ${
                      isRisky
                        ? 'bg-[#15121c] border-rose-800/60 shadow-sm shadow-rose-950/30'
                        : 'bg-[#111622] border-[#1c2738] hover:border-slate-600'
                    }`}
                  >
                    <div className="flex flex-wrap items-start justify-between gap-2 mb-2">
                      <div className="flex items-center space-x-2.5">
                        <div className={`p-2 rounded border ${
                          isRisky ? 'bg-rose-950/80 text-rose-400 border-rose-800' : 'bg-slate-800 text-cyan-400 border-slate-700'
                        }`}>
                          <Package size={16} />
                        </div>
                        <div>
                          <div className="text-sm font-bold text-slate-100 font-mono">{norm.package_name}</div>
                          <span className="text-[10px] text-slate-500">Source: {norm.installer || 'Sideloaded APK'}</span>
                        </div>
                      </div>

                      <div className="flex items-center space-x-2">
                        {isRisky && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-950 text-rose-300 border border-rose-700 flex items-center space-x-1">
                            <ShieldAlert size={12} />
                            <span>SURVEILLANCE RISK</span>
                          </span>
                        )}
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#172333] text-cyan-300 border border-[#26374f]">
                          {permissions.length} Perms
                        </span>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px] font-mono text-slate-400 bg-[#090d13] p-2 rounded border border-[#17212f] mb-2">
                      <div><strong className="text-slate-500">APK Path:</strong> <code className="text-slate-300">{norm.code_path}</code></div>
                      <div><strong className="text-slate-500">Install Time:</strong> {norm.install_time_utc || 'N/A'}</div>
                    </div>

                    {permissions.length > 0 && (
                      <div className="text-xs">
                        <span className="text-[10px] text-slate-500 uppercase font-semibold block mb-1">
                          Audited Permissions:
                        </span>
                        <div className="flex flex-wrap gap-1">
                          {permissions.map((perm: string) => {
                            const isDangerous =
                              perm.includes('SMS') ||
                              perm.includes('RECORD_AUDIO') ||
                              perm.includes('CAMERA') ||
                              perm.includes('LOCATION') ||
                              perm.includes('SYSTEM_ALERT_WINDOW');
                            return (
                              <span
                                key={perm}
                                className={`px-2 py-0.5 rounded text-[9px] font-mono border ${
                                  isDangerous
                                    ? 'bg-rose-950/70 text-rose-300 border-rose-800'
                                    : 'bg-[#151d2a] text-slate-400 border-[#222e40]'
                                }`}
                              >
                                {perm.replace('android.permission.', '')}
                              </span>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })
            ) : (
              <div className="text-center py-16 text-slate-500 text-xs">
                No installed packages match current filters. Ingest packages.xml or run live device inspection.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
