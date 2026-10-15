import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Smartphone, CheckCircle, XCircle, AlertTriangle, RefreshCw, Terminal } from 'lucide-react';

export const DevicesPage: React.FC = () => {
  const [deviceData, setDeviceData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  const fetchStatus = () => {
    setIsLoading(true);
    api.getDeviceStatus()
      .then(setDeviceData)
      .catch(console.error)
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const adb = deviceData?.adb;

  return (
    <div className="flex-1 h-full min-h-0 overflow-y-auto p-4 bg-[#0c0f14] space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-[#1c2738]">
        <div>
          <h2 className="text-lg font-bold text-slate-100 tracking-wide">Connected Devices & Tool Detection</h2>
          <p className="text-xs text-slate-400">
            Runtime discovery of Android Platform-Tools (ADB), Apple iOS utilities, and physical connectivity.
          </p>
        </div>
        <button
          onClick={fetchStatus}
          disabled={isLoading}
          className="px-3 py-1.5 rounded text-xs font-semibold bg-[#16202e] border border-[#24344a] text-cyan-300 hover:border-cyan-500/50 transition-colors flex items-center space-x-1.5"
        >
          <RefreshCw size={13} className={isLoading ? 'animate-spin' : ''} />
          <span>Rescan Interfaces</span>
        </button>
      </div>

      {/* Tool Matrix */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* ADB Android card */}
        <div className="bg-[#10151f] border border-[#1c2738] rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              <Smartphone size={18} className="text-cyan-400" />
              <h3 className="text-sm font-semibold text-slate-200">Android Debug Bridge (ADB)</h3>
            </div>
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-semibold flex items-center space-x-1 ${
                adb?.available
                  ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800'
                  : 'bg-amber-950/60 text-amber-400 border border-amber-800'
              }`}
            >
              {adb?.available ? <CheckCircle size={12} /> : <AlertTriangle size={12} />}
              <span>{adb?.available ? 'TOOL DETECTED' : 'NOT INSTALLED'}</span>
            </span>
          </div>
          <p className="text-xs text-slate-400 mb-3 font-sans">
            {adb?.available
              ? `Host tool: ${adb.version}`
              : 'Android platform-tools not found in PATH. Install via Kali terminal using "sudo apt install adb" to enable live physical extraction.'}
          </p>

          <div className="bg-[#090d13] rounded p-3 border border-[#182333] text-xs font-mono">
            <div className="text-[11px] text-slate-400 font-semibold mb-2 uppercase">Connected Android Devices ({adb?.devices?.length || 0})</div>
            {adb?.devices && adb.devices.length > 0 ? (
              adb.devices.map((d: any, i: number) => (
                <div key={i} className="flex items-center justify-between py-1 border-b border-[#151e2b] last:border-0">
                  <span className="text-cyan-300">{d.serial}</span>
                  <span className="text-emerald-400 font-semibold">{d.state}</span>
                  <span className="text-slate-500">{d.details}</span>
                </div>
              ))
            ) : (
              <div className="text-slate-500 py-2">No authorized USB Android devices detected.</div>
            )}
          </div>
        </div>

        {/* iOS Libimobiledevice card */}
        <div className="bg-[#10151f] border border-[#1c2738] rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              <Smartphone size={18} className="text-blue-400" />
              <h3 className="text-sm font-semibold text-slate-200">Apple iOS / iPadOS Utilities</h3>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-950/60 text-amber-400 border border-amber-800 flex items-center space-x-1">
              <AlertTriangle size={12} />
              <span>DIRECTORY IMPORT ONLY</span>
            </span>
          </div>
          <p className="text-xs text-slate-400 mb-3 font-sans">
            Live Apple device pairing requires libimobiledevice suite. iOS Finder/iTunes backup folders can be directly imported via the Acquisition & Import panel without external tools.
          </p>
          <div className="bg-[#090d13] rounded p-3 border border-[#182333] text-xs font-mono space-y-1">
            <div className="text-slate-400 font-semibold mb-1">SUPPORTED EXTRACTION FORMATS:</div>
            <div className="text-slate-300">• Unencrypted iTunes / Finder Backup folders (Manifest.db, Info.plist)</div>
            <div className="text-slate-300">• Password-authorized Encrypted iOS Backups</div>
            <div className="text-slate-300">• Third-party iOS forensic file extractions (.tar, .zip)</div>
          </div>
        </div>
      </div>
    </div>
  );
};
