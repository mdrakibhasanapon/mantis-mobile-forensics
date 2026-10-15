export interface Case {
  id: string;
  case_number: string;
  title: string;
  investigator: string;
  agency?: string;
  created_at: string;
  updated_at: string;
  status: string;
  description?: string;
  storage_path: string;
  evidence_count: number;
  artifact_count: number;
}

export interface Evidence {
  id: string;
  case_id: string;
  name: string;
  source_type: string;
  original_path: string;
  stored_path: string;
  file_size: number;
  sha256: string;
  acquired_at: string;
  acquisition_method: string;
  device_info: Record<string, any>;
  status: string;
  verification_status: 'match' | 'mismatch' | 'unverified' | 'error';
  error_message?: string;
}

export interface Artifact {
  id: string;
  case_id: string;
  evidence_id: string;
  platform: string;
  category: string;
  subcategory?: string;
  raw_data: Record<string, any>;
  normalized_data: Record<string, any>;
  timestamp_utc?: string;
  original_timestamp?: string;
  source_file: string;
  source_table?: string;
  source_row_id?: string;
  parser_id: string;
  parser_version: string;
  confidence: number;
  recovery_status: string;
  notes?: string;
}

export interface TimelineEvent {
  id: string;
  case_id: string;
  evidence_id: string;
  timestamp_utc: string;
  event_type: string;
  title: string;
  description: string;
  source_file: string;
  raw_timestamp?: string;
  details: Record<string, any>;
}

export interface CaseStatistics {
  evidence_count: number;
  total_bytes: number;
  total_artifacts: number;
  contacts_count: number;
  messages_count: number;
  calls_count: number;
  browser_count: number;
  installed_apps_count: number;
  wireless_count: number;
  app_data_count: number;
  recovered_items_count: number;
  triage_findings_count: number;
  timeline_events_count: number;
  correlations_count: number;
  category_breakdown: Record<string, number>;
}

export interface AuditRecord {
  id: string;
  case_id: string;
  timestamp: string;
  action: string;
  actor: string;
  details: Record<string, any>;
  evidence_id?: string;
  hash_signature: string;
}

export interface BackgroundJob {
  id: string;
  case_id?: string;
  job_type: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  message: string;
  created_at: string;
  finished_at?: string;
  error?: string;
}

export interface CorrelationLink {
  id: string;
  case_id: string;
  entity_type: string;
  value: string;
  occurrences: number;
  linked_artifact_ids: string[];
  linked_evidence_ids: string[];
  description: string;
}

export interface TriageFinding {
  id: string;
  case_id: string;
  evidence_id: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  category: string;
  rule_id: string;
  title: string;
  description: string;
  target_file: string;
  details: Record<string, any>;
}

export interface RecoveredItem {
  id: string;
  case_id: string;
  source_file: string;
  offset: number;
  recovery_method: string;
  classification: string;
  data_preview: string;
  confidence: number;
  parsed_fields: Record<string, any>;
}

declare global {
  interface Window {
    mantisDesktop?: {
      isDesktop: boolean;
      getApiConfig: () => Promise<{ port: number; token: string; baseUrl: string; dataDir: string }>;
      openDataDirectory: () => Promise<void>;
      checkActiveJobs: () => Promise<any[]>;
      showSaveDialog: (options: any) => Promise<{ canceled: boolean; filePath?: string }>;
      showOpenDialog: (options: any) => Promise<{ canceled: boolean; filePaths: string[] }>;
    };
  }
}
