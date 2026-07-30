/**
 * Types for features the backend does not expose yet (see "Missing-API
 * Items" in plans/frontend_dev_plan.md). Shapes are this app's own best
 * guess at what a future endpoint would need — adjust once the real
 * contract exists.
 */
export interface UpdateRepositoryRequest {
  name: string;
}

export interface UpdateBranchRequest {
  commit_hashed: string;
}

/** Backend removed PATCH /workspaces/{id} — demoted from real to template. */
export interface UpdateWorkspaceRequest {
  workspace_name?: string | null;
  description?: string | null;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface ForgotPasswordRequest {
  email: string;
}

export interface ResetPasswordRequest {
  token: string;
  new_password: string;
}

export interface UpdateProfileRequest {
  username?: string;
  full_name?: string;
  email?: string;
}
