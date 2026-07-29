import type { RepositoryResponse } from './repository';

export interface WorkspaceResponse {
  id: number;
  workspace_name: string;
  description?: string | null;
  owner_id: number;
}

export interface WorkspaceCreate {
  workspace_name: string;
  description?: string | null;
}

export interface WorkspaceUpdate {
  workspace_name?: string | null;
  description?: string | null;
}

/**
 * `project_id` here is a backend naming artifact — it's actually the
 * workspace-membership row id, not a Project (sub-project) id. Kept verbatim
 * (not renamed client-side) per plans/frontend_dev_plan.md.
 */
export interface MemberResponse {
  project_id: number;
  user_id: number;
  email?: string | null;
  username?: string | null;
}

export interface AddMemberRequest {
  email: string;
}

/** Full nested tree: Workspace -> Repositories -> Branches -> Projects, plus Members. */
export interface WorkspaceHierarchyResponse {
  id: number;
  workspace_name: string;
  owner_id: number;
  members: MemberResponse[];
  repositories: RepositoryResponse[];
}
