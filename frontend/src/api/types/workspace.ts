import type { RepositoryResponse } from './repository';

export interface WorkspaceResponse {
  id: number;
  workspace_name: string;
  description?: string | null;
  owner_id: number;
}

export interface CreateWorkspaceRequest {
  workspace_name: string;
  description?: string | null;
}

/**
 * `project_id` here is a backend naming artifact — it's actually the
 * workspace-membership row id, not a Project (sub-project) id. Kept verbatim
 * (not renamed client-side) per plans/frontend_dev_plan.md.
 */
export interface MemberResponse {
  workspace_id?: number | null;
  project_id?: number | null;
  user_id: number;
  email?: string | null;
  username?: string | null;
  full_name?: string | null;
}

/** Backend accepts either — at least one must be provided. */
export interface AddMemberRequest {
  email?: string;
  user_id?: number;
}

/** Full nested tree: Workspace -> Repositories -> Branches -> Projects, plus Members. */
export interface WorkspaceHierarchyResponse {
  id: number;
  workspace_name: string;
  owner_id: number;
  members: MemberResponse[];
  repositories: RepositoryResponse[];
}
