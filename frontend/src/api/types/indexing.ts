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
