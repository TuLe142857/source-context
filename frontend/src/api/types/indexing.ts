/**
 * `status` is a free string on the backend (not formally tied to the
 * BranchIndexingStatus enum) — don't assume it only ever holds those 5 values.
 */
export interface IndexingJobResponse {
  id: number;
  workspace_id: number;
  branch_id: number;
  status: string;
  progress_pct: number;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface IndexingRunResponse {
  id: number;
  workspace_id: number;
  branch_id: number;
  job_id: number | null;
  base_commit_sha: string | null;
  target_commit_sha: string;
  mode: string;
  status: string;
  current_stage: string | null;
  fallback_reason: string | null;
  error_message: string | null;
  statistics: Record<string, number> | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface IndexingStateResponse {
  workspace_id: number;
  branch_id: number;
  latest_observed_commit_sha: string | null;
  indexed_commit_sha: string | null;
  index_version: string | null;
  checkpoint_valid: boolean;
  status: string;
  updated_at: string;
}
