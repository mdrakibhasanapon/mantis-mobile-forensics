import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { TriageFinding } from '../types';
import {
  ShieldAlert,
  AlertTriangle,
  Coins,
  CreditCard,
  Key,
  Globe,
  Search,
  RefreshCw,
  Copy,
  Check,
  FileText,
} from 'lucide-react';

interface TriagePageProps {
  caseId: string;
}

export const TriagePage: React.FC<TriagePageProps> = ({ caseId }) => {
  const [findings, setFindings] = useState<TriageFinding[]>([]);
  const [activeCategory, setActiveCategory] = useState<string>('all');
  const [isLoading, setIsLoading] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const fetchFindings = () => {
    if (!caseId) return;
    setIsLoading(true);
    api.getTriageFindings(caseId)
      .then(setFindings)
      .catch(console.error)
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    fetchFindings();
  }, [caseId]);

  const handleRunDeepScan = async () => {
    if (!caseId) return;
    setIsScanning(true);
    try {
      await api.runDeepTriageScan(caseId);
      fetchFindings();
    } catch (err) {
      console.error('Deep triage scan failed:', err);
    } finally {
      setIsScanning(false);
    }
  };

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const getSeverityBadge = (sev: string) => {
    switch (sev.toLowerCase()) {
      case 'critical':
        return <span className="px-2 py-0.5 rounded bg-rose-950/70 border border-rose-800 text-rose-400 font-bold text-[10px]">CRITICAL</span>;
      case 'high':
        return <span className="px-2 py-0.5 rounded bg-orange-950/70 border border-orange-800 text-orange-400 font-bold text-[10px]">HIGH</span>;
      case 'medium':
        return <span className="px-2 py-0.5 rounded bg-amber-950/70 border border-amber-800 text-amber-400 font-bold text-[10px]">MEDIUM</span>;
      default:
        return <span className="px-2 py-0.5 rounded bg-blue-950/70 border border-blue-800 text-blue-400 font-bold text-[10px]">LOW</span>;
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'cryptocurrency':
        return <Coins size={16} className="text-amber-400" />;
      case 'financial_card':
        return <CreditCard size={16} className="text-cyan-400" />;
      case 'secrets_credentials':
        return <Key size={16} className="text-rose-400" />;
      case 'suspicious_url':
        return <Globe size={16} className="text-purple-400" />;
      case 'investigation_keyword':
        return <Search size={16} className="text-yellow-400" />;
      default:
        return <ShieldAlert size={16} className="text-orange-400" />;
    }
  };

  const filteredFindings = activeCategory === 'all'
    ? findings
    : findings.filter((f) => f.category === activeCategory);

  const categories = [
    { id: 'all', label: `All (${findings.length})` },
    { id: 'cryptocurrency', label: `Crypto Wallets (${findings.filter((f) => f.category === 'cryptocurrency').length})` },
    { id: 'financial_card', label: `Payment Cards (${findings.filter((f) => f.category === 'financial_card').length})` },
    { id: 'secrets_credentials', label: `Credentials & Secrets (${findings.filter((f) => f.category === 'secrets_credentials').length})` },
    { id: 'suspicious_permission', label: `Permissions (${findings.filter((f) => f.category === 'suspicious_permission' || f.category === 'spyware_heuristic').length})` },
    { id: 'suspicious_url', label: `Darkweb & C2 (${findings.filter((f) => f.category === 'suspicious_url').length})` },
    { id: 'investigation_keyword', label: `Keywords (${findings.filter((f) => f.category === 'investigation_keyword').length})` },
  ];

  return (
    <div className="flex-1 h-full min-h-0 overflow-y-auto p-4 bg-[#0c0f14] space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between pb-3 border-b border-[#1c2738] gap-3">
        <div>
          <div className="flex items-center space-x-2">
            <ShieldAlert size={20} className="text-amber-400" />
            <h2 className="text-lg font-bold text-slate-100 tracking-wide">
              Automated Forensic Triage & Deep IOC Scanner
            </h2>
          </div>
          <p className="text-xs text-slate-400">
            Offline pattern recognition scanning for Cryptocurrency Wallets, Luhn-verified Cards, Credentials, Darkweb URLs, and Spyware Permissions.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={fetchFindings}
            disabled={isLoading || isScanning}
            className="px-3 py-1.5 rounded text-xs font-semibold bg-[#16202e] border border-[#24344a] text-slate-300 hover:border-slate-500 transition-colors flex items-center space-x-1.5"
          >
            <RefreshCw size={13} className={isLoading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>

          <button
            onClick={handleRunDeepScan}
            disabled={isScanning}
            className="px-3.5 py-1.5 rounded text-xs font-bold bg-amber-600 hover:bg-amber-500 text-white shadow-lg shadow-amber-900/40 transition-all flex items-center space-x-1.5"
          >
            <Search size={14} className={isScanning ? 'animate-spin' : ''} />
            <span>{isScanning ? 'Scanning Artefacts...' : 'Run Deep IOC & Keyword Scan'}</span>
          </button>
        </div>
      </div>

      {/* Category Pills */}
      <div className="flex flex-wrap gap-1.5 pb-1">
        {categories.map((c) => (
          <button
            key={c.id}
            onClick={() => setActiveCategory(c.id)}
            className={`px-3 py-1 rounded-md text-xs font-semibold transition-colors ${
              activeCategory === c.id
                ? 'bg-amber-500 text-slate-950 font-bold'
                : 'bg-[#121824] text-slate-400 hover:text-slate-200 border border-[#1e2a3c]'
            }`}
          >
            {c.label}
          </button>
        ))}
      </div>

      {/* Findings List */}
      <div className="space-y-2.5">
        {isLoading ? (
          <div className="text-center py-16 text-slate-500 font-mono text-xs">Scanning evidence items...</div>
        ) : filteredFindings.length > 0 ? (
          filteredFindings.map((f) => {
            const copyTarget = f.details?.address || f.details?.card_masked || f.details?.marker || f.details?.matched;
            return (
              <div
                key={f.id}
                className="bg-[#111622] border border-[#1e2a3c] hover:border-amber-500/40 rounded-lg p-3.5 transition-all text-xs flex items-start space-x-3.5"
              >
                <div className="p-2 rounded bg-[#0b0e14] border border-[#1d2737] flex-shrink-0 mt-0.5">
                  {getCategoryIcon(f.category)}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center space-x-2">
                      <span className="font-semibold text-slate-100 text-sm font-sans">{f.title}</span>
                      <span className="text-[10px] text-slate-500 font-mono">[{f.rule_id}]</span>
                    </div>
                    {getSeverityBadge(f.severity)}
                  </div>

                  <p className="text-slate-300 font-sans text-xs mb-2 select-text">{f.description}</p>

                  {/* Context / Extracted Content */}
                  {f.details?.context && (
                    <div className="text-xs bg-[#090d14] p-2 rounded border border-[#182333] text-slate-300 font-mono mb-2 select-text">
                      <span className="text-[10px] text-slate-500 block mb-0.5 font-sans uppercase font-bold">Matched Snippet:</span>
                      "{f.details.context}"
                    </div>
                  )}

                  <div className="text-[11px] font-mono text-slate-500 flex flex-wrap items-center justify-between gap-2 bg-[#090d13] p-1.5 rounded border border-[#16202e]">
                    <div className="flex items-center space-x-3">
                      <span>Source: <code className="text-cyan-400">{f.target_file}</code></span>
                      <span>Category: <strong className="text-slate-300">{f.category}</strong></span>
                    </div>

                    {copyTarget && (
                      <button
                        onClick={() => handleCopy(copyTarget, f.id)}
                        className="px-2 py-0.5 rounded text-[10px] bg-[#1a2536] hover:bg-[#253652] text-slate-300 flex items-center space-x-1 border border-[#2b3a50] transition-colors"
                      >
                        {copiedId === f.id ? <Check size={10} className="text-emerald-400" /> : <Copy size={10} />}
                        <span>{copiedId === f.id ? 'Copied' : 'Copy IOC'}</span>
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        ) : (
          <div className="text-center py-16 text-slate-500 text-xs">
            No indicators matching category "{activeCategory}". Click "Run Deep IOC & Keyword Scan" to scan ingested artefacts.
          </div>
        )}
      </div>
    </div>
  );
};
