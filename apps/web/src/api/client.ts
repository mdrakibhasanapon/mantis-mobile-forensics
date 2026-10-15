import {
  Case,
  Evidence,
  Artifact,
  TimelineEvent,
  CaseStatistics,
  AuditRecord,
  BackgroundJob,
  CorrelationLink,
  TriageFinding,
  RecoveredItem,
} from '../types';

let cachedBaseUrl = 'http://127.0.0.1:8765';
let cachedToken = '';

async function initConfig() {
  if (typeof window !== 'undefined' && (window as any).mantisDesktop) {
    try {
      const cfg = await (window as any).mantisDesktop.getApiConfig();
      if (cfg) {
        cachedBaseUrl = cfg.baseUrl || 'http://127.0.0.1:8765';
        cachedToken = cfg.token || '';
      }
    } catch (e) {
      console.warn('Failed to fetch desktop API config:', e);
    }
  }
}

initConfig();

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  if (!cachedToken && typeof window !== 'undefined' && (window as any).mantisDesktop) {
    await initConfig();
  }

  const url = `${cachedBaseUrl}${endpoint}`;
  const headers = new Headers(options.headers || {});
  headers.set('Content-Type', 'application/json');
  if (cachedToken) {
    headers.set('X-MMF-Session-Token', cachedToken);
  }

  const res = await fetch(url, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`API Error [${res.status}]: ${errText}`);
  }

  return res.json();
}

export const api = {
  // Health
  getHealth: () => request<any>('/health'),

  // Cases
  listCases: () => request<Case[]>('/cases'),
  createCase: (data: { case_number: string; title: string; investigator: string; agency?: string; description?: string }) =>
    request<Case>('/cases', { method: 'POST', body: JSON.stringify(data) }),
  getActiveCase: () => request<Case | null>('/cases/active'),
  setActiveCase: (caseId: string) => request<any>(`/cases/active/${caseId}`, { method: 'POST' }),
  getCaseStats: (caseId: string) => request<CaseStatistics>(`/cases/${caseId}/stats`),
  getCaseAudit: (caseId: string) => request<{ records: AuditRecord[]; verification: any }>(`/cases/${caseId}/audit`),
  exportManifest: (caseId: string) => request<any>(`/cases/${caseId}/manifest`, { method: 'POST' }),

  // Devices & Acquisition
  getDeviceStatus: () => request<any>('/devices/status'),
  generateSynthetic: (caseId: string, deviceName?: string) =>
    request<{ status: string; job_id: string }>('/evidence/generate-synthetic', {
      method: 'POST',
      body: JSON.stringify({ case_id: caseId, device_name: deviceName }),
    }),
  importPath: (caseId: string, sourcePath: string, sourceType = 'archive') =>
    request<Evidence>('/evidence/import-path', {
      method: 'POST',
      body: JSON.stringify({ case_id: caseId, source_path: sourcePath, source_type: sourceType }),
    }),

  // Evidence Explorer
  listEvidence: (caseId: string) => request<Evidence[]>(`/evidence?case_id=${caseId}`),
  getEvidenceTree: (caseId: string, evidenceId: string) =>
    request<{ tree: any[] }>(`/evidence/${evidenceId}/tree?case_id=${caseId}`),
  getFilePreview: (caseId: string, evidenceId: string, path: string, offset = 0, length = 4096) =>
    request<any>(`/evidence/${evidenceId}/preview?case_id=${caseId}&path=${encodeURIComponent(path)}&offset=${offset}&length=${length}`),
  verifyEvidence: (caseId: string, evidenceId: string) =>
    request<{ status: string; error?: string }>(`/evidence/${evidenceId}/verify?case_id=${caseId}`, { method: 'POST' }),
  queryEvidenceDb: (caseId: string, evidenceId: string, relativePath: string, tableName: string, limit = 50, offset = 0) =>
    request<any>(`/evidence/${evidenceId}/query-db`, {
      method: 'POST',
      body: JSON.stringify({
        case_id: caseId,
        relative_path: relativePath,
        table_name: tableName,
        limit,
        offset,
      }),
    }),

  // Artifacts & Timeline
  listArtifacts: (caseId: string, category?: string, query?: string, limit = 500) => {
    let q = `/artifacts?case_id=${caseId}&limit=${limit}`;
    if (category) q += `&category=${encodeURIComponent(category)}`;
    if (query) q += `&query=${encodeURIComponent(query)}`;
    return request<Artifact[]>(q);
  },
  listTimeline: (caseId: string, eventType?: string, limit = 500) => {
    let q = `/timeline?case_id=${caseId}&limit=${limit}`;
    if (eventType) q += `&event_type=${encodeURIComponent(eventType)}`;
    return request<TimelineEvent[]>(q);
  },
  exportTimelineCsvUrl: (caseId: string) =>
    `${cachedBaseUrl}/timeline/export-csv?case_id=${caseId}${cachedToken ? `&token=${encodeURIComponent(cachedToken)}` : ''}`,

  // Forensics: Correlations, Triage, Recovery, SQLite
  getCorrelations: (caseId: string) => request<CorrelationLink[]>(`/forensics/correlations?case_id=${caseId}`),
  getTriageFindings: (caseId: string) => request<TriageFinding[]>(`/forensics/triage?case_id=${caseId}`),
  getRecoveredItems: (caseId: string) => request<RecoveredItem[]>(`/forensics/recovered?case_id=${caseId}`),
  listSqliteDatabases: (caseId: string) => request<any[]>(`/forensics/sqlite/databases?case_id=${caseId}`),
  getSqliteSchema: (caseId: string, relativeDbPath: string) =>
    request<any>(`/forensics/sqlite/schema?case_id=${caseId}&relative_db_path=${encodeURIComponent(relativeDbPath)}`),
  executeSqliteQuery: (caseId: string, relativeDbPath: string, query: string, limit = 100) =>
    request<any>('/forensics/sqlite/query', {
      method: 'POST',
      body: JSON.stringify({ case_id: caseId, relative_db_path: relativeDbPath, query, limit }),
    }),
  getSqliteFreelist: (caseId: string, relativeDbPath: string) =>
    request<{ carved_strings: any[]; count: number }>(`/forensics/sqlite/freelist?case_id=${caseId}&relative_db_path=${encodeURIComponent(relativeDbPath)}`),

  // Reports
  generateHtmlReport: (caseId: string) => request<any>(`/reports/generate-html?case_id=${caseId}`, { method: 'POST' }),
  getViewHtmlReportUrl: (caseId: string) =>
    `${cachedBaseUrl}/reports/view-html?case_id=${caseId}${cachedToken ? `&token=${encodeURIComponent(cachedToken)}` : ''}`,

  // Background Jobs
  listJobs: (caseId?: string) => request<BackgroundJob[]>(`/jobs${caseId ? `?case_id=${caseId}` : ''}`),
  getActiveJobs: () => request<BackgroundJob[]>('/jobs/active'),
  cancelJob: (jobId: string) => request<any>(`/jobs/${jobId}/cancel`, { method: 'POST' }),
};
