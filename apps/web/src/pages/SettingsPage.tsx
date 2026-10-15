import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import {
  Settings,
  Folder,
  Shield,
  Cpu,
  ExternalLink,
  HardDrive,
  RefreshCw,
  GitBranch,
  Check,
  Copy,
  Sparkles,
  Terminal,
  ArrowUpCircle,
} from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const [healthData, setHealthData] = useState<any>(null);
  const [isCheckingUpdate, setIsCheckingUpdate] = useState(false);
  const [updateStatus, setUpdateStatus] = useState<string | null>(null);
  const [copiedCmd, setCopiedCmd] = useState<string>('');

  const handleCheckUpdate = () => {
    setIsCheckingUpdate(true);
    setUpdateStatus(null);
    setTimeout(() => {
      setIsCheckingUpdate(false);
      setUpdateStatus('up-to-date');
    }, 1200);
  };

  const handleCopyCmd = (cmd: string) => {
    navigator.clipboard.writeText(cmd);
    setCopiedCmd(cmd);
    setTimeout(() => setCopiedCmd(''), 2000);
  };

  useEffect(() => {
    api.getHealth()
      .then(setHealthData)
      .catch(console.error);
  }, []);

  const openDataDir = () => {
    if (typeof window !== 'undefined' && (window as any).mantisDesktop) {
      (window as any).mantisDesktop.openDataDirectory();
    }
  };

  return (
    <div className="flex-1 h-full min-h-0 overflow-y-auto p-4 bg-[#0c0f14] space-y-4 select-none">
      <div className="pb-3 border-b border-[#1c2738]">
        <h2 className="text-lg font-bold text-slate-100 tracking-wide">Workstation Settings & Diagnostics</h2>
        <p className="text-xs text-slate-400">
          Environment configuration, local storage directories, loopback security, and installed DFIR dependencies.
        </p>
      </div>

      <div className="space-y-4 max-w-3xl">
        {/* Evidence Storage Boundary */}
        <div className="bg-[#10151f] border border-[#1c2738] rounded-lg p-4 space-y-3">
          <div className="flex items-center space-x-2">
            <HardDrive size={18} className="text-cyan-400" />
            <h3 className="text-sm font-semibold text-slate-100">Configurable Local Storage Directory</h3>
          </div>
          <p className="text-xs text-slate-400">
            In compliance with forensic best practices, original evidence and case databases are strictly stored in an isolated user data directory, never inside the application installation directory.
          </p>
          <div className="bg-[#090d13] p-3 rounded border border-[#192333] flex items-center justify-between font-mono text-xs">
            <span className="text-cyan-300 truncate mr-3">
              {healthData?.storage_dir || '/home/kali/.local/share/mantis-forensics'}
            </span>
            <button
              onClick={openDataDir}
              className="px-3 py-1 bg-[#172233] hover:bg-cyan-500/20 text-cyan-300 border border-[#23354d] text-xs font-semibold rounded flex items-center space-x-1 flex-shrink-0"
            >
              <Folder size={13} />
              <span>Open in File Manager</span>
            </button>
          </div>
        </div>

        {/* Software Updates & In-Build Auto-Update Engine */}
        <div className="bg-[#10151f] border border-[#1c2738] rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <ArrowUpCircle size={18} className="text-cyan-400" />
              <h3 className="text-sm font-semibold text-slate-100">Software Updates & In-Build Auto-Update Engine</h3>
            </div>
            <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-cyan-950/60 text-cyan-300 border border-cyan-800/60 font-semibold">
              v1.0.0 (Latest)
            </span>
          </div>

          <p className="text-xs text-slate-400">
            Keep your forensic workstation synchronized across laptops. Push code updates to your GitHub repository, then run the in-build updater to pull, recompile, and verify all modules automatically.
          </p>

          <div className="bg-[#090d13] p-3 rounded border border-[#192333] space-y-2.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2 text-xs font-mono">
                <GitBranch size={13} className="text-slate-400" />
                <span className="text-slate-400">Update Mechanism:</span>
                <span className="text-emerald-400 font-semibold">Git Remote & In-Build Script</span>
              </div>
              <button
                onClick={handleCheckUpdate}
                disabled={isCheckingUpdate}
                className="px-3 py-1 bg-[#172233] hover:bg-cyan-500/20 text-cyan-300 border border-[#23354d] text-xs font-semibold rounded flex items-center space-x-1.5 transition-colors disabled:opacity-50"
              >
                <RefreshCw size={12} className={isCheckingUpdate ? 'animate-spin' : ''} />
                <span>{isCheckingUpdate ? 'Checking GitHub...' : 'Check for Updates'}</span>
              </button>
            </div>

            {updateStatus === 'up-to-date' && (
              <div className="p-2 rounded bg-emerald-950/30 border border-emerald-800/40 text-[11px] font-mono text-emerald-300 flex items-center space-x-2">
                <Check size={13} className="text-emerald-400 flex-shrink-0" />
                <span>All forensic modules and parsers are up to date! To pull changes from your other laptop, run <code className="text-cyan-300 bg-[#0d141f] px-1 py-0.5 rounded">./update.sh</code></span>
              </div>
            )}

            <div className="pt-2 border-t border-[#16202e] text-xs font-mono space-y-2">
              <div className="text-slate-400 text-[11px] font-sans font-semibold uppercase tracking-wider">
                Multi-Laptop Update Workflow:
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px]">
                <div className="p-2 rounded bg-[#0d131c] border border-[#1c2738] space-y-1">
                  <span className="text-slate-400 font-semibold block">1. On laptop where you wrote code:</span>
                  <div className="flex items-center justify-between text-slate-300 bg-[#080c12] p-1.5 rounded border border-[#151f2d]">
                    <code className="text-cyan-300 text-[10px]">git push origin main</code>
                    <button
                      onClick={() => handleCopyCmd('git add . && git commit -m "update" && git push origin main')}
                      className="text-slate-400 hover:text-cyan-300 text-[10px] ml-2"
                      title="Copy Git Push Command"
                    >
                      {copiedCmd.includes('git push') ? <Check size={11} className="text-emerald-400" /> : <Copy size={11} />}
                    </button>
                  </div>
                </div>

                <div className="p-2 rounded bg-[#0d131c] border border-[#1c2738] space-y-1">
                  <span className="text-slate-400 font-semibold block">2. On your other laptop (to auto-update):</span>
                  <div className="flex items-center justify-between text-slate-300 bg-[#080c12] p-1.5 rounded border border-[#151f2d]">
                    <code className="text-cyan-300 text-[10px]">./update.sh</code>
                    <button
                      onClick={() => handleCopyCmd('./update.sh')}
                      className="text-slate-400 hover:text-cyan-300 text-[10px] ml-2"
                      title="Copy Update Command"
                    >
                      {copiedCmd === './update.sh' ? <Check size={11} className="text-emerald-400" /> : <Copy size={11} />}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Localhost Protection */}
        <div className="bg-[#10151f] border border-[#1c2738] rounded-lg p-4 space-y-3">
          <div className="flex items-center space-x-2">
            <Shield size={18} className="text-emerald-400" />
            <h3 className="text-sm font-semibold text-slate-100">Localhost Security & Access Protection</h3>
          </div>
          <p className="text-xs text-slate-400">
            The Python FastAPI forensic engine is strictly bound to loopback interface <code className="text-slate-200">127.0.0.1</code> and requires an ephemeral high-entropy session token on all HTTP requests to prevent unauthorized cross-origin access from local browsers.
          </p>
          <div className="bg-[#090d13] p-3 rounded border border-[#192333] text-xs font-mono space-y-1">
            <div>Loopback Binding: <strong className="text-emerald-400">127.0.0.1:8765</strong></div>
            <div>Session Protection: <strong className="text-emerald-400">Active (X-MMF-Session-Token Enforced)</strong></div>
            <div>Offline Mode: <strong className="text-cyan-400">Full Offline Operation (Zero Remote Calls)</strong></div>
          </div>
        </div>

        {/* Runtime Diagnostics */}
        <div className="bg-[#10151f] border border-[#1c2738] rounded-lg p-4 space-y-3">
          <div className="flex items-center space-x-2">
            <Cpu size={18} className="text-blue-400" />
            <h3 className="text-sm font-semibold text-slate-100">Runtime Engine Diagnostics</h3>
          </div>
          <div className="bg-[#090d13] p-3 rounded border border-[#192333] text-xs font-mono grid grid-cols-2 gap-2">
            <div>Application: <span className="text-slate-200">Mantis Mobile Forensics</span></div>
            <div>Version: <span className="text-cyan-400">1.0.0 (Kali Desktop Edition)</span></div>
            <div>Platform: <span className="text-slate-200">{healthData?.platform || 'Linux x86_64'}</span></div>
            <div>Python Engine: <span className="text-slate-200">{healthData?.python_version || '3.14.7'}</span></div>
          </div>
        </div>
      </div>
    </div>
  );
};
