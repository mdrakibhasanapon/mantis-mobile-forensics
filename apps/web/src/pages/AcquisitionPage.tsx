import React, { useState, useRef } from 'react';
import { api } from '../api/client';
import { Case } from '../types';
import {
  DownloadCloud,
  Sparkles,
  FolderUp,
  FileCode,
  Folder,
  CheckCircle,
  RefreshCw,
  HardDrive,
  UploadCloud,
  AlertTriangle,
} from 'lucide-react';

interface AcquisitionPageProps {
  activeCase: Case | null;
  onRefreshEvidence: () => void;
  onNavigateTab: (tab: string) => void;
}

function parseErrorMessage(err: any): string {
  if (!err) return 'Unknown error';
  const raw = err.message || String(err);
  try {
    const jsonMatch = raw.match(/\{.*detail.*:\s*"([^"]+)".*\}/);
    if (jsonMatch && jsonMatch[1]) {
      return jsonMatch[1].replace(/\\"/g, '"');
    }
    const cleanStr = raw.replace(/^API Error \[\d+\]:\s*/, '');
    const parsed = JSON.parse(cleanStr);
    if (parsed.detail) return parsed.detail;
  } catch {}
  return raw;
}

export const AcquisitionPage: React.FC<AcquisitionPageProps> = ({
  activeCase,
  onRefreshEvidence,
  onNavigateTab,
}) => {
  const [deviceName, setDeviceName] = useState('Samsung Galaxy S22 Ultra');
  const [isGenerating, setIsGenerating] = useState(false);
  const [importPath, setImportPath] = useState('');
  const [isImporting, setIsImporting] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [statusType, setStatusType] = useState<'info' | 'error' | 'success'>('info');
  const [isDragOver, setIsDragOver] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);

  const handleGenerateSynthetic = async () => {
    if (!activeCase) return;
    setIsGenerating(true);
    setStatusMsg('Generating realistic multi-platform synthetic mobile extraction package...');
    try {
      const res = await api.generateSynthetic(activeCase.id, deviceName);
      setStatusMsg('Extraction running in background engine. Monitoring job...');
      const interval = setInterval(async () => {
        try {
          const job = await api.listJobs(activeCase.id);
          const activeJob = job.find((j) => j.id === res.job_id);
          if (activeJob) {
            setStatusMsg(`Processing: ${activeJob.message} (${activeJob.progress}%)`);
            if (activeJob.status === 'completed') {
              clearInterval(interval);
              setIsGenerating(false);
              setStatusMsg('Synthetic dataset successfully created, vaulted, and parsed!');
              onRefreshEvidence();
              setTimeout(() => onNavigateTab('dashboard'), 1000);
            } else if (activeJob.status === 'failed') {
              clearInterval(interval);
              setIsGenerating(false);
              setStatusMsg(`Failed: ${activeJob.error}`);
            }
          }
        } catch (e) {
          clearInterval(interval);
          setIsGenerating(false);
        }
      }, 1000);
    } catch (err: any) {
      setIsGenerating(false);
      setStatusMsg(`Error: ${err.message}`);
    }
  };

  const handleSelectFile = async () => {
    if (window.mantisDesktop?.showOpenDialog) {
      try {
        const res = await window.mantisDesktop.showOpenDialog({
          title: 'Select Mobile Forensic Extraction or Archive',
          properties: ['openFile'],
          filters: [
            {
              name: 'Forensic Images & Archives',
              extensions: ['zip', 'tar', 'gz', 'bz2', '7z', 'db', 'sqlite', 'dd', 'raw', 'e01', 'ab', 'dmg', 'iso'],
            },
            { name: 'All Files', extensions: ['*'] },
          ],
        });
        if (!res.canceled && res.filePaths && res.filePaths.length > 0) {
          setImportPath(res.filePaths[0]);
          setStatusMsg(`Selected file: ${res.filePaths[0]}`);
        }
      } catch (err) {
        console.error('File dialog error:', err);
      }
    } else if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleSelectFolder = async () => {
    if (window.mantisDesktop?.showOpenDialog) {
      try {
        const res = await window.mantisDesktop.showOpenDialog({
          title: 'Select Extracted Mobile Filesystem Directory',
          properties: ['openDirectory'],
        });
        if (!res.canceled && res.filePaths && res.filePaths.length > 0) {
          setImportPath(res.filePaths[0]);
          setStatusMsg(`Selected folder: ${res.filePaths[0]}`);
        }
      } catch (err) {
        console.error('Folder dialog error:', err);
      }
    } else if (folderInputRef.current) {
      folderInputRef.current.click();
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // In Electron, File objects contain the absolute path on .path
      const filePath = (file as any).path || file.name;
      setImportPath(filePath);
      setStatusMsg(`Selected: ${filePath}`);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      const filePath = (file as any).path || file.name;
      setImportPath(filePath);
      setStatusMsg(`Selected via Drop: ${filePath}`);
    }
  };

  const handleImportPath = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeCase || !importPath.trim()) return;
    setIsImporting(true);
    setStatusType('info');
    setStatusMsg(`Importing evidence from ${importPath}...`);
    try {
      await api.importPath(activeCase.id, importPath.trim(), 'archive');
      setIsImporting(false);
      setStatusType('success');
      setStatusMsg('Evidence successfully imported into read-only vault!');
      onRefreshEvidence();
      setTimeout(() => onNavigateTab('evidence'), 800);
    } catch (err: any) {
      setIsImporting(false);
      setStatusType('error');
      const cleanErr = parseErrorMessage(err);
      setStatusMsg(cleanErr);
    }
  };

  return (
    <div className="flex-1 h-full min-h-0 overflow-y-auto p-4 bg-[#0c0f14] space-y-4">
      <div className="pb-3 border-b border-[#1c2738]">
        <h2 className="text-lg font-bold text-slate-100 tracking-wide">Acquisition & Evidence Intake</h2>
        <p className="text-xs text-slate-400">
          Select and import forensic images, archives, directories, or generate synthetic mobile datasets.
        </p>
      </div>

      {statusMsg && (
        <div
          className={`p-3 rounded border text-xs font-mono flex items-start space-x-2.5 transition-all ${
            statusType === 'error'
              ? 'bg-rose-950/60 border-rose-800/70 text-rose-200 shadow-lg shadow-rose-950/30'
              : statusType === 'success'
              ? 'bg-emerald-950/50 border-emerald-800/60 text-emerald-300'
              : 'bg-cyan-950/40 border-cyan-800/50 text-cyan-300'
          }`}
        >
          {statusType === 'error' ? (
            <AlertTriangle size={15} className="text-rose-400 flex-shrink-0 mt-0.5" />
          ) : statusType === 'success' ? (
            <CheckCircle size={15} className="text-emerald-400 flex-shrink-0 mt-0.5" />
          ) : (
            <RefreshCw
              size={14}
              className={`text-cyan-400 flex-shrink-0 mt-0.5 ${isGenerating || isImporting ? 'animate-spin' : ''}`}
            />
          )}
          <div className="flex-1 select-text leading-relaxed font-sans font-medium text-xs">
            <span>{statusMsg}</span>
          </div>
          <button
            onClick={() => setStatusMsg('')}
            className="text-slate-400 hover:text-slate-200 ml-2 font-bold text-sm leading-none"
            title="Dismiss message"
          >
            &times;
          </button>
        </div>
      )}

      {/* Hidden browser file inputs for fallback */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileInputChange}
        className="hidden"
        accept=".zip,.tar,.gz,.bz2,.7z,.db,.sqlite,.dd,.raw,.e01,.ab"
      />
      <input
        type="file"
        ref={folderInputRef}
        onChange={handleFileInputChange}
        className="hidden"
        {...({ webkitdirectory: '', directory: '' } as any)}
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Manual Local File / Directory Select & Import */}
        <form onSubmit={handleImportPath} className="bg-[#10151f] border border-[#1c2738] rounded-lg p-4 flex flex-col justify-between shadow-lg">
          <div>
            <div className="flex items-center space-x-2 mb-2">
              <FolderUp size={18} className="text-emerald-400" />
              <h3 className="text-sm font-semibold text-slate-100">Select Forensic Image or Directory</h3>
            </div>
            <p className="text-xs text-slate-400 mb-3">
              Browse your filesystem to import forensic archives (ZIP, TAR, E01, DD, SQLite) or uncompressed extracted directories with cryptographic SHA-256 integrity verification.
            </p>

            {/* Quick Action Selector Buttons */}
            <div className="grid grid-cols-2 gap-2 mb-3">
              <button
                type="button"
                onClick={handleSelectFile}
                className="py-2 px-3 rounded bg-[#162030] border border-cyan-500/50 hover:bg-cyan-500/20 text-cyan-300 text-xs font-semibold flex items-center justify-center space-x-2 transition-all shadow-sm"
              >
                <FileCode size={15} />
                <span>Browse File / Archive...</span>
              </button>

              <button
                type="button"
                onClick={handleSelectFolder}
                className="py-2 px-3 rounded bg-[#162030] border border-[#2b3d56] hover:border-cyan-500/50 hover:bg-[#1a2638] text-slate-200 text-xs font-semibold flex items-center justify-center space-x-2 transition-all shadow-sm"
              >
                <Folder size={15} />
                <span>Browse Directory...</span>
              </button>
            </div>

            {/* Drag & Drop Zone */}
            <div
              onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
              onDragLeave={() => setIsDragOver(false)}
              onDrop={handleDrop}
              onClick={handleSelectFile}
              className={`border-2 border-dashed rounded-lg p-4 mb-3 text-center cursor-pointer transition-colors ${
                isDragOver
                  ? 'border-cyan-400 bg-cyan-950/30 text-cyan-300'
                  : 'border-[#223044] hover:border-cyan-500/50 bg-[#0e131d]'
              }`}
            >
              <UploadCloud size={24} className="mx-auto mb-1 text-slate-400" />
              <div className="text-xs font-medium text-slate-200">
                Click to Select or Drag & Drop Forensic File Here
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5 font-mono">
                Supports: .ZIP, .TAR, .GZ, .E01, .DD, .RAW, .DB, .SQLITE, .AB
              </div>
            </div>

            {/* Path Input Box */}
            <div className="space-y-1.5 text-xs mb-4">
              <label className="block text-slate-400 font-semibold">Evidence Filesystem Path</label>
              <input
                type="text"
                required
                placeholder="/path/to/extraction.zip or /path/to/extracted_folder"
                value={importPath}
                onChange={(e) => setImportPath(e.target.value)}
                className="w-full bg-[#16202e] border border-[#24344a] rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono text-xs"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isImporting || !activeCase || !importPath.trim()}
            className="w-full py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-slate-950 font-bold text-xs rounded transition-all flex items-center justify-center space-x-2 disabled:opacity-40 shadow-md"
          >
            <FolderUp size={15} />
            <span>{isImporting ? 'Vaulting & Calculating SHA-256...' : 'Import into Case Vault & Analyze'}</span>
          </button>
        </form>

        {/* Synthetic Generator Card */}
        <div className="bg-[#10151f] border border-cyan-500/40 rounded-lg p-4 flex flex-col justify-between shadow-lg">
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2">
                <Sparkles size={18} className="text-cyan-400" />
                <h3 className="text-sm font-semibold text-slate-100">Synthetic Mobile Extraction Generator</h3>
              </div>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
                AUTOMATED LAB DEMO
              </span>
            </div>
            <p className="text-xs text-slate-400 mb-3">
              Generates a full synthetic forensic extraction package containing Android SQLite databases (Contacts, SMS, Calls, Chrome, WhatsApp), iOS property lists (Info.plist), unallocated freelist records for recovery carving, and suspicious APK manifests for malware triage.
            </p>

            <div className="space-y-2 text-xs mb-4">
              <label className="block text-slate-400 font-semibold">Simulated Target Device Model</label>
              <input
                type="text"
                value={deviceName}
                onChange={(e) => setDeviceName(e.target.value)}
                className="w-full bg-[#16202e] border border-[#24344a] rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono text-xs"
              />
            </div>
          </div>

          <button
            onClick={handleGenerateSynthetic}
            disabled={isGenerating || !activeCase}
            className="w-full py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-slate-950 font-bold text-xs rounded transition-all shadow-md flex items-center justify-center space-x-2 disabled:opacity-40"
          >
            <DownloadCloud size={15} />
            <span>{isGenerating ? 'Generating & Parsing Dataset...' : 'Generate Synthetic Mobile Evidence & Parse'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
