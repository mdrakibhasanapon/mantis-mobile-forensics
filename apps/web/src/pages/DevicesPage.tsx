import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Case } from '../types';
import {
  Smartphone,
  CheckCircle,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Terminal,
  ShieldCheck,
  ShieldAlert,
  Battery,
  HardDrive,
  DownloadCloud,
  CheckCircle2,
  Cpu,
} from 'lucide-react';

interface DevicesPageProps {
  activeCase?: Case | null;
  onRefreshEvidence?: () => void;
  onNavigateTab?: (tab: string) => void;
}

export const DevicesPage: React.FC<DevicesPageProps> = ({
  activeCase,
  onRefreshEvidence,
  onNavigateTab,
}) => {
  const [deviceData, setDeviceData] = useState<any>(null);
  const [selectedDevice, setSelectedDevice] = useState<any | null>(null);
  const [deviceDetails, setDeviceDetails] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isInspecting, setIsInspecting] = useState(false);
  const [isAcquiring, setIsAcquiring] = useState(false);
  const [acqMode, setAcqMode] = useState<'quick' | 'media' | 'packages'>('quick');
  const [statusMsg, setStatusMsg] = useState('');

  const fetchStatus = () => {
    setIsLoading(true);
    api.getDeviceStatus()
      .then((data) => {
        setDeviceData(data);
        if (data?.adb?.devices && data.adb.devices.length > 0) {
          setSelectedDevice(data.adb.devices[0]);
          loadDeviceDetails(data.adb.devices[0].serial);
        }
      })
      .catch(console.error)
      .finally(() => setIsLoading(false));
  };

  const loadDeviceDetails = (serial: string) => {
    setIsInspecting(true);
    api.getDeviceDetails(serial)
      .then(setDeviceDetails)
      .catch(console.error)
      .finally(() => setIsInspecting(false));
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleStartAcquisition = async () => {
    if (!selectedDevice || !activeCase) return;
    setIsAcquiring(true);
    setStatusMsg(`Initiating live ADB extraction (${acqMode}) from device ${selectedDevice.serial}...`);

    try {
      const res = await api.acquireLiveDevice(selectedDevice.serial, activeCase.id, acqMode);
      setStatusMsg('Acquisition running in background engine. Monitoring job...');

      const interval = setInterval(async () => {
        try {
          const jobs = await api.listJobs(activeCase.id);
          const activeJob = jobs.find((j) => j.id === res.job_id);
          if (activeJob) {
            setStatusMsg(`Progress: ${activeJob.message} (${activeJob.progress}%)`);
            if (activeJob.status === 'completed') {
              clearInterval(interval);
              setIsAcquiring(false);
              setStatusMsg('Live ADB extraction vaulted and cryptographically verified!');
              if (onRefreshEvidence) onRefreshEvidence();
              if (onNavigateTab) setTimeout(() => onNavigateTab('evidence'), 1200);
            } else if (activeJob.status === 'failed') {
              clearInterval(interval);
              setIsAcquiring(false);
              setStatusMsg(`Extraction failed: ${activeJob.error}`);
            }
          }
        } catch {
          clearInterval(interval);
          setIsAcquiring(false);
        }
      }, 1000);
    } catch (err: any) {
      setIsAcquiring(false);
      setStatusMsg(`Error: ${err.message}`);
    }
  };

  const adb = deviceData?.adb;

  return (
    <div className="flex-1 h-full min-h-0 overflow-y-auto p-4 bg-[#0c0f14] space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-[#1c2738]">
        <div>
          <h2 className="text-lg font-bold text-slate-100 tracking-wide">Connected Devices & Live Extraction</h2>
          <p className="text-xs text-slate-400">
            Hardware discovery, root privilege verification, live ADB logical extraction, and iOS utility detection.
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

      {statusMsg && (
        <div className="p-3 rounded-lg bg-cyan-950/40 border border-cyan-800 text-cyan-300 text-xs font-mono flex items-center space-x-2">
          <CheckCircle2 size={14} className="flex-shrink-0" />
          <span>{statusMsg}</span>
        </div>
      )}

      {/* Tool Matrix */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* ADB Android card */}
        <div className="bg-[#10151f] border border-[#1c2738] rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between">
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

          <p className="text-xs text-slate-400 font-sans">
            {adb?.available
              ? `Host tool: ${adb.version}`
              : 'Android platform-tools not found in PATH. Install via "sudo apt install adb" to enable live physical extraction.'}
          </p>

          <div className="bg-[#090d13] rounded p-3 border border-[#182333] text-xs font-mono">
            <div className="text-[11px] text-slate-400 font-semibold mb-2 uppercase">
              Connected Android Devices ({adb?.devices?.length || 0})
            </div>
            {adb?.devices && adb.devices.length > 0 ? (
              adb.devices.map((d: any, i: number) => {
                const isSelected = selectedDevice?.serial === d.serial;
                return (
                  <div
                    key={i}
                    onClick={() => {
                      setSelectedDevice(d);
                      loadDeviceDetails(d.serial);
                    }}
                    className={`flex items-center justify-between p-2 rounded cursor-pointer transition-colors ${
                      isSelected
                        ? 'bg-[#142030] border border-cyan-500/50 text-cyan-300'
                        : 'hover:bg-[#121924] border border-transparent'
                    }`}
                  >
                    <span className="font-bold">{d.serial}</span>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                      d.authorized ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-rose-950 text-rose-400 border border-rose-800'
                    }`}>
                      {d.state.toUpperCase()}
                    </span>
                    <span className="text-slate-500 text-[11px] truncate max-w-[150px]">{d.details}</span>
                  </div>
                );
              })
            ) : (
              <div className="text-slate-500 py-3 text-center">
                No USB Android devices detected. Enable USB debugging on the handset.
              </div>
            )}
          </div>
        </div>

        {/* iOS Libimobiledevice card */}
        <div className="bg-[#10151f] border border-[#1c2738] rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Smartphone size={18} className="text-blue-400" />
              <h3 className="text-sm font-semibold text-slate-200">Apple iOS / iPadOS Utilities</h3>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-950/60 text-amber-400 border border-amber-800 flex items-center space-x-1">
              <AlertTriangle size={12} />
              <span>DIRECTORY IMPORT ONLY</span>
            </span>
          </div>

          <p className="text-xs text-slate-400 font-sans">
            Live Apple device pairing requires libimobiledevice suite. iOS Finder/iTunes backup folders can be directly imported via the Acquisition & Import panel without external tools.
          </p>

          <div className="bg-[#090d13] rounded p-3 border border-[#182333] text-xs font-mono space-y-1">
            <div className="text-slate-400 font-semibold mb-1 uppercase text-[10px]">Supported Extraction Formats:</div>
            <div className="text-slate-300">• Unencrypted iTunes / Finder Backup folders (Manifest.db, Info.plist)</div>
            <div className="text-slate-300">• Password-authorized Encrypted iOS Backups</div>
            <div className="text-slate-300">• Third-party iOS forensic file extractions (.tar, .zip)</div>
          </div>
        </div>
      </div>

      {/* Live Device Hardware & Extraction Control Panel */}
      {selectedDevice && (
        <div className="bg-[#10151f] border border-[#1c2738] rounded-lg p-4 space-y-4">
          <div className="flex flex-wrap items-center justify-between pb-2 border-b border-[#182333] gap-2">
            <div>
              <h3 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                <span>Selected Device:</span>
                <span className="text-cyan-400 font-mono">{selectedDevice.serial}</span>
              </h3>
              <p className="text-[11px] text-slate-400">
                Execute live forensic logical pull, diagnostics dump, and root execution inspection.
              </p>
            </div>

            <div className="flex items-center space-x-2">
              {deviceDetails?.root_status && (
                <span className={`px-2.5 py-1 rounded text-xs font-bold flex items-center space-x-1.5 ${
                  deviceDetails.root_status.is_rooted
                    ? 'bg-rose-950/80 text-rose-400 border border-rose-800'
                    : 'bg-emerald-950/80 text-emerald-400 border border-emerald-800'
                }`}>
                  {deviceDetails.root_status.is_rooted ? <ShieldAlert size={13} /> : <ShieldCheck size={13} />}
                  <span>{deviceDetails.root_status.is_rooted ? 'ROOT PRIVILEGES ACTIVE' : 'NON-ROOTED (STANDARD USER)'}</span>
                </span>
              )}
            </div>
          </div>

          {/* Properties & Diagnostics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
            <div className="bg-[#090d13] p-2.5 rounded border border-[#17212f]">
              <span className="text-[10px] text-slate-500 uppercase font-sans">Manufacturer</span>
              <div className="text-slate-200 font-bold mt-0.5 truncate">
                {deviceDetails?.properties?.manufacturer || 'Unknown'}
              </div>
            </div>
            <div className="bg-[#090d13] p-2.5 rounded border border-[#17212f]">
              <span className="text-[10px] text-slate-500 uppercase font-sans">Model / Device</span>
              <div className="text-cyan-300 font-bold mt-0.5 truncate">
                {deviceDetails?.properties?.model || 'Unknown'}
              </div>
            </div>
            <div className="bg-[#090d13] p-2.5 rounded border border-[#17212f]">
              <span className="text-[10px] text-slate-500 uppercase font-sans">Android OS</span>
              <div className="text-emerald-300 font-bold mt-0.5">
                {deviceDetails?.properties?.os_version ? `Android ${deviceDetails.properties.os_version}` : 'N/A'}
              </div>
            </div>
            <div className="bg-[#090d13] p-2.5 rounded border border-[#17212f]">
              <span className="text-[10px] text-slate-500 uppercase font-sans">Battery Level</span>
              <div className="text-amber-300 font-bold mt-0.5 flex items-center space-x-1">
                <Battery size={13} />
                <span>{deviceDetails?.diagnostics?.battery?.level ? `${deviceDetails.diagnostics.battery.level}%` : 'N/A'}</span>
              </div>
            </div>
          </div>

          {/* Acquisition Workflow Controls */}
          <div className="bg-[#0b1017] p-3 rounded-lg border border-[#172333] space-y-3">
            <div className="text-xs font-bold text-slate-200 uppercase tracking-wide">
              Execute Live Acquisition Into Active Case: {activeCase ? activeCase.case_number : 'No Active Case Selected'}
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <label className="text-xs text-slate-400 font-semibold">Acquisition Profile:</label>
              <div className="flex bg-[#121924] p-1 rounded-md border border-[#1e2a3c]">
                <button
                  onClick={() => setAcqMode('quick')}
                  className={`px-3 py-1 rounded text-xs font-semibold transition-colors ${
                    acqMode === 'quick' ? 'bg-cyan-600 text-white' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Quick Triage (Properties + Packages + Logcat)
                </button>
                <button
                  onClick={() => setAcqMode('media')}
                  className={`px-3 py-1 rounded text-xs font-semibold transition-colors ${
                    acqMode === 'media' ? 'bg-cyan-600 text-white' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Media Extraction (/sdcard/DCIM)
                </button>
              </div>

              <button
                onClick={handleStartAcquisition}
                disabled={isAcquiring || !activeCase || !selectedDevice.authorized}
                className="px-4 py-1.5 rounded text-xs font-bold bg-cyan-600 hover:bg-cyan-500 text-slate-950 transition-colors flex items-center space-x-1.5 shadow-md shadow-cyan-950 disabled:opacity-40"
              >
                <DownloadCloud size={14} className={isAcquiring ? 'animate-bounce' : ''} />
                <span>{isAcquiring ? 'Extracting Evidence...' : 'Start Live Acquisition'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
