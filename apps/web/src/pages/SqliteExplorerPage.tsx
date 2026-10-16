import React, { useState, useEffect, useMemo } from 'react';
import { api } from '../api/client';
import {
  Database,
  Play,
  Table,
  Info,
  AlertTriangle,
  Clock,
  Sparkles,
  Code,
  Binary,
  Copy,
  Check,
  Search,
  X,
  Download,
  Image as ImageIcon,
  Layers,
  Eye,
  FileCode,
  FileText,
} from 'lucide-react';

interface SqliteExplorerPageProps {
  caseId: string;
}

import {
  DecodedValue,
  formatBytes,
  getRelativeTime,
  generateHexDump,
  decodeCell,
} from '../utils/forensicFormatter';


export const SqliteExplorerPage: React.FC<SqliteExplorerPageProps> = ({ caseId }) => {
  const [databases, setDatabases] = useState<any[]>([]);
  const [selectedDb, setSelectedDb] = useState<string>('');
  const [schemaData, setSchemaData] = useState<any>(null);
  const [selectedTable, setSelectedTable] = useState<string>('');
  const [query, setQuery] = useState<string>('SELECT * FROM raw_contacts LIMIT 25;');
  const [queryResult, setQueryResult] = useState<any>(null);
  const [queryError, setQueryError] = useState<string>('');
  const [isExecuting, setIsExecuting] = useState(false);

  // Human-Readable Format & Tooling states
  const [isHumanReadable, setIsHumanReadable] = useState<boolean>(true);
  const [tableSearchFilter, setTableSearchFilter] = useState<string>('');
  const [inspectCell, setInspectCell] = useState<{ col: string; rowIdx: number; decoded: DecodedValue } | null>(null);
  const [activeInspectorTab, setActiveInspectorTab] = useState<'decoded' | 'hex' | 'raw'>('decoded');
  const [copiedKey, setCopiedKey] = useState<string>('');

  // Freelist unallocated space state
  const [activeView, setActiveView] = useState<'table' | 'freelist'>('table');
  const [freelistStrings, setFreelistStrings] = useState<any[]>([]);
  const [isLoadingFreelist, setIsLoadingFreelist] = useState<boolean>(false);

  useEffect(() => {
    if (!caseId) return;
    api.listSqliteDatabases(caseId)
      .then((dbs) => {
        setDatabases(dbs);
        if (dbs.length > 0) {
          setSelectedDb(dbs[0].relative_path);
        }
      })
      .catch(console.error);
  }, [caseId]);

  useEffect(() => {
    if (caseId && selectedDb) {
      api.getSqliteSchema(caseId, selectedDb)
        .then((data) => {
          setSchemaData(data);
          if (data.schema && data.schema.length > 0) {
            const firstTbl = data.schema[0].name;
            setSelectedTable(firstTbl);
            setQuery(`SELECT * FROM '${firstTbl}' LIMIT 25;`);
          }
        })
        .catch(console.error);
    }
  }, [caseId, selectedDb]);

  const handleRunQuery = async () => {
    if (!caseId || !selectedDb || !query.trim()) return;
    setIsExecuting(true);
    setQueryError('');
    try {
      const res = await api.executeSqliteQuery(caseId, selectedDb, query, 100);
      setQueryResult(res);
    } catch (e: any) {
      setQueryError(e.message || 'Error executing query');
      setQueryResult(null);
    } finally {
      setIsExecuting(false);
    }
  };

  const handleLoadFreelist = async () => {
    if (!caseId || !selectedDb) return;
    setIsLoadingFreelist(true);
    try {
      const res = await api.getSqliteFreelist(caseId, selectedDb);
      setFreelistStrings(res.carved_strings || []);
      setActiveView('freelist');
    } catch (err) {
      console.error('Freelist carving error:', err);
    } finally {
      setIsLoadingFreelist(false);
    }
  };

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(''), 2000);
  };

  const filteredRows = useMemo(() => {
    if (!queryResult?.rows) return [];
    if (!tableSearchFilter.trim()) return queryResult.rows;
    const q = tableSearchFilter.trim().toLowerCase();
    return queryResult.rows.filter((row: any) => {
      return Object.entries(row).some(([col, val]) => {
        const decoded = decodeCell(val, col);
        return (
          String(val).toLowerCase().includes(q) ||
          decoded.display.toLowerCase().includes(q) ||
          (decoded.details?.utcDate && decoded.details.utcDate.toLowerCase().includes(q))
        );
      });
    });
  }, [queryResult, tableSearchFilter]);

  const handleExportCsv = () => {
    if (!queryResult || !queryResult.columns || filteredRows.length === 0) return;
    const cols = queryResult.columns;
    const headerRow = cols.join(',');
    const dataRows = filteredRows.map((row: any) => {
      return cols
        .map((c: string) => {
          const val = row[c];
          const text = isHumanReadable ? decodeCell(val, c).display : String(val ?? '');
          return `"${text.replace(/"/g, '""')}"`;
        })
        .join(',');
    });
    const csvContent = [headerRow, ...dataRows].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedTable || 'sqlite_query'}_export.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-[#0c0f14] overflow-hidden select-none">
      {/* Top Database Selector & Header Metrics */}
      <div className="p-3 bg-[#10151f] border-b border-[#1c2738] flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
        <div className="flex items-center space-x-2">
          <Database size={15} className="text-cyan-400" />
          <span className="font-sans font-semibold text-slate-300">Database:</span>
          <select
            value={selectedDb}
            onChange={(e) => setSelectedDb(e.target.value)}
            className="bg-[#172232] border border-[#24344a] rounded-md px-3 py-1.5 text-slate-200 text-xs font-mono min-w-[280px] sm:min-w-[340px] max-w-lg truncate focus:outline-none focus:border-cyan-500 cursor-pointer shadow-sm hover:border-[#354964]"
          >
            {databases.length === 0 ? (
              <option value="" disabled>-- No databases detected in evidence --</option>
            ) : (
              databases.map((db, i) => (
                <option key={i} value={db.relative_path}>
                  🗄️ {db.name} ({(db.file_size / 1024).toFixed(1)} KB)
                </option>
              ))
            )}
          </select>
        </div>

        {schemaData?.header && (
          <div className="flex items-center space-x-3 text-[11px] text-slate-400">
            <span>
              Page Size: <strong className="text-slate-200">{schemaData.header.page_size}B</strong>
            </span>
            <span>
              Pages: <strong className="text-slate-200">{schemaData.header.total_pages}</strong>
            </span>
            <button
              onClick={handleLoadFreelist}
              disabled={isLoadingFreelist}
              className={`px-2 py-0.5 rounded flex items-center space-x-1 transition-colors ${
                schemaData.header.freelist_pages > 0
                  ? 'bg-amber-950/40 border border-amber-800/50 text-amber-300 hover:bg-amber-900/50'
                  : 'bg-[#151e2c] border border-[#202e42] text-slate-400'
              }`}
              title="Carve deleted strings from database unallocated freelist space"
            >
              <span>Freelist:</span>
              <strong className={schemaData.header.freelist_pages > 0 ? 'text-amber-400' : 'text-slate-300'}>
                {schemaData.header.freelist_pages} pgs
              </strong>
              {isLoadingFreelist ? <span className="animate-spin text-xs">🌀</span> : <Layers size={11} />}
            </button>
            <span>
              WAL:{' '}
              <strong className={schemaData.header.wal_present ? 'text-emerald-400' : 'text-slate-500'}>
                {schemaData.header.wal_present ? 'PRESENT' : 'NONE'}
              </strong>
            </span>
          </div>
        )}
      </div>

      {/* Main Split: Tables list (left), Query & Table View (right) */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Tables & Columns */}
        <div className="w-64 bg-[#0e131d] border-r border-[#1c2738] flex flex-col flex-shrink-0">
          <div className="p-2 border-b border-[#1c2738] text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center justify-between">
            <span>Tables ({schemaData?.schema?.length || 0})</span>
            {schemaData?.header?.freelist_pages > 0 && (
              <span className="text-amber-400 font-mono text-[9px] bg-amber-950/60 px-1 rounded">
                DELETED DATA PRESENT
              </span>
            )}
          </div>
          <div className="flex-1 overflow-y-auto p-1.5 space-y-1 text-xs font-mono">
            {schemaData?.schema?.map((t: any, i: number) => (
              <button
                key={i}
                onClick={() => {
                  setSelectedTable(t.name);
                  setActiveView('table');
                  setQuery(`SELECT * FROM '${t.name}' LIMIT 50;`);
                }}
                className={`w-full text-left px-2 py-1.5 rounded flex items-center justify-between transition-colors ${
                  selectedTable === t.name && activeView === 'table'
                    ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-[#141d2a]'
                }`}
              >
                <div className="flex items-center space-x-1.5 truncate">
                  <Table size={12} className="text-cyan-500 flex-shrink-0" />
                  <span className="truncate">{t.name}</span>
                </div>
                <span className="text-[10px] text-slate-600 ml-1 font-semibold">{t.row_count}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Right: Main View Area */}
        <div className="flex-1 flex flex-col bg-[#0b0e14] min-w-0 overflow-hidden">
          {/* Query Bar */}
          <div className="p-3 bg-[#111722] border-b border-[#1c2738] flex items-center space-x-2 flex-shrink-0">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter read-only SQL query (SELECT ...)"
              className="flex-1 bg-[#16202e] border border-[#233347] rounded px-3 py-1.5 text-xs font-mono text-cyan-300 focus:outline-none focus:border-cyan-500"
            />
            <button
              onClick={handleRunQuery}
              disabled={isExecuting}
              className="px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold text-xs rounded transition-colors flex items-center space-x-1 shadow-sm"
            >
              <Play size={12} />
              <span>Execute</span>
            </button>
          </div>

          {/* View Toolbar: Human-Readable Toggle, In-Table Search, View Switch, Export */}
          <div className="px-3 py-2 bg-[#0e131d] border-b border-[#1c2738] flex flex-wrap items-center justify-between gap-2 text-xs font-mono select-none flex-shrink-0">
            <div className="flex items-center space-x-2">
              {/* Human-Readable Mode Switch */}
              <button
                onClick={() => setIsHumanReadable(!isHumanReadable)}
                className={`px-2.5 py-1 rounded text-xs font-semibold flex items-center space-x-1.5 transition-all shadow-sm ${
                  isHumanReadable
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/50 shadow-cyan-950/40'
                    : 'bg-[#151e2c] text-slate-400 border border-[#223145] hover:text-slate-200'
                }`}
                title="Automatically decodes timestamps (UTC), JSON strings, BLOB images, base64, and cleans garbage control bytes"
              >
                <Sparkles size={13} className={isHumanReadable ? 'text-cyan-400' : 'text-slate-500'} />
                <span>Human-Readable Format:</span>
                <strong className={isHumanReadable ? 'text-cyan-300 font-bold' : 'text-slate-400'}>
                  {isHumanReadable ? 'ON' : 'RAW'}
                </strong>
              </button>

              {/* View Tabs */}
              <div className="flex items-center bg-[#141b27] border border-[#202d3e] rounded p-0.5 ml-2">
                <button
                  onClick={() => setActiveView('table')}
                  className={`px-2.5 py-0.5 rounded text-[11px] font-semibold transition-colors ${
                    activeView === 'table' ? 'bg-[#1d2737] text-cyan-300' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Table Data {queryResult ? `(${filteredRows.length})` : ''}
                </button>
                <button
                  onClick={handleLoadFreelist}
                  className={`px-2.5 py-0.5 rounded text-[11px] font-semibold transition-colors flex items-center space-x-1 ${
                    activeView === 'freelist' ? 'bg-[#1d2737] text-amber-300' : 'text-slate-400 hover:text-amber-300'
                  }`}
                >
                  <Layers size={11} />
                  <span>Carved Freelist {freelistStrings.length > 0 ? `(${freelistStrings.length})` : ''}</span>
                </button>
              </div>
            </div>

            {/* In-table search filter and export */}
            {activeView === 'table' && queryResult && (
              <div className="flex items-center space-x-2">
                <div className="relative flex items-center">
                  <Search size={12} className="absolute left-2.5 text-slate-500 pointer-events-none" />
                  <input
                    type="text"
                    value={tableSearchFilter}
                    onChange={(e) => setTableSearchFilter(e.target.value)}
                    placeholder="Filter results..."
                    className="w-44 bg-[#141b27] border border-[#202d3e] rounded pl-7 pr-6 py-0.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                  />
                  {tableSearchFilter && (
                    <button
                      onClick={() => setTableSearchFilter('')}
                      className="absolute right-1.5 text-slate-400 hover:text-slate-200"
                    >
                      <X size={12} />
                    </button>
                  )}
                </div>

                <button
                  onClick={handleExportCsv}
                  className="px-2 py-1 rounded bg-[#16202f] border border-[#223145] text-slate-300 hover:text-cyan-300 hover:border-cyan-500/50 transition-colors flex items-center space-x-1"
                  title="Export current rows to CSV"
                >
                  <Download size={12} />
                  <span>Export CSV</span>
                </button>
              </div>
            )}
          </div>

          {/* Error display */}
          {queryError && (
            <div className="p-2.5 bg-rose-950/40 border-b border-rose-800/40 text-rose-300 text-xs font-mono flex items-center space-x-2">
              <AlertTriangle size={14} className="flex-shrink-0" />
              <span>{queryError}</span>
            </div>
          )}

          {/* Results Grid / Table View */}
          {activeView === 'table' ? (
            <div className="flex-1 overflow-auto p-2">
              {queryResult ? (
                <table className="w-full text-left text-xs font-mono border-collapse select-text">
                  <thead>
                    <tr className="bg-[#141b27] text-slate-400 uppercase text-[10px] sticky top-0 border-b border-[#1c2738] z-10">
                      <th className="py-2 px-2 text-slate-600 w-8 text-center">#</th>
                      {queryResult.columns.map((col: string, i: number) => (
                        <th key={i} className="py-2 px-2.5 whitespace-nowrap">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#17212f]">
                    {filteredRows.map((row: any, rIdx: number) => (
                      <tr key={rIdx} className="hover:bg-cyan-500/5 transition-colors group">
                        <td className="py-1.5 px-2 text-[10px] text-slate-600 font-mono text-center select-none">
                          {rIdx + 1}
                        </td>
                        {queryResult.columns.map((col: string, cIdx: number) => {
                          const rawVal = row[col];
                          const decoded = decodeCell(rawVal, col);

                          return (
                            <td
                              key={cIdx}
                              onClick={() => setInspectCell({ col, rowIdx: rIdx, decoded })}
                              className="py-1.5 px-2.5 text-slate-200 whitespace-nowrap max-w-sm truncate cursor-pointer hover:bg-cyan-500/10 hover:text-cyan-200 transition-colors relative"
                              title="Click cell to inspect full forensic decoding, hex dump, and raw database value"
                            >
                              {rawVal === null || rawVal === undefined ? (
                                <span className="text-slate-600 italic">null</span>
                              ) : isHumanReadable ? (
                                decoded.type === 'timestamp' ? (
                                  <span className="inline-flex items-center space-x-1.5 text-cyan-300">
                                    <Clock size={11} className="text-cyan-400 flex-shrink-0" />
                                    <span>{decoded.display}</span>
                                    <span className="text-slate-500 text-[10px] font-mono">
                                      ({String(decoded.rawValue).slice(-6)})
                                    </span>
                                  </span>
                                ) : decoded.type === 'json' ? (
                                  <span className="inline-flex items-center space-x-1 text-amber-300 bg-amber-950/40 px-1.5 py-0.5 rounded border border-amber-800/40 text-[10px]">
                                    <Code size={11} className="text-amber-400" />
                                    <span>{decoded.display}</span>
                                  </span>
                                ) : decoded.type === 'blob' ? (
                                  <span
                                    className={`inline-flex items-center space-x-1 px-1.5 py-0.5 rounded border text-[10px] font-sans font-semibold ${decoded.badgeColor}`}
                                  >
                                    {decoded.details?.isImage ? <ImageIcon size={11} /> : <Binary size={11} />}
                                    <span>{decoded.display}</span>
                                  </span>
                                ) : decoded.type === 'hex_text' || decoded.type === 'base64_text' ? (
                                  <span className="inline-flex items-center space-x-1">
                                    <span className="text-pink-300 font-sans">{decoded.display}</span>
                                    <span
                                      className={`text-[9px] px-1 py-0.2 rounded font-sans uppercase font-bold border ${decoded.badgeColor}`}
                                    >
                                      {decoded.badge}
                                    </span>
                                  </span>
                                ) : decoded.type === 'boolean' ? (
                                  <span
                                    className={`px-1.5 py-0.5 rounded text-[10px] font-semibold border ${decoded.badgeColor}`}
                                  >
                                    {decoded.display}
                                  </span>
                                ) : (
                                  <span>{decoded.display}</span>
                                )
                              ) : (
                                <span className="text-slate-400 font-mono">
                                  {typeof rawVal === 'object' ? JSON.stringify(rawVal) : String(rawVal)}
                                </span>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="text-center py-20 text-slate-500 font-mono text-xs">
                  Select a table or click Execute to run read-only forensic inspection.
                </div>
              )}
            </div>
          ) : (
            /* Freelist Carved Strings View */
            <div className="flex-1 overflow-auto p-3">
              <div className="mb-3 flex items-center justify-between">
                <div>
                  <h3 className="text-xs font-semibold text-amber-300 font-sans flex items-center space-x-1.5">
                    <Layers size={13} />
                    <span>Carved Strings from Freelist & Unallocated Database Space</span>
                  </h3>
                  <p className="text-[11px] text-slate-400">
                    Recovered text fragments preserved in unallocated pages of{' '}
                    <code className="text-cyan-400">{selectedDb}</code>. These often correspond to deleted records.
                  </p>
                </div>
                <span className="text-xs font-mono text-slate-400">
                  Total Recovered: <strong className="text-amber-400">{freelistStrings.length}</strong>
                </span>
              </div>

              {freelistStrings.length > 0 ? (
                <div className="border border-[#1e2b3d] rounded bg-[#0d121c] overflow-hidden">
                  <table className="w-full text-left text-xs font-mono select-text">
                    <thead>
                      <tr className="bg-[#141b27] text-slate-400 uppercase text-[10px] border-b border-[#1c2738]">
                        <th className="py-2 px-3 w-28">Byte Offset</th>
                        <th className="py-2 px-3 w-20">Length</th>
                        <th className="py-2 px-3">Recovered Text String</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#17212f]">
                      {freelistStrings.map((item, idx) => (
                        <tr key={idx} className="hover:bg-amber-500/5">
                          <td className="py-1.5 px-3 text-cyan-400 font-mono">
                            0x{item.offset.toString(16).toUpperCase().padStart(8, '0')}
                          </td>
                          <td className="py-1.5 px-3 text-slate-500">{item.length}B</td>
                          <td className="py-1.5 px-3 text-slate-200 select-text whitespace-pre-wrap font-sans">
                            {item.text}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-20 text-slate-500 font-mono text-xs">
                  {isLoadingFreelist
                    ? 'Scanning unallocated space...'
                    : 'No deleted text strings found in unallocated space.'}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Forensic Value Inspector Modal */}
      {inspectCell && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50">
          <div className="bg-[#111723] border border-[#24354c] rounded-lg w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="p-3 bg-[#141b28] border-b border-[#202f43] flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Sparkles size={16} className="text-cyan-400" />
                <span className="font-semibold text-sm text-slate-100 font-sans">
                  Forensic Value Inspector: <code className="text-cyan-300 font-mono">{inspectCell.col}</code>
                </span>
                <span className="text-[10px] text-slate-500 font-mono">Row #{inspectCell.rowIdx + 1}</span>
                {inspectCell.decoded.badge && (
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded font-sans uppercase font-bold border ${inspectCell.decoded.badgeColor}`}
                  >
                    {inspectCell.decoded.badge}
                  </span>
                )}
              </div>
              <button
                onClick={() => setInspectCell(null)}
                className="text-slate-400 hover:text-slate-200 text-lg font-bold"
              >
                &times;
              </button>
            </div>

            {/* Inspector Tab Bar */}
            <div className="h-9 bg-[#0e1420] border-b border-[#1c293b] px-3 flex items-center justify-between text-xs font-mono">
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setActiveInspectorTab('decoded')}
                  className={`px-2.5 py-1 rounded text-xs font-semibold flex items-center space-x-1 transition-colors ${
                    activeInspectorTab === 'decoded'
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Sparkles size={12} />
                  <span>Decoded (Human-Readable)</span>
                </button>
                <button
                  onClick={() => setActiveInspectorTab('hex')}
                  className={`px-2.5 py-1 rounded text-xs font-semibold flex items-center space-x-1 transition-colors ${
                    activeInspectorTab === 'hex'
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Binary size={12} />
                  <span>Hex Dump</span>
                </button>
                <button
                  onClick={() => setActiveInspectorTab('raw')}
                  className={`px-2.5 py-1 rounded text-xs font-semibold flex items-center space-x-1 transition-colors ${
                    activeInspectorTab === 'raw'
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <FileCode size={12} />
                  <span>Raw Database Value</span>
                </button>
              </div>

              {/* Copy actions */}
              <div className="flex items-center space-x-2">
                <button
                  onClick={() =>
                    handleCopy(
                      inspectCell.decoded.details?.utcDate ||
                        inspectCell.decoded.details?.formattedJson ||
                        inspectCell.decoded.display,
                      'decoded'
                    )
                  }
                  className="px-2 py-0.5 rounded bg-[#162131] border border-[#25364c] text-[11px] text-slate-300 hover:text-cyan-300 transition-colors flex items-center space-x-1"
                >
                  {copiedKey === 'decoded' ? <Check size={11} className="text-emerald-400" /> : <Copy size={11} />}
                  <span>{copiedKey === 'decoded' ? 'Copied!' : 'Copy Decoded'}</span>
                </button>
                <button
                  onClick={() => handleCopy(String(inspectCell.decoded.rawValue ?? ''), 'raw')}
                  className="px-2 py-0.5 rounded bg-[#162131] border border-[#25364c] text-[11px] text-slate-300 hover:text-cyan-300 transition-colors flex items-center space-x-1"
                >
                  {copiedKey === 'raw' ? <Check size={11} className="text-emerald-400" /> : <Copy size={11} />}
                  <span>{copiedKey === 'raw' ? 'Copied!' : 'Copy Raw'}</span>
                </button>
              </div>
            </div>

            {/* Inspector Content */}
            <div className="p-4 overflow-y-auto space-y-3 text-xs font-mono select-text flex-1">
              {activeInspectorTab === 'decoded' ? (
                /* Decoded Tab */
                <div className="space-y-3">
                  {inspectCell.decoded.type === 'timestamp' && inspectCell.decoded.details && (
                    <div className="bg-[#0b0f16] border border-[#1b2637] rounded p-3 space-y-2">
                      <div className="text-cyan-400 font-semibold font-sans text-sm flex items-center space-x-2">
                        <Clock size={15} />
                        <span>{inspectCell.decoded.details.utcDate}</span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs pt-1 border-t border-[#182333]">
                        <div>
                          <span className="text-slate-500 block">Local Time:</span>
                          <span className="text-slate-200">{inspectCell.decoded.details.localDate}</span>
                        </div>
                        <div>
                          <span className="text-slate-500 block">Relative:</span>
                          <span className="text-emerald-400">{inspectCell.decoded.details.relativeTime}</span>
                        </div>
                        <div>
                          <span className="text-slate-500 block">ISO-8601:</span>
                          <span className="text-slate-300">{inspectCell.decoded.details.isoDate}</span>
                        </div>
                        <div>
                          <span className="text-slate-500 block">Detection Format:</span>
                          <span className="text-slate-300">{inspectCell.decoded.details.timestampFormat}</span>
                        </div>
                        <div className="col-span-2">
                          <span className="text-slate-500 block">Original Stored Epoch:</span>
                          <code className="text-amber-400">{String(inspectCell.decoded.details.epoch)}</code>
                        </div>
                      </div>
                    </div>
                  )}

                  {inspectCell.decoded.type === 'json' && inspectCell.decoded.details?.formattedJson && (
                    <div>
                      <span className="text-slate-400 block mb-1">FORMATTED JSON DATA:</span>
                      <pre className="p-3 rounded bg-[#090d14] border border-[#1b2738] text-amber-300 overflow-x-auto text-xs leading-relaxed max-h-96">
                        {inspectCell.decoded.details.formattedJson}
                      </pre>
                    </div>
                  )}

                  {inspectCell.decoded.type === 'blob' && (
                    <div className="space-y-3">
                      {inspectCell.decoded.details?.isImage && inspectCell.decoded.details.base64 ? (
                        <div className="bg-[#0b0f16] border border-[#1b2637] rounded p-3 text-center">
                          <span className="text-slate-400 block mb-2 text-left">IMAGE PREVIEW:</span>
                          <img
                            src={`data:${inspectCell.decoded.details.blobMime};base64,${inspectCell.decoded.details.base64}`}
                            alt="Decoded BLOB"
                            className="max-h-64 max-w-full mx-auto rounded border border-[#1f2d3f] shadow-lg object-contain"
                          />
                          <div className="mt-2 text-slate-400 text-[11px]">
                            {inspectCell.decoded.details.blobTag} ({formatBytes(inspectCell.decoded.details.blobSize || 0)})
                          </div>
                        </div>
                      ) : (
                        <div className="bg-[#0b0f16] border border-[#1b2637] rounded p-3">
                          <div className="flex items-center space-x-2 text-purple-300 font-semibold mb-2">
                            <Binary size={15} />
                            <span>
                              {inspectCell.decoded.details?.blobTag} ({formatBytes(inspectCell.decoded.details?.blobSize || 0)})
                            </span>
                          </div>
                          <span className="text-slate-500 block text-[11px]">
                            MIME: {inspectCell.decoded.details?.blobMime || 'application/octet-stream'}
                          </span>
                        </div>
                      )}

                      {inspectCell.decoded.details?.hexDump && (
                        <div>
                          <span className="text-slate-400 block mb-1">HEX STREAM PREVIEW:</span>
                          <pre className="p-2.5 rounded bg-[#090d14] border border-[#1b2738] text-cyan-300 overflow-x-auto text-[11px] leading-tight">
                            {inspectCell.decoded.details.hexDump}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}

                  {inspectCell.decoded.type === 'hex_text' && inspectCell.decoded.details && (
                    <div className="space-y-2">
                      <div>
                        <span className="text-slate-400 block mb-1">ASCII DECODED STRING:</span>
                        <div className="p-3 rounded bg-[#090d14] border border-[#1b2738] text-pink-300 text-sm font-sans select-text">
                          {inspectCell.decoded.details.decodedText}
                        </div>
                      </div>
                      {inspectCell.decoded.details.hexDump && (
                        <div>
                          <span className="text-slate-400 block mb-1">HEX DUMP:</span>
                          <pre className="p-2.5 rounded bg-[#090d14] border border-[#1b2738] text-cyan-300 overflow-x-auto text-[11px]">
                            {inspectCell.decoded.details.hexDump}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}

                  {inspectCell.decoded.type === 'base64_text' && inspectCell.decoded.details && (
                    <div className="space-y-2">
                      <div>
                        <span className="text-slate-400 block mb-1">BASE64 DECODED TEXT:</span>
                        <div className="p-3 rounded bg-[#090d14] border border-[#1b2738] text-indigo-300 text-sm font-sans select-text">
                          {inspectCell.decoded.details.decodedText}
                        </div>
                      </div>
                    </div>
                  )}

                  {['text', 'number', 'boolean', 'filesize', 'null'].includes(inspectCell.decoded.type) && (
                    <div className="bg-[#0b0f16] border border-[#1b2637] rounded p-3">
                      <span className="text-slate-500 block mb-1 uppercase text-[10px]">VALUE:</span>
                      <div className="text-slate-200 text-sm select-text whitespace-pre-wrap">
                        {inspectCell.decoded.display}
                      </div>
                    </div>
                  )}
                </div>
              ) : activeInspectorTab === 'hex' ? (
                /* Hex Tab */
                <div>
                  <span className="text-slate-400 block mb-1">HEXADECIMAL DUMP:</span>
                  <pre className="p-3 rounded bg-[#090d14] border border-[#1b2738] text-cyan-300 overflow-x-auto text-[11px] leading-tight select-text">
                    {inspectCell.decoded.details?.hexDump ||
                      generateHexDump(
                        typeof inspectCell.decoded.rawValue === 'string'
                          ? Array.from(inspectCell.decoded.rawValue)
                              .map((c: any) => c.charCodeAt(0).toString(16).padStart(2, '0'))
                              .join('')
                          : String(inspectCell.decoded.rawValue)
                      )}
                  </pre>
                </div>
              ) : (
                /* Raw Tab */
                <div>
                  <span className="text-slate-400 block mb-1">ORIGINAL DATABASE STORED VALUE:</span>
                  <pre className="p-3 rounded bg-[#090d14] border border-[#1b2738] text-slate-300 overflow-x-auto text-xs leading-relaxed select-text whitespace-pre-wrap">
                    {typeof inspectCell.decoded.rawValue === 'object'
                      ? JSON.stringify(inspectCell.decoded.rawValue, null, 2)
                      : String(inspectCell.decoded.rawValue ?? 'null')}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
