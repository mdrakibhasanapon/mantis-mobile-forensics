import React, { useState } from 'react';
import { api } from '../api/client';
import { Case } from '../types';
import { FileText, Download, ExternalLink, RefreshCw, FileCode, CheckCircle2 } from 'lucide-react';

interface ReportsPageProps {
  caseId: string;
  activeCase: Case | null;
}

export const ReportsPage: React.FC<ReportsPageProps> = ({ caseId, activeCase }) => {
  const [isGenerating, setIsGenerating] = useState(false);
  const [reportUrl, setReportUrl] = useState<string>(
    caseId ? api.getViewHtmlReportUrl(caseId) : ''
  );
  const [statusMsg, setStatusMsg] = useState('');

  const handleGenerate = async () => {
    if (!caseId) return;
    setIsGenerating(true);
    setStatusMsg('Compiling executive summary, evidence hashes, and timeline into HTML report...');
    try {
      await api.generateHtmlReport(caseId);
      setReportUrl(`${api.getViewHtmlReportUrl(caseId)}&t=${Date.now()}`);
      setStatusMsg('Forensic HTML report successfully generated!');
    } catch (err: any) {
      setStatusMsg(`Error: ${err.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleExportManifest = async () => {
    if (!caseId) return;
    try {
      const res = await api.exportManifest(caseId);
      const blob = new Blob([JSON.stringify(res.manifest, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `case_manifest_${activeCase?.case_number || 'export'}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-[#0c0f14] overflow-hidden select-none">
      {/* Top Controls */}
      <div className="p-3 bg-[#10151f] border-b border-[#1c2738] flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <FileText size={18} className="text-cyan-400" />
          <h2 className="text-sm font-bold text-slate-100">Forensic Investigation Reports & Manifests</h2>
        </div>

        <div className="flex items-center space-x-2">
          {statusMsg && (
            <span className="text-xs text-cyan-400 font-mono mr-2 flex items-center space-x-1">
              <CheckCircle2 size={13} />
              <span>{statusMsg}</span>
            </span>
          )}

          <button
            onClick={handleExportManifest}
            className="px-3 py-1.5 rounded text-xs font-semibold bg-[#172233] border border-[#26374f] text-slate-200 hover:text-cyan-300 hover:border-cyan-500/50 transition-colors flex items-center space-x-1.5"
          >
            <FileCode size={13} />
            <span>Export Manifest (JSON)</span>
          </button>

          <button
            onClick={handleGenerate}
            disabled={isGenerating || !caseId}
            className="px-3 py-1.5 rounded text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 text-slate-950 transition-colors flex items-center space-x-1.5 shadow-sm disabled:opacity-40"
          >
            <RefreshCw size={13} className={isGenerating ? 'animate-spin' : ''} />
            <span>Re-Generate HTML Report</span>
          </button>

          <a
            href={reportUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="px-3 py-1.5 rounded text-xs font-semibold bg-[#1a2538] border border-[#2c3d59] text-cyan-300 hover:bg-[#23324d] transition-colors flex items-center space-x-1.5"
          >
            <ExternalLink size={13} />
            <span>Open in Browser</span>
          </a>
        </div>
      </div>

      {/* Embedded Report Frame */}
      <div className="flex-1 bg-white">
        {caseId ? (
          <iframe
            src={reportUrl}
            title="Forensic Report Preview"
            className="w-full h-full border-none"
          />
        ) : (
          <div className="flex items-center justify-center h-full bg-[#0c0f14] text-slate-500 text-xs">
            Select or initialize a case to view report.
          </div>
        )}
      </div>
    </div>
  );
};
