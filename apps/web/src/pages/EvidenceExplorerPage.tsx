import React, { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api/client';
import { Evidence } from '../types';
import {
  Folder,
  FolderOpen,
  FileCode,
  ShieldCheck,
  ShieldAlert,
  ChevronRight,
  ChevronDown,
  ChevronLeft,
  Binary,
  FileText,
  RefreshCw,
  FolderUp,
  GripVertical,
  Columns,
  Maximize2,
  Minimize2,
  Search,
  X,
  Database,
  Sparkles,
  Clock,
  Code,
  Image as ImageIcon,
  Copy,
  Check,
  Download,
  Table,
} from 'lucide-react';
import {
  DecodedValue,
  formatBytes,
  getRelativeTime,
  generateHexDump,
  decodeCell,
} from '../utils/forensicFormatter';


interface EvidenceExplorerPageProps {
  caseId: string;
  evidenceList: Evidence[];
  onRefreshEvidence: () => void;
}

function countFiles(node: any): number {
  if (typeof node.file_count === 'number') return node.file_count;
  if (!node.is_dir) return 1;
  if (!node.children || node.children.length === 0) return 0;
  return node.children.reduce((acc: number, child: any) => acc + countFiles(child), 0);
}

function getAllDirPaths(nodes: any[]): string[] {
  let paths: string[] = [];
  for (const n of nodes) {
    if (n.is_dir) {
      paths.push(n.path);
      if (n.children) {
        paths = paths.concat(getAllDirPaths(n.children));
      }
    }
  }
  return paths;
}

function filterTree(nodes: any[], query: string): { filtered: any[]; autoExpandPaths: Set<string>; matchCount: number } {
  const q = query.trim().toLowerCase();
  const autoExpandPaths = new Set<string>();
  let matchCount = 0;

  function filterNode(node: any): any | null {
    if (!node.is_dir) {
      if (node.name.toLowerCase().includes(q)) {
        matchCount++;
        return node;
      }
      return null;
    }

    const filteredChildren: any[] = [];
    if (node.children) {
      for (const child of node.children) {
        const res = filterNode(child);
        if (res) filteredChildren.push(res);
      }
    }

    const nameMatches = node.name.toLowerCase().includes(q);
    if (nameMatches) matchCount++;

    if (nameMatches || filteredChildren.length > 0) {
      autoExpandPaths.add(node.path);
      return {
        ...node,
        children: filteredChildren.length > 0 ? filteredChildren : node.children,
      };
    }

    return null;
  }

  const filtered = nodes.map(filterNode).filter(Boolean);
  return { filtered, autoExpandPaths, matchCount };
}

export const EvidenceExplorerPage: React.FC<EvidenceExplorerPageProps> = ({
  caseId,
  evidenceList,
  onRefreshEvidence,
}) => {
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string>(evidenceList[0]?.id || '');
  const [fileTree, setFileTree] = useState<any[]>([]);
  const [selectedFile, setSelectedFile] = useState<string>('');
  const [previewTab, setPreviewTab] = useState<'database' | 'image' | 'hex' | 'text'>('hex');
  const [previewData, setPreviewData] = useState<any>(null);
  const [offset, setOffset] = useState<number>(0);
  const [cleanStringsOnly, setCleanStringsOnly] = useState<boolean>(true);
  const [isLoadingTree, setIsLoadingTree] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [treeSearchQuery, setTreeSearchQuery] = useState<string>('');
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());

  // Database Inspector states
  const [selectedDbTable, setSelectedDbTable] = useState<string>('');
  const [dbTableRows, setDbTableRows] = useState<any[]>([]);
  const [dbTableColumns, setDbTableColumns] = useState<string[]>([]);
  const [isDbLoading, setIsDbLoading] = useState<boolean>(false);
  const [isDbHumanReadable, setIsDbHumanReadable] = useState<boolean>(true);
  const [dbSearchFilter, setDbSearchFilter] = useState<string>('');
  const [inspectCell, setInspectCell] = useState<{ col: string; rowIdx: number; decoded: DecodedValue } | null>(null);
  const [activeInspectorTab, setActiveInspectorTab] = useState<'decoded' | 'hex' | 'raw'>('decoded');
  const [copiedKey, setCopiedKey] = useState<string>('');

  // Panel Adjustment & Sliding states
  const [treeWidth, setTreeWidth] = useState<number>(() => {
    try {
      const saved = localStorage.getItem('mmf_tree_width');
      return saved ? Math.max(240, Math.min(parseInt(saved, 10), 900)) : 420;
    } catch {
      return 420;
    }
  });
  const [isDragging, setIsDragging] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const treeContainerRef = useRef<HTMLDivElement>(null);

  // Draggable Splitter Mouse Handlers
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;
      // 64px is the left app sidebar width; constrain panel between 240px and 850px
      const newWidth = Math.max(240, Math.min(e.clientX - 64, 850));
      setTreeWidth(newWidth);
      try {
        localStorage.setItem('mmf_tree_width', String(newWidth));
      } catch {}
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    } else {
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isDragging]);

  useEffect(() => {
    if (evidenceList.length > 0 && !selectedEvidenceId) {
      setSelectedEvidenceId(evidenceList[0].id);
    }
  }, [evidenceList]);

  useEffect(() => {
    if (selectedEvidenceId && caseId) {
      setIsLoadingTree(true);
      setExpandedPaths(new Set());
      setTreeSearchQuery('');
      api.getEvidenceTree(caseId, selectedEvidenceId)
        .then((res) => {
          setFileTree(res.tree || []);
          if (res.tree && res.tree.length > 0) {
            const firstFile = findFirstFile(res.tree);
            if (firstFile) {
              setSelectedFile(firstFile);
            }
          }
        })
        .catch(console.error)
        .finally(() => setIsLoadingTree(false));
    }
  }, [selectedEvidenceId, caseId]);

  useEffect(() => {
    if (caseId && selectedEvidenceId && selectedFile) {
      api.getFilePreview(caseId, selectedEvidenceId, selectedFile, offset, 4096)
        .then(setPreviewData)
        .catch(console.error);
    }
  }, [caseId, selectedEvidenceId, selectedFile, offset]);

  useEffect(() => {
    if (!previewData) return;
    if (previewData.is_sqlite) {
      setPreviewTab('database');
      const firstTbl = previewData.sqlite_info?.selected_table || (previewData.sqlite_info?.tables?.[0]?.name ?? '');
      setSelectedDbTable(firstTbl);
      setDbTableRows(previewData.sqlite_info?.sample_data?.rows || []);
      setDbTableColumns(previewData.sqlite_info?.sample_data?.columns || []);
      setDbSearchFilter('');
    } else if (previewData.is_image) {
      setPreviewTab('image');
    } else {
      setPreviewTab((prev) => (prev === 'database' || prev === 'image' ? 'hex' : prev));
    }
  }, [previewData]);

  const handleSelectDbTable = async (tableName: string) => {
    if (!caseId || !selectedEvidenceId || !selectedFile) return;
    setSelectedDbTable(tableName);
    setIsDbLoading(true);
    try {
      const res = await api.queryEvidenceDb(caseId, selectedEvidenceId, selectedFile, tableName, 50, 0);
      setDbTableRows(res.rows || []);
      setDbTableColumns(res.columns || []);
    } catch (err) {
      console.error('Failed to query DB table:', err);
    } finally {
      setIsDbLoading(false);
    }
  };

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(''), 2000);
  };

  const filteredDbRows = React.useMemo(() => {
    if (!dbSearchFilter.trim()) return dbTableRows;
    const q = dbSearchFilter.toLowerCase();
    return dbTableRows.filter((row: any) =>
      Object.values(row).some((val) => {
        if (val === null || val === undefined) return false;
        if (typeof val === 'object') return JSON.stringify(val).toLowerCase().includes(q);
        return String(val).toLowerCase().includes(q);
      })
    );
  }, [dbTableRows, dbSearchFilter]);

  const handleExportDbCsv = () => {
    if (!dbTableRows.length || !dbTableColumns.length) return;
    const header = dbTableColumns.join(',');
    const rows = dbTableRows.map((r: any) =>
      dbTableColumns
        .map((col) => {
          const val = r[col];
          if (val === null || val === undefined) return '';
          const str = typeof val === 'object' ? JSON.stringify(val) : String(val);
          return `"${str.replace(/"/g, '""')}"`;
        })
        .join(',')
    );
    const csvContent = 'data:text/csv;charset=utf-8,' + encodeURIComponent([header, ...rows].join('\n'));
    const link = document.createElement('a');
    link.setAttribute('href', csvContent);
    link.setAttribute('download', `${selectedDbTable || 'table'}_export.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };


  function findFirstFile(nodes: any[]): string | null {
    for (const n of nodes) {
      if (!n.is_dir) return n.path;
      if (n.children) {
        const found = findFirstFile(n.children);
        if (found) return found;
      }
    }
    return null;
  }

  const handleToggleExpand = useCallback((path: string) => {
    setExpandedPaths((prev) => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  }, []);

  const handleExpandAll = useCallback(() => {
    setExpandedPaths(new Set(getAllDirPaths(fileTree)));
  }, [fileTree]);

  const handleCollapseAll = useCallback(() => {
    setExpandedPaths(new Set());
  }, []);

  const { filtered: displayedTree, autoExpandPaths, matchCount } = React.useMemo(() => {
    if (!treeSearchQuery.trim()) {
      return { filtered: fileTree, autoExpandPaths: new Set<string>(), matchCount: 0 };
    }
    return filterTree(fileTree, treeSearchQuery);
  }, [fileTree, treeSearchQuery]);

  const effectiveExpandedPaths = React.useMemo(() => {
    if (treeSearchQuery.trim()) {
      return new Set([...expandedPaths, ...autoExpandPaths]);
    }
    return expandedPaths;
  }, [expandedPaths, autoExpandPaths, treeSearchQuery]);

  const totalFilesCount = React.useMemo(() => {
    return fileTree.reduce((acc, node) => acc + countFiles(node), 0);
  }, [fileTree]);

  const selectedEvidence = evidenceList.find((e) => e.id === selectedEvidenceId);

  const handleVerify = async () => {
    if (!selectedEvidenceId || !caseId) return;
    setIsVerifying(true);
    try {
      await api.verifyEvidence(caseId, selectedEvidenceId);
      onRefreshEvidence();
    } catch (e) {
      console.error(e);
    } finally {
      setIsVerifying(false);
    }
  };

  const handleSelectEvidenceFile = async () => {
    if (!caseId) return;
    if (window.mantisDesktop?.showOpenDialog) {
      try {
        const res = await window.mantisDesktop.showOpenDialog({
          title: 'Select Mobile Forensic Evidence File or Directory',
          properties: ['openFile'],
          filters: [
            {
              name: 'Forensic Images & Archives',
              extensions: ['zip', 'tar', 'gz', 'bz2', '7z', 'db', 'sqlite', 'dd', 'raw', 'e01', 'ab', 'dmg', 'iso'],
            },
            { name: 'All Files', extensions: ['*'] },
          ],
        });
        if (!res.canceled && res.filePaths && res.filePaths[0]) {
          await api.importPath(caseId, res.filePaths[0], 'archive');
          onRefreshEvidence();
        }
      } catch (err) {
        console.error('File dialog error:', err);
      }
    }
  };

  const renderTree = (nodes: any[]) => {
    return (
      <ul className="min-w-max space-y-0.5 text-xs font-mono pr-6 pb-6 select-none">
        {nodes.map((node, i) => (
          <TreeNode
            key={node.path || i}
            node={node}
            selectedFile={selectedFile}
            expandedPaths={effectiveExpandedPaths}
            onToggleExpand={handleToggleExpand}
            onSelectFile={(path) => {
              setSelectedFile(path);
              setOffset(0);
            }}
          />
        ))}
      </ul>
    );
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-[#0c0f14] overflow-hidden select-none">
      {/* Top Evidence Selector Bar */}
      <div className="h-12 bg-[#101621] border-b border-[#1c2738] px-4 flex items-center justify-between text-xs font-mono flex-shrink-0">
        <div className="flex items-center space-x-3">
          <span className="text-slate-400 font-sans font-semibold">Evidence Vault:</span>
          <select
            value={selectedEvidenceId}
            onChange={(e) => setSelectedEvidenceId(e.target.value)}
            className="bg-[#182333] border border-[#25364d] rounded px-2.5 py-1 text-slate-200 text-xs focus:outline-none focus:border-cyan-500"
          >
            {evidenceList.map((e) => (
              <option key={e.id} value={e.id}>
                {e.name} ({e.source_type}) - {(e.file_size / (1024 * 1024)).toFixed(1)} MB
              </option>
            ))}
          </select>

          <button
            onClick={handleSelectEvidenceFile}
            className="px-2.5 py-1 rounded bg-[#162030] border border-cyan-500/40 text-cyan-300 hover:bg-cyan-600/30 transition-colors flex items-center space-x-1.5"
            title="Browse and select a forensic evidence file or archive to import into this case"
          >
            <FolderUp size={13} />
            <span>Select & Import File...</span>
          </button>
        </div>

        {selectedEvidence && (
          <div className="flex items-center space-x-3">
            <span className="text-slate-400">
              SHA-256: <code className="text-amber-400">{selectedEvidence.sha256.slice(0, 16)}...</code>
            </span>
            <span
              className={`px-2 py-0.5 rounded text-[11px] font-semibold flex items-center space-x-1 ${
                selectedEvidence.verification_status === 'match'
                  ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/60'
                  : 'bg-rose-950/60 text-rose-400 border border-rose-800/60'
              }`}
            >
              {selectedEvidence.verification_status === 'match' ? (
                <>
                  <ShieldCheck size={12} />
                  <span>HASH VERIFIED</span>
                </>
              ) : (
                <>
                  <ShieldAlert size={12} />
                  <span>MISMATCH</span>
                </>
              )}
            </span>
            <button
              onClick={handleVerify}
              disabled={isVerifying}
              className="px-2 py-1 rounded bg-[#1b2536] border border-[#283952] text-slate-300 hover:text-cyan-300 hover:border-cyan-500/50 transition-colors flex items-center space-x-1"
            >
              <RefreshCw size={12} className={isVerifying ? 'animate-spin' : ''} />
              <span>Verify Integrity</span>
            </button>
          </div>
        )}
      </div>

      {/* Main Split: Tree (Left) and Hex/Text Viewer (Right) */}
      <div className="flex-1 flex overflow-hidden min-h-0">
        {/* Left Tree Panel with Slide (horizontal scroll) & Window Adjustment (resizable width) */}
        {!isCollapsed && (
          <div
            style={{ width: `${treeWidth}px` }}
            className="border-r border-[#1c2738] bg-[#0e131c] flex flex-col flex-shrink-0 relative overflow-hidden"
          >
            {/* Tree Header with Window Adjustment Controls */}
            <div className="p-2 border-b border-[#1c2738] bg-[#0d121b] text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center justify-between select-none flex-shrink-0">
              <div className="flex items-center space-x-1.5 truncate">
                <span className="truncate">Evidence Hierarchy</span>
                <span className="text-[10px] text-cyan-400/80 font-mono">({treeWidth}px)</span>
              </div>

              {/* Window Adjustment Presets & Collapse Toggle */}
              <div className="flex items-center space-x-1 flex-shrink-0">
                <button
                  onClick={() => { setTreeWidth(320); localStorage.setItem('mmf_tree_width', '320'); }}
                  className={`px-1.5 py-0.5 rounded text-[9px] font-mono transition-colors ${
                    treeWidth === 320
                      ? 'bg-cyan-500/25 text-cyan-300 border border-cyan-500/50'
                      : 'bg-[#162030] text-slate-400 hover:text-slate-200 border border-[#202d3f]'
                  }`}
                  title="Compact Width (320px)"
                >
                  320
                </button>
                <button
                  onClick={() => { setTreeWidth(480); localStorage.setItem('mmf_tree_width', '480'); }}
                  className={`px-1.5 py-0.5 rounded text-[9px] font-mono transition-colors ${
                    treeWidth === 480
                      ? 'bg-cyan-500/25 text-cyan-300 border border-cyan-500/50'
                      : 'bg-[#162030] text-slate-400 hover:text-slate-200 border border-[#202d3f]'
                  }`}
                  title="Wide Width (480px)"
                >
                  480
                </button>
                <button
                  onClick={() => { setTreeWidth(650); localStorage.setItem('mmf_tree_width', '650'); }}
                  className={`px-1.5 py-0.5 rounded text-[9px] font-mono transition-colors ${
                    treeWidth === 650
                      ? 'bg-cyan-500/25 text-cyan-300 border border-cyan-500/50'
                      : 'bg-[#162030] text-slate-400 hover:text-slate-200 border border-[#202d3f]'
                  }`}
                  title="Ultra-Wide Width (650px)"
                >
                  650
                </button>
                <button
                  onClick={() => setIsCollapsed(true)}
                  className="p-1 rounded bg-[#162030] text-slate-400 hover:text-cyan-300 border border-[#202d3f] transition-colors ml-1"
                  title="Collapse Hierarchy Panel"
                >
                  <ChevronLeft size={13} />
                </button>
              </div>
            </div>

            {/* Tree Search & Quick Expand/Collapse Toolbar */}
            <div className="p-2 border-b border-[#1c2738] bg-[#0b1018] flex flex-col gap-1.5 flex-shrink-0 select-none">
              <div className="relative flex items-center">
                <Search size={13} className="absolute left-2.5 text-slate-500 pointer-events-none" />
                <input
                  type="text"
                  value={treeSearchQuery}
                  onChange={(e) => setTreeSearchQuery(e.target.value)}
                  placeholder="Filter files & folders..."
                  className="w-full bg-[#131b26] border border-[#223145] rounded pl-8 pr-7 py-1 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 font-mono transition-colors"
                />
                {treeSearchQuery && (
                  <button
                    onClick={() => setTreeSearchQuery('')}
                    className="absolute right-2 text-slate-400 hover:text-slate-200"
                    title="Clear search"
                  >
                    <X size={13} />
                  </button>
                )}
              </div>

              <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 px-0.5">
                <div className="flex items-center space-x-1">
                  {treeSearchQuery.trim() ? (
                    <span className="text-cyan-400 font-semibold">
                      {matchCount} match{matchCount === 1 ? '' : 'es'}
                    </span>
                  ) : (
                    <span>
                      Total: <strong className="text-cyan-300">{totalFilesCount}</strong> files
                    </span>
                  )}
                </div>
                <div className="flex items-center space-x-1.5">
                  <button
                    onClick={handleExpandAll}
                    className="px-1.5 py-0.5 rounded bg-[#151e2c] border border-[#223146] text-[10px] text-slate-400 hover:text-cyan-300 hover:border-cyan-500/40 transition-colors flex items-center space-x-1"
                    title="Expand all folders"
                  >
                    <Maximize2 size={10} />
                    <span>Expand</span>
                  </button>
                  <button
                    onClick={handleCollapseAll}
                    className="px-1.5 py-0.5 rounded bg-[#151e2c] border border-[#223146] text-[10px] text-slate-400 hover:text-cyan-300 hover:border-cyan-500/40 transition-colors flex items-center space-x-1"
                    title="Collapse all folders"
                  >
                    <Minimize2 size={10} />
                    <span>Collapse</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Tree Content with Smooth Horizontal & Vertical Sliding (Scroll) */}
            <div
              ref={treeContainerRef}
              className="flex-1 overflow-y-auto overflow-x-auto p-2"
            >
              {isLoadingTree ? (
                <div className="text-center py-8 text-xs text-slate-500 font-mono">Loading extracted files...</div>
              ) : displayedTree.length > 0 ? (
                renderTree(displayedTree)
              ) : treeSearchQuery.trim() ? (
                <div className="text-center py-8 text-xs text-slate-500 font-mono">
                  No files or folders matching &quot;{treeSearchQuery}&quot;
                </div>
              ) : (
                <div className="text-center py-8 text-xs text-slate-500">No extracted files available</div>
              )}
            </div>
          </div>
        )}

        {/* Collapsed Rail to Re-expand */}
        {isCollapsed && (
          <div className="w-8 bg-[#0d121b] border-r border-[#1c2738] flex flex-col items-center py-2 flex-shrink-0">
            <button
              onClick={() => setIsCollapsed(false)}
              className="p-1.5 rounded bg-[#162030] text-cyan-400 hover:bg-cyan-500/20 border border-cyan-500/40"
              title="Expand Evidence Hierarchy"
            >
              <ChevronRight size={14} />
            </button>
          </div>
        )}

        {/* Draggable Divider Splitter Handle */}
        {!isCollapsed && (
          <div
            onMouseDown={handleMouseDown}
            className={`w-1.5 hover:w-2 hover:bg-cyan-500 cursor-col-resize transition-all select-none z-20 flex items-center justify-center flex-shrink-0 ${
              isDragging ? 'bg-cyan-500 w-2 shadow-lg shadow-cyan-500/50' : 'bg-[#182232] border-r border-[#1e2a3c]'
            }`}
            title="Drag horizontally to adjust panel width | Double-click to toggle width"
            onDoubleClick={() => {
              const next = treeWidth > 450 ? 320 : 540;
              setTreeWidth(next);
              localStorage.setItem('mmf_tree_width', String(next));
            }}
          >
            <GripVertical size={11} className="text-slate-500 pointer-events-none" />
          </div>
        )}

        {/* Right Preview Panel */}
        <div className="flex-1 flex flex-col bg-[#0b0e14] min-w-0 overflow-hidden">
          {/* Preview Tab Bar */}
          <div className="h-10 bg-[#111722] border-b border-[#1c2738] px-3 flex items-center justify-between flex-shrink-0">
            <div className="flex items-center space-x-2">
              {previewData?.is_sqlite && (
                <button
                  onClick={() => setPreviewTab('database')}
                  className={`px-2.5 py-1 rounded text-xs font-semibold flex items-center space-x-1.5 transition-colors ${
                    previewTab === 'database'
                      ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 shadow-sm shadow-cyan-950/40'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Database size={13} className="text-cyan-400" />
                  <span>Database Inspector</span>
                  <span className="text-[10px] px-1.5 py-0.2 rounded bg-cyan-950 border border-cyan-800 text-cyan-300 font-mono">
                    {previewData.sqlite_info?.tables?.length || 0} tables
                  </span>
                </button>
              )}

              {previewData?.is_image && (
                <button
                  onClick={() => setPreviewTab('image')}
                  className={`px-2.5 py-1 rounded text-xs font-semibold flex items-center space-x-1.5 transition-colors ${
                    previewTab === 'image'
                      ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 shadow-sm shadow-cyan-950/40'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <ImageIcon size={13} className="text-cyan-400" />
                  <span>Image Preview</span>
                </button>
              )}

              <button
                onClick={() => setPreviewTab('hex')}
                className={`px-2.5 py-1 rounded text-xs font-semibold flex items-center space-x-1.5 transition-colors ${
                  previewTab === 'hex'
                    ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Binary size={13} />
                <span>Hexadecimal View</span>
              </button>

              <button
                onClick={() => setPreviewTab('text')}
                className={`px-2.5 py-1 rounded text-xs font-semibold flex items-center space-x-1.5 transition-colors ${
                  previewTab === 'text'
                    ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <FileText size={13} />
                <span>Text Preview</span>
              </button>
            </div>

            {previewData && (
              <div className="flex items-center space-x-3 text-xs font-mono text-slate-400">
                <span>File: <strong className="text-slate-200">{previewData.file_name}</strong></span>
                <span>Size: {(previewData.file_size / 1024).toFixed(1)} KB</span>
                {previewTab === 'hex' && (
                  <div className="flex items-center space-x-1">
                    <button
                      disabled={offset <= 0}
                      onClick={() => setOffset(Math.max(0, offset - 4096))}
                      className="px-1.5 py-0.5 rounded bg-[#182333] border border-[#25364d] text-slate-300 disabled:opacity-40"
                    >
                      Prev 4KB
                    </button>
                    <span className="text-[11px] px-1.5 text-cyan-400">
                      Offset: 0x{offset.toString(16).toUpperCase().padStart(8, '0')}
                    </span>
                    <button
                      disabled={offset + 4096 >= (previewData.file_size || 0)}
                      onClick={() => setOffset(offset + 4096)}
                      className="px-1.5 py-0.5 rounded bg-[#182333] border border-[#25364d] text-slate-300 disabled:opacity-40"
                    >
                      Next 4KB
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Viewer Content with Slide (Scroll) */}
          <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
            {previewData ? (
              previewTab === 'database' && previewData.sqlite_info ? (
                /* Dedicated Database Inspector View */
                <div className="flex-1 flex flex-col min-h-0 bg-[#0a0d13]">
                  {/* Table Selection Pills & Toolbar */}
                  <div className="px-3 py-2 bg-[#0e131d] border-b border-[#1c2738] flex flex-wrap items-center justify-between gap-2 flex-shrink-0 select-none">
                    <div className="flex items-center space-x-1.5 overflow-x-auto py-0.5 max-w-[60%]">
                      <span className="text-slate-400 text-xs font-sans font-semibold flex items-center space-x-1 mr-1 flex-shrink-0">
                        <Table size={12} className="text-cyan-400" />
                        <span>Tables:</span>
                      </span>
                      {previewData.sqlite_info.tables?.map((tbl: any) => (
                        <button
                          key={tbl.name}
                          onClick={() => handleSelectDbTable(tbl.name)}
                          className={`px-2.5 py-1 rounded text-xs font-mono transition-colors flex items-center space-x-1.5 flex-shrink-0 ${
                            selectedDbTable === tbl.name
                              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold shadow-sm shadow-cyan-950/40'
                              : 'bg-[#141b27] text-slate-400 hover:text-slate-200 border border-[#202d3e]'
                          }`}
                        >
                          <span>{tbl.name}</span>
                          <span className="text-[10px] px-1 rounded bg-[#0f1722] text-slate-400 font-normal">
                            {tbl.row_count}
                          </span>
                        </button>
                      ))}
                    </div>

                    <div className="flex items-center space-x-2">
                      {/* Human-Readable Mode Switch */}
                      <button
                        onClick={() => setIsDbHumanReadable(!isDbHumanReadable)}
                        className={`px-2.5 py-1 rounded text-xs font-semibold flex items-center space-x-1.5 transition-all shadow-sm ${
                          isDbHumanReadable
                            ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/50 shadow-cyan-950/40'
                            : 'bg-[#151e2c] text-slate-400 border border-[#223145] hover:text-slate-200'
                        }`}
                        title="Automatically decodes timestamps (Windows FileTime & Unix), toast XML payloads, BLOBs, JSON, and clean strings"
                      >
                        <Sparkles size={13} className={isDbHumanReadable ? 'text-cyan-400' : 'text-slate-500'} />
                        <span>Human-Readable:</span>
                        <strong className={isDbHumanReadable ? 'text-cyan-300 font-bold' : 'text-slate-400'}>
                          {isDbHumanReadable ? 'ON' : 'RAW'}
                        </strong>
                      </button>

                      {/* In-table search filter */}
                      <div className="relative flex items-center">
                        <Search size={12} className="absolute left-2.5 text-slate-500 pointer-events-none" />
                        <input
                          type="text"
                          value={dbSearchFilter}
                          onChange={(e) => setDbSearchFilter(e.target.value)}
                          placeholder="Filter table rows..."
                          className="w-36 bg-[#141b27] border border-[#202d3e] rounded pl-7 pr-6 py-1 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono"
                        />
                        {dbSearchFilter && (
                          <button
                            onClick={() => setDbSearchFilter('')}
                            className="absolute right-1.5 text-slate-400 hover:text-slate-200"
                          >
                            <X size={12} />
                          </button>
                        )}
                      </div>

                      {/* CSV Export */}
                      <button
                        onClick={handleExportDbCsv}
                        className="px-2 py-1 rounded bg-[#16202f] border border-[#223145] text-slate-300 hover:text-cyan-300 hover:border-cyan-500/50 transition-colors flex items-center space-x-1"
                        title="Export current table to CSV"
                      >
                        <Download size={12} />
                        <span>CSV</span>
                      </button>
                    </div>
                  </div>

                  {/* Interactive Decoded Table View */}
                  <div className="flex-1 overflow-auto p-2">
                    {isDbLoading ? (
                      <div className="text-center py-20 text-slate-500 font-mono text-xs flex items-center justify-center space-x-2">
                        <RefreshCw size={14} className="animate-spin text-cyan-400" />
                        <span>Loading table records...</span>
                      </div>
                    ) : dbTableRows.length > 0 && dbTableColumns.length > 0 ? (
                      <table className="w-full text-left text-xs font-mono border-collapse select-text">
                        <thead>
                          <tr className="bg-[#141b27] text-slate-400 uppercase text-[10px] sticky top-0 border-b border-[#1c2738] z-10">
                            <th className="py-2 px-2 text-slate-600 w-8 text-center">#</th>
                            {dbTableColumns.map((col, i) => (
                              <th key={i} className="py-2 px-2.5 whitespace-nowrap">
                                {col}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[#17212f]">
                          {filteredDbRows.map((row: any, rIdx: number) => (
                            <tr key={rIdx} className="hover:bg-cyan-500/5 transition-colors group">
                              <td className="py-1.5 px-2 text-[10px] text-slate-600 font-mono text-center select-none">
                                {rIdx + 1}
                              </td>
                              {dbTableColumns.map((col, cIdx) => {
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
                                    ) : isDbHumanReadable ? (
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
                        No records found in table &quot;{selectedDbTable}&quot;.
                      </div>
                    )}
                  </div>
                </div>
              ) : previewTab === 'image' && previewData.image_base64 ? (
                /* Image Preview View */
                <div className="flex-1 flex flex-col items-center justify-center p-6 bg-[#0a0d13] overflow-auto">
                  <div className="bg-[#111723] p-4 rounded-lg border border-[#202f43] shadow-xl text-center max-w-full">
                    <img
                      src={`data:image/png;base64,${previewData.image_base64}`}
                      alt={previewData.file_name}
                      className="max-h-[70vh] max-w-full rounded border border-[#1f2d3f] shadow-lg object-contain mx-auto"
                    />
                    <div className="mt-3 text-xs font-mono text-slate-400 flex items-center justify-center space-x-3">
                      <span>{previewData.file_name}</span>
                      <span>•</span>
                      <span>{(previewData.file_size / 1024).toFixed(1)} KB</span>
                    </div>
                  </div>
                </div>
              ) : previewTab === 'hex' ? (
                /* Hexadecimal View */
                <div className="flex-1 overflow-y-auto overflow-x-auto p-4 font-mono text-xs">
                  <div className="space-y-0.5 select-text min-w-max">
                    <div className="text-slate-500 text-[11px] border-b border-[#1c2738] pb-1 mb-2 flex">
                      <span className="w-24">OFFSET</span>
                      <span className="w-96">00 01 02 03 04 05 06 07  08 09 0A 0B 0C 0D 0E 0F</span>
                      <span>ASCII</span>
                    </div>
                    {previewData.hex_lines?.map((line: any, idx: number) => (
                      <div key={idx} className="flex hover:bg-cyan-500/5 py-0.5">
                        <span className="w-24 text-slate-500">{line.offset}</span>
                        <span className="w-96 text-cyan-300 font-medium">{line.hex}</span>
                        <span className="text-slate-300 border-l border-[#1f2c40] pl-2">{line.ascii}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                /* Text Preview View with Clean Strings Option */
                <div className="flex-1 flex flex-col min-h-0 bg-[#0a0d13]">
                  <div className="px-3 py-1.5 bg-[#0e131d] border-b border-[#1c2738] flex items-center justify-between text-xs font-mono select-none flex-shrink-0">
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => setCleanStringsOnly(true)}
                        className={`px-2.5 py-0.5 rounded text-[11px] font-semibold flex items-center space-x-1 transition-colors ${
                          cleanStringsOnly
                            ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm shadow-cyan-950/40'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                        title="Filter out null bytes and binary control characters, showing only clean human-readable strings"
                      >
                        <Sparkles size={11} />
                        <span>Clean Readable Strings</span>
                      </button>
                      <button
                        onClick={() => setCleanStringsOnly(false)}
                        className={`px-2.5 py-0.5 rounded text-[11px] font-semibold flex items-center space-x-1 transition-colors ${
                          !cleanStringsOnly
                            ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                        title="Raw text decode including binary control characters"
                      >
                        <span>Raw Chunk Decode</span>
                      </button>
                    </div>
                    <span className="text-[11px] text-slate-500">
                      {cleanStringsOnly ? 'Filtered printable strings (>= 4 chars)' : 'Raw UTF-8 / ASCII chunk'}
                    </span>
                  </div>
                  <div className="flex-1 overflow-auto p-4">
                    <pre className="text-slate-300 whitespace-pre-wrap font-mono text-xs select-text leading-relaxed">
                      {cleanStringsOnly
                        ? (previewData.clean_text_preview || 'No printable strings found in this chunk.')
                        : (previewData.text_preview || 'No readable text content in this chunk.')}
                    </pre>
                  </div>
                </div>
              )
            ) : (
              <div className="text-center py-20 text-slate-500">
                Select a file from the evidence tree to inspect byte structure.
              </div>
            )}
          </div>
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

              {/* Copy Actions */}
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
                          <code className="text-amber-400">{String(inspectCell.decoded.details.epoch ?? inspectCell.decoded.rawValue)}</code>
                        </div>
                      </div>
                    </div>
                  )}

                  {inspectCell.decoded.type === 'json' && inspectCell.decoded.details?.formattedJson && (
                    <div>
                      <span className="text-slate-400 block mb-1">DECODED STRUCTURED PAYLOAD:</span>
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


interface TreeNodeProps {
  node: any;
  selectedFile: string;
  expandedPaths: Set<string>;
  onToggleExpand: (path: string) => void;
  onSelectFile: (p: string) => void;
}

const TreeNode: React.FC<TreeNodeProps> = ({
  node,
  selectedFile,
  expandedPaths,
  onToggleExpand,
  onSelectFile,
}) => {
  const isExpanded = expandedPaths.has(node.path);
  const isSelected = selectedFile === node.path;
  const fileCount = countFiles(node);

  if (node.is_dir) {
    return (
      <li>
        <div
          onClick={() => onToggleExpand(node.path)}
          className="group flex items-center space-x-1.5 py-1 px-1.5 rounded hover:bg-[#161f2e] cursor-pointer text-slate-300 whitespace-nowrap transition-colors"
        >
          {isExpanded ? (
            <ChevronDown size={14} className="text-slate-400 flex-shrink-0" />
          ) : (
            <ChevronRight size={14} className="text-slate-500 flex-shrink-0 group-hover:text-slate-300" />
          )}
          {isExpanded ? (
            <FolderOpen size={14} className="text-cyan-400 flex-shrink-0" />
          ) : (
            <Folder size={14} className="text-cyan-500/80 flex-shrink-0 group-hover:text-cyan-400" />
          )}
          <span className="whitespace-nowrap select-text font-medium text-slate-200">{node.name}</span>
          <span
            className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-[#131b27] border border-[#1e2a3c] text-cyan-400/90 ml-1.5 flex-shrink-0"
            title={`${fileCount} files inside`}
          >
            {fileCount} {fileCount === 1 ? 'file' : 'files'}
          </span>
        </div>
        {isExpanded && node.children && node.children.length > 0 && (
          <ul className="pl-4 border-l border-[#1c2738] ml-2 space-y-0.5 mt-0.5 min-w-max">
            {node.children.map((c: any, i: number) => (
              <TreeNode
                key={c.path || i}
                node={c}
                selectedFile={selectedFile}
                expandedPaths={expandedPaths}
                onToggleExpand={onToggleExpand}
                onSelectFile={onSelectFile}
              />
            ))}
          </ul>
        )}
      </li>
    );
  }

  return (
    <li>
      <div
        onClick={() => onSelectFile(node.path)}
        className={`flex items-center space-x-1.5 py-1 px-1.5 rounded cursor-pointer whitespace-nowrap transition-colors ${
          isSelected
            ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm shadow-cyan-950/40'
            : 'text-slate-400 hover:text-slate-200 hover:bg-[#161f2e]'
        }`}
      >
        <FileCode size={13} className={`flex-shrink-0 ${isSelected ? 'text-cyan-400' : 'text-slate-500'}`} />
        <span className="whitespace-nowrap select-text mr-4">{node.name}</span>
        <span className="text-[10px] text-slate-600 ml-auto flex-shrink-0 font-mono">
          {(node.size / 1024).toFixed(0)}K
        </span>
      </div>
    </li>
  );
};
