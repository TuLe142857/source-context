import type { BranchCreateRequest, BranchResponse } from './branch';

export interface RepositoryResponse {
  id: number;
  name: string;
  git_url: string;
  branches: BranchResponse[];
}

export interface RepositoryCreateRequest {
  name: string;
  git_url: string;
  branches: BranchCreateRequest[];
}

export interface InspectGitHubBranchesRequest {
  git_url: string;
}

/** Response of the pre-attach preview: lists remote branches for a git URL. */
export interface RemoteBranchesResponse {
  git_url: string;
  owner: string;
  repo_name: string;
  branches: string[];
}
