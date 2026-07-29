import type { ProjectResponse } from './project';

export type BranchIndexingStatus = 'UNINDEXED' | 'INDEXING' | 'INDEXED' | 'OUTDATED' | 'FAILED';

export const BRANCH_INDEXING_STATUSES: BranchIndexingStatus[] = [
  'UNINDEXED',
  'INDEXING',
  'INDEXED',
  'OUTDATED',
  'FAILED',
];

export interface BranchCreateRequest {
  branch_name: string;
  /** Commit hash SHA or "HEAD". Defaults to "HEAD" on the backend. */
  commit_hashed?: string;
}

export interface BranchResponse {
  id: number;
  repository_id: number;
  branch_name: string;
  commit_hashed: string;
  indexing_status: BranchIndexingStatus;
  local_path?: string | null;
  projects: ProjectResponse[];
}
