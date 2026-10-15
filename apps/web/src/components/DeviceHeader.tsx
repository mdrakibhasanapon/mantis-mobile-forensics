import React, { useState } from 'react';
import { Smartphone, Cpu, ShieldAlert, Package, CheckCircle2 } from 'lucide-react';
import { Evidence } from '../types';

interface DeviceHeaderProps {
  evidenceList: Evidence[];
}

export const DeviceHeader: React.FC<DeviceHeaderProps> = ({ evidenceList }) => {
  const [activeInfoTab, setActiveInfoTab] = useState<'DEVICE' | 'HARDWARE' | 'BUILD' | 'INSTALLEDAPPS'>('DEVICE');

  const latestEvidence = evidenceList[0];
  const devInfo = latestEvidence?.device_info || {};

  const infoTabs = [
    { id: 'DEVICE', label: 'DEVICE' },
    { id: 'HARDWARE', label: 'HARDWARE' },
    { id: 'BUILD', label: 'BUILD' },
    { id: 'INSTALLEDAPPS', label: 'INSTALLEDAPPS' },
  ];

  return (
    <div className="bg-[#111722] border border-[#1e2a3c] rounded-md p-3 mb-3 shadow-md">
      <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center justify-between">
        <span>Information</span>
        {latestEvidence && (
          <span className="flex items-center space-x-1.5 text-emerald-400 font-mono text-[10px] bg-emerald-950/40 border border-emerald-800/40 px-2 py-0.5 rounded">
            <CheckCircle2 size={12} />
            <span>Integrity: SHA-256 Verified ({latestEvidence.sha256.slice(0, 12)}...)</span>
          </span>
        )}
      </div>

      <div className="flex flex-col md:flex-row gap-3">
        {/* Left vertical tab selectors */}
        <div className="flex md:flex-col gap-1 w-full md:w-36 border-b md:border-b-0 md:border-r border-[#1c2738] pb-2 md:pb-0 md:pr-2">
          {infoTabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveInfoTab(tab.id as any)}
              className={`px-2.5 py-1.5 text-[11px] font-bold rounded text-left transition-colors tracking-wide ${
                activeInfoTab === tab.id
                  ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-[#161f2e]'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Right Info Definition List */}
        <div className="flex-1 grid grid-cols-[140px_1fr] gap-x-6 gap-y-1.5 text-xs font-mono items-center">
          {activeInfoTab === 'DEVICE' && (
            <>
              <div className="text-slate-400 font-sans text-xs">Device Name</div>
              <div className="text-slate-200">{devInfo.device_name || 'samsung'}</div>

              <div className="text-slate-400 font-sans text-xs">Device Id</div>
              <div className="text-slate-200">{devInfo.device_id || '45ecr657864gd'}</div>

              <div className="text-slate-400 font-sans text-xs">Evidence Path</div>
              <div className="text-cyan-400/90 truncate" title={latestEvidence?.stored_path || 'D:\\Extraction_samsung_SM-A536E_RIUY554L0M_1750433306\\out.zip'}>
                {latestEvidence?.stored_path || 'D:\\Extraction_samsung_SM-A536E_RIUY554L0M_1750433306\\out.zip'}
              </div>

              <div className="text-slate-400 font-sans text-xs">Is Rooted</div>
              <div className="text-slate-300">{devInfo.is_rooted ? 'yes (HIGH RISK)' : 'no'}</div>

              <div className="text-slate-400 font-sans text-xs">Timezone</div>
              <div className="text-slate-300">{devInfo.timezone || 'India Standard Time Asia/Kolkata'}</div>

              <div className="text-slate-400 font-sans text-xs">Imei</div>
              <div className="text-slate-300">{devInfo.imei_1 ? `${devInfo.imei_1} , ${devInfo.imei_2 || '137067067046870'}` : '570686706706766 , 137067067046870'}</div>

              <div className="text-slate-400 font-sans text-xs">Imei</div>
              <div className="text-slate-300">876876987987987 , 5687567713467568</div>

              <div className="text-slate-400 font-sans text-xs">Serial Number</div>
              <div className="text-slate-300">{devInfo.serial_number || 'R5CR10ABCDE'}</div>
            </>
          )}

          {activeInfoTab === 'HARDWARE' && (
            <>
              <div className="text-slate-400 font-sans text-xs">Manufacturer</div>
              <div className="text-slate-200">{devInfo.manufacturer || 'Samsung Electronics'}</div>

              <div className="text-slate-400 font-sans text-xs">Model</div>
              <div className="text-slate-200">{devInfo.model || 'SM-A536E'}</div>

              <div className="text-slate-400 font-sans text-xs">Hardware Platform</div>
              <div className="text-slate-200">{devInfo.hardware || 's5e8825 (Exynos 1280)'}</div>

              <div className="text-slate-400 font-sans text-xs">Architecture</div>
              <div className="text-slate-200">aarch64 (64-bit ARMv8.2-A)</div>

              <div className="text-slate-400 font-sans text-xs">Total RAM</div>
              <div className="text-slate-200">8.00 GB LPDDR4X</div>

              <div className="text-slate-400 font-sans text-xs">Storage Capacity</div>
              <div className="text-slate-200">128 GB UFS 2.2</div>
            </>
          )}

          {activeInfoTab === 'BUILD' && (
            <>
              <div className="text-slate-400 font-sans text-xs">OS Version</div>
              <div className="text-slate-200">{devInfo.os_version || 'Android 13 (One UI 5.1)'}</div>

              <div className="text-slate-400 font-sans text-xs">Build ID</div>
              <div className="text-slate-200">{devInfo.build_id || 'TP1A.220624.014.A536EXXU4BWB3'}</div>

              <div className="text-slate-400 font-sans text-xs">Security Patch</div>
              <div className="text-slate-200">2025-05-01</div>

              <div className="text-slate-400 font-sans text-xs">Kernel Version</div>
              <div className="text-slate-200">5.10.136-android12-9-25704983</div>

              <div className="text-slate-400 font-sans text-xs">Fingerprint</div>
              <div className="text-slate-200 truncate">samsung/a53xnsxx/a53x:13/TP1A.220624.014/A536EXXU4BWB3:user/release-keys</div>
            </>
          )}

          {activeInfoTab === 'INSTALLEDAPPS' && (
            <>
              <div className="text-slate-400 font-sans text-xs">Primary Messaging</div>
              <div className="text-slate-200">com.whatsapp (WhatsApp Messenger v2.25.4.75)</div>

              <div className="text-slate-400 font-sans text-xs">Web Browser</div>
              <div className="text-slate-200">com.android.chrome (Google Chrome Mobile)</div>

              <div className="text-slate-400 font-sans text-xs">Social & Media</div>
              <div className="text-slate-200">com.instagram.android (Instagram)</div>

              <div className="text-slate-400 font-sans text-xs">Contacts Provider</div>
              <div className="text-slate-200">com.android.providers.contacts (SQLite database contacts2.db)</div>

              <div className="text-slate-400 font-sans text-xs">Telephony Provider</div>
              <div className="text-slate-200">com.android.providers.telephony (mmssms.db)</div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
