import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Artifact } from '../types';
import { Search, Eye, Filter, Code, CheckCircle, AlertCircle } from 'lucide-react';

interface ArtifactsPageProps {
  caseId: string;
  initialCategory?: string;
  initialSearchFocus?: boolean;
}

export const ArtifactsPage: React.FC<ArtifactsPageProps> = ({
  caseId,
  initialCategory = 'all',
  initialSearchFocus = false,
}) => {
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [category, setCategory] = useState<string>(initialCategory);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [inspectArtifact, setInspectArtifact] = useState<Artifact | null>(null);
  const searchInputRef = React.useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (initialCategory) {
      setCategory(initialCategory);
    }
  }, [initialCategory]);

  useEffect(() => {
    if (initialSearchFocus && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [initialSearchFocus]);

  const categories = [
    { id: 'all', label: 'All Categories' },
    { id: 'contacts', label: 'Contacts' },
    { id: 'messages', label: 'Messages & SMS' },
    { id: 'calls', label: 'Call Logs' },
    { id: 'browser', label: 'Browser History' },
    { id: 'installed_apps', label: 'Installed Apps' },
  ];

  const fetchArtifacts = () => {
    if (!caseId) return;
    setIsLoading(true);
    api.listArtifacts(caseId, category === 'all' ? undefined : category, searchQuery)
      .then(setArtifacts)
      .catch(console.error)
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    fetchArtifacts();
  }, [caseId, category]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchArtifacts();
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-[#0c0f14] overflow-hidden select-none">
      {/* Category Tabs & Search Bar */}
      <div className="p-3 bg-[#10151f] border-b border-[#1c2738] flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center space-x-1 overflow-x-auto">
          {categories.map((c) => (
            <button
              key={c.id}
              onClick={() => setCategory(c.id)}
              className={`px-3 py-1.5 rounded text-xs font-semibold tracking-wide transition-colors ${
                category === c.id
                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-[#161f2e]'
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>

        <form onSubmit={handleSearch} className="flex items-center space-x-2">
          <div className="relative">
            <Search size={14} className="absolute left-2.5 top-2.5 text-slate-500" />
            <input
              ref={searchInputRef}
              type="text"
              placeholder="Search normalized data..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 pr-3 py-1 bg-[#16202e] border border-[#233347] rounded text-xs text-slate-200 focus:outline-none focus:border-cyan-500 w-64"
            />
          </div>
          <button
            type="submit"
            className="px-3 py-1 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-semibold rounded text-xs transition-colors"
          >
            Filter
          </button>
        </form>
      </div>

      {/* Artifacts Table */}
      <div className="flex-1 overflow-y-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-[#121824] text-slate-400 uppercase font-semibold text-[11px] border-b border-[#1c2738] sticky top-0 z-10">
              <th className="py-2.5 px-3">Timestamp (UTC)</th>
              <th className="py-2.5 px-3">Category</th>
              <th className="py-2.5 px-3">Normalized Finding / Detail</th>
              <th className="py-2.5 px-3">Source File</th>
              <th className="py-2.5 px-3">Status</th>
              <th className="py-2.5 px-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#17212f]">
            {isLoading ? (
              <tr>
                <td colSpan={6} className="py-12 text-center text-slate-500 font-mono">
                  Querying database artifacts...
                </td>
              </tr>
            ) : artifacts.length > 0 ? (
              artifacts.map((art) => {
                const norm = art.normalized_data || {};
                const summary =
                  norm.contact_name ||
                  norm.phone_number ||
                  norm.message_body ||
                  norm.message_text ||
                  norm.page_title ||
                  norm.url ||
                  norm.device_name ||
                  'Normalized record';

                return (
                  <tr key={art.id} className="hover:bg-cyan-500/5 transition-colors font-mono">
                    <td className="py-2 px-3 text-slate-400 whitespace-nowrap">
                      {art.timestamp_utc ? new Date(art.timestamp_utc).toLocaleString() : 'N/A'}
                    </td>
                    <td className="py-2 px-3">
                      <span className="px-2 py-0.5 rounded bg-[#172333] border border-[#23354d] text-cyan-400 text-[10px] font-sans uppercase font-semibold">
                        {art.category}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-slate-200 max-w-md truncate font-sans">
                      <strong className="text-cyan-300 font-mono mr-1">
                        {norm.sender_or_recipient ? `[${norm.sender_or_recipient}]` : ''}
                      </strong>
                      {summary}
                    </td>
                    <td className="py-2 px-3 text-slate-400">
                      <code>{art.source_file}</code>
                      {art.source_table && <span className="text-slate-600 ml-1">({art.source_table})</span>}
                    </td>
                    <td className="py-2 px-3">
                      <span className="text-[10px] text-emerald-400 bg-emerald-950/40 border border-emerald-800/40 px-1.5 py-0.5 rounded uppercase font-semibold">
                        {art.recovery_status}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-right">
                      <button
                        onClick={() => setInspectArtifact(art)}
                        className="px-2 py-1 rounded bg-[#162232] border border-[#26374e] text-slate-300 hover:text-cyan-300 hover:border-cyan-500/50 transition-colors inline-flex items-center space-x-1"
                      >
                        <Eye size={12} />
                        <span>Inspect</span>
                      </button>
                    </td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan={6} className="py-12 text-center text-slate-500">
                  No artifacts match current filter criteria.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Raw JSON Modal */}
      {inspectArtifact && (
        <div className="fixed inset-0 bg-black/75 flex items-center justify-center p-4 z-50">
          <div className="bg-[#121824] border border-[#223147] rounded-lg w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl">
            <div className="p-3 border-b border-[#223147] flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Code size={16} className="text-cyan-400" />
                <span className="font-semibold text-sm text-slate-100">
                  Artefact Inspector: {inspectArtifact.category}
                </span>
              </div>
              <button
                onClick={() => setInspectArtifact(null)}
                className="text-slate-400 hover:text-slate-200 text-lg font-bold"
              >
                &times;
              </button>
            </div>
            <div className="p-4 overflow-y-auto space-y-3 text-xs font-mono select-text">
              <div>
                <span className="text-slate-500 block mb-1">NORMALIZED FORENSIC VALUES:</span>
                <pre className="p-2.5 rounded bg-[#090d13] border border-[#1a2536] text-cyan-300 overflow-x-auto">
                  {JSON.stringify(inspectArtifact.normalized_data, null, 2)}
                </pre>
              </div>
              <div>
                <span className="text-slate-500 block mb-1">RAW SOURCE VALUES (PRESERVED):</span>
                <pre className="p-2.5 rounded bg-[#090d13] border border-[#1a2536] text-slate-300 overflow-x-auto">
                  {JSON.stringify(inspectArtifact.raw_data, null, 2)}
                </pre>
              </div>
              <div className="text-[11px] text-slate-400 border-t border-[#1c2738] pt-2">
                Parser: {inspectArtifact.parser_id} v{inspectArtifact.parser_version} | Confidence: {inspectArtifact.confidence * 100}%
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
